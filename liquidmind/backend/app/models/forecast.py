import uuid
from datetime import datetime, date

from sqlalchemy import String, Numeric, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    horizon_date: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_net: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    predicted_in: Mapped[float | None] = mapped_column(Numeric(18, 2))
    predicted_out: Mapped[float | None] = mapped_column(Numeric(18, 2))
    confidence_low: Mapped[float | None] = mapped_column(Numeric(18, 2))
    confidence_high: Mapped[float | None] = mapped_column(Numeric(18, 2))
    model_version: Mapped[str | None] = mapped_column(String(50))
    features_json: Mapped[dict | None] = mapped_column(JSONB)
