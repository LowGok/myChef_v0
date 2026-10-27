# SQLAlchemy ORM Migration Specification

## Overview
Refactor myChef database interactions from raw SQL queries to SQLAlchemy ORM for better type safety, maintainability, and consistency.

## Current Problems
1. **Raw SQL with manual string concatenation** - Using `text()` with manual parameter binding
2. **Inconsistent patterns** - Mix of `conn.query()` and `conn.session.execute()`
3. **No transaction management** - Manual commits scattered everywhere
4. **No model layer** - User data manually extracted from DataFrames
5. **Repetitive boilerplate** - Connection setup, error handling duplicated

## Goals
- Replace all raw SQL with SQLAlchemy ORM models
- Implement clean repository pattern for database operations
- Maintain all existing functionality
- Improve type safety and error handling
- Reduce code duplication

## Architecture

### New Structure
```
mychefApp/
├── database/
│   ├── __init__.py
│   ├── base.py           # Base declarative model, engine setup
│   ├── session.py        # Session management, context managers
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py       # User ORM model
│   │   ├── meal.py       # Meal ORM model
│   │   └── ingredient.py # Ingredient ORM model
│   └── repositories/
│       ├── __init__.py
│       ├── base.py       # Base repository with common operations
│       ├── user_repo.py  # User-specific database operations
│       └── meal_repo.py  # Meal and ingredient operations
└── [existing files...]
```

### Database Schema (Current)

#### users table
- user_id (PK, auto-increment)
- firstname, lastname, username
- sex, birthdate, email (unique)
- password (bcrypt hashed)
- allergens, diet, dislikes (nullable)
- cooking_technique, cooking_efforts (nullable)
- lastmeal (date), haspref (boolean)

#### meals table
- meal_id (PK, unique)
- creator_id (FK to users.user_id)
- creationDate, recipeTitle, yield
- prepTime, cookTime, totalTime
- myChefNotes, equipment, instructions
- allergens, allergensSafetyNote
- isMeatOrFish, recipeimg
- cloudinary_public_id

#### ingredients table
- pk_ingredients (PK, auto-increment)
- recipe_id (FK to meals.meal_id)
- quantity, unit, ingredient_name
- date

## Implementation Plan

### Phase 1: Setup Foundation
**Task 1.1: Create database base infrastructure**
- Create `database/base.py` with declarative base and engine setup
- Use existing Neon PostgreSQL connection from secrets.toml
- Implement connection pooling and retry logic

**Task 1.2: Create session management**
- Create `database/session.py` with context manager pattern
- Implement automatic session cleanup
- Add transaction management (commit/rollback)

### Phase 2: Define ORM Models
**Task 2.1: Create User model**
- Map to existing `users` table schema
- Add type hints for all columns
- Include relationships to meals

**Task 2.2: Create Meal model**
- Map to existing `meals` table schema
- Add relationship to User (creator)
- Add relationship to Ingredients

**Task 2.3: Create Ingredient model**
- Map to existing `ingredients` table schema
- Add relationship to Meal

### Phase 3: Implement Repository Pattern
**Task 3.1: Create base repository**
- Generic CRUD operations (Create, Read, Update, Delete)
- Common query patterns
- Error handling wrapper

**Task 3.2: Create User repository**
- `get_user_by_email(email: str) -> Optional[User]`
- `get_user_by_id(user_id: int) -> Optional[User]`
- `create_user(email, password, firstname, lastname, ...) -> User`
- `update_user_preferences(user_id, preferences) -> bool`
- `update_user_credentials(user_id, credentials) -> bool`
- `verify_credentials(email, password) -> bool`

**Task 3.3: Create Meal repository**
- `get_meals_by_user_and_week(user_id, week_number) -> List[Meal]`
- `create_meal(meal_data) -> Meal`
- `get_ingredients_by_recipe_ids(recipe_ids) -> List[Ingredient]`
- `create_ingredients(ingredients_data) -> List[Ingredient]`
- `update_meal_image(meal_id, image_url, cloudinary_id) -> bool`

### Phase 4: Migrate Existing Functions
**Task 4.1: Migrate authentication.py**
- Replace `fetch_user_info()` with User repository calls
- Replace `credentials()` with User repository
- Replace `registration_protocol()` with User repository
- Keep User class as DTO for session state

**Task 4.2: Migrate db_fetch_functions.py**
- Replace `fetch_user_recipes()` with Meal repository
- Replace `fetch_recipes_ingredients()` with Meal repository
- Maintain same return types for backward compatibility

**Task 4.3: Migrate db_insert_functions.py**
- Replace `databaseRecipesStorage()` with Meal repository
- Replace `databaseIngredientsStorage()` with Meal repository
- Replace `updateCredentials()` with User repository
- Replace `pushPreferences()` with User repository
- Replace `databaseImageStorage()` with Meal repository

### Phase 5: Testing & Validation
**Task 5.1: Test authentication flow**
- Test login with existing users
- Test registration flow
- Test session management

**Task 5.2: Test meal operations**
- Test meal creation and retrieval
- Test ingredient storage
- Test image upload

**Task 5.3: Integration testing**
- Full end-to-end app testing
- Verify all existing functionality works
- Performance comparison

## Technical Decisions

### Connection Management
- **Use SQLAlchemy engine with connection pooling**
- Maintain existing retry logic from `connection.py`
- Support both sync operations (current) and async (future)

### Session State Compatibility
- Keep existing `User` class as DTO
- ORM models map to DTOs for session state
- Minimal changes to UI code

### Migration Strategy
- **No database schema changes** - ORM maps to existing schema
- Gradual migration - can run both systems in parallel during transition
- All functions maintain same signatures initially

## Success Criteria
- [ ] All database operations use SQLAlchemy ORM
- [ ] No raw SQL queries remain in codebase
- [ ] All existing functionality works identically
- [ ] Type hints on all models and repositories
- [ ] Reduced code duplication (boilerplate removed)
- [ ] Better error handling and logging
- [ ] Code is more maintainable and testable

## Risks & Mitigations
- **Risk**: Breaking existing functionality
  - **Mitigation**: Keep same function signatures, thorough testing
- **Risk**: Performance regression
  - **Mitigation**: Use connection pooling, measure before/after
- **Risk**: Complex queries harder in ORM
  - **Mitigation**: Can still use raw SQL for complex cases, but wrapped in repository

## Timeline Estimate
- Phase 1: 1-2 hours
- Phase 2: 2-3 hours
- Phase 3: 2-3 hours
- Phase 4: 3-4 hours
- Phase 5: 2-3 hours
- **Total: 10-15 hours**

## Dependencies
- SQLAlchemy 2.0+ (already installed)
- psycopg2-binary (already installed)
- No new external dependencies required
