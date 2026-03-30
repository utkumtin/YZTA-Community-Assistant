# Changelog

Bu dosya [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) biçimine uyar ve [Semantic Versioning](https://semver.org/lang/tr/) ile uyumludur.

**Sürüm notu düzeni:** Her sürümde değişiklikler mümkün olduğunca **`packages/*`** (paylaşılan kütüphaneler) ve **`services/*`** (çalışan servisler) altında ayrılır; alt başlıklar ilgili modül veya dosya düzeyinde tutulur. `[Unreleased]` bölümünde yapılan işler birikir; sürüm etiketi kesildiğinde ilgili maddeler numaralı sürüm başlığının altına taşınır.

## [Unreleased]

Sonraki sürüme taşınacak değişiklikler. Eklerken mümkünse **`packages/...`** ve **`services/...`** alt başlıklarıyla hangi yapıyı etkilediğinizi belirtin.

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

---

## [2.0.0] - 2026-03-31

İlk kayıtlı sürüm: mevcut kod tabanının paket ve servis bazında özetlenmesi.

### Added

#### `packages/settings`

- Tek modül (`settings.py`): **Pydantic Settings** ile ortam değişkeni yükleme (proje kökünde `.env`).
- **PostgreSQL:** `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`; bağlantı havuzu: `db_pool_size`, `db_max_overflow`, `db_pool_timeout`, `db_pool_pre_ping`, `db_pool_recycle`.
- **Slack:** `slack_bot_token`, `slack_user_token`, `slack_app_token`; kanal ve yönetici kimlikleri: `SLACK_WORKSPACE_OWNER_ID`, `SLACK_ADMIN_SLACK_ID`, `SLACK_ADMIN_CHANNEL`, `SLACK_CHALLENGE_CHANNEL`.
- **Monitör aralıkları (saniye):** `monitor_challenge_interval`, `monitor_deadline_interval`, `monitor_evaluation_interval`.
- **Challenge / değerlendirme:** `challenge_min_participants`, `challenge_max_participants`, `evaluation_max_wait_hours`, `evaluation_jury_count`.
- **SMTP (isteğe bağlı):** `smtp_host`, `smtp_port`, `smtp_timeout`, `smtp_email`, `smtp_password`; e-posta/şifre çift doğrulaması ve `smtp_enabled` özelliği.

#### `packages/database`

- **`manager.py`:** `DatabaseManager` — async SQLAlchemy engine ve `async_sessionmaker`; `initilaze` / `shutdown`; `session()` bağlam yöneticisi (`read_only` ile salt okunur oturum).
- **`models/base.py`:** SQLAlchemy bildirim tabanı (`Base`).
- **`models/mixins.py`:** Ortak mixin’ler (ör. kimlik ve zaman damgası).
- **`models/challenge.py`:** `ChallengeCategory`, `ChallengeStatus`, `ChallengeType`, `Challenge`, `ChallengeTeamMember`, `ChallengeJuryMember`.
- **`models/user.py`:** `User`, `UserRole`, `UserSession`.
- **`models/slack.py`:** `SlackUser`.
- **`repository/base.py`:** Repository temel kalıbı.
- **`repository/challenge.py`**, **`repository/user.py`**, **`repository/slack.py`:** İlgili varlıklar için veri erişim katmanı.

#### `packages/slack`

- **`client.py`:** Slack Bolt `App`, `WebClient` (bot ve user token), **Socket Mode** (`SocketModeHandler`) — tek giriş noktası `slack_client`.
- **`blocks/builder.py`**, **`blocks/layouts.py`:** Slack Block Kit bileşenleri ve düzen yardımcıları.
- **`commands/`:** Web API sarmalayıcıları — `chat`, `conversations`, `files`, `pins`, `reactions`, `search`, `usergroups`, `users`, `views`, `canvases`; `__init__.py` ile dışa aktarım.

#### `packages/logger`

- **`manager.py`:** Log kurulumu ve logger fabrikası (`get_logger`, `start_logging`).
- **`formatters.py`:** `SystemMessageFormatter`, `ErrorMessageFormatter`, `ApiMessageFormatter`, `QueueMessageFormatter`.
- **`filters.py`:** `SystemFilter`, `ErrorFilter`, `ApiFilter`, `QueueFilter` — kayıtları kanala göre ayırma.

#### `packages/smtp`

- **`client.py`:** E-posta gönderim istemcisi.
- **`template.py`**, **`schema.py`:** Şablon ve veri şeması.
- **`templates/welcome.html`:** Hoş geldin e-posta şablonu (HTML).

#### `services/challenge_service`

- **`__main__.py`:** Servis giriş noktası — arka plan `asyncio` döngüsü (`set_loop`), veritabanı başlatma, `service_manager.start()`, Slack Socket Mode’un bloklayıcı çalıştırılması, `SIGINT` / `SIGTERM` ile zarif kapanış; `--fresh` ile `StartupMode.FRESH`, aksi halde `RESUME`.
- **`manager.py`:** `ChallengeServiceManager` (tekil); `StartupMode` (`FRESH` / `RESUME`); başlangıçta DB temizliği, bellek sıfırlama, `ChannelRegistry` doldurma, monitörlerin başlatılması / durdurulması; iptal edilen challenge’lar için bildirim ve Slack kanal arşivleme akışı.
- **`logger.py`:** Servise özel `dictConfig` — dönen dosya handler’ları (`system`, `errors`, `api`, `queue`), stdout; log dizini `logs/challenge_service/`.
- **`core/event_loop.py`:** Bolt işleyicilerinden async iş çalıştırma (`run_async` vb.).
- **`core/queue/channel_registry.py`:** Kanal kayıt defteri ve başlangıçta DB’den yükleme (`_on_startup`).
- **`core/queue/challenge_queue.py`:** Kategori / jüri için `CustomQueue` ve kuyruk öğeleri.
- **`core/monitor/challenge_monitor.py`:** Challenge durumu için periyodik monitör.
- **`core/monitor/deadline_monitor.py`:** Son tarih monitörü.
- **`core/monitor/evaluation_monitor.py`:** Değerlendirme aşaması monitörü.
- **`handlers/commands/challenge.py`:** Challenge slash komutları ve ilgili iş akışı.
- **`handlers/commands/evaluation.py`:** Değerlendirme komutları.
- **`handlers/commands/internal.py`:** Dahili / yönetim komutları.
- **`handlers/commands/jury.py`:** `/jury` komutu (`join`, `leave`, `list` vb.).
- **`handlers/events/challenge.py`:** Challenge etkinlikleri (mesaj, etkileşim).
- **`handlers/events/evaluation.py`:** Değerlendirme etkinlikleri.
- **`handlers/events/internal.py`:** Dahili etkinlikler.
- **`handlers/__init__.py`:** Tüm handler modüllerinin içe aktarılması (dekoratör kayıtlarının yüklenmesi).
- **`utils/notifications.py`:** Başlangıç, kapanış ve iptal bildirimleri.
- **`utils/slack_helpers.py`:** Slack tarafı yardımcı işlemler (ör. kanal arşivleme).
- **`utils/slack_user_sync.py`:** Slack kullanıcı verisinin senkronu.
- **`utils/datetime_helpers.py`:** Tarih/saat yardımcıları.
- **`config/criteria.json`:** Değerlendirme ölçütleri yapılandırması.
- **`start.sh`**, **`stop.sh`:** Kabuk ile servisi başlatma / durdurma yardımcıları.

#### Dokümantasyon ve kök yapılandırma

- **`README.md`:** Paketler, servisler, özellikler, kapsam ve sürüm notları bağlantısı.
- **`CHANGELOG.md`:** Bu dosya — değişiklik geçmişi.
- **`.env.template`:** `Settings` ile uyumlu ortam değişkeni şablonu.
- **`requiremets.txt`:** Python bağımlılık listesi (proje kökü).
