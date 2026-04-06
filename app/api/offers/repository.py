from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, func, select, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.offers import Offer


class OfferRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def batch_upsert(self, value: list[dict]):
        if not value:
            return

        stmt = insert(Offer).values(value)

        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "search_hash"],
            set_={
                "price": stmt.excluded.price,
                "currency": stmt.excluded.currency,
                "departure_date": stmt.excluded.departure_date,
                "return_date": stmt.excluded.return_date,
                "available_seats": stmt.excluded.available_seats,
                "adt": stmt.excluded.adt,
                "chd": stmt.excluded.chd,
                "inf": stmt.excluded.inf,
                "ins": stmt.excluded.ins,
                "is_active": True,
                "raw_json": stmt.excluded.raw_json,
                "updated_at": func.now(), 
            },
        )

        await self.session.execute(stmt)

    async def get_offers(self) -> list[Offer]:
        data = select(Offer)

        result = await self.session.execute(data)
        return list(result.scalars().all())
    
    
    async def search_offers(self, user_id: UUID, search) -> list[dict[str, Any]]:
        filters = [Offer.is_active.is_(True), Offer.user_id == user_id]

        # --- ЛОГИКА НАПРАВЛЕНИЙ (Directions) ---
        if len(search.directions) == 1:
            # Ищем билеты в одну сторону (One Way)
            d = search.directions[0]
            filters.append(and_(
                Offer.origin == d.departure,
                Offer.destination == d.arrival,
                Offer.departure_date == d.departure_date,
                Offer.return_date.is_(None) # Важно: отсекаем RT, если ищут OW
            ))
        elif len(search.directions) == 2:
            # Ищем билеты Туда-Обратно (Round Trip)
            d_to = search.directions[0]
            d_back = search.directions[1]
            filters.append(and_(
                Offer.origin == d_to.departure,
                Offer.destination == d_to.arrival,
                Offer.departure_date == d_to.departure_date,
                Offer.return_date == d_back.departure_date
            ))

        # --- ЛОГИКА МЕСТ И ПАССАЖИРОВ ---
        # Суммируем всех нужных пассажиров (кроме младенцев без места INF)
        total_seats_needed = (search.adt or 0) + (search.chd or 0) + (search.ins or 0)
        filters.append(Offer.available_seats >= total_seats_needed)

        # Проверяем поддержку типов тарифом (флаги 1/0)
        if search.adt: filters.append(Offer.adt == 1)
        if search.chd: filters.append(Offer.chd == 1)
        if search.inf: filters.append(Offer.inf == 1)
        if search.ins: filters.append(Offer.ins == 1)

        # Фильтры по классу и провайдеру
        if search.booking_class: 
            filters.append(Offer.booking_class == search.booking_class)
        if search.direct is not None:
            filters.append(Offer.direct == search.direct)
        if getattr(search, 'provider', None):
            filters.append(Offer.provider_id == search.provider)

        stmt = select(Offer.raw_json, Offer.search_hash).where(and_(*filters))
        result = await self.session.execute(stmt)
        return [
            {"raw_json": row.raw_json, "search_hash": row.search_hash}
            for row in result.all()
        ]
    

    async def clear_expired_offers(self):
        """
        Удаляет записи из БД:
        1. Которые уже вылетили (departure_date < сегодня)
        2. Которые не обновлялись более чем max_age_minutes
        """
        today = datetime.now(timezone.utc).date()
        stmt = delete(Offer).where(
            Offer.departure_date < today,
        )

        result = cast(CursorResult[Any], await self.session.execute(stmt))
        return result.rowcount

        


