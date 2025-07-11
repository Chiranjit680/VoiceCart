import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from sqlmodel import Session
from typing import List
import uuid
from jose import JWTError
from .. import models, oauth2
from dotenv import load_dotenv
import os

# Load environment variables first
load_dotenv()

# Get the API key and validate it
gemini_api_key = os.getenv("GEMINI_API_KEY")  # Changed from GOOGLE_API_KEY to GEMINI_API_KEY
if not gemini_api_key:
    print("⚠️ Warning: GEMINI_API_KEY not found in environment variables")
    gemini_api_key = None

# Initialize client only if API key is available
client = None
if gemini_api_key:
    try:
        from google import genai
        client = genai.Client(api_key=gemini_api_key)
        print("✅ Google GenAI client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize GenAI client: {e}")
        client = None
else:
    print("❌ Cannot initialize GenAI client: No API key provided")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def agent_response(self, user_message: str) -> str:
        """Get response from the agent with fallback."""
        if not client:
            return self.get_fallback_response(user_message)
        
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=user_message
            )
            return response.text if response and hasattr(response, 'text') else "No response from agent."
        except Exception as e:
            print(f"GenAI API error: {e}")
            return self.get_fallback_response(user_message)
    
    def get_fallback_response(self, user_message: str) -> str:
        """Simple fallback responses when API is not available"""
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["hello", "hi", "hey"]):
            return "Hello! I'm VoiceCart, your shopping assistant. How can I help you today?"
        elif "cart" in message_lower:
            return "I can help you with your cart! You can ask me to show your cart, add items, or remove items."
        elif any(word in message_lower for word in ["search", "find", "product"]):
            return "I can search for products! What are you looking for?"
        elif "help" in message_lower:
            return "I can help you search for products, manage your cart, and place orders. What would you like to do?"
        else:
            return "I'm VoiceCart, your shopping assistant. I can help you search for products and manage your cart. What would you like to do?"

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Broadcast error: {e}")

    async def send_personal_message(
        self, message: str, websocket: WebSocket, user_id: uuid.UUID, db: Session
    ):
        try:
            # Create chat message (fix the enum usage)
            chat_message = models.ChatMessage(
                user_id=int(user_id),  # Convert UUID to int if needed
                message=message,
                sender="agent",  # Use string instead of enum
            )
            
            # Use sync database operations (remove asyncio.to_thread)
            db.add(chat_message)
            db.commit()
            db.refresh(chat_message)

            # Send via WebSocket
            await websocket.send_text(f"Agent: {message}")
            
        except Exception as e:
            print(f"Error saving/sending message: {e}")
            # Still send the message even if DB fails
            await websocket.send_text(f"Agent: {message}")

    async def websocket_agent_chat(
        self, user_id: uuid.UUID, websocket: WebSocket, db: Session
    ):
        try:
            # Send welcome message
            welcome_msg = "Hello! I'm VoiceCart, your shopping assistant. How can I help you today?"
            await self.send_personal_message(welcome_msg, websocket, user_id, db)
            
            while True:
                data = await websocket.receive_text()
                
                # Save user message
                try:
                    chat_message = models.ChatMessage(
                        user_id=int(user_id),  # Convert UUID to int if needed
                        message=data,
                        sender="user",  # Use string instead of enum
                    )
                    db.add(chat_message)
                    db.commit()
                    db.refresh(chat_message)
                except Exception as db_error:
                    print(f"Database error: {db_error}")
                
                # Get agent response
                agent_response = await self.agent_response(data)
                await self.send_personal_message(agent_response, websocket, user_id, db)
                
        except WebSocketDisconnect:
            print(f"User {user_id} disconnected")
            self.disconnect(websocket)
        except Exception as e:
            print(f"WebSocket error: {e}")
            self.disconnect(websocket)
