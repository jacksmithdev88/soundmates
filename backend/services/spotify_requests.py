from http.client import HTTPException

import httpx, random

from app.core.config import settings
class SpotifyRequests():
    def __init__(self):
        pass
   
    async def refresh_spotify_access_token(self, refresh_token: str):
        url = "https://accounts.spotify.com/api/token"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                auth=(
                    settings.SPOTIFY_CLIENT_ID,
                    settings.SPOTIFY_CLIENT_SECRET
                )
            )

            if response.status_code != 200:
                error_detail = self._spotify_error_detail(response)
                print(f"Error refreshing access token: {error_detail}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Spotify token refresh failed: {error_detail}"
                )

            response.raise_for_status()

            return response.json()

    async def spotify_request(
        self,
        method: str,
        url: str,
        access_token: str,
        refresh_token: str | None = None,
        user=None
    ):
        async with httpx.AsyncClient() as client:

            response = await client.request(
                method,
                url,
                headers={
                    "Authorization": f"Bearer {access_token}"
                }
            )

            if response.status_code == 401 and refresh_token and user:

                token_data = await self.refresh_spotify_access_token(
                    refresh_token
                )

                new_access_token = token_data["access_token"]

                user.spotify_access_token = new_access_token

                if "refresh_token" in token_data:
                    user.spotify_refresh_token = token_data["refresh_token"]

                if hasattr(user, "save"):
                    user.save()

                response = await client.request(
                    method,
                    url,
                    headers={
                        "Authorization": f"Bearer {new_access_token}"
                    }
                )

            response.raise_for_status()

            return response.json()

    async def get_current_user(self, access_token: str, refresh_token: str | None = None, user=None): 
       
        url = "https://api.spotify.com/v1/me"

        return await self.spotify_request(
            "GET",
            url,
            access_token,
            refresh_token,
            user
        )

    async def get_users_top_artists(self, time_range: str = "medium_term", limit: int = 20, access_token: str = None, refresh_token: str = None, user=None):
        url = f"https://api.spotify.com/v1/me/top/artists?time_range={time_range}&limit={limit}"
        response = await self.spotify_request(
            "GET",
            url,
            access_token,
            refresh_token,
            user
        )

        return response["items"] if "items" in response else []
    
    async def get_users_top_tracks(self, time_range: str = "medium_term", limit: int = 20, access_token: str = None, refresh_token: str = None, user=None):
        url = f"https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit={limit}"
        response = await self.spotify_request(
            "GET",
            url,
            access_token,
            refresh_token,
            user
        )

        return response["items"] if "items" in response else []
    
    async def get_random_songs(self, access_token, refresh_token, user, count):
        tracks = await self.get_users_top_tracks(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user,
            limit=50
        )

        if not tracks:
            return []

        if count <= 0:
            return []

        selected_tracks = []
        available_tracks = list(tracks)

        for _ in range(min(count, len(available_tracks))):
            track = random.choice(available_tracks)
            selected_tracks.append(track)
            available_tracks.remove(track)

        return selected_tracks
    
    async def get_user_playlists(self, access_token, refresh_token, user):
        url = "https://api.spotify.com/v1/me/playlists?offset=0&limit=50"
        response = await self.spotify_request(
            "GET",
            url,
            access_token,
            refresh_token,
            user
        )


        return response["items"]