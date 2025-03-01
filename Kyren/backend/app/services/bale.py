import logging
import aiohttp
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import crud

logger = logging.getLogger(__name__)

class BaleAPI:
    def __init__(self, token: str, api_url: str):
        self.token = token
        self.api_url = api_url
        self.session = None
    
    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None):
        session = await self._get_session()
        url = f"{self.api_url}/bot{self.token}/{endpoint}"
        
        try:
            async with session.request(method, url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    logger.error(f"Bale API error: {response.status} - {text}")
                    return {"ok": False, "error": text}
        except Exception as e:
            logger.error(f"Error making request to Bale API: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown"):
        """Send a message to a user through Bale"""
        return await self._make_request(
            "post", 
            "sendMessage", 
            {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
        )
    
    async def send_product_info(self, chat_id: int, product_data: Dict):
        """Send product information with an image and buttons"""
        text = f"*{product_data['name']}*\n\n"
        text += f"{product_data['description']}\n\n"
        text += f"Price: ${product_data['price']}\n"
        text += f"Discount: {product_data['discount_percentage']}% when {product_data['min_group_size']} buyers join"
        
        # Create inline keyboard for actions
        inline_keyboard = [
            [
                {"text": "Join Group Buy", "callback_data": f"join_group:{product_data['id']}"},
                {"text": "View Details", "callback_data": f"view_product:{product_data['id']}"}
            ]
        ]
        
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": inline_keyboard
            }
        }
        
        # If image_url exists, send photo with caption
        if product_data.get('image_url'):
            return await self._make_request(
                "post",
                "sendPhoto",
                {
                    "chat_id": chat_id,
                    "photo": product_data['image_url'],
                    "caption": text,
                    "parse_mode": "Markdown",
                    "reply_markup": {
                        "inline_keyboard": inline_keyboard
                    }
                }
            )
        
        # Otherwise send text message
        return await self._make_request("post", "sendMessage", data)
    
    async def answer_callback_query(self, callback_query_id: str, text: str = "", show_alert: bool = False):
        """Answer a callback query from an inline button"""
        return await self._make_request(
            "post",
            "answerCallbackQuery",
            {
                "callback_query_id": callback_query_id,
                "text": text,
                "show_alert": show_alert
            }
        )

# Initialize Bale API client
bale_client = BaleAPI(settings.BALE_TOKEN, settings.BALE_API_URL)

async def process_bale_update(update_data: Dict[str, Any], db: Session):
    """Process incoming updates from Bale webhook"""
    
    # Process messages
    if "message" in update_data:
        message = update_data["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        
        # Check if user exists, if not create user
        db_user = crud.get_user_by_bale_id(db, str(user_id))
        if not db_user:
            user_data = {
                "bale_id": str(user_id),
                "username": message["from"].get("username", ""),
                "name": f"{message['from'].get('first_name', '')} {message['from'].get('last_name', '')}".strip()
            }
            db_user = crud.create_user(db, user_data)
        
        # Process commands
        if "text" in message:
            text = message["text"]
            
            # Process commands
            if text.startswith("/start"):
                await bale_client.send_message(
                    chat_id,
                    "Welcome to Kyren Group Buying platform! Use the menu to browse products and join group purchases."
                )
                return {"type": "start_command", "user_id": user_id}
            
            elif text.startswith("/products"):
                # Fetch products and send them to the user
                products = crud.get_products(db, limit=5)
                for product in products:
                    await bale_client.send_product_info(chat_id, product.__dict__)
                
                return {"type": "products_command", "user_id": user_id, "product_count": len(products)}
            
            elif text.startswith("/myorders"):
                # Fetch user's orders
                orders = crud.get_user_orders(db, db_user.id)
                
                if not orders:
                    await bale_client.send_message(chat_id, "You don't have any orders yet.")
                else:
                    for order in orders:
                        await bale_client.send_message(
                            chat_id,
                            f"Order #{order.id}\n"
                            f"Product: {order.group_buy.product.name}\n"
                            f"Status: {order.status}\n"
                            f"Price: ${order.unit_price}\n"
                            f"Discount: ${order.unit_price - order.discount_price if order.discount_price else 0}"
                        )
                
                return {"type": "myorders_command", "user_id": user_id, "order_count": len(orders) if orders else 0}
    
    # Process callback queries (button clicks)
    elif "callback_query" in update_data:
        callback_query = update_data["callback_query"]
        user_id = callback_query["from"]["id"]
        callback_data = callback_query.get("data", "")
        
        await bale_client.answer_callback_query(callback_query["id"])
        
        # Get or create user
        db_user = crud.get_user_by_bale_id(db, str(user_id))
        if not db_user:
            user_data = {
                "bale_id": str(user_id),
                "username": callback_query["from"].get("username", ""),
                "name": f"{callback_query['from'].get('first_name', '')} {callback_query['from'].get('last_name', '')}".strip()
            }
            db_user = crud.create_user(db, user_data)
        
        # Process different button actions
        if callback_data.startswith("join_group:"):
            # Extract product ID
            product_id = int(callback_data.split(":")[1])
            
            # Find or create a group buy for this product
            group_buy = crud.get_or_create_active_group_buy(db, product_id)
            
            # Create an order with 10% deposit
            product = crud.get_product(db, product_id)
            deposit_amount = product.price * 0.1
            
            order = crud.create_order(
                db,
                {
                    "buyer_id": db_user.id,
                    "group_buy_id": group_buy.id,
                    "quantity": 1,
                    "unit_price": product.price,
                    "deposit_amount": deposit_amount
                }
            )
            
            # Send payment link or instructions
            await bale_client.send_message(
                callback_query["message"]["chat"]["id"],
                f"You've joined the group buy for *{product.name}*!\n\n"
                f"Please pay the initial deposit of ${deposit_amount:.2f} to confirm your participation.\n\n"
                f"Current group: {group_buy.current_count + 1}/{group_buy.target_count} buyers"
            )
            
            return {
                "type": "join_group",
                "user_id": user_id,
                "product_id": product_id,
                "group_buy_id": group_buy.id,
                "order_id": order.id
            }
        
        elif callback_data.startswith("view_product:"):
            # Extract product ID
            product_id = int(callback_data.split(":")[1])
            product = crud.get_product(db, product_id)
            
            # Get active group buy for this product
            group_buy = crud.get_active_group_buy(db, product_id)
            
            # Create detailed product view
            message = (
                f"*{product.name}*\n\n"
                f"{product.description}\n\n"
                f"Price: ${product.price:.2f}\n"
                f"Available: {product.available_qty} units\n\n"
                f"*Group Buying Details:*\n"
                f"Minimum group size: {product.min_group_size}\n"
                f"Discount: {product.discount_percentage}%\n"
            )
            
            if group_buy:
                message += f"Current group: {group_buy.current_count}/{group_buy.target_count} buyers\n"
            
            # Add discount tiers if any
            if product.discount_tiers:
                message += "\n*Discount Tiers:*\n"
                for tier in product.discount_tiers:
                    message += f"- {tier.group_size} buyers: {tier.discount_percentage}% discount\n"
            
            await bale_client.send_message(
                callback_query["message"]["chat"]["id"],
                message
            )
            
            return {
                "type": "view_product",
                "user_id": user_id,
                "product_id": product_id
            }
    
    return {"status": "unhandled_update"}