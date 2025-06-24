from .. import models, schemas, database, oauth2
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List


router = APIRouter(
    prefix="/product",
    tags=["product"],
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.ProductOut)
def create_product(product: schemas.ProductCreate, categories: List[schemas.CategoryCreate], db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)): 
    # Check if the user is an admin
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to create products")
    
    new_product = models.Product(**product.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    for category in categories:
        # check if the category exists
        existing_category = db.query(models.Category).filter(models.Category.name == category.name).first()
        if existing_category:
            product_category = models.ProductCategory(product_id=new_product.id, category_id=existing_category.id)
        else:
            new_category = models.Category(**category.model_dump())
            db.add(new_category)
            db.commit()
            db.refresh(new_category)
            product_category = models.ProductCategory(product_id=new_product.id, category_id=new_category.id)
        db.add(product_category)
    db.commit()
    return new_product

@router.get("/{id}", response_model=schemas.ProductOut)
def get_product(id: int, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    product = db.query(models.Product).filter(models.Product.id == id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    # fetch categories
    categories = db.query(models.Category).join(models.ProductCategory).filter(models.ProductCategory.product_id == id).all()
    product.categories = categories
    return product

@router.get("/stock/{id}")
def get_product_stock(id: int, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    product = db.query(models.Product).filter(models.Product.id == id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return {"stock": product.stock}


@router.get("/", response_model=List[schemas.ProductOut])
def get_all_products(db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)): # TODO: add query parameters for filtering, sorting, and pagination
    products = db.query(models.Product).all()
    for product in products:
        # fetch categories for each product
        categories = db.query(models.Category).join(models.ProductCategory).filter(models.ProductCategory.product_id == product.id).all()
        product.categories = categories
    return products

@router.patch("/{id}", response_model=schemas.ProductOut)
def update_product(id: int, product: schemas.ProductCreate, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    # Check if the user is an admin
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to update products")

    existing_product = db.query(models.Product).filter(models.Product.id == id).first()
    if not existing_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    for key, value in product.model_dump().items():
        setattr(existing_product, key, value)
    
    db.commit()
    db.refresh(existing_product)
    
    return existing_product

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(id: int, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    # Check if the user is an admin
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete products")
    
    existing_product = db.query(models.Product).filter(models.Product.id == id).first()
    if not existing_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    db.delete(existing_product)
    db.commit()
    
    return {"detail": "Product deleted successfully"}

@router.get("/categories", response_model=List[schemas.CategoryOut])
def get_all_categories(db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    categories = db.query(models.Category).all()
    return categories

@router.post("/categories", status_code=status.HTTP_201_CREATED, response_model=schemas.CategoryOut)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    # Check if the user is an admin
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to create categories")
       
    new_category = models.Category(**category.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category