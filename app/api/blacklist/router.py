from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.blacklist.schemas import BlackListCreateIn, BlackListOut, BlackListUpdateIn
from app.api.blacklist.service import BlackListService
from app.api.deps import get_current_user
from app.db.session import AsyncSession
from app.db.session import get_session
from app.models.black_list import BlackListTripType


router = APIRouter(prefix="/blacklist", tags=["blacklist"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=BlackListOut)
async def create_blacklist_rule(
    payload: BlackListCreateIn,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return await BlackListService.create(session, current_user.id, payload)


@router.get("", response_model=list[BlackListOut])
async def list_blacklist_rules(
    trip_type: BlackListTripType | None = Query(default=None),
    origin: str | None = Query(default=None, min_length=3, max_length=3),
    destination: str | None = Query(default=None, min_length=3, max_length=3),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return await BlackListService.list(
        session,
        current_user.id,
        trip_type=trip_type,
        origin=origin,
        destination=destination,
    )


@router.get("/{rule_id}", response_model=BlackListOut)
async def get_blacklist_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return await BlackListService.get_or_404(session, current_user.id, rule_id)


@router.patch("/{rule_id}", response_model=BlackListOut)
async def update_blacklist_rule(
    rule_id: UUID,
    payload: BlackListUpdateIn,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return await BlackListService.update(session, current_user.id, rule_id, payload)


@router.delete("/{rule_id}")
async def delete_blacklist_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    await BlackListService.delete(session, current_user.id, rule_id)
    return {"status": "ok"}
