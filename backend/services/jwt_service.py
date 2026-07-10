from jose import jwt
from datetime import datetime, timedelta
import os
from app.core.config import settings
class JWTService:
    def __init__(self):
        self.secret = settings.JWT_SECRET
        self.algorithm = "HS256"

    def create_access_token(self, user_id: int):

        payload = {
            "sub": str(user_id),
            "exp": datetime.utcnow() + timedelta(days=7)
        }

        return jwt.encode(
            payload,
            self.secret,
            algorithm=self.algorithm
        )
    
    
    def create_refresh_token(self, user_id: int):

        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=30)
        }

        return jwt.encode(
            payload,
            self.secret,
            algorithm="HS256"
        )
    
    def refresh_access_token(self, refresh_token: str):
        payload = self.verify_token(refresh_token)

        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        user_id = payload.get("sub")
        print(f"User ID from refresh token: {user_id}")
        return self.create_access_token(user_id), user_id

    def verify_token(self, token: str):

        return jwt.decode(
            token,
            self.secret,
            algorithms=[self.algorithm]
        )