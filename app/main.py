from fastapi import FastAPI, WebSocket, Depends, HTTPException, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from .routers.oauth2 import get_current_user
from . import models
from .database import engine, get_db
from .routers import user, post, auth, vote, search, comments, groups, categories, notifications, locations, messages, live_feeds, admin
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Mount the uploads directory
app.mount("/Uploads", StaticFiles(directory="Uploads"), name="uploads")

# CORS configuration
origins = [
    "http://localhost:3000",  # Frontend URL 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",  
    "*"  # Allow all for now (restrict in production)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log request bodies
@app.middleware("http")
async def log_requests(request, call_next):
    logger.debug(f"Request: {request.method} {request.url}")
    try:
        body = await request.body()
        logger.debug(f"Request body: {body.decode('utf-8')}")
    except Exception as e:
        logger.error(f"Error reading request body: {e}")
    response = await call_next(request)
    return response

# Include routers
app.include_router(user.router)
app.include_router(post.router)
app.include_router(auth.router)
app.include_router(vote.router)
app.include_router(search.router)
app.include_router(comments.router)
app.include_router(categories.router)
app.include_router(groups.router)
app.include_router(notifications.router)
app.include_router(messages.router)
app.include_router(admin.router)
app.include_router(live_feeds.router)
app.include_router(locations.router)

# Startup event for DB tables
@app.on_event("startup")
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    logger.info("Database tables created")

@app.get("/")
def root():
    return {"message": "Hello, world"}

# WebSocket connection manager for messaging
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.debug(f"WebSocket connected for user_id: {user_id}")

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.debug(f"WebSocket disconnected for user_id: {user_id}")

    async def send_message(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
            logger.debug(f"Sent message to user_id: {user_id}, message: {message}")

manager = ConnectionManager()

# WebSocket for real-time notifications
connected_users = {}

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        logger.warning("WebSocket closed: Missing token")
        return
    try:
        current_user = await get_current_user(token=token, db=db)
        connected_users[current_user.id] = websocket
        await websocket.accept()
        logger.debug(f"WebSocket notification connected for user_id: {current_user.id}")
        try:
            while True:
                await websocket.receive_text()  # Keep connection alive
        except WebSocketDisconnect:
            if current_user.id in connected_users:
                del connected_users[current_user.id]
            await websocket.close()
            logger.debug(f"WebSocket notification disconnected for user_id: {current_user.id}")
    except HTTPException as e:
        await websocket.close(code=1008, reason=f"Unauthorized: {e.detail}")
        logger.warning(f"WebSocket closed: {e.detail}")

# WebSocket for real-time direct messaging
@app.websocket("/ws/{user_id}")
async def websocket_messaging(websocket: WebSocket, user_id: int, db: AsyncSession = Depends(get_db)):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        logger.warning("WebSocket closed: Missing token")
        return
    try:
        current_user = await get_current_user(token=token, db=db)
        if current_user.id != user_id:
            await websocket.close(code=1008, reason="Unauthorized: user_id mismatch")
            logger.warning(f"WebSocket closed: user_id mismatch, requested {user_id}, got {current_user.id}")
            return
        if not current_user.is_active:
            await websocket.close(code=1008, reason="Unauthorized: user is suspended")
            logger.warning(f"WebSocket closed: user_id {user_id} is suspended")
            return

        await manager.connect(websocket, user_id)
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                if message.get("type") == "typing":
                    await manager.send_message(
                        message["recipient_id"],
                        {"type": "typing", "sender_id": user_id}
                    )
                else:
                    await manager.send_message(
                        message["recipient_id"],
                        {
                            "sender_id": user_id,
                            "content": message["content"],
                            "created_at": datetime.utcnow().isoformat()
                        }
                    )
        except WebSocketDisconnect:
            manager.disconnect(user_id)
            await websocket.close()
            logger.debug(f"WebSocket messaging disconnected for user_id: {user_id}")
    except HTTPException as e:
        await websocket.close(code=1008, reason=f"Unauthorized: {e.detail}")
        logger.warning(f"WebSocket closed: {e.detail}")