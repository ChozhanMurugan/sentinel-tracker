"""REST route for live system stats."""
from fastapi import APIRouter
from app.services.stats import get_counts

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_stats():
    """Live contact counts from Redis."""
    return await get_counts()
