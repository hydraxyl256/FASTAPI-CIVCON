from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func  # For like count
from .. import schemas, models
from ..database import get_db
from .oauth2 import get_current_user  # FIXED: Import get_current_user directly

router = APIRouter(
    prefix="/votes",
    tags=["Votes/Likes"]
)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def votes(
    vote: schemas.Vote,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)  # FIXED: Allow any logged-in user
):
    # Validate dir
    if vote.dir not in [0, 1]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Vote direction must be 0 (unvote) or 1 (upvote)")

    post_query = select(models.Post).where(models.Post.id == vote.post_id)
    post_result = await db.execute(post_query)
    post = post_result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {vote.post_id} does not exist"
        )

    vote_query = select(models.Vote).where(
        models.Vote.post_id == vote.post_id,
        models.Vote.user_id == current_user.id
    )
    vote_result = await db.execute(vote_query)
    found_vote = vote_result.scalar_one_or_none()

    if vote.dir == 1:
        if found_vote:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"user {current_user.id} has already voted on post {vote.post_id}"
            )
        new_vote = models.Vote(post_id=vote.post_id, user_id=current_user.id)
        db.add(new_vote)
        await db.commit()
        # Get updated likes
        like_query = select(func.count()).select_from(models.Vote).where(models.Vote.post_id == vote.post_id)
        like_result = await db.execute(like_query)
        likes = like_result.scalar()
        return {"message": "Voted successfully", "likes": likes}
    else:  # dir == 0: unvote
        if not found_vote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vote does not exist")

        await db.delete(found_vote)
        await db.commit()
        # Get updated likes
        like_query = select(func.count()).select_from(models.Vote).where(models.Vote.post_id == vote.post_id)
        like_result = await db.execute(like_query)
        likes = like_result.scalar()
        return {"message": "Successfully deleted vote", "likes": likes}