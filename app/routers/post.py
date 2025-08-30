from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, insert
from typing import List, Optional
from datetime import datetime
from .. import models, schemas
from ..routers import oauth2
from ..database import get_db
from sqlalchemy.orm import selectinload
from fastapi.responses import JSONResponse
from .permissions import require_role

router = APIRouter(
    prefix="/posts",
    tags=["Posts"]
)


#get all post endpoint inclusive of pagination

@router.get("/", response_model=None)  # Set to None to use JSONResponse
async def get_posts(
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
    skip: int = 0,
    category_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: Optional[str] = None  # Options: "newest", "likes", "comments"
):
    # Count total posts for pagination
    count_query = select(func.count()).select_from(models.Post)
    if category_id:
        count_query = count_query.join(models.post_categories).where(models.post_categories.c.category_id == category_id)
    if start_date:
        count_query = count_query.where(models.Post.created_at >= start_date)
    if end_date:
        count_query = count_query.where(models.Post.created_at <= end_date)
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()

    posts_query = select(models.Post).options(
        selectinload(models.Post.owner), selectinload(models.Post.categories)
    )
    
    if category_id:
        posts_query = posts_query.join(models.post_categories).where(models.post_categories.c.category_id == category_id)
    if start_date:
        posts_query = posts_query.where(models.Post.created_at >= start_date)
    if end_date:
        posts_query = posts_query.where(models.Post.created_at <= end_date)
    
    if sort_by == "newest":
        posts_query = posts_query.order_by(models.Post.created_at.desc())
    elif sort_by == "likes":
        posts_query = posts_query.join(models.Vote, isouter=True).group_by(models.Post.id).order_by(func.count(models.Vote.post_id).desc())
    elif sort_by == "comments":
        posts_query = posts_query.join(models.Comment, isouter=True).group_by(models.Post.id).order_by(func.count(models.Comment.post_id).desc())
    else:
        posts_query = posts_query.order_by(models.Post.created_at.desc())
    
    posts_query = posts_query.offset(skip).limit(limit)
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
    
    # Pagination metadata
    next_url = f"/posts/?limit={limit}&skip={skip + limit}" if skip + limit < total_count else None
    prev_url = f"/posts/?limit={limit}&skip={skip - limit}" if skip > 0 else None
    
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



#create post endpoint
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Post)
async def create_post(post: schemas.PostCreate, db: AsyncSession = Depends(get_db), 
            current_user: schemas.UserOut = Depends(require_role([schemas.Role.CITIZEN, schemas.Role.MP, schemas.Role.JOURNALIST]))):
    # Validate group if provided
    if post.group_id:
        group_query = select(models.Group).where(models.Group.id == post.group_id).options(selectinload(models.Group.members))
        group_result = await db.execute(group_query)
        group = group_result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
        
        # Check if user is a group member
        user_query = select(models.User).where(models.User.id == current_user.id)
        user_result = await db.execute(user_query)
        db_user = user_result.scalar_one_or_none()
        if not db_user or db_user not in group.members:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be a group member to post in this group")

    # Validate categories
    if post.category_ids:
        category_query = select(models.Category).where(models.Category.id.in_(post.category_ids))
        category_result = await db.execute(category_query)
        categories = category_result.scalars().all()
        if len(categories) != len(post.category_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more categories not found")

    # Create post
    db_post = models.Post(
        title_of_the_post=post.title_of_the_post,
        content=post.content,
        published=post.published,
        owner_id=current_user.id,
        group_id=post.group_id
    )
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)

    # Associate categories
    if post.category_ids:
        for category_id in post.category_ids:
            await db.execute(
                insert(models.post_categories).values(post_id=db_post.id, category_id=category_id)
            )
        await db.commit()

    # Notify group members if post is in a group
    if post.group_id:
        group_query = select(models.Group).where(models.Group.id == post.group_id).options(selectinload(models.Group.members))
        group_result = await db.execute(group_query)
        group = group_result.scalar_one_or_none()
        if group:
            for member in group.members:
                if member.id != current_user.id:  # Skip the post creator
                    notification = models.Notification(
                        user_id=member.id,
                        message=f"New post '{post.title_of_the_post}' in group '{group.name}' by {current_user.username}",
                        group_id=post.group_id,
                        post_id=db_post.id
                    )
                    db.add(notification)
                    # Send WebSocket notification
                    from ..main import connected_users
                    if member.id in connected_users:
                        await connected_users[member.id].send_json({
                            "id": notification.id,
                            "message": notification.message,
                            "is_read": notification.is_read,
                            "post_id": notification.post_id,
                            "group_id": notification.group_id,
                            "created_at": db_post.created_at.isoformat(),
                            "user_id": member.id
                        })
            await db.commit()

    await db.refresh(db_post, attribute_names=["categories"])
    return db_post


#tending post endpoint
@router.get("/trending", response_model=None)
async def get_trending_posts(db: AsyncSession = Depends(get_db), limit: int = 10, skip: int = 0):
    seven_days_ago = func.now() - func.interval('7 days')
    count_query = select(func.count()).select_from(models.Post).where(models.Post.created_at >= seven_days_ago)
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()

    posts_query = select(models.Post).where(models.Post.created_at >= seven_days_ago).options(
        selectinload(models.Post.owner), selectinload(models.Post.categories)
    ).offset(skip).limit(limit)
    posts_result = await db.execute(posts_query)
    posts = posts_result.scalars().all()

    trending_posts = []
    for post in posts:
        like_query = select(func.count()).select_from(models.Vote).where(models.Vote.post_id == post.id)
        comment_query = select(func.count()).select_from(models.Comment).where(models.Comment.post_id == post.id)
        like_result = await db.execute(like_query)
        comment_result = await db.execute(comment_query)
        likes = like_result.scalar()
        comments = comment_result.scalar()
        score = post.view_count * 0.5 + likes * 1.0 + comments * 1.5
        trending_posts.append((post, likes, comments, score))

    trending_posts.sort(key=lambda x: x[3], reverse=True)
    result = [{"post": post, "like": likes, "comment_count": comments} for post, likes, comments, _ in trending_posts[:limit]]

    next_url = f"/posts/trending?limit={limit}&skip={skip + limit}" if skip + limit < total_count else None
    prev_url = f"/posts/trending?limit={limit}&skip={skip - limit}" if skip > 0 else None
    
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










@router.get("/{id}", response_model=schemas.PostLike)
async def get_post(id: int, db: AsyncSession = Depends(get_db)):
    # Fetch post and increment view count
    post_query = select(models.Post).where(models.Post.id == id).options(
        selectinload(models.Post.owner), selectinload(models.Post.categories)
    )
    post_result = await db.execute(post_query)
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    # Update view_count
    post.view_count += 1
    db.add(post)
    await db.commit()

    # Get like and comment counts
    like_query = select(func.count()).select_from(models.Vote).where(models.Vote.post_id == id)
    comment_query = select(func.count()).select_from(models.Comment).where(models.Comment.post_id == id)
    like_result = await db.execute(like_query)
    comment_result = await db.execute(comment_query)
    likes = like_result.scalar()
    comments = comment_result.scalar()

    return {"post": post, "like": likes, "comment_count": comments}

@router.get("/", response_model=List[schemas.PostLike])
async def get_posts(
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
    skip: int = 0,
    category_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: Optional[str] = None  # Options: "newest", "likes", "comments"
):
    posts_query = select(models.Post).options(
        selectinload(models.Post.owner), selectinload(models.Post.categories)
    )
    
    # Filter by category
    if category_id:
        posts_query = posts_query.join(models.post_categories).where(models.post_categories.c.category_id == category_id)
    
    # Filter by date range
    if start_date:
        posts_query = posts_query.where(models.Post.created_at >= start_date)
    if end_date:
        posts_query = posts_query.where(models.Post.created_at <= end_date)
    
    # Sorting
    if sort_by == "newest":
        posts_query = posts_query.order_by(models.Post.created_at.desc())
    elif sort_by == "likes":
        posts_query = posts_query.join(models.Vote, isouter=True).group_by(models.Post.id).order_by(func.count(models.Vote.post_id).desc())
    elif sort_by == "comments":
        posts_query = posts_query.join(models.Comment, isouter=True).group_by(models.Post.id).order_by(func.count(models.Comment.post_id).desc())
    else:
        posts_query = posts_query.order_by(models.Post.created_at.desc())
    
    posts_query = posts_query.offset(skip).limit(limit)
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
    
    return result

# @router.get("/trending", response_model=List[schemas.PostLike])
# async def get_trending_posts(db: AsyncSession = Depends(get_db), limit: int = 10):
#     # Calculate trending score: (views * 0.5 + likes * 1.0 + comments * 1.5) within last 7 days
#     seven_days_ago = func.now() - func.interval('7 days')
#     posts_query = select(models.Post).where(models.Post.created_at >= seven_days_ago).options(
#         selectinload(models.Post.owner), selectinload(models.Post.categories)
#     )
#     posts_result = await db.execute(posts_query)
#     posts = posts_result.scalars().all()