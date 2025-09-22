from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from .. import models, schemas
from ..database import get_db
from ..routers.oauth2 import get_current_user
from ..schemas import Role
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)

# Lazy import to avoid circular import
async def send_message(user_id: int, message: dict):
    from ..main import manager, connected_users  # Import both manager and connected_users
    await manager.send_message(user_id, message)
    return connected_users  # Return for use in create_message

@router.post("/", response_model=schemas.MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    message: schemas.MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)
):
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is suspended")

    # Auto-route to MP if recipient_id not provided
    recipient_id = message.recipient_id
    if recipient_id is None:
        # Find MP for user's constituency
        result = await db.execute(
            select(models.User).where(
                models.User.constituency == current_user.constituency,
                models.User.role == Role.MP.value,
                models.User.is_active == True
            )
        )
        mp = result.scalar_one_or_none()
        if not mp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active MP found for constituency {current_user.constituency}"
            )
        recipient_id = mp.id

    # Validate recipient
    result = await db.execute(
        select(models.User).where(
            models.User.id == recipient_id,
            models.User.is_active == True
        )
    )
    recipient = result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found or inactive")

    # Create message
    db_message = models.Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=message.content,
        created_at=datetime.utcnow(),
        is_read=False
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)

    # Send WebSocket message
    connected_users = await send_message(recipient_id, {
        "sender_id": current_user.id,
        "content": message.content,
        "created_at": db_message.created_at.isoformat(),
        "is_read": False
    })

    # Create notification for MP
    notification = models.Notification(
        user_id=recipient_id,
        content=f"New message from {current_user.full_name} in {current_user.constituency}",
        created_at=datetime.utcnow(),
        is_read=False
    )
    db.add(notification)
    await db.commit()

    # Send WebSocket notification (if connected)
    if recipient_id in connected_users:
        await connected_users[recipient_id].send_json({
            "type": "notification",
            "content": notification.content,
            "created_at": notification.created_at.isoformat(),
            "is_read": False
        })

    return db_message

@router.get("/", response_model=None)  # Use JSONResponse for pagination
async def get_messages(
    constituency: Optional[str] = None,
    current_user: schemas.UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    skip: int = 0
):
    # Count total messages for pagination
    count_query = select(func.count()).select_from(models.Message)
    if current_user.role == Role.MP and constituency:
        count_query = count_query.join(models.User, models.Message.sender_id == models.User.id).where(
            models.User.constituency == constituency,
            models.Message.recipient_id == current_user.id,
            models.User.is_active == True
        )
    else:
        count_query = count_query.join(models.User, models.Message.sender_id == models.User.id).where(
            (models.Message.sender_id == current_user.id) | (models.Message.recipient_id == current_user.id),
            models.User.is_active == True
        )
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()

    # Fetch messages
    query = select(models.Message)
    if current_user.role == Role.MP and constituency:
        query = query.join(models.User, models.Message.sender_id == models.User.id).where(
            models.User.constituency == constituency,
            models.Message.recipient_id == current_user.id,
            models.User.is_active == True
        )
    else:
        query = query.join(models.User, models.Message.sender_id == models.User.id).where(
            (models.Message.sender_id == current_user.id) | (models.Message.recipient_id == current_user.id),
            models.User.is_active == True
        )
    query = query.order_by(models.Message.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    messages = result.scalars().all()

    # Convert ORM to Pydantic for serialization
    message_schemas = [schemas.MessageResponse.model_validate(msg) for msg in messages]

    # Pagination metadata
    next_url = f"/messages/?limit={limit}&skip={skip + limit}" if skip + limit < total_count else None
    prev_url = f"/messages/?limit={limit}&skip={skip - limit}" if skip > 0 else None

    return JSONResponse(content={
        "data": [msg.dict() for msg in message_schemas],
        "pagination": {
            "total_count": total_count,
            "limit": limit,
            "skip": skip,
            "next": next_url,
            "previous": prev_url
        }
    })

@router.patch("/{message_id}/read", response_model=schemas.MessageResponse)
async def mark_message_read(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)
):
    # Fetch message
    result = await db.execute(
        select(models.Message).where(models.Message.id == message_id)
    )
    db_message = result.scalar_one_or_none()
    if not db_message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    
    # Only recipient can mark as read
    if db_message.recipient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to mark this message as read")
    
    # Update read status
    db_message.is_read = True
    await db.commit()
    await db.refresh(db_message)
    
    # Notify sender via WebSocket
    connected_users = await send_message(db_message.sender_id, {
        "type": "read_receipt",
        "message_id": db_message.id,
        "is_read": True,
        "updated_at": datetime.utcnow().isoformat()
    })
    
    return db_message