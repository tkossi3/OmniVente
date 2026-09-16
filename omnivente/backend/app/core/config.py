"""Configuration centrale de l'application OmniVente.

Toutes les valeurs sont lues depuis le fichier `backend/.env`.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Application ---
    APP_NAME: str = "OmniVente"
    API_V1_PREFIX: str = "/api"
    DEBUG: bool = True

    # --- Base de donnees PostgreSQL locale ---
    DATABASE_URL: str = (
        "postgresql+asyncpg://omnivente_user:omnivente_secret_password"
        "@localhost:5432/omnivente_db"
    )

    # --- Securite ---
    SECRET_KEY: str = "change_moi"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- WhatsApp Business Cloud API ---
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "omnivente_verify_token"

    # --- Meta (Messenger / Instagram) ---
    META_PAGE_TOKEN: str = ""
    META_VERIFY_TOKEN: str = "omnivente_verify_token"

    # --- Email professionnel ---
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
