from dataclasses import dataclass


@dataclass
class UserCreate:
    name: str
    id: str | None = None
