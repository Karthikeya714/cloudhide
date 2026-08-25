from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import AnalyticsResponse, AnalyticsSummaryResponse, RecentTransferResponse
from app.services.analytics_service import get_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsResponse)
def get_analytics_endpoint(
    recent_limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AnalyticsResponse:
    data = get_analytics(db, recent_limit=recent_limit)
    return AnalyticsResponse(
        summary=AnalyticsSummaryResponse(**data.summary.__dict__),
        recent_transfers=[
            RecentTransferResponse(**t.__dict__) for t in data.recent_transfers
        ],
    )
