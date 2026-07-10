from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from app.api.jwt import add_refresh_token_to_user, create_refresh_token, refresh_access_token, verify_token
from app.database.database import get_db
from app.api.user import get_user_by_id, get_users_current_refresh_token
from app.dependencies.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.config import settings
router = APIRouter(prefix="/user/auth", tags=["user-auth"])

ACCESS_TOKEN_COOKIE_NAME = "access_token"
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"

def serialize_user(user):
    return {
        "id": user.id,
        "spotify_id": user.spotify_id,
        "display_name": user.username,
    }

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh")
async def refresh_token(
    response: Response,
    data: RefreshRequest | None = None,
    refresh_token_cookie: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE_NAME),
    db: AsyncSession = Depends(get_db)
):
    refresh_token_value = data.refresh_token if data else refresh_token_cookie

    if not refresh_token_value:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    jwt_token, user_id = refresh_access_token(refresh_token_value)
    current_refresh_token = await get_users_current_refresh_token(db, user_id)

    if current_refresh_token != refresh_token_value:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await get_user_by_id(db, user_id)

    new_refresh_token = create_refresh_token(user_id)
    await add_refresh_token_to_user(db, user, new_refresh_token)

    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=jwt_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        max_age=60 * 60 * 24 * 7,
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=new_refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        max_age=60 * 60 * 24 * 30,
    )

    return {"ok": True}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path="/")
    return {"ok": True}

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return serialize_user(user)

@router.get("/session")
async def session(
    response: Response,
    access_token: str | None = Cookie(default=None, alias=ACCESS_TOKEN_COOKIE_NAME),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    if not access_token and not refresh_token:
        return {"authenticated": False, "user": None}

    user = None
    payload = None

    if access_token:
        try:
            payload = verify_token(access_token)
            user = await get_user_by_id(db, payload["sub"])
        except Exception:
            user = None

    if not user and refresh_token:
        try:
            payload = verify_token(refresh_token)
            user = await get_user_by_id(db, payload["sub"])
        except Exception:
            return {"authenticated": False, "user": None}

    if not user:
        return {"authenticated": False, "user": None}

    if refresh_token:
        new_access_token, _ = refresh_access_token(refresh_token)
        response.set_cookie(
            key=ACCESS_TOKEN_COOKIE_NAME,
            value=new_access_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/",
            max_age=60 * 60 * 24 * 7,
        )

    return {
        "authenticated": True,
        "user": serialize_user(user),
    }
