"""Legacy context entry point with the default OS adapter."""

from ..adapters import action_executor
from ..modules.agent.application.context_resolver import resolve_context as resolve


def resolve_context(activity, active_app):
    return resolve(activity, active_app, action_executor.active_window)
