from time import sleep
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from .. import models, schemas, database, oauth2
from typing import List, Optional
from ..utils import filter as filter_utils, products as product_utils   

router = APIRouter(
    prefix="/search",
    tags=["search"],
)

def search_products(query: str, db: Session, limit: int = 20) -> List[models.Product]:
    """
    Search for products by name, description, or brand.
    
    Args:
        query: Search term
        db: Database session
        limit: Maximum number of results
        
    Returns:
        List of Product models (not ProductOut schemas)
    """
    try:
        # Search in products table
        product_results = db.query(models.Product).filter(
            or_(
                models.Product.name.ilike(f"%{query}%"),
                models.Product.description.ilike(f"%{query}%"),
                models.Product.brand_name.ilike(f"%{query}%")
            ),
            models.Product.for_sale == True
        ).limit(limit).all()

        # Search in categories and get related products
        category_results = db.query(models.Category).filter(
            or_(
                models.Category.name.ilike(f"%{query}%")
            )
        ).all()

        # Get products from matching categories
        if category_results:
            category_ids = [cat.id for cat in category_results]
            
            category_products = db.query(models.Product).join(
                models.ProductCategory
            ).filter(
                models.ProductCategory.category_id.in_(category_ids),
                models.Product.for_sale == True
            ).limit(limit).all()
            
            # Combine results and remove duplicates
            all_products = product_results + category_products
            seen_ids = set()
            unique_products = []
            
            for product in all_products:
                if product.id not in seen_ids:
                    unique_products.append(product)
                    seen_ids.add(product.id)
            
            return unique_products[:limit]
        
        return product_results
        
    except Exception as e:
        print(f"Search error: {e}")
        return []

@router.get("/", response_model=List[schemas.ProductOut])
def search_products_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(database.get_db)
):
    """Search for products endpoint"""
    try:
        products = search_products(query=q, db=db, limit=limit)
        
        # Convert to ProductOut schema safely
        result = []
        for product in products:
            try:
                # Create a safe dictionary without problematic fields
                product_dict = {
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "price": product.price,
                    "for_sale": product.for_sale,
                    "stock": product.stock,
                    "image": product.image,
                    "brand_name": product.brand_name,
                    "created_at": product.created_at,
                    "avg_rating": product.avg_rating,
                    "num_reviews": product.num_reviews,
                    "num_sold": product.num_sold,
                    "specs": product.specs if hasattr(product, 'specs') else {}
                }
                
                # Create ProductOut from dict
                product_out = schemas.ProductOut(**product_dict)
                result.append(product_out)
                
            except Exception as conversion_error:
                print(f"Error converting product {product.id}: {conversion_error}")
                continue
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")