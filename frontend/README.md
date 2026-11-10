# Delivery & Dispatch Tracker — Frontend

Responsive React application for customer delivery requests, dispatch operations,
and rider workflows. Built with React, Vite, Tailwind CSS 4, React Router,
TanStack Query, Axios, React Leaflet, and Spline.

## Requirements and local setup

- Node.js 20.19+ and npm
- Backend API available at `http://localhost:8000` by default

From `frontend/`:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

Set `VITE_API_BASE_URL` in `.env` if the backend URL differs. Set
`VITE_SPLINE_SCENE_URL` to a published Spline scene URL to embed that interactive
scene on the landing page. When unset, the page displays an animated local
scene illustration instead. Restart Vite after changing environment variables.

## Commands

```powershell
npm run dev
npm run lint
npm run build
npm run preview
```

## Main views

- `/` — landing page with an optional interactive Spline scene.
- `/login` and `/register` — JWT sign-in and customer registration.
- `/customer` — customer order list; `/customer/create` creates an order;
  `/customer/track` lists deliveries and `/customer/track/:orderId` shows the
  timeline and periodically refreshed rider location.
- `/dispatcher` — pending-order review, rider availability, assignment dialog,
  and map of open-order pickup and destination points.
- `/rider` — assignment acceptance, pickup/transit status updates, location
  sharing, and delivery-code/proof submission.

The registration form calls `POST /auth/register` and includes the selected role.
Customer registration is always available. Dispatcher and rider test accounts
can be registered only when the backend explicitly enables its local-development
role-registration setting and the request is local/allowlisted; the form then
logs the new account in and opens the corresponding workspace. Rider signup
also collects required vehicle details. Never enable this setting in a shared
or production environment. `POST /users` remains admin-only.

The order form displays an estimate from direct map distance (GH₵ 5 base plus
GH₵ 1.50/km). The backend independently calculates and stores the authoritative
fee; clients cannot choose the persisted price.

The delivery-proof dialog accepts a proof-image URL because the current backend
requires `image_url` and does not expose an image upload endpoint. When an order
enters transit, an in-app notification points its owner to the tracking page to
request a code. The code is returned once to the authenticated customer, stored
only as an Argon2 hash, and is limited to three requests and five failed attempts
per order. A production deployment should connect this workflow to an SMS or
email provider. Riders can share their browser location while a delivery is
active; each location is tied to its assignment, and customer tracking refreshes
the current assignment's location every 15 seconds.

## Structure

- `src/components/` — app shell, route guard, reusable Leaflet map, status badge,
  and Spline landing scene.
- `src/context/` — auth state and server-verified user role.
- `src/services/api.js` — Axios API base URL and bearer-token interceptor.
- `src/pages/auth/` — login and public customer registration.
- `src/pages/customer/` — dashboard, order creation, and live tracking.
- `src/pages/dispatcher/` — dispatch review and assignment operations.
- `src/pages/rider/` — assignment and delivery lifecycle interface.

The access token is stored in `localStorage` to survive refreshes. Because
JavaScript can read local storage, production deployments should pair this with
a strong Content Security Policy and consider secure, HttpOnly cookies if the
backend authentication design is changed to support them.
