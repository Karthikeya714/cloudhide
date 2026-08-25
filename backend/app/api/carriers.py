import logging

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.carrier import CarrierMetricsResponse, CarrierRankResponse
from app.services.carrier_service import (
    get_carrier,
    list_carriers,
    rank_carriers,
    recommend_carriers,
    upload_and_analyze_carrier,
)
from app.services.file_service import FileTooLargeError
from app.services.steganography_service import UnsupportedFormatError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/carriers", tags=["carriers"])


@router.post("/upload", response_model=CarrierMetricsResponse, status_code=status.HTTP_201_CREATED)
async def upload_carrier(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> CarrierMetricsResponse:
    data = await file.read()

    try:
        carrier = upload_and_analyze_carrier(db, file.filename or "unnamed.png", data)
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CarrierMetricsResponse.model_validate(carrier)


@router.get("/analyze", response_model=list[CarrierMetricsResponse])
def get_carrier_analysis(
    carrier_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CarrierMetricsResponse]:
    """Return computed metrics for one carrier (carrier_id) or all analyzed carriers."""
    if carrier_id:
        carrier = get_carrier(db, carrier_id)
        if carrier is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carrier not found")
        return [CarrierMetricsResponse.model_validate(carrier)]

    return [CarrierMetricsResponse.model_validate(c) for c in list_carriers(db)]


@router.get("/rank", response_model=CarrierRankResponse)
def get_carrier_ranking(
    limit: int = Query(default=3, ge=1, le=50),
    db: Session = Depends(get_db),
) -> CarrierRankResponse:
    """All carriers ranked best-to-worst, plus the top `limit` recommended carriers."""
    ranked = rank_carriers(db)
    recommended = recommend_carriers(db, count=limit)

    return CarrierRankResponse(
        carriers=[CarrierMetricsResponse.model_validate(c) for c in ranked],
        recommended=[CarrierMetricsResponse.model_validate(c) for c in recommended],
    )
