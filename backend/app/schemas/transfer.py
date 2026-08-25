from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StegoImageSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    fragment_id: str
    carrier_id: str
    storage_provider: str
    storage_path: str


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    fragment_count: int
    status: str
    processing_time_ms: float | None
    created_at: datetime


class FragmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    fragment_index: int
    size: int
    sha256: str


class StegoImageDetail(BaseModel):
    id: str
    fragment_id: str
    fragment_index: int
    carrier_id: str
    carrier_filename: str
    psnr_db: float | None
    ssim: float | None
    capacity_utilization: float | None


class TransferDetailResponse(TransferResponse):
    encrypted_file_id: str | None
    encryption_time_ms: float | None
    fragmentation_time_ms: float | None
    embedding_time_ms: float | None
    extraction_time_ms: float | None
    recovery_time_ms: float | None
    recovered: bool
    fragments: list[FragmentSummary]
    stego_images: list[StegoImageDetail]


class TransferHideResponse(BaseModel):
    transfer_id: str
    fragment_count: int
    selected_carrier_ids: list[str]
    stego_images: list[StegoImageSummary]
    processing_time_ms: float
    status: str


class TransferRecoverResponse(BaseModel):
    transfer_id: str
    status: str
    original_filename: str
    recovered_size: int
    integrity_verified: bool
    processing_time_ms: float
