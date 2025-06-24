from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database, oauth2
from typing import List

router = APIRouter(
    prefix="/search",
    tags=["search"],
)

@router.get("/products", response_model=List[schemas.ProductOut]) # TODO: add filtering and pagination
def search_products(
    query: str,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(oauth2.get_current_user)
):
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    
    products = db.query(models.Product).filter(
        or_(
            models.Product.name.ilike(f"%{query}%"),
            models.Product.categories.contains(query),
            models.Product.description.ilike(f"%{query}%")
            )).all()
    
    if not products:
        raise HTTPException(status_code=404, detail="No products found matching the query")
    
    for product in products:
        # fetch categories for each product
        categories = db.query(models.Category).join(models.ProductCategory).filter(models.ProductCategory.product_id == product.id).all()
        product.categories = categories
    
    return products