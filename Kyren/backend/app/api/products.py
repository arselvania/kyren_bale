from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.crud import get_db, get_products, get_product, create_product, update_product, delete_product
from app.db.models import UserRole

router = APIRouter()

class DiscountTierCreate(BaseModel):
    group_size: int = Field(..., description="Number of buyers required for this discount tier")
    discount_percentage: float = Field(..., description="Discount percentage for this tier")

class ProductCreate(BaseModel):
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product description")
    price: float = Field(..., description="Product price")
    image_url: Optional[str] = Field(None, description="URL to product image")
    available_qty: int = Field(..., description="Available quantity")
    min_group_size: int = Field(..., description="Minimum buyers for discount")
    discount_percentage: float = Field(..., description="Discount percentage")
    discount_tiers: Optional[List[DiscountTierCreate]] = Field(None, description="Optional tiered discounts")

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    available_qty: Optional[int] = None
    min_group_size: Optional[int] = None
    discount_percentage: Optional[float] = None

class DiscountTierResponse(BaseModel):
    id: int
    group_size: int
    discount_percentage: float

class ProductResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    image_url: Optional[str]
    available_qty: int
    min_group_size: int
    discount_percentage: float
    seller_id: int
    discount_tiers: Optional[List[DiscountTierResponse]] = None

@router.get("/", response_model=List[ProductResponse])
def read_products(
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Get all products with optional filtering
    """
    products = get_products(
        db, 
        skip=skip, 
        limit=limit, 
        search=search,
        min_price=min_price,
        max_price=max_price
    )
    return products

@router.get("/{product_id}", response_model=ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    """
    Get a specific product by ID
    """
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.post("/", response_model=ProductResponse)
def create_new_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Create a new product (seller only)
    """
    # Note: In a real implementation, we would check user authentication and authorization
    # to ensure only sellers can create products.
    # For now, we'll assume the seller_id is provided or determined from auth token
    
    # Dummy seller_id for demonstration
    seller_id = 1  # In reality, this would come from the authenticated user
    
    product_data = product.dict()
    
    # Extract discount_tiers from the request data
    discount_tiers = None
    if "discount_tiers" in product_data:
        discount_tiers = product_data.pop("discount_tiers")
    
    # Add seller_id to product data
    product_data["seller_id"] = seller_id
    
    # Create the product
    db_product = create_product(db, product_data, discount_tiers)
    return db_product

@router.put("/{product_id}", response_model=ProductResponse)
def update_existing_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing product (seller only)
    """
    # Check if product exists
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Note: In a real implementation, we would check if the authenticated user
    # is the seller of this product
    
    # Update the product
    updated_product = update_product(db, product_id, product.dict(exclude_unset=True))
    return updated_product

@router.delete("/{product_id}")
def delete_existing_product(product_id: int, db: Session = Depends(get_db)):
    """
    Delete a product (seller only)
    """
    # Check if product exists
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Note: In a real implementation, we would check if the authenticated user
    # is the seller of this product
    
    # Delete the product
    delete_product(db, product_id)
    return {"status": "success", "message": "Product deleted"}