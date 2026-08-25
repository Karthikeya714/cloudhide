from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FragmentCreateRequest(BaseModel):
    encrypted_file_id: str
    fragment_count: int = Field(default=3, ge=1, le=64)


class FragmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transfer_id: str
    encrypted_file_id: str
    fragment_index: int
    total_fragments: int
    size: int
    sha256: str
    created_at: datetime


class FragmentCreateResponse(BaseModel):
    transfer_id: str
    fragment_count: int
    fragments: list[FragmentResponse]
