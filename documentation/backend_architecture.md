# Delivery & Dispatch Tracker — Backend Architecture

## 1. System overview

The backend is a REST API for customer delivery requests, dispatcher-assisted
rider assignment, rider delivery updates, location reporting, and proof of
delivery. FastAPI exposes the HTTP API and its OpenAPI documentation. SQLAlchemy
models define the relational schema, and PostgreSQL stores the operational
records.

### Technology choices

| Concern | Technology | Reason and trade-off |
|---|---|---|
| HTTP API | FastAPI | Type-driven route definitions, dependency injection, request validation, and generated OpenAPI docs. |
| ORM | SQLAlchemy 2.x declarative mapping | Typed models and relationships keep database structure explicit and support PostgreSQL constraints and transactions. |
| API schemas | Pydantic v2 | Validates and serializes request/response data independently of ORM persistence. |
| Database | PostgreSQL through psycopg | Relational integrity, transactions, native enums, and partial indexes suit this workflow. |
| Password/code hashing | Argon2 via `pwdlib` | Adaptive password hashing; plaintext account passwords and delivery codes are not stored in their respective hash fields. |
| Authentication | Signed JWT bearer tokens (HS256) | Stateless request authentication with a configured expiration. Active account status and role are still checked against the database for protected requests. |

### Request and persistence flow

1. A route receives a Pydantic request model and authenticated-user dependency.
2. The dependency validates the bearer token and loads the active user.
3. The route/service applies role, ownership, assignment, and lifecycle rules.
4. SQLAlchemy persists related changes in one database session and commits them
   together where the route changes an order and its history or assignment.
5. A Pydantic response model shapes the API response.

The API is REST-based. Location updates are currently ordinary authenticated
HTTP requests; Socket.IO/WebSocket broadcasting and an external SMS/email
provider are not implemented.

## 2. Project layout and responsibilities

```text
backend/
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 97efcca21231_initial_database_schema.py
│       ├── 4e31c9bd72a1_add_user_verification_approval.py
│       ├── 6fa3ac25c821_scope_locations_and_rider_capacity.py
│       └── 83c1e0a42f69_redact_legacy_delivery_codes.py
├── app/
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── database/
│   │   ├── base.py
│   │   └── connection.py
│   ├── dependencies/
│   │   └── authentication.py
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── tests/
│   ├── test_delivery_flow.py
│   ├── test_order_lifecycle.py
│   └── test_security.py
├── .env
├── .env.example
├── alembic.ini
└── requirements.txt
```

| Directory/file | Responsibility |
|---|---|
| `app/core/config.py` | Loads and validates settings from environment and `.env`; requires a JWT secret, restricts algorithm to HS256, bounds token lifetime, and configures trusted CORS origins. |
| `app/core/security.py` | Argon2 password/code hashing and verification helpers. |
| `app/database/base.py` | SQLAlchemy declarative `Base` shared by all ORM models. |
| `app/database/connection.py` | PostgreSQL engine, `SessionLocal`, and FastAPI `get_db` session dependency. |
| `app/dependencies/authentication.py` | JWT creation/validation, active-user lookup, and role dependency factory. |
| `app/models/` | ORM entities, enum types, foreign keys, relationships, indexes, and database constraints. `models/__init__.py` imports all entities so Alembic sees their metadata. |
| `app/schemas/` | Pydantic input/output schemas, validation limits, and response serialization. |
| `app/routers/` | HTTP endpoints grouped by authentication, users, orders, dispatch, rider, tracking, and notifications. |
| `app/services/order_service.py` | Shared allowed-transition map and status-transition/history recording helper. |
| `app/services/tracking_service.py` | Tracking service module; current HTTP tracking reads are implemented in `routers/tracking.py`. |
| `app/main.py` | Creates the FastAPI app, applies the configured CORS allowlist, includes versioned routers, and defines `/health`. |
| `alembic/env.py` | Loads application settings and model metadata for migration generation/application. |
| `alembic/versions/` | Versioned schema migrations. The initial migration creates the nine application tables. |
| `tests/` | Order lifecycle, end-to-end delivery-flow, and security regression coverage. |

### Route groups

Routes are mounted under `/api/v1`:

| Prefix | Purpose |
|---|---|
| `/auth` | Customer registration, login, and current-user lookup. |
| `/users` | Admin-managed operational user creation and user listing. |
| `/orders` | Order creation, scoped listing/detail, public tracking-number lookup, cancellation, and customer reviews. |
| `/dispatch` | Order review, available-rider recommendations, assignment/reassignment, and failed-order return. |
| `/rider` | Assignment responses, delivery status, availability, proof submission, and GPS updates. |
| `/tracking` | Latest permitted rider location and location history. |
| `/notifications` | Current-user notification listing and read state. |

## 3. Database schema and key entities

All IDs are integer primary keys. Foreign keys preserve relationships between
users, orders, riders, dispatchers, and delivery events. UTC-aware timestamps
are used for operational times. The initial PostgreSQL migration is
`97efcca21231_initial_database_schema.py`.

### `users`

The account table: `id`, unique indexed `email`, `hashed_password`,
`full_name`, `phone_number`, `role`, `is_verified`, `account_status`, `created_at`, and
`updated_at`. Roles are `admin`, `dispatcher`, `rider`, and `customer`;
account status is `active` or `suspended`. Customer and trusted administrator
accounts are verified by default; dispatcher and rider self-registration
requires administrator approval before login. A user may have one rider
profile, place many orders, and receive many notifications.

### `rider_profiles`

Rider-specific information: `id`, unique `user_id` foreign key,
`vehicle_type`, `vehicle_registration`, and `availability_status`.
Availability values are `available`, `unavailable`, and `on_delivery`.
Keeping these fields out of `users` avoids nullable vehicle data for
non-riders.

### `orders`

Delivery request and current snapshot: `id`, `customer_id`, unique indexed
`tracking_number`, pickup and destination addresses and coordinates,
recipient name and phone, package description, nonnegative `delivery_fee`,
`current_status`, and creation time. Coordinate checks constrain latitude to
[-90, 90] and longitude to [-180, 180]. Decimal numeric columns preserve
coordinate and fee precision. `customer_id` references `users`.

### `assignments`

An assignment attempt associates an order, rider profile, and dispatcher.
It stores `assigned_at`, optional `accepted_at`, and an assignment status:
`pending`, `accepted`, `rejected`, `withdrawn`, or `completed`. Orders have
multiple assignment records over their lifetime. This is intentionally
separate from `orders`: reassignment preserves who was previously assigned
instead of overwriting history. PostgreSQL partial unique indexes allow at
most one `pending` or `accepted` assignment per order and per rider, preventing
double assignment when dispatch requests race.

### `order_status_history`

An append-style status timeline: `order_id`, `updated_by`, previous and new
status, optional remarks, and `updated_at`. `updated_by` references `users`;
it records which actor initiated a change. Initial order creation records a
`pending` event with no previous status.

### `rider_locations`

Timestamped location history: `rider_id`, nullable `assignment_id`, latitude,
longitude, recorded time, and optional accuracy. New records link to the
assignment that reported them; older rows remain unlinked until they can be
reliably attributed. Database checks validate coordinate ranges and
nonnegative accuracy. Customer tracking history is scoped to the exact active
assignment and order authorization, rather than exposing the rider's entire
location history.

### `notifications`

Per-user messages: `user_id`, title, message, `is_read`, and `created_at`.
Read and list operations are restricted to the authenticated owner.

### `delivery_proofs`

Proof metadata: `order_id`, optional `image_url`, `verification_code_hash`,
`verified_at`, `code_expires_at`, `verification_attempts`, and `created_at`.
The hash column stores an Argon2 digest, not the submitted OTP. Attempt count
is constrained to be nonnegative. One order can have proof records across
verification events.

### `reviews`

Customer feedback: `order_id`, `customer_id`, `rider_id`, rating, optional
comment, and `created_at`. The order foreign key is unique (one review per
order); a check constraint limits rating to 1–5. The API only allows the
owning customer to review a delivered order and resolves the completed rider
assignment before inserting a review.

### Relationship and constraint rationale

- Foreign keys express ownership and operational relationships and prevent
  orphan records.
- `users.email`, `orders.tracking_number`, and `rider_profiles.user_id` are
  unique.
-   The assignment partial indexes complement route checks to protect the
  one-active-assignment-per-order and per-rider invariants at the database layer.
- Coordinate/rating/fee checks duplicate Pydantic validation at the database
  boundary; malformed writes cannot bypass API input validation and violate
  these key constraints.
- Status history and assignment history are retained rather than represented
  only by mutable current-state columns.
- Delivery fees are calculated by the server as a GH₵ 5.00 base plus GH₵ 1.50
  per straight-line kilometer, rounded to two decimals. The frontend estimate
  is display-only and client-supplied fee values are ignored.
- Rider location rows can grow rapidly. This first version retains history and
  indexes by rider/time; production deployments should define a retention
  policy and may add a dedicated latest-location strategy.

## 4. Security architecture

### Authentication and JWTs

`POST /api/v1/auth/register` accepts an optional role field for signup forms,
normalizes case-insensitive role names, and defaults to `customer`. Customer
registration is always available. Dispatcher and rider self-registration is
disabled by default and can only be enabled when `APP_ENV=development` and
`ALLOW_PUBLIC_ROLE_REGISTRATION=true`; the route additionally requires a
loopback client IP or a request with an allowlisted localhost origin and
localhost API host (for Windows-to-WSL local forwarding). Admin
self-registration is never permitted. Never enable the development setting in
a shared or production environment. Rider registration also creates an
unavailable rider profile and requires vehicle type and registration.
Publicly registered dispatcher and rider accounts are created with
`is_verified=false`. An administrator approves them in the Admin dashboard or
with `PATCH /api/v1/users/{user_id}/approve`. Until approved,
`POST /api/v1/auth/login` returns `403` with
`Account pending administrator approval.` Admin-provisioned accounts through
`/api/v1/users` are verified immediately. Customer and approved operational
accounts can log in; login verifies the submitted password and returns an
access token. Clients send it as:

```http
Authorization: Bearer <access-token>
```

The token contains a string `sub` user ID and an `exp` expiration. PyJWT signs
and verifies using HS256 only. Runtime configuration:

| Setting | Meaning | Validation |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection string | Required. |
| `JWT_SECRET_KEY` | HMAC signing secret | Required and at least 32 characters. Keep private; never commit or log it. |
| `JWT_ALGORITHM` | JWT signing algorithm | Restricted to `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime | Integer from 1 through 1440; default 30. |
| `APP_ENV` | Runtime environment | `development`, `test`, or `production`; defaults to production. |
| `ALLOW_PUBLIC_ROLE_REGISTRATION` | Local test-account provisioning | Defaults to false; honored only in development and for loopback requests. |

Protected requests validate the signature and expiry, load the user from the
database, and reject missing, suspended, or unknown accounts. Role authorization
uses the current database role, not an untrusted client-supplied role claim.
There is no refresh-token or explicit token-revocation list; suspending an
account prevents use of its otherwise-unexpired token.

### Passwords and delivery codes

`hash_password` and `verify_password` use Argon2 via `pwdlib`. User creation
requires passwords of at least eight characters (and no more than 128).
Passwords are never included in user response schemas.

When a rider moves an order to `in_transit`, the backend creates an in-app
notification directing the owner to request a delivery code from the
authenticated tracking page. The customer-only endpoint returns a newly
generated six-digit code once and stores only its Argon2 hash and expiration
(15 minutes). Each order allows at most three code requests and five failed
attempts across all assignments, so reassignment cannot reset the retry budget.
The response is a demonstration delivery channel; production should send the
code through a configured SMS or email provider.

Proof submission requires the rider's accepted assignment, an `in_transit`
order, an unexpired code, a matching Argon2 verification, and a valid proof
image URL. Failed comparisons are counted; five failed attempts are allowed,
and subsequent attempts are rejected. Successful verification timestamps the
proof, marks the order delivered, completes the assignment, and restores rider
availability.

### Authorization and IDOR protection

- Customers can list and view only their own orders, cancel only their own
  eligible orders, review only their delivered orders, and see only their own
  notifications.
- Riders can list only their assignments, respond only to assignments owned
  by their rider profile, update status/location/proof only for their own
  accepted assignment, and cannot use dispatcher routes.
- Dispatch routes use a router-level role dependency for dispatcher access;
  admins are explicitly accepted by the shared role dependency as operational
  administrators.
- Admin routes for user management require the admin role.
- Tracking endpoints verify customer ownership, rider assignment, or an
  operational role before returning rider location. Public tracking-number
  lookup deliberately returns a limited status/address view and does not
  expose GPS coordinates or recipient contact information.
- SQLAlchemy parameterized expressions are used for database queries; user
  input is not concatenated into SQL statements.
- Request schemas and database checks constrain coordinates, fees, ratings,
  identifier formats, and body sizes where defined.
- Browser clients are restricted by `CORS_ALLOWED_ORIGINS`; local Vite origins
  are supplied as defaults. Production deployments must configure their exact
  HTTPS frontend origin. Cross-origin cookies are disabled; the frontend uses
  bearer authorization headers.

### Security regression suite

`tests/test_security.py` uses isolated SQLite metadata and API requests to
exercise:

- Customer order read/cancel ownership and tracking access isolation.
- Rider attempts to update an order not assigned to that rider.
- Customer/rider denial on dispatcher-only routes.
- Argon2 password hash format, successful/failed verification, and short
  password rejection.
- Malformed, wrong-signature, and expired JWT rejection.
- Injection-like tracking parameters, out-of-range coordinates, and malformed
  order bodies.
- Hashed OTP storage, failed-attempt limits, and expiry.

`tests/test_delivery_flow.py` exercises a full customer → dispatcher → rider →
recipient-verification → customer-review workflow. `tests/test_order_lifecycle.py`
checks the lifecycle transition map and event recording.

## 5. Business logic and order lifecycle

`app/services/order_service.py` defines permitted transitions. The API rejects
invalid transitions with HTTP 409 and records each successful transition with
actor, previous/new status, timestamp, and optional remarks.

| Current state | Permitted next state(s) |
|---|---|
| `pending` | `confirmed`, `rejected`, `cancelled` |
| `confirmed` | `assigned`, `cancelled` |
| `assigned` | `accepted`, `confirmed` (declined/withdrawn assignment) |
| `accepted` | `picked_up`, `confirmed` (reassignment) |
| `picked_up` | `in_transit` |
| `in_transit` | `delivered`, `failed` |
| `failed` | `assigned` (retry) or `returned` |
| `rejected`, `cancelled`, `delivered`, `returned` | No further transitions |

Operational constraints further narrow which role can request a particular
permitted transition. Dispatchers review pending orders, assign confirmed
orders to available active riders, and may reassign eligible assignments.
Riders accept or reject pending assignments and update their assigned orders.
Only the delivery-proof verification endpoint completes an order as delivered.
All order/assignment/history changes are committed in the same request
transaction.

Rider recommendations are dispatcher-assisted: the API filters for active
accounts and available riders with no active assignment. If pickup coordinates
are provided, candidates with recent (no older than ten minutes) location data
can be filtered by distance. The dispatcher makes the final assignment.

Location updates require an accepted assignment and an active delivery state.
Coordinates are range-checked, timestamps must be within the accepted recent
window, timestamps must increase, and updates are limited to at least five
seconds apart. The latest stored location remains available with its recorded
time; clients should present stale data as stale rather than live.

## 6. API reference

All paths below are prefixed with `/api/v1`.

| Method | Path | Access / behavior |
|---|---|---|
| `POST` | `/auth/register` | Public; accepts `role` (default `CUSTOMER`); customer registration is immediate, local-development dispatcher/rider signup requires approval. |
| `POST` | `/auth/login` | Public; rejects unverified accounts with 403, otherwise returns a bearer token. |
| `GET` | `/auth/me` | Authenticated; returns current user. |
| `GET`, `POST` | `/users` | Admin only; list users or create a verified operational account. |
| `PATCH` | `/users/{user_id}/approve` | Admin only; verify and activate a dispatcher or rider, including restoring a rejected account. |
| `PATCH` | `/users/{user_id}/reject` | Admin only; reject and suspend a pending dispatcher or rider account. |
| `POST` | `/orders` | Customer; create order with a server-calculated fee and initial status-history record. |
| `POST` | `/orders/{order_id}/delivery-code` | Owning customer requests a short-lived verification code while the order is in transit. |
| `GET` | `/orders` | Authenticated; results scoped by customer/rider role; operations roles can view all. |
| `GET` | `/orders/{order_id}` | Authenticated; order and status history, with ownership/assignment checks. |
| `PATCH` | `/orders/{order_id}/cancel` | Customer owner, dispatcher, or admin; only pending/confirmed. |
| `GET` | `/orders/track/{tracking_number}` | Public; limited tracking information, no GPS. |
| `POST` | `/orders/{order_id}/review` | Owning customer; delivered orders only. |
| `GET` | `/dispatch/orders` | Dispatcher/admin; awaiting review or assignment. |
| `PATCH` | `/dispatch/orders/{order_id}/review` | Dispatcher/admin; confirm or reject pending order. |
| `PATCH` | `/dispatch/orders/{order_id}/return` | Dispatcher/admin; return failed order. |
| `GET` | `/dispatch/riders` | Dispatcher/admin; candidate riders with optional pickup-distance filtering. |
| `POST` | `/dispatch/assignments` | Dispatcher/admin; assign a rider to confirmed order. |
| `PATCH` | `/dispatch/assignments/{assignment_id}` | Dispatcher/admin; reassign eligible order. |
| `GET` | `/rider/deliveries` | Rider; active assignments, optionally including history. |
| `PATCH` | `/rider/assignments/{assignment_id}/respond` | Assigned rider; accept or reject. |
| `PATCH` | `/rider/orders/{order_id}/status` | Assigned rider; pickup, in-transit, or failed updates. |
| `PATCH` | `/rider/availability` | Rider; availability update subject to active assignments. |
| `POST` | `/rider/orders/{order_id}/proof` | Assigned rider; code verification and proof URL. |
| `POST` | `/rider/location` | Rider with accepted assignment; validated GPS update. |
| `GET` | `/tracking/{order_id}` | Authenticated and authorized; latest location. |
| `GET` | `/tracking/{order_id}/history` | Authenticated and authorized; bounded history scoped to the active assignment. |
| `GET` | `/notifications` | Authenticated; current user's notifications. |
| `PATCH` | `/notifications/{notification_id}/read` | Authenticated owner; mark read. |
| `GET` | `/health` | Public process health check. |

FastAPI provides interactive OpenAPI docs at `/docs` and a schema at
`/openapi.json`.

## 7. Local setup and developer workflow

Run commands from the `backend/` directory. Python 3.10+ is recommended for
the type syntax used in the code.

### Create a virtual environment

PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use the Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Configure `.env`

Copy the example and edit the local file:

```powershell
Copy-Item .env.example .env
```

Set these variables in `backend/.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/delivery_dispatch
JWT_SECRET_KEY=<random-secret-at-least-32-characters>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

Generate a secret without echoing or committing it:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

`.env` is ignored by Git. Never paste the secret into documentation, logs, or
source control. Keep `JWT_ALGORITHM` at HS256; configuration rejects other
algorithms. The database server and database must exist and be reachable before
migrations or application startup.
`CORS_ALLOWED_ORIGINS` is a JSON array; replace or extend its local defaults
with the exact frontend origin for the deployment.

### Apply or create migrations

Apply the current schema:

```powershell
alembic upgrade head
```

Create a migration after changing models:

```powershell
alembic revision --autogenerate -m "Describe schema change"
```

Review autogenerated scripts before applying them. To confirm the database has
no schema drift:

```powershell
alembic check
alembic current
```

The current initial revision is `97efcca21231`. Do not edit an already-applied
migration; add a new revision for subsequent schema changes.

### Run the API and tests

```powershell
uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000/docs`. Run the full tests:

```powershell
python -m pytest -q
```

Useful focused checks:

```powershell
python -m pytest tests/test_security.py -q
python -m pytest tests/test_order_lifecycle.py tests/test_delivery_flow.py -q
python -m compileall -q app tests alembic
```

## 8. Operational notes and current limitations

- `backend/.env` is environment-specific and must be configured locally or in
  the deployment secret manager. The `.env.example` contains placeholders.
- Public registration creates customers only. The first admin must be
  provisioned through a trusted, controlled bootstrap procedure before admin
  user-management endpoints can be used.
- Delivery notifications currently direct the customer to request the code in
  their authenticated tracking page; no SMS/email integration is present.
- Proof submission stores a URL, not an uploaded image. A production
  implementation needs controlled object storage, authorization, and upload
  validation.
- The current API stores and reads location via HTTP. It does not broadcast
  real-time socket events or promise background GPS after the rider closes the
  browser.
- Database engine SQL echo is currently enabled in `app/database/connection.py`
  for development. Disable it for production to avoid verbose query logging.
- Add deployment-specific rate limiting, secret rotation, audit/retention
  policies, TLS enforcement, and observability before production use.
