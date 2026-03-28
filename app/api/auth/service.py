
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi.security import OAuth2PasswordBearer
import jwt
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.repository import AuthRepository
from app.api.auth.schemas import RegisterIn, TokenOut
from app.core.config import settings
from app.db.session import get_session


class AuthService:

    @staticmethod
    def hash_password(plain_password: str) -> str:
        return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()

    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        matched = bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
        return matched
    
    
    @staticmethod
    def _generate_token(payload: dict, expires_delta: timedelta) -> str:
        to_encode = payload.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode, 
            settings.JWT_SECRET_KEY.get_secret_value(), 
            algorithm=settings.JWT_ALGORITHM
        )


    @staticmethod
    def create_access_token(payload: dict) -> str:
        return AuthService._generate_token(
        payload, timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    @staticmethod
    def create_refresh_token(payload: dict) -> str:
        return AuthService._generate_token(
        payload, timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
        

    @staticmethod
    def decode_access_token(token: str) -> dict:
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY.get_secret_value(), 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail='Token expired')
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail='Invalid token')
        
        

    @staticmethod
    async def register(session: AsyncSession, data: RegisterIn) -> TokenOut:
        """Create a new user. Raise 409 if username already taken. Return access token."""
        user_exist = await AuthRepository.get_by_email(session=session, email=data.email)
        if user_exist:
            raise HTTPException(status_code=409, detail='User already exists')
        
        hashed_password = AuthService.hash_password(data.password)

        create_user = await AuthRepository.create_user(session, data.email, hashed_password=hashed_password)

        access_token = AuthService.create_access_token({'sub': create_user.email})

        refresh_token = AuthService.create_refresh_token({'sub': create_user.email})

        return TokenOut(access_token=access_token, refresh_token=refresh_token)


        

    @staticmethod
    async def login(session: AsyncSession, email: str, password: str) -> TokenOut:
        """Verify credentials. Raise 401 if wrong. Return access token."""
        user = await AuthRepository.get_by_email(session=session, email=email)

        if not user:
            raise HTTPException(status_code=401, detail='Invalid email or password')
        
        credentials_match = AuthService.verify_password(plain_password=password, hashed_password=user.password)

        if not credentials_match:
            raise HTTPException(status_code=401, detail='Invalid email or password')

        access_token = AuthService.create_access_token({'sub': user.email})
        refresh_token = AuthService.create_refresh_token({'sub': user.email})
        return TokenOut(access_token=access_token, refresh_token=refresh_token)
    

    @staticmethod
    async def refresh_tokens(session: AsyncSession, refresh_token: str) -> TokenOut:
        payload = AuthService.decode_access_token(token=refresh_token)

        email: str = payload.get('sub')
        if not email:
            raise HTTPException(status_code=401, detail='Invalid refresh token')
        
        user = await AuthRepository.get_by_email(session=session, email=email)

        if not user:
            raise HTTPException(status_code=401, detail='User not found')
        
        access_token = AuthService.create_access_token({'sub': user.email})
        new_refresh_token = AuthService.create_refresh_token({'sub': user.email})

        return TokenOut(access_token=access_token, refresh_token=new_refresh_token)

