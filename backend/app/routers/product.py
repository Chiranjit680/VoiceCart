from .. import models, schemas, database, oauth2
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..utils import products as product_utils


router = APIRouter(
    prefix="/product",
    tags=["product"],
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.ProductOut)
def create_product(product: schemas.ProductCreate, categories: List[schemas.CategoryCreate], db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)): 
    """
    Create a new product with associated categories.
    This function checks if the user is an admin before allowing product creation.
    It creates a new product and associates it with the provided categories.
    If a category does not exist, it creates a new category.
    """
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

    db.refresh(new_product)
    categories = [pc.category for pc in new_product.categories]
    return product_utils.add_category(new_product, db)

# I don't think this function associates parent categories with products, so it is not needed.
@router.get("/{id}", response_model=schemas.ProductOut)
def get_product(id: int, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    """
    Retrieve a product by its ID.
    This function fetches a product from the database by its ID and also retrieves its associated categories
    if the product exists. If the product does not exist, it raises a 404 error.
    """
    product = db.query(models.Product).filter(models.Product.id == id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    # fetch categories
    categories = db.query(models.Category).join(models.ProductCategory).filter(models.ProductCategory.product_id == id).all()
    # product.categories = categories
    return product_utils.add_category(product, db)

@router.get("/stock/{id}")
def get_product_stock(id: int, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    """
    Retrieve the stock of a product by its ID.
    This function fetches the stock of a product from the database by its ID.
    If the product does not exist, it raises a 404 error.
    It returns the stock quantity of the product.
    """
    product = db.query(models.Product).filter(models.Product.id == id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return {"stock": product.stock}


@router.get("/", response_model=List[schemas.ProductOut])
def get_all_products(db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)): # TODO: add query parameters for filtering, sorting, and pagination
    """
    Retrieve all products.
    This function fetches all products from the database and retrieves their associated categories.
    It returns a list of products, each with its categories populated.
    If no products are found, it returns an empty list.
    """
    products = db.query(models.Product).all()
    res = []
    for product in products:
        # fetch categories for each product
        categories = db.query(models.Category).join(models.ProductCategory).filter(models.ProductCategory.product_id == product.id).all()
        res.append(product_utils.add_category(product, db))
    return res

@router.patch("/{id}", response_model=schemas.ProductOut)
def update_product(id: int, product: schemas.ProductUpdate, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    """
    Update an existing product by its ID.
    This function allows an admin user to update the details of a product.
    It checks if the user is an admin before allowing the update.
    If the product does not exist, it raises a 404 error.
    """
    # Check if the user is an admin
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to update products")

    existing_product = db.query(models.Product).filter(models.Product.id == id).first()
    if not existing_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    for key, value in product.model_dump(exclude_unset=True).items():
        setattr(existing_product, key, value)
    
    db.commit()
    db.refresh(existing_product)
    
    return product_utils.add_category(existing_product, db)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(id: int, db: Session = Depends(database.get_db), current_user: schemas.UserOut = Depends(oauth2.get_current_user)):
    """
    Delete a product by its ID.
    This function allows an admin user to delete a product from the database.
    It checks if the user is an admin before allowing the deletion.
    If the product does not exist, it raises a 404 error.
    """
    # Check if the user is an admin
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete products")
    
    existing_product = db.query(models.Product).filter(models.Product.id == id).first()
    if not existing_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    db.delete(existing_product)
    db.commit()
    
    return {"detail": "Product deleted successfully"}