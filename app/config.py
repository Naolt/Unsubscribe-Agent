from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


# Load .env once when this module is imported
load_dotenv(dotenv_path=Path(".env"), override=False)


class Settings(BaseSettings):
    # Add your environment variables here
    GOOGLE_API_KEY: Optional[str] = None
    # Example: DATABASE_URL: Optional[str] = None


settings = Settings()


