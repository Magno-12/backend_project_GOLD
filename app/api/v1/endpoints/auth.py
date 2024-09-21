from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from dependency_injector.wiring import inject, Provide
from datetime import date
from app.core.container import Container
from app.schemas.user import UserCreate, UserLogin, Token
from app.services.auth_service import AuthService
from app.core.config import is_feature_enabled

router = APIRouter()

@router.post("/register", response_model=Token)
@inject
async def register(
    user: UserCreate,
    auth_service: AuthService = Depends(Provide[Container.auth_service])
):
    # Check age restriction
    today = date.today()
    age = today.year - user.birth_date.year - ((today.month, today.day) < (user.birth_date.month, user.birth_date.day))
    if age < 18:
        raise HTTPException(status_code=400, detail="User must be 18 years or older")

    # Check if email verification feature is enabled
    email_verification_enabled = is_feature_enabled("email-verification", {"key": user.email or user.phone})

    return await auth_service.register(user, email_verification_enabled)

@router.post("/login", response_model=Token)
@inject
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(Provide[Container.auth_service])
):
    return await auth_service.authenticate(form_data.username, form_data.password)

@router.post("/logout")
@inject
async def logout(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(Provide[Container.auth_service])
):
    await auth_service.logout(token)
    return {"message": "Successfully logged out"}

@router.post("/password-reset-request")
@inject
async def password_reset_request(
    email: str,
    auth_service: AuthService = Depends(Provide[Container.auth_service])
):
    await auth_service.request_password_reset(email)
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/password-reset")
@inject
async def password_reset(
    token: str,
    new_password: str,
    auth_service: AuthService = Depends(Provide[Container.auth_service])
):
    await auth_service.reset_password(token, new_password)
    return {"message": "Password has been reset successfully"}
