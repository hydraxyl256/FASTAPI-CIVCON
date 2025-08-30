from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .. import models, schemas
from ..database import get_db
from ..routers.permissions import require_role
from datetime import datetime

router = APIRouter(
    prefix="/live_feeds",
    tags=["Live Feeds"]
)

@router.post("/", response_model=schemas.LiveFeedResponse, status_code=status.HTTP_201_CREATED)
async def create_live_feed(
    live_feed: schemas.LiveFeedCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(require_role([schemas.Role.JOURNALIST]))
):
    db_feed = models.LiveFeed(
        title=live_feed.title,
        stream_url=live_feed.stream_url,
        description=live_feed.description,
        journalist_id=current_user.id
    )
    db.add(db_feed)
    await db.commit()
    await db.refresh(db_feed)
    return db_feed