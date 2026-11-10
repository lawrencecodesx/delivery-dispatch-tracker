# Delivery & Dispatch Tracker API

## Configuration and startup

Copy `.env.example` to `.env`, set the PostgreSQL connection string, generate a
`JWT_SECRET_KEY` with at least 32 characters, keep `JWT_ALGORITHM=HS256`, and
choose an `ACCESS_TOKEN_EXPIRE_MINUTES` value from 1 to 1440. For example, in
PowerShell generate the secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`CORS_ALLOWED_ORIGINS` is a JSON array of trusted browser origins. The example
allows the local Vite URLs; add the deployed frontend's exact HTTPS origin when
deploying. The API does not enable cross-origin cookies.

Install the requirements and start the API from this directory:

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API documentation is available at `/docs`. Create database migrations from
the SQLAlchemy metadata with Alembic before deploying schema changes. The
initial schema is applied with:

```powershell
alembic upgrade head
```

## Authentication and roles

`POST /api/v1/auth/register` accepts a role field and defaults to customer.
Dispatcher and rider self-registration is disabled by default; for isolated
local testing only, set `APP_ENV=development` and
`ALLOW_PUBLIC_ROLE_REGISTRATION=true`. The backend still accepts those roles
only for loopback connections or allowlisted localhost browser origins (to
support Windows-to-WSL local forwarding). Never enable this setting in a shared
or production environment. Admin accounts can only be provisioned through a
trusted bootstrap. Login at
`POST /api/v1/auth/login` with JSON containing `email` and `password`, then send
the returned bearer token in the `Authorization` header. Admins create
dispatcher, rider, and other operational accounts through the admin-only
`/api/v1/users` endpoint. Provision the first administrator through a trusted
database bootstrap process; public registration cannot assign privileged roles.

Customers can access only their own orders and notifications. Riders can access
their assignments and locations. Dispatchers manage operational reviews and
assignments. Administrators can use administrative and operational endpoints.

Customer accounts are verified automatically. Publicly registered dispatcher
and rider accounts remain unverified and cannot log in until an administrator
approves them from the Admin dashboard. Administrators can also approve an
account through `PATCH /api/v1/users/{user_id}/approve`. Accounts created by an
administrator through the trusted `/api/v1/users` endpoint are verified
immediately. A pending application can be rejected with the same admin-only
API surface at `PATCH /api/v1/users/{user_id}/reject`; rejection suspends the
account so it cannot sign in. The administrator can later restore and approve
that account through the approve endpoint, which marks it verified and active.

## Order lifecycle

The API enforces the lifecycle defined in the project plan:

`pending -> confirmed/rejected/cancelled -> assigned -> accepted -> picked_up -> in_transit -> delivered/failed -> assigned/returned`

Only a recipient verification code can complete delivery. On the transition to
`in_transit`, the backend sends the customer an in-app notification directing
them to request a short-lived code on the authenticated tracking page. The API
returns the code only to the owning customer, stores only its Argon2 hash, and
limits an order to three code requests and five failed attempts across all
assignments. The rider submits that code with an image URL as delivery proof.
The request/response path is a demonstration channel; production should deliver
the code through an SMS or email provider.

Status changes and their actor are stored in `order_status_history`. Assignments
are retained as history, while a partial unique index prevents more than one
pending or accepted assignment for an order or rider. Rider GPS updates are
accepted only for an active assignment and include coordinate and timestamp
validation. Customer tracking history is filtered to the specific active
assignment instead of all locations reported by its rider.

The backend calculates delivery fees from straight-line pickup/destination
distance using a GH₵ 5.00 base plus GH₵ 1.50/km, rounded to the nearest pesewa.
The frontend displays the same calculation as an estimate; submitted client
fees are ignored.