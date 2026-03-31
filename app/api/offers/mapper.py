# app/api/offers/mapper.py

from fastapi import HTTPException
from app.api.offers.schemas import OfferIn


class OfferMapper:
    """
    Pure, stateless data transformation — no I/O, no side effects.
    Easy to unit test without mocking anything.
    """

    @staticmethod
    def to_db_row(offer: OfferIn) -> dict:
        if not offer.routes or not offer.routes[0].segments:
            raise HTTPException(status_code=422, detail="Route or segments are missing")

        first_segment = offer.routes[0].segments[0]
        last_segment = offer.routes[-1].segments[-1]

        return_date = (
            offer.routes[1].segments[0].departure_date
            if len(offer.routes) > 1
            else None
        )

        pax_types = {d.passenger_type.upper() for d in offer.price_details}

        available_seats = (
            min(fare.seats for fare in offer.fares_info)
            if offer.fares_info
            else 0
        )

        return {
            "provider_id":       offer.provider.provider_id,
            "supplier_offer_id": offer.offer_id,
            "origin":            first_segment.departure_city_code,
            "destination":       last_segment.arrival_city_code,
            "departure_date":    first_segment.departure_date,
            "return_date":       return_date,
            "price":             offer.price_info.price,
            "currency":          offer.price_info.currency,
            "adt": int("ADT" in pax_types),
            "chd": int("CHD" in pax_types),
            "inf": int("INF" in pax_types),
            "ins": int("INS" in pax_types),
            "available_seats":   available_seats,
            "booking_class":     offer.fares_info[0].booking_class if offer.fares_info else None,
            "direct":            len(offer.routes[0].segments) == 1,
            "is_active":         True,
            "raw_json":          offer.model_dump(mode="json"),
        }