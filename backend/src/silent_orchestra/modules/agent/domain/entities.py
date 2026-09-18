from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(kw_only=True, eq=False)
class Context:
    id: str
    user_id: str
    active_app: str
    activity: str
    space: str = "unspecified"
    device: str = "laptop"
    captured_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True, eq=False)
class GestureObservation:
    id: str
    user_id: str
    context_id: str
    gesture_key: str
    gesture_embedding: list[float]
    motion_type: str
    direction: str = "none"
    duration_ms: int
    speed: float | None = None
    amplitude: float | None = None
    frame_stored: bool = False
    detected_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True, eq=False)
class Action:
    id: str
    user_id: str
    observation_id: str
    action_type: str
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)
    executed_by: str = "USER"
    executed_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True, eq=False)
class GesturePattern:
    id: str
    user_id: str
    gesture_key: str
    gesture_embedding: list[float]
    motion_type: str
    direction: str
    intent: str
    context_scope: str
    target: str
    confidence: float = 0.0
    observation_count: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    auto_execute: bool = False
    status: str = "CANDIDATE"
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True, eq=False)
class AgentSuggestion:
    id: str
    user_id: str
    gesture_pattern_id: str
    suggested_intent: str
    modified_intent: str | None = None
    reason: str
    confidence: float
    status: str = "PENDING"
    created_at: datetime = field(default_factory=utcnow)
    responded_at: datetime | None = None


@dataclass(kw_only=True, eq=False)
class Execution:
    id: str
    user_id: str
    gesture_pattern_id: str
    observation_id: str
    intent: str
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float
    execution_mode: str = "DRY_RUN"
    status: str
    error_message: str | None = None
    executed_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True, eq=False)
class Feedback:
    id: str
    user_id: str
    gesture_pattern_id: str
    execution_id: str
    feedback_type: str
    corrected_intent: str | None = None
    created_at: datetime = field(default_factory=utcnow)
