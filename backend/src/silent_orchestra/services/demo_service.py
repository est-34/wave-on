"""Legacy Session-based demo entry points."""

from ..modules.demo.adapters.repository import DemoRepository
from ..modules.demo.api import ensure_demo_user as ensure, reset_demo_user as reset
from ..modules.demo.application.use_cases import DEMO_USER_ID, DEMO_USER_NAME


def ensure_demo_user(db):
    return ensure(DemoRepository(db))


def reset_demo_user(db):
    return reset(DemoRepository(db))
