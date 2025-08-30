from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .. import models, schemas, utils
from ..database import get_db
from ..routers.permissions import require_role
from ..utils import hash_password

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db), current_user: schemas.UserOut = Depends(require_role([schemas.Role.ADMIN]))):
    if user.role != schemas.Role.CITIZEN and current_user.role != schemas.Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can assign non-citizen roles")

    user_query = select(models.User).where(models.User.nin == user.nin)
    result = await db.execute(user_query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="NIN already registered")

    hashed_password = hash_password(user.password)
    db_user = models.User(
        full_name=user.full_name,
        nin=user.nin,
        constituency=user.constituency,
        district=user.district,
        sub_county=user.sub_county,
        gender=user.gender,
        date_of_birth=user.date_of_birth,
        phone_number=user.phone_number,
        email=user.email,
        password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.get("/{id}", response_model=schemas.UserOut)
async def get_user(id: int, db: AsyncSession = Depends(get_db)):
    user_query = select(models.User).where(models.User.id == id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {id} does not exist"
        )
    return user


