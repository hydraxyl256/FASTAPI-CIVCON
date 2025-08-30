from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .. import models, schemas
from ..database import get_db
from ..routers.permissions import require_role

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

@router.post("/users/{user_id}/suspend", response_model=schemas.UserOut)
async def suspend_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(require_role([schemas.Role.ADMIN]))
):
    user_query = select(models.User).where(models.User.id == user_id)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role == schemas.Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot suspend another admin")
    
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/users/{user_id}/unsuspend", response_model=schemas.UserOut)
async def unsuspend_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(require_role([schemas.Role.ADMIN]))
):
    user_query = select(models.User).where(models.User.id == user_id)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/modules", response_model=dict)
async def add_module(
    module: dict,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserOut = Depends(require_role([schemas.Role.ADMIN]))
):
    return {"message": f"Module {module.get('name')} added successfully"}