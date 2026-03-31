
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.offers.schemas import OffersDataIn, OfferSearchRequest
from app.api.offers.service import OfferService
from app.db.session import get_session
from app.api.offers.schemas import  OffersSearchResponse
from app.api.deps import get_current_user


router = APIRouter(
    prefix="/offers", 
    tags=["offers"], 
    # dependencies=[Depends(get_current_user)] # auth middleware
)


@router.post("/import")
async def import_offers(payload: OffersDataIn, session: AsyncSession = Depends(get_session)):
    await OfferService.save_offers(session, payload)
    return {"status": "ok"}



@router.get("/export")
async def export_offers(session: AsyncSession = Depends(get_session)):
    data = await OfferService.get_offers(session)
    return data



@router.post("/search", response_model=OffersSearchResponse)
async def search_offers(
    search: OfferSearchRequest,
    session: AsyncSession = Depends(get_session)
 ):
    offers = await OfferService.search_offers(session, search)
    return {"count": len(offers), "offers": offers}

