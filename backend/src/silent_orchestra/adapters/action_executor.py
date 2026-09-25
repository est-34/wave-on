"""Compatibility alias for the module-owned adapter."""
import sys
from ..modules.agent.adapters import action_executor as implementation

sys.modules[__name__] = implementation
