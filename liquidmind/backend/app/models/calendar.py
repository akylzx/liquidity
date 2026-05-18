from datetime import date

from sqlalchemy import String, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Holiday(Base):
    __tablename__ = "holidays"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    country: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    affects_sepa: Mapped[bool] = mapped_column(Boolean, default=False)
    affects_swift: Mapped[bool] = mapped_column(Boolean, default=False)
    affects_cards: Mapped[bool] = mapped_column(Boolean, default=False)
