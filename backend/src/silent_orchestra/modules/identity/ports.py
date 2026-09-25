from typing import Protocol
from ...shared.ports import UnitOfWork
from .domain.entities import User


class IdentityRepository(UnitOfWork, Protocol):
    def list_users(self) -> list[User]: ...
