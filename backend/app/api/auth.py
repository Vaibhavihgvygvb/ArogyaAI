from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token, ChangePasswordRequest, RefreshTokenRequest
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Email already registered"},
    },
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        return AuthService.register_user(db, user_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/login",
    response_model=Token,
    summary="Login with email and password",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid email or password"},
    },
)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = AuthService.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    tokens = AuthService.create_tokens(user)
    return tokens


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token using a valid refresh token",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid or expired refresh token"},
    },
)
def refresh(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    tokens = AuthService.refresh_access_token(request.refresh_token)
    if not tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    return tokens


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password for authenticated user",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid current password"},
    },
)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    success = AuthService.change_password(db, current_user, request.old_password, request.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid current password")
    return {"message": "Password changed successfully"}
