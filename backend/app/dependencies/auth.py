from fastapi import Cookie, Depends, HTTPException
from fastapi.security import HTTPBearer
from app.database.database import get_db
from services.user_service import UserService
from services.jwt_service import JWTService

security = HTTPBearer(auto_error=False)

jwt_service = JWTService()
user_service = UserService()
async def get_current_user(
    credentials = Depends(security),
    access_token: str | None = Cookie(default=None),
    refresh_token: str | None = Cookie(default=None),
    db=Depends(get_db)
):
    token = credentials.credentials if credentials else access_token

    if not token:
        token = refresh_token

    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        payload = jwt_service.verify_token(token)

        
        current_user = await user_service.get_user_by_id(db, payload["sub"])
        return current_user

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
