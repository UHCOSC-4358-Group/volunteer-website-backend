"""
How Auth is going to work:
Begins when user logins in with email and password
They'll hit a different route depending on whether admin or vol, giving us context
We'll use different db statements based on that
Website hits our route. First, we grab the user data from db, including hashed password
If user doesn't exist, then we reject
We check hashed vs input with bcrypt, if not correct, reject
If pass, then we return a token with user's data
Should we handle refreshing? idk
"""

from bcrypt import hashpw, gensalt, checkpw
from pydantic import BaseModel
from fastapi import Request, Response, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import time
import jwt


JWT_SECRET = os.environ.get("JWT_SECRET")
ALGORITHMS = ["HS256"]
SALT_ROUNDS = 12


# Hashes password by turning into bytes, salting it, then hashing
def hash_password(plain_pw: str) -> str:
    bytes_pw = plain_pw.encode("utf-8")
    salt = gensalt(SALT_ROUNDS)
    hashed_pw = hashpw(bytes_pw, salt).decode("utf-8")  # Hashes and turns to string
    return hashed_pw


def verify_password(plaintext_pw: str, hashed_pw: str) -> bool:
    return checkpw(plaintext_pw.encode("utf-8"), hashed_pw.encode("utf-8"))


# Signs the JWT string
def sign_JWT_admin(userId: int, response: Response):
    payload = {"userId": userId, "exp": time.time() + 3600, "userType": "admin"}
    if JWT_SECRET is None:
        raise HTTPException(500, "Environemnt credentials are not loaded!")
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHMS[0])
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        max_age=3600,
        path="/",
        samesite="none",
        secure=False,
    )
    return response


def sign_JWT_volunteer(userId: int, response: Response):
    payload = {"userId": userId, "exp": time.time() + 3600, "userType": "volunteer"}
    if JWT_SECRET is None:
        raise HTTPException(500, "Environment credentials are not loaded!")
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHMS[0])
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        max_age=3600,
        path="/",
        samesite="lax",
        secure=False,
    )
    return response


def decodeJWT(token: str):
    try:
        if JWT_SECRET is None:
            raise HTTPException(500, "Environemnt credentials are not loaded!")
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=ALGORITHMS)
        return decoded_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token has expired!")
    except HTTPException as exc:
        raise exc
    except:
        raise HTTPException(status_code=403, detail="Bad token credentials!")


class JWTBearer(HTTPBearer):
    def __init__(self, auto_Error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_Error)

    async def __call__(self, request: Request) -> str | None:

        token = request.cookies.get("access_token")
        if not token:
            credentials: HTTPAuthorizationCredentials | None = await super(
                JWTBearer, self
            ).__call__(request)

            if credentials and credentials.scheme == "Bearer":
                token = credentials.credentials

        if not token:
            raise HTTPException(status_code=403, detail="Invalid or Expired token!")

        if not self.verify_jwt(token):
            raise HTTPException(status_code=403, detail="Invalid or Expired token!")

        return token

    def verify_jwt(self, jwt_token: str):
        isTokenValid = False
        payload = decodeJWT(jwt_token)
        if payload:
            isTokenValid = True
        return isTokenValid


class UserTokenInfo(BaseModel):
    user_id: int
    user_type: str


async def get_current_user(token: str = Depends(JWTBearer())):
    payload = decodeJWT(token)
    if not payload:
        raise HTTPException(status_code=403, detail="Invalid or Expired token!")

    user_id: int | None = payload.get("userId")
    user_type: str | None = payload.get("userType")
    if not user_id or not user_type:
        raise HTTPException(status_code=403, detail="Invalid token payload!")

    # Create new user token info object

    user_token_info = UserTokenInfo(user_id=user_id, user_type=user_type)
    return user_token_info


def is_admin(user_info: UserTokenInfo):
    return user_info.user_type == "admin"


def is_volunteer(user_info: UserTokenInfo):
    return user_info.user_type == "volunteer"
