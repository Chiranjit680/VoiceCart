from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket
from sqlalchemy.orm import Session
from datetime import datetime
from jose import JWTError
import uuid
import json
import sys
import os
from .. import models, schemas, oauth2, database
current_file = os.path.abspath(__file__)
app_dir = os.path.dirname(current_file)  # backend/app
backend_dir = os.path.dirname(app_dir)   # backend
voicecart_dir = os.path.dirname(backend_dir)  # VoiceCart
project_root = os.path.dirname(voicecart_dir)   # Root

from backend.app import models, oauth2, database
    
from .websockets_server import ConnectionManager

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def chat_with_agent(
    user_id: uuid.UUID,
    websocket: WebSocket,
    db: Session = Depends(database.get_db),
):
    """WebSocket endpoint for chatting with the VoiceCart agent"""
    
    try:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008, reason="Token is required")
            return
        else:
            current_user = oauth2.verify_access_token(token, credentials_exception=None)
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
    #     return
    
    try:
        await manager.connect(websocket)
        
        # Send welcome message
        welcome_message = {
            "message": "Hello! I'm VoiceCart, your shopping assistant. How can I help you today?",
            "timestamp": datetime.now().isoformat(),
            "type": "welcome"
        }
        await manager.send_personal_message(json.dumps(welcome_message), websocket)
        
        # Start receiving messages
        await manager.receive_messages(user_id, websocket, db)
        
    except Exception as e:
        print(f"Chat error: {e}")
        await websocket.close()
        raise HTTPException(status_code=500, detail=str(e))

# Add a test endpoint
@router.get("/test")
async def test_chat():
    """Test endpoint to verify chat router is working"""
    return {"message": "Chat router is working!"}
