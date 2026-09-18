from uuid import uuid4


from .dependencies import AgentDependencies
from ..domain.entities import Context, Execution, GestureObservation
from ..contracts import InferenceResult
from ..domain.action_catalog import action_label

from ..domain.gesture_encoder import cosine_similarity


from ..domain.inference import magnitude as execution_magnitude, score


def infer_intent(
    db: AgentDependencies, observation: GestureObservation, context: Context
) -> InferenceResult:
    # A detection error must not damage a valid action mapping. Temporarily
    # suppress similar detections in this user's activity using the event itself.
    accidental_embeddings = db.repository.accidental_embeddings(context, observation)
    if any(
        cosine_similarity(observation.gesture_embedding, item) >= 0.95
        for item in accidental_embeddings
    ):
        return InferenceResult(
            matched=False,
            reason="최근 우발적 동작으로 표시한 유사 모션은 5분간 실행하지 않습니다.",
        )
    scored = [
        (*score(observation, pattern), pattern)
        for pattern in db.repository.executable_memories(context, observation)
    ]
    if not scored:
        return InferenceResult(
            matched=False,
            reason="현재 상황에서 활성화된 개인 제스처 기억이 없습니다.",
        )

    scored = sorted(
        (item for item in scored if item[1] >= 0.85),
        key=lambda item: item[0],
        reverse=True,
    )
    if not scored:
        return InferenceResult(
            matched=False,
            reason="모션 특징이 승인된 기억과 충분히 유사하지 않아 실행하지 않았습니다.",
        )
    confidence, similarity, pattern = scored[0]
    if any(
        other.intent != pattern.intent and confidence - other_score < 0.08
        for other_score, _, other in scored[1:]
    ):
        return InferenceResult(
            matched=False,
            confidence=confidence,
            reason="서로 다른 의도의 점수가 비슷하여 실행하지 않았습니다.",
        )
    if confidence < db.policy.auto_execution_threshold:
        return InferenceResult(
            matched=False,
            intent=pattern.intent,
            target=pattern.target,
            confidence=confidence,
            reason=(
                f"유사한 기억을 찾았지만 자동 실행 기준 {db.policy.auto_execution_threshold:.2f}보다 "
                "확신도가 낮아 실행하지 않았습니다."
            ),
        )

    magnitude = execution_magnitude(pattern.intent, observation.amplitude)
    mode, status, error_message = db.execute_action(
        pattern.intent, pattern.target, magnitude
    )
    execution = Execution(
        id=str(uuid4()),
        user_id=observation.user_id,
        gesture_pattern_id=pattern.id,
        observation_id=observation.id,
        intent=pattern.intent,
        target=pattern.target,
        parameters={"magnitude": magnitude},
        confidence=confidence,
        execution_mode=mode,
        status=status,
        error_message=error_message,
    )
    db.repository.add(execution)
    db.repository.commit()

    scale_note = f" ({magnitude}단계)" if magnitude > 1 else ""
    return InferenceResult(
        matched=True,
        intent=pattern.intent,
        target=pattern.target,
        confidence=confidence,
        reason=(
            f"{context.activity} 맥락의 개인 기억과 {similarity:.0%} 유사하여 "
            f"'{action_label(pattern.intent)}'{scale_note} 의도로 해석했습니다."
        ),
        execution=execution,
    )
