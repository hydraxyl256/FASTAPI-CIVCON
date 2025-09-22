from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from .. import models, schemas
from ..schemas import Role  # Import Role for require_role
from ..database import get_db
from .permissions import require_role

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

@router.get("/users", response_model=List[schemas.UserOut])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(lambda: require_role([Role.ADMIN])),  
    limit: int = 100,
    skip: int = 0
):
    query = select(models.User).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    return users

@router.post("/users/{user_id}/suspend", response_model=schemas.UserOut)
async def suspend_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(lambda: require_role([Role.ADMIN]))  # FIXED: Lambda wrapper for async dep
):
    # Fetch user to suspend
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if db_user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot suspend yourself")
    
    # Suspend user (set is_active = False)
    db_user.is_active = False
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/users/{user_id}/unsuspend", response_model=schemas.UserOut)
async def unsuspend_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(lambda: require_role([Role.ADMIN]))  # Lambda for unsuspend
):
    # Fetch user to unsuspend
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Unsuspend user (set is_active = True)
    db_user.is_active = True
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(lambda: require_role([Role.ADMIN]))  # Lambda for delete
):
    # Fetch user to delete
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if db_user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    
    # Soft delete: Set is_active = False (or use await db.delete(db_user) for hard delete)
    db_user.is_active = False
    await db.commit()
    return None

# Optional: Other admin endpoints (e.g., promote to role)
@router.post("/users/{user_id}/promote/{new_role}", response_model=schemas.UserOut)
async def promote_user(
    user_id: int,
    new_role: Role,  # e.g., "mp" or Role.MP
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(lambda: require_role([Role.ADMIN]))
):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    db_user.role = new_role
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/modules", response_model=dict)
async def add_module(
    module: dict,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(lambda: require_role([Role.ADMIN]))
):
    return {"message": f"Module {module.get('name')} added successfully"}