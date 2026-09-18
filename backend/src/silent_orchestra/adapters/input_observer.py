"""Compatibility alias for the module-owned adapter."""
import sys
from ..modules.agent.adapters import input_observer as implementation

sys.modules[__name__] = implementation
