from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from typing import List
from app.models import User, Message
from app.schemas import MessageCreate, MessageOut, UserOut
from app.database import get_db
from .oauth2 import get_current_user
from app.main import manager
from datetime import datetime

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=MessageOut)
async def send_message(
    message: MessageCreate,
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify recipient exists
    recipient = await db.execute(select(User).filter(User.id == message.recipient_id))
    recipient = recipient.scalars().first()
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")
    if not recipient.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recipient is suspended")

    # Create message
    new_message = Message(
        sender_id=current_user.id,
        recipient_id=message.recipient_id,
        content=message.content
    )
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)

    # Broadcast via WebSocket
    await manager.send_message(
        message.recipient_id,
        {
            "sender_id": current_user.id,
            "content": message.content,
            "created_at": new_message.created_at.isoformat()
        }
    )

    return new_message

@router.get("/", response_model=List[MessageOut])
async def get_messages(
    constituency: str | None = None,
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == "mp" and constituency:
        # MPs can view messages sent to them in their constituency
        result = await db.execute(
            select(Message)
            .join(User, Message.sender_id == User.id)
            .filter(
                and_(
                    Message.recipient_id == current_user.id,
                    User.constituency == constituency,
                    User.is_active == True
                )
            )
        )
    else:
        # Regular users see their own conversations
        result = await db.execute(
            select(Message).filter(
                and_(
                    (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id),
                    User.is_active == True
                )
            )
        )
    messages = result.scalars().all()
    return messages