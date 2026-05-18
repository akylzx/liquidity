import uuid
from datetime import datetime

from sqlalchemy import String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(3), nullable=False)  # 'in' or 'out'
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # p2p, card, sepa, swift, partner, internal
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="settled")
    counterparty: Mapped[str | None] = mapped_column(String(255))
    reference: Mapped[str | None] = mapped_column(String(140))
    initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_settle: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    balance: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    available: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    in_flight_in: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    in_flight_out: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    source: Mapped[str] = mapped_column(String(20), default="synthetic")
