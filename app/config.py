import logging
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


# Load .env once when this module is imported
load_dotenv(dotenv_path=Path(".env"), override=False)


class Settings(BaseSettings):
    # Add your environment variables here
    GOOGLE_API_KEY: Optional[str] = None
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    REDIS_URL: str = "redis://localhost:6379"
    # Example: DATABASE_URL: Optional[str] = None
    LLM_MODEL_NAME: Optional[str] = None
    LLM_MODEL_PROVIDER: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    USE_LLM_ONLY: bool = False
    HEADLESS: bool = True
    


settings = Settings()


def setup_logging():
    """Set up logging configuration for the application"""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Set specific loggers
    logging.getLogger('app').setLevel(log_level)
    logging.getLogger('app.handlers').setLevel(log_level)
    logging.getLogger('app.services').setLevel(log_level)
    
    logging.info(f"Logging configured with level: {settings.LOG_LEVEL}")


# Auto-setup logging when module is imported
setup_logging()


