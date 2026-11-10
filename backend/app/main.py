from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, dispatch, notifications, orders, rider, tracking, users

app = FastAPI(
    title="Delivery Dispatch Tracker API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(dispatch.router)
app.include_router(rider.router)
app.include_router(tracking.router)
app.include_router(notifications.router)
app.include_router(users.router)

@app.get("/health")
def health_check():
    """Health check endpoint to verify the server is running."""
    return {
        "status": "ok",
        "message": "Service is healthy and running"
    }