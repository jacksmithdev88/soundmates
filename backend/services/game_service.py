import time
import json
import random
import string
from collections import defaultdict
import asyncio
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from services.question_service import QuestionService
from app.database.models.user import User
from app.dependencies.auth import jwt_service
from services.user_service import UserService


class GameService:
    VALID_GAME_MODES = [
        "Higher or Lower",
        "Get that year",
        "Guess the Artist",
        "Whats the song?",
        "Who Listened To This?",
        "Music Trivia",
        "Guess who? (Playlist)"
    ]

    def __init__(self):
        self.game_rooms = {}
        self.connections = defaultdict(dict)
        self.room_members = defaultdict(dict)
        self.user_service = UserService()

    def generate_room_id(self):
        room_id = ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )

        while room_id in self.game_rooms:
            room_id = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )

        return room_id

    def _member_payload(self, user):
        return {
            "id": user.id,
            "display_name": getattr(user, "display_name", None)
            or getattr(user, "username", None)
            or f"User {user.id}",
            "spotify_id": getattr(user, "spotify_id", None),
        }

    def _add_room_member(self, room_id, user):
        self.game_rooms[room_id]["users"].add(user.id)

        self.room_members[room_id][user.id] = self._member_payload(user)

        self.game_rooms[room_id]["scores"][user.id] = 0

    def _remove_room_member(self, room_id: str, user_id: int):
        self.game_rooms[room_id]["users"].discard(user_id)
        self.room_members[room_id].pop(user_id, None)

    def _room_state_payload(self, room_id):
        return {
            "type": "room_state",
            "room_id": room_id,
            "players": [
                {
                    **self.room_members[room_id][user_id],
                    "score": self.game_rooms[room_id]["scores"].get(user_id,0)
                }
                for user_id in self.connections[room_id]
            ]
        }

    async def _broadcast_room_state(self, room_id: str, exclude_user_id: int | None = None):
        payload = self._room_state_payload(room_id)

        for user_id, websocket in self.connections[room_id].items():
            if user_id != exclude_user_id:
                await websocket.send_json(payload)

    def create_game_room(self, user):
        if any(room["host"] == user.id for room in self.game_rooms.values()):
            raise HTTPException(
                status_code=400,
                detail="User already hosts a game room"
            )

        if any(user.id in room["users"] for room in self.game_rooms.values()):
            raise HTTPException(
                status_code=400,
                detail="User is already in a game room"
            )

        room_id = self.generate_room_id()


        self.game_rooms[room_id] = {
            "host": user.id,
            "users": {user.id},
            "started": False,
            "game_mode": None,
            "scores": {},
            "answers": {}
        }

        self._add_room_member(room_id, user)

        return {
            "room_id": room_id,
            "joined": True,
            "host": self._member_payload(user),
            "players": [self._member_payload(user)],
            "game_mode": self.game_rooms[room_id].get("game_mode"),
        }

    async def join_room(self, room_id: str, user):
        if room_id not in self.game_rooms:
            raise HTTPException(
                status_code=404,
                detail="Room not found"
            )

        if user.id in self.game_rooms[room_id]["users"]:
            return {
                "room_id": room_id,
                "joined": True,
                "host": self.room_members[room_id].get(self.game_rooms[room_id]["host"]),
                "players": [
                    self.room_members[room_id][user_id]
                    for user_id in self.connections[room_id]
                    if user_id in self.room_members[room_id]
                ],
                "game_mode": self.game_rooms[room_id].get("game_mode"),
            }

        self._add_room_member(room_id, user)

        await self._broadcast_room_state(room_id)

        return {
            "room_id": room_id,
            "joined": True,
            "host": self.room_members[room_id].get(self.game_rooms[room_id]["host"]),
            "players": [
                self.room_members[room_id][user_id]
                for user_id in self.connections[room_id]
                if user_id in self.room_members[room_id]
            ],
            "game_mode": self.game_rooms[room_id].get("game_mode"),
        }
    
    async def select_game_mode(self, room_id: str, user, game_mode: str):
        room = self.game_rooms.get(room_id)

        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        if room["host"] != user.id:
            raise HTTPException(status_code=403, detail="Only the host can choose a game mode")

        if game_mode not in self.VALID_GAME_MODES:
            raise HTTPException(status_code=400, detail="Invalid game mode")

        room["game_mode"] = game_mode

        await self._broadcast(room_id, {
            "type": "game_mode_selected",
            "room_id": room_id,
            "game_mode": game_mode,
            "host": self.room_members[room_id].get(room["host"]),
        })

        return {
            "type": "game_mode_selected",
            "room_id": room_id,
            "game_mode": game_mode,
        }

    async def generate_questions(
        self,
        room_id: str,
        user,
        game_mode,
        db: AsyncSession
    ):
        room = self.game_rooms.get(room_id)

        spotify_users = []

        for member_id in room["users"]:
            spotify_user = await self.user_service.get_user_by_id(
                db,
                member_id
            )

            spotify_users.append(spotify_user)

        question_service = QuestionService(
            game_mode,
            spotify_users
        )

        room["question_service"] = question_service
        room["current_question"] = 0

    async def reveal_answer(self, room_id: str):
        room = self.game_rooms[room_id]

        question = room["current_question_data"]

        await self._broadcast(room_id, {
            "type": "answer",
            "answer": question["answer"],
            "question_id": room["current_question"],
            "reveal_extra": (
                f"Chart score: {question['track_b'].get('popularity')}/100"
                if question.get("type") == "higher_or_lower"
                and question.get("track_b", {}).get("popularity") is not None
                else None
            ),
        })


        await asyncio.sleep(4)

        await self.send_next_question(room_id)

    async def start_game(self, room_id: str, user):
        room = self.game_rooms.get(room_id)

        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        if room["host"] != user.id:
            raise HTTPException(status_code=403, detail="Only the host can start the game")

        if room.get("started", False):
            return {"type": "game_started", "room_id": room_id, "already_started": True}

        if not room.get("game_mode"):
            raise HTTPException(status_code=400, detail="Please select a game mode before starting")

        room["started"] = True

        print(f"Game started in room {room_id} by host {user.id} with mode {room['game_mode']}")

        await self._broadcast(room_id, {
            "type": "game_started",
            "room_id": room_id,
            "message": "Game started",
            "game_mode": room["game_mode"],
            "host": self.room_members[room_id].get(room["host"]),
        })

        return {"type": "game_started", "room_id": room_id, "game_mode": room["game_mode"]}

    async def leave_room(self, user: User):
        room_id = self._get_user_room_id(user.id)

        if room_id is None:
            raise HTTPException(
                status_code=404,
                detail="User is not in a room"
            )

        self._remove_room_member(room_id, user.id)
        self.game_rooms[room_id]["users"].discard(user.id)
        self.connections[room_id].pop(user.id, None)

        await self._broadcast_room_state(room_id)

        if not self.game_rooms[room_id]["users"]:
            del self.game_rooms[room_id]
            self.connections.pop(room_id, None)

        return {
            "room_id": room_id,
            "left": True,
        }
    
    async def send_next_question(self, room_id):
        room = self.game_rooms[room_id]
        room["answers"] = {}

        question_service = room["question_service"]
        question = await question_service.get_next_question()

        if not question:
            scores = []
            for user_id in room["users"]:
                scores.append({
                    "id": user_id,
                    "name": self.room_members[room_id][user_id]["display_name"],
                    "score": room["scores"].get(user_id, 0),
                })

            await self._broadcast(room_id, {
                "type": "game_over",
                "scores": scores,
            })
            return

        room["current_question_data"] = question

        client_question = dict(question)
        if client_question.get("type") == "higher_or_lower" and "track_b" in client_question:
            track_b = dict(client_question["track_b"])
            track_b.pop("popularity", None)
            client_question["track_b"] = track_b

        await self._broadcast(room_id, {
            "type": "question",
            "question": client_question,
        })

    async def send_score_update(self, room_id):
        room = self.game_rooms[room_id]

        scores = []

        for user_id in room["users"]:
            scores.append({
                "id": user_id,
                "name": self.room_members[room_id][user_id]["display_name"],
                "score": room["scores"].get(user_id, 0)
            })


        await self._broadcast(room_id, {
            "type": "score_update",
            "scores": scores
        })

    async def handle_answer(self, room_id, user, answer):
        room = self.game_rooms[room_id]
        room["answers"][user.id] = answer

        await self._broadcast(room_id, {
            "type": "player_answered",
            "user": user.username,
        })

        if len(room["answers"]) >= len(room["users"]):
            question = room["current_question_data"]
            correct = question["answer"]

            for user_id, submitted_answer in room["answers"].items():
                if submitted_answer == correct:
                    room["scores"][user_id] += 1

            await self.send_score_update(room_id)
            await self.reveal_answer(room_id)
            return True

    async def websocket_join(
        self,
        websocket: WebSocket,
        room_id: str,
        db: AsyncSession,
    ):
        token = websocket.cookies.get("access_token")

        if not token:
            await websocket.close(code=1008)
            return

        try:
            payload = jwt_service.verify_token(token)
            user = await self.user_service.get_user_by_id(db, payload["sub"])
        except Exception:
            await websocket.close(code=1008)
            return

        if user is None:
            await websocket.close(code=1008)
            return

        if room_id not in self.game_rooms:
            await websocket.accept()
            await websocket.send_json({
                "error": "Room not found"
            })
            await websocket.close()
            return

        if user.id not in self.game_rooms[room_id]["users"]:
            await websocket.accept()
            await websocket.send_json({
                "error": "Join the room before connecting"
            })
            await websocket.close()
            return

        await websocket.accept()

        self.connections[room_id][user.id] = websocket

        await websocket.send_json({
            "type": "connected",
            "room_id": room_id
        })

        await self._broadcast_room_state(room_id, exclude_user_id=user.id)

        await self._broadcast(room_id, {
            "type": "player_connected",
            "user": user.username
        }, exclude_user_id=user.id)

        try:
            while True:
                message = await websocket.receive_text()
                print(message)
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    payload = {"type": "message", "message": message}

                if payload.get("type") == "select_game_mode":
                    await self.select_game_mode(room_id, user, payload.get("game_mode"))
                    continue

                if payload.get("type") == "submit_answer":

                    await self.handle_answer(
                        room_id,
                        user,
                        payload.get("answer")
                    )

                    continue

                if payload.get("type") == "start_game":
                    room = self.game_rooms[room_id]
                    game_mode = payload.get("game_mode") or room.get("game_mode")
                    if game_mode not in self.VALID_GAME_MODES:
                        print("Game mode not in list")
                        continue

                    await self._broadcast_room_state(room_id)
                    await self.start_game(room_id, user)

                    await self.generate_questions(
                        room_id,
                        user,
                        game_mode,
                        db
                    )

                    await asyncio.sleep(2)
                    await self.send_next_question(room_id)
                    continue

                for ws in self.connections[room_id].values():
                    await ws.send_json({
                        "type": "message",
                        "user": user.username,
                        "message": message
                    })

        except WebSocketDisconnect:
            self.connections[room_id].pop(user.id, None)

            if room_id in self.game_rooms:
                await self._broadcast_room_state(room_id)
                await self._broadcast(room_id, {
                    "type": "player_disconnected",
                    "user": user.username
                })

    def _get_user_room_id(self, user_id: int):
        for room_id, room in self.game_rooms.items():
            if user_id in room["users"]:
                return room_id

        return None

    async def _broadcast(
        self,
        room_id: str,
        message: dict,
        exclude_user_id: int | None = None
    ):
        for user_id, websocket in self.connections[room_id].items():
            if user_id != exclude_user_id:
                await websocket.send_json(message)