from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pathlib import Path
import uuid
from typing import List
from .. import models, schemas
from ..routers import oauth2
from ..database import get_db
import os

UPLOAD_DIR = Path("Uploads/comments")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(
    prefix="/comments",
    tags=["Comments"]
)

@router.post("/{post_id}/comments", response_model=schemas.CommentResponse)
async def create_comment(
    post_id: int,
    content: str = Form(...),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(oauth2.get_current_user)
):
    # Validate post exists
    post_query = select(models.Post).where(models.Post.id == post_id)
    post_result = await db.execute(post_query)
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Handle file upload
    media_url = None
    if file:
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov'}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")

        max_size = 10 * 1024 * 1024
        if file.size > max_size:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size exceeds 10MB")

        file_name = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / file_name
        try:
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)
            media_url = f"/Uploads/comments/{file_name}"
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save file: {str(e)}")

    # Create comment
    db_comment = models.Comment(
        content=content,
        post_id=post_id,
        user_id=current_user.id,
        media_url=media_url
    )
    db.add(db_comment)
    await db.commit()

    # Notify post owner (if not the commenter)
    if post.owner_id != current_user.id:
        notification = models.Notification(
            user_id=post.owner_id,
            message=f"New comment on your post '{post.title_of_the_post}' by {current_user.username}",
            post_id=post_id
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)  # Refresh to get notification.id
        
        # Send WebSocket notification
        from ..main import connected_users
        if post.owner_id in connected_users:
            await connected_users[post.owner_id].send_json({
                "id": notification.id,
                "message": notification.message,
                "is_read": notification.is_read,
                "post_id": notification.post_id,
                "group_id": notification.group_id,
                "created_at": notification.created_at.isoformat(),
                "user_id": post.owner_id
            })

    await db.refresh(db_comment, attribute_names=["user"])
    return db_comment

@router.get("/{post_id}/comments", response_model=List[schemas.CommentResponse])
async def get_comments(
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    post_query = select(models.Post).where(models.Post.id == post_id)
    post_result = await db.execute(post_query)
    if not post_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    comment_query = select(models.Comment).where(models.Comment.post_id == post_id).options(selectinload(models.Comment.user))
    comment_result = await db.execute(comment_query)
    comments = comment_result.scalars().all()
    return comments

@router.put("/comments/{comment_id}", response_model=schemas.CommentResponse)
async def update_comment(
    comment_id: int,
    comment: schemas.CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(oauth2.get_current_user)
):
    comment_query = select(models.Comment).where(models.Comment.id == comment_id)
    comment_result = await db.execute(comment_query)
    db_comment = comment_result.scalar_one_or_none()
    if not db_comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if db_comment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this comment")

    db_comment.content = comment.content
    await db.commit()
    await db.refresh(db_comment, attribute_names=["user"])
    return db_comment

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(oauth2.get_current_user)
):
    comment_query = select(models.Comment).where(models.Comment.id == comment_id)
    comment_result = await db.execute(comment_query)
    db_comment = comment_result.scalar_one_or_none()
    if not db_comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if db_comment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this comment")

    if db_comment.media_url:
        file_path = Path(f".{db_comment.media_url}")
        if file_path.exists():
            file_path.unlink()

    await db.delete(db_comment)
    await db.commit()
    return None