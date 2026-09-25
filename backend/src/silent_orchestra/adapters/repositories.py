"""Compatibility exports for module-owned persistence adapters."""
from . import mapping  # noqa: F401 - preserve legacy ORM initialization
from .unit_of_work import SqlUnitOfWork
from ..modules.agent.adapters.repository import AgentRepository
from ..modules.identity.adapters.repository import IdentityRepository
from ..modules.demo.adapters.repository import DemoRepository

__all__ = ["SqlUnitOfWork", "AgentRepository", "IdentityRepository", "DemoRepository"]
