from services.user_service import UserService
user_service = UserService()
 
async def get_user_by_id(db, user_id: int):
    return await user_service.get_user_by_id(db, user_id)

async def get_users_current_refresh_token(db, user_id: int):
    return await user_service.get_users_current_refresh_token(db, user_id)