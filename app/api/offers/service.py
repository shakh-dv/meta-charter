import asyncio

from fastapi import HTTPException
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.offers.external_client import GlobalTravelClient
from app.api.offers.repository import OfferRepository
from app.api.offers.schemas import OfferIn, OfferSearchRequest, OffersDataIn
from app.db.session import AsyncSessionLocal

from app.core.logger import logger

_SEARCH_POLL_DELAY = 4  # seconds — external API needs time to assemble results


class OfferService:

    @staticmethod
    async def search_offers(session: AsyncSession, search: OfferSearchRequest) -> list:
        db_offers = await OfferRepository.search_offers(session, search)
        if db_offers:
            return [o.raw_json for o in db_offers]

        return await OfferService._search_external(search)

    @staticmethod
    async def _search_external(search: OfferSearchRequest) -> list:
        async with httpx.AsyncClient(timeout=30.0) as client:
            travel = GlobalTravelClient(client)
            await travel.authenticate()

            result = await travel.create_search(search.model_dump(mode="json", by_alias=True))
            request_id = result["data"]["request_id"]

            await asyncio.sleep(_SEARCH_POLL_DELAY)

            return await travel.fetch_offers(request_id)
        
    @staticmethod
    def map_offer(offer: OfferIn) -> dict:
        if not offer.routes or not offer.routes[0].segments:
            raise HTTPException(status_code=422, detail="Маршрут или сегменты отсутствуют")
        
        first_segment = offer.routes[0].segments[0]
        last_segment = offer.routes[-1].segments[-1]

        return_date = (
            offer.routes[1].segments[0].departure_date
            if len(offer.routes) > 1
            else None
        )

        pax_types = {detail.passenger_type.upper() for detail in offer.price_details}

        # Считаем доступные места (Available Seats).
        # Провайдер может прислать разные квоты на разные части пути.
        # Мы берем минимальное (min), потому что если на одном плече 9 мест, 
        # а на другом всего 2, то на весь маршрут мы можем продать только 2.
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


    @staticmethod
    async def save_offers(session: AsyncSession, payload: OffersDataIn) -> None:
        rows = []
        for offer in payload.offers:
            try:
                rows.append(OfferService.map_offer(offer))
            except Exception as exc:
                logger.warning("Skipping invalid offer", offer_id=getattr(offer, "offer_id", None), error=str(exc))

        if rows:
            await OfferRepository.batch_upsert(session, rows)
            await session.commit()




    @staticmethod
    async def get_offers(session: AsyncSession):
        return await OfferRepository.get_offers(session)

    @staticmethod
    async def run_cleanup() -> None:
        """Called by APScheduler — creates its own session since there's no request context."""
        logger.info("Starting expired offer cleanup...")
        async with AsyncSessionLocal() as session:
            try:
                deleted = await OfferRepository.clear_expired_offers(session)
                await session.commit()
                logger.info("Cleanup complete", deleted=deleted)
            except Exception as exc:
                await session.rollback()
                logger.error("Cleanup failed", error=str(exc))