from fastapi import APIRouter
from fastapi import Depends, Query
from app.api.spotify_oauth import current_user
from app.database.database import get_db
from app.dependencies.auth import get_current_user
from services.user_service import UserService
from services.spotify_requests import SpotifyRequests
router = APIRouter(prefix="/spotify/requests", tags=["spotify-requests"])

user_service = UserService()
spotify_requests = SpotifyRequests()


def normalize_track(track: dict) -> dict:
    artists = track.get("artists", []) or []
    artist_names = [artist.get("name") for artist in artists if artist.get("name")]
    album = track.get("album", {}) or {}
    images = album.get("images") or []
    release_date = album.get("release_date") or ""
    release_year = release_date[:4]

    return {
        "id": track.get("id"),
        "name": track.get("name"),
        "artist": artist_names[0] if artist_names else "Unknown",
        "artists": artist_names,
        "image": images[0]["url"] if images else None,
        "release_year": release_year if release_year.isdigit() else None,
    }

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

@router.get("/search/songs")
async def get_tracks_from_search(q: str = Query(...), user=Depends(get_current_user)):
    spotify_access_token = user.spotify_access_token
    spotify_refresh_token = user.spotify_refresh_token
    print(f"Searching for {q}")
    search_results = await spotify_requests.get_search_results(
        access_token=spotify_access_token,
        refresh_token=spotify_refresh_token,
        user=user,
        type="track",
        query=q
    )

    return [
        normalize_track(track)
        for track in search_results
        if track.get("name")
    ]