from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
import httpx
from app.core.config import settings

class SpotifyAuthenticator():
    def __init__(self):
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.callback_url = settings.SPOTIFY_REDIRECT_URL
        self.scopes = [
            "user-read-email",
            "user-read-private",
            "playlist-read-private",
            "user-top-read",
            "user-read-recently-played",
        ]

    def return_id_and_secrets(self):
        print(f"Client ID: {self.client_id} Client secret: {self.client_secret} Redirect URL: {self.callback_url}")

    def _spotify_error_detail(self, response: httpx.Response) -> str:
        try:
            error_data = response.json()
        except ValueError:
            return response.text

        return error_data.get("error_description") or error_data.get("error") or response.text


    def login(self):
        params = { 
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.callback_url,
            "scope": " ".join(self.scopes)
        }

        url = (
            "https://accounts.spotify.com/authorize?"
            + urlencode(params)
        )

        return RedirectResponse(url)
    
    async def callback(self, code: str):
        async with httpx.AsyncClient() as client:

            response = await client.post(
                "https://accounts.spotify.com/api/token",

                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.callback_url,
                },

                auth=(
                    self.client_id,
                    self.client_secret
                )
            )

            if response.status_code != 200:
                error_detail = self._spotify_error_detail(response)
                print(f"Error exchanging Spotify code: {error_detail}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Spotify token exchange failed: {error_detail}"
                )

            response.raise_for_status()

            return response.json()
