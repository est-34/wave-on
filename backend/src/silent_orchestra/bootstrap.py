"""Composition root: the only place that binds application ports to adapters."""

from fastapi import Depends
from .config import settings
from .shared.policy import AgentPolicy
from .database import get_db
from .modules.agent.adapters.repository import AgentRepository
from .modules.identity.adapters.repository import IdentityRepository
from .modules.demo.adapters.repository import DemoRepository
from .modules.agent.application.dependencies import AgentDependencies
from .modules.identity.api import get_user
from .modules.agent.adapters import action_executor


def build_agent_dependencies(db) -> AgentDependencies:
    policy = AgentPolicy(
        suggestion_threshold=settings.suggestion_threshold,
        auto_execution_threshold=settings.auto_execution_threshold,
        recency_half_life_days=settings.recency_half_life_days,
        confirm_feedback_window_seconds=settings.confirm_feedback_window_seconds,
    )
    return AgentDependencies(
        repository=AgentRepository(db),
        policy=policy,
        execute_action=action_executor.execute_action,
        active_window=action_executor.active_window,
        require_user=lambda user_id: get_user(user_id, IdentityRepository(db)),
    )


def get_agent_dependencies(db=Depends(get_db)) -> AgentDependencies:
    return build_agent_dependencies(db)


# Preserve Session-based integrations while HTTP uses the explicit dependency bundle.
agent_repository = build_agent_dependencies
get_agent_repository = get_agent_dependencies


def get_identity_repository(db=Depends(get_db)):
    return IdentityRepository(db)


def get_demo_repository(db=Depends(get_db)):
    return DemoRepository(db)
