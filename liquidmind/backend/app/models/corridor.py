import uuid

from sqlalchemy import String, Numeric, Boolean, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Corridor(Base):
    __tablename__ = "corridors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    typical_delay_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    max_delay_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=72)
    fixed_cost: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    variable_cost: Mapped[float] = mapped_column(Numeric(8, 6), default=0)
    cutoff_hour: Mapped[int | None] = mapped_column(Integer)  # hour in UTC
    max_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "channel", name="uq_corridor"),
    )
