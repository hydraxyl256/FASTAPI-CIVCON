from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, insert
from sqlalchemy.orm import selectinload
from typing import List
from .. import models, schemas
from ..routers import oauth2
from ..database import get_db
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/groups",
    tags=["Groups"]
)

@router.post("/", response_model=schemas.GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(group: schemas.GroupCreate, db: AsyncSession = Depends(get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    # Check if group name exists
    group_query = select(models.Group).where(models.Group.name == group.name)
    group_result = await db.execute(group_query)
    if group_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group name already exists")
    
    # Fetch the database User instance
    user_query = select(models.User).where(models.User.id == current_user.id)
    user_result = await db.execute(user_query)
    db_user = user_result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Create group
    db_group = models.Group(name=group.name, description=group.description, owner_id=current_user.id)
    db.add(db_group)
    await db.commit()
    await db.refresh(db_group)

    # Insert creator into group_members table
    await db.execute(
        insert(models.group_members).values(group_id=db_group.id, user_id=db_user.id)
    )
    await db.commit()

    # Refresh group with owner and members
    group_query = select(models.Group).where(models.Group.id == db_group.id).options(
        selectinload(models.Group.owner), selectinload(models.Group.members)
    )
    group_result = await db.execute(group_query)
    db_group = group_result.scalar_one_or_none()
    
    return {**db_group.__dict__, "member_count": len(db_group.members)}

@router.get("/", response_model=List[schemas.GroupResponse])
async def get_groups(db: AsyncSession = Depends(get_db)):
    groups_query = select(models.Group).options(selectinload(models.Group.owner), selectinload(models.Group.members))
    groups_result = await db.execute(groups_query)
    groups = groups_result.scalars().all()
    return [{**group.__dict__, "member_count": len(group.members)} for group in groups]

@router.post("/{id}/join", response_model=schemas.GroupResponse)
async def join_group(id: int, db: AsyncSession = Depends(get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    # Fetch group with members
    group_query = select(models.Group).where(models.Group.id == id).options(selectinload(models.Group.members))
    group_result = await db.execute(group_query)
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    # Fetch the database User instance
    user_query = select(models.User).where(models.User.id == current_user.id)
    user_result = await db.execute(user_query)
    db_user = user_result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Check if user is already a member
    member_query = select(models.group_members).where(
        models.group_members.c.group_id == id,
        models.group_members.c.user_id == db_user.id
    )
    member_result = await db.execute(member_query)
    if member_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already a member")
    
    # Insert into group_members
    await db.execute(
        insert(models.group_members).values(group_id=id, user_id=db_user.id)
    )
    await db.commit()

    # Refresh group with owner and members
    group_query = select(models.Group).where(models.Group.id == id).options(
        selectinload(models.Group.owner), selectinload(models.Group.members)
    )
    group_result = await db.execute(group_query)
    group = group_result.scalar_one_or_none()
    
    return {**group.__dict__, "member_count": len(group.members)}



@router.get("/{id}/posts", response_model=None)
async def get_group_posts(id: int, db: AsyncSession = Depends(get_db), limit: int = 10, skip: int = 0):
    group_query = select(models.Group).where(models.Group.id == id)
    group_result = await db.execute(group_query)
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    count_query = select(func.count()).select_from(models.Post).where(models.Post.group_id == id)
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()

    posts_query = select(models.Post).where(models.Post.group_id == id).options(
        selectinload(models.Post.owner), selectinload(models.Post.categories)
    ).offset(skip).limit(limit)
    posts_result = await db.execute(posts_query)
    posts = posts_result.scalars().all()

    result = []
    for post in posts:
        like_query = select(func.count()).select_from(models.Vote).where(models.Vote.post_id == post.id)
        comment_query = select(func.count()).select_from(models.Comment).where(models.Comment.post_id == post.id)
        like_result = await db.execute(like_query)
        comment_result = await db.execute(comment_query)
        likes = like_result.scalar()
        comments = comment_result.scalar()
        result.append({"post": post, "like": likes, "comment_count": comments})
    
    next_url = f"/groups/{id}/posts?limit={limit}&skip={skip + limit}" if skip + limit < total_count else None
    prev_url = f"/groups/{id}/posts?limit={limit}&skip={skip - limit}" if skip > 0 else None
    
    return JSONResponse(content={
        "data": result,
        "pagination": {
            "total_count": total_count,
            "limit": limit,
            "skip": skip,
            "next": next_url,
            "previous": prev_url
        }
    })




# @router.get("/{id}/posts", response_model=List[schemas.PostLike])
# async def get_group_posts(id: int, db: AsyncSession = Depends(get_db), limit: int = 10, skip: int = 0):
#     group_query = select(models.Group).where(models.Group.id == id)
#     group_result = await db.execute(group_query)
#     if not group_result.scalar_one_or_none():
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
#     posts_query = select(models.Post).where(models.Post.group_id == id).options(
#         selectinload(models.Post.owner), selectinload(models.Post.categories)
#     ).offset(skip).limit(limit)
#     posts_result = await db.execute(posts_query)
#     posts = posts_result.scalars().all()

#     result = []
#     for post in posts:
#         like_query = select(func.count()).select_from(models.Vote).where(models.Vote.post_id == post.id)
#         comment_query = select(func.count()).select_from(models.Comment).where(models.Comment.post_id == post.id)
#         like_result = await db.execute(like_query)
#         comment_result = await db.execute(comment_query)
#         likes = like_result.scalar()
#         comments = comment_result.scalar()
#         result.append({"post": post, "like": likes, "comment_count": comments})
    
#     return result