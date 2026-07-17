import os
import json
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./resume.db"

    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS: List[str] = ['.pdf', '.docx', '.txt']

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173"
    ]

    # Environment
    ENVIRONMENT: str = "development"

    # Job Search
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            # Handle JSON array format
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma separated
            return [
                origin.strip()
                for origin in v.split(",")
                if origin.strip()
            ]
        return v

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            return [
                ext.strip()
                for ext in v.split(",")
                if ext.strip()
            ]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not self.SECRET_KEY:
            raise ValueError("❌ SECRET_KEY must be set!")

        if not self.GEMINI_API_KEY:
            raise ValueError("❌ GEMINI_API_KEY must be set!")

        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

settings = Settings()