from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, select, and_, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.offers import Offer


class OfferRepository:

    @staticmethod
    async def batch_upsert(session: AsyncSession, value: list[dict]):
        if not value:
            return

        stmt = insert(Offer).values(value)

        stmt = stmt.on_conflict_do_update(
            index_elements=["provider_id", "supplier_offer_id"],
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

        await session.execute(stmt)

    @staticmethod
    async def get_offers(session: AsyncSession):
        data = select(Offer)

        result = await session.execute(data)
        return result.scalars().all()
    
    
    @staticmethod
    async def search_offers(session: AsyncSession, search):
        filters = [Offer.is_active == True]

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

        stmt = select(Offer).where(and_(*filters))
        result = await session.execute(stmt)
        return result.scalars().all()
    

    @staticmethod
    async def clear_expired_offers(session: AsyncSession, max_age_minutes: int = 60):
        """
        Удаляет записи из БД:
        1. Которые уже вылетили (departure_date < сегодня)
        2. Которые не обновлялись более чем max_age_minutes
        """

        threshold = datetime.now() - timedelta(minutes=max_age_minutes)

        stmt = delete(Offer).where(
            or_(
                Offer.departure_date < date.today(),
                Offer.updated_at < threshold
            )
        )

        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

        


