---
status: draft
status_description: "Schema inspected; awaiting independent spec review and owner acceptance."
issue: null
goal: "Users can save and retrieve complete meal plans through SQLAlchemy ORM without losing existing data."
covers:
  - mychefApp/
  - migrations/
  - alembic.ini
  - requirements.txt
  - tests/
  - pytest.ini
  - Makefile
---

# SQLAlchemy ORM and reliable meal persistence

## Context

The application already depends on SQLAlchemy 2.0.41, but uses handwritten SQL
through Streamlit's SQLConnection. There are no mapped models or migrations
(`requirements.txt`; `mychefApp/db_insert_functions.py:13`;
`git ls-files '*alembic*' '*migration*'` returned no paths at `c0d5775`).

The database schema was inspected through SQLAlchemy Inspector on 2026-10-26
using the supplied connection, without fetching user records. It has three
tables with useful integrity constraints:

| Table | Key and relationships | Other constraints |
| --- | --- | --- |
| users | Integer primary key with users_user_id_seq | Required names, email, password and username; unique email and username |
| meals | BIGINT primary key without a default; creator_id references users.user_id with ON DELETE CASCADE | Required creator_id, creationdate and recipetitle |
| ingredients | Integer primary key with ingredients_pk_ingredients_seq; recipe_id references meals.meal_id with ON DELETE CASCADE | Required recipe_id and ingredient_name; NUMERIC quantity |

The only secondary indexes reported were the unique email and username indexes.
Preferences, equipment, instructions and allergens are TEXT; ismeatorfish and
haspref are BOOLEAN. They must not be mapped as PostgreSQL ARRAY or JSONB without
a separate migration. Existing user and ingredient sequences can remain.

The structure is sufficient for the first ORM migration. At the imported baseline, recipe IDs concatenated a date, recipe position and
user ID (`git show c0d5775:mychefApp/db_insert_functions.py`, lines 49 to 58),
causing collisions when the same user generated again that day. The stabilization
branch uses random positive BIGINT values as an interim measure; the ORM
migration will give allocation to the database. Meals and users.lastmeal commit before ingredients
are inserted (`mychefApp/db_insert_functions.py:79` and `:135`). A failure can
leave an apparently finished plan without ingredients.

## Scope

Map the existing users, meals and ingredients tables, move persistence behind
small repositories and services, and introduce reviewed Alembic migrations.
Preserve existing rows, primary keys, relationships and bcrypt hashes. Keep the
Streamlit interface and provider integrations working during the transition.

A larger schema redesign, meal_plans table, normalized dietary preferences,
JSONB conversion, authentication-provider replacement and new favorites or
photo-to-recipe features are outside this change.

## Design

### Models match the inspected schema

Add typed SQLAlchemy declarative models in `mychefApp/db/models.py` for User,
Meal and Ingredient. Use the actual lowercase column names and types. Python
attribute names may differ through explicit column mappings; map SQL column
yield to a suitable Python name. Preserve nullable values and existing foreign
key deletion behavior. Include the allergenssafetynote column.

The User model replaces the data-only authentication.User object at the
persistence boundary. Session state receives detached data objects with the
existing presentation attributes; mapped objects and sessions are never stored
in Streamlit state or cached globally. This keeps lazy loads out of page rendering.
The current presentation shape is defined in `mychefApp/authentication.py:12`.

### Engine and transaction lifetime

`mychefApp/db/session.py` owns one cached engine and session factory. Reuse the
configured Neon URL and PostgreSQL driver, retain TLS settings and connection
pre-ping, and keep bounded pool settings. Each service call owns a fresh session
and a transaction context which commits once, rolls back on failure and closes.
Sessions are not shared between users or Streamlit reruns. This follows the
SQLAlchemy session lifecycle guidance linked in Sources.

Generate and validate the AI response before opening a write transaction.
`save_menu(user_id, validated_recipes)` creates every Meal and Ingredient and
updates users.lastmeal in one transaction. Flush to obtain IDs; never commit in
repository helpers. Return ordered recipe results with IDs rather than a map
keyed only by recipe title, so duplicate titles cannot attach ingredients to the
wrong recipe. The present title map is at
`mychefApp/db_insert_functions.py:76` and `:126`.

Image generation and upload run after that transaction closes. Attach image
metadata in a separate short, owner-scoped transaction. An image failure leaves
the saved menu available with its placeholder and can be retried independently.
No database connection stays checked out during a model or Cloudinary call.

### Queries and failure handling

`mychefApp/db/repositories.py` uses ORM expressions for account lookup, profile
updates, preferences, meals, ingredients and image updates. Every meal or
ingredient query takes the authenticated user ID and applies ownership filtering.
Weekly queries use a half-open Monday-to-Monday date range, including weeks that
cross New Year. Presentation adapters preserve existing recipe and ingredient
return shapes while callers migrate.

The service boundary distinguishes validation, missing records, conflicts and
database availability failures. It does not print SQL parameters or credentials.
Retry read-only disconnected operations within a bound. Never replay an
arbitrary write after a lost commit acknowledgement. Pool pre-ping checks
connections before checkout; it cannot establish whether an interrupted commit
succeeded. Write idempotency beyond independent image updates requires a
separate accepted design.

### Migrations preserve current data

Capture and review the inspected schema as the baseline migration. On an
existing database, verify table definitions before stamping that baseline;
never treat stamping as verification. The same migration history must create
the schema in an empty disposable PostgreSQL database.

Allocate new meals with a PostgreSQL BIGINT sequence/default. Set its next value
above the largest existing meal_id while coordinating concurrent writers;
retain all current IDs and ingredient references. Add indexes for
meals(creator_id, creationdate) and ingredients(recipe_id), after checking for
equivalent existing indexes. Keep the current tables and their TEXT fields.

Manually review Alembic autogenerate output. Do not run create_all or apply
migrations during app startup. Rehearse upgrade and rollback on a disposable
copy, compare keys, counts and relationships, and back up the real database
before any approved deployment. This draft authorizes no schema changes.

## Acceptance Criteria

- [ ] AC-01: Existing accounts, bcrypt hashes, meals and ingredients remain usable after the migration without changes to their stored IDs or relationships.
- [ ] AC-02: A new database can be initialized using the same Alembic history used to adopt an existing database.
- [ ] AC-03: Saving a menu either persists all meals, ingredients and the updated lastmeal date together, or leaves all three unchanged.
- [ ] AC-04: Two menu generations for one user on the same day receive distinct meal IDs, and duplicate recipe titles keep their own ingredients.
- [ ] AC-05: Users can retrieve only their own meals and ingredients, including the correct results for a week spanning New Year.
- [ ] AC-06: Profile and preference changes survive a new login, and image metadata updates affect only meals owned by that user.
- [ ] AC-07: Database failures close sessions without leaking credentials, replaying ambiguous writes, or reporting an unsuccessful save as successful.
- [ ] AC-08: The automated browser flow signs in, generates a real menu, opens recipe instructions and verifies its persisted ingredients; a provider failure remains inspectable through local request and response artifacts.

## Test Plan

| Criterion | Proof |
| --- | --- |
| AC-01 | Restore a representative database copy, run adoption checks and migrations, and compare row counts, keys, foreign key edges and bcrypt verification before and after. Run account, meal and ingredient reads through the migrated adapters. |
| AC-02 | Run alembic upgrade head against an empty disposable PostgreSQL database and against an inspected baseline copy; compare schemas and run alembic check. |
| AC-03 | PostgreSQL transaction tests inject a failure after a meal insert, during ingredient insertion and before lastmeal update; no partial writes remain. A successful menu persists all rows once. |
| AC-04 | Persist two menus for one account on one date, including duplicate titles within a menu; assert unique IDs and exact ingredient ownership. |
| AC-05 | Seed two accounts, overlapping recipe-ID requests and adjacent years; exercise repository queries and verify isolation and Monday-to-Monday boundaries. |
| AC-06 | Exercise profile, preferences and image updates through the app and a second login; assert another user's rows and zero-row updates cannot be reported as saved. |
| AC-07 | Inject execute, flush and commit disconnects, plus validation failures; assert rollback and close, bounded reads, one write attempt and logs without SQL parameters. |
| AC-08 | Extend tests/e2e/test_live_menu.py to verify stored rows against the captured provider response; run with an explicitly configured test account and live services, retaining ignored artifacts on failure. |

## Tasks

- [ ] T1 `tests/integration/test_schema_adoption.py` - reproduce current schema and data compatibility checks in disposable PostgreSQL; establish the pre-migration fixture (AC-01, AC-02).
- [ ] T2 `mychefApp/db/models.py`, `migrations/`, `alembic.ini` - map verified types and add baseline, ID allocation and indexes; T1 passes for empty and adopted databases (AC-01, AC-02, AC-04).
- [ ] T3 `tests/integration/test_menu_transactions.py` - demonstrate partial-write and repeated-generation failures with fault injection (AC-03, AC-04, AC-07).
- [ ] T4 `mychefApp/db/session.py`, `mychefApp/db/services.py` - implement short transactions and ordered menu results; T3 passes, with no provider calls inside a transaction (AC-03, AC-04, AC-07).
- [ ] T5 `mychefApp/db/repositories.py`, `mychefApp/authentication.py`, `mychefApp/db_fetch_functions.py`, `mychefApp/db_insert_functions.py` - migrate all existing callers through owner-scoped adapters; account, date-boundary and update tests pass (AC-01, AC-05, AC-06).
- [ ] T6 `mychefApp/generateMealPlans.py`, `tests/e2e/test_live_menu.py` - wire the atomic menu service and separate image updates; live menu verification compares captured output with stored rows and rendered instructions (AC-03, AC-06, AC-08).

## Open Questions

None. The owner's preference to retain a sound schema is satisfied by the
inspected constraints and a data-preserving ORM migration. Production migration
timing remains a deployment decision after review and acceptance.

## Review Log

| Date | Review | Kind | Commit | Model | Isolation | Outcome |
| --- | --- | --- | --- | --- | --- | --- |

Independent spec review and owner acceptance are pending. No ORM implementation
or schema migration has been performed.

## Sources

- [SQLAlchemy session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html): session scope, transaction contexts and rollback.
- [SQLAlchemy pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html): pre-ping and disconnect handling boundaries.
- [Alembic autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html): generated migrations require review against real metadata.
- [Pinned feature document standard](https://github.com/vhco-pro/docs/blob/e4d58d2cd69bd42f1efacf91dfdd3f01a24e134a/conventions/feature-documents.md): draft format and acceptance gates.
- SQLAlchemy Inspector against the supplied database on 2026-10-26: column types, defaults, primary keys, foreign keys, unique constraints and indexes for users, meals and ingredients.
