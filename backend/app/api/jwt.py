from services.jwt_service import JWTService
from services.user_service import UserService
jwt_service = JWTService()
user_service = UserService()

def create_access_token(user_id: int):
    return jwt_service.create_access_token(user_id)

def create_refresh_token(user_id: int):
    return jwt_service.create_refresh_token(user_id)

def verify_token(token: str):
    return jwt_service.verify_token(token)

def add_refresh_token_to_user(db, user, refresh_token: str):
    return user_service.add_refresh_token_to_user(db, user, refresh_token)

def refresh_access_token(refresh_token: str):
    return jwt_service.refresh_access_token(refresh_token)