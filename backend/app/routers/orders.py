from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2, database
from . import cart

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.OrderOut) # TODO: make arrangements such that this method can only be called from cart.checkout
def create_order(address: str, total_amount: float, db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    
    # Check if the cart is empty
    cart_items = db.query(models.Cart).filter(models.Cart.user_id == current_user.id).all()
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty. Please add items to the cart before placing an order.")
    
    # remove items from cart and reduce the stock
    for item in cart_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with id {item.product_id} not found")
        
        if product.stock < item.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient stock for product {product.name}")
        
        # Reduce the stock and delete item from cart
        product.stock -= item.quantity
        db.commit()

    # Create the order
    new_order = models.Order(
        user_id=current_user.id,
        address=address,
        total_amount=total_amount,
        status="Pending",
       products=[{"product_id": item.product_id, "quantity": item.quantity} for item in cart_items]  # List of dictionaries# Assuming products is a list of product IDs and quantities
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    cart.clear_cart(db, current_user)  # Clear the cart after processing the order

    return new_order

@router.get("/", response_model=List[schemas.OrderOut])
def get_orders(db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)): # TODO: add query parameters later
    orders = db.query(models.Order).filter(models.Order.user_id == current_user.id).all()
    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No orders found")
    return orders

@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    order = db.query(models.Order).filter(models.Order.id == order_id, models.Order.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order

@router.patch("/{order_id}", response_model=schemas.OrderOut)
def update_order(order_id: int, status: str, db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    order = db.query(models.Order).filter(models.Order.id == order_id, models.Order.user_id == current_user.id).first()
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status == "Delivered":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update a delivered order")
    if order.status == "Cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update a cancelled order")
    
    # address and total_amount cannot be updated
    if status not in ["Pending", "Shipped", "Delivered", "Cancelled"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
    
    if status == "Cancelled":
        pass # TODO: add refund logic if needed

    order.status = status
    db.commit()
    db.refresh(order)
    
    return order