from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .. import schemas, models
from ..database import get_db
from ..config import settings
from datetime import datetime, timedelta
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str, credentials_exception: HTTPException):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id = payload.get("user_id")
        if id is None:
            raise credentials_exception
        token_data = schemas.TokenData(id=str(id))
        return token_data
    except JWTError:
        raise credentials_exception

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_access_token(token, credentials_exception)
    user_query = select(models.User).where(models.User.id == int(token_data.id))
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return schemas.UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at
    )




# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from jose import JWTError, jwt
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from .. import schemas, models
# from ..database import get_db
# from ..config import settings
# from datetime import datetime, timedelta
# from typing import Optional

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# SECRET_KEY = settings.secret_key
# ALGORITHM = settings.algorithm
# ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# # Create access token for the user
# def create_access_token(data: dict):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# # Verify access token for the user
# def verify_access_token(token: str, credentials_exception: HTTPException):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         id = payload.get("user_id")
#         if id is None:
#             raise credentials_exception
#         token_data = schemas.TokenData(id=str(id))
#         return token_data
#     except JWTError:
#         raise credentials_exception

# # Get current user
# async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )

#     token_data = verify_access_token(token, credentials_exception)
#     user_query = select(models.User).where(models.User.id == int(token_data.id))
#     user_result = await db.execute(user_query)
#     user = user_result.scalar_one_or_none()
    
#     if user is None:
#         raise credentials_exception
    
#     return schemas.UserOut(
#         id=user.id,
#         username=user.username,
#         email=user.email,
#         created_at=user.created_at
#     )










# # from fastapi import Depends, HTTPException, status
# # from fastapi.security import OAuth2PasswordBearer
# # from jose import JWTError, jwt
# # from .. import schemas, database, models
# # from datetime import datetime, timedelta
# # from typing import Optional
# # from sqlalchemy.orm import session
# # from ..database import get_db
# # from ..config import settings



# # oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# # SECRET_KEY = settings.secret_key
# # ALGORITHM = settings.algorithm
# # ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


# # #create access token for the user
# # def create_access_token(data: dict):

# #     to_encode = data.copy()
# #     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
# #     to_encode.update({"exp": expire})
# #     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  
# #     return encoded_jwt


# # #verify access token for the user
# # def verify_access_token(token: str, credentials_exception: HTTPException):

# #     try:
# #         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
# #         id = payload.get("user_id")
# #         if id is None:
# #             raise credentials_exception
        
# #         token_data = schemas.TokenData(id=str(id))  

# #         return token_data  
    
# #     except JWTError:
# #         raise credentials_exception

# # def get_current_user(token: str = Depends(oauth2_scheme), db: session = Depends(get_db)):

# #     credentials_exception = HTTPException(
# #         status_code=status.HTTP_401_UNAUTHORIZED,
# #         detail="Could not validate credentials",
# #         headers={"WWW-Authenticate": "Bearer"},
# #     )

# #     token =  verify_access_token(token, credentials_exception)
# #     user = db.query(models.User).filter(models.User.id == token.id).first()
    
# #     return user