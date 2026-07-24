import re

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from app.api.spotify_oauth import create_or_update_user, login as spotify_login
from app.api.spotify_oauth import callback as spotify_callback
from app.api.spotify_oauth import current_user as spotify_current_user
from app.api.jwt import create_access_token, create_refresh_token, add_refresh_token_to_user
from app.database.database import get_db
from app.core.config import settings
from models.SpotifyToken import SpotifyToken

router = APIRouter(prefix="/spotify/auth", tags=["spotify-auth"])

FRONTEND_DASHBOARD_URL = settings.FRONTEND_URL + "/dashboard"
ACCESS_TOKEN_COOKIE_NAME = "access_token"
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"

# Only ever redirect back into the app on a known-safe, tightly-matched path.
# This is the only thing standing between an attacker-controlled `state`/`next`
# value and an open redirect, so keep it strict rather than permissive.
SAFE_NEXT_PATH_PATTERN = re.compile(r"^/join/[A-Z0-9]{6}$")


def _safe_next_path(next_path: str | None) -> str | None:
    if next_path and SAFE_NEXT_PATH_PATTERN.match(next_path):
        return next_path
    return None


@router.get("/login")
async def login(next: str | None = None):
    return spotify_login(_safe_next_path(next))

@router.get("/callback")
async def callback(code: str, state: str | None = None, db=Depends(get_db)):

    token = SpotifyToken(**await spotify_callback(code))

    current_user = await spotify_current_user(token.access_token)

    user = await create_or_update_user(current_user, token, db)

    jwt_token = create_access_token(user.id)

    refresh_token = create_refresh_token(user.id)

    await add_refresh_token_to_user(db, user, refresh_token)

    safe_next_path = _safe_next_path(state)
    redirect_url = f"{settings.FRONTEND_URL}{safe_next_path}" if safe_next_path else FRONTEND_DASHBOARD_URL

    response = RedirectResponse(redirect_url)
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
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        max_age=60 * 60 * 24 * 30,
    )

    return response
