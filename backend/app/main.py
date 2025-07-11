from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

from sympy import re

# Add the project root to Python path
current_file = os.path.abspath(__file__)
app_dir = os.path.dirname(current_file)  # backend/app
backend_dir = os.path.dirname(app_dir)   # backend
voicecart_dir = os.path.dirname(backend_dir)  # VoiceCart
project_root = os.path.dirname(voicecart_dir)  # Root

# Add paths to sys.path
paths_to_add = [project_root, voicecart_dir, backend_dir]
for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

# Now use absolute imports
from backend.app import models, database
from backend.app.routers import (
    user, 
    reviews,
    
    product, 
    cart, 
    orders, 
    search, 
    chat
)

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="VoiceCart API",
    description="Voice-enabled shopping cart application",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(user.router)
app.include_router(reviews.router)
app.include_router(product.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(search.router)
app.include_router(chat.router)

@app.get("/")
def root():
    return {"message": "Welcome to VoiceCart API!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "VoiceCart API is running"}