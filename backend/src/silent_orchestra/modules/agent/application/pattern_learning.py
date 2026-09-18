from datetime import datetime, timezone
from uuid import uuid4


from .dependencies import AgentDependencies
from ..domain.entities import (
    Action,
    AgentSuggestion,
    Context,
    GestureObservation,
    GesturePattern,
)
from ..contracts import TeachRequest
from ..domain.action_catalog import CONTEXT_INTENTS, action_label

from ..domain.learning import (
    LEARNING_WINDOW,
    MAX_LEARNING_ACTIONS,
    summarize_evidence,
    utc,
)


def check_intent_change(
    db: AgentDependencies, pattern: GesturePattern, intent: str, field: str
) -> None:
    """Reject an intent the context forbids or that another memory already owns."""
    if intent not in CONTEXT_INTENTS.get(pattern.context_scope, ()):
        raise ValueError(f"{field} is not allowed for this context")
    duplicate = db.repository.duplicate_memory(intent, pattern)
    if duplicate is not None:
        raise ValueError("A gesture memory with this intent already exists")


def record_user_action(
    db: AgentDependencies,
    request: TeachRequest,
) -> tuple[Action, GesturePattern, AgentSuggestion | None]:
    observation = db.repository.get(GestureObservation, request.observation_id)
    if observation is None or observation.user_id != request.user_id:
        raise ValueError("Observation not found for this user")
    if db.repository.observation_has_action(observation.id):
        raise ValueError("This observation already has a linked action")
    context = db.repository.get(Context, observation.context_id)
    if context is None:
        raise ValueError("Context not found")
    if request.action_type not in CONTEXT_INTENTS.get(context.activity, ()):
        raise ValueError("action_type is not allowed for this context")

    now = datetime.now(timezone.utc)
    action = Action(
        id=str(uuid4()),
        user_id=request.user_id,
        observation_id=observation.id,
        action_type=request.action_type,
        target=request.target,
        parameters=request.parameters,
        executed_by="USER",
        executed_at=now,
    )
    db.repository.add(action)
    db.repository.flush()

    # Bound the evidence so a long-established habit can still change. Agent
    # executions are never votes for the mapping that produced them.
    rows = db.repository.learning_evidence(
        request.user_id,
        observation.gesture_key,
        context.activity,
        now,
        LEARNING_WINDOW,
        MAX_LEARNING_ACTIONS,
    )

    evidence = summarize_evidence(rows, now, db.policy.recency_half_life_days)

    last_rejected_at = db.repository.last_rejection(
        request.user_id, observation.gesture_key, context.activity, evidence.intent
    )
    fresh_count = sum(
        last_rejected_at is None or utc(row.action.executed_at) > utc(last_rejected_at)
        for row in evidence.rows
    )
    rejection_cleared = (
        last_rejected_at is None or fresh_count >= db.policy.suggestion_threshold
    )

    pattern = db.repository.matching_memory(
        request.user_id, observation.gesture_key, context.activity, evidence.intent
    )

    if pattern is None:
        pattern = GesturePattern(
            id=str(uuid4()),
            user_id=request.user_id,
            gesture_key=observation.gesture_key,
            gesture_embedding=evidence.embedding,
            motion_type=evidence.latest_observation.motion_type,
            direction=evidence.latest_observation.direction,
            intent=evidence.intent,
            context_scope=context.activity,
            target=evidence.target,
            confidence=evidence.confidence,
            observation_count=evidence.count,
            auto_execute=False,
            status="CANDIDATE" if rejection_cleared else "REJECTED",
        )
        db.repository.add(pattern)
    else:
        pattern.gesture_embedding = evidence.embedding
        pattern.target = evidence.target
        pattern.confidence = evidence.confidence
        pattern.observation_count = evidence.count
        if pattern.status == "REJECTED" and rejection_cleared:
            pattern.status = "CANDIDATE"

    db.repository.flush()

    scope_patterns = db.repository.scope_memories(
        request.user_id, observation.gesture_key, context.activity
    )
    for item in scope_patterns:
        if item.status == "ACTIVE" and (
            not evidence.has_unique_winner or item.id != pattern.id
        ):
            item.status = "CANDIDATE"
            item.auto_execute = False

    eligible = (
        evidence.has_unique_winner
        and evidence.count >= db.policy.suggestion_threshold
        and rejection_cleared
        and pattern.status != "ACTIVE"
    )
    suggestion: AgentSuggestion | None = None
    for pending in db.repository.pending_suggestions(scope_patterns):
        if eligible and pending.gesture_pattern_id == pattern.id and suggestion is None:
            suggestion = pending
        else:
            db.repository.delete(pending)

    if eligible:
        reason = (
            f"{context.activity} 상황에서 최근 30일 내 최대 20건의 조작 중 "
            f"유사한 동작 후 '{action_label(evidence.intent)}' 행동이 "
            f"{evidence.count}회 관찰되었습니다."
        )
        if suggestion is None:
            suggestion = AgentSuggestion(
                id=str(uuid4()),
                user_id=request.user_id,
                gesture_pattern_id=pattern.id,
                suggested_intent=evidence.intent,
                reason=reason,
                confidence=evidence.confidence,
                status="PENDING",
            )
            db.repository.add(suggestion)
        else:
            suggestion.suggested_intent = evidence.intent
            suggestion.reason = reason
            suggestion.confidence = evidence.confidence

    db.repository.commit()
    return action, pattern, suggestion


def respond_to_suggestion(
    db: AgentDependencies,
    suggestion: AgentSuggestion,
    decision: str,
    modified_intent: str | None,
) -> tuple[AgentSuggestion, GesturePattern]:
    if suggestion.status != "PENDING":
        raise ValueError("Only pending suggestions can be answered")
    if decision not in {"ACCEPTED", "MODIFIED", "REJECTED"}:
        raise ValueError(f"Unsupported decision: {decision}")

    pattern = db.repository.get(GesturePattern, suggestion.gesture_pattern_id)
    if pattern is None:
        raise ValueError("Gesture pattern not found")

    if decision == "MODIFIED":
        if not modified_intent:
            raise ValueError("modified_intent is required for MODIFIED")
        check_intent_change(db, pattern, modified_intent, "modified_intent")

    suggestion.status = decision
    suggestion.responded_at = datetime.now(timezone.utc)

    if decision == "REJECTED":
        pattern.status = "REJECTED"
        pattern.auto_execute = False
        pattern.confidence = max(0.0, round(pattern.confidence - 0.20, 3))
    else:
        if decision == "MODIFIED":
            suggestion.modified_intent = modified_intent
            pattern.intent = modified_intent
        # Only one memory per gesture may auto-execute in a given context.
        db.repository.deactivate_other_memories(pattern)
        pattern.status = "ACTIVE"
        pattern.auto_execute = True
        pattern.confidence = max(pattern.confidence, db.policy.auto_execution_threshold)

    db.repository.commit()
    return suggestion, pattern
