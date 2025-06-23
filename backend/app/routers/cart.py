from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2, database
from . import orders

router = APIRouter(
    prefix="/cart",
    tags=["cart"],
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.CartOut)
def add_to_cart(cart_item: schemas.CartCreate, db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    existing_item = db.query(models.Cart).filter(
        models.Cart.product_id == cart_item.product_id,
        models.Cart.user_id == current_user.id
    ).first()

    if existing_item:
        # If the product already exists in the cart, update the quantity
        existing_item.quantity += cart_item.quantity
        db.commit()
        db.refresh(existing_item)
        return existing_item

    # If the product does not exist in the cart, create a new cart item
    new_cart_item = models.Cart(**cart_item.model_dump(), user_id=current_user.id)
    db.add(new_cart_item)
    db.commit()
    db.refresh(new_cart_item)
    return new_cart_item

@router.get("/", response_model=List[schemas.CartOut])
def get_cart(db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    cart_items = db.query(models.Cart).filter(models.Cart.user_id == current_user.id).all()
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart is empty")
    return cart_items

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_product_from_cart(product_id: int, db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    cart_item = db.query(models.Cart).filter(models.Cart.product_id == product_id, models.Cart.user_id == current_user.id).all()
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    
    db.delete(cart_item)
    db.commit()
    return {"detail": "Product removed from cart"}

@router.patch("/{product_id}", response_model=schemas.CartOut)
def update_cart_item(product_id: int, cart_item: schemas.CartCreate, db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    existing_item = db.query(models.Cart).filter(models.Cart.product_id == product_id, models.Cart.user_id == current_user.id).first()
    
    if not existing_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    
    # Update the quantity of the existing cart item
    existing_item.quantity = cart_item.quantity
    db.commit()
    db.refresh(existing_item)
    return existing_item

# dummy checkout endpoint
@router.post("/checkout", status_code=status.HTTP_200_OK)
def checkout(db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    cart_items = db.query(models.Cart).filter(models.Cart.user_id == current_user.id).all()
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart is empty")
    
    for item in cart_items:
        if models.product.stock < item.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Not enough stock for product {item.product_id}")
    
    # Here you would typically process the payment and create an order
    # TODO: Implement payment processing logic
    # For now, we will just clear the cart

    for item in cart_items:
        db.query(models.product).filter(models.product.id == item.product_id).update({"stock": models.product.stock - item.quantity})  # Update stock based on cart items
        db.delete(item)

    orders.create_order(db, current_user.id, cart_items)  # TODO check it
    
    db.commit()
    return {"detail": "Checkout successful, cart cleared"}