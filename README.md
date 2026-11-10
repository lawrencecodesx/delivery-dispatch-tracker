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
