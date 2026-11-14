from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

BigIntPK = BigInteger().with_variant(Integer, "sqlite")  # sqlite only autoincrements INTEGER PKs


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    scores: Mapped[list["ScoreEntry"]] = relationship(back_populates="user")


class ScoreEntry(Base):
    """Append-only score events."""
    __tablename__ = "score_entries"
    __table_args__ = (Index("idx_score_user", "user_id"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), nullable=False)
    points: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[AppUser] = relationship(back_populates="scores")
