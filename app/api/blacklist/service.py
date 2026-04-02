from datetime import date
from uuid import UUID

from fastapi import HTTPException

from app.api.blacklist.repository import BlackListRepository
from app.api.blacklist.schemas import BlackListCreateIn, BlackListUpdateIn
from app.db.session import AsyncSession
from app.models.black_list import BlackList, BlackListTripType


class BlackListService:
    @staticmethod
    async def _ensure_not_duplicate(
        session: AsyncSession,
        user_id: UUID,
        origin: str,
        destination: str,
        trip_type: BlackListTripType,
        departure_date: date | None,
        return_date: date | None,
        exclude_id: UUID | None = None,
    ) -> None:
        duplicate = await BlackListRepository.find_duplicate(
            session=session,
            user_id=user_id,
            origin=origin,
            destination=destination,
            trip_type=trip_type,
            departure_date=departure_date,
            return_date=return_date,
            exclude_id=exclude_id,
        )
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Blacklist rule already exists")

    @staticmethod
    async def create(session: AsyncSession, user_id: UUID, payload: BlackListCreateIn) -> BlackList:
        values = payload.model_dump()
        await BlackListService._ensure_not_duplicate(
            session=session,
            user_id=user_id,
            origin=values["origin"],
            destination=values["destination"],
            trip_type=values["trip_type"],
            departure_date=values["departure_date"],
            return_date=values["return_date"],
        )
        instance = await BlackListRepository.create(
            session,
            {
                "user_id": user_id,
                **values,
            },
        )
        await session.commit()
        return instance

    @staticmethod
    async def list(
        session: AsyncSession,
        user_id: UUID,
        trip_type: BlackListTripType | None = None,
        origin: str | None = None,
        destination: str | None = None,
    ) -> list[BlackList]:
        normalized_origin = origin.strip().upper() if origin is not None else None
        normalized_destination = destination.strip().upper() if destination is not None else None
        return await BlackListRepository.list(
            session,
            user_id,
            trip_type=trip_type,
            origin=normalized_origin,
            destination=normalized_destination,
        )

    @staticmethod
    async def get_or_404(session: AsyncSession, user_id: UUID, rule_id: UUID) -> BlackList:
        instance = await BlackListRepository.get_by_id(session, user_id, rule_id)
        if instance is None:
            raise HTTPException(status_code=404, detail="Blacklist rule not found")
        return instance

    @staticmethod
    async def update(
        session: AsyncSession,
        user_id: UUID,
        rule_id: UUID,
        payload: BlackListUpdateIn,
    ) -> BlackList:
        instance = await BlackListService.get_or_404(session, user_id, rule_id)
        values = payload.model_dump(exclude_unset=True)
        if not values:
            return instance

        new_origin = values.get("origin", instance.origin)
        new_destination = values.get("destination", instance.destination)
        new_trip_type = values.get("trip_type", instance.trip_type)
        new_departure_date = values.get("departure_date", instance.departure_date)
        new_return_date = values.get("return_date", instance.return_date)

        await BlackListService._ensure_not_duplicate(
            session=session,
            user_id=user_id,
            origin=new_origin,
            destination=new_destination,
            trip_type=new_trip_type,
            departure_date=new_departure_date,
            return_date=new_return_date,
            exclude_id=instance.id,
        )

        for key, value in values.items():
            setattr(instance, key, value)

        await session.commit()
        await session.refresh(instance)
        return instance

    @staticmethod
    async def delete(session: AsyncSession, user_id: UUID, rule_id: UUID) -> None:
        instance = await BlackListService.get_or_404(session, user_id, rule_id)
        await BlackListRepository.delete(instance, session)
        await session.commit()
