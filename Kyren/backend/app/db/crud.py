from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.db.models import User, Product, GroupBuy, Order, PaymentTransaction, DiscountTier, OrderStatus

# User operations
def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_bale_id(db: Session, bale_id: str):
    return db.query(User).filter(User.bale_id == bale_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user_data: Dict[str, Any]):
    db_user = User(**user_data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_data: Dict[str, Any]):
    db_user = get_user(db, user_id)
    if db_user:
        for key, value in user_data.items():
            setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user

# Product operations
def get_product(db: Session, product_id: int):
    return db.query(Product).filter(Product.id == product_id).first()

def get_products(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    query = db.query(Product)
    
    # Apply filters if provided
    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            )
        )
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    return query.offset(skip).limit(limit).all()

def create_product(db: Session, product_data: Dict[str, Any], discount_tiers: Optional[List[Dict[str, Any]]] = None):
    db_product = Product(**product_data)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # Add discount tiers if provided
    if discount_tiers:
        for tier_data in discount_tiers:
            tier = DiscountTier(
                product_id=db_product.id,
                group_size=tier_data["group_size"],
                discount_percentage=tier_data["discount_percentage"]
            )
            db.add(tier)
        
        db.commit()
        db.refresh(db_product)
    
    return db_product

def update_product(db: Session, product_id: int, product_data: Dict[str, Any]):
    db_product = get_product(db, product_id)
    if db_product:
        for key, value in product_data.items():
            setattr(db_product, key, value)
        db.commit()
        db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int):
    db_product = get_product(db, product_id)
    if db_product:
        db.delete(db_product)
        db.commit()
    return db_product

# GroupBuy operations
def get_group_buy(db: Session, group_id: int):
    return db.query(GroupBuy).filter(GroupBuy.id == group_id).first()

def get_active_group_buy(db: Session, product_id: int):
    return db.query(GroupBuy).filter(
        GroupBuy.product_id == product_id,
        GroupBuy.is_active == True
    ).first()

def get_or_create_active_group_buy(db: Session, product_id: int):
    # Check if there's an active group for this product
    group_buy = get_active_group_buy(db, product_id)
    
    if not group_buy:
        # No active group, create one
        product = get_product(db, product_id)
        group_buy = GroupBuy(
            product_id=product_id,
            target_count=product.min_group_size,
            current_count=0,
            is_active=True
        )
        db.add(group_buy)
        db.commit()
        db.refresh(group_buy)
    
    return group_buy

def create_group_buy(db: Session, group_data: Dict[str, Any]):
    db_group = GroupBuy(**group_data)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

def get_incomplete_groups(db: Session):
    """Get active groups that haven't reached their target count"""
    return db.query(GroupBuy).filter(
        GroupBuy.is_active == True,
        GroupBuy.current_count < GroupBuy.target_count
    ).all()

def get_expired_groups(db: Session, threshold_date: datetime):
    """Get active groups that haven't been updated since the threshold date"""
    return db.query(GroupBuy).filter(
        GroupBuy.is_active == True,
        GroupBuy.updated_at < threshold_date,
        GroupBuy.current_count < GroupBuy.target_count
    ).all()

# Order operations
def get_order(db: Session, order_id: int):
    return db.query(Order).filter(Order.id == order_id).first()

def get_orders_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(Order).filter(Order.buyer_id == user_id).offset(skip).limit(limit).all()

def get_orders_by_group(db: Session, group_id: int):
    return db.query(Order).filter(Order.group_buy_id == group_id).all()

def create_order(db: Session, order_data: Dict[str, Any]):
    db_order = Order(**order_data)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

def update_order_status(db: Session, order_id: int, new_status: OrderStatus):
    db_order = get_order(db, order_id)
    if db_order:
        db_order.status = new_status
        db.commit()
        db.refresh(db_order)
    return db_order

# Payment operations
def create_payment(db: Session, payment_data: Dict[str, Any]):
    db_payment = PaymentTransaction(**payment_data)
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

def get_payments_by_order(db: Session, order_id: int):
    return db.query(PaymentTransaction).filter(PaymentTransaction.order_id == order_id).all()

# Database connection
def get_db():
    """
    Generator function to provide database sessions to FastAPI endpoints.
    
    Usage:
    ```
    @app.get("/users/{user_id}")
    def read_user(user_id: int, db: Session = Depends(get_db)):
        db_user = get_user(db, user_id)
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return db_user
    ```
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    
    engine = create_engine(str(settings.DATABASE_URI))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()