import os
from pydantic_settings import BaseSettings


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
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt"

    # CORS - stored as string, parsed to list via property
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Environment
    ENVIRONMENT: str = "development"

    # Job Search
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set!")

        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY must be set!")

        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

    @property
    def allowed_origins_list(self) -> list:
        """Parse ALLOWED_ORIGINS string to list"""
        if not self.ALLOWED_ORIGINS:
            return ["http://localhost:3000"]
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def allowed_extensions_list(self) -> list:
        """Parse ALLOWED_EXTENSIONS string to list"""
        return [
            ext.strip()
            for ext in self.ALLOWED_EXTENSIONS.split(",")
            if ext.strip()
        ]


settings = Settings()