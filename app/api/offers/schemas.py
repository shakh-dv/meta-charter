
# --- Search Schemas ---
from typing import Optional, List
from datetime import date

from pydantic import BaseModel, Field

class DirectionSearchIn(BaseModel):
    departure: str
    arrival: str
    departure_date: date

class OfferSearchRequest(BaseModel):
    directions: List[DirectionSearchIn]
    adt: int = 1 
    chd: int = 0
    inf: int = 0
    ins: int = 0
    
    booking_class: Optional[str] = Field(None, alias="class")
    direct: Optional[bool] = False
    flexible: Optional[bool] = True
    airlines: Optional[List[str]] = []
    passengers_ids: Optional[list[str]] = []

    model_config = {
        "populate_by_name": True
    }


class PriceDetailIn(BaseModel):
    passenger_type: str

    model_config = {
        "extra": "allow"
    }


class FareInfoIn(BaseModel):
    seats: int
    booking_class: Optional[str] = None

    model_config = {"extra": "allow"}



class ProviderIn(BaseModel):
    provider_id: str
    name: str
    is_charter: bool

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
    upsell: bool
    booking: bool
    is_baggage_info_provided_by_pax: bool
    is_no_changing_airport: bool
    price_details: list[PriceDetailIn]
    fares_info: list[FareInfoIn]
    baggages_info: list[dict]
    routes: list[RouteIn]
    provider: ProviderIn
    supplier_provider: dict


    model_config = {
        "extra": "allow"
    }


class OffersDataIn(BaseModel):
    offers: list[OfferIn]


# --- Response schema for /offers/search ---
class OffersSearchResponse(BaseModel):
    count: int
    offers: list[OfferIn]



