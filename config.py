from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "VinylTube Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Serveur
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Frontend
    FRONTEND_BUILD_PATH: str = "./static"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Downloads
    DOWNLOAD_DIR: str = "./downloads"
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB
    MAX_TOTAL_SIZE_MB: int = 2000  # 2GB maximum pour le dossier downloads
    CLEANUP_INTERVAL: int = 1800  # 30 minutes en secondes (plus fréquent en prod)
    FILE_RETENTION: int = 6 * 3600  # 6 heures (plus court en prod)
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_WINDOW: int = 60  # secondes
    
    class Config:
        env_file = ".env"

settings = Settings()
