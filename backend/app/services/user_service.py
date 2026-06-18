from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserUpdate


class UserService:

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User | None:
        return db.get(User, user_id)

    @staticmethod
    def update_user(db: Session, user: User, update_data: UserUpdate) -> User:
        data = update_data.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
        return user
