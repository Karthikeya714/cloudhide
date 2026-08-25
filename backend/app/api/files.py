import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.file import EncryptedFileResponse
from app.services.encryption_service import encrypt_file
from app.services.file_service import FileTooLargeError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])


@router.post("/encrypt", response_model=EncryptedFileResponse, status_code=status.HTTP_201_CREATED)
async def encrypt_file_endpoint(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> EncryptedFileResponse:
    data = await file.read()

    try:
        record = encrypt_file(db, file.filename or "unnamed", data)
    except FileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        logger.exception("Failed to encrypt uploaded file %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to encrypt file"
        ) from None

    return EncryptedFileResponse.model_validate(record)
