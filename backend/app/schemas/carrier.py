import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class CarrierMetricsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    width: int
    height: int
    pixel_count: int
    raw_capacity_bytes: int
    max_payload_bytes: int
    shannon_entropy: float
    edge_density: float
    distortion_risk: float
    capacity_score: float
    entropy_score: float
    edge_score: float
    distortion_score: float
    overall_score: float
    explanation: list[str]
    created_at: datetime

    @field_validator("explanation", mode="before")
    @classmethod
    def _parse_explanation(cls, value: object) -> object:
        # The ORM stores explanation as a JSON-encoded string; decode it here
        # so API responses always expose a real list of strings.
        if isinstance(value, str):
            return json.loads(value)
        return value


class CarrierRankResponse(BaseModel):
    carriers: list[CarrierMetricsResponse]
    recommended: list[CarrierMetricsResponse]
