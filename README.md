# Slack Community Agent

## Paketler (`packages/`)

| Paket | Tanım |
|--------|--------|
| **settings** | Ortam değişkenleri ve uygulama yapılandırması (`Settings`, PostgreSQL, Slack, monitör aralıkları, challenge limitleri, SMTP). |
| **database** | Async SQLAlchemy ile PostgreSQL: modeller (challenge, kullanıcı, Slack ile ilgili tablolar), repository katmanı, oturum yönetimi. |
| **slack** | Slack Bolt uygulaması, Socket Mode bağlantısı, Web API sarmalayıcıları; blok/layout yardımcıları; konuşma, mesaj, dosya, kullanıcı vb. komut modülleri. |
| **logger** | Log yapılandırması, formatlayıcılar ve filtreler (servis logları için). |
| **smtp** | İsteğe bağlı e-posta gönderimi (şablonlar, şema). |

## Servisler (`services/`)

| Servis | Tanım |
|--------|--------|
| **challenge_service** | Slack üzerinden challenge yaşam döngüsünü yürüten süreç: slash komutları ve etkileşimler, arka planda kategori kuyrukları, kanal kayıt defteri, zamanlayıcı monitörler (challenge, son tarih, değerlendirme), başlangıç/kapanış bildirimleri. |

## Özellikler

- Slack Socket Mode ile gerçek zamanlı komut ve etkinlik işleme.
- Challenge oluşturma, katılımcı ve takım akışı, kategori bazlı sıra (kuyruk) yönetimi.
- Son tarih ve değerlendirme aşamaları için arka plan monitörleri.
- Jüri ve değerlendirme ile ilgili komut ve etkinlik akışları.
- PostgreSQL üzerinde challenge ve ilgili verilerin kalıcılığı; servis yeniden başlatıldığında kayıt defterinin veritabanından yeniden kurulması (resume modu).
- İsteğe bağlı SMTP ile e-posta tarafı (yapılandırma `Settings` ile).

## Kapsam

**Bu projede olanlar:** Slack topluluğu içinde challenge odaklı otomasyon, veritabanı ve Slack API entegrasyonu, tek ana servis olarak `challenge_service`.

**Bu projede olmayanlar:** Genel amaçlı HTTP/REST API sunucusu, Slack dışı web arayüzü, çoklu bağımsız mikroservis dağıtım modeli ve bu README kapsamı dışında kalan konular.

## Sürüm notları

Değişiklik geçmişi: [CHANGELOG.md](CHANGELOG.md).
