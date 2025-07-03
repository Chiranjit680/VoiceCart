from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, JSON, DECIMAL, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from sqlalchemy.sql.sqltypes import TIMESTAMP

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=True, server_default=None) # in development phase, this field is set to be nullable
    address = Column(String, nullable=True, server_default=None)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'))

    orders = relationship("Orders", back_populates="user", cascade="all, delete-orphan")
    cart = relationship("Cart", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Reviews", back_populates="user", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True, server_default=None)
    specs = Column(JSON, nullable=True, server_default=None)
    price = Column(DECIMAL(precision=10, scale=2), nullable=False) # price is currently not nullable, # but it can be changed in the future
    for_sale = Column(Boolean, default=True, nullable=False)
    stock = Column(Integer, default=0, nullable=False)
    # image_url = Column(String, nullable=True, server_default=None)
    image = Column(LargeBinary, nullable=True, server_default=None)  # Storing image as BLOB
    brand_name = Column(String, nullable=True, server_default=None)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'))
    avg_rating = Column(DECIMAL(precision=2, scale=1), default=0.0, nullable=False)  # Average rating of the product
    num_reviews = Column(Integer, default=0, nullable=False)  # Number of reviews for the product
    num_sold = Column(Integer, default=0, nullable=False)  # Number of items sold

    categories = relationship("ProductCategory", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("Reviews", back_populates="product", cascade="all, delete-orphan")
    cart = relationship("Cart", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, server_default=None)

    parent = relationship("Category", remote_side=[id], backref="children")

    products = relationship("ProductCategory", back_populates="category", cascade="all, delete-orphan")

class ProductCategory(Base):
    __tablename__ = "product_categories"

    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), primary_key=True, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'), primary_key=True, nullable=False)

    product = relationship("Product", back_populates="categories")
    category = relationship("Category", back_populates="products")

class Cart(Base):
    __tablename__ = "cart"

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), primary_key=True)
    quantity = Column(Integer, nullable=False, default=1)

    user = relationship("User", back_populates="cart")
    product = relationship("Product", back_populates="cart")

class Orders(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    total_amount = Column(DECIMAL(precision=10, scale=2), nullable=False)
    status = Column(String, default="pending", nullable=False)  # e.g., pending, completed, cancelled
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'))
    address = Column(String, nullable=True, server_default=None)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False, index=True, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False, primary_key=True)
    quantity = Column(Integer, default=1, nullable=False)
    price = Column(DECIMAL(precision=10, scale=2), nullable=False)  # Price at the time of order

    order = relationship("Orders", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class Reviews(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    rating = Column(Integer, nullable=False)  # e.g., 1 to 5 stars
    comment = Column(String, nullable=True, server_default=None)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'))

    user = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")