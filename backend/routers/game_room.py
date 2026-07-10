from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from services.game_service import GameService


router = APIRouter(prefix="/rooms", tags=["game-rooms"])

game_service = GameService()


@router.post("/create")
async def create_game_room(user=Depends(get_current_user)):
    return game_service.create_game_room(user)


@router.post("/join/{room_id}")
async def join_room(
    room_id: str,
    user=Depends(get_current_user)
):
    return await game_service.join_room(room_id, user)


@router.post("/leave")
async def leave_room(
    user=Depends(get_current_user)
):
    return await game_service.leave_room(user)


@router.post("/{room_id}/game-mode")
async def select_game_mode(
    room_id: str,
    game_mode: str,
    user=Depends(get_current_user)
):
    return await game_service.select_game_mode(room_id, user, game_mode)


@router.websocket("/ws/{room_id}")
async def websocket_join(
    websocket: WebSocket,
    room_id: str,
    db: AsyncSession = Depends(get_db),
):
    print(f"WebSocket connection request for room {room_id}")
    await game_service.websocket_join(websocket, room_id, db)
