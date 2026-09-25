"""Resolve the two supported activities from local application signals."""

from typing import Callable
from ..domain.action_catalog import TARGET_WINDOWS

TARGET_ACTIVITIES = {"powerpoint": "presentation", "media_player": "music"}


def resolve_context(
    activity: str | None,
    active_app: str | None,
    active_window: Callable[[], str | None],
) -> tuple[str, str]:
    """Explicit activity is a simulation override; auto mode never guesses."""
    window = active_app or active_window()
    if activity and activity != "auto":
        if activity not in TARGET_ACTIVITIES.values():
            raise ValueError("Unsupported activity")
        return activity, (window or "manual")[:100]
    if not window:
        raise ValueError(
            "Active application is unavailable; select a supported app or explicit simulation context"
        )
    matches = {
        TARGET_ACTIVITIES[target]
        for target, names in TARGET_WINDOWS.items()
        if any(name in window.casefold() for name in names)
    }
    if len(matches) != 1:
        raise ValueError(
            "Active application is unsupported or ambiguous; no activity was inferred"
        )
    return matches.pop(), window[:100]
