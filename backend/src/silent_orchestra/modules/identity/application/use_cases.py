from uuid import uuid4
from ....shared.errors import ApplicationError
from ..ports import IdentityRepository as Repository
from ..domain.entities import User
from ..contracts import UserCreate


def create_user(payload: UserCreate, db: Repository) -> User:
    user_id = payload.id or str(uuid4())
    if db.get(User, user_id) is not None:
        raise ApplicationError(status_code=409, detail="User id already exists")
    user = User(id=user_id, name=payload.name)
    db.add(user)
    db.commit()
    return user


def list_users(db: Repository) -> list[User]:
    return db.list_users()


def get_user(user_id: str, db: Repository) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise ApplicationError(status_code=404, detail="User not found")
    return user
