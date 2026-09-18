from typing import Protocol
from ...shared.ports import UnitOfWork


class DemoRepository(UnitOfWork, Protocol):
    def dependent_counts(self, user_id: str) -> dict[str, int]: ...
