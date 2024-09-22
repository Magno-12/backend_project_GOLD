from sqlalchemy import Column, String, Date, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    birth_date = Column(Date, nullable=False)
    id_number = Column(String, unique=True, nullable=False)
    id_issue_date = Column(Date, nullable=False)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    is_email_verified = Column(Boolean(), default=False)
    is_phone_verified = Column(Boolean(), default=False)
    email_verification_token = Column(String, nullable=True)
    phone_verification_code = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
