# Migration Rehberi

[← README](../README.md)

Veritabanı şema değişikliklerini yönetmek için **Alembic** tabanlı migration sistemi.

---

## İçindekiler

- [Dosya Yapısı](#dosya-yapısı)
- [Komutlar](#komutlar)
- [Tipik İş Akışı](#tipik-iş-akışı)
- [İlk Kurulum](#ilk-kurulum)
- [Mevcut Veritabanı](#mevcut-veritabanı)
- [Bağlantı Konfigürasyonu](#bağlantı-konfigürasyonu)
- [Migration Zinciri](#migration-zinciri)
- [Sınırlar](#sınırlar)

---

## Dosya Yapısı

```
alembic.ini                  Alembic konfigürasyonu
migrate.py                   CLI aracı
migrations/
  env.py                     Async bağlantı + model yükleme
  script.py.mako             Yeni migration şablonu
  versions/
    0001_initial_schema.py   Tüm tabloların ilk oluşturulması
    0002_add_slack_id_to_members.py   slack_id kolonu + backfill
```

---

## Komutlar

```bash
# Tüm migration'ları uygula (en güncel versiyona çık)
python migrate.py upgrade

# Belirli bir versiyona çık
python migrate.py upgrade 0001

# Bir adım geri al
python migrate.py downgrade

# Belirli bir versiyona in
python migrate.py downgrade 0001

# Tüm versiyonları sıfırla (tabloları sil)
python migrate.py downgrade base

# Veritabanının şu anki versiyonunu göster
python migrate.py current

# Tüm migration geçmişini listele
python migrate.py history

# En güncel revision'ları göster
python migrate.py heads

# Veritabanına dokunmadan SQL üret (CI/inceleme için)
python migrate.py sql

# Migration çalıştırmadan versiyonu işaretle
python migrate.py stamp 0001
```

---

## Tipik İş Akışı

Model değiştikten sonra izlenecek adımlar:

```
1. Model dosyasını değiştir  (packages/database/models/*.py)
         ↓
2. Migration üret
   python migrate.py autogenerate "ne değişti"
         ↓
3. Oluşan dosyayı oku ve doğrula
   migrations/versions/<rev>_<slug>.py
         ↓
4. Uygula
   python migrate.py upgrade
```

> **Önemli:** `upgrade` tek başına model değişikliklerini algılamaz.
> Önce `autogenerate` ile migration dosyası oluşturulmalıdır.

---

## İlk Kurulum

Sıfırdan yeni bir veritabanı kuruyorsanız:

```bash
# Tüm tabloları oluşturur ve alembic_version'ı 0002'ye ayarlar
python migrate.py upgrade
```

Bu komut sırasıyla şunları yapar:

1. `alembic_version` tablosunu oluşturur
2. `0001` — 8 tabloyu ve enum tiplerini oluşturur
3. `0002` — `challenge_team_members` ve `challenge_jury_members` tablolarına `slack_id` kolonu ekler

---

## Mevcut Veritabanı

Migration sistemi kurulmadan önce oluşturulmuş bir veritabanınız varsa:

```bash
# 1. Veritabanı 0001 şemasına sahip, sadece işaretle
python migrate.py stamp 0001

# 2. slack_id migration'ını uygula (meta'dan backfill dahil)
python migrate.py upgrade
```

`0002` migration'ı mevcut `meta->>'slack_id'` verisini otomatik olarak yeni `slack_id` kolonuna kopyalar.

---

## Bağlantı Konfigürasyonu

`migrate.py` çalıştırılırken DB bağlantısı şu sırayla aranır:

### 1. `DATABASE_URL` ortam değişkeni (CI/CD)

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db python migrate.py upgrade
```

### 2. Ana `.env` dosyası (production)

`.env` dosyasında tüm Slack ve DB alanları dolu ise otomatik okunur:

```bash
python migrate.py upgrade   # .env'den okur
```

### 3. `POSTGRES_*` değişkenleri (`.env.template` formatı)

```bash
POSTGRES_USER=myuser \
POSTGRES_PASSWORD=mypass \
POSTGRES_HOST=localhost \
POSTGRES_PORT=5432 \
POSTGRES_DB=mydb \
python migrate.py upgrade
```

---

## Migration Zinciri

```
(base)
  └── 0001  initial schema
        └── 0002  add slack_id to challenge_team_members & challenge_jury_members
                    ↑ head (mevcut)
```

### Tablolar

| Tablo | Açıklama |
|-------|----------|
| `user_roles` | Kullanıcı rolleri ve izinleri |
| `users` | Admin/web kullanıcıları |
| `user_sessions` | JWT oturum takibi |
| `slack_users` | Slack çalışma alanı üyeleri |
| `challenge_types` | Challenge şablonları (kategori, süre, kontrol listesi) |
| `challenges` | Challenge kayıtları |
| `challenge_team_members` | Takım üyeleri |
| `challenge_jury_members` | Jüri üyeleri |

### Constraint İsimlendirme

Tüm constraint'ler tutarlı isim kuralını takip eder:

| Tip | Format | Örnek |
|-----|--------|-------|
| Primary Key | `pk_<tablo>` | `pk_challenges` |
| Foreign Key | `fk_<tablo>_<kolon>_<hedef_tablo>` | `fk_challenges_challenge_type_id_challenge_types` |
| Unique Index | `ix_<tablo_kolon>` | `ix_users_username` |
| Index | `ix_<tablo_kolon>` | `ix_challenges_status` |

---

## Sınırlar

Autogenerate'in **algılayamadığı** değişiklikler — bunlar için migration dosyası elle yazılmalıdır:

| Durum | Çözüm |
|-------|-------|
| PostgreSQL enum'a yeni değer ekleme | `op.execute("ALTER TYPE ... ADD VALUE '...'")`  |
| `server_default` değişiklikleri | Bazen kaçabilir, doğrula |
| Fonksiyon/trigger tabanlı constraint'ler | Her zaman elle yazılır |

Her autogenerate sonrası oluşan dosyayı okumak zorunludur.
