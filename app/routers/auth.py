from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .. import models, schemas
from ..database import get_db
from ..utils import verify, hash  
from .oauth2 import create_access_token, get_current_user
from ..ug_locale import uga_locale
from ..config import settings
from datetime import date
import secrets
import httpx
from urllib.parse import urlencode

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Google OAuth2 endpoints
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

# LinkedIn OAuth2 endpoints
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"

@router.post("/login", response_model=schemas.Token)
async def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.User).filter(
            (models.User.username == user_credentials.username) |
            (models.User.nin == user_credentials.username) |
            (models.User.email == user_credentials.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify(user_credentials.password, user.password):  # FIXED: Use 'verify'
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/google/login")
async def google_login():
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": "http://localhost:8000/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    return {"url": f"{GOOGLE_AUTH_URL}?{urlencode(params)}"}

@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        try:
            # Exchange code for token
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": "http://localhost:8000/auth/google/callback",
                    "grant_type": "authorization_code"
                }
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get("access_token")

            # Get user info
            user_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_response.raise_for_status()
            user_info = user_response.json()

            email = user_info.get("email")
            if not email:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No email found in Google profile")

            full_name = user_info.get("name", "Google User")

            result = await db.execute(select(models.User).filter_by(email=email))
            user = result.scalar_one_or_none()

            if not user:
                base_username = full_name.lower().replace(" ", "_")
                username = base_username
                while True:
                    result = await db.execute(select(models.User).filter_by(username=username))
                    if not result.scalar_one_or_none():
                        break
                    username = f"{base_username}{secrets.token_hex(4)}"

                user = models.User(
                    username=username,
                    full_name=full_name,
                    email=email,
                    password=hash(secrets.token_hex(16)),  # FIXED: Use 'hash'
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
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/linkedin/login")
async def linkedin_login():
    params = {
        "client_id": settings.linkedin_client_id,
        "redirect_uri": "http://localhost:8000/auth/linkedin/callback",
        "response_type": "code",
        "scope": "profile email openid",
        "state": secrets.token_hex(16)
    }
    return {"url": f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"}

@router.get("/linkedin/callback")
async def linkedin_callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        try:
            # Exchange code for token
            token_response = await client.post(
                LINKEDIN_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.linkedin_client_id,
                    "client_secret": settings.linkedin_client_secret,
                    "redirect_uri": "http://localhost:8000/auth/linkedin/callback",
                    "grant_type": "authorization_code"
                }
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get("access_token")

            # Get user info
            user_response = await client.get(
                LINKEDIN_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_response.raise_for_status()
            user_info = user_response.json()

            email = user_info.get("email")
            if not email:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No email found in LinkedIn profile")

            full_name = f"{user_info.get('given_name', '')} {user_info.get('family_name', 'LinkedIn User')}".strip()

            result = await db.execute(select(models.User).filter_by(email=email))
            user = result.scalar_one_or_none()

            if not user:
                base_username = full_name.lower().replace(" ", "_")
                username = base_username
                while True:
                    result = await db.execute(select(models.User).filter_by(username=username))
                    if not result.scalar_one_or_none():
                        break
                    username = f"{base_username}{secrets.token_hex(4)}"

                user = models.User(
                    username=username,
                    full_name=full_name,
                    email=email,
                    password=hash(secrets.token_hex(16)),  # FIXED: Use 'hash'
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
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/complete-profile", response_model=schemas.UserOut)
async def complete_profile(
    user_data: schemas.UserCreate,
    current_user: schemas.UserOut = Depends(get_current_user),  # Assuming get_current_user is defined in oauth2.py or permissions
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(models.User).filter_by(id=current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    district = uga_locale.find_district_by_id(user_data.district)
    if not district:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid district ID: {user_data.district}")

    county = uga_locale.find_county_by_id(user_data.county)
    if not county or county["district"] != user_data.district:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid county ID: {user_data.county}")

    subcounty = uga_locale.find_subcounty_by_id(user_data.sub_county)
    if not subcounty or subcounty["county"] != user_data.county:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sub-county ID: {user_data.sub_county}")

    parish = uga_locale.find_parish_by_id(user_data.parish)
    if not parish or parish["subcounty"] != user_data.sub_county:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid parish ID: {user_data.parish}")

    user.region = user_data.region
    user.district = district["name"]
    user.constituency = county["name"]
    user.sub_county = subcounty["name"]
    user.parish = parish["name"]
    user.village = user_data.village
    user.interests = user_data.interests
    user.occupation = user_data.occupation
    user.bio = user_data.bio
    user.political_interest = user_data.political_interest
    user.community_role = user_data.community_role
    # Safe access for notifications (assuming nested model)
    user.notification_email = user_data.notifications.email if hasattr(user_data.notifications, 'email') else False
    user.notification_sms = user_data.notifications.sms if hasattr(user_data.notifications, 'sms') else False
    user.notification_push = user_data.notifications.push if hasattr(user_data.notifications, 'push') else False

    await db.commit()
    await db.refresh(user)
    return user