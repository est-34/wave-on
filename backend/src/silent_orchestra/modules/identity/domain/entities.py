from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(kw_only=True, eq=False)
class User:
    id: str
    name: str
    created_at: datetime = field(default_factory=utcnow)
