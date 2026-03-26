
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


class SegmentIn(BaseModel):
    departure_city_code: str
    arrival_city_code: str
    departure_date: date


class RouteIn(BaseModel):
    segments: list[SegmentIn]


class PriceInfoIn(BaseModel):
    price: float
    currency: str


class OfferIn(BaseModel):
    offer_id: str
    provider: ProviderIn
    routes: list[RouteIn]
    price_info: PriceInfoIn
    adt: Optional[int] = 1
    chd: Optional[int] = 0
    inf: Optional[int] = 0
    ins: Optional[int] = 0
    class_: Optional[str] = None
    direct: Optional[bool] = False


class OffersDataIn(BaseModel):
    offers: list[OfferIn]



