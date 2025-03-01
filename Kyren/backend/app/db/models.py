from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class UserRole(str, Enum):
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"

class OrderStatus(str, Enum):
    PENDING = "pending"  # Group not formed yet
    CONFIRMED = "confirmed"  # Group formed, awaiting full payment
    PAID = "paid"  # Full payment completed
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    bale_id = Column(String, unique=True, index=True)
    username = Column(String, index=True)
    name = Column(String)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    role = Column(String, default=UserRole.BUYER)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = relationship("Product", back_populates="seller")
    orders = relationship("Order", back_populates="buyer")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float)
    image_url = Column(String, nullable=True)
    available_qty = Column(Integer, default=0)
    min_group_size = Column(Integer, default=1)  # Minimum buyers for discount
    discount_percentage = Column(Float, default=0.0)  # Discount percentage when min_group_size is reached
    
    # For tiered discounts
    discount_tiers = relationship("DiscountTier", back_populates="product")
    
    # Relationships
    seller = relationship("User", back_populates="products")
    group_buys = relationship("GroupBuy", back_populates="product")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DiscountTier(Base):
    __tablename__ = "discount_tiers"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    group_size = Column(Integer)  # Number of buyers required for this discount
    discount_percentage = Column(Float)  # Discount percentage for this tier
    
    # Relationships
    product = relationship("Product", back_populates="discount_tiers")

class GroupBuy(Base):
    __tablename__ = "group_buys"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    current_count = Column(Integer, default=0)  # Current number of buyers
    target_count = Column(Integer)  # Target number for group completion
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration time
    
    # Relationships
    product = relationship("Product", back_populates="group_buys")
    orders = relationship("Order", back_populates="group_buy")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"))
    group_buy_id = Column(Integer, ForeignKey("group_buys.id"))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float)  # Original price
    discount_price = Column(Float, nullable=True)  # Price after discount
    deposit_amount = Column(Float)  # 10% upfront payment
    status = Column(String, default=OrderStatus.PENDING)
    
    # Shipping information
    shipping_address = Column(String, nullable=True)
    shipping_tracking = Column(String, nullable=True)
    
    # Relationships
    buyer = relationship("User", back_populates="orders")
    group_buy = relationship("GroupBuy", back_populates="orders")
    payment_transactions = relationship("PaymentTransaction", back_populates="order")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    amount = Column(Float)
    is_deposit = Column(Boolean, default=False)  # Whether this is the initial 10% deposit
    transaction_id = Column(String, nullable=True)  # Payment gateway transaction ID
    status = Column(String)  # success, pending, failed
    
    # Relationships
    order = relationship("Order", back_populates="payment_transactions")
    
    created_at = Column(DateTime, default=datetime.utcnow)