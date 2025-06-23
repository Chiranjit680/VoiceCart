from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2

router = APIRouter(
    prefix="/cart",
    tags=["cart"],
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.CartOut)
def add_to_cart(cart_item: schemas.CartCreate, db: Session = Depends(models.get_db), current_user: int = Depends(oauth2.get_current_user)):
    new_item = models.Cart(**cart_item.model_dump(), user_id=current_user.id)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@router.get("/", response_model=List[schemas.CartOut])
def get_cart(db: Session = Depends(models.get_db), current_user: int = Depends(oauth2.get_current_user)):
    cart_items = db.query(models.Cart).filter(models.Cart.user_id == current_user.id).all()
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart is empty")
    return cart_items

@router.delete("/{cart_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_cart(cart_item_id: int, db: Session = Depends(models.get_db), current_user: int = Depends(oauth2.get_current_user)):
    cart_item = db.query(models.Cart).filter(models.Cart.id == cart_item_id, models.Cart.user_id == current_user.id).first()
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    
    db.delete(cart_item)
    db.commit()
    return {"detail": "Item removed from cart"}

@router.delete("/product/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_product_from_cart(product_id: int, db: Session = Depends(models.get_db), current_user: int = Depends(oauth2.get_current_user)):
    cart_item = db.query(models.Cart).filter(models.Cart.product_id == product_id, models.Cart.user_id == current_user.id).all()
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    
    db.delete(cart_item)
    db.commit()
    return {"detail": "Product removed from cart"}