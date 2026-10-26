from pathlib import Path
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

import authentication
import generateMealPlans


def test_signed_out_page_starts_without_secrets():
    app = AppTest.from_file(str(Path("mychefApp/main.py").resolve())).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Sign-In :unlock:", "Sign-Up :receipt:"]


def test_email_cookie_cannot_authenticate(monkeypatch):
    import streamlit_cookies_controller
    controller = Mock()
    controller.get.return_value = "victim@example.com"
    monkeypatch.setattr(streamlit_cookies_controller, "CookieController", lambda: controller)
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
    assert not generateMealPlans.generateImage(10, "carrot")
