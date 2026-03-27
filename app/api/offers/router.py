
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.offers.schemas import OffersDataIn, OfferSearchRequest
from app.api.offers.service import OfferService
from app.db.session import get_session


router = APIRouter(prefix="/offers", tags=["offers"])


@router.post("/import")
async def import_offers(payload: OffersDataIn, session: AsyncSession = Depends(get_session)):
    await OfferService.save_offers(session, payload)
    # return api_response()
    return {"status": "ok"}



from typing import List
from app.api.offers.schemas import  OffersSearchResponse

@router.get("/export")
async def export_offers(session: AsyncSession = Depends(get_session)):
    data = await OfferService.get_offers(session)
    return data


# --- Новый endpoint поиска ---


@router.post("/search", response_model=OffersSearchResponse)
async def search_offers(
    search: OfferSearchRequest,
    session: AsyncSession = Depends(get_session),
):
    offers = await OfferService.search_offers(session, search)
    return {"count": len(offers), "offers": offers}

