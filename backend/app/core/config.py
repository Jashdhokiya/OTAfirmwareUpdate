"""
Application configuration loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Central configuration for the Fleet Manager backend."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://fleet_admin:devpassword123@localhost:5432/fleet_manager"

    # JWT Authentication
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Admin seed
    ADMIN_EMAIL: str = "admin@fleet.local"
    ADMIN_PASSWORD: str = "admin123"

    # Public URL (set to ngrok URL for cross-network access)
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # MQTT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: str = "fleet_backend"
    MQTT_PASSWORD: str = "fleet_mqtt_pass"

    # Firmware storage
    FIRMWARE_STORAGE_PATH: str = "./storage"
    MAX_FIRMWARE_SIZE_MB: int = 4

    # Device health
    DEVICE_OFFLINE_TIMEOUT_SECONDS: int = 120  # 2 minutes without heartbeat = offline
    HEARTBEAT_INTERVAL_SECONDS: int = 30

    # Deployment
    DEPLOYMENT_COMMAND_TIMEOUT_SECONDS: int = 300  # 5 min timeout for device to respond
    DEPLOYMENT_OBSERVATION_PERIOD_SECONDS: int = 60  # Watch device after update

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
