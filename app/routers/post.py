from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, insert
from typing import List, Optional
from datetime import datetime
from .. import models, schemas
from ..schemas import Role
from ..database import get_db
from sqlalchemy.orm import selectinload
from fastapi.responses import JSONResponse
from .permissions import require_role
from ..routers.oauth2 import get_current_user 
import urllib.parse  # For URL encoding in share links

router = APIRouter(
    prefix="/posts",
    tags=["Posts"]
)

# Get all posts endpoint with pagination 
@router.get("/", response_model=None)  # Use JSONResponse for pagination
async def get_posts(
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user),
    limit: int = 10,
    skip: int = 0,
    category_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: Optional[str] = None,  # Options: "newest", "likes", "comments"
    constituency: Optional[str] = None  # MP filtering
):
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is suspended")

    # Build query with relationships and counts
    query = select(
        models.Post,
        func.count(models.Vote.post_id).label("like_count"),
        func.count(models.Comment.post_id).label("comment_count")
    ).options(
        selectinload(models.Post.owner),
        selectinload(models.Post.categories)
    ).outerjoin(
        models.Vote, models.Vote.post_id == models.Post.id
    ).outerjoin(
        models.Comment, models.Comment.post_id == models.Post.id
    ).group_by(models.Post.id)

    count_query = select(func.count()).select_from(models.Post)

    # Apply filters
    if category_id:
        query = query.join(models.post_categories).where(models.post_categories.c.category_id == category_id)
        count_query = count_query.join(models.post_categories).where(models.post_categories.c.category_id == category_id)
    if start_date:
        query = query.where(models.Post.created_at >= start_date)
        count_query = count_query.where(models.Post.created_at >= start_date)
    if end_date:
        query = query.where(models.Post.created_at <= end_date)
        count_query = count_query.where(models.Post.created_at <= end_date)
    if current_user.role == Role.MP and constituency:
        query = query.join(models.User, models.Post.owner_id == models.User.id).where(
            models.User.constituency == constituency,
            models.User.is_active == True
        )
        count_query = count_query.join(models.User, models.Post.owner_id == models.User.id).where(
            models.User.constituency == constituency,
            models.User.is_active == True
        )
    elif current_user.role == Role.CITIZEN:
        # Filter for public posts or posts in user's groups
        result = await db.execute(
            select(models.Group).join(models.group_members).where(models.group_members.c.user_id == current_user.id)
        )
        user_groups = result.scalars().all()
        group_ids = [group.id for group in user_groups]
        if group_ids:
            query = query.where(
                (models.Post.group_id.is_(None)) | (models.Post.group_id.in_(group_ids))
            )
            count_query = count_query.where(
                (models.Post.group_id.is_(None)) | (models.Post.group_id.in_(group_ids))
            )

    # Apply sorting
    if sort_by == "newest":
        query = query.order_by(models.Post.created_at.desc())
    elif sort_by == "likes":
        query = query.order_by(func.count(models.Vote.post_id).desc())
    elif sort_by == "comments":
        query = query.order_by(func.count(models.Comment.post_id).desc())
    else:
        query = query.order_by(models.Post.created_at.desc())

    # Execute count query
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()

    # Fetch posts
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    posts_data = result.all()

    # Convert to Pydantic models
    result = [
        {
            "post": schemas.Post.model_validate(post),
            "like": like_count,
            "comment_count": comment_count
        }
        for post, like_count, comment_count in posts_data
    ]

    # Pagination metadata
    next_url = f"/posts/?limit={limit}&skip={skip + limit}" if skip + limit < total_count else None
    prev_url = f"/posts/?limit={limit}&skip={skip - limit}" if skip > 0 else None

    return JSONResponse(content={
        "data": [  # Convert Pydantic post to dict for JSON
            {"post": item["post"].dict(), "like": item["like"], "comment_count": item["comment_count"]}
            for item in result
        ],
        "pagination": {
            "total_count": total_count,
            "limit": limit,
            "skip": skip,
            "next": next_url,
            "previous": prev_url
        }
    })


# Create post endpoint 
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Post)
async def create_post(
    post: schemas.PostCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: schemas.UserOut = Depends(lambda: require_role([Role.CITIZEN, Role.MP, Role.JOURNALIST]))
):
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
                    # Send WebSocket notification (ensure connected_users is accessible)
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

# Trending posts endpoint (uncommented and fixed with JSONResponse for consistency)
@router.get("/trending", response_model=None)
async def get_trending_posts(db: AsyncSession = Depends(get_db), limit: int = 10, skip: int = 0):
    seven_days_ago = func.now() - func.interval('7 days')
    count_query = select(func.count()).select_from(models.Post).where(models.Post.created_at >= seven_days_ago)
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()

    posts_query = select(models.Post).where(models.Post.created_at >= seven_days_ago).options(
        selectinload(models.Post.owner), selectinload(models.Post.categories)
    )
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
    # Apply skip/limit after sorting for pagination
    paginated_posts = trending_posts[skip:skip + limit]
    result = [{"post": post, "like": likes, "comment_count": comments} for post, likes, comments, _ in paginated_posts]

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

# Get single post 
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


#Sharing endpoint
@router.post("/{id}/share", status_code=status.HTTP_201_CREATED)
async def share_post(
    id: int,
    share: schemas.ShareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)
):
    # Verify post exists
    post_query = select(models.Post).where(models.Post.id == id)
    result = await db.execute(post_query)
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # In-app sharing to users
    if share.recipient_ids:
        for recipient_id in share.recipient_ids:
            recipient_query = select(models.User).where(models.User.id == recipient_id)
            result = await db.execute(recipient_query)
            recipient = result.scalar_one_or_none()
            if not recipient:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recipient {recipient_id} not found")

            # Create message
            db_message = models.Message(
                sender_id=current_user.id,
                recipient_id=recipient_id,
                content=f"Shared post: {post.title_of_the_post}\n{post.content}",
                created_at=datetime.utcnow(),
                is_read=False
            )
            db.add(db_message)

            # Create notification
            notification = models.Notification(
                user_id=recipient_id,
                message=f"{current_user.username} shared a post with you: {post.title_of_the_post}",
                post_id=post.id,
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.add(notification)

    # In-app sharing to group
    if share.group_id:
        group_query = select(models.Group).where(models.Group.id == share.group_id)
        result = await db.execute(group_query)
        group = result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

        # Verify user is member (optional)
        member_query = select(models.group_members).where(
            models.group_members.c.group_id == share.group_id,
            models.group_members.c.user_id == current_user.id
        )
        result = await db.execute(member_query)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this group")

        # Notify group members
        member_query = select(models.group_members).where(models.group_members.c.group_id == share.group_id)
        result = await db.execute(member_query)
        members = result.scalars().all()
        for member in members:
            notification = models.Notification(
                user_id=member.user_id,
                message=f"{current_user.username} shared a post in group {group.name}: {post.title_of_the_post}",
                post_id=post.id,
                group_id=share.group_id,
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.add(notification)

    # External sharing
    if share.platform:
        base_url = "http://127.0.0.1:8000"  
        post_url = f"{base_url}/posts/{id}"
        encoded_url = urllib.parse.quote(post_url)
        encoded_title = urllib.parse.quote(post.title_of_the_post)
        share_url = ""
        if share.platform.lower() == "twitter":
            share_url = f"https://twitter.com/intent/tweet?url={encoded_url}&text={encoded_title}"
        elif share.platform.lower() == "whatsapp":
            share_url = f"https://wa.me/?text={encoded_title}%20{encoded_url}"
        elif share.platform.lower() == "facebook":
            share_url = f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}"
        

        return {"message": "Post shared successfully", "share_url": share_url}

    await db.commit()
    return {"message": "Post shared successfully"}