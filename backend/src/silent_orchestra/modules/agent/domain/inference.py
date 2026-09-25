from .action_catalog import SCALABLE_INTENTS
from .entities import GestureObservation, GesturePattern
from .gesture_encoder import cosine_similarity


def magnitude(intent: str, amplitude: float | None) -> int:
    """How many times to repeat the key for a scalable intent (SPEC C-5): a
    bigger measured swipe means a bigger volume/zoom step. Fixed at 1 for
    simulated input (no amplitude) and for intents where "how much" has no
    meaning, so existing single-step behavior is unchanged for them."""
    if intent not in SCALABLE_INTENTS or amplitude is None:
        return 1
    return 1 + min(int(amplitude), 4)


def score(
    observation: GestureObservation, pattern: GesturePattern
) -> tuple[float, float]:
    """Return the pattern's confidence weighted by gesture shape, and the raw similarity."""
    similarity = cosine_similarity(
        observation.gesture_embedding, pattern.gesture_embedding
    )
    key_bonus = 1.0 if observation.gesture_key == pattern.gesture_key else 0.0
    shape_score = (0.20 * key_bonus) + (0.80 * max(similarity, 0.0))
    return round(pattern.confidence * shape_score, 3), similarity
