"""Opt-in browser test using the supplied account and real external services."""

import json
import os
from pathlib import Path
import re
import socket
import secrets
import subprocess
import sys
import time
import tomllib
from uuid import uuid4
from datetime import datetime
from urllib.request import urlopen

import pytest

pytestmark = [pytest.mark.live, pytest.mark.skipif(
    os.environ.get("MYCHEF_RUN_LIVE_E2E") != "1",
    reason="Set MYCHEF_RUN_LIVE_E2E=1 to use the configured account and live APIs",
)]
ROOT = Path(__file__).resolve().parents[2]


def database_connect_args(settings):
    args = {"connect_timeout": 10}
    if os.environ.get("MYCHEF_E2E_IPV4") == "1":
        from sqlalchemy.engine import make_url
        url = make_url(settings["connections"]["neon"]["url"])
        args["hostaddr"] = socket.getaddrinfo(url.host, url.port or 5432,
            family=socket.AF_INET, type=socket.SOCK_STREAM)[0][4][0]
    return args


def wait_for_outcome(page, success, timeout=240):
    """Fail on visible product errors instead of hiding them behind a long timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        exceptions = page.locator('[data-testid="stException"]')
        errors = page.locator('[data-testid="stAlertContentError"]')
        failed_status = page.get_by_text(re.compile(r"^Failed to (generate|save|upload)"))
        if exceptions.count() or errors.count():
            pytest.fail("Product error: " + " ".join(exceptions.all_text_contents() + errors.all_text_contents()))
        if failed_status.count() and failed_status.first.is_visible():
            pytest.fail("Product error: " + failed_status.first.inner_text())
        if success.count() and success.first.is_visible():
            return
        page.wait_for_timeout(250)
    pytest.fail("Product did not reach the expected state before the timeout; visible headings: "
                + repr(page.get_by_role("heading").all_text_contents())
                + "; alerts: " + repr(page.get_by_test_id("stAlert").all_text_contents()))


def wait_for_generation(page, artifacts, started):
    """Wait for this request, so a previous menu cannot make the new test pass."""
    deadline = time.monotonic() + 300
    events = artifacts / "generations/events.jsonl"
    while time.monotonic() < deadline:
        if events.exists():
            for line in events.read_text().splitlines():
                event = json.loads(line)
                if event["stage"] == "menu_complete" and datetime.fromisoformat(event["time"]).timestamp() >= started:
                    return
        for path in (artifacts / "generations").glob("*/error.json"):
            if path.stat().st_mtime >= started:
                pytest.fail("Recipe provider failed: " + path.read_text())
        errors = page.locator('[data-testid="stException"], [data-testid="stAlertContentError"]')
        if errors.count():
            pytest.fail("Product error: " + " ".join(errors.all_text_contents()))
        page.wait_for_timeout(250)
    pytest.fail("This generation did not complete; inspect generations/events.jsonl")


@pytest.fixture
def live_app(tmp_path):
    artifacts = Path(os.environ.get("MYCHEF_E2E_ARTIFACTS", ROOT / "test-results/live-menu"))
    artifacts.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = {**os.environ, "MYCHEF_TRACE_DIR": str(artifacts / "generations"),
                   "PYTHONUNBUFFERED": "1"}
    settings = tomllib.loads((ROOT / ".streamlit/secrets.toml").read_text())
    connect_args = database_connect_args(settings)
    if "hostaddr" in connect_args:
        environment["PGHOSTADDR"] = connect_args["hostaddr"]
    log = (artifacts / "server.log").open("w")
    process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "mychefApp/main.py",
        "--server.address=127.0.0.1", f"--server.port={port}",
        "--server.headless=true", "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ], cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            if process.poll() is not None:
                pytest.fail("Streamlit exited during startup; see the local server log")
            try:
                with urlopen(url + "/_stcore/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("Streamlit did not start")
        yield url, artifacts
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log.close()


def test_live_menu_generation(live_app):
    from playwright.sync_api import sync_playwright, expect

    settings = tomllib.loads((ROOT / ".streamlit/secrets.toml").read_text())
    account = settings.get("e2e", {})
    create_account = os.environ.get("MYCHEF_E2E_CREATE_ACCOUNT") == "1"
    if create_account:
        account_path = ROOT / ".test-artifacts/e2e-account.json"
        account_path.parent.mkdir(exist_ok=True)
        if account_path.exists():
            account = json.loads(account_path.read_text())
        else:
            identifier = uuid4().hex[:12]
            account = {"email": f"mychef-e2e-{identifier}@example.test",
                       "password": secrets.token_urlsafe(24), "username": f"e2e_{identifier}"}
            account_path.write_text(json.dumps(account))
            account_path.chmod(0o600)
        # Reuse this identity if an earlier run registered successfully but failed later.
        from sqlalchemy import create_engine, text
        engine = create_engine(settings["connections"]["neon"]["url"],
                               connect_args=database_connect_args(settings))
        try:
            with engine.connect() as conn:
                exists = conn.execute(text("SELECT EXISTS (SELECT 1 FROM users WHERE email=:email)"),
                                      {"email": account["email"]}).scalar_one()
            create_account = not exists
        finally:
            engine.dispose()
    assert account.get("email") and account.get("password"), "Configure [e2e] email and password in local secrets"
    url, artifacts = live_app
    with sync_playwright() as playwright:
        executable = os.environ.get("MYCHEF_E2E_CHROMIUM")
        browser = playwright.chromium.launch(executable_path=executable)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        page.set_default_timeout(30_000)
        stages = []
        def stage(name):
            stages.append(name)
            (artifacts / "result.json").write_text(json.dumps({"result": "running", "stages": stages}, indent=2))
            print("E2E:", name, flush=True)
        try:
            page.goto(url)
            if create_account:
                page.get_by_role("tab", name=re.compile("Sign-Up")).click()
                signup = page.get_by_role("tabpanel", name=re.compile("Sign-Up"))
                signup.get_by_role("textbox", name="Enter your email:").fill(account["email"])
                signup.get_by_role("textbox", name="Enter your password:", exact=True).fill(account["password"])
                signup.get_by_role("textbox", name="Confirm your password:").fill(account["password"])
                signup.get_by_role("button", name="Register now!").click()
                registration = page.get_by_role("dialog")
                registration.get_by_role("textbox", name="What is your firstname?").fill("Automated")
                registration.get_by_role("textbox", name="What is your lastname?").fill("Menu Test")
                registration.get_by_role("textbox", name="Enter a username:").fill(account["username"])
                birthdate = registration.get_by_test_id("stDateInput").locator("input")
                birthdate.fill("1990/01/01")
                birthdate.press("Enter")
                registration.get_by_text("Thank you for signing up!", exact=False).click()
                registration.get_by_role("button", name="Submit", exact=True).click()
                wait_for_outcome(page, page.get_by_role("button", name="Logout", exact=True), timeout=90)
                stage("registration")
                page.get_by_role("button", name="Logout", exact=True).click()
            panel = page.get_by_role("tabpanel", name=re.compile("Sign-In"))
            panel.get_by_role("textbox", name="Enter your email:").fill(account["email"])
            panel.get_by_role("textbox", name="Enter your password:", exact=True).fill(account["password"])
            panel.get_by_role("button", name="Login", exact=True).click()
            wait_for_outcome(page, page.get_by_role("button", name="Logout", exact=True), timeout=90)
            stage("login")
            wait_for_outcome(page, page.get_by_role("heading", name=re.compile("Hello ")), timeout=60)

            # A current plan is preserved. Use the explicit generation button for another plan.
            preference_button = page.get_by_role("button", name="Enter the Preferences Form")
            if preference_button.count():
                preference_button.click()
                page.get_by_role("button", name="Submit My Preferences").click()
                # Saving onboarding preferences opens the meal-preference dialog.
                wait_for_outcome(page, page.get_by_role("dialog").filter(has_text="Number of meals:"), timeout=60)

            generate = page.get_by_role("button", name="Plan your weekly meals!", exact=False)
            if page.get_by_role("dialog").filter(has_text="Number of meals:").count():
                pass
            elif generate.count():
                generate.click()
            else:
                page.get_by_role("button", name="Generate another meal plan").click()
            dialog = page.get_by_role("dialog")
            expect(dialog).to_be_visible()
            dialog.get_by_role("button", name="Monday", exact=True).click()
            dialog.get_by_text("30 min", exact=True).click()
            # Adults and children have separate pill groups.
            dialog.get_by_text("2", exact=True).first.click()
            dialog.get_by_text("Medium", exact=True).click()
            generation_started = time.time()
            dialog.get_by_role("button", name="Generate Now!", exact=True).click()
            stage("generation submitted")
            wait_for_generation(page, artifacts, generation_started)
            wait_for_outcome(page, page.get_by_role("heading", name="Your Weekly Meals!"), timeout=300)
            stage("meal cards")
            traces = sorted((p for p in (artifacts / "generations").glob("*/response.txt")
                             if p.stat().st_mtime >= generation_started), key=lambda p: p.stat().st_mtime)
            assert traces, "No real Gemini response was captured"
            recipes = json.loads(traces[-1].read_text())["recipes"]
            assert len(recipes) == 1
            assert recipes[0]["Ingredients List"] and recipes[0]["Instructions"]
            events = [json.loads(line) for line in (artifacts / "generations/events.jsonl").read_text().splitlines()]
            saved = [event for event in events if event["stage"] == "recipes_saved"
                     and datetime.fromisoformat(event["time"]).timestamp() >= generation_started]
            meal_id = saved[-1]["meal_ids"][0]
            page.locator(f".st-key-{meal_id}").get_by_role("button", name="Cook Now!").click()
            wait_for_outcome(page, page.get_by_role("tab", name="Instructions", exact=True))
            page.get_by_role("tab", name="Instructions", exact=True).click()
            expect(page.get_by_text(recipes[0]["Instructions"][0], exact=False)).to_be_visible()
            stage("recipe instructions")
            page.screenshot(path=str(artifacts / "recipe.png"), full_page=True)
            request = json.loads((traces[-1].parent / "request.json").read_text())
            assert "Number of recipes: 1" in request["prompt"]
            from sqlalchemy import create_engine, text
            engine = create_engine(settings["connections"]["neon"]["url"],
                                   connect_args=database_connect_args(settings))
            try:
                with engine.connect() as conn:
                    meals = conn.execute(text("""
                        SELECT m.meal_id, m.recipeimg FROM meals m
                        JOIN users u ON u.user_id=m.creator_id
                        WHERE u.email=:email AND m.recipetitle=:title AND m.meal_id=:meal_id
                        ORDER BY m.creationdate DESC
                    """), {"email": account["email"], "title": recipes[0]["Recipe Title"], "meal_id": meal_id}).mappings().all()
                    assert meals, "Generated meal was not persisted for the test account"
                    expected_names = {item["Ingredient Name"] for item in recipes[0]["Ingredients List"]}
                    matching = []
                    for meal in meals:
                        stored = set(conn.execute(text("SELECT ingredient_name FROM ingredients WHERE recipe_id=:id"),
                                                  {"id": meal["meal_id"]}).scalars())
                        if stored == expected_names:
                            matching.append(dict(meal))
                    assert matching, "Ingredients do not match the generated menu"
                    has_image = any(meal["recipeimg"] for meal in matching)
                    if not has_image:
                        expect(page.get_by_text("Your meals and ingredients are saved. Images are unavailable; placeholders are shown.")).to_be_visible()
                    if os.environ.get("MYCHEF_E2E_REQUIRE_IMAGE") == "1":
                        assert has_image, "Image integration failed; inspect the provider stage events"
            finally:
                engine.dispose()
            stage("database persistence")
            (artifacts / "result.json").write_text(json.dumps({
                "result": "passed", "stages": stages, "recipe_count": len(recipes),
                "image_status": "generated" if has_image else "placeholder",
                "model": request["model"],
                "generation": str(traces[-1].parent.relative_to(artifacts)),
            }, indent=2))
        except BaseException:
            # Do not capture the login form, which contains the account password.
            page.screenshot(path=str(artifacts / "failure.png"), full_page=True,
                            mask=[page.locator('input[type="password"]')])
            (artifacts / "result.json").write_text(json.dumps({"result": "failed", "stages": stages}, indent=2))
            raise
        finally:
            context.close()
            browser.close()
