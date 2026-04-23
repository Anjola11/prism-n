from fastapi import HTTPException, status, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from src.utils.auth import decode_token
from src.db.main import get_session
from src.auth.models import User
from src.db.redis import redis_client
from sqlmodel import select
import uuid
import logging

logger = logging.getLogger(__name__)

async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    access_token = request.cookies.get("access_token")
    if not access_token:
        # check auth header as fallback
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
    
    try:
        token_data = decode_token(access_token)
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    jti = token_data.get('jti')
    if jti:
        try:
            is_blacklisted = await redis_client.get(jti)
            if is_blacklisted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked. Please login again."
                )
        except Exception as e:
            logger.warning(f"Failed to check token in redis: {e}")
        
    uid = token_data.get("sub")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token data"
        )
        
    try:
        parsed_uid = uuid.UUID(uid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format"
        )
        
    statement = select(User).where(User.uid == parsed_uid)
    result = await session.exec(statement)
    user = result.first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    return user

async def get_verified_user(
    current_user = Depends(get_current_user)
):
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not verified. Please verify your email first."
        )
        
    return current_user


async def get_verified_user_id(
    current_user = Depends(get_verified_user)
):
    return current_user.uid
