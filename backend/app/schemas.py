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