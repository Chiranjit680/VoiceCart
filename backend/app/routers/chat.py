from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime
from jose import JWTError
import uuid
import json
import sys
import os
from .. import models, schemas, oauth2, database

from .websockets_server import ConnectionManager

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def chat_with_agent(
    user_id: int,  # Keep as int
    websocket: WebSocket,
    db: Session = Depends(database.get_db),
):
    """WebSocket endpoint for chatting with the VoiceCart agent"""
    
    # First, try to get and verify the token
    try:
        token = websocket.query_params.get("token")
        if not token:
            print("❌ No token provided")
            await websocket.close(code=1008, reason="Token is required")
            return
        
        print(f"🔑 Received token: {token[:20]}...")
        
        # Verify the token
        current_user = oauth2.verify_access_token(token, credentials_exception=None)
        if not current_user:
            print("❌ Token verification failed")
            await websocket.close(code=1008, reason="Invalid token")
            return

        print(f"✅ Token verified for user ID: {current_user.id}")
        
        # Check if the token user matches the URL user (both are integers)
        if current_user.id != user_id:
            print(f"❌ User ID mismatch: token={current_user.id}, url={user_id}")
            await websocket.close(code=1008, reason="User ID mismatch")
            return
            
    except JWTError as e:
        print(f"❌ JWT Error: {e}")
        await websocket.close(code=1008, reason="Invalid token")
        return
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # If we reach here, authentication was successful
    try:
        print(f"🔌 Connecting WebSocket for user {current_user.id}")
        await manager.connect(websocket)
        
        # Send welcome message as JSON
        welcome_message = {
            "message": "Hello! I'm VoiceCart, your shopping assistant. How can I help you today?",
            "timestamp": datetime.now().isoformat(),
            "type": "welcome",
            "user_id": current_user.id
        }
        
        await websocket.send_text(json.dumps(welcome_message))
        print(f"📨 Welcome message sent to user {current_user.id}")

        # Pass the integer user_id directly (NO UUID conversion)
        await manager.websocket_agent_chat(user_id, websocket, db)
        
    except WebSocketDisconnect:
        print(f"🔌 User {current_user.id} disconnected normally")
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"❌ Chat error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
        finally:
            manager.disconnect(websocket, user_id)

# Test endpoint without authentication
@router.websocket("/ws/test")
async def chat_test(
    websocket: WebSocket,
    db: Session = Depends(database.get_db),
):
    """Test WebSocket endpoint without authentication"""
    try:
        await manager.connect(websocket)
        
        welcome_message = {
            "message": "Hello! This is a test connection to VoiceCart assistant.",
            "timestamp": datetime.now().isoformat(),
            "type": "welcome",
            "user_id": "test_user"
        }
        
        await websocket.send_text(json.dumps(welcome_message))
        
        # Use integer 999 for test user
        await manager.websocket_agent_chat(999, websocket, db)
        
    except WebSocketDisconnect:
        print("Test user disconnected")
        manager.disconnect(websocket, 999)
    except Exception as e:
        print(f"Test chat error: {e}")
        manager.disconnect(websocket, 999)

@router.get("/test")
async def test_chat():
    """Test endpoint to verify chat router is working"""
    return {"message": "Chat router is working!", "status": "success"}

@router.get("/debug/auth")
async def debug_auth(current_user: models.User = Depends(oauth2.get_current_user)):
    """Debug endpoint to test authentication"""
    return {
        "message": "Authentication working", 
        "user_id": current_user.id,
        "user_email": current_user.email
    }
