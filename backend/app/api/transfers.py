import logging

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.transfer import Transfer
from app.schemas.transfer import (
    FragmentSummary,
    StegoImageDetail,
    StegoImageSummary,
    TransferDetailResponse,
    TransferHideResponse,
    TransferRecoverResponse,
    TransferResponse,
)
from app.services.file_service import read_bytes
from app.services.pipeline_service import PipelineError, hide_file
from app.services.recovery_service import RecoveryError, recover_transfer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("/hide", response_model=TransferHideResponse, status_code=status.HTTP_201_CREATED)
async def hide_file_endpoint(
    file: UploadFile,
    fragment_count: int | None = Form(default=None),
    carrier_ids: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> TransferHideResponse:
    settings = get_settings()
    data = await file.read()
    count = fragment_count or settings.default_fragment_count
    ids = [c.strip() for c in carrier_ids.split(",") if c.strip()] if carrier_ids else None

    try:
        transfer = hide_file(db, file.filename or "unnamed", data, count, carrier_ids=ids)
    except PipelineError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        logger.exception("Hide pipeline failed for %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Hide pipeline failed"
        ) from None

    return TransferHideResponse(
        transfer_id=transfer.id,
        fragment_count=transfer.fragment_count,
        selected_carrier_ids=[s.carrier_id for s in transfer.stego_images],
        stego_images=[StegoImageSummary.model_validate(s) for s in transfer.stego_images],
        processing_time_ms=transfer.processing_time_ms or 0.0,
        status=transfer.status,
    )


@router.get("", response_model=list[TransferResponse])
def list_transfers(db: Session = Depends(get_db)) -> list[TransferResponse]:
    transfers = db.query(Transfer).order_by(Transfer.created_at.desc()).all()
    return [TransferResponse.model_validate(t) for t in transfers]


@router.get("/{transfer_id}", response_model=TransferDetailResponse)
def get_transfer(transfer_id: str, db: Session = Depends(get_db)) -> TransferDetailResponse:
    transfer = db.get(Transfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")

    return TransferDetailResponse(
        id=transfer.id,
        original_filename=transfer.original_filename,
        fragment_count=transfer.fragment_count,
        status=transfer.status,
        processing_time_ms=transfer.processing_time_ms,
        created_at=transfer.created_at,
        encrypted_file_id=transfer.encrypted_file_id,
        encryption_time_ms=transfer.encryption_time_ms,
        fragmentation_time_ms=transfer.fragmentation_time_ms,
        embedding_time_ms=transfer.embedding_time_ms,
        extraction_time_ms=transfer.extraction_time_ms,
        recovery_time_ms=transfer.recovery_time_ms,
        recovered=transfer.status == "recovered",
        fragments=[FragmentSummary.model_validate(f) for f in transfer.fragments],
        stego_images=[
            StegoImageDetail(
                id=s.id,
                fragment_id=s.fragment_id,
                fragment_index=s.fragment.fragment_index,
                carrier_id=s.carrier_id,
                carrier_filename=s.carrier.original_filename,
                psnr_db=s.psnr_db,
                ssim=s.ssim,
                capacity_utilization=s.capacity_utilization,
            )
            for s in transfer.stego_images
        ],
    )


@router.post("/{transfer_id}/recover", response_model=TransferRecoverResponse)
def recover_transfer_endpoint(transfer_id: str, db: Session = Depends(get_db)) -> TransferRecoverResponse:
    try:
        transfer = recover_transfer(db, transfer_id)
    except RecoveryError as exc:
        message = str(exc)
        not_found = f"No transfer with id {transfer_id}" in message
        code = status.HTTP_404_NOT_FOUND if not_found else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=code, detail=message) from exc
    except Exception:
        logger.exception("Recovery pipeline failed for transfer %s", transfer_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Recovery pipeline failed"
        ) from None

    recovered_bytes = read_bytes(transfer.recovered_storage_path)
    return TransferRecoverResponse(
        transfer_id=transfer.id,
        status=transfer.status,
        original_filename=transfer.original_filename,
        recovered_size=len(recovered_bytes),
        integrity_verified=True,
        processing_time_ms=transfer.recovery_time_ms or 0.0,
    )


@router.get("/{transfer_id}/download")
def download_recovered_file(transfer_id: str, db: Session = Depends(get_db)) -> Response:
    transfer = db.get(Transfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    if not transfer.recovered_storage_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transfer has not been recovered yet; call POST /recover first",
        )

    data = read_bytes(transfer.recovered_storage_path)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{transfer.original_filename}"'
        },
    )
