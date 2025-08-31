from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .. import models, schemas
from ..database import get_db
from ..utils import verify_password, hash_password
from .oauth2 import create_access_token
from fastapi_authlib import Auth, OAuth2ClientCredentials
from ..config import settings
from datetime import date
import secrets

router = APIRouter(prefix="/auth", tags=["Authentication"])

# OAuth2 clients
google_auth = Auth(
    provider="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    redirect_uri="http://localhost:8000/auth/google/callback"
)

linkedin_auth = Auth(
    provider="linkedin",
    client_id=settings.linkedin_client_id,
    client_secret=settings.linkedin_client_secret,
    redirect_uri="http://localhost:8000/auth/linkedin/callback"
)

@router.post("/login", response_model=schemas.Token)
async def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user_query = select(models.User).where(
        (models.User.username == user_credentials.username) |
        (models.User.nin == user_credentials.username) |
        (models.User.email == user_credentials.username)
    )
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/google/login")
async def google_login():
    return {"url": google_auth.get_authorization_url()}

@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    try:
        token = await google_auth.get_access_token(code)
        user_info = await google_auth.get_user_info(token)
        email = user_info.get("email")
        full_name = user_info.get("name", "Google User")

        # Check if user exists
        user_query = select(models.User).where(models.User.email == email)
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            base_username = full_name.lower().replace(" ", "_")
            username = base_username
            while True:
                username_query = select(models.User).where(models.User.username == username)
                result = await db.execute(username_query)
                if not result.scalar_one_or_none():
                    break
                username = f"{base_username}{secrets.token_hex(4)}"

            user = models.User(
                username=username,
                full_name=full_name,
                email=email,
                password=hash_password(secrets.token_hex(16)),  # Random password
                nin=f"NIN-temp-{username}",
                role=schemas.Role.CITIZEN,
                gender="Unknown",
                date_of_birth=date(2000, 1, 1),
                phone_number="0000000000",
                region="Unknown",
                district="Unknown",
                constituency="Unknown",
                sub_county="Unknown",
                parish="Unknown",
                village="Unknown",
                interests=[],
                notification_email=True,
                notification_sms=False,
                notification_push=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            user.nin = f"NIN{user.id}-{user.created_at.strftime('%Y%m%d%H%M%S')}"
            await db.commit()
            await db.refresh(user)

        access_token = create_access_token(data={"user_id": user.id})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/linkedin/login")
async def linkedin_login():
    return {"url": linkedin_auth.get_authorization_url()}

@router.get("/linkedin/callback")
async def linkedin_callback(code: str, db: AsyncSession = Depends(get_db)):
    try:
        token = await linkedin_auth.get_access_token(code)
        user_info = await linkedin_auth.get_user_info(token)
        email = user_info.get("email")
        full_name = user_info.get("localizedFirstName", "") + " " + user_info.get("localizedLastName", "LinkedIn User")

        # Check if user exists
        user_query = select(models.User).where(models.User.email == email)
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            base_username = full_name.lower().replace(" ", "_")
            username = base_username
            while True:
                username_query = select(models.User).where(models.User.username == username)
                result = await db.execute(username_query)
                if not result.scalar_one_or_none():
                    break
                username = f"{base_username}{secrets.token_hex(4)}"

            user = models.User(
                username=username,
                full_name=full_name,
                email=email,
                password=hash_password(secrets.token_hex(16)),  # Random password
                nin=f"NIN-temp-{username}",
                role=schemas.Role.CITIZEN,
                gender="Unknown",
                date_of_birth=date(2000, 1, 1),
                phone_number="0000000000",
                region="Unknown",
                district="Unknown",
                constituency="Unknown",
                sub_county="Unknown",
                parish="Unknown",
                village="Unknown",
                interests=[],
                notification_email=True,
                notification_sms=False,
                notification_push=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            user.nin = f"NIN{user.id}-{user.created_at.strftime('%Y%m%d%H%M%S')}"
            await db.commit()
            await db.refresh(user)

        access_token = create_access_token(data={"user_id": user.id})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))