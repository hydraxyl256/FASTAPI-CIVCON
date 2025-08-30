from fastapi import FastAPI, WebSocket, Depends, HTTPException, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from .routers.oauth2 import get_current_user
from . import models
from .database import engine, get_db
from .routers import user, post, auth, vote, search, comments, groups, categories, notifications, messages, live_feeds, admin
from .config import settings
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import json
from datetime import datetime

# Initialize FastAPI app
app = FastAPI()

# Mount the uploads directory
app.mount("/Uploads", StaticFiles(directory="Uploads"), name="uploads")

# CORS configuration
origins = [
    "https://www.google.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# models.Base.metadata.create_all(bind=engine)

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

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_message(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

manager = ConnectionManager()

# WebSocket for real-time notifications
connected_users = {}  # Store WebSocket connections by user_id for notifications

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    token = websocket.query_params.get("token")
    try:
        current_user = await get_current_user(token=token, db=db)
        connected_users[current_user.id] = websocket
        await websocket.accept()
        try:
            while True:
                await websocket.receive_text()  # Keep connection alive
        except Exception:
            if current_user.id in connected_users:
                del connected_users[current_user.id]
            await websocket.close()
    except HTTPException:
        await websocket.close(code=1008, reason="Unauthorized")

# WebSocket for real-time direct messaging
@app.websocket("/ws/{user_id}")
async def websocket_messaging(websocket: WebSocket, user_id: int, token: str, db: AsyncSession = Depends(get_db)):
    try:
        # Authenticate user
        current_user = await get_current_user(token=token, db=db)
        if current_user.id != user_id:
            await websocket.close(code=1008, reason="Unauthorized: user_id mismatch")
            return
        if not current_user.is_active:
            await websocket.close(code=1008, reason="Unauthorized: user is suspended")
            return

        # Connect WebSocket
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
    except HTTPException:
        await websocket.close(code=1008, reason="Unauthorized")