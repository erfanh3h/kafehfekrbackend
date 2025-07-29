from typing import Optional
import uuid, datetime
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from Entities.Database import game_database

SECRET_KEY = "09da5e74afaa9ma2565c818195b7b9563b93xc059f6f0f4cab6cf63b88e8d3e7"
ALGORITHM = "HS256"


# ACCESS_TOKEN_EXPIRE_DAY = 30

class Token(BaseModel):
    access_token: str
    token_type: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_device_id_hash(device_id):
    return uuid.uuid5(uuid.NAMESPACE_X500, device_id)


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.UTC) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(weeks=52)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def extract_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone: int = payload.get("phone")
        id: str = payload.get("id")
        device_id: str = payload.get("device_id")
        token_data = {'phone': phone, 'id': id, 'device_id': device_id}
        return token_data
    except:
        return None

async def check_is_token_valid(auth_data):
    if auth_data is None:
        return None
    try:
        user_token_data = await extract_token(auth_data['token'])
        if user_token_data is None:
            return None
        user = game_database.users_manager.read_user(user_token_data['id'])
        if user is None or user['device_id'] != user_token_data['device_id']:
            return None
        else:
            return user_token_data
    except:
        return None
