


from sqlalchemy import select, and_, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.offers import Offer


class OfferRepository:

    @staticmethod
    async def batch_upsert(session: AsyncSession, value: list[dict]):
        stmt = insert(Offer).values(value)

        stmt = stmt.on_conflict_do_update(
            index_elements=["provider_id", "supplier_offer_id"],
            set_={
                "price": stmt.excluded.price,
                "currency": stmt.excluded.currency,
                "is_active": True,
                "raw_json": stmt.excluded.raw_json,
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
        """
        Фильтрация по directions (OR), is_active, adt, chd, inf, ins, class_, direct, airlines, provider.
        """
        filters = [Offer.is_active == True]

        # directions: OR по каждому направлению
        direction_filters = []
        for d in search.directions:
            direction_filters.append(and_(
                Offer.origin == d.departure,
                Offer.destination == d.arrival,
                Offer.departure_date == d.departure_date
            ))
        if direction_filters:
            filters.append(or_(*direction_filters))

        # Новые фильтры
        if search.adt is not None:
            filters.append(Offer.adt == search.adt)
        if search.chd is not None:
            filters.append(Offer.chd == search.chd)
        if search.inf is not None:
            filters.append(Offer.inf == search.inf)
        if search.ins is not None:
            filters.append(Offer.ins == search.ins)
        if search.class_ is not None:
            filters.append(Offer.class_ == search.class_)
        if search.direct is not None:
            filters.append(Offer.direct == search.direct)
        # airlines и provider — если появятся в модели, добавить фильтрацию
        if getattr(search, 'provider', None):
            filters.append(Offer.provider_id == search.provider)

        stmt = select(Offer).where(and_(*filters))
        result = await session.execute(stmt)
        return result.scalars().all()
        


