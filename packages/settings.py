from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Proje kökü: packages/settings.py → ../ → proje kökü
_PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Uygulama ayarları; ortam değişkenleri ve isteğe bağlı `.env` dosyasından yüklenir."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    # --- PostgreSQL ---
    username: str = Field(..., validation_alias="POSTGRES_USER", description="Veritabanı kullanıcı adı")
    password: str = Field(default="", validation_alias="POSTGRES_PASSWORD", description="Veritabanı şifresi")
    host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    database: str = Field(..., validation_alias="POSTGRES_DB", description="Veritabanı adı")

    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout: float = Field(default=30.0, ge=0)
    db_pool_pre_ping: bool = Field(default=True)
    db_pool_recycle: int = Field(default=1800, ge=0)

    # --- Slack ---
    slack_bot_token: str = Field(..., min_length=1)
    slack_user_token: str = Field(..., min_length=1)
    slack_app_token: str = Field(..., min_length=1)

    # Ortamda virgülle ayrılmış kanal ID'leri (JSON listesi değil); boş bırakılabilir.
    slack_workspace_owner_id: str = Field(..., validation_alias="SLACK_WORKSPACE_OWNER_ID")
    slack_admin_slack_id: str = Field(..., validation_alias="SLACK_ADMIN_SLACK_ID")
    slack_admin_channel: str = Field(..., validation_alias="SLACK_ADMIN_CHANNEL")
    slack_challenge_channel: str = Field(..., validation_alias="SLACK_CHALLENGE_CHANNEL")
    
    # --- Monitoring Intervals (Seconds) ---
    monitor_challenge_interval: int = Field(default=60, ge=10)
    monitor_deadline_interval: int = Field(default=300, ge=30)
    monitor_evaluation_interval: int = Field(default=600, ge=60)

    # --- Challenge & Evaluation Limits ---
    challenge_min_participants: int = Field(default=2, ge=2, description="Bir challenge için minimum katılımcı sayısı")
    challenge_max_participants: int = Field(default=5, ge=2, description="Bir challenge için maksimum katılımcı sayısı")
    evaluation_max_wait_hours: int = Field(default=24, ge=1)
    evaluation_jury_count: int = Field(default=2, ge=1, description="Bir challenge için atanacak jüri üyesi sayısı")

    # --- SMTP (opsiyonel; ikisi birlikte tanımlanmalı veya ikisi de boş bırakılmalı) ---
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_timeout: int = Field(default=30, ge=1)
    smtp_email: str = Field(default="")
    smtp_password: str = Field(default="")

    @model_validator(mode="after")
    def _validate_smtp(self) -> "Settings":
        has_email = bool(self.smtp_email)
        has_password = bool(self.smtp_password)
        if has_email != has_password:
            missing = "smtp_password" if has_email else "smtp_email"
            raise ValueError(
                f"SMTP yarı yapılandırılmış: '{missing}' eksik. "
                "Her ikisini de doldurun ya da ikisini de boş bırakın."
            )
        return self

    @property
    def smtp_enabled(self) -> bool:
        """SMTP kullanımına hazır olup olmadığını döner."""
        return bool(self.smtp_email and self.smtp_password)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

