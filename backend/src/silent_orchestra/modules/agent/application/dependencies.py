"""Request-scoped ports assembled by the composition root."""
from dataclasses import dataclass
from ....shared.policy import AgentPolicy
from ..ports import AgentRepository, ActionExecutor, ActiveWindow, UserLookup


@dataclass(frozen=True)
class AgentDependencies:
    repository: AgentRepository
    policy: AgentPolicy
    execute_action: ActionExecutor
    active_window: ActiveWindow
    require_user: UserLookup
