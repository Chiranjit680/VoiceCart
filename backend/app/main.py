from fastapi import FastAPI
from . import models
from .routers import cart, orders, product, user
from .database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(user.router)
app.include_router(product.router)
app.include_router(cart.router)
app.include_router(orders.router)

@app.get("/")
async def root():
    return {"message": "Welcome to VoiceCart!"}