from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .domain.entities import Execution


@dataclass(kw_only=True)
class ContextInput:
    active_app: str | None = None
    activity: str | None = None
    space: str = "unspecified"
    device: str = "laptop"


@dataclass(kw_only=True)
class GestureInput:
    motion_type: str
    direction: str = "none"
    duration_ms: int = 430
    speed: float | None = None
    amplitude: float | None = None
    embedding: list[float] | None = None


@dataclass(kw_only=True)
class InferenceResult:
    matched: bool
    intent: str | None = None
    target: str | None = None
    confidence: float = 0.0
    reason: str
    execution: Execution | None = None


@dataclass(kw_only=True)
class ObserveRequest:
    user_id: str
    context: ContextInput
    gesture: GestureInput
    attempt_inference: bool = True


@dataclass(kw_only=True)
class TeachRequest:
    user_id: str
    observation_id: str
    action_type: str
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(kw_only=True)
class SuggestionResponseRequest:
    decision: str
    modified_intent: str | None = None


@dataclass(kw_only=True)
class FeedbackCreate:
    user_id: str
    feedback_type: str
    corrected_intent: str | None = None
