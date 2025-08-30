from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, Computed, Enum, Date
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy_utils.types import TSVectorType
from sqlalchemy import Table
from sqlalchemy.ext.declarative import declarative_base
import enum
from sqlalchemy.dialects.postgresql import TSVECTOR

Base = declarative_base(cls=AsyncAttrs)



# Role Enum
class Role(enum.Enum):
    CITIZEN = "citizen"
    MP = "mp"
    ADMIN = "admin"
    JOURNALIST = "journalist"

group_members = Table(
    'group_members',
    Base.metadata,
    Column('group_id', Integer, ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
)

post_categories = Table(
    'post_categories',
    Base.metadata,
    Column('post_id', Integer, ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
    Column('category_id', Integer, ForeignKey('categories.id', ondelete='CASCADE'), primary_key=True)
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
    gender = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    phone_number = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    role = Column(Enum(Role), default=Role.CITIZEN, nullable=False)
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
    title_of_the_post = Column(String, index=True, nullable=False)
    content = Column(String, index=True, nullable=False)
    published = Column(Boolean, server_default='TRUE', index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    view_count = Column(Integer, default=0, nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    search_vector = Column(TSVectorType, Computed(
        "to_tsvector('english', title_of_the_post || ' ' || content)", persisted=True
    ))
    owner = relationship("User")
    categories = relationship("Category", secondary=post_categories, back_populates="posts")
    group = relationship("Group")


class Vote(Base):
    __tablename__ = "votes"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    media_url = Column(String, nullable=True)
    search_vector = Column(TSVectorType, Computed(
        "to_tsvector('english', content)", persisted=True
    ))
    user = relationship("User")
    post = relationship("Post")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    posts = relationship("Post", secondary=post_categories, back_populates="categories")

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner = relationship("User")
    members = relationship("User", secondary=group_members, back_populates="groups")
    posts = relationship("Post", back_populates="group")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'), nullable=True)
    group_id = Column(Integer, ForeignKey('groups.id', ondelete='CASCADE'), nullable=True)
    user = relationship("User", back_populates="notifications")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recipient_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    recipient = relationship("User", back_populates="received_messages", foreign_keys=[recipient_id])

class LiveFeed(Base):
    __tablename__ = "live_feeds"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    stream_url = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    journalist_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    journalist = relationship("User", back_populates="live_feeds")