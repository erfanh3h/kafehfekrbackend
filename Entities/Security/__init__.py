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


def _normalize_phone(phone_val) -> str:
    if phone_val is None:
        return ""
    s = str(phone_val).strip().replace(" ", "")
    if s.startswith("+98"):
        s = s[3:]
    elif s.startswith("98") and len(s) == 12:
        s = s[2:]
    if s.startswith("0"):
        s = s[1:]
    return s


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(weeks=52)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def extract_token(token):
    try:
        if isinstance(token, str) and token.startswith("Bearer "):
            token = token[7:].strip()
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone = payload.get("phone")
        id: str = payload.get("id")
        device_id: str = payload.get("device_id")
        is_bot: bool = payload.get("is_bot", False)
        token_data = {"phone": phone, "id": id, "device_id": device_id, "is_bot": is_bot}
        return token_data
    except Exception:
        return None


async def check_is_token_valid(auth_data):
    if auth_data is None:
        return None
    try:
        if isinstance(auth_data, dict):
            token = auth_data.get("token")
        elif isinstance(auth_data, str):
            token = auth_data
        else:
            return None
        if not token:
            return None
        user_token_data = await extract_token(token)
        if user_token_data is None or not user_token_data.get("id"):
            return None
        if user_token_data.get("is_bot"):
            return user_token_data
        user = game_database.users_manager.read_user(user_token_data["id"])
        if user is None:
            return None
        db_phone = _normalize_phone(user.get("phone"))
        tok_phone = _normalize_phone(user_token_data.get("phone"))
        if db_phone and tok_phone and db_phone != tok_phone:
            return None
        return user_token_data
    except Exception:
        return None
