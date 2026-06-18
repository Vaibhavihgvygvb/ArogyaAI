from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_access_token


class AuthService:

    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        existing = db.scalar(select(User).where(User.email == user_data.email))
        if existing:
            raise ValueError("Email already registered")
        user = User(
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            role=user_data.role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User | None:
        user = db.scalar(select(User).where(User.email == email))
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_tokens(user: User) -> dict:
        token_data = {"sub": str(user.id), "role": user.role.value}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
        }

    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict | None:
        payload = decode_access_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None
        token_data = {"sub": payload["sub"], "role": payload["role"]}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": refresh_token,
        }

    @staticmethod
    def change_password(db: Session, user: User, old_password: str, new_password: str) -> bool:
        if not verify_password(old_password, user.hashed_password):
            return False
        user.hashed_password = hash_password(new_password)
        db.commit()
        return True
