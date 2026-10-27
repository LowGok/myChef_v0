# MyChef Web App - Version 0

## Run locally

Use Python 3.15.2 (pinned in `.python-version`) and run these commands from the repository root:

```bash
python3 -m pip install 'uv==0.13.5'
uv sync --locked
uv run --locked playwright install chromium
make run
```

Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and fill in
the service configuration locally. The secrets file is ignored by Git.
PostgreSQL URLs use `postgresql+psycopg://` (or `postgresql://` with SQLAlchemy
2.1). Change an explicit `postgresql+psycopg2://` prefix when upgrading an
existing local configuration; Psycopg 3 replaces the old driver.

## Automated tests

`make test` runs offline regression tests and Streamlit page checks. It skips
the live test. To exercise the real browser, database, Gemini and Cloudinary:

```bash
make test-live
```

The live test reads an existing account from the local `[e2e]` secrets section.
It generates one meal and stores its menu, ingredients and image. Use a test
account. To create and reuse a dedicated synthetic account instead:

```bash
MYCHEF_E2E_CREATE_ACCOUNT=1 make test-live
```

Browser screenshots, the model request and raw response, and the test result
are saved under ignored `test-results/`. A locally generated account is retained
under ignored `.test-artifacts/` for subsequent test runs. Failures in the app
fail the test; a skipped live test does not establish that providers work.

For an environment with an unavailable IPv6 route, set `MYCHEF_E2E_IPV4=1` for
the live test. `MYCHEF_E2E_CHROMIUM` can select an existing Chromium executable.
`MYCHEF_RECIPE_MODEL` and `MYCHEF_IMAGE_MODEL` select explicit model overrides.
The result records the recipe model used. When image quota is unavailable,
the menu must still render with a visible warning and placeholder. Set
`MYCHEF_E2E_REQUIRE_IMAGE=1` to require successful image generation and upload too.

The [SQLAlchemy migration draft](docs/specs/sqlalchemy-orm.md) describes the ORM
and transaction changes proposed after the product checks.

## Dependency maintenance

`pyproject.toml` declares runtime dependencies and a separate development group.
`uv.lock` pins the complete dependency tree and package hashes. The required uv
version is pinned in `pyproject.toml`. `uv sync --locked` installs the development
environment; `uv sync --locked --no-dev` installs runtime dependencies only.

Use `uv add PACKAGE` or `uv add --dev PACKAGE` to change dependencies. Use
`uv lock --upgrade` to refresh transitive dependencies. Commit `pyproject.toml`
and `uv.lock` together. `make lock-check` rejects stale locks; `uv run --locked`
also refuses to run with a lock that needs updating.

Renovate proposes dependency and GitHub Actions updates, including weekly uv lock
refreshes, after its GitHub App is installed for this repository. Automatic
merging is disabled. CI verifies the hashes, dependency consistency and offline
product tests, and runs `make audit` against current vulnerability advisories on
PRs and weekly. Live provider tests remain explicit because they write test data
and consume API quota. An advisory audit is current evidence, not a fixed result.

The version represent the crash test of the app. 
The function of this app is to provide a visual interface to the weekly meal generated for the communication.

This app doesn't reflect the final product and complete changes could be applied. 

Follow the documentation below for navigation.

### Documentation:

TBD

### Ownership and copyrights

The applications uses Google Gemini AI API, Google Gemini AI and Google AI Studio.

The prompting is crafted by GKL Development which has solely the full ownership of the app. 

MyChef is a meal planning application service provide by GKL Development, using a freemium model which makes the app lucrative.

