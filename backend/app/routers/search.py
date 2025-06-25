from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database, oauth2
from typing import List

router = APIRouter(
    prefix="/search",
    tags=["search"],
)

@router.get("/products", response_model=List[schemas.ProductSearchOut]) # TODO: add filtering and pagination
def search_products(
    query: str,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(oauth2.get_current_user)
):
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    
    query = query.strip().lower()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    matched_products = []
    
    for word in query.split():
        word = word.strip()
        if not word:
            continue
        
        # Search for products matching the word in name, categories, description, or brand_name
        matched_products = db.query(models.Product).filter(
            or_(
                models.Product.name.ilike(f"%{word}%"),
                models.Product.categories.contains(word),
                models.Product.description.ilike(f"%{word}%"),
                models.Product.brand_name.ilike(f"%{word}%")
                )).all()
    
    if not matched_products:
        raise HTTPException(status_code=404, detail="No products found matching the query")
    
    results: List[schemas.ProductSearchOut] = []

    for word in query.split():
        word = word.strip()
        if not word:
            continue

        for product in matched_products:
            relevance = 0
            if word in product.name.lower():
                relevance += 5
            if word in (product.brand_name or "").lower():
                relevance += 3
            if word in str(product.description).lower():
                relevance += 2
    
    results.append(schemas.ProductSearchOut(**product.__dict__, relevance_score=relevance))
    
    return results