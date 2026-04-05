import asyncio
import hashlib
import json
from typing import NamedTuple, Protocol
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


class PreparedOffer(NamedTuple):
    validated: OfferIn
    normalized: dict
    search_hash: str


class OfferSearchUser(Protocol):
    id: UUID
    gts_email: str | None
    gts_password: str | None


class OfferService:

    def __init__(self, session: AsyncSession, user: OfferSearchUser) -> None:
        self.session = session
        self.user = user
        self.user_id = user.id


    async def search_offers(self, search: OfferSearchRequest) -> list:
        await self._ensure_not_blacklisted(search)

        db_offers = await OfferRepository.search_offers(self.session, self.user_id, search)
        if db_offers:
            return [{**o["raw_json"], "search_hash": o["search_hash"]} for o in db_offers]

        raw_offers = await self._fetch_from_gts(search)
        offers = [self._prepare_offer(o) for o in raw_offers]

        # Cache results locally for subsequent identical searches.
        if offers:
            try:
                await self._upsert_prepared(offers)
                logger.info("Cached %d offers for user %s", len(offers), self.user_id)
            except Exception as exc:
                logger.warning("Failed to persist external offers in cache: %s", exc)

        return [{**o.normalized, "search_hash": o.search_hash} for o in offers]
    
    async def save_offers(self, payload: OffersDataIn) -> None:
        """Public endpoint for /import. Normalizes each offer and upserts."""
        offers = [
            self._prepare_offer(offer.model_dump(mode="json"))
            for offer in payload.offers
        ]
        await self._upsert_prepared(offers)

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

    # ── PRIVATE ────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    async def _ensure_not_blacklisted(self, search: OfferSearchRequest) -> None:
        if not search.directions:
            return
        
        outbound = search.directions[0]
        if len(search.directions) == 1:
            trip_type = BlackListTripType.OW
            return_date = None
        elif len(search.directions) == 2:
            trip_type = BlackListTripType.RT
            return_date = search.directions[1].departure_date
        else:
            raise HTTPException(status_code=422, detail="Поддерживаются только OW и RT")

        blocking_rule = await BlackListRepository.find_blocking_rule(
            session=self.session,
            user_id=self.user_id,
            origin=outbound.departure,
            destination=outbound.arrival,
            trip_type=trip_type,
            departure_date=outbound.departure_date,
            return_date=return_date,
        )
        if blocking_rule is not None:
            raise HTTPException(
                status_code=403,
                detail="По этому направлению поиск запрещен blacklist-правилом",
            )


    async def _fetch_from_gts(self, search: OfferSearchRequest) -> list:
        if not self.user.gts_email or not self.user.gts_password:
            raise HTTPException(
                status_code=400,
                detail="Для пользователя не настроены GTS credentials",
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            travel = GlobalTravelClient(
                client,
                email=str(self.user.gts_email),
                password=str(self.user.gts_password),
            )
            await travel.authenticate()

            search_payload = search.model_dump(mode='json', by_alias=True, exclude_none=True)

            if search.direct is None:
                search_payload['direct'] = False

            result = await travel.create_search(search_payload)
            request_id = result["data"]["request_id"]

            await asyncio.sleep(settings.SEARCH_POLL_DELAY)

            return await travel.fetch_offers(request_id)
        

    def _build_db_row(self, prepared: PreparedOffer) -> dict:
        offer = prepared.validated

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
            "user_id":           str(self.user_id),
            "search_hash":       prepared.search_hash,
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
            "raw_json":          prepared.normalized,
        }
    
    async def _upsert_prepared(self, offers: list[PreparedOffer]) -> None:
        """Map prepared offers to DB rows and upsert."""
        rows = []
        for offer in offers:
            try:
                rows.append(self._build_db_row(offer))
            except Exception as exc:
                logger.warning("Skipping invalid offer offer_id=%s error=%s", getattr(offer.validated, "offer_id", None), exc)
        if rows:
            await OfferRepository.batch_upsert(self.session, rows)
            await self.session.commit()

    @staticmethod
    def _prepare_offer(raw: dict) -> PreparedOffer:
        """Validate, normalize and hash a raw offer. Single source of truth for search_hash."""
        model = OfferIn.model_validate(raw)
        data = model.model_dump(mode="json")
        return PreparedOffer(validated=model, normalized=data, search_hash=OfferService._compute_search_hash(data))


    @staticmethod
    def _compute_search_hash(data: dict) -> str:
        canonical = {k: v for k, v in data.items() if k not in _DYNAMIC_KEYS}
        return hashlib.md5(json.dumps(canonical, sort_keys=True, default=str).encode()).hexdigest()