from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.time import now_utc
from app.core.types import UTCDateTime


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=now_utc, onupdate=now_utc, nullable=False
    )


def str_enum(enum_cls: type[PyEnum], name: str) -> Enum:
    """Enum stored as VARCHAR(32) holding the enum *values*.

    Non-native on purpose: adding a status later is a data change, not a
    PostgreSQL ALTER TYPE, and the same definition works on SQLite for tests.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=32,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )
