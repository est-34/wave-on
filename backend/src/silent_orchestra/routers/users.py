from fastapi import APIRouter, Depends, Request, Response, status
from ..bootstrap import get_identity_repository as get_repository
from ..modules.identity import api
from ..schemas import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, request: Request, response: Response, db=Depends(get_repository)):
    user = api.create_user(payload=api.UserCreate(**payload.model_dump()), db=db)
    response.headers["Location"] = str(request.url_for("get_user", user_id=user.id))
    return user


@router.get("", response_model=list[UserRead])
def list_users(db=Depends(get_repository)):
    return api.list_users(db=db)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: str, db=Depends(get_repository)):
    return api.get_user(user_id=user_id, db=db)
