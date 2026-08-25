from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EncryptedFileResponse(BaseModel):
    """Public response for an encrypted file. Never includes the AES key."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    original_size: int
    encrypted_size: int
    status: str
    created_at: datetime
