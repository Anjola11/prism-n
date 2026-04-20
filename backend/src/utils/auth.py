import bcrypt
from datetime import datetime, timedelta, timezone
import uuid
from enum import Enum
import jwt
from src.config import Config
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


access_token_expiry = timedelta(hours=3)
refresh_token_expiry = timedelta(days=3)
reset_password_expiry = timedelta(minutes=15)

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"

def generate_password_hash(password: str ) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password_hash(password: str, hashed_password: str) -> bool:

    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))



def create_token(user_data: dict, token_type: TokenType):

    current_time = datetime.now(timezone.utc)
    payload = {
        'iat': current_time,
        'jti': str(uuid.uuid4()),
        'type': token_type,
        'role': str(user_data.get('role', 'user')),
        'sub': str(user_data.get('uid')),
        
    }

    # Compute absolute expiration time once to keep iat/exp consistent.

    if token_type == TokenType.ACCESS:
        payload['exp'] = current_time + access_token_expiry
    elif token_type == TokenType.REFRESH:
        payload['exp'] = current_time + refresh_token_expiry
    elif token_type == TokenType.RESET:
        payload['exp'] = current_time + reset_password_expiry

    token = jwt.encode(
        payload=payload,
        key=Config.JWT_KEY,
        algorithm=Config.JWT_ALGORITHM
    )

    return token


def decode_token(token: str):

    try:
        token_data = jwt.decode(
            jwt=token,
            key=Config.JWT_KEY,
            algorithms=[Config.JWT_ALGORITHM],
            leeway=10
        )
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token."
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Something went wrong processing the token."
        )
    return token_data
