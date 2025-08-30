from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from typing import List
from .. import models, schemas
from ..routers import oauth2
from ..database import get_db
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)

@router.get("/", response_model=None)
async def get_notifications(db: AsyncSession = Depends(get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user), limit: int = 10, skip: int = 0):
    count_query = select(func.count()).select_from(models.Notification).where(models.Notification.user_id == current_user.id)
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()

    notifications_query = select(models.Notification).where(models.Notification.user_id == current_user.id).options(
        selectinload(models.Notification.user)
    ).order_by(models.Notification.created_at.desc()).offset(skip).limit(limit)
    notifications_result = await db.execute(notifications_query)
    notifications = notifications_result.scalars().all()

    next_url = f"/notifications?limit={limit}&skip={skip + limit}" if skip + limit < total_count else None
    prev_url = f"/notifications?limit={limit}&skip={skip - limit}" if skip > 0 else None

    return JSONResponse(content={
        "data": notifications,
        "pagination": {
            "total_count": total_count,
            "limit": limit,
            "skip": skip,
            "next": next_url,
            "previous": prev_url
        }
    })

@router.patch("/{id}/read", response_model=schemas.NotificationResponse)
async def mark_notification_read(id: int, db: AsyncSession = Depends(get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    notification_query = select(models.Notification).where(
        models.Notification.id == id,
        models.Notification.user_id == current_user.id
    ).options(selectinload(models.Notification.user))
    notification_result = await db.execute(notification_query)
    notification = notification_result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found or not authorized")
    
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    
    return notification