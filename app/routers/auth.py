from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from .. import  models, schemas, utils
from .import oauth2
from ..database import SessionLocal, engine, get_db

router = APIRouter(
    tags=["Authentication"]
)

#verify user credential during login
@router.post("/login", response_model=schemas.Token)

def login(user_credential: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credential.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credentials")
    if not utils.verify(user_credential.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credentials")
    
    #create JWT token
    access_token = oauth2.create_access_token(data = {"user_id": user.id})
    #return token
    return {"access_token": access_token, "token_type": "bearer"}


