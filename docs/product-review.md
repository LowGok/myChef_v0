# Product review and live test evidence

## Imported history

The feature branch starts at LowGok/myChef_v0 master, commit
`c0d5775909572ce78d15152ce3ce2ada6ea01c3e`. Both fork commits, `912bb47`
and `c0d5775`, remain in its history. No changes were copied from an unrelated
branch and the default branch was not rewritten.

All five original development branches were already ancestors of the fork.
`git rev-list --left-right --count origin/master...upstream/<branch>` returned
98/0 for cookies_protocol, 67/0 for development, 53/0 for development.v2,
51/0 for development.v3 and 84/0 for geminiAPIdev. There was no unmerged
development commit to recover from those refs.

## Review of every source change in the fork

| File | Assessment | Verification and correction |
| --- | --- | --- |
| authentication.py | Removing an unused pandas import is safe. | Login is covered by the browser test. The stabilization also removes duplicated SELECT column labels and the unsigned email-cookie login path. |
| recipeGenerator.py | The selected gemini-3.8-flash model exists, but availability must be checked by execution. | The original key returned 429 daily-quota errors; replacement-key menu calls returned 503 and 504. The complete menu test passed with an explicit gemini-3.1-flash-lite override. The captured request records that model. |
| connection.py | Pre-ping, recycling and keepalives are useful; the retry wrapper was unsafe. | Regression tests reproduced three write attempts after an ambiguous disconnect, swallowed ValueError and SQL-parameter output. Writes now get one attempt, programming errors propagate, only read-only work retries, and errors omit parameters. Reset targets the same configured connection. |
| db_insert_functions.py | Resolving the user at call time fixes import-time session access, but the new blanket retries and successful zero-row updates were unsafe. | Tests cover two current users, owner-scoped image updates, missing users, invalid payloads and repeated generations. Updates check affected rows; storage requires an explicit user. Random positive BIGINT IDs replace repeatable date-based IDs pending the ORM sequence migration. |
| imageGenerator.py | The new requests and quote imports were unused. The existing Imagen provider call is now obsolete. | Removed unused imports. Google's current Imagen page states that Imagen is shut down. Image generation now uses Gemini's content API and extracts inline image bytes. |

The remaining changes in those commits were compiled `.pyc` files. They are
generated artifacts rather than reviewable source and are removed from the Git
index; source and test execution generate their own local bytecode.

## Product defects addressed during testing

- An editable browser email cookie could establish an authenticated session.
  New sessions now require credentials. The cookie component is removed from
  the login flow; real browser form submission and login are exercised.
- Ingredient retrieval accepted a user ID without filtering ownership. It now
  joins meals and filters creator_id; the two-user database check passes.
- Weekly retrieval matched the week number across all years. It now uses a
  Monday-to-Monday date range and has a New Year regression check.
- Profile updates and image saves reported success when no row matched.
  Affected-row checks and the image orchestration failure check now prevent that.
- Updating dietary preferences did not update the prompt's session values.
  Successful updates now refresh those values before menu generation.
- Same-day regeneration reused deterministic IDs. It now allocates positive
  random BIGINTs and offers an explicit additional-menu action. A generation
  request is consumed once so a rerun cannot silently replay a paid request.
- Image prompting used the database ID as the dish name. It now uses the
  generated recipe title.
- An image-quota failure stopped the page after meals and ingredients were
  saved. The app now displays the saved menu with a warning and placeholder.
- Weekly results stayed cached after generating another menu. Successful writes
  now clear those caches; the browser test opens the newly returned recipe.
- The requirements file included an unused MySQL client which failed to build
  without system MySQL headers. PostgreSQL remains the configured backend;
  requirements are now UTF-8 and omit that unused client.

## Verification

The offline suite uses Streamlit's real SQLConnection over disposable SQLite
fixtures, Streamlit AppTest for page checks, and provider fakes for request
construction and failure handling. These checks do not prove PostgreSQL or
provider integration. `make test-live` is the separate live browser check.

The live test starts a localhost-only server, registers a dedicated synthetic
account when explicitly requested, reuses that identity across reruns, logs in,
submits onboarding and meal options, requests one recipe, opens its instructions
and compares persisted ingredients with the captured response. It records image
status separately and requires a visible warning when placeholders are used.
`MYCHEF_E2E_REQUIRE_IMAGE=1` additionally requires an image to be saved.
It saves local artifacts under ignored `test-results/`. Provider calls are real.

This environment's database DNS returns unreachable IPv6 addresses before
IPv4. `MYCHEF_E2E_IPV4=1` resolves an IPv4 address for the test while preserving
the configured hostname and TLS options. This is a local test setting.

Verification on 2026-10-27:

- Offline regression suite: 25 passed. These include database isolation,
  ambiguous-write retry handling, page startup, provider errors and image failure
  recovery.
- Real browser menu test: 1 passed in 29.72 seconds against committed code `63ea063`. It used the replacement key,
  `gemini-3.1-flash-lite`, the same registered synthetic account and the IPv4
  setting. Login, new recipe generation, meal cards, the returned instruction
  text and matching persisted ingredients passed.
- The resulting recipe was "Pan-Seared European Seabass with Roasted Autumn Vegetables", with six ingredients.
  The request, raw JSON response and screenshot are retained locally. The result
  is `test-results/live-menu/result.json`.
- Image provider execution returned HTTP 429 with a zero free-tier quota for
  `gemini-3.1-flash-image`. Placeholder recovery passed. Actual image generation
  and Cloudinary upload are not verified by this passing menu test.
- Dependency consistency and Python compilation passed. The ORM draft passed
  `vh-adlc lint` using the repository pin.

The successful live run used `MYCHEF_E2E_CREATE_ACCOUNT=1`,
`MYCHEF_E2E_IPV4=1` and the installed Chromium selected through
`MYCHEF_E2E_CHROMIUM`. The recipe model came from the local secrets setting,
`gemini_recipe_model = "gemini-3.1-flash-lite"`. A generated account is
reused after the first registration; additional runs do not create new accounts.
The local secrets file now selects the verified recipe model for normal app
startup too; the API key and account credentials remain ignored by Git.

## Remaining work

The [ORM draft](specs/sqlalchemy-orm.md) covers atomic meal and ingredient
persistence, database-generated IDs, ORM models and reviewed migrations.
Current menu and ingredient writes still use separate transactions. The existing
title-keyed ID map also needs to support duplicate titles reliably.

The shopping-list and image-to-recipe pages are placeholders. The live test
checks ingredients within the recipe view and database; it does not establish
that those unfinished pages work. Allergy output remains model-generated and
needs its own product validation before any stronger safety claim.

## Sources

- [Google model catalogue](https://ai.google.dev/gemini-api/docs/models): recipe model naming.
- [Imagen shutdown and migration](https://ai.google.dev/gemini-api/docs/imagen): the image endpoint must be replaced.
- [Gemini image generation](https://ai.google.dev/gemini-api/docs/image-generation): supported native image models and image response parts.
- [Playwright Python](https://playwright.dev/python/docs/intro): browser test execution.
- The baseline Git diff, executed regression checks, the supplied key's model catalogue, and live browser artifacts described above.
