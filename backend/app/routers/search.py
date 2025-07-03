from time import sleep
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from .. import models, schemas, database, oauth2
from typing import List
from ..utils import filter as filter_utils, products as product_utils   

router = APIRouter(
    prefix="/search",
    tags=["search"],
)

@router.get("/products", response_model=List[schemas.ProductSearchOut]) # TODO: add filtering and pagination
def search_products(
    query: str,
    filters: dict = None,  # Placeholder for future filters
    categories: List[str] = None,  # Placeholder for future categories
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
        
        # Search for products matching the word in name, description, or brand_name
        matched_products = db.query(models.Product).filter(
            or_(
                models.Product.name.ilike(f"%{word}%"),
                models.Product.description.ilike(f"%{word}%"),
                models.Product.brand_name.ilike(f"%{word}%")
                )).all()
        
        # Matches in categories
        cat_list = db.query(models.Category).filter(
            or_(
                models.Category.name.ilike(f"%{word}%"),
                models.Category.parent_id.in_(
                    db.query(models.Category.id).filter(models.Category.name.ilike(f"%{word}%"))
                )
            )
        ).all()

        # list of products in matched categories
        cat_prod_list = db.query(models.ProductCategory).filter(
            models.ProductCategory.category_id.in_([cat.id for cat in cat_list])
        ).all()

        # Extend matched products with those in matched categories
        matched_products.extend(
            db.query(models.Product).filter(
                models.Product.id.in_([pc.product_id for pc in cat_prod_list])
            ).all()
        )

    # Remove duplicates while preserving order
    matched_products = list({product.id: product for product in matched_products}.values()) # dict comprehension to remove duplicates
    
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
                relevance += 10
            if word in (product.brand_name or "").lower():
                relevance += 6
            if word in str(product.description).lower():
                relevance += 2
            if word in str(product.specs).lower():
                relevance += 1
            
            # Check if the word matches any category name
            # TODO check here
            product_data = product_utils.add_category(product, db)


            if any(word in cat.name.lower() for cat in product_data.categories):
                relevance += 4

            # results.append(schemas.ProductSearchOut(**product_data, relevance_score=relevance))
            results.append(schemas.ProductSearchOut(
                **product_data.model_dump(),
                relevance_score=relevance
            ))

    # Apply filters if provided
    if filters or categories:
        results = filter_utils.filter_products(results, categories=categories, dict=filters)

    results.sort(key=lambda x: (x.relevance_score, x.num_sold), reverse=True)
    return results