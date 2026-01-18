"""
Sales Intelligence Platform - Main Server
Enterprise-grade FastAPI application with modular architecture
"""
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List
import logging
import os

from core.config import settings
from core.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Sales Intelligence Platform...")
    
    try:
        await Database.connect(settings.MONGO_URL, settings.DB_NAME)
        logger.info("Database connected successfully")
        
        # Initialize RBAC system (roles, permissions, departments)
        from services.rbac.service import RBACService
        rbac = RBACService(Database.get_db())
        await rbac.initialize()
        logger.info("RBAC system initialized")
        
        # Seed demo data if needed
        await seed_demo_data()
        
        # Start background sync service (5 minute interval)
        try:
            from services.sync.background_sync import start_background_sync
            await start_background_sync(interval_minutes=5)
            logger.info("Background sync service started (5 min interval)")
        except Exception as e:
            logger.warning(f"Failed to start background sync: {e}")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    # Stop background sync
    try:
        from services.sync.background_sync import stop_background_sync
        await stop_background_sync()
    except Exception:
        pass
        
    await Database.disconnect()


# Create FastAPI app
app = FastAPI(
    title="Sales Intelligence Platform",
    description="Enterprise-grade Sales CRM with ERP Integration",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware (add before error handlers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router with /api prefix
api_router = APIRouter(prefix="/api")


# ===================== HEALTH CHECK =====================

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "sales-intelligence-platform"}


@api_router.get("/health")
async def api_health_check():
    """API health check with database status"""
    try:
        db = Database.get_db()
        await db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "version": "2.0.0"
    }


# ===================== IMPORT ROUTES =====================

from routes.auth import router as auth_router
from routes.data_lake import router as data_lake_router
from routes.integrations import router as integrations_router
from routes.webhooks import router as webhooks_router
from routes.admin import router as admin_router
from routes.admin_logs import router as admin_logs_router  # NEW: Admin logging
from routes.personal import router as personal_router
from routes.sales import router as sales_router
from routes.config import router as config_router
from routes.goals import router as goals_router
from routes.teams import router as teams_router  # NEW: Team management
from routes.portfolios import router as portfolios_router  # NEW: Portfolio management
from routes.initiatives import router as initiatives_router  # NEW: Initiative tracking
from api.v2_dashboard import router as v2_dashboard_router  # CQRS v2 API
from api.v2_activities import router as v2_activities_router  # CQRS v2 Activities API
from api.cqrs_sync_api import router as cqrs_sync_router  # CQRS sync endpoints

# Import Odoo routes factory (will be instantiated after DB connection)
from odoo_routes import create_odoo_routes

# Register routes
api_router.include_router(auth_router)
api_router.include_router(data_lake_router)
api_router.include_router(integrations_router)
api_router.include_router(webhooks_router)

# Create and register Odoo router dynamically
from services.auth.jwt_handler import get_current_user_from_token
try:
    # Simple role requirement wrapper for Odoo routes
    def require_role_wrapper(roles: List[str]):
        async def dependency(token_data: dict = Depends(get_current_user_from_token)):
            db = Database.get_db()
            user = await db.users.find_one({"id": token_data["id"]}, {"is_super_admin": 1})
            if user and user.get("is_super_admin"):
                return token_data
            raise HTTPException(status_code=403, detail="Admin access required")
        return dependency
    
    odoo_router = create_odoo_routes(
        db=Database.get_db(),
        get_current_user=get_current_user_from_token,
        require_role=require_role_wrapper
    )
    api_router.include_router(odoo_router)
    logger.info("Odoo Integration routes registered")
except Exception as e:
    logger.error(f"Failed to register Odoo routes: {e}", exc_info=True)

api_router.include_router(admin_router)
api_router.include_router(admin_logs_router)  # Admin logging endpoints
api_router.include_router(personal_router)
api_router.include_router(sales_router)
api_router.include_router(config_router)
api_router.include_router(goals_router)
api_router.include_router(teams_router)  # NEW: Team management
api_router.include_router(portfolios_router)  # NEW: Portfolio management
api_router.include_router(initiatives_router)  # NEW: Initiative tracking
api_router.include_router(v2_dashboard_router, prefix="/v2/dashboard")  # CQRS v2
api_router.include_router(v2_activities_router, prefix="/v2/activities")  # CQRS v2 Activities
api_router.include_router(cqrs_sync_router, prefix="/integrations/cqrs")  # CQRS sync with prefix

# Mount API router
app.include_router(api_router)


# ===================== SEED DATA =====================

async def seed_demo_data():
    """Seed initial demo data if database is empty"""
    from datetime import datetime, timezone
    from services.auth.jwt_handler import hash_password
    import uuid
    
    db = Database.get_db()
    
    # Check if users exist
    user_count = await db.users.count_documents({})
    if user_count > 0:
        logger.info("Database already has data, skipping seed")
        return
    
    logger.info("Seeding demo data...")
    now = datetime.now(timezone.utc)
    
    # Create demo users
    users = [
        {
            "id": str(uuid.uuid4()),
            "email": "admin@salesintel.com",
            "password_hash": hash_password("admin123"),
            "name": "System Administrator",
            "role": "super_admin",
            "department": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "id": str(uuid.uuid4()),
            "email": "sales@salesintel.com",
            "password_hash": hash_password("demo123"),
            "name": "Sales Manager",
            "role": "account_manager",
            "department": "sales",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
    ]
    await db.users.insert_many(users)
    
    # Create default integration configs
    integrations = [
        {
            "id": str(uuid.uuid4()),
            "integration_type": "odoo",
            "enabled": False,
            "config": {},
            "sync_status": "pending",
            "created_at": now,
            "updated_at": now
        },
        {
            "id": str(uuid.uuid4()),
            "integration_type": "salesforce",
            "enabled": False,
            "config": {},
            "sync_status": "pending",
            "created_at": now,
            "updated_at": now
        },
        {
            "id": str(uuid.uuid4()),
            "integration_type": "ms365",
            "enabled": False,
            "config": {},
            "sync_status": "pending",
            "created_at": now,
            "updated_at": now
        }
    ]
    await db.integrations.insert_many(integrations)
    
    logger.info(f"Seeded {len(users)} users and {len(integrations)} integration configs")


# ===================== RUN SERVER =====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
