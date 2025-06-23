from typing import List
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: int

class CartCreate(BaseModel):
    product_id: int
    quantity: int

class CartOut(CartCreate):
    user_id: int

class Order(BaseModel):
    products: List[CartCreate]
    address: str
    total_amount: float
    id: int
    user_id: int
    status: str