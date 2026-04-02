import enum
import uuid

from sqlalchemy import TIMESTAMP, Column, Date, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class BlackListTripType(str, enum.Enum):
    OW = "OW"
    RT = "RT"
    ANY = "ANY"


class BlackList(Base):
    __tablename__ = "black_list"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    trip_type = Column(Enum(BlackListTripType), nullable=False, default=BlackListTripType.ANY)

    # Optional date constraints: if provided in rule, must match search exactly.
    departure_date = Column(Date, nullable=True)
    return_date = Column(Date, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            "ux_black_list_rule",
            "user_id",
            "origin",
            "destination",
            "trip_type",
            "departure_date",
            "return_date",
            unique=True,
        ),
        Index("idx_black_list_lookup", "user_id", "origin", "destination", "trip_type"),
    )
