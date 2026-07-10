from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.user import User
from models.SpotifyToken import SpotifyToken
from sqlalchemy import select
import requests
import base64
from datetime import datetime, timedelta
class UserService():
    def __init__(self):
        pass

    def get_profile_image_base64(self, profile_image_url: str) -> str:
        response = requests.get(profile_image_url)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode('utf-8')
        else:
            return None
        
    def calculate_token_expiry(self, expires_in: int) -> int:
        return datetime.utcnow() + timedelta(seconds=expires_in)

    async def get_user_by_id(self, db: AsyncSession, user_id: int):
        user_id = int(user_id)
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def add_refresh_token_to_user(
        self,
        db: AsyncSession,
        user: User,
        refresh_token: str
    ):
        user.user_refresh_token = refresh_token
        user.user_refresh_token_expires_at = self.calculate_token_expiry(
            30 * 24 * 60 * 60
        )

        await db.commit()
        await db.refresh(user)

        return user

  
    async def create_or_update_user(
        self,
        user_data: dict,
        tokens: SpotifyToken,
        db: AsyncSession
    ):
        result = await db.execute(
            select(User)
            .where(User.spotify_id == user_data["id"])
        )

        user = result.scalar_one_or_none()

        if user:
            user.access_token = tokens.access_token
            user.refresh_token = tokens.refresh_token
            user.expires_in = tokens.expires_in
            user.token_type = tokens.token_type

        else:
            user = User(
                spotify_id=user_data["id"],
                username=user_data.get("display_name"),
                email=user_data.get("email"),
                spotify_access_token=tokens.access_token,
                spotify_refresh_token=tokens.refresh_token,
                token_expires_at=self.calculate_token_expiry(tokens.expires_in),
                profile_image=user_data.get("images")[0]["url"] if user_data.get("images") else None,
            )

            db.add(user)


        await db.commit()
        await db.refresh(user)

        print(f"User {user.spotify_id} created or updated successfully.")

        return user
    
    async def get_users_current_refresh_token(self, db: AsyncSession, user_id: int):
        user = await self.get_user_by_id(db, user_id)
        if user:
            return user.user_refresh_token
        return None

    async def get_users_spotify_tokens(self, db, user_id):
        user = await self.get_user_by_id(db, user_id)
        if user:
            return {
                "access_token": getattr(user, "spotify_access_token", None),
                "refresh_token": getattr(user, "spotify_refresh_token", None),
            }
        return None