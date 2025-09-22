from typing import List
from functools import lru_cache  
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..schemas import UserOut, Role  
from .oauth2 import get_current_user  


async def require_role(
    roles: List[Role],
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)  
) -> UserOut:
    """
    Dependency to require the current user to have one of the specified roles.
    Admins are always allowed as a bypass.
    """
    if not roles:
        raise ValueError("roles list cannot be empty")  
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is suspended or inactive"
        )
    
    if user.role.value not in [r.value for r in roles] and user.role.value != Role.ADMIN.value:
        allowed_roles = [r.value for r in roles]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation requires one of the following roles: {', '.join(allowed_roles)}"
        )
    return user

async def require_admin_or_self(
    user_id: int,
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserOut:
    if user.role.value != Role.ADMIN.value and user.id != user_id:  
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation requires admin role or self")
    return user