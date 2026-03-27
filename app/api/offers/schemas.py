
# --- Search Schemas ---
from typing import Optional, List
from datetime import date

from pydantic import BaseModel

class DirectionSearchIn(BaseModel):
    departure: str
    arrival: str
    departure_date: date

class OfferSearchRequest(BaseModel):
    directions: List[DirectionSearchIn]
    adt: Optional[int] = None
    chd: Optional[int] = None
    inf: Optional[int] = None
    ins: Optional[int] = None
    class_: Optional[str] = None  # Класс перелёта (E, B, ...)
    direct: Optional[bool] = None
    airlines: Optional[List[str]] = None
    provider: Optional[str] = None


class ProviderIn(BaseModel):
    provider_id: str

    model_config = {
        "extra": "allow"
    }


class SegmentIn(BaseModel):
    departure_city_code: str
    arrival_city_code: str
    departure_date: date

    model_config = {
        "extra": "allow"
    }


class RouteIn(BaseModel):
    segments: list[SegmentIn]

    model_config = {
        "extra": "allow"
    }


class PriceInfoIn(BaseModel):
    price: float
    currency: str

    model_config = {
        "extra": "allow"
    }


class OfferIn(BaseModel):
    offer_id: str
    price_info: PriceInfoIn
    price_details: list[dict]
    baggages_info: list[dict]
    fares_info: list[dict]
    routes: list[RouteIn]
    provider: ProviderIn
    supplier_provider: dict


    """
        Если нужно разрешить дополнительные поля — раскомментируйте model_config с extra="allow".
        Если нужно запретить лишние поля — оставьте как есть (по умолчанию extra="forbid").
    """
    # model_config = {
    #     "extra": "allow"
    # }


class OffersDataIn(BaseModel):
    offers: list[OfferIn]


# --- Response schema for /offers/search ---
class OffersSearchResponse(BaseModel):
    count: int
    offers: list[OfferIn]



