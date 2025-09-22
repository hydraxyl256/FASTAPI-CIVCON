from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from .. import models, schemas
from ..database import get_db
from ..routers.oauth2 import get_current_user
from datetime import datetime
from fastapi.responses import JSONResponse
from .permissions import require_role


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)

# Lazy import for WebSocket
async def send_notification(user_id: int, notification: dict):
    from ..main import connected_users  
    if user_id in connected_users:
        await connected_users[user_id].send_json(notification)

@router.get("/", response_model=List[schemas.NotificationResponse])
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user),
    limit: int = 10,
    skip: int = 0
):
    query = select(models.Notification).where(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()
    return notifications

@router.post("/", response_model=schemas.NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification: schemas.NotificationBase,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(lambda: require_role([schemas.Role.ADMIN]))  # Admin-only for manual creation
):
    db_notification = models.Notification(
        user_id=notification.user_id,
        content=notification.content,
        created_at=datetime.utcnow(),
        is_read=False
    )
    db.add(db_notification)
    await db.commit()
    await db.refresh(db_notification)
    
    # Send WebSocket notification
    await send_notification(db_notification.user_id, {
        "type": "notification",
        "content": db_notification.content,
        "created_at": db_notification.created_at.isoformat(),
        "is_read": False
    })
    
    return db_notification

@router.patch("/{notification_id}/read", response_model=schemas.NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Notification).where(models.Notification.id == notification_id)
    )
    db_notification = result.scalar_one_or_none()
    if not db_notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    
    if db_notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to mark this notification as read")
    
    db_notification.is_read = True
    await db.commit()
    await db.refresh(db_notification)
    return db_notification
