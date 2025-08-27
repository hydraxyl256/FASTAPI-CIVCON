from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from pydantic.types import conint
from typing import Annotated

#pydantic model
class PostBase(BaseModel):
    title_of_the_post: str
    content: str
    published: bool = True


#Our server response to creating user
class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True 

    


class PostCreate(PostBase):
    pass

#Our server response
class Post(PostBase):
    id: int
    created_at: datetime
    owner_id: int
    owner: UserOut

    class Config:
        from_attributes = True  


class PostLike(PostBase):
    post: Post
    like: int

    class Config:
        from_attributes = True  


#Creating user/ user registration
class CreateUser(BaseModel):
    email: EmailStr
    password: str

    
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

    
class TokenData(BaseModel):
    id: Optional[str] = None

class Vote(BaseModel):
    post_id: int
    dir: Annotated[int, conint(le=1)]




