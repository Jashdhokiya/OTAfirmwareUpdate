"""
Smart OTA Fleet Manager — FastAPI Application Entry Point

Assembles all API routes, starts MQTT client, seeds admin user,
and configures CORS for cross-network access.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.core.config import settings
from app.core.database import engine, async_session, Base
from app.models import *  # noqa: F401, F403 — import all models for metadata
from app.api.v1 import auth, devices, firmware, deployments, device_api
from app.security.auth import hash_password
from app.mqtt.client import mqtt_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("fleet_manager")


# ─── WebSocket manager for real-time dashboard updates ───
class ConnectionManager:
    """Manages WebSocket connections for live dashboard updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


ws_manager = ConnectionManager()


# ─── Lifespan: startup and shutdown logic ───
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting Smart OTA Fleet Manager...")

    # Seed admin user
    await seed_admin()

    # Start MQTT client
    try:
        mqtt_client.set_event_loop(asyncio.get_running_loop())
        mqtt_client.connect()
        logger.info("MQTT client started")

        # Register MQTT handlers
        from app.mqtt.handlers import register_mqtt_handlers
        register_mqtt_handlers()
    except Exception as e:
        logger.warning(f"MQTT client failed to start: {e} (broker may not be running)")

    yield

    # Shutdown
    mqtt_client.disconnect()
    logger.info("Fleet Manager shutdown complete")


async def seed_admin():
    """Create the initial admin user if it doesn't exist."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        if not result.scalar_one_or_none():
            admin = User(
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                full_name="Administrator",
                role="admin",
            )
            session.add(admin)
            await session.commit()
            logger.info(f"Admin user created: {settings.ADMIN_EMAIL}")


# ─── Create FastAPI app ───
app = FastAPI(
    title="Smart OTA Fleet Manager",
    description="IoT fleet management platform for ESP32 OTA updates",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the frontend and any ngrok URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Mount API routes ───
app.include_router(auth.router, prefix="/api/v1")
app.include_router(devices.router, prefix="/api/v1")
app.include_router(firmware.router, prefix="/api/v1")
app.include_router(deployments.router, prefix="/api/v1")
app.include_router(device_api.router, prefix="/api/v1")


# ─── WebSocket endpoint ───
@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ─── Health check ───
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mqtt_connected": mqtt_client.is_connected,
        "version": "1.0.0",
    }
