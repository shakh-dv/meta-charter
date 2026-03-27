import json

from fastapi import HTTPException

from app.api.offers.schemas import OfferSearchRequest, OffersDataIn

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.offers.repository import OfferRepository
from app.api.offers.schemas import OfferIn


class OfferService:

    @staticmethod
    async def search_offers(session: AsyncSession, search: OfferSearchRequest):
        """
        Поиск офферов по directions, class, direct, airlines, provider.
        Возвращает объекты, соответствующие OfferIn (через raw_json).
        """
        offers = await OfferRepository.search_offers(session, search)
        return [o.raw_json for o in offers]

    @staticmethod
    def map_offer(offer: OfferIn) -> dict:

        if not offer.routes or not offer.routes[0].segments:
            raise HTTPException(status_code=422, detail="Маршрут или сегменты отсутствуют")
        
        if not offer.routes[-1].segments:
            raise HTTPException(status_code=422, detail="В последнем маршруте нет сегментов")
        

        segment = offer.routes[0].segments[0]
        last_segment = offer.routes[-1].segments[-1]
        return {
            "provider_id": offer.provider.provider_id,
            "supplier_offer_id": offer.offer_id,
            "origin": segment.departure_city_code,
            "destination": last_segment.arrival_city_code,
            "departure_date": segment.departure_date,
            "price": offer.price_info.price,
            "currency": offer.price_info.currency,
            "is_active": True,
            "raw_json": json.loads(offer.model_dump_json()),
        }

    @staticmethod
    async def save_offers(session: AsyncSession, payload: OffersDataIn):
        offers = payload.offers

        values = [OfferService.map_offer(o) for o in offers]

        await OfferRepository.batch_upsert(session, values)
        await session.commit()

    @staticmethod
    async def get_offers(session: AsyncSession):
        data = await OfferRepository.get_offers(session)
        return data