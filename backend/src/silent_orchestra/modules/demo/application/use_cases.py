from ..ports import DemoRepository
from ...identity.api import User

DEMO_USER_ID = "demo-user"
DEMO_USER_NAME = "수영"


def ensure_demo_user(db: DemoRepository) -> User:
    user = db.get(User, DEMO_USER_ID)
    if user is None:
        user = User(id=DEMO_USER_ID, name=DEMO_USER_NAME)
        db.add(user)
        db.commit()
    return user


def reset_demo_user(db: DemoRepository) -> tuple[User, dict[str, int]]:
    """Delete the demo user and recreate it in one transaction.

    Dependent rows go with it through ON DELETE CASCADE, so a failure anywhere
    rolls back to the previous state instead of leaving the demo half-erased.
    """
    try:
        deleted_counts = db.dependent_counts(DEMO_USER_ID)
        existing = db.get(User, DEMO_USER_ID)
        if existing is not None:
            db.delete(existing)
            db.flush()
        user = User(id=DEMO_USER_ID, name=DEMO_USER_NAME)
        db.add(user)
        db.commit()
        return user, deleted_counts
    except Exception:
        db.rollback()
        raise
