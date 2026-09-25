from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import now_utc
from app.core.types import UTCDateTime
from app.models.base import Base, TimestampMixin, str_enum
from app.models.enums import Language, UserRole


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable: HR administrators do not have to be employees.
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), unique=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        str_enum(UserRole, "user_role"), default=UserRole.EMPLOYEE, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    preferred_language: Mapped[Language] = mapped_column(
        str_enum(Language, "language"), default=Language.UZ, nullable=False
    )

    employee: Mapped["Employee | None"] = relationship(back_populates="user", lazy="joined")  # noqa: F821
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="raise"
    )

    @property
    def is_hr(self) -> bool:
        return self.role == UserRole.HR


class RefreshToken(Base):
    """Server-side record of issued refresh tokens so they can be revoked (logout, rotation, reuse detection)."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now_utc, nullable=False)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens", lazy="raise")

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > now_utc()
