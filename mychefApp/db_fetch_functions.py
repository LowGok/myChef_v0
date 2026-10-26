from datetime import timedelta

import pandas as pd
import streamlit as st

from connection import init_connection


@st.cache_data(max_entries=200, ttl=3600)
def fetch_user_recipes(userId, date):
    """Return this user's recipes in the ISO week containing date."""
    if not userId or date is None:
        raise ValueError("A user and date are required")
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=7)
    recipe_query = """
        SELECT meal_id, recipetitle, yield, preptime, cooktime, mychefnotes,
               equipment, instructions, allergens, ismeatorfish, recipeimg, totaltime
        FROM meals
        WHERE creator_id = :user
          AND creationdate >= :start AND creationdate < :end
        ORDER BY creationdate, meal_id
    """
    recipes = init_connection().query(
        recipe_query, params={"user": int(userId), "start": start, "end": end},
        show_spinner=False, ttl=0,
    )
    if recipes.empty:
        return {}, []
    return dict(enumerate(recipes.to_dict(orient="records"))), recipes["meal_id"].tolist()


@st.cache_data(max_entries=200, ttl=3600)
def fetch_recipes_ingredients(userId, recipesId):
    """Fetch ingredients only for meals owned by the requesting user."""
    if not userId:
        raise ValueError("A user is required")
    if not recipesId:
        return pd.DataFrame(columns=["recipe_id", "quantity", "unit", "ingredient_name"])
    # SQLConnection.query accepts SQL strings. Generate only parameter names here;
    # every recipe ID remains a bound value.
    recipe_params = {f"recipe_{index}": int(recipe_id)
                     for index, recipe_id in enumerate(recipesId)}
    placeholders = ", ".join(f":{name}" for name in recipe_params)
    ingredient_query = f"""
        SELECT i.recipe_id, SUM(i.quantity) AS quantity, i.unit, i.ingredient_name
        FROM ingredients AS i
        JOIN meals AS m ON m.meal_id = i.recipe_id
        WHERE m.creator_id = :user AND i.recipe_id IN ({placeholders})
        GROUP BY i.recipe_id, i.unit, i.ingredient_name
        ORDER BY i.recipe_id, i.unit, i.ingredient_name
    """
    return init_connection().query(
        ingredient_query, params={"user": int(userId), **recipe_params},
        show_spinner=False, ttl=0,
    )
