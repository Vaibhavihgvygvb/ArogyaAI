from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import UserService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user email",
)
def update_my_profile(
    update_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.update_user(db, current_user, update_data)
