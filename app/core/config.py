from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    app_name: str = "SecureTradeAPI"
    debug: bool = False
    
    database_url: str = "postgresql://trader:secure_password@localhost/trading_platform"
    redis_url: str = "redis://localhost:6379"
    kafka_bootstrap_servers: str = "localhost:9092"
    
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    environment: str = "development"
    log_level: str = "INFO"
    
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    
    coinbase_api_key: Optional[str] = None
    coinbase_api_secret: Optional[str] = None
    
    class Config:
        env_file = ".env"


settings = Settings()