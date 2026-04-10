from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, ConfigDict


class SystemSettings(BaseSettings):
    # Slack Ayarları
    slack_bot_token: str = Field(..., description="Slack Bot Token (xoxb-...)")
    slack_app_token: str = Field(..., description="Slack App Token (xapp-...)")
    slack_user_token: str = Field(..., description="Slack User Token (xoxp-...) - Kanal oluşturma için")

    # Groq API
    groq_api_key: Optional[str] = Field(None, description="Groq Cloud API anahtarı")

    # Gemini API
    gemini_api_key: Optional[str] = Field(None, description="Gemini API anahtarı")

    # SMTP (STARTTLS; tipik olarak 587 — env → get_settings() → packages.smtp.SmtpClient)
    smtp_email: Optional[str] = Field(None, description="SMTP gönderen adresi")
    smtp_password: Optional[str] = Field(None, description="SMTP şifresi (Gmail için App Password önerilir)")
    smtp_host: str = Field("smtp.gmail.com", description="SMTP sunucu host")
    smtp_port: int = Field(587, ge=1, description="SMTP port (STARTTLS için genelde 587)")
    smtp_timeout: int = Field(10, ge=1, description="SMTP bağlantı zaman aşımı (saniye)")
    admin_email: Optional[str] = Field(None, description="Admin e-posta adresi (virgülle ayrılmış birden fazla)")

    # Slack Bilgileri
    slack_admins: list[str] = Field(..., description="Slack Admin ID listesi")
    slack_startup_channel: Optional[str] = Field(None, description="Slack Startup Channel ID")
    slack_report_channel: Optional[str] = Field(None, description="Slack Report Channel ID")
    slack_command_channels: list[str] = Field(..., description="Slack Command Channel ID listesi")
    slack_admin_channel: str = Field(..., description="Admin bildirim kanal ID'si (C...)")

    # Event Service Ayarlari
    event_channel: str = Field(..., description="Serbest Kursu kanal ID'si (C...)")
    event_reminder_enabled: bool = Field(True, description="Hatirlatma sistemi acik/kapali")
    event_approval_timeout_hours: int = Field(72, ge=1, description="Admin onay suresi (saat)")

    # Database Ayarları
    username: str = Field(..., description="Veritabanı kullanıcı adı")
    password: str = Field(..., description="Veritabanı şifresi")
    host: str = Field(..., description="Veritabanı host")
    port: int = Field(..., description="Veritabanı port")
    database: str = Field(..., description="Veritabanı adı")
    db_pool_size: int = Field(5, ge=1, description="SQLAlchemy pool boyutu")
    db_max_overflow: int = Field(10, ge=0, description="Pool overflow bağlantı sayısı")
    db_pool_timeout: int = Field(30, ge=1, description="Pool'dan bağlantı bekleme süresi (saniye)")
    db_pool_pre_ping: bool = Field(True, description="Bağlantı kullanılmadan önce canlılık kontrolü")
    db_pool_recycle: int = Field(3600, ge=60, description="Bağlantıların yenileneceği süre (saniye)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator('slack_admins', 'slack_command_channels', mode='before')
    @classmethod
    def parse_comma_separated_list(cls, v: str) -> list[str]:
        """Virgülle ayrılmış string'i listeye çevirir."""
        if isinstance(v, list):
            return v
        if not v:
            return []
        return [item.strip() for item in v.split(',') if item.strip()]

# Global Settings Instance
_settings = SystemSettings()
def get_settings(reload: bool = False) -> SystemSettings:
    global _settings
    if _settings is None or reload:
        _settings = SystemSettings()
    return _settings
