import logging
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Base
from app.db.crud import get_db
from app.api import auth, products, groups, orders, payments
from app.services.bale import process_bale_update

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kyren Group Buying API",
    description="API for Kyren group buying platform integrated with Bale messenger",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(groups.router, prefix="/api/groups", tags=["Group Buys"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])

# Bale webhook endpoint
@app.post("/webhook/bale")
async def bale_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        logger.info(f"Received webhook from Bale: {data}")
        
        # Process the webhook data
        result = await process_bale_update(data, db)
        return {"status": "success", "message": "Webhook processed successfully", "data": result}
    
    except Exception as e:
        logger.error(f"Error processing Bale webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Kyren API"}

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Kyren API...")
    # Additional startup logic can be added here (DB initialization, etc.)

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Kyren API...")
    # Cleanup logic can be added here