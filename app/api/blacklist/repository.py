from datetime import date
from uuid import UUID

from sqlalchemy import and_, or_, select

from app.db.session import AsyncSession
from app.models.black_list import BlackList, BlackListTripType


class BlackListRepository:
    @staticmethod
    async def create(session: AsyncSession, value: dict) -> BlackList:
        instance = BlackList(**value)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    @staticmethod
    async def find_duplicate(
        session: AsyncSession,
        user_id: UUID,
        origin: str,
        destination: str,
        trip_type: BlackListTripType,
        departure_date: date | None,
        return_date: date | None,
        exclude_id: UUID | None = None,
    ) -> BlackList | None:
        filters = [
            BlackList.user_id == user_id,
            BlackList.origin == origin,
            BlackList.destination == destination,
            BlackList.trip_type == trip_type,
            (
                BlackList.departure_date.is_(None)
                if departure_date is None
                else BlackList.departure_date == departure_date
            ),
            (
                BlackList.return_date.is_(None)
                if return_date is None
                else BlackList.return_date == return_date
            ),
        ]
        if exclude_id is not None:
            filters.append(BlackList.id != exclude_id)

        stmt = select(BlackList).where(and_(*filters)).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: UUID, rule_id: UUID) -> BlackList | None:
        stmt = select(BlackList).where(
            and_(
                BlackList.id == rule_id,
                BlackList.user_id == user_id,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        session: AsyncSession,
        user_id: UUID,
        trip_type: BlackListTripType | None = None,
        origin: str | None = None,
        destination: str | None = None,
    ) -> list[BlackList]:
        filters = [BlackList.user_id == user_id]
        if trip_type is not None:
            filters.append(BlackList.trip_type == trip_type)
        if origin is not None:
            filters.append(BlackList.origin == origin)
        if destination is not None:
            filters.append(BlackList.destination == destination)

        stmt = select(BlackList).where(and_(*filters)).order_by(BlackList.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def delete(instance: BlackList, session: AsyncSession) -> None:
        await session.delete(instance)

    @staticmethod
    async def find_blocking_rule(
        session: AsyncSession,
        user_id: UUID,
        origin: str,
        destination: str,
        trip_type: BlackListTripType,
        departure_date: date,
        return_date: date | None,
    ) -> BlackList | None:
        return_date_filter = (
            BlackList.return_date.is_(None)
            if return_date is None
            else or_(BlackList.return_date.is_(None), BlackList.return_date == return_date)
        )

        stmt = (
            select(BlackList)
            .where(
                and_(
                    BlackList.user_id == user_id,
                    BlackList.origin == origin,
                    BlackList.destination == destination,
                    or_(BlackList.trip_type == BlackListTripType.ANY, BlackList.trip_type == trip_type),
                    or_(BlackList.departure_date.is_(None), BlackList.departure_date == departure_date),
                    return_date_filter,
                )
            )
            .limit(1)
        )

        result = await session.execute(stmt)
        return result.scalar_one_or_none()
