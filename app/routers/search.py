from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
from sqlalchemy.orm import selectinload
from typing import List
from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/search",
    tags=["Search"]
)

@router.get("/", response_model=schemas.SearchResponse)
async def search(query: str, db: AsyncSession = Depends(get_db)):
    if not query or len(query) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters long")

    tsquery = func.plainto_tsquery('english', query)
    user_query = select(models.User).filter(models.User.search_vector.op('@@')(tsquery))
    post_query = select(models.Post).filter(models.Post.search_vector.op('@@')(tsquery)).options(
        selectinload(models.Post.owner)
    )
    comment_query = select(models.Comment).filter(models.Comment.search_vector.op('@@')(tsquery)).options(
        selectinload(models.Comment.user)
    )

    user_result = await db.execute(user_query)
    post_result = await db.execute(post_query)
    comment_result = await db.execute(comment_query)

    return schemas.SearchResponse(
        users=user_result.scalars().all(),
        posts=post_result.scalars().all(),
        comments=comment_result.scalars().all()
    )



# from fastapi import FastAPI, Depends, HTTPException, APIRouter
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy.sql import func
# from typing import List
# from .. import models, schemas
# from ..database import get_db

# app = FastAPI()

# router = APIRouter(
#     prefix= "/search",
#     tags=["Search"]
# )

# # Search endpoint
# @app.get("/search", response_model=schemas.SearchResponse)
# async def search(query: str, db: AsyncSession = Depends(get_db)):
#     if not query or len(query) < 3:
#         raise HTTPException(status_code=400, detail="Query must be at least 3 characters long")

#     # Convert query to tsquery
#     tsquery = func.plainto_tsquery('english', query)

#     # Search users by username or email
#     user_query = select(models.User).filter(models.User.search_vector.op('@@')(tsquery))
#     user_result = await db.execute(user_query)
#     users = user_result.scalars().all()

#     # Search posts by title_of_the_post or content
#     post_query = select(models.Post).filter(models.Post.search_vector.op('@@')(tsquery))
#     post_result = await db.execute(post_query)
#     posts = post_result.scalars().all()

#     return schemas.SearchResponse(users=users, posts=posts)