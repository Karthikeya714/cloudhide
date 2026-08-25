import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.fragment import FragmentCreateRequest, FragmentCreateResponse, FragmentResponse
from app.services.fragmentation_service import FragmentationError, fragment_file, list_fragments

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fragments", tags=["fragments"])


@router.post("/create", response_model=FragmentCreateResponse, status_code=status.HTTP_201_CREATED)
def create_fragments(
    request: FragmentCreateRequest,
    db: Session = Depends(get_db),
) -> FragmentCreateResponse:
    try:
        fragments = fragment_file(db, request.encrypted_file_id, request.fragment_count)
    except FragmentationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return FragmentCreateResponse(
        transfer_id=fragments[0].transfer_id,
        fragment_count=len(fragments),
        fragments=[FragmentResponse.model_validate(f) for f in fragments],
    )


@router.get("/{transfer_id}", response_model=list[FragmentResponse])
def get_fragments(transfer_id: str, db: Session = Depends(get_db)) -> list[FragmentResponse]:
    fragments = list_fragments(db, transfer_id)
    if not fragments:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No fragments found for transfer")
    return [FragmentResponse.model_validate(f) for f in fragments]
