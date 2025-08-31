from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
from app.database import get_db
from app.routers.permissions import require_role
from ..utils import hash_password
import secrets
import os
from datetime import date

router = APIRouter(prefix="/users", 
                   tags=["Users"])

@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def signup(
    user: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
    profile_image: UploadFile = File(None)
):
    # Validate confirm_password
    if user.password != user.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    # Check email uniqueness
    if user.email:
        email_query = select(models.User).where(models.User.email == user.email)
        result = await db.execute(email_query)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Generate username
    base_username = f"{user.first_name.lower()}_{user.last_name.lower()}"
    username = base_username
    while True:
        username_query = select(models.User).where(models.User.username == username)
        result = await db.execute(username_query)
        if not result.scalar_one_or_none():
            break
        username = f"{base_username}{secrets.token_hex(4)}"

    # Handle profile image
    profile_image_url = None
    if profile_image:
        file_path = f"Uploads/{profile_image.filename}"
        with open(file_path, "wb") as buffer:
            content = await profile_image.read()
            buffer.write(content)
        profile_image_url = f"/Uploads/{profile_image.filename}"

    # Create user
    hashed_password = hash_password(user.password)
    db_user = models.User(
        username=username,
        full_name=f"{user.first_name} {user.last_name}",
        email=user.email,
        password=hashed_password,
        region=user.region,
        district=user.district,
        constituency=user.county,
        sub_county=user.sub_county,
        parish=user.parish,
        village=user.village,
        interests=user.interests,
        occupation=user.occupation,
        bio=user.bio,
        political_interest=user.political_interest,
        community_role=user.community_role,
        notification_email=user.notifications.email,
        notification_sms=user.notifications.sms,
        notification_push=user.notifications.push,
        profile_image=profile_image_url,
        role=schemas.Role.CITIZEN,
        nin=f"NIN-temp-{username}",  
        gender="Unknown",
        date_of_birth=date(2000, 1, 1),
        phone_number="0000000000"
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    # Update nin with user ID
    db_user.nin = f"NIN{db_user.id}-{db_user.created_at.strftime('%Y%m%d%H%M%S')}"
    await db.commit()
    await db.refresh(db_user)

    return db_user

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def create_user(
    user: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(require_role([schemas.Role.ADMIN])),
    profile_image: UploadFile = File(None)
):
    if user.role != schemas.Role.CITIZEN and current_user.role != schemas.Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can assign non-citizen roles")

    # Check username uniqueness
    username_query = select(models.User).where(models.User.username == user.username)
    result = await db.execute(username_query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")

    # Check nin uniqueness
    nin_query = select(models.User).where(models.User.nin == user.nin)
    result = await db.execute(nin_query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="NIN already registered")

    # Handle profile image
    profile_image_url = None
    if profile_image:
        file_path = f"Uploads/{profile_image.filename}"
        with open(file_path, "wb") as buffer:
            content = await profile_image.read()
            buffer.write(content)
        profile_image_url = f"/Uploads/{profile_image.filename}"

    hashed_password = hash_password(user.password)
    db_user = models.User(
        username=user.username,
        full_name=f"{user.first_name} {user.last_name}",
        nin=user.nin,
        constituency=user.county,
        district=user.district,
        sub_county=user.sub_county,
        region=user.region,
        parish=user.parish,
        village=user.village,
        gender="Unknown",
        date_of_birth=date(2000, 1, 1),
        phone_number="0000000000",
        email=user.email,
        password=hashed_password,
        role=user.role,
        bio=user.bio,
        political_interest=user.political_interest,
        community_role=user.community_role,
        occupation=user.occupation,
        interests=user.interests,
        notification_email=user.notifications.email,
        notification_sms=user.notifications.sms,
        notification_push=user.notifications.push,
        profile_image=profile_image_url
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user