import uuid

from sqlalchemy import TIMESTAMP, Boolean, Column, Date, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class Offer(Base):
    __tablename__ = 'offers'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    provider_id = Column(String, nullable=False)
    supplier_offer_id = Column(String, nullable=False)

    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    price = Column(Numeric, nullable=False)
    currency = Column(String)


    available_seats = Column(Numeric, default=0, nullable=False)
    # Новые поля для фильтрации
    adt = Column(Numeric, nullable=False, default=1)
    chd = Column(Numeric, nullable=False, default=0)
    inf = Column(Numeric, nullable=False, default=0)
    ins = Column(Numeric, nullable=False, default=0)
    booking_class = Column(String(2), nullable=True)
    direct = Column(Boolean, nullable=False, default=False)

    is_active = Column(Boolean, default=True, nullable=False)

    raw_json = Column(JSONB, nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


    __table_args__ = (
        Index("ux_offer", "provider_id", "supplier_offer_id", unique=True),
        Index("idx_search", "origin", "destination", "departure_date", "price"),
        Index(
            "idx_active_true",
            "origin", "destination", "departure_date", "price",
            postgresql_where=is_active.is_(True)
        ),
    )