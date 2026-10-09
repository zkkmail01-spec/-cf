# Family Menu Mini Program Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a networked family meal-ordering WeChat Mini Program with a Python FastAPI backend running in WeChat CloudBase Cloud Hosting.

**Architecture:** A native WeChat Mini Program calls a versioned FastAPI API through `wx.cloud.callContainer`. FastAPI owns identity, authorization, business rules and SQLAlchemy persistence; SQLite supports local development and PostgreSQL is the production database. Dish images are uploaded to CloudBase storage by the Mini Program and only their file IDs are persisted.

**Tech Stack:** Native WeChat Mini Program JavaScript/WXML/WXSS, Jest, Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, SQLite/PostgreSQL, pytest, httpx, Docker, WeChat CloudBase Cloud Hosting.

**Spec:** `docs/superpowers/specs/2026-10-09-family-menu-miniapp-design.md`

## Global Constraints

- Use `/api/v1` for every backend route.
- Use UUID primary keys, snake_case database fields, camelCase API JSON and UTC timestamps.
- Production identity comes only from trusted Cloud Hosting headers; local mock identity works only when `APP_ENV=local` and `ALLOW_MOCK_IDENTITY=true`.
- Every family-owned query is scoped by the authenticated member's `family_id`.
- The only roles are `chef` and `member`; chef-only writes are enforced by the API, not only by hidden buttons.
- Meal types are exactly `breakfast`, `lunch` and `dinner`.
- The Mini Program UI uses forest green, warm orange, cream backgrounds, text at least `28rpx` and primary controls at least `88rpx` high.
- Secrets, AppID, environment ID, database URLs and storage credentials never enter committed source files.

## Review Focus

- Forged identity or `familyId` values must not permit cross-family reads or writes; pin in Task 2 authorization tests.
- Two members selecting the same dish concurrently must preserve both selectors without duplicate items; pin in Task 4 transaction tests.
- Expired, revoked, exhausted and repeated invitations must return distinct safe errors; pin in Task 5 invitation tests.
- A deactivated dish must disappear from the catalog while its historical snapshot remains readable; pin in Tasks 3 and 4 tests.
- Network retry must not double-submit a meal mutation; pin with idempotency tests in Task 4 and request-state tests in Task 6.

---

## File Structure

```text
backend/
  app/
    api/deps.py
    api/v1/router.py
    api/v1/endpoints/{session,families,dishes,meals,invitations}.py
    core/{config,errors,identity}.py
    db/{base,session}.py
    models/{family,dish,meal,invitation,shopping}.py
    schemas/{common,family,dish,meal,invitation,shopping}.py
    services/{families,dishes,meals,invitations,shopping}.py
    main.py
  alembic/versions/0001_initial.py
  tests/
  Dockerfile
  alembic.ini
  pyproject.toml
  .env.example
miniprogram/
  app.{js,json,wxss}
  config/env.js
  utils/{api,date,meal-draft}.js
  components/{dish-card,empty-state,meal-tabs}/
  pages/{welcome,home,order,dishes,dish-edit,records,shopping,family,invite}/
  tests/
project.config.json
docker-compose.yml
docs/deployment/cloudbase.md
```

## Task 1: Backend Foundation and Relational Model

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/errors.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/models/family.py`
- Create: `backend/app/models/dish.py`
- Create: `backend/app/models/meal.py`
- Create: `backend/app/models/invitation.py`
- Create: `backend/app/models/shopping.py`
- Create: `backend/app/main.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`
- Create: `.gitignore`
- Test: `backend/tests/test_config.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: the SQL schema and invariants in design spec section 6.
- Produces: `Settings`, `get_session()`, SQLAlchemy `Base`, all ORM models and `create_app() -> FastAPI`.

- [ ] **Step 1: Write failing configuration and model tests**

Test `Settings` rejects a production start without `DATABASE_URL`, rejects mock identity outside local mode, and defaults local database to `sqlite+aiosqlite:///./family_menu.db`. Test the database enforces unique `(family_id, openid)`, `(family_id, meal_date, meal_type)` and `(meal_order_item_id, openid)` constraints.

- [ ] **Step 2: Run tests and verify the foundation is absent**

Run: `cd backend && python -m pytest tests/test_config.py tests/test_models.py -q`
Expected: FAIL because `app.core.config` and ORM models do not exist.

- [ ] **Step 3: Initialize project version control and ignore generated state**

Run `git init` because the current workspace is not yet a repository. Create `.gitignore` covering `.env`, SQLite files, Python/Node caches, test coverage, `node_modules/` and `.superpowers/` visual-companion state.

- [ ] **Step 4: Implement settings, session lifecycle and focused ORM model modules**

Use Python 3.12, SQLAlchemy async sessions, UUID strings portable across SQLite/PostgreSQL, Decimal ingredient quantities, JSON only for immutable meal snapshots and checked-key arrays, and named uniqueness constraints.

- [ ] **Step 5: Create the initial Alembic migration and health endpoint**

`GET /health` returns `{"status":"ok"}` without authentication. The migration creates every table, foreign key, index and uniqueness constraint from the spec.

- [ ] **Step 6: Run migration and tests**

Run: `cd backend && alembic upgrade head && python -m pytest tests/test_config.py tests/test_models.py -q`
Expected: PASS and a local SQLite schema at the configured path.

- [ ] **Step 7: Commit**

```bash
git add .gitignore backend
git commit -m "feat: scaffold FastAPI backend and relational model"
```

## Task 2: Trusted Identity and Family Lifecycle

**Files:**
- Create: `backend/app/core/identity.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/schemas/family.py`
- Create: `backend/app/services/families.py`
- Create: `backend/app/api/v1/endpoints/session.py`
- Create: `backend/app/api/v1/endpoints/families.py`
- Create: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_identity.py`
- Test: `backend/tests/test_families_api.py`

**Interfaces:**
- Consumes: `Settings`, `get_session()`, `Family` and `FamilyMember` from Task 1.
- Produces: `CurrentIdentity(openid, appid)`, `CurrentMember(family_id, openid, role)`, `require_identity`, `require_member`, `require_chef`, `GET /api/v1/session`, `POST /api/v1/families`, `GET /api/v1/families/current`, `PATCH /api/v1/families/current`, `PATCH /api/v1/members/me`, `POST /api/v1/families/current/leave`.

- [ ] **Step 1: Write failing identity and cross-family authorization tests**

Cover trusted `x-wx-openid` extraction, missing identity returning 401, mock `x-mock-openid` accepted only under both local flags, forged request-body `familyId` ignored, non-member returning 403 and member from family A unable to read family B.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `cd backend && python -m pytest tests/test_identity.py tests/test_families_api.py -q`
Expected: FAIL because dependencies and routes do not exist.

- [ ] **Step 3: Implement identity and authorization dependencies**

Define `require_identity`, `require_member` and `require_chef` as FastAPI dependencies. Resolve family scope from `family_members`, never from a client-provided family ID.

- [ ] **Step 4: Implement family lifecycle service and routes**

`POST /families` creates the family and its chef membership in one transaction. `GET/PATCH /families/current` returns or updates the authenticated family. `PATCH /members/me` changes only the authenticated member's nickname and avatar. Leaving marks membership `left`; the sole chef cannot leave until ownership is transferred or the family is removed in a later release.

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_identity.py tests/test_families_api.py -q`
Expected: PASS, including all Review Focus identity cases.

- [ ] **Step 6: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat: add trusted identity and family lifecycle"
```

## Task 3: Category, Dish and Ingredient APIs

**Files:**
- Create: `backend/app/schemas/dish.py`
- Create: `backend/app/services/dishes.py`
- Create: `backend/app/api/v1/endpoints/dishes.py`
- Test: `backend/tests/test_dishes_api.py`

**Interfaces:**
- Consumes: `require_member`, `require_chef`, `DishCategory`, `Dish`, `DishIngredient`.
- Produces: category CRUD at `/api/v1/categories`; catalog CRUD at `/api/v1/dishes`; `DishRead` with `ingredients: IngredientRead[]` and CloudBase `imageFileId`.

- [ ] **Step 1: Write failing catalog tests**

Test category sorting, member catalog search by name or ingredient, chef-only create/update/deactivate, ingredient replacement in one transaction, cross-family category rejection, invalid non-positive quantity rejection, and deactivated dish absence from normal lists while direct historical data remains unaffected.

- [ ] **Step 2: Run catalog tests and confirm failure**

Run: `cd backend && python -m pytest tests/test_dishes_api.py -q`
Expected: FAIL because schemas, service and routes do not exist.

- [ ] **Step 3: Implement Pydantic schemas and dish service**

Define `CategoryCreate`, `CategoryRead`, `IngredientWrite`, `IngredientRead`, `DishCreate`, `DishUpdate` and `DishRead`. Normalize surrounding whitespace but preserve Chinese names and ingredient units.

- [ ] **Step 4: Implement category and dish routes**

List endpoints require membership; all mutations require chef role. `DELETE /dishes/{id}` and `DELETE /categories/{id}` perform soft deactivation and return 204.

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_dishes_api.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app backend/tests/test_dishes_api.py
git commit -m "feat: add family recipe catalog APIs"
```

## Task 4: Meal Selection, History and Shopping Aggregation

**Files:**
- Create: `backend/app/schemas/meal.py`
- Create: `backend/app/schemas/shopping.py`
- Create: `backend/app/services/meals.py`
- Create: `backend/app/services/shopping.py`
- Create: `backend/app/api/v1/endpoints/meals.py`
- Create: `backend/app/models/idempotency.py`
- Create: `backend/alembic/versions/0002_idempotency_records.py`
- Test: `backend/tests/test_meals_api.py`
- Test: `backend/tests/test_shopping_api.py`

**Interfaces:**
- Consumes: authenticated family scope and active dish details from Tasks 2-3.
- Produces: `PUT /api/v1/meals/{date}/{mealType}/selections/{dishId}`, `DELETE` on the same path, `GET /api/v1/meals/{date}`, `GET /api/v1/meals/calendar?month=YYYY-MM`, `POST /api/v1/meals/repeat`, `GET /api/v1/dishes/frequent`, `GET /api/v1/shopping?start=&end=`, `PUT /api/v1/shopping/checks`; every mutation accepts `Idempotency-Key`.

- [ ] **Step 1: Write failing meal and idempotency tests**

Test date and meal-type validation, immutable dish snapshots, two users selecting the same dish yielding one item and two selectors, one user cancelling without removing the other, final selector removal deleting the item, concurrent version conflict retry, and repeated `Idempotency-Key` returning the first result without duplicate writes.

- [ ] **Step 2: Write failing history and shopping tests**

Test month markers, three-meal day grouping, repeat-to-target behavior, inactive dish history readability, frequent-dish counts limited to the authenticated family, identical ingredient name+unit aggregation with Decimal totals, different units remaining separate, and persisted checked keys scoped by family and date range.

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `cd backend && python -m pytest tests/test_meals_api.py tests/test_shopping_api.py -q`
Expected: FAIL because the services and routes do not exist.

- [ ] **Step 4: Implement transactional meal mutation service and its migration**

Use a database transaction, unique constraints and version checks. Add migration `0002_idempotency_records.py` with `(family_id, openid, key)` uniqueness, request fingerprint, status code and JSON response; reject key reuse for a different request with HTTP 409. Do not modify the already-applied initial migration.

- [ ] **Step 5: Implement history, repeat and shopping aggregation**

Return API dates as `YYYY-MM-DD`, Decimal quantities as strings, and meal groups ordered breakfast, lunch, dinner.

- [ ] **Step 6: Run tests**

Run: `cd backend && alembic upgrade head && python -m pytest tests/test_meals_api.py tests/test_shopping_api.py -q`
Expected: PASS, including concurrency and idempotency Review Focus cases.

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat: add collaborative meals history and shopping"
```

## Task 5: Invitations and Member Management

**Files:**
- Create: `backend/app/schemas/invitation.py`
- Create: `backend/app/services/invitations.py`
- Create: `backend/app/api/v1/endpoints/invitations.py`
- Test: `backend/tests/test_invitations_api.py`

**Interfaces:**
- Consumes: identity and family membership dependencies from Task 2.
- Produces: `POST /api/v1/invitations`, `GET /api/v1/invitations/{code}/preview`, `POST /api/v1/invitations/{code}/join`, `DELETE /api/v1/invitations/{id}`, `GET /api/v1/members`, `DELETE /api/v1/members/{memberId}`.

- [ ] **Step 1: Write failing invitation-state and member-management tests**

Assert SHA-256 code storage, chef-only creation/revocation/removal, neutral preview data, atomic use count, exact error codes `INVITE_EXPIRED`, `INVITE_REVOKED`, `INVITE_EXHAUSTED`, `ALREADY_IN_FAMILY`, `ALREADY_JOINED`, and prevention of removing the chef.

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd backend && python -m pytest tests/test_invitations_api.py -q`
Expected: FAIL because invitation schemas, service and routes do not exist.

- [ ] **Step 3: Implement invitation and member services**

Return the plaintext random code only at creation; store only its SHA-256 digest. Join in one transaction that locks the invitation, validates current state, creates membership and increments `used_count`.

- [ ] **Step 4: Implement routes and stable error envelopes**

All errors use `{"error":{"code":"...","message":"..."}}`. Preview reveals family name, avatar and inviter nickname but no member identifiers.

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_invitations_api.py -q`
Expected: PASS for every Review Focus invitation state.

- [ ] **Step 6: Commit**

```bash
git add backend/app backend/tests/test_invitations_api.py
git commit -m "feat: add secure family invitations"
```

## Task 6: Mini Program Shell, API Client and Onboarding

**Files:**
- Create: `project.config.json`
- Create: `miniprogram/app.js`
- Create: `miniprogram/app.json`
- Create: `miniprogram/app.wxss`
- Create: `miniprogram/config/env.js`
- Create: `miniprogram/utils/api.js`
- Create: `miniprogram/utils/meal-draft.js`
- Create: `miniprogram/pages/welcome/*`
- Create: `miniprogram/pages/invite/*`
- Create: `miniprogram/tests/api.test.js`
- Create: `miniprogram/tests/meal-draft.test.js`
- Create: `package.json`

**Interfaces:**
- Consumes: Task 2 and Task 5 HTTP contracts.
- Produces: `api.request({path, method, data, idempotent})`, `api.uploadDishImage(filePath)`, app-level `session`, onboarding routes and persistent unsent meal draft helpers.

- [ ] **Step 1: Write failing API client and draft-state tests**

Test `wx.cloud.callContainer` adds the service header and API prefix, maps backend error envelopes, generates and reuses an idempotency key for one pending mutation, clears it after success, preserves meal draft on network error and never reads AppSecret from configuration.

- [ ] **Step 2: Run tests and confirm failure**

Run: `npm test -- --runInBand miniprogram/tests/api.test.js miniprogram/tests/meal-draft.test.js`
Expected: FAIL because Mini Program utilities do not exist.

- [ ] **Step 3: Implement app configuration and API client**

Use placeholder values `YOUR_CLOUDBASE_ENV_ID` and `YOUR_CLOUDRUN_SERVICE_NAME`. Initialize `wx.cloud` once in `app.js`; use `wx.cloud.uploadFile` for images and `callContainer` for API calls.

- [ ] **Step 4: Implement welcome, create-family and invite-confirmation pages**

Route from `GET /session`: active member to home, no family to welcome, invite scene to preview/confirm. Use explicit loading, empty and retry states.

- [ ] **Step 5: Run tests**

Run: `npm test -- --runInBand miniprogram/tests/api.test.js miniprogram/tests/meal-draft.test.js`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add project.config.json package.json miniprogram
git commit -m "feat: add Mini Program shell and onboarding"
```

## Task 7: Home, Ordering and Recipe Management UI

**Files:**
- Create: `miniprogram/components/dish-card/*`
- Create: `miniprogram/components/empty-state/*`
- Create: `miniprogram/components/meal-tabs/*`
- Create: `miniprogram/pages/home/*`
- Create: `miniprogram/pages/order/*`
- Create: `miniprogram/pages/dishes/*`
- Create: `miniprogram/pages/dish-edit/*`
- Test: `miniprogram/tests/order-page.test.js`
- Test: `miniprogram/tests/dish-edit.test.js`

**Interfaces:**
- Consumes: catalog routes from Task 3, meal mutation routes from Task 4, `api.request` and `meal-draft` from Task 6.
- Produces: the approved B-layout home, three-meal selection UI, searchable category catalog and chef-only dish editor.

- [ ] **Step 1: Write failing ordering and editor state tests**

Test breakfast/lunch/dinner switching, category/search filters, selected count, draft retention after request failure, chef-only edit controls, positive ingredient quantity validation, and successful CloudBase image upload assigning `imageFileId`.

- [ ] **Step 2: Run UI logic tests and confirm failure**

Run: `npm test -- --runInBand miniprogram/tests/order-page.test.js miniprogram/tests/dish-edit.test.js`
Expected: FAIL because components and pages do not exist.

- [ ] **Step 3: Implement shared visual components**

Match the approved forest-green, warm-orange and cream style. Components expose explicit `loading`, `empty`, `error` and `selected` states and use minimum `88rpx` primary controls.

- [ ] **Step 4: Implement home and collaborative ordering pages**

Home shows today's meal summary, four quick actions and frequent dishes. Order page submits per-dish incremental mutations with one idempotency key per user action and refreshes from the server result.

- [ ] **Step 5: Implement catalog and chef dish editor**

Members can search and view; chefs see category management, add/edit/deactivate actions and ingredient rows. Failed image upload preserves all textual form fields.

- [ ] **Step 6: Run tests and lint-style checks**

Run: `npm test -- --runInBand miniprogram/tests/order-page.test.js miniprogram/tests/dish-edit.test.js`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add miniprogram
git commit -m "feat: build home ordering and recipe UI"
```

## Task 8: Records, Shopping and Family UI

**Files:**
- Create: `miniprogram/utils/date.js`
- Create: `miniprogram/pages/records/*`
- Create: `miniprogram/pages/shopping/*`
- Create: `miniprogram/pages/family/*`
- Test: `miniprogram/tests/records-page.test.js`
- Test: `miniprogram/tests/family-page.test.js`

**Interfaces:**
- Consumes: Tasks 4-5 API contracts and Task 6 API client.
- Produces: month calendar/history, repeat-meal dialog, aggregated shopping checklist, family member list and WeChat share invitation flow.

- [ ] **Step 1: Write failing records and family-page state tests**

Test local date formatting without timezone drift, three-meal ordering, month-marker rendering, repeat destination selection, shopping checked-state persistence, member/chef control differences, invitation share path and safe display of all invitation error codes.

- [ ] **Step 2: Run tests and confirm failure**

Run: `npm test -- --runInBand miniprogram/tests/records-page.test.js miniprogram/tests/family-page.test.js`
Expected: FAIL because pages and date helpers do not exist.

- [ ] **Step 3: Implement records and repeat-meal flow**

Use local calendar dates as `YYYY-MM-DD`; never derive them by slicing UTC ISO timestamps. Mark dates returned by the month endpoint and render breakfast, lunch, dinner consistently.

- [ ] **Step 4: Implement shopping and family pages**

Shopping groups by normalized name plus unit. Family page shows roles, hides chef-only actions for members and creates an invitation before returning `onShareAppMessage.path`.

- [ ] **Step 5: Run tests**

Run: `npm test -- --runInBand miniprogram/tests/records-page.test.js miniprogram/tests/family-page.test.js`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add miniprogram
git commit -m "feat: add records shopping and family UI"
```

## Task 9: Container Deployment, Demo Data and End-to-End Verification

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `backend/.env.example`
- Create: `backend/scripts/seed_demo.py`
- Create: `docker-compose.yml`
- Create: `docs/deployment/cloudbase.md`
- Test: `backend/tests/test_end_to_end.py`

**Interfaces:**
- Consumes: all backend routes and Mini Program configuration from Tasks 1-8.
- Produces: reproducible local stack, CloudBase-compatible container, non-secret configuration template, demo family data and deployment/runbook documentation.

- [ ] **Step 1: Write a failing end-to-end API journey**

Test chef creates family, categories and dishes; member joins through invitation; both select dishes for lunch; history shows two selectors; shopping aggregates ingredients; a second family cannot access any first-family resource.

- [ ] **Step 2: Run the end-to-end test and confirm any integration gaps**

Run: `cd backend && python -m pytest tests/test_end_to_end.py -q`
Expected: FAIL until route registration and integrations are complete.

- [ ] **Step 3: Add production container and local compose stack**

Use a non-root container, Python 3.12 slim, health check on `/health`, `uvicorn` bound to port 80, PostgreSQL in Compose, and startup migration as an explicit documented command rather than an unsafe automatic multi-instance migration.

- [ ] **Step 4: Add deterministic demo seed and deployment guide**

Document AppID setup, CloudBase environment creation, Cloud Hosting service deployment, PostgreSQL connection secret, trusted identity headers, storage permissions, Mini Program environment/service placeholders, schema migration, demo seeding and experience-member testing. Never request or print AppSecret.

- [ ] **Step 5: Run the full verification suite**

Run: `cd backend && python -m pytest -q`
Expected: all backend tests PASS.

Run: `npm test -- --runInBand`
Expected: all Mini Program utility/page-state tests PASS.

Run: `docker compose config`
Expected: valid configuration with no embedded secret values.

- [ ] **Step 6: Open the project in WeChat Developer Tools for manual acceptance**

Verify the six approved phone UIs, safe-area layout, font scaling, create/join family flow, three-meal ordering, image upload, records, shopping and sharing against the local or Cloud Hosting API.

- [ ] **Step 7: Commit**

```bash
git add backend docker-compose.yml docs/deployment miniprogram project.config.json package.json
git commit -m "docs: add deployment and end-to-end verification"
```
