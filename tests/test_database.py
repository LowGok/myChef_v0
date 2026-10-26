from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from streamlit.connections import SQLConnection

import db_fetch_functions as reads
import db_insert_functions as writes


@pytest.fixture
def database(monkeypatch, tmp_path):
    connection = SQLConnection("test", url=f"sqlite:///{tmp_path / 'test.db'}")
    engine = connection._instance
    with engine.begin() as conn:
        conn.execute(text("""CREATE TABLE users (
            user_id INTEGER PRIMARY KEY, firstname TEXT, lastname TEXT,
            birthdate DATE, username TEXT, allergens TEXT, diet TEXT,
            dislikes TEXT, cooking_efforts TEXT, cooking_technique TEXT, haspref TEXT
        )"""))
        conn.execute(text("INSERT INTO users(user_id) VALUES (1), (2)"))
        conn.execute(text("""CREATE TABLE meals (
            meal_id INTEGER PRIMARY KEY, creator_id INTEGER, creationdate DATE,
            recipetitle TEXT, yield TEXT, preptime TEXT, cooktime TEXT,
            mychefnotes TEXT, equipment TEXT, instructions TEXT, allergens TEXT,
            ismeatorfish TEXT, recipeimg TEXT, totaltime TEXT, cloudinary_public_id TEXT
        )"""))
        conn.execute(text("""INSERT INTO meals(meal_id, creator_id, creationdate) VALUES
            (10, 1, '2025-12-29'), (11, 1, '2026-01-02'),
            (12, 1, '2026-12-28'), (20, 2, '2026-01-02')"""))
        conn.execute(text("""CREATE TABLE ingredients (
            recipe_id INTEGER, quantity REAL, unit TEXT, ingredient_name TEXT
        )"""))
        conn.execute(text("""INSERT INTO ingredients VALUES
            (10, 1, 'g', 'flour'), (20, 99, 'g', 'private ingredient')"""))

    monkeypatch.setattr(writes, "init_connection", lambda: connection)
    monkeypatch.setattr(reads, "init_connection", lambda: connection)
    monkeypatch.setattr(writes.st, "error", Mock())
    reads.fetch_user_recipes.clear()
    reads.fetch_recipes_ingredients.clear()
    yield engine
    reads.fetch_user_recipes.clear()
    reads.fetch_recipes_ingredients.clear()
    engine.dispose()


def test_profile_defaults_follow_the_current_user(database, monkeypatch):
    state = SimpleNamespace()
    monkeypatch.setattr(writes.st, "session_state", state)
    for user_id in (1, 2):
        state.user_instance = SimpleNamespace(user_id=user_id, firstName=f"User {user_id}",
            lastName="Chef", birthdate=date(1990, 1, 1), userName=f"chef{user_id}")
        assert writes.updateCredentials() is True
    with database.connect() as conn:
        assert conn.execute(text("SELECT firstname FROM users ORDER BY user_id")).scalars().all() == ["User 1", "User 2"]


def test_image_update_requires_ownership(database):
    assert writes.databaseImageStorage("pub", "https://example.com/image.jpg", 20, user_id=1) is False
    assert writes.databaseImageStorage("pub", "https://example.com/image.jpg", 10, user_id=1) is True
    with database.connect() as conn:
        assert conn.execute(text("SELECT recipeimg FROM meals WHERE meal_id=20")).scalar() is None


def test_missing_user_cannot_report_preferences_saved(database):
    assert writes.pushPreferences("pan", "vegan", "", "", "quick", 999) is False


def test_empty_recipe_payload_does_not_open_a_transaction(monkeypatch):
    connect = Mock()
    monkeypatch.setattr(writes, "init_connection", connect)
    monkeypatch.setattr(writes.st, "error", Mock())
    assert not writes.databaseRecipesStorage({"recipes": []}, userId=1)
    connect.assert_not_called()


def test_recipe_storage_never_defaults_to_account_one(monkeypatch):
    connect = Mock()
    monkeypatch.setattr(writes, "init_connection", connect)
    monkeypatch.setattr(writes.st, "error", Mock())
    assert not writes.databaseRecipesStorage({"recipes": [{"Recipe Title": "Soup"}]})
    connect.assert_not_called()


def test_repeated_generations_get_distinct_positive_bigint_ids(monkeypatch):
    conn = MagicMock()
    monkeypatch.setattr(writes, "init_connection", lambda: conn)
    payload = {"recipes": [{"Recipe Title": "Soup"}]}
    first = writes.databaseRecipesStorage(payload, userId=1)["Soup"]
    second = writes.databaseRecipesStorage(payload, userId=1)["Soup"]
    assert first != second
    assert 0 < first < 2**63 and 0 < second < 2**63


def test_week_spanning_new_year_excludes_other_years(database):
    plan, ids = reads.fetch_user_recipes(1, date(2026, 1, 1))
    assert ids == [10, 11]
    assert len(plan) == 2


def test_ingredients_filter_by_owner_even_with_other_users_ids(database):
    ingredients = reads.fetch_recipes_ingredients(1, [10, 20])
    assert ingredients["ingredient_name"].tolist() == ["flour"]


def test_empty_ingredients_are_a_valid_empty_result(database):
    assert reads.fetch_recipes_ingredients(1, []).empty
