from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer
from .base import Base
from datetime import datetime
from sqlalchemy import DateTime, func

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    spotify_id: Mapped[str] = mapped_column(unique=True, nullable=False)

    username: Mapped[str | None]

    email: Mapped[str | None]

    profile_image: Mapped[str | None]

    spotify_access_token: Mapped[str]

    spotify_refresh_token: Mapped[str]

    token_expires_at: Mapped[datetime]

    user_refresh_token: Mapped[str | None]
    user_refresh_token_expires_at: Mapped[datetime| None]

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())