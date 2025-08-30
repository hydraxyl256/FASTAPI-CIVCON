from pydantic import BaseModel, EmailStr
from datetime import datetime, date
from typing import Optional, List, Annotated, Union
from pydantic.types import conint
from enum import Enum


class PostBase(BaseModel):
    title_of_the_post: str
    content: str
    published: bool = True
    category_ids: Optional[List[int]] = []  # List of category IDs for post categorization
    group_id: Optional[int] = None  # ID of the group the post belongs to (if any)



class Role(str, Enum):
    CITIZEN = "citizen"
    MP = "mp"
    ADMIN = "admin"
    JOURNALIST = "journalist"

class CreateUser(BaseModel):
    username: str
    full_name: str
    nin: str
    constituency: str
    district: str
    sub_county: str
    gender: str
    date_of_birth: date
    phone_number: str
    email: Optional[EmailStr] = None
    password: str
    role: Role = Role.CITIZEN  # Default to citizen


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    nin: str
    constituency: str
    district: str
    sub_county: str
    gender: str
    date_of_birth: date
    phone_number: str
    email: Optional[EmailStr]
    created_at: datetime
    role: Role
    is_active: bool

    class Config:
        from_attributes = True



class MessageCreate(BaseModel):
    recipient_id: int
    content: str

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    content: str
    created_at: datetime
    class Config:
        from_attributes = True

class LiveFeedCreate(BaseModel):
    title: str
    stream_url: str
    description: Optional[str] = None

class LiveFeedResponse(BaseModel):
    id: int
    title: str
    stream_url: str
    description: Optional[str]
    created_at: datetime
    journalist_id: int
    class Config:
        from_attributes = True



class PostCreate(PostBase):
    pass

class Post(PostBase):
    id: int
    created_at: datetime
    owner_id: int
    view_count: int  # For trending
    owner: UserOut
    categories: List['CategoryResponse']  # Categories associated with the post

    class Config:
        from_attributes = True

class PostLike(BaseModel):
    post: Post
    like: int
    comment_count: int

    class Config:
        from_attributes = True





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

class SearchResponse(BaseModel):
    users: List[UserOut]
    posts: List[Post]
    comments: List['CommentResponse']

class CommentBase(BaseModel):
    content: str

class CommentUpdate(BaseModel):
    content: str

class CommentResponse(CommentBase):
    id: int
    created_at: datetime
    post_id: int
    user_id: int
    media_url: Optional[str]
    user: UserOut

    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class GroupResponse(GroupBase):
    id: int
    created_at: datetime
    owner_id: int
    owner: UserOut
    member_count: int  # Number of members in the group

    class Config:
        from_attributes = True


class NotificationBase(BaseModel):
    message: str
    is_read: bool = False
    post_id: Optional[int] = None
    group_id: Optional[int] = None

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    created_at: datetime
    user: UserOut

    class Config:
        from_attributes = True

class NotificationListResponse(BaseModel):
    data: List[NotificationResponse]
    pagination: dict