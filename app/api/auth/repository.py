
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


class AuthRepository:

    @staticmethod
    async def get_by_email(session: AsyncSession, email: str):
        """Return User or None."""
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)

        return result.scalar_one_or_none()
    
 
    @staticmethod
    async def create_user(session: AsyncSession, email: str, hashed_password: str):
        """Insert new user row and return it."""
        stmt = insert(User).values(email=email, password=hashed_password).returning(User)
        result = await session.execute(stmt)
        await session.commit()

        return result.scalar_one()




    
        


