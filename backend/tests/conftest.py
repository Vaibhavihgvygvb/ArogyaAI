import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.cache.deps import set_cache_provider, reset_cache_provider
from app.cache.providers.memory import MemoryCacheProvider
from app.core.config import settings
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.core.security import hash_password, create_access_token
from app.models.enums import UserRole, JobStatus, JobType
from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.job import Job

TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    settings.RATE_LIMIT_ENABLED = False
    set_cache_provider(MemoryCacheProvider())
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def reset_cache():
    from app.cache.deps import get_cache_provider
    yield
    try:
        get_cache_provider().clear()
    except Exception:
        pass


@pytest.fixture
def db():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def doctor_token(db: Session) -> str:
    user = User(
        email="doctor@test.com",
        hashed_password=hash_password("testpass123"),
        role=UserRole.DOCTOR,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token({"sub": str(user.id), "role": user.role.value})


@pytest.fixture
def patient_token(db: Session) -> str:
    user = User(
        email="patient@test.com",
        hashed_password=hash_password("testpass123"),
        role=UserRole.PATIENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token({"sub": str(user.id), "role": user.role.value})


@pytest.fixture
def admin_token(db: Session) -> str:
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("testpass123"),
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token({"sub": str(user.id), "role": user.role.value})


@pytest.fixture
def doctor_with_profile(db: Session) -> str:
    user = User(
        email="doctor_profile@test.com",
        hashed_password=hash_password("testpass123"),
        role=UserRole.DOCTOR,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    doctor = Doctor(
        user_id=user.id,
        full_name="Dr Test",
        email=user.email,
        phone_number="1111111111",
        specialization="Cardiology",
        clinic_name="Test Clinic",
    )
    db.add(doctor)
    db.commit()

    return create_access_token({"sub": str(user.id), "role": user.role.value})


@pytest.fixture
def patient_with_profile(db: Session) -> str:
    user = User(
        email="patient_profile@test.com",
        hashed_password=hash_password("testpass123"),
        role=UserRole.PATIENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    patient = Patient(
        user_id=user.id,
        full_name="Pat Test",
        phone_number="2222222222",
        gender="female",
    )
    db.add(patient)
    db.commit()

    return create_access_token({"sub": str(user.id), "role": user.role.value})
