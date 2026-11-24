# Delivery & Dispatch Tracker

A web application for requesting deliveries, dispatching riders, and tracking
orders through delivery. The project is organized as a FastAPI backend and a
React/Vite frontend.

## Project structure

- [`backend/`](./backend/) — FastAPI, SQLAlchemy 2, Pydantic, PostgreSQL, Alembic,
  authentication, delivery workflows, and backend tests.
- [`frontend/`](./frontend/) — React/Vite application for customers,
  dispatchers, riders, and administrators.
- [`documentation/backend_architecture.md`](./documentation/backend_architecture.md) —
  backend architecture, security, database, and lifecycle details.

## Local development

1. Configure PostgreSQL and create local environment files:

   ```powershell
   Copy-Item backend/.env.example backend/.env
   Copy-Item frontend/.env.example frontend/.env
   ```

2. Follow [`backend/README.md`](./backend/README.md) to install Python
   dependencies, configure the database and JWT secret, apply Alembic migrations,
   and start the API.
3. Follow [`frontend/README.md`](./frontend/README.md) to install Node
   dependencies and start the frontend.

Do not commit `.env` files, production credentials, or database dumps. The
`.env.example` files contain placeholders for local configuration.

## Render + Vercel deployment

- Deploy the API and PostgreSQL database from [`render.yaml`](./render.yaml).
  Set Render's `ALLOWED_ORIGINS` to the exact Vercel HTTPS origin plus any
  local origins needed for development. Render runs Alembic migrations during
  the build and checks `/healthz`.
- Import [`frontend/`](./frontend/) as a Vercel project. Set
  `VITE_API_BASE_URL` to the deployed API's `https://<render-host>/api/v1`.
  The Vercel rewrite serves the React application for client-side routes.
