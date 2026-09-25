from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from .entities import Action, GestureObservation

LEARNING_WINDOW = timedelta(days=30)
MAX_LEARNING_ACTIONS = 20


@dataclass(frozen=True)
class LearningEvidence:
    intent: str
    count: int
    rows: list[EvidenceRow]
    has_unique_winner: bool
    confidence: float
    target: str
    latest_observation: GestureObservation
    embedding: list[float]


def utc(value: datetime) -> datetime:
    # SQLite returns naive values even for DateTime(timezone=True).
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def _recency_weight(executed_at: datetime, now: datetime, half_life: float) -> float:
    """Exponential decay so a habit built from old evidence stays less certain
    than the same count built from recent evidence, even inside the 30-day
    learning window (SPEC C-2 gap: raw counts alone treat both the same)."""
    age_days = (now - utc(executed_at)).total_seconds() / 86400
    return 0.5 ** (max(age_days, 0.0) / half_life)


def _confidence(winner_count: int, total_count: int, recency_factor: float) -> float:
    consistency = winner_count / total_count
    score = 0.35 + (0.10 * min(winner_count, 5)) + (0.22 * consistency)
    return round(min(0.99, score * recency_factor), 3)


def _ranked_by_recency(
    rows, now: datetime, half_life: float
) -> list[tuple[str, float]]:
    """Vote per intent weighted by how recent each supporting action is, most
    weight first (SPEC C-2 residual): a raw count alone lets an intent that was
    dominant early in the 30-day window keep outranking a newer, smaller but
    more recent run of a different intent for as long as the window holds
    both. ``_recency_weight`` already discounts old evidence in confidence;
    this reuses the same weight to decide *who* is currently the habit."""
    scores: dict[str, float] = {}
    for row in rows:
        scores[row.action.action_type] = scores.get(
            row.action.action_type, 0.0
        ) + _recency_weight(row.action.executed_at, now, half_life)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def summarize_evidence(
    rows: list[EvidenceRow], now: datetime, half_life: float
) -> LearningEvidence:
    """Reduce recent action rows to the current winning habit."""
    raw_counts = Counter(row.action.action_type for row in rows)
    ranked = _ranked_by_recency(rows, now, half_life)
    intent, score = ranked[0]
    winning_rows = [row for row in rows if row.action.action_type == intent]
    count = raw_counts[intent]
    has_unique_winner = len(ranked) == 1 or not math.isclose(
        score, ranked[1][1], rel_tol=1e-6, abs_tol=1e-6
    )
    recency_factor = sum(
        _recency_weight(row.action.executed_at, now, half_life) for row in winning_rows
    ) / len(winning_rows)
    latest_observation = winning_rows[0].observation
    embedding_size = len(latest_observation.gesture_embedding)
    embeddings = [
        row.observation.gesture_embedding
        for row in winning_rows
        if len(row.observation.gesture_embedding) == embedding_size
    ]
    return LearningEvidence(
        intent=intent,
        count=count,
        rows=winning_rows,
        has_unique_winner=has_unique_winner,
        confidence=_confidence(count, len(rows), recency_factor),
        # Rows are newest first, so Counter's insertion order breaks target
        # ties using the most recent target.
        target=Counter(row.action.target for row in winning_rows).most_common(1)[0][0],
        latest_observation=latest_observation,
        embedding=[
            round(sum(values) / len(embeddings), 6)
            for values in zip(*embeddings, strict=True)
        ],
    )


@dataclass(frozen=True)
class EvidenceRow:
    action: Action
    observation: GestureObservation
