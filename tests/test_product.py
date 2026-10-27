from pathlib import Path
from unittest.mock import Mock
from unittest.mock import MagicMock
from types import SimpleNamespace
import sys

import pytest
from google.genai.errors import ClientError

from streamlit.testing.v1 import AppTest

import authentication
import generateMealPlans


@pytest.mark.parametrize("password", ["a" * 73, "é" * 37])
def test_oversized_password_is_rejected_without_database_access(monkeypatch, password):
    connection = Mock()
    monkeypatch.setattr(authentication, "init_connection", connection)
    warning = Mock()
    monkeypatch.setattr(authentication.st, "warning", warning)
    assert authentication.credentials("test@example.test", password) is False
    assert authentication.registration_protocol("test@example.test", password,
            "Test", "User", "Other", "1990-01-01", "test_user") is False
    connection.assert_not_called()
    assert "72" in warning.call_args.args[0]


def test_signed_out_page_starts_without_secrets():
    app = AppTest.from_file(str(Path("mychefApp/main.py").resolve())).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Sign-In :unlock:", "Sign-Up :receipt:"]


def test_email_cookie_cannot_authenticate(monkeypatch):
    controller = Mock()
    controller.get.return_value = "victim@example.com"
    monkeypatch.setitem(sys.modules, "streamlit_cookies_controller", SimpleNamespace(CookieController=lambda: controller))
    fetch = Mock(return_value=True)
    monkeypatch.setattr(authentication, "fetch_user_info", fetch)
    app = AppTest.from_file(str(Path("mychefApp/main.py").resolve())).run()
    assert not app.exception
    assert app.session_state["authenticated"] is False
    fetch.assert_not_called()


def test_failed_image_save_cannot_report_success(monkeypatch):
    monkeypatch.setattr(generateMealPlans, "configure_cloudinary", Mock())
    monkeypatch.setattr(generateMealPlans, "imageGenerator", Mock(return_value=b"image"))
    monkeypatch.setattr(generateMealPlans, "uploadImageToCloud", Mock(return_value={
        "public_id": "image-1", "secure_url": "https://example.com/image.jpg"}))
    monkeypatch.setattr(generateMealPlans, "databaseImageStorage", Mock(return_value=False))
    assert not generateMealPlans.generateImage(10, "carrot", meal_title="Carrot soup")
    generateMealPlans.imageGenerator.assert_called_once_with(meal="Carrot soup", ingredient_list="carrot")


def test_quota_failure_is_actionable_and_does_not_replay(monkeypatch):
    class Session(dict):
        __getattr__ = dict.__getitem__

    class Stopped(BaseException):
        pass

    state = Session(mealPreferences={"days": ["Monday"], "total_time": "30 min",
                    "adults": 2, "childs": None, "budget": "Medium", "creativity": 8},
                    preferences={"technique": "pan", "diet": "", "allergy": "",
                                 "dislikes": "", "efforts": "quick"})
    monkeypatch.setattr(generateMealPlans.st, "session_state", state)
    monkeypatch.setattr(generateMealPlans.st, "status", MagicMock())
    monkeypatch.setattr(generateMealPlans.st, "error", Mock())
    monkeypatch.setattr(generateMealPlans.st, "stop", Mock(side_effect=Stopped))
    monkeypatch.setattr(generateMealPlans.time, "sleep", Mock())
    provider = Mock(side_effect=ClientError(429, {"error": {"message": "Quota exceeded"}}))
    monkeypatch.setattr(generateMealPlans, "gemini_ai_api", provider)
    with pytest.raises(Stopped):
        generateMealPlans.generateMealPlan(1)
    provider.assert_called_once()
    assert "quota" in generateMealPlans.st.error.call_args.args[0].lower()
    assert "mealPreferences" not in state


def test_image_quota_does_not_hide_a_saved_menu(monkeypatch):
    import json

    class Session(dict):
        __getattr__ = dict.__getitem__
        __delattr__ = dict.__delitem__

    class Rerun(BaseException):
        pass

    state = Session(mealPreferences={"days": ["Monday"], "total_time": "30 min",
                    "adults": 2, "childs": None, "budget": "Medium", "creativity": 8},
                    preferences={"technique": "pan", "diet": "", "allergy": "",
                                 "dislikes": "", "efforts": "quick"},
                    user_instance=object(), email="test-account@example.test")
    monkeypatch.setattr(generateMealPlans.st, "session_state", state)
    monkeypatch.setattr(generateMealPlans.st, "status", MagicMock())
    monkeypatch.setattr(generateMealPlans.st, "rerun", Mock(side_effect=Rerun))
    monkeypatch.setattr(generateMealPlans.time, "sleep", Mock())
    monkeypatch.setattr(generateMealPlans, "gemini_ai_api", Mock(return_value=json.dumps({"recipes": [{
        "Recipe Title": "Soup", "Ingredients List": [{"Ingredient Name": "Carrot"}]}]})))
    monkeypatch.setattr(generateMealPlans, "databaseRecipesStorage", Mock(return_value={"Soup": 42}))
    monkeypatch.setattr(generateMealPlans, "databaseIngredientsStorage", Mock(return_value=True))
    monkeypatch.setattr(generateMealPlans, "generateImage", Mock(side_effect=ClientError(429, {"error": {"message": "Quota"}})))
    monkeypatch.setattr(generateMealPlans, "fetch_user_info", Mock(return_value=True))
    with pytest.raises(Rerun):
        generateMealPlans.generateMealPlan(1)
    assert "Images are unavailable" in state["image_generation_notice"]
    generateMealPlans.databaseRecipesStorage.assert_called_once()
    generateMealPlans.databaseIngredientsStorage.assert_called_once()
    generateMealPlans.fetch_user_info.assert_called_once()
