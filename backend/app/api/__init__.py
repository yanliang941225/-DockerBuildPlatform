"""
API routes initialization
"""
from app.api.tasks import router as tasks_router
from app.api.health import router as health_router
from app.api.storage import router as storage_router

__all__ = ["tasks_router", "health_router", "storage_router"]
