import asyncio
import hashlib
import json
from typing import Protocol
from uuid import UUID

from fastapi import HTTPException
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.blacklist.repository import BlackListRepository
from app.api.offers.external_client import GlobalTravelClient
from app.api.offers.repository import OfferRepository
from app.api.offers.schemas import OfferIn, OfferSearchRequest, OffersDataIn
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.black_list import BlackListTripType

from app.core.logger import logger

# Keys removed from raw_json before hashing — they are provider-side volatile IDs
# that change between requests but don't affect the semantic identity of the offer.
_DYNAMIC_KEYS: frozenset[str] = frozenset({"offer_id"})



class OfferSearchUser(Protocol):
    id: UUID
    gts_email: str | None
    gts_password: str | None


class OfferService:

    @staticmethod
    def _compute_search_hash(raw: dict) -> str:
        stable = {k: v for k, v in raw.items() if k not in _DYNAMIC_KEYS}
        serialized = json.dumps(stable, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()

    @staticmethod
    async def _ensure_not_blacklisted(
        session: AsyncSession,
        user_id: UUID,
        search: OfferSearchRequest,
    ) -> None:
        if not search.directions:
            return

        if len(search.directions) == 1:
            trip_type = BlackListTripType.OW
            outbound = search.directions[0]
            return_date = None
        elif len(search.directions) == 2:
            trip_type = BlackListTripType.RT
            outbound = search.directions[0]
            return_date = search.directions[1].departure_date
        else:
            raise HTTPException(status_code=422, detail="Поддерживаются только OW и RT")

        blocking_rule = await BlackListRepository.find_blocking_rule(
            session=session,
            user_id=user_id,
            origin=outbound.departure.strip().upper(),
            destination=outbound.arrival.strip().upper(),
            trip_type=trip_type,
            departure_date=outbound.departure_date,
            return_date=return_date,
        )
        if blocking_rule is not None:
            raise HTTPException(
                status_code=403,
                detail="По этому направлению поиск запрещен blacklist-правилом",
            )

    @staticmethod
    async def search_offers(session: AsyncSession, user: OfferSearchUser, search: OfferSearchRequest) -> list:
        def _item(offer: dict, search_hash: str) -> dict:
            result = dict(offer)
            result["search_hash"] = search_hash
            result["offer_id"] = offer["offer_id"]
            return result

        user_id = user.id

        await OfferService._ensure_not_blacklisted(session, user_id, search)

        db_offers = await OfferRepository.search_offers(session, user_id, search)
        if db_offers:
            return [_item(o["raw_json"], o["search_hash"]) for o in db_offers]

        external_offers = await OfferService._search_external(search, user)

        # Cache external results locally for subsequent identical searches.
        if external_offers:
            try:
                await OfferService.save_offers(
                    session,
                    user_id,
                    OffersDataIn(offers=[OfferIn.model_validate(offer) for offer in external_offers]),
                )
                pretty = json.dumps(external_offers, indent=2, ensure_ascii=False)
                logger.info("\n" + pretty)
            except Exception as exc:
                logger.warning("Failed to persist external offers in cache: %s", exc)

        return [_item(offer, OfferService._compute_search_hash(offer)) for offer in external_offers]

    @staticmethod
    async def _search_external(search: OfferSearchRequest, user: OfferSearchUser) -> list:
        gts_email = user.gts_email
        gts_password = user.gts_password

        if not gts_email or not gts_password:
            raise HTTPException(
                status_code=400,
                detail="Для пользователя не настроены GTS credentials",
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            travel = GlobalTravelClient(client, email=str(gts_email), password=str(gts_password))
            await travel.authenticate()

            result = await travel.create_search(search.model_dump(mode="json", by_alias=True, exclude_none=True))
            request_id = result["data"]["request_id"]

            await asyncio.sleep(settings.SEARCH_POLL_DELAY)

            return await travel.fetch_offers(request_id)
        
    @staticmethod
    def map_offer(user_id: UUID, offer: OfferIn) -> dict:
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
      

        raw = offer.model_dump(mode="json")
        search_hash = OfferService._compute_search_hash(raw)

        return {
            "user_id":           str(user_id),
            "search_hash":       search_hash,
            "provider_id":       offer.provider.provider_id,
            "supplier_offer_id": offer.offer_id,
            "origin":            first_segment.departure_city_code or first_segment.departure_airport_code,
            "destination":       last_segment.arrival_city_code or last_segment.arrival_airport_code,
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
            "raw_json":          raw,
        }


    @staticmethod
    async def save_offers(session: AsyncSession, user_id: UUID, payload: OffersDataIn) -> None:
        rows = []
        for offer in payload.offers:
            try:
                rows.append(OfferService.map_offer(user_id, offer))
            except Exception as exc:
                logger.warning("Skipping invalid offer offer_id=%s error=%s", getattr(offer, "offer_id", None), exc)

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
                logger.info("Cleanup complete: deleted=%s", deleted)
            except Exception as exc:
                await session.rollback()
                logger.error("Cleanup failed: %s", exc)