from services.spotify_oauth import SpotifyAuthenticator
from services.spotify_requests import SpotifyRequests
from services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from fastapi import Depends
from models.SpotifyToken import SpotifyToken
spotify_authenticator = SpotifyAuthenticator()
user_service = UserService()
spotify_requests = SpotifyRequests()
def login():
    spotify_authenticator.return_id_and_secrets()
    return spotify_authenticator.login()

async def callback(code: str):
    return await spotify_authenticator.callback(code)

async def current_user(access_token: str, refresh_token: str | None = None, user=None):
    return await spotify_requests.get_current_user(access_token, refresh_token, user)

async def create_or_update_user(user_data: dict, tokens: SpotifyToken, db: AsyncSession):
    return await user_service.create_or_update_user(user_data, tokens, db)

async def refresh_spotify_access_token(refresh_token: str):
    return await spotify_authenticator.refresh_spotify_access_token(refresh_token)
