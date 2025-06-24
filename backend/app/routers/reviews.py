from .. import models, schemas, database, oauth2
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

router = APIRouter(
    prefix="/reviews",
    tags=["review"],
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.ReviewOut)
def create_review(review: schemas.ReviewCreate, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    # Check if the product exists
    product = db.query(models.Product).filter(models.Product.id == review.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Create the review
    new_review = models.Reviews(**review.model_dump(), user_id=current_user.id)
    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return new_review

@router.get("/{id}", response_model=schemas.ReviewOut)
def get_review(id: int, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    review = db.query(models.Reviews).filter(models.Reviews.id == id).first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    
    return review

@router.get("/product/{product_id}", response_model=List[schemas.ReviewOut])
def get_reviews_by_product(product_id: int, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    reviews = db.query(models.Reviews).filter(models.Reviews.product_id == product_id).all()
    if not reviews:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No reviews found for this product")
    
    return reviews

@router.get("/user/{user_id}", response_model=List[schemas.ReviewOut])
def get_reviews_by_user(user_id: int, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    reviews = db.query(models.Reviews).filter(models.Reviews.user_id == user_id).all()
    if not reviews:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No reviews found for this user")
    
    return reviews

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(id: int, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    review = db.query(models.Reviews).filter(models.Reviews.id == id).first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this review")
    
    db.delete(review)
    db.commit()
    return {"detail": "Review deleted successfully"}

@router.put("/{id}", response_model=schemas.ReviewOut)
def update_review(id: int, review: schemas.ReviewCreate, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    existing_review = db.query(models.Reviews).filter(models.Reviews.id == id).first()
    if not existing_review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if existing_review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to update this review")
    
    # Update the review fields
    for key, value in review.model_dump().items():
        setattr(existing_review, key, value)
    
    db.commit()
    db.refresh(existing_review)
    
    return existing_review