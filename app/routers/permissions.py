from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..schemas import UserOut, Role
from .oauth2 import get_current_user

async def require_role(roles: list[Role], user: UserOut = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is suspended")
    if user.role not in roles and user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Operation requires one of {', '.join(r.value for r in roles)} roles")
    return user

async def require_admin_or_self(user_id: int, user: UserOut = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != Role.ADMIN and user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation requires admin role or self")
    return user