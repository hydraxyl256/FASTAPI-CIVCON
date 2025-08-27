from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from .. import  models, schemas, utils, database
from typing import Optional, List
from .. database import SessionLocal, get_db
from . import oauth2
from sqlalchemy import func



router = APIRouter(
    prefix= "/posts",
    tags=["Posts"]
)


# GET ALL POSTS
#@router.get("/", response_model=List[schemas.PostLike])

#def get_posts(db: Session = Depends(get_db), limit: int = 10, skip: int = 0, 
    #          search: Optional[str]= ""):
    #posts = db.query(models.Post).filter(models.Post.title_of_the_post.contains(search)).limit(limit).offset(skip).all()
    
    
   #results = db.query(models.Post, func.count(models.Vote.post_id).label("like")).outerjoin(models.Vote, models.Vote.post_id == models.Post.id).group_by(models.Post.id).all()
    
    #return results


@router.get("/", response_model=List[schemas.PostLike])
def get_posts(db: Session = Depends(get_db), limit: int = 10, skip: int = 0, 
              search: Optional[str] = ""):
    results = (
        db.query(models.Post, func.count(models.Vote.post_id).label("like"))
        .outerjoin(models.Vote, models.Vote.post_id == models.Post.id)
        .filter(models.Post.title_of_the_post.contains(search))
        .group_by(models.Post.id)
        .limit(limit)
        .offset(skip)
        .all()
    )

    # Transform the query results to match the PostLike schema
    response = [
        schemas.PostLike(
            title_of_the_post=post.title_of_the_post,
            content=post.content,
            published=post.published,
            post=schemas.Post(
                id=post.id,
                title_of_the_post=post.title_of_the_post,
                content=post.content,
                published=post.published,
                created_at=post.created_at,
                owner_id=post.owner_id,
                owner=schemas.UserOut(
                    id=post.owner.id,
                    email=post.owner.email,
                    created_at=post.owner.created_at
                )
            ),
            like=like_count
        )
        for post, like_count in results
    ]

    return response




# CREATE POST
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Post)
def create_posts(post: schemas.PostCreate, db: Session = Depends(get_db), 
                 
                 #must be login to create a post
                 current_user: int = Depends(oauth2.get_current_user)):
    
    new_post = models.Post(owner_id = current_user.id ,**post.dict()) 
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post



# GET INDIVIDUAL POST
@router.get("/{id}", response_model=schemas.PostLike)
def get_post(id: int, db: Session = Depends(get_db)):
    result = (
        db.query(models.Post, func.count(models.Vote.post_id).label("like"))
        .outerjoin(models.Vote, models.Vote.post_id == models.Post.id)
        .filter(models.Post.id == id)
        .group_by(models.Post.id)
        .first()
    )

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id: {id} was not found")

    post, like_count = result

    response = schemas.PostLike(
        title_of_the_post=post.title_of_the_post,
        content=post.content,
        published=post.published,
        post=schemas.Post(
            id=post.id,
            title_of_the_post=post.title_of_the_post,
            content=post.content,
            published=post.published,
            created_at=post.created_at,
            owner_id=post.owner_id,
            owner=schemas.UserOut(
                id=post.owner.id,
                email=post.owner.email,
                created_at=post.owner.created_at
            )
        ),
        like=like_count
    )

    return response




# DELETE POST
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id: int, db: Session = Depends(get_db), 
                
                #must be login to delete a post
                 current_user: int = Depends(oauth2.get_current_user)):
    post_query = db.query(models.Post).filter(models.Post.id == id)
    post = post_query.first()

    if post == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The Post with id {id} does not exist"
        )
    
        #Make the user only delete his own post
    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail= "Not authorized to perform requested action")


    post_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# UPDATE POST
@router.put("/{id}", response_model=schemas.Post)
def update_post(id: int, updated_post: schemas.PostCreate, db: Session = Depends(get_db), 
                 
                #must be login to edit/update a post
                 current_user: int = Depends(oauth2.get_current_user)):
    
    post_query = db.query(models.Post).filter(models.Post.id == id)
    post = post_query.first()
    if post == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The Post with id {id} does not exist"
        )
    
    #Make the user only update his own post
    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail= "Not authorized to perform requested action")


    post_query.update(updated_post.dict(), synchronize_session=False)
    db.commit()

    
    return  post_query.first()


