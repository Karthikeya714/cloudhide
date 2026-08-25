"""Aggregates all versioned API routers (mounted under settings.api_prefix).

Future phases register their routers here, e.g.:
    from app.api import files
    api_router.include_router(files.router)
"""
from fastapi import APIRouter

from app.api import analytics, carriers, files, fragments, transfers

api_router = APIRouter()
api_router.include_router(files.router)
api_router.include_router(fragments.router)
api_router.include_router(carriers.router)
api_router.include_router(transfers.router)
api_router.include_router(analytics.router)
