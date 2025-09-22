from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, Enum, Date
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.schema import ForeignKey, Table
from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB
import enum
from sqlalchemy import Enum as SQLEnum  
from app.schemas import Role

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Role(enum.Enum):
    CITIZEN = "citizen"
    MP = "mp"
    ADMIN = "admin"
    JOURNALIST = "journalist"

# Association tables
group_members = Table(
    "group_members",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True, nullable=False),
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True, nullable=False),
)

post_categories = Table(
    "post_categories",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id"), primary_key=True, nullable=False),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True, nullable=False),
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    nin = Column(String, unique=True, nullable=False)
    constituency = Column(String, nullable=False)
    district = Column(String, nullable=False)
    sub_county = Column(String, nullable=False)
    region = Column(String, nullable=False)
    parish = Column(String, nullable=False)
    village = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    phone_number = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=False)
    bio = Column(String, nullable=True)
    political_interest = Column(String, nullable=True)
    community_role = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    interests = Column(JSONB, nullable=True)
    notification_email = Column(Boolean, default=True, nullable=False)
    notification_sms = Column(Boolean, default=False, nullable=False)
    notification_push = Column(Boolean, default=True, nullable=False)
    profile_image = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    # FIXED: Bind to lowercase .value strings from Role Enum
    role = Column(SQLEnum(Role, native_enum=False, values_callable=lambda x: [e.value for e in x]), default=Role.CITIZEN, nullable=False)
    is_active = Column(Boolean, default=True)
    search_vector = Column(TSVECTOR, nullable=True)

    posts = relationship("Post", back_populates="owner")
    comments = relationship("Comment", back_populates="user")
    votes = relationship("Vote", back_populates="user")
    groups = relationship("Group", secondary=group_members, back_populates="members")
    notifications = relationship("Notification", back_populates="user")
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="[Message.sender_id]")
    received_messages = relationship("Message", back_populates="recipient", foreign_keys="[Message.recipient_id]")
    live_feeds = relationship("LiveFeed", back_populates="journalist")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    search_vector = Column(TSVECTOR, nullable=True)

    owner = relationship("User", back_populates="posts")
    group = relationship("Group", back_populates="posts")
    comments = relationship("Comment", back_populates="post")
    votes = relationship("Vote", back_populates="post")
    categories = relationship("Category", secondary=post_categories, back_populates="posts")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    parent_comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    parent_comment = relationship("Comment", remote_side=[id])
    replies = relationship("Comment", back_populates="parent_comment")

class Vote(Base):
    __tablename__ = "votes"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), primary_key=True, nullable=False)
    vote_type = Column(String, nullable=False)  # "up" or "down"

    user = relationship("User", back_populates="votes")
    post = relationship("Post", back_populates="votes")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    posts = relationship("Post", secondary=post_categories, back_populates="categories")

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    is_active = Column(Boolean, default=True)

    members = relationship("User", secondary=group_members, back_populates="groups")
    posts = relationship("Post", back_populates="group")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    is_read = Column(Boolean, default=False)

    user = relationship("User", back_populates="notifications")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)

    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    recipient = relationship("User", back_populates="received_messages", foreign_keys=[recipient_id])

class LiveFeed(Base):
    __tablename__ = "live_feeds"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    journalist_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)

    journalist = relationship("User", back_populates="live_feeds")