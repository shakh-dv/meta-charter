import logging

from fastapi import HTTPException

from app.api.offers.schemas import OfferSearchRequest, OffersDataIn

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.offers.repository import OfferRepository
from app.api.offers.schemas import OfferIn
from app.db.session import AsyncSessionLocal
logger = logging.getLogger(__name__)

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
        # 1. Защита от «пустых» данных. 
        # Проверяем, что в оффере есть хотя бы один маршрут и один сегмент.
        if not offer.routes or not offer.routes[0].segments:
            raise HTTPException(status_code=422, detail="Маршрут или сегменты отсутствуют")
        
        # 2. Определяем ключевые точки.
        # first_segment — это самый первый взлет (откуда летим).
        # last_segment — это самый последний прилет (куда в итоге приземлимся).
        # Используем [-1], чтобы достать ПОСЛЕДНИЙ элемент из списков.
        first_segment = offer.routes[0].segments[0]
        last_segment = offer.routes[-1].segments[-1]

        # 3. Вычисляем дату возврата (Return Date).
        # В авиации Round-Trip (RT) — это когда в массиве routes ДВА объекта: 
        # [0] — путь туда, [1] — путь обратно.
        return_date = None
        if len(offer.routes) > 1:
            # Если маршрутов больше одного, берем дату вылета первого сегмента из ВТОРОГО маршрута.
            return_date = offer.routes[1].segments[0].departure_date

        # 4. Собираем поддерживаемые типы пассажиров (Pax Types).
        # Делаем set (множество) из всех типов, которые прислал провайдер в ценах.
        # Пример результата: {"ADT", "CHD"}
        pax_types = {detail.passenger_type.upper() for detail in offer.price_details}

        # 5. Считаем доступные места (Available Seats).
        # Провайдер может прислать разные квоты на разные части пути.
        # Мы берем минимальное (min), потому что если на одном плече 9 мест, 
        # а на другом всего 2, то на весь маршрут мы можем продать только 2.
        available_seats = 0
        if offer.fares_info:
            available_seats = min(fare.seats for fare in offer.fares_info)

        # 6. Формируем плоский словарь для вставки в БД.
        return {
            "provider_id": offer.provider.provider_id,
            "supplier_offer_id": offer.offer_id,
            "origin": first_segment.departure_city_code,      # Код города вылета (напр. TAS)
            "destination": last_segment.arrival_city_code,    # Код города прилета (напр. MOW)
            "departure_date": first_segment.departure_date,
            "return_date": return_date,                       # NULL для билетов в одну сторону
            "price": offer.price_info.price,
            "currency": offer.price_info.currency,
            
            # Мапим типы пассажиров в 1 (да) или 0 (нет).
            # Это нужно, чтобы быстро фильтровать в SQL.
            "adt": 1 if "ADT" in pax_types else 0,
            "chd": 1 if "CHD" in pax_types else 0,
            "inf": 1 if "INF" in pax_types else 0,
            "ins": 1 if "INS" in pax_types else 0,
            
            "available_seats": available_seats,
            # Класс бронирования (напр. "E" - эконом, "B" - бизнес).
            "booking_class": offer.fares_info[0].booking_class if offer.fares_info else None,
            # Прямой рейс или нет? Если в первом маршруте всего 1 сегмент — значит прямой.
            "direct": len(offer.routes[0].segments) == 1,
            "is_active": True,
            # Сохраняем весь исходный JSON, чтобы потом отдать его фронтенду без потерь.
            # mode="json" превращает даты Pydantic в строки.
            "raw_json": offer.model_dump(mode="json"),
        }

    @staticmethod
    async def save_offers(session: AsyncSession, payload: OffersDataIn):
        offers = payload.offers
        valid_values = []

        for o in offers:
            try:
                mapped_data = OfferService.map_offer(o)
                valid_values.append(mapped_data)
            except Exception as e:
                continue
        
        if valid_values:
            await OfferRepository.batch_upsert(session, valid_values)
            await session.commit()

    @staticmethod
    async def get_offers(session: AsyncSession):
        data = await OfferRepository.get_offers(session)
        return data


    @staticmethod
    async def run_cleanup():
        """
        Фоновая задача, которую будет дергать APScheduler.
        """
        logger.info("Запуск фоновой очистки устаревших офферов...")
        # Создаем новую сессию вручную, так как это не HTTP-запрос
        async with AsyncSessionLocal() as session:
            try:
                deleted_count = await OfferRepository.clear_expired_offers(session)
                await session.commit()
                logger.info(f"Очистка завершена. Удалено: {deleted_count} записей.")
            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка при фоновой очистке: {e}")