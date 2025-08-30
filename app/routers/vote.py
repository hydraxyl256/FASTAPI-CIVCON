from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .. import schemas, models
from ..routers import oauth2
from ..database import get_db

router = APIRouter(
    prefix="/votes",
    tags=["Votes/Likes"]
)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def votes(
    vote: schemas.Vote,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(oauth2.get_current_user)
):
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
        return {"message": "Voted successfully"}
    else:
        if not found_vote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vote does not exist")

        await db.delete(found_vote)
        await db.commit()
        return {"message": "Successfully deleted vote"}






# from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
# from .. import schemas, database, models
# from . import oauth2
# from sqlalchemy.orm import Session
# from ..database import  get_db


# router = APIRouter(
#     prefix= "/votes",
#     tags=["Votes/Likes"]
# )

# @router.post("/", status_code= status.HTTP_201_CREATED)
# def votes(vote: schemas.Vote, db: Session = Depends(get_db), 
#           current_user: int = Depends(oauth2.get_current_user)):
    
#     post = db.query(models.Post).filter(models.Post.id == vote.post_id).first()

#     if not post: 
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
#                             detail=f"Post with id {vote.post_id} does not exist ")




#     vote_query = db.query(models.Vote).filter(models.Vote.post_id == vote.post_id, 
#                                               models.Vote.user_id == current_user.id)
    
#     found_vote = vote_query.first()

#     if (vote.dir == 1):
#         if found_vote:
#             raise HTTPException( f"user{current_user.id} has already voted on post{vote.post_id}", 
#                                 status_code=status.HTTP_409_CONFLICT)
#         new_vote = models.Vote(post_id = vote.post_id, user_id = current_user.id)
#         db.add(new_vote)
#         db.commit()
#         return {"message": "Voted successfully"}

#     else:
#         if not found_vote:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= "vote does not exist")
        
#         vote_query.delete(synchronize_session=False)
#         db.commit()
#         return {"message": "successfully deleted vote"}