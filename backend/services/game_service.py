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
        "Guess the Year",
        "Guess the Artist",
        "Whats the song?",
        "Who Listened To This?",
        "Guess who? (Playlist)",
        "Find a Song From the Year",
        "Playlist Vibes",
        "Cover Art Blur",
        "Taste Twins",
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
            "host_id": self.game_rooms[room_id]["host"],
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
        db: AsyncSession,
        question_count: int = 15
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
            spotify_users,
            question_count
        )

        room["question_service"] = question_service
        room["current_question"] = 0

    def _taste_twins_verdict(self, overlap: int) -> str:
        if overlap == 0:
            return "Complete opposites — not a single artist in common! 🙅"

        if overlap <= 3:
            return f"Practically strangers — only {overlap} shared artist(s)."

        if overlap <= 8:
            return f"A few bangers in common — {overlap} shared artists."

        if overlap <= 15:
            return f"Basically musical twins — {overlap} shared artists!"

        return f"Soulmates?! {overlap} shared artists — do you two share a Spotify account? 💞"

    async def reveal_answer(self, room_id: str):
        room = self.game_rooms[room_id]

        question = room["current_question_data"]

        if question.get("type") == "match_the_year":
            target_year = int(question["target_year"])

            for user_id, submitted in room["answers"].items():
                name = self.room_members[room_id].get(user_id, {}).get("display_name", "Player")
                has_pick = isinstance(submitted, dict) and submitted.get("year")

                years_off = abs(target_year - int(submitted["year"])) if has_pick else None
                points = (5 - years_off) if has_pick else 0

                await self._broadcast(room_id, {
                    "type": "player_reveal",
                    "question_id": room["current_question"],
                    "user_id": user_id,
                    "name": name,
                    "track_name": submitted.get("name") if has_pick else None,
                    "track_artist": submitted.get("artist") if has_pick else None,
                    "year": submitted.get("year") if has_pick else None,
                    "years_off": years_off,
                    "points": points,
                })

                await asyncio.sleep(1.5)

            await self._broadcast(room_id, {
                "type": "answer",
                "answer": f"Target year: {target_year}",
                "question_id": room["current_question"],
                "reveal_extra": None,
            })

            await asyncio.sleep(2)

            await self.send_next_question(room_id)
            return
        elif question.get("type") == "taste_twins":
            target = int(question["target_overlap"])

            for user_id, submitted in room["answers"].items():
                name = self.room_members[room_id].get(user_id, {}).get("display_name", "Player")

                try:
                    guess = int(submitted)
                except (TypeError, ValueError):
                    guess = None

                points = (5 - abs(target - guess)) if guess is not None else 0

                await self._broadcast(room_id, {
                    "type": "player_reveal",
                    "question_id": room["current_question"],
                    "user_id": user_id,
                    "name": name,
                    "guess": guess,
                    "points": points,
                })

                await asyncio.sleep(1.2)

            await self._broadcast(room_id, {
                "type": "answer",
                "answer": f"The real number: {target} shared artists!",
                "question_id": room["current_question"],
                "reveal_extra": self._taste_twins_verdict(target),
            })

            await asyncio.sleep(2)

            await self.send_next_question(room_id)
            return
        else:
            round_points = room.get("last_round_points", {})
            round_scores = [
                {
                    "user_id": user_id,
                    "name": self.room_members[room_id].get(user_id, {}).get("display_name", "Player"),
                    "points": points,
                }
                for user_id, points in round_points.items()
            ]

            await self._broadcast(room_id, {
                "type": "answer",
                "answer": question["answer"],
                "question_id": room["current_question"],
                "reveal_extra": None,
                "round_scores": round_scores,
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

    def get_current_room(self, user: User):
        room_id = self._get_user_room_id(user.id)

        if room_id is None:
            return {"room_id": None}

        room = self.game_rooms[room_id]

        return {
            "room_id": room_id,
            "host": self.room_members[room_id].get(room["host"]),
            "players": [
                self.room_members[room_id][user_id]
                for user_id in room["users"]
                if user_id in self.room_members[room_id]
            ],
            "game_mode": room.get("game_mode"),
        }

    async def leave_room(self, user: User):
        room_id = self._get_user_room_id(user.id)

        if room_id is None:
            raise HTTPException(
                status_code=404,
                detail="User is not in a room"
            )

        room = self.game_rooms[room_id]
        was_host = room["host"] == user.id

        self._remove_room_member(room_id, user.id)
        room["users"].discard(user.id)
        self.connections[room_id].pop(user.id, None)

        if not room["users"]:
            del self.game_rooms[room_id]
            self.connections.pop(room_id, None)
            return {
                "room_id": room_id,
                "left": True,
            }

        if was_host:
            room["host"] = next(iter(room["users"]))

        await self._broadcast_room_state(room_id)

        if was_host:
            await self._broadcast(room_id, {
                "type": "host_changed",
                "room_id": room_id,
                "host": self.room_members[room_id].get(room["host"]),
            })

        return {
            "room_id": room_id,
            "left": True,
        }
    
    async def send_next_question(self, room_id):
        room = self.game_rooms[room_id]
        room["answers"] = {}

        question_service = room["question_service"]

        try:
            question = await question_service.get_next_question()
        except Exception as exc:
            print(f"Failed to generate question for room {room_id}: {exc}")
            question = None

        if not question:
            room["started"] = False

            scores = []
            for user_id in room["users"]:
                scores.append({
                    "id": user_id,
                    "name": self.room_members[room_id][user_id]["display_name"],
                    "score": room["scores"].get(user_id, 0),
                })

            await self._broadcast_room_state(room_id)

            await self._broadcast(room_id, {
                "type": "game_over",
                "scores": scores,
            })
            return

        room["current_question_data"] = question

        await self._broadcast(room_id, {
            "type": "question",
            "question": dict(question),
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
            round_points = {}

            if question.get("type") == "match_the_year":
                target_year = int(question["target_year"])

                for user_id, submitted_answer in room["answers"].items():
                    submitted_year = (
                        submitted_answer.get("year")
                        if isinstance(submitted_answer, dict)
                        else None
                    )

                    if submitted_year is None:
                        round_points[user_id] = 0
                        continue

                    years_off = abs(target_year - int(submitted_year))
                    points = 5 - years_off
                    round_points[user_id] = points
                    room["scores"][user_id] += points
            elif question.get("type") == "guess_the_song":
                correct = question["answer"]
                max_clues = len(question.get("clues", [])) or 5

                for user_id, submitted_answer in room["answers"].items():
                    if not isinstance(submitted_answer, dict) or submitted_answer.get("option") != correct:
                        round_points[user_id] = 0
                        continue

                    clues_shown = submitted_answer.get("clues_shown") or 1
                    clues_shown = max(1, min(max_clues, int(clues_shown)))
                    points = (max_clues - clues_shown) + 1
                    round_points[user_id] = points
                    room["scores"][user_id] += points
            elif question.get("type") == "cover_art_blur":
                correct = question["answer"]
                max_stages = question.get("blur_stages") or 5

                for user_id, submitted_answer in room["answers"].items():
                    if not isinstance(submitted_answer, dict) or submitted_answer.get("option") != correct:
                        round_points[user_id] = 0
                        continue

                    blur_stage = submitted_answer.get("blur_stage") or 1
                    blur_stage = max(1, min(max_stages, int(blur_stage)))
                    points = (max_stages - blur_stage) + 1
                    round_points[user_id] = points
                    room["scores"][user_id] += points
            elif question.get("type") == "taste_twins":
                target = int(question["target_overlap"])

                for user_id, submitted_answer in room["answers"].items():
                    try:
                        guess = int(submitted_answer)
                    except (TypeError, ValueError):
                        round_points[user_id] = 0
                        continue

                    points = 5 - abs(target - guess)
                    round_points[user_id] = points
                    room["scores"][user_id] += points
            else:
                correct = question["answer"]

                for user_id, submitted_answer in room["answers"].items():
                    if submitted_answer == correct:
                        round_points[user_id] = 1
                        room["scores"][user_id] += 1
                    else:
                        round_points[user_id] = 0

            room["last_round_points"] = round_points

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

        await self._broadcast_room_state(room_id)

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
                    try:
                        await self.select_game_mode(room_id, user, payload.get("game_mode"))
                    except HTTPException as exc:
                        await websocket.send_json({"type": "error", "message": exc.detail})
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
                        await websocket.send_json({"type": "error", "message": "Invalid game mode"})
                        continue

                    try:
                        question_count = int(payload.get("question_count", 15))
                    except (TypeError, ValueError):
                        question_count = 15
                    question_count = max(5, min(20, question_count))

                    try:
                        await self._broadcast_room_state(room_id)
                        await self.start_game(room_id, user)
                    except HTTPException as exc:
                        await websocket.send_json({"type": "error", "message": exc.detail})
                        continue

                    await self.generate_questions(
                        room_id,
                        user,
                        game_mode,
                        db,
                        question_count
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