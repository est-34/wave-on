from datetime import datetime, timedelta
from typing import Protocol

from ...shared.ports import UnitOfWork
from .domain.entities import (
    AgentSuggestion,
    Context,
    Execution,
    Feedback,
    GestureObservation,
    GesturePattern,
)
from .domain.learning import EvidenceRow


class AgentRepository(UnitOfWork, Protocol):
    """Persistence port; implementations return entities, never SQL results."""

    def observation_has_action(self, observation_id: str) -> bool: ...
    def duplicate_memory(
        self, intent: str, pattern: GesturePattern
    ) -> GesturePattern | None: ...
    def learning_evidence(
        self,
        user_id: str,
        gesture_key: str,
        activity: str,
        now: datetime,
        window: timedelta,
        limit: int,
    ) -> list[EvidenceRow]: ...
    def last_rejection(
        self, user_id: str, gesture_key: str, activity: str, intent: str
    ) -> datetime | None: ...
    def matching_memory(
        self, user_id: str, gesture_key: str, activity: str, intent: str
    ) -> GesturePattern | None: ...
    def scope_memories(
        self, user_id: str, gesture_key: str, activity: str
    ) -> list[GesturePattern]: ...
    def pending_suggestions(
        self, scope_patterns: list[GesturePattern]
    ) -> list[AgentSuggestion]: ...
    def deactivate_other_memories(self, pattern: GesturePattern) -> None: ...
    def accidental_embeddings(
        self, context: Context, observation: GestureObservation
    ) -> list[list[float]]: ...
    def executable_memories(
        self, context: Context, observation: GestureObservation
    ) -> list[GesturePattern]: ...
    def execution_feedback(self, execution: Execution) -> Feedback | None: ...
    def pending_confirmation(
        self, activity: str, user_id: str
    ) -> AgentSuggestion | None: ...
    def unrated_execution(
        self, activity: str, cutoff: datetime, user_id: str
    ) -> Execution | None: ...
    def list_suggestions(
        self, user_id: str, status: str | None = None
    ) -> list[AgentSuggestion]: ...
    def list_memories(
        self,
        user_id: str,
        gesture_key: str | None = None,
        context_scope: str | None = None,
        *,
        threshold: float,
    ) -> list[GesturePattern]: ...
    def dashboard(self, user_id: str, *, suggestion_threshold: int) -> dict: ...


class ActionExecutor(Protocol):
    def __call__(
        self, intent: str, target: str, magnitude: int
    ) -> tuple[str, str, str | None]: ...


class ActiveWindow(Protocol):
    def __call__(self) -> str | None: ...


class UserLookup(Protocol):
    """Raise ApplicationError when the user does not exist."""
    def __call__(self, user_id: str) -> object: ...
