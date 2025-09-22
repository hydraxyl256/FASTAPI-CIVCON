from pydantic import BaseModel, EmailStr
from datetime import datetime, date
from typing import Optional, List, Annotated, Union
from pydantic.types import conint
from enum import Enum


class PostBase(BaseModel):
    title_of_the_post: str
    content: str
    published: bool = True
    category_ids: Optional[List[int]] = []
    group_id: Optional[int] = None


class Role(str, Enum):
    CITIZEN = "citizen"
    MP = "mp"
    ADMIN = "admin"
    JOURNALIST = "journalist"


class Notifications(BaseModel):
    email: bool = True
    sms: bool = False
    push: bool = True


class UserBase(BaseModel):
    username: str  # Added to match user.py
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    password: str
    confirm_password: str
    region: str
    district: str  # District ID
    constituency: str  # Renamed from county to match user.py
    sub_county: str  # Sub-county ID
    parish: str    # Parish ID
    village: str   # Village name
    interests: List[str] = []
    occupation: str = ""
    bio: Optional[str] = None
    political_interest: Optional[str] = None
    community_role: Optional[str] = None
    notifications: Notifications = Notifications()

class UserCreate(UserBase):
    pass  # Inherits username, password, confirm_password

class UserSignup(BaseModel):  # Added to wrap UserCreate
    user: UserCreate

class UserOut(UserBase):
    id: int
    role: Role
    is_active: bool
    created_at: datetime
    profile_image: Optional[str] = None
    notification_email: bool
    notification_sms: bool
    notification_push: bool

    class Config:
        from_attributes = True



class MessageBase(BaseModel):
    content: str


class MessageCreate(BaseModel):
    recipient_id: Optional[int] = None  # Optional for auto-routing to MP
    content: str

class MessageResponse(MessageBase):
    id: int
    sender_id: int
    recipient_id: int
    created_at: datetime
    is_read: bool  
    sender: UserOut
    recipient: UserOut


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
    member_count: int  
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

class ShareRequest(BaseModel):
    recipient_ids: Optional[List[int]] = None  # For in-app sharing to users
    group_id: Optional[int] = None  # For group sharing
    platform: Optional[str] = None  # e.g., "twitter", "whatsapp"