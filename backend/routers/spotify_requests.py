from fastapi import APIRouter
from fastapi import Depends
from app.api.spotify_oauth import current_user
from app.database.database import get_db
from app.dependencies.auth import get_current_user
from services.user_service import UserService
from services.spotify_requests import SpotifyRequests
router = APIRouter(prefix="/spotify/requests", tags=["spotify-requests"])

user_service = UserService()
spotify_requests = SpotifyRequests()

@router.get("/current_user")
async def get_current_spotify_user( user=Depends(get_current_user)):
    spotify_access_token = user.spotify_access_token
    spotify_refresh_token = user.spotify_refresh_token
    spotify_user = await current_user(spotify_access_token, spotify_refresh_token, user)

    return spotify_user

@router.get("/top_artists")
async def get_top_artists(user=Depends(get_current_user)):
    spotify_access_token = user.spotify_access_token
    spotify_refresh_token = user.spotify_refresh_token
    top_artists = await spotify_requests.get_users_top_artists(access_token=spotify_access_token, refresh_token=spotify_refresh_token, user=user)
    return top_artists

@router.get("/top_tracks")
async def get_top_tracks(user=Depends(get_current_user)):
    spotify_access_token = user.spotify_access_token
    spotify_refresh_token = user.spotify_refresh_token
    top_tracks = await spotify_requests.get_users_top_tracks(access_token=spotify_access_token, refresh_token=spotify_refresh_token, user=user)
    return top_tracks
