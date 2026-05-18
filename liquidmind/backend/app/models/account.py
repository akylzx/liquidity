import uuid
from datetime import datetime

from sqlalchemy import String, Numeric, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_country: Mapped[str] = mapped_column(String(2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    account_number: Mapped[str | None] = mapped_column(String(34))
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, default="nostro")
    min_balance: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    max_balance: Mapped[float | None] = mapped_column(Numeric(18, 2))
    overdraft_limit: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    transfer_cost: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
