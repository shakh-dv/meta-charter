from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.auth.schemas import LoginIn, RegisterIn, TokenOut
from app.api.auth.service import AuthService
from app.db.session import get_session


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(data: RegisterIn, session: AsyncSession = Depends(get_session)):
    token = await AuthService.register(session=session, data=data)
    return token


@router.post("/login")
async def login(data: LoginIn, session: AsyncSession = Depends(get_session)):
    token = await AuthService.login(session=session, email=data.email, password=data.password)
    return token


@router.post('/refresh', response_model=TokenOut)
async def refresh_token(
    refresh_token: str,
    session: AsyncSession = Depends(get_session)
):
    return await AuthService.refresh_tokens(session=session, refresh_token=refresh_token)