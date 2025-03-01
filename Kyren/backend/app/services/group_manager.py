import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import GroupBuy, Order, OrderStatus
from app.services.bale import bale_client

logger = logging.getLogger(__name__)

async def process_new_order(db: Session, order_id: int) -> Dict[str, Any]:
    """
    Process a new order in a group buy.
    This function is called when a user joins a group buy and pays the deposit.
    It checks if the group is now complete and processes accordingly.
    """
    order = crud.get_order(db, order_id)
    if not order:
        logger.error(f"Order {order_id} not found")
        return {"status": "error", "message": "Order not found"}
    
    group_buy = order.group_buy
    product = group_buy.product
    
    # Update group buy with new order
    group_buy.current_count += 1
    db.commit()
    
    # Check if group is now complete
    if group_buy.current_count >= group_buy.target_count:
        # Group is complete, update status
        group_buy.is_active = False
        
        # Calculate discount based on group size
        discount_percentage = get_discount_percentage(product, group_buy.current_count)
        
        # Update all orders in this group
        orders = crud.get_orders_by_group(db, group_buy.id)
        for order in orders:
            # Calculate discounted price
            order.discount_price = order.unit_price * (1 - (discount_percentage / 100))
            order.status = OrderStatus.CONFIRMED
            
            # Notify the buyer
            await bale_client.send_message(
                int(order.buyer.bale_id),
                f"Good news! Your group buy for *{product.name}* is now complete!\n\n"
                f"Total buyers: {group_buy.current_count}\n"
                f"Discount: {discount_percentage}%\n"
                f"Your discounted price: ${order.discount_price:.2f}\n\n"
                f"Please complete your payment to finalize your order."
            )
        
        db.commit()
        return {
            "status": "success",
            "message": "Group buy completed",
            "group_buy_id": group_buy.id,
            "discount_percentage": discount_percentage
        }
    
    # Group is not complete yet, notify the buyer
    await bale_client.send_message(
        int(order.buyer.bale_id),
        f"You've successfully joined the group buy for *{product.name}*!\n\n"
        f"Current group size: {group_buy.current_count}/{group_buy.target_count}\n"
        f"We'll notify you when the group is complete."
    )
    
    return {
        "status": "success",
        "message": "Added to group buy",
        "group_buy_id": group_buy.id,
        "current_count": group_buy.current_count,
        "target_count": group_buy.target_count
    }

def get_discount_percentage(product, group_size: int) -> float:
    """
    Calculate the discount percentage based on the group size and product discount tiers.
    """
    # Check if product has discount tiers
    if product.discount_tiers:
        # Find the highest applicable tier
        applicable_tiers = [
            tier for tier in product.discount_tiers 
            if tier.group_size <= group_size
        ]
        
        if applicable_tiers:
            # Sort by discount percentage (highest first)
            applicable_tiers.sort(key=lambda x: x.discount_percentage, reverse=True)
            return applicable_tiers[0].discount_percentage
    
    # If no tiers or no applicable tier, use the default discount
    if group_size >= product.min_group_size:
        return product.discount_percentage
    
    return 0.0

async def rearrange_incomplete_groups(db: Session) -> Dict[str, Any]:
    """
    Rearrange buyers in incomplete groups to form complete groups where possible.
    This is run periodically or when groups expire.
    """
    # Get all active but incomplete groups
    incomplete_groups = crud.get_incomplete_groups(db)
    
    if not incomplete_groups:
        return {"status": "success", "message": "No incomplete groups to rearrange"}
    
    # Group by product
    product_groups = {}
    for group in incomplete_groups:
        if group.product_id not in product_groups:
            product_groups[group.product_id] = []
        product_groups[group.product_id].append(group)
    
    results = []
    
    # Process each product's groups
    for product_id, groups in product_groups.items():
        product = crud.get_product(db, product_id)
        
        # Get all orders from these groups
        all_orders = []
        for group in groups:
            orders = crud.get_orders_by_group(db, group.id)
            all_orders.extend(orders)
        
        # Sort orders by creation date (oldest first)
        all_orders.sort(key=lambda x: x.created_at)
        
        # Calculate how many complete groups we can form
        total_buyers = len(all_orders)
        complete_groups_possible = total_buyers // product.min_group_size
        
        if complete_groups_possible > 0:
            # Create new groups and assign orders
            for i in range(complete_groups_possible):
                # Create a new group
                new_group = crud.create_group_buy(
                    db,
                    {
                        "product_id": product_id,
                        "target_count": product.min_group_size,
                        "current_count": product.min_group_size,
                        "is_active": False  # Completed immediately
                    }
                )
                
                # Assign orders to this group
                start_idx = i * product.min_group_size
                group_orders = all_orders[start_idx:start_idx + product.min_group_size]
                
                # Calculate discount
                discount_percentage = get_discount_percentage(product, product.min_group_size)
                
                # Update orders
                for order in group_orders:
                    order.group_buy_id = new_group.id
                    order.status = OrderStatus.CONFIRMED
                    order.discount_price = order.unit_price * (1 - (discount_percentage / 100))
                    
                    # Notify the buyer
                    await bale_client.send_message(
                        int(order.buyer.bale_id),
                        f"Good news! We've rearranged groups and your order for *{product.name}* is now part of a complete group!\n\n"
                        f"Discount: {discount_percentage}%\n"f"Your discounted price: ${order.discount_price:.2f}\n\n"
                    f"Please complete your payment to finalize your order."
                    )
                
                db.commit()
                
                results.append({
                    "product_id": product_id,
                    "new_group_id": new_group.id,
                    "order_count": len(group_orders),
                    "discount_percentage": discount_percentage
                })
            
            # Handle remaining orders (if any)
            remaining_count = total_buyers % product.min_group_size
            if remaining_count > 0:
                # Create a new active group for remaining buyers
                new_active_group = crud.create_group_buy(
                    db,
                    {
                        "product_id": product_id,
                        "target_count": product.min_group_size,
                        "current_count": remaining_count,
                        "is_active": True
                    }
                )
                
                # Assign remaining orders
                remaining_orders = all_orders[complete_groups_possible * product.min_group_size:]
                for order in remaining_orders:
                    order.group_buy_id = new_active_group.id
                    
                    # Notify the buyer
                    await bale_client.send_message(
                        int(order.buyer.bale_id),
                        f"We've rearranged groups for *{product.name}*. You're now in a new group with {remaining_count}/{product.min_group_size} buyers.\n\n"
                        f"We'll notify you when the group is complete."
                    )
                
                db.commit()
                
                results.append({
                    "product_id": product_id,
                    "new_active_group_id": new_active_group.id,
                    "current_count": remaining_count,
                    "target_count": product.min_group_size
                })
            
            # Close the old incomplete groups
            for group in groups:
                group.is_active = False
            db.commit()
    
    return {"status": "success", "rearrangements": results}

async def check_expired_groups(db: Session) -> Dict[str, Any]:
    """
    Check for expired groups and process them.
    This is run periodically (e.g., daily) to find groups that haven't reached completion.
    """
    # Find groups that haven't been updated in 7 days (configurable)
    expiration_threshold = datetime.utcnow() - timedelta(days=7)
    expired_groups = crud.get_expired_groups(db, expiration_threshold)
    
    if not expired_groups:
        return {"status": "success", "message": "No expired groups"}
    
    # Process each expired group
    for group in expired_groups:
        # Get orders in this group
        orders = crud.get_orders_by_group(db, group.id)
        
        # Notify buyers
        for order in orders:
            await bale_client.send_message(
                int(order.buyer.bale_id),
                f"The group buy for *{group.product.name}* didn't reach the minimum number of buyers within the timeframe.\n\n"
                f"Your deposit will be refunded. You can join another group buy for this product if you're still interested."
            )
            
            # Mark order as cancelled
            order.status = OrderStatus.CANCELLED
        
        # Mark group as inactive
        group.is_active = False
        
    db.commit()
    
    # After processing expired groups, try to rearrange other incomplete groups
    rearrangement_result = await rearrange_incomplete_groups(db)
    
    return {
        "status": "success",
        "expired_groups_count": len(expired_groups),
        "rearrangement_result": rearrangement_result
    }