from uuid import uuid4
from ....shared.errors import ApplicationError
from .dependencies import AgentDependencies
from ..domain.entities import Context, GestureObservation, AgentSuggestion, Execution
from ..contracts import (
    ObserveRequest,
    TeachRequest,
    SuggestionResponseRequest,
    FeedbackCreate,
    InferenceResult,
)
from .confirmation import apply_confirmation, is_confirm_gesture
from .feedback_service import record_feedback
from .context_resolver import resolve_context
from ..domain.gesture_encoder import encode_gesture, gesture_key
from .intent_reasoner import infer_intent
from .pattern_learning import record_user_action, respond_to_suggestion


def _get_or_404(db: AgentDependencies, model: type, key: str, label: str):
    instance = db.repository.get(model, key)
    if instance is None:
        raise ApplicationError(status_code=404, detail=f"{label} not found")
    return instance


def observe(payload: ObserveRequest, db: AgentDependencies) -> dict:
    db.require_user(payload.user_id)
    try:
        activity, active_app = resolve_context(
            payload.context.activity, payload.context.active_app, db.active_window
        )
    except ValueError as exc:
        raise ApplicationError(status_code=400, detail=str(exc)) from exc
    context = Context(
        id=str(uuid4()),
        user_id=payload.user_id,
        active_app=active_app,
        activity=activity,
        space=payload.context.space,
        device=payload.context.device,
    )
    observation = GestureObservation(
        id=str(uuid4()),
        user_id=payload.user_id,
        context_id=context.id,
        gesture_key=gesture_key(payload.gesture.motion_type, payload.gesture.direction),
        gesture_embedding=payload.gesture.embedding
        or encode_gesture(
            payload.gesture.motion_type,
            payload.gesture.direction,
            payload.gesture.duration_ms,
            payload.gesture.speed,
            payload.gesture.amplitude,
        ),
        motion_type=payload.gesture.motion_type,
        direction=payload.gesture.direction,
        duration_ms=payload.gesture.duration_ms,
        speed=payload.gesture.speed,
        amplitude=payload.gesture.amplitude,
        frame_stored=False,
    )
    db.repository.add_all([context, observation])
    db.repository.commit()

    # A reserved confirm gesture never becomes a learnable candidate itself -
    # it only answers whatever suggestion or unrated execution is waiting.
    if is_confirm_gesture(observation.gesture_key):
        matched, reason, intent = apply_confirmation(
            db, payload.user_id, activity, observation.gesture_key
        )
        inference = InferenceResult(matched=matched, intent=intent, reason=reason)
    elif payload.attempt_inference:
        inference = infer_intent(db, observation, context)
    else:
        inference = InferenceResult(matched=False, reason="추론을 요청하지 않았습니다.")
    return {"context": context, "observation": observation, "inference": inference}


def teach(payload: TeachRequest, db: AgentDependencies) -> dict:
    db.require_user(payload.user_id)
    try:
        action, pattern, suggestion = record_user_action(db, payload)
    except ValueError as exc:
        raise ApplicationError(status_code=400, detail=str(exc)) from exc
    return {
        "action": action,
        "pattern": pattern,
        "suggestion": suggestion,
        "progress_current": min(
            pattern.observation_count, db.policy.suggestion_threshold
        ),
        "progress_required": db.policy.suggestion_threshold,
    }


def list_suggestions(
    user_id: str,
    status: str | None = None,
    *,
    db: AgentDependencies,
):
    db.require_user(user_id)
    return db.repository.list_suggestions(user_id, status)


def respond_suggestion(
    suggestion_id: str,
    payload: SuggestionResponseRequest,
    *,
    db: AgentDependencies,
) -> dict:
    suggestion = _get_or_404(db, AgentSuggestion, suggestion_id, "Suggestion")
    try:
        updated, pattern = respond_to_suggestion(
            db, suggestion, payload.decision, payload.modified_intent
        )
    except ValueError as exc:
        raise ApplicationError(status_code=400, detail=str(exc)) from exc
    return {"suggestion": updated, "pattern": pattern}


def list_memories(
    user_id: str,
    gesture_key: str | None = None,
    context_scope: str | None = None,
    *,
    db: AgentDependencies,
):
    db.require_user(user_id)
    return db.repository.list_memories(
        user_id, gesture_key, context_scope,
        threshold=db.policy.auto_execution_threshold,
    )


def submit_feedback(
    execution_id: str,
    payload: FeedbackCreate,
    *,
    db: AgentDependencies,
) -> dict:
    execution = _get_or_404(db, Execution, execution_id, "Execution")
    try:
        feedback, pattern = record_feedback(
            db,
            execution,
            payload.user_id,
            payload.feedback_type,
            payload.corrected_intent,
        )
    except ValueError as exc:
        raise ApplicationError(status_code=400, detail=str(exc)) from exc
    return {"feedback": feedback, "pattern": pattern}


def dashboard(user_id: str, db: AgentDependencies):
    db.require_user(user_id)
    return db.repository.dashboard(
        user_id, suggestion_threshold=db.policy.suggestion_threshold
    )
