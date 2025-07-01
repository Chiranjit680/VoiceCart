from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: int

# --- User Schemas ---
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_admin: Optional[bool] = False

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_admin: bool
    created_at: datetime

    class Config:
        orm_mode = True

class User(UserOut):
    orders: List["OrderOut"] = []
    cart: List["CartOut"] = []
    reviews: List["ReviewOut"] = []

# --- Product Schemas ---
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    specs: Optional[Dict[str, str]] = None  # JSON field
    price: float
    for_sale: Optional[bool] = True
    stock: Optional[int] = 0
    brand_name: Optional[str] = None

class ProductOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    specs: Optional[Dict[str, str]] = None 
    price: float
    for_sale: bool
    stock: int
    brand_name: Optional[str] = None
    created_at: datetime
    categories: List["CategoryOut"] = []
    avg_rating: float = 0.0
    num_reviews: int = 0
    num_sold: int = 0

    class Config:
        orm_mode = True

# --- Category Schemas ---
class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None

class CategoryOut(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    children: List["CategoryOut"] = []

    class Config:
        orm_mode = True

# --- ProductCategory Schemas (for many-to-many) ---
class ProductCategoryCreate(BaseModel):
    product_id: int
    category_id: int

class ProductCategoryOut(BaseModel):
    product_id: int
    category_id: int

    class Config:
        orm_mode = True

# --- Cart Schemas ---
class CartCreate(BaseModel):
    product_id: int
    quantity: int

class CartOut(BaseModel):
    user_id: int
    product_id: int
    quantity: int
    product: Optional[ProductOut] = None

    class Config:
        orm_mode = True

# --- Order Item Schemas ---
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    price: float

class OrderItemOut(BaseModel):
    order_id: int
    product_id: int
    quantity: int
    price: float
    product: Optional[ProductOut] = None

    class Config:
        orm_mode = True

# --- Order Schemas ---
class OrderCreate(BaseModel):
    address: str
    total_amount: float

class OrderOut(BaseModel):
    id: int
    user_id: int
    address: str
    total_amount: float
    status: str
    created_at: datetime
    items: List[OrderItemOut] = []

    class Config:
        orm_mode = True

# --- Review Schemas ---
class ReviewCreate(BaseModel):
    product_id: int
    rating: int
    comment: Optional[str] = None

class ReviewOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    user: Optional[UserOut] = None
    product: Optional[ProductOut] = None

    class Config:
        orm_mode = True

class ProductSearchOut(ProductOut):
    relevance_score: float

# --- Chat Schemas ---
class ChatInput(BaseModel):
    input_text: str


# For forward references (self-referencing models)
User.update_forward_refs()
CategoryOut.update_forward_refs()
OrderOut.update_forward_refs()
ReviewOut.update_forward_refs()
ProductOut.update_forward_refs()