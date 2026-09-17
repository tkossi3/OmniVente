"""Configuration centralisée, lue depuis les variables d'environnement (.env)."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://omnivente:change_me_2026@localhost:5432/omnivente_db"

    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    app_env: str = "development"
    default_tenant: str = "kino-steak"
    cors_origins: str = "http://localhost:5173"
    # Motif d'origines supplémentaire pour un environnement local particulier.
    cors_origin_regex: str | None = None

    # Crée les tables et importe le catalogue au démarrage.
    auto_seed: bool = False
    auto_seed_demo: bool = False

    # Sondage e-mail (voir app/services/mail_poller.py)
    mail_poll_enabled: bool = True
    mail_poll_seconds: int = 30

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        """Accepte les formats PostgreSQL courants utilisés en local."""
        if value.startswith("postgres://"):
            return "postgresql+psycopg2://" + value[len("postgres://"):]
        if value.startswith("postgresql://") and "+psycopg2" not in value:
            return "postgresql+psycopg2://" + value[len("postgresql://"):]
        return value

    whatsapp_phone_number_id: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_verify_token: str = "omnivente_kino_2026"

    meta_app_id: str | None = None
    meta_app_secret: str | None = None
    meta_page_access_token: str | None = None
    meta_verify_token: str = "omnivente_kino_2026"

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    sales_email: str | None = None
    sales_email_app_password: str | None = None

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
