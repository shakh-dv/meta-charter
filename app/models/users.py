import enum
import uuid

from sqlalchemy import TIMESTAMP, Column, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class UserRole(str, enum.Enum):
    admin = 'admin'
    agent = 'agent'


class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email = Column(String, nullable=False, unique=True, index=True)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.agent)
    created_at = Column(TIMESTAMP, server_default=func.now())

    