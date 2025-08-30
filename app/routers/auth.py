from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .. import models, schemas, utils
from ..routers import oauth2
from ..database import get_db
from ..utils import verify_password
from ..routers.oauth2 import create_access_token

router = APIRouter(
    tags=["Authentication"]
)


@router.post("/", response_model=schemas.Token)
async def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user_query = select(models.User).where(
        (models.User.nin == user_credentials.username) | (models.User.email == user_credentials.username)
    )
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}







# @router.post("/login", response_model=schemas.Token)
# async def login(
#     user_credentials: OAuth2PasswordRequestForm = Depends(),
#     db: AsyncSession = Depends(get_db)
# ):
#     user_query = select(models.User).where(models.User.email == user_credentials.username)
#     user_result = await db.execute(user_query)
#     user = user_result.scalar_one_or_none()
#     if not user or not utils.verify(user_credentials.password, user.password):
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

#     access_token = oauth2.create_access_token(data={"user_id": user.id})
#     return {"access_token": access_token, "token_type": "bearer"}

