from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.black_list import BlackListTripType


class BlackListBase(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    trip_type: BlackListTripType = BlackListTripType.ANY
    departure_date: date | None = None
    return_date: date | None = None

    @field_validator("origin", "destination")
    @classmethod
    def normalize_airport_code(cls, value: str) -> str:
        return value.strip().upper()


class BlackListCreateIn(BlackListBase):
    pass


class BlackListUpdateIn(BaseModel):
    origin: str | None = Field(None, min_length=3, max_length=3)
    destination: str | None = Field(None, min_length=3, max_length=3)
    trip_type: BlackListTripType | None = None
    departure_date: date | None = None
    return_date: date | None = None

    @field_validator("origin", "destination")
    @classmethod
    def normalize_airport_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().upper()


class BlackListOut(BaseModel):
    id: UUID
    user_id: UUID
    origin: str
    destination: str
    trip_type: BlackListTripType
    departure_date: date | None
    return_date: date | None

    model_config = {"from_attributes": True}
