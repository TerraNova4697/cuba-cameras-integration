from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import String
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    ip: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(onupdate=func.now(), nullable=True)
    ping_period: Mapped[int] = mapped_column(default=60)
    prev_ping_period: Mapped[int] = mapped_column(default=60)
    last_ping: Mapped[datetime] = mapped_column(nullable=True)
    status: Mapped[int] = mapped_column(default=0, index=True)
