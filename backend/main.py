from fastapi import FastAPI
from dotenv import load_dotenv
from app.api.spotify_oauth import login
from routers.spotify_auth import router as spotify_router
from routers.user_auth import router as user_auth_router
from routers.spotify_requests import router as spotify_requests_router
from routers.game_room import router as game_room_router
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   
        "http://127.0.0.1:3000",
        "http://localhost:5173",  
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5500", 
        "null",                   
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(spotify_router)
app.include_router(user_auth_router)
app.include_router(spotify_requests_router)
app.include_router(game_room_router)
@app.get("/")
async def root():
    login()
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    return {"status": "ok"}