from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Body
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2, database
from . import cart
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)

# In this version: should be called from cart.checkout
# TODO: add total amount calculation logic here only, if relied on user, then it will be prone to manipulation
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.OrderOut) # TODO: make arrangements such that this method can only be called from cart.checkout
def create_order(address: str, total_amount: Optional[float], db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    """
    Create a new order for the current user.
    This function checks if the cart is empty, retrieves items from the cart
    and reduces the stock of the products accordingly and increases the order count for each product.
    It also checks if the products exist and if there is sufficient stock for each product.
    It then creates an order with the provided address and total amount.
    Then it adds the order items to the order and commits the changes to the database.
    THis function also clears the cart after processing the order.
    Raises HTTPException if the cart is empty, if any product is not found,
    or if there is insufficient stock for any product.
    """
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
        product.num_sold += item.quantity  # Increment order count for the product
        db.commit()

    # Create the order
    new_order = models.Orders(
        user_id=current_user.id,
        address=address,
        total_amount=total_amount,
        status="Pending"
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    for item in cart_items:
        order_item = models.OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=product.price  # Assuming product has a price attribute
        )
        db.add(order_item)
    db.commit()

    cart.clear_cart(db, current_user)  # Clear the cart after processing the order

    return new_order

@router.get("/", response_model=List[schemas.OrderOut])
def get_orders(db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)): # TODO: add query parameters later
    """
    Retrieve all orders for the current user.
    Raises HTTPException if no orders are found for the user.
    """
    orders = db.query(models.Orders).filter(models.Orders.user_id == current_user.id).all()
    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No orders found")
    return orders

@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    """
    Retrieve a specific order by order_id for the current user.
    Raises HTTPException if the order is not found or does not belong to the user.
    """
    order = db.query(models.Orders).filter(models.Orders.id == order_id, models.Orders.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order

@router.patch("/{order_id}", response_model=schemas.OrderOut)
def update_order(order_id: int, orderUpdate: schemas.OrderUpdate, db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    """
    Update the status of an order by order_id for the current user.
    The status can be one of the following: "Pending", "Shipped", "Delivered", "Cancelled".
    Raises HTTPException if the order is not found, does not belong to the user,
    or if the order status cannot be updated (e.g., if it is already delivered or cancelled).

    if the order is cancelled, the stock of the products will be restored
    and the number of items sold will be decremented.

    Address can be updated now

    Currently, total_amount cannot be updated.
    If the order is cancelled, additional refund logic can be added later.
    """
    order = db.query(models.Orders).filter(models.Orders.id == order_id, models.Orders.user_id == current_user.id).first()
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status == "Delivered":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update a delivered order")
    if order.status == "Cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update a cancelled order")
    
    new_status = orderUpdate.status
    if new_status:
        if new_status not in ["Pending", "Shipped", "Delivered", "Cancelled"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
        order.status = new_status
    
        if new_status == "Cancelled":
            # TODO: add refund logic if needed
            for item in order.items:
                product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
                if product:
                    product.stock += item.quantity
                    product.num_sold -= item.quantity
                    # db.commit()

    if orderUpdate.address:
        # Address of order cannot be updated 24 hours after the order is placed
        if order.created_at.replace(tzinfo = None) + timedelta(hours=24) < datetime.now().replace(tzinfo=None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update address after 24 hours of order placement")
        order.address = orderUpdate.address

    db.commit()
    db.refresh(order)
    
    return order