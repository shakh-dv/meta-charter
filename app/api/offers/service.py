import json

from fastapi import HTTPException

from app.api.offers.schemas import OfferSearchRequest, OffersDataIn

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.offers.repository import OfferRepository
from app.api.offers.schemas import OfferIn


class OfferService:

    @staticmethod
    def serialize_offer_from_db(offer) -> dict:
        return {
            "provider_id": offer.provider_id,
            "supplier_offer_id": offer.supplier_offer_id,
            "origin": offer.origin,
            "destination": offer.destination,
            "departure_date": offer.departure_date,
            "price": float(offer.price),
            "currency": offer.currency,
            "adt": int(offer.adt) if offer.adt is not None else 1,
            "chd": int(offer.chd) if offer.chd is not None else 0,
            "inf": int(offer.inf) if offer.inf is not None else 0,
            "ins": int(offer.ins) if offer.ins is not None else 0,
            "class_": offer.class_,
            "direct": offer.direct,
            "is_active": offer.is_active,
            "raw_json": offer.raw_json,
            "created_at": offer.created_at.isoformat() if offer.created_at else None,
        }

    @staticmethod
    async def search_offers(session: AsyncSession, search: OfferSearchRequest):
        """
        Поиск офферов по directions, class, direct, airlines, provider.
        Возвращает сериализуемые dict-объекты из базы (serialize_offer_from_db).
        """
        offers = await OfferRepository.search_offers(session, search)
        return [OfferService.serialize_offer_from_db(o) for o in offers]

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
            "adt": offer.adt if offer.adt is not None else 1,
            "chd": offer.chd if offer.chd is not None else 0,
            "inf": offer.inf if offer.inf is not None else 0,
            "ins": offer.ins if offer.ins is not None else 0,
            "class_": offer.class_,
            "direct": offer.direct if offer.direct is not None else False,
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