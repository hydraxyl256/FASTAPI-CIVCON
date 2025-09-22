from typing import Optional
from functools import partial
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .. import models, schemas
from ..database import get_db
from ..routers.permissions import require_role
from ..utils import hash
from ..ug_locale import uga_locale
import secrets
import os
from datetime import date
import logging

router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger(__name__)

@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def signup(
    signup_data: schemas.UserSignup,
    db: AsyncSession = Depends(get_db),
    profile_image: Optional[UploadFile] = None
):
    user = signup_data.user
    logger.debug(f"Received signup data: {user.dict()}")
    # Validate passwords
    if user.password != user.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    # Validate email uniqueness
    if user.email:
        email_query = select(models.User).where(models.User.email == user.email)
        result = await db.execute(email_query)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Validate location fields
    district = uga_locale.find_district_by_id(user.district)
    if not district or "name" not in district:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid district ID: {user.district}")

    county = uga_locale.find_county_by_id(user.constituency)
    if not county or "name" not in county or county["district"] != user.district:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid constituency ID: {user.constituency}")

    subcounty = uga_locale.find_subcounty_by_id(user.sub_county)
    if not subcounty or "name" not in subcounty or subcounty["county"] != user.constituency:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sub-county ID: {user.sub_county}")

    parish = uga_locale.find_parish_by_id(user.parish)
    if not parish or "name" not in parish or parish["subcounty"] != user.sub_county:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid parish ID: {user.parish}")

    # Use provided username
    username = user.username
    username_query = select(models.User).where(models.User.username == username)
    result = await db.execute(username_query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")

    # Handle profile image
    profile_image_url = None
    if profile_image and profile_image.filename:
        if not profile_image.content_type.startswith('image/'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")
        os.makedirs("Uploads", exist_ok=True)
        file_path = f"Uploads/{secrets.token_hex(8)}_{profile_image.filename}"
        with open(file_path, "wb") as buffer:
            content = await profile_image.read()
            buffer.write(content)
        profile_image_url = f"/Uploads/{os.path.basename(file_path)}"

    # Create user
    hashed_password = hash(user.password)
    db_user = models.User(
        username=username,
        full_name=f"{user.first_name} {user.last_name}",
        email=user.email,
        password=hashed_password,
        region=user.region,
        district=district["name"],
        constituency=county["name"],
        sub_county=subcounty["name"],
        parish=parish["name"],
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
        gender=user.gender,
        date_of_birth=user.date_of_birth or date(2000, 1, 1),
        phone_number=user.phone_number
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    # Update nin
    db_user.nin = f"NIN{db_user.id}-{db_user.created_at.strftime('%Y%m%d%H%M%S')}"
    await db.commit()
    await db.refresh(db_user)

    return db_user

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def create_user(
    user: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(lambda: require_role([schemas.Role.ADMIN])),
    profile_image: Optional[UploadFile] = None
):
    logger.debug(f"Received create_user data: {user.dict()}")
    if user.role != schemas.Role.CITIZEN and current_user.role != schemas.Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can assign non-citizen roles")

    # Validate passwords
    if user.password != user.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    # Validate email uniqueness
    if user.email:
        email_query = select(models.User).where(models.User.email == user.email)
        result = await db.execute(email_query)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Validate location fields
    district = uga_locale.find_district_by_id(user.district)
    if not district or "name" not in district:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid district ID: {user.district}")

    county = uga_locale.find_county_by_id(user.constituency)
    if not county or "name" not in county or county["district"] != user.district:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid constituency ID: {user.constituency}")

    subcounty = uga_locale.find_subcounty_by_id(user.sub_county)
    if not subcounty or "name" not in subcounty or subcounty["county"] != user.constituency:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sub-county ID: {user.sub_county}")

    parish = uga_locale.find_parish_by_id(user.parish)
    if not parish or "name" not in parish or parish["subcounty"] != user.sub_county:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid parish ID: {user.parish}")

    # Check username uniqueness
    username_query = select(models.User).where(models.User.username == user.username)
    result = await db.execute(username_query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")

    # Handle profile image
    profile_image_url = None
    if profile_image and profile_image.filename:
        if not profile_image.content_type.startswith('image/'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")
        os.makedirs("Uploads", exist_ok=True)
        file_path = f"Uploads/{secrets.token_hex(8)}_{profile_image.filename}"
        with open(file_path, "wb") as buffer:
            content = await profile_image.read()
            buffer.write(content)
        profile_image_url = f"/Uploads/{os.path.basename(file_path)}"

    # Create user
    hashed_password = hash(user.password)
    db_user = models.User(
        username=user.username,
        full_name=f"{user.first_name} {user.last_name}",
        email=user.email,
        password=hashed_password,
        region=user.region,
        district=district["name"],
        constituency=county["name"],
        sub_county=subcounty["name"],
        parish=parish["name"],
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
        role=user.role or schemas.Role.CITIZEN,
        nin=f"NIN-temp-{user.username}",
        gender=user.gender or "Unknown",
        date_of_birth=user.date_of_birth or date(2000, 1, 1),
        phone_number=user.phone_number or "0000000000"
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    # Update nin
    db_user.nin = f"NIN{db_user.id}-{db_user.created_at.strftime('%Y%m%d%H%M%S')}"
    await db.commit()
    await db.refresh(db_user)

    return db_user