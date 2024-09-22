from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, Token, TokenPayload
import uuid
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_phone(self, phone: str) -> Optional[User]:
        return self.db.query(User).filter(User.phone == phone).first()

    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, user: UserCreate) -> User:
        db_user = User(
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            hashed_password=self.get_password_hash(user.password),
            birth_date=user.birth_date,
            id_number=user.id_number,
            id_issue_date=user.id_issue_date,
            is_email_verified=False,
            is_phone_verified=False
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_email(username) or self.get_user_by_phone(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    def decode_token(self, token: str) -> Optional[TokenPayload]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            token_data = TokenPayload(**payload)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token_data

    async def register(self, user: UserCreate) -> Token:
        db_user = self.get_user_by_email(user.email)
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        db_user = self.get_user_by_phone(user.phone)
        if db_user:
            raise HTTPException(status_code=400, detail="Phone number already registered")
        
        new_user = self.create_user(user)
        access_token = self.create_access_token(data={"sub": str(new_user.id)})
        refresh_token = self.create_refresh_token(data={"sub": str(new_user.id)})
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    async def login(self, username: str, password: str) -> Token:
        user = self.authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = self.create_access_token(data={"sub": str(user.id)})
        refresh_token = self.create_refresh_token(data={"sub": str(user.id)})
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    async def refresh_token(self, refresh_token: str) -> Token:
        token_data = self.decode_token(refresh_token)
        user = self.get_user_by_id(uuid.UUID(token_data.sub))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = self.create_access_token(data={"sub": str(user.id)})
        new_refresh_token = self.create_refresh_token(data={"sub": str(user.id)})
        return Token(access_token=access_token, refresh_token=new_refresh_token, token_type="bearer")

    async def logout(self, token: str) -> bool:
        # Add the token to a blacklist in the database
        blacklisted_token = BlacklistedToken(token=token, blacklisted_on=datetime.utcnow())
        self.db.add(blacklisted_token)
        self.db.commit()
        return True

    async def change_password(self, user_id: uuid.UUID, old_password: str, new_password: str) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not self.verify_password(old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect old password")
        user.hashed_password = self.get_password_hash(new_password)
        self.db.commit()
        return True

    async def request_password_reset(self, email: str) -> str:
        user = self.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        reset_token = secrets.token_urlsafe()
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        self.db.commit()
        # Here you would typically send an email with the reset token
        return reset_token

    async def reset_password(self, reset_token: str, new_password: str) -> bool:
        user = self.db.query(User).filter(User.reset_token == reset_token).first()
        if not user or user.reset_token_expires < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        user.hashed_password = self.get_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        self.db.commit()
        return True

    async def verify_email(self, verification_token: str) -> bool:
        user = self.db.query(User).filter(User.email_verification_token == verification_token).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid verification token")
        user.is_email_verified = True
        user.email_verification_token = None
        self.db.commit()
        return True

    async def verify_phone(self, user_id: uuid.UUID, verification_code: str) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.phone_verification_code != verification_code:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        user.is_phone_verified = True
        user.phone_verification_code = None
        self.db.commit()
        return True

    async def generate_email_verification_token(self, user_id: uuid.UUID) -> str:
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        verification_token = secrets.token_urlsafe()
        user.email_verification_token = verification_token
        self.db.commit()
        # Here you would typically send an email with the verification token
        return verification_token

    async def generate_phone_verification_code(self, user_id: uuid.UUID) -> str:
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        user.phone_verification_code = verification_code
        self.db.commit()
        # Here you would typically send an SMS with the verification code
        return verification_code
