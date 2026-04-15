# Event Service — Tasarim Dokumani

> Slack toplulugunda etkinlik olusturma, admin onayi, duyuru, hatirlatma ve takip sureci.

---

## 1. Ozet

`#serbest-kursu` kanalinda `/event` komutu ile kullanicilar etkinlik talebi olusturur. Admin onayi sonrasi duyuru yapilir, katilim takibi saglanir ve zamanlanmis bildirimler gonderilir.

**Temel Akis:**
```
Kullanici /event create → Form doldurur → Admin'e bildirim (Slack + e-posta)
→ Admin onaylar/reddeder → Onaylanirsa duyuru → Hatirlatmalar → Etkinlik gerceklesir
```

**Bagimlilik:** `packages/` altindaki ortak altyapiyi kullanir (database, slack, smtp, logger, settings). `challenge_service` ile sifir bagimlilik — birbirini import etmez.

---

## 2. Komutlar

Tum komutlar `#serbest-kursu` kanalinda calisir.

| Komut | Gorunurluk | Aciklama |
|-------|-----------|----------|
| `/event create` | Modal acilir | Yeni etkinlik talebi olustur |
| `/event list` | Ephemeral | Bu ayki etkinlikleri listele (ID, ad, sahip, link, tarih/saat) |
| `/event my_list` | Ephemeral | Kullanicinin kendi olusturdugu etkinlikleri listele |
| `/event history` | Ephemeral | Gecmis etkinlikleri listele |
| `/event add_me` | Modal acilir | Etkinlige ilgi goster — form ile secim (kullanici basina 1 kez) |
| `/event update` | Modal acilir (2 adim) | Etkinlik bilgilerini guncelle (sahip: kendi eventleri, admin: tum eventler) |
| `/event cancel` | Modal + duyuru | Etkinligi iptal et (sahip: kendi eventleri, admin: tum eventler) |
| `/event help` | Ephemeral | Komut listesini goster |

### 2.1 Komut Ciktilari

**`/event list` (ephemeral):**

Format: emoji yok, event ID yok. Her etkinlik 4 satirda gosterilir:
- 1. satir: `*Etkinlik Adi*` (bold)
- 2. satir: `Tarih · Saat · Lokasyon` — Slack kanali ise `<#C123>` mention, harici platform ise duz metin. Link varsa platform adindan sonra parantez icinde `(<link|Link>)` eklenir.
- 3. satir: `Etkinlik Aciklamasi`
- 4. satir: `<@creator>  · N ilgili · ✓ ilgi gosterdin` — son kisim sadece kullanici bu etkinlige ilgi gosterdiyse eklenir.

```
┌─ Event Bot (sadece sana gorunur) ──────────────────┐
│                                                     │
│  Bu Ayin Etkinlikleri                                │
│  ─────────────────────────────────────────────      │
│                                                     │
│  • *Python Workshop*                                 │
│    15 Nisan 2026 · 20:00 · Zoom (<zoom.us/j/123|Link>)│
│    Python ile web scraping tekniklerini ogrenecegiz.│
│    <@U123>  · 5 ilgili · ✓ ilgi gosterdin           │
│                                                     │
│  • *AI Sohbeti*                                      │
│    22 Nisan 2026 · 21:00 · <#C456>                  │
│    Yapay zeka trendleri uzerine serbest sohbet.      │
│    <@U789>  · 3 ilgili                              │
│                                                     │
│  • *DevOps Sunumu*                                   │
│    28 Nisan 2026 · 18:30 · Google Meet (<meet.g.co/xyz|Link>)│
│    CI/CD ve IaC kavramlarina giris sunumu.          │
│    <@UABC>  · 8 ilgili · ✓ ilgi gosterdin           │
│                                                     │
│  ─────────────────────────────────────────────      │
│  Toplam: 3 etkinlik                                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Teknik notlar:**

- `<@U123>` ve `<#C456>` Slack mrkdwn mention'lari — tiklanabilir olarak render olur.
- Kullanicinin ilgi gosterdigi etkinlikler `EventInterestRepository` ile tek sorguda toplu olarak cekilir (N+1 onleme icin `list_event_ids_by_user(slack_id)` pattern'i kullanilabilir).
- Link gosterimi `<url|Link>` formatinda olup kucuk yer kaplar.

**`/event my_list` (ephemeral):**

```
┌─ Event Bot (sadece sana gorunur) ──────────────────┐
│                                                     │
│  📋 Etkinliklerim                                    │
│                                                     │
│  ─────────────────────────────────────────────      │
│                                                     │
│  • #EVT-a1b2 | *Python Workshop*                    │
│    📅 15 Nisan 20:00 · 📍 Zoom · ⏳ Onaylandi       │
│    🙋 5 ilgili                                       │
│                                                     │
│  • #EVT-g7h8 | *Docker 101*                         │
│    📅 3 Mayis 19:00 · 📍 YouTube · 🟡 Onay Bekliyor │
│                                                     │
│  ─────────────────────────────────────────────      │
│  _Toplam: 2 etkinlik_                               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**`/event history` (ephemeral):**

```
┌─ Event Bot (sadece sana gorunur) ──────────────────┐
│                                                     │
│  📋 Gecmis Etkinlikler                               │
│                                                     │
│  ─────────────────────────────────────────────      │
│                                                     │
│  • #EVT-x1y2 | *React Hooks Sunumu*                 │
│    👤 @ayse · 📅 10 Mart 20:00 · 📍 Zoom            │
│    ✅ Gerceklesti · 🙋 12 ilgili                     │
│                                                     │
│  • #EVT-z3w4 | *Git Workshop*                        │
│    👤 @can · 📅 3 Mart 18:00 · 📍 #genel            │
│    ❌ Iptal Edildi                                    │
│                                                     │
│  • #EVT-m5n6 | *API Design Sohbeti*                 │
│    👤 @ahmet · 📅 20 Subat 21:00 · 📍 Google Meet   │
│    ✅ Gerceklesti · 🙋 7 ilgili                      │
│                                                     │
│  ─────────────────────────────────────────────      │
│  _Toplam: 3 etkinlik_                               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**`/event help` (ephemeral):**

```
┌─ Event Bot (sadece sana gorunur) ──────────────────┐
│                                                     │
│  📖 Event Komutlari                                  │
│                                                     │
│  *`/event create`*                                   │
│  Yeni etkinlik talebi olustur. Form acilir,          │
│  admin onayindan sonra duyuru yapilir.               │
│                                                     │
│  *`/event list`*                                     │
│  Bu ayin yaklasan etkinliklerini listele.            │
│                                                     │
│  *`/event my_list`*                                  │
│  Kendi olusturdugum etkinlikleri listele.            │
│                                                     │
│  *`/event history`*                                  │
│  Gecmis etkinlikleri goruntule.                      │
│                                                     │
│  *`/event add_me`*                                   │
│  Ilgi formu acar. Onumuzdeki 1 ay icindeki henuz    │
│  ilgi gostermediginiz etkinlikler listelenir.        │
│  Her etkinlige 1 kez ilgi gosterilebilir.            │
│                                                     │
│  *`/event update`*                                   │
│  Guncelleme formu acar. Sahip kendi eventlerini,      │
│  admin tum aktif eventleri gorup guncelleyebilir.    │
│                                                     │
│  *`/event cancel`*                                   │
│  Iptal formu acar. Sahip kendi eventlerini,           │
│  admin tum aktif eventleri gorup iptal edebilir.     │
│                                                     │
│  *`/event help`*                                     │
│  Bu yardim mesajini goster.                          │
│                                                     │
│  ─────────────────────────────────────────────      │
│  _Etkinlik ID'sini `/event list` ile ogrenebilirsin_ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**`/event add_me` — secim formu (modal):**

Dropdown icerigi:
- **Tarih filtresi:** Bugunden itibaren 1 ay (30 gun) icinde gerceklesecek etkinlikler
- **Status:** Sadece `APPROVED` etkinlikler
- **Exclusion:** Kullanicinin daha once ilgi gostermedigi etkinlikler (zaten ilgi gosterilenler listelenmez)
- **Siralama:** Tarih ve saate gore artan
- **Label format:** `gg Ay — Etkinlik Adi (Duzenleyen Adi)`

```
┌─────────────────────────────────────────────────┐
│          Etkinlige Ilgi Goster              [X]  │
├─────────────────────────────────────────────────┤
│                                                  │
│  Ilgi Gosterilecek Etkinlik *                    │
│  ┌─────────────────────────────────────────────┐ │
│  │ Etkinlik secin...                       [v] │ │
│  │                                             │ │
│  │  · 16 Nis — RAG Sohbetleri (Ahmet Yilmaz)  │ │
│  │  · 18 Nis — Python Workshop (Ayse Demir)    │ │
│  │  · 22 Nis — DevOps Sunumu (Can Kaya)        │ │
│  │  · 28 Nis — AI Paneli (Zeynep Kara)         │ │
│  │  · 05 May — Web3 Sohbeti (Mehmet Aydin)     │ │
│  │                                             │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  _Onumuzdeki 1 ay icinde gerceklesecek ve       │
│   henuz ilgi gostermediginiz etkinlikler._       │
│                                                  │
│                     [Iptal]  [Ilgi Goster]       │
└─────────────────────────────────────────────────┘
```

**`/event add_me` — secenek yok (ephemeral):**

Onumuzdeki 1 ay icinde ilgi gosterilebilecek etkinlik yoksa modal acilmaz:

```
┌─ Event Bot (sadece sana gorunur) ──────────────────┐
│                                                     │
│  📭 Onumuzdeki 1 ay icinde ilgi gosterebileceginiz │
│  etkinlik yok.                                      │
│                                                     │
│  Tum etkinlikleri gormek icin `/event list`         │
│  komutunu kullanin.                                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**`/event add_me` — basarili (ephemeral):**

Form gonderildikten sonra, komutun yazildigi kanalda gelen onay mesaji. Modal view submission'larinda `body.channel_id` bulunmadigi icin, kanal bilgisi modal acilirken `private_metadata` uzerinden tasinir ve submission handler'inda kullanilir. Mesaj minimal tutulur: emoji yok, event ID yok, buton yok.

```
┌─ Event Bot (sadece sana gorunur) ──────────────────┐
│                                                     │
│  Ilgin kaydedildi!                                   │
│  *Python ile Web Scraping Workshop*                  │
│  18 Nisan 2026 · 20:00 · Zoom                       │
│  Python ile web scraping tekniklerini ogrenecegiz.  │
│                                                     │
│  Etkinlik gunu hatirlatma e-postasi alacaksin.       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**`/event add_me` — basarili (DM):**

Ayrica kullaniciya kisisel DM olarak da ilgili etkinligin tum detaylari ve **Google Takvime Ekle** butonu gonderilir.

```
┌─ Event Bot → @ahmet (DM) ─────────────────────────┐
│                                                     │
│  🙋 Ilgin kaydedildi!                                │
│                                                     │
│  *Python ile Web Scraping Workshop*                  │
│  📅 18 Nisan 2026 · 🕐 20:00 · 📍 Zoom              │
│  🔗 https://zoom.us/j/123456                        │
│                                                     │
│  Etkinlik gunu hatirlatma e-postasi alacaksin.       │
│                                                     │
│  [📅 Google Takvime Ekle]                            │
│                                                     │
│  _#EVT-a1b2_                                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Race condition (nadir): Secim sirasinda baskasi veya kendi butonla ilgi gosterirse (ephemeral):**

```
┌─ Event Bot (sadece sana gorunur) ──────────────────┐
│                                                     │
│  ℹ️ Bu etkinlige zaten ilgi gostermissiniz.          │
│                                                     │
│  *Python ile Web Scraping Workshop*                  │
│  _#EVT-a1b2_                                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 3. Event Formu (`/event create`)

Modal acilir, asagidaki alanlar bulunur:

| # | Alan | Tip | Zorunlu | Aciklama |
|---|------|-----|---------|----------|
| 1 | Etkinlik Adi | Text input | Evet | Kisa baslik |
| 2 | Konu | Text input | Evet | Etkinligin konusu |
| 3 | Aciklama & Amac | Textarea | Evet | Detayli aciklama ve amac |
| 4 | Tarih | Date picker | Evet | Etkinlik tarihi |
| 5 | Saat | Time picker | Evet | Baslangic saati |
| 6 | Sure | Static select | Evet | Tahmini sure |
| 7 | Etkinlik Lokasyonu | Static select | Evet | Nerede gerceklesecek |
| 8 | Slack Kanali | Channel select | Kosullu | Lokasyon "Slack Kanali" secildiyse zorunlu |
| 9 | Etkinlik Linki | URL input | Kosullu | Lokasyon harici platform secildiyse zorunlu (Zoom, Meet, Drive vb.) |
| 10 | YZTA'dan Beklenen | Textarea | Hayir | Organizasyondan destek/kaynak talebi |

Toplam 10 alan — Slack modal limiti dahilinde.

### 3.1 Etkinlik Lokasyonu Secenekleri

| Secenek | Aciklama |
|---------|----------|
| Slack Kanali | Etkinlik bir Slack kanalinda gerceklesir → Slack Kanali alani zorunlu olur |
| Zoom | Harici platform → Etkinlik Linki alani zorunlu olur |
| YouTube | Harici platform → Etkinlik Linki alani zorunlu olur |
| Google Meet | Harici platform → Etkinlik Linki alani zorunlu olur |
| Discord | Harici platform → Etkinlik Linki alani zorunlu olur |
| Diger | Harici platform → Etkinlik Linki alani zorunlu olur |

**Validasyon (backend):** Slack Kanali secildiyse `channel_id` zorunlu, diger seceneklerde `link` zorunlu. Her iki alan da formda her zaman gorunur (Slack modal kosullu gorunum desteklemez).

### 3.2 Form Gorunumu (Modal Detay)

```
┌─────────────────────────────────────────────────┐
│            Yeni Etkinlik Olustur            [X]  │
├─────────────────────────────────────────────────┤
│                                                  │
│  Etkinlik Adi *                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │ Orn: Python ile Web Scraping Workshop       │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  Konu *                                          │
│  ┌─────────────────────────────────────────────┐ │
│  │ Orn: Web Scraping, Veri Analizi             │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  Aciklama & Amac *                               │
│  ┌─────────────────────────────────────────────┐ │
│  │ Etkinligin amacini ve katilimcilara neler   │ │
│  │ katacagini aciklayin...                     │ │
│  │                                             │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  Tarih *                    Saat *               │
│  ┌──────────────────┐      ┌──────────────────┐  │
│  │ Tarih secin...   │      │ Saat secin...    │  │
│  └──────────────────┘      └──────────────────┘  │
│                                                  │
│  Tahmini Sure *                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │ Sure secin...                           [v] │ │
│  │  · 30 dakika                                │ │
│  │  · 1 saat                                   │ │
│  │  · 1.5 saat                                 │ │
│  │  · 2 saat                                   │ │
│  │  · 3 saat                                   │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  Etkinlik Lokasyonu *                            │
│  ┌─────────────────────────────────────────────┐ │
│  │ Lokasyon secin...                       [v] │ │
│  │  · Slack Kanali                             │ │
│  │  · Zoom                                     │ │
│  │  · YouTube                                  │ │
│  │  · Google Meet                              │ │
│  │  · Discord                                  │ │
│  │  · Diger                                    │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  Slack Kanali (lokasyon Slack ise zorunlu)        │
│  ┌─────────────────────────────────────────────┐ │
│  │ Kanal secin...                          [v] │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  Etkinlik Linki (harici platform ise zorunlu)    │
│  ┌─────────────────────────────────────────────┐ │
│  │ Orn: https://zoom.us/j/123 veya Drive linki│ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  YZTA'dan Beklenen (opsiyonel)                   │
│  ┌─────────────────────────────────────────────┐ │
│  │ Organizasyondan bir destek veya kaynak      │ │
│  │ talebiniz varsa belirtin...                 │ │
│  │                                             │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│                    [Iptal]  [Gonder]              │
└─────────────────────────────────────────────────┘
```

### 3.3 Duyuru Kanallari

Duyuru kanallari otomatik belirlenir:
- `#serbest-kursu` (event_channel) — her zaman
- Kullanicinin sectigi Slack kanali (`channel_id`) — lokasyon "Slack Kanali" secildiyse ve `#serbest-kursu`'den farkliysa eklenir

Ayni kanal secildiyse veya lokasyon harici platformsa (Zoom, Meet vb.) sadece `#serbest-kursu` duyuru kanali olur.

---

## 4. Admin Onay Akisi

### 4.1 Form Gonderildiginde

1. Admin kanalina (`slack_admin_channel`) Slack mesaji gonderilir:
   - Form detaylari (tum alanlar)
   - **Onayla** ve **Reddet** butonlari
2. Admin e-postasina bildirim gonderilir (form detaylari)
3. Kullaniciya ephemeral mesaj + DM: "Talebiniz iletildi, onay bekleniyor"
4. DB'de event kaydi olusturulur, status: `PENDING`

**Admin kanalina giden mesaj:**

```
┌─────────────────────────────────────────────────────┐
│ #admin-kanal                                         │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─ Event Bot ──────────────────────────────────┐    │
│  │                                               │    │
│  │  📩 Yeni Etkinlik Talebi                      │    │
│  │                                               │    │
│  │  *Python ile Web Scraping Workshop*           │    │
│  │                                               │    │
│  │  📌 *Konu:* Web Scraping                      │    │
│  │  📝 *Aciklama:* Python ile web scraping        │    │
│  │  tekniklerini ogrenecegiz. BeautifulSoup ve   │    │
│  │  Selenium kutuphanelerini kullanacagiz.        │    │
│  │                                               │    │
│  │  📅 *Tarih:* 15 Nisan 2026                    │    │
│  │  🕐 *Saat:* 20:00                             │    │
│  │  ⏱ *Sure:* 1.5 saat                          │    │
│  │  📍 *Lokasyon:* Zoom                          │    │
│  │  🔗 *Link:* https://zoom.us/j/123456         │    │
│  │  👤 *Talep Eden:* @ahmet                      │    │
│  │  📎 *YZTA'dan Beklenen:* Projektor gerekli    │    │
│  │                                               │    │
│  │  ─────────────────────────────────────────    │    │
│  │                                               │    │
│  │  [✅ Onayla]  [❌ Reddet]                      │    │
│  │                                               │    │
│  │  _#EVT-a1b2 · Gonderim: 8 Nisan 2026 14:30_  │    │
│  │                                               │    │
│  └───────────────────────────────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Kullaniciya ephemeral mesaj:**

```
┌─ Event Bot (sadece sana gorunur) ──────────────────┐
│                                                     │
│  ✅ Etkinlik talebiniz basariyla iletildi!           │
│                                                     │
│  *Python ile Web Scraping Workshop*                  │
│  📅 15 Nisan 2026 · 🕐 20:00 · 📍 Zoom              │
│                                                     │
│  Admin onayini bekliyor. Sonuc Slack DM ve           │
│  e-posta ile bildirilecek.                           │
│                                                     │
│  _Talep ID: #EVT-a1b2_                              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Kullaniciya DM (ayni icerik):**

```
┌─ Event Bot → @ahmet (DM) ─────────────────────────┐
│                                                     │
│  ✅ Etkinlik talebiniz basariyla iletildi!           │
│                                                     │
│  *Python ile Web Scraping Workshop*                  │
│  📅 15 Nisan 2026 · 🕐 20:00 · 📍 Zoom              │
│                                                     │
│  Admin onayini bekliyor. Sonuc bu DM uzerinden       │
│  ve e-posta ile bildirilecek.                        │
│                                                     │
│  _Talep ID: #EVT-a1b2_                              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 4.2 Admin Aksiyonu

Admin butona tikladiginda kisa bir modal acilir — opsiyonel not alani ile.

**Admin onay/red modali:**

```
┌─────────────────────────────────────────────────┐
│          Etkinlik Onay / Red                [X]  │
├─────────────────────────────────────────────────┤
│                                                  │
│  *Python ile Web Scraping Workshop*              │
│  👤 @ahmet · 📅 15 Nisan 2026 · 🕐 20:00        │
│                                                  │
│  Not (opsiyonel)                                 │
│  ┌─────────────────────────────────────────────┐ │
│  │ Varsa eklemek istediginiz notu yazin...     │ │
│  │                                             │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│                    [Iptal]  [Gonder]              │
└─────────────────────────────────────────────────┘
```

**Onaylandi:**
- DB status → `APPROVED`, `approved_by` kaydedilir
- Kullaniciya Slack DM + e-posta: "Etkinliginiz onaylandi!" (admin notu varsa eklenir)
- Duyuru akisi baslar (Bolum 5)

**Kullaniciya onay DM'i:**

```
┌─ Event Bot → @ahmet (DM) ─────────────────────────┐
│                                                     │
│  🎉 Etkinliginiz Onaylandi!                         │
│                                                     │
│  *Python ile Web Scraping Workshop*                  │
│                                                     │
│  📅 *Tarih:* 15 Nisan 2026                          │
│  🕐 *Saat:* 20:00                                   │
│  ⏱ *Sure:* 1.5 saat                                │
│  📍 *Lokasyon:* Zoom                                │
│  🔗 *Link:* https://zoom.us/j/123456               │
│                                                     │
│  📝 *Admin Notu:* Harika bir konu, basarilar!       │
│                                                     │
│  Duyuru #serbest-kursu kanalina gonderildi.          │
│  _#EVT-a1b2_                                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Reddedildi:**
- DB status → `REJECTED`
- Kullaniciya Slack DM + e-posta: "Etkinliginiz reddedildi" (admin notu varsa eklenir)

**Kullaniciya red DM'i:**

```
┌─ Event Bot → @ahmet (DM) ─────────────────────────┐
│                                                     │
│  ❌ Etkinliginiz Reddedildi                          │
│                                                     │
│  *Python ile Web Scraping Workshop*                  │
│  📅 15 Nisan 2026 · 🕐 20:00                        │
│                                                     │
│  📝 *Admin Notu:* Bu hafta cok yogun, haftaya        │
│  tekrar deneyin.                                     │
│                                                     │
│  Yeni bir etkinlik talebi icin `/event create`       │
│  komutunu kullanabilirsiniz.                         │
│  _#EVT-a1b2_                                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 4.3 Otomatik Timeout (3 Gun)

- Background scheduler her saat kontrol eder
- `created_at + 72 saat` gecmis ve hala `PENDING` olan etkinlikler otomatik `REJECTED` yapilir
- Kullaniciya Slack DM + e-posta gonderilir

**Kullaniciya timeout DM'i:**

```
┌─ Event Bot → @ahmet (DM) ─────────────────────────┐
│                                                     │
│  ⏰ Etkinlik Talebiniz Zaman Asimina Ugradi         │
│                                                     │
│  *Python ile Web Scraping Workshop*                  │
│  📅 15 Nisan 2026 · 🕐 20:00                        │
│                                                     │
│  Talebiniz 3 gun icinde yanit alamadigi icin         │
│  otomatik olarak reddedildi.                         │
│                                                     │
│  Yeni bir etkinlik talebi icin `/event create`       │
│  komutunu kullanabilirsiniz.                         │
│  _#EVT-a1b2_                                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 5. Duyuru & Bildirim Akisi

### 5.1 Duyuru Kanallari

Bolum 3.3'te tanimlandigi gibi otomatik belirlenir:
- `#serbest-kursu` (event_channel) — her zaman
- Kullanicinin sectigi Slack kanali (`channel_id`) — farkli kanal secildiyse eklenir
- Lokasyon harici platformsa (Zoom, Meet vb.) sadece `#serbest-kursu`

### 5.2 Ilk Duyuru (Onay Aninda)

- Hedef: Duyuru kanallari (3.3)
- Icerik: Etkinlik detaylari (ad, konu, aciklama, tarih, saat, sure, link)
- Butonlar: **Katilacagim** + **Google Takvime Ekle**

```
┌─────────────────────────────────────────────────────┐
│ #serbest-kursu                                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─ Event Bot ──────────────────────────────────┐    │
│  │                                               │    │
│  │  📢 Yeni Etkinlik Duyurusu                    │    │
│  │                                               │    │
│  │  *Python ile Web Scraping Workshop*           │    │
│  │                                               │    │
│  │  📌 *Konu:* Web Scraping                      │    │
│  │  📝 *Aciklama:* Python ile web scraping        │    │
│  │  tekniklerini ogrenecegiz. BeautifulSoup ve   │    │
│  │  Selenium kutuphanelerini kullanacagiz.        │    │
│  │                                               │    │
│  │  📅 *Tarih:* 15 Nisan 2026                    │    │
│  │  🕐 *Saat:* 20:00                             │    │
│  │  ⏱ *Sure:* 1.5 saat                          │    │
│  │  📍 *Lokasyon:* Zoom                          │    │
│  │  🔗 *Link:* https://zoom.us/j/123456         │    │
│  │  👤 *Duzenleyen:* @ahmet                      │    │
│  │                                               │    │
│  │  ─────────────────────────────────────────    │    │
│  │                                               │    │
│  │  [🙋 Katilacagim]  [📅 Google Takvime Ekle]   │    │
│  │                                               │    │
│  │  _3 kisi ilgi gosterdi_                       │    │
│  │                                               │    │
│  └───────────────────────────────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 5.3 Gun Basi Hatirlatma (Etkinlik Gunu Sabahi)

- Hedef: Duyuru kanallari (3.3)
- Icerik: O gun gerceklesecek tum etkinliklerin listesi (saat, aciklama, link)
- Her etkinlik icin: **Link** butonu + **Google Takvime Ekle** butonu
- "Katilacagim" diyenlere e-posta hatirlatma

```
┌─────────────────────────────────────────────────────┐
│ #serbest-kursu                                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─ Event Bot ──────────────────────────────────┐    │
│  │                                               │    │
│  │  📅 Bugunun Etkinlikleri — 15 Nisan 2026      │    │
│  │                                               │    │
│  │  ─────────────────────────────────────────    │    │
│  │                                               │    │
│  │  *1. Python ile Web Scraping Workshop*        │    │
│  │  🕐 20:00 · ⏱ 1.5 saat · 📍 Zoom             │    │
│  │  👤 @ahmet · 🙋 5 kisi ilgi gosterdi          │    │
│  │                                               │    │
│  │  [🔗 Katil]  [📅 Takvime Ekle]                │    │
│  │                                               │    │
│  │  ─────────────────────────────────────────    │    │
│  │                                               │    │
│  │  *2. React State Management Sohbeti*          │    │
│  │  🕐 21:30 · ⏱ 1 saat · 📍 #frontend-kanal    │    │
│  │  👤 @ayse · 🙋 3 kisi ilgi gosterdi           │    │
│  │                                               │    │
│  │  [🔗 Kanala Git]  [📅 Takvime Ekle]           │    │
│  │                                               │    │
│  │  ─────────────────────────────────────────    │    │
│  │                                               │    │
│  │  _Iyi etkinlikler! 🚀_                        │    │
│  │                                               │    │
│  └───────────────────────────────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 5.4 10 Dakika Oncesi Hatirlatma

- Hedef: Duyuru kanallari (3.3)
- Icerik: Tek etkinlik bildirimi
- Butonlar: **Link** + **Google Takvime Ekle**
- "Katilacagim" diyenlere e-posta hatirlatma

```
┌─────────────────────────────────────────────────────┐
│ #serbest-kursu                                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─ Event Bot ──────────────────────────────────┐    │
│  │                                               │    │
│  │  🔔 10 Dakika Sonra Basliyor!                 │    │
│  │                                               │    │
│  │  *Python ile Web Scraping Workshop*           │    │
│  │                                               │    │
│  │  🕐 *Saat:* 20:00                             │    │
│  │  ⏱ *Sure:* 1.5 saat                          │    │
│  │  📍 *Lokasyon:* Zoom                          │    │
│  │  👤 *Duzenleyen:* @ahmet                      │    │
│  │  🙋 *Ilgi:* 5 kisi                            │    │
│  │                                               │    │
│  │  [🔗 Katil]  [📅 Google Takvime Ekle]          │    │
│  │                                               │    │
│  └───────────────────────────────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 5.5 Ilgi Gosterme Mekanizmasi

Kullanicilar iki yolla ilgi gosterebilir:
- **[🙋 Katilacagim] butonu** — duyuru/hatirlatma mesajlarindaki buton (tek tikla ilgi gosterir)
- **`/event add_me` komutu** — modal form ile secim (bolum 2.1'deki mockup)

Her iki yol da ayni backend mantigini kullanir:
1. `event_interest` tablosunda `(event_id, slack_id)` cifti kontrol edilir
2. Kayit yoksa olusturulur → ephemeral basari mesaji + DM
3. Kayit varsa → ephemeral "zaten ilgi gosterdiniz" mesaji (race condition durumu)
4. Sadece `APPROVED` statusundeki etkinliklere ilgi gosterilebilir

**Farklar:**
- **Buton:** Duyuru mesajindaki etkinlige dogrudan ilgi gosterir
- **Form:** Kullanici onumuzdeki 1 ay icindeki, henuz ilgi gostermedigi etkinlikleri dropdown'dan secer. Zaten ilgi gosterilen etkinlikler dropdown'da listelenmez.

Buton tiklandiktan sonra buton metni degismez (Slack buton state desteklemez), ancak alt context satiri guncellenir: `_5 kisi ilgi gosterdi_`

### 5.6 Google Takvim Linki

API entegrasyonu degil, URL semasi ile olusturulur:

```
https://calendar.google.com/calendar/render?action=TEMPLATE
  &text=Etkinlik Adi
  &dates=20260408T170000Z/20260408T180000Z
  &details=Aciklama
  &location=Link
```

Kullanicinin Google hesabina yonlendirir, tek tikla takvime ekler. API key veya OAuth gerektirmez.

---

## 6. Guncelleme Mekanizmasi (`/event update`)

### 6.1 Yetki

- **Etkinlik sahibi:** Sadece kendi etkinliklerini gorur ve guncelleyebilir
- **Admin:** Tum aktif etkinlikleri gorur ve guncelleyebilir

### 6.2 Guncellenebilir Durumlar

Sadece `APPROVED` statusundeki etkinlikler guncellenebilir. `PENDING`, `REJECTED`, `CANCELLED`, `COMPLETED` statusundeki etkinlikler guncellenmez.

### 6.3 Guncelleme Akisi (Iki Adimli Modal)

1. `/event update` komutu girilir (ID parametresi yok)
2. **1. Modal acilir** — dropdown'da kullanicinin yetkisine gore aktif etkinlikler listelenir
3. Kullanici dropdown'dan guncellenecek etkinligi secer ve **Devam** butonuna basar
4. **2. Modal acilir** — event formu (Bolum 3) mevcut degerlerle dolu gelir
5. Kullanici degisiklikleri yapar ve gonderir
6. DB guncellenir (direkt, tekrar onay gerekmez)
7. Admin'e bildirim gonderilir:
   - **Slack mesaji:** Admin kanalina oncesi/sonrasi karsilastirmali bildirim
   - **E-posta:** Ayni oncesi/sonrasi detay
8. Duyuru kanallarina (5.1) "Etkinlik guncellendi" bildirisi gonderilir
9. "Katilacagim" diyenlere e-posta: guncellenmis etkinlik detaylari

### 6.4 Etkinlik Secim Formu (1. Modal)

Dropdown icerigi yetkiye gore degisir:
- **Normal kullanici:** Sadece kendi olusturdugu APPROVED etkinlikler
- **Admin:** Tum APPROVED etkinlikler

Dropdown secenekleri tarihe gore siralanir. Her secenek etkinlik adi ve duzenleyenin gercek ismini icerir (Slack API'den cozumlenir).

```
┌─────────────────────────────────────────────────┐
│          Etkinlik Guncelle — Secim          [X]  │
├─────────────────────────────────────────────────┤
│                                                  │
│  Guncellenecek Etkinlik *                        │
│  ┌─────────────────────────────────────────────┐ │
│  │ Etkinlik secin...                       [v] │ │
│  │                                             │ │
│  │  · 15 Nis — RAG Sohbetleri (Ahmet Yilmaz)  │ │
│  │  · 18 Nis — Python Workshop (Ayse Demir)    │ │
│  │  · 22 Nis — DevOps Sunumu (Can Kaya)        │ │
│  │                                             │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│                       [Iptal]  [Devam]            │
└─────────────────────────────────────────────────┘
```

**Etkinlik yoksa (ephemeral):**

```
┌─ Event Bot (sadece sana gorunur) ──────────────────┐
│                                                     │
│  📭 Guncellenebilecek aktif etkinliginiz yok.        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 6.5 Guncelleme Formu (2. Modal)

Secilen etkinligin mevcut bilgileriyle dolu gelen event formu (Bolum 3). Tum alanlar `initial_value` / `initial_date` / `initial_time` / `initial_option` / `initial_channel` ile dolu gelir. Kullanici sadece degistirmek istedigi alani duzenler.

### 6.6 Oncesi/Sonrasi Bildirim Formati

Admin'e giden bildirimde degisen alanlar vurgulanir. Sadece degisen alanlar listelenir, degismeyenler gosterilmez.

**Admin kanalina giden guncelleme bildirimi:**

```
┌─────────────────────────────────────────────────────┐
│ #admin-kanal                                         │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─ Event Bot ──────────────────────────────────┐    │
│  │                                               │    │
│  │  ✏️ Etkinlik Guncellendi                      │    │
│  │                                               │    │
│  │  *Python ile Web Scraping Workshop*           │    │
│  │  👤 *Guncelleyen:* @ahmet                     │    │
│  │                                               │    │
│  │  ─────────────────────────────────────────    │    │
│  │  *Degisen Alanlar:*                           │    │
│  │                                               │    │
│  │  📅 *Tarih:*                                   │    │
│  │     ~10 Nisan 2026~ → *12 Nisan 2026*         │    │
│  │                                               │    │
│  │  🕐 *Saat:*                                    │    │
│  │     ~15:00~ → *17:00*                          │    │
│  │                                               │    │
│  │  🔗 *Link:*                                    │    │
│  │     — → *https://meet.google.com/xyz*          │    │
│  │                                               │    │
│  │  ─────────────────────────────────────────    │    │
│  │  _#EVT-a1b2 · Guncelleme: 10 Nisan 14:30_    │    │
│  │                                               │    │
│  └───────────────────────────────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Duyuru kanallarina giden guncelleme bildirimi:**

```
┌─────────────────────────────────────────────────────┐
│ #serbest-kursu                                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─ Event Bot ──────────────────────────────────┐    │
│  │                                               │    │
│  │  ✏️ Etkinlik Guncellendi                      │    │
│  │                                               │    │
│  │  *Python ile Web Scraping Workshop*           │    │
│  │                                               │    │
│  │  📅 *Yeni Tarih:* 12 Nisan 2026               │    │
│  │  🕐 *Yeni Saat:* 17:00                        │    │
│  │  ⏱ *Sure:* 1.5 saat                          │    │
│  │  📍 *Lokasyon:* Google Meet                   │    │
│  │  🔗 *Link:* https://meet.google.com/xyz       │    │
│  │  👤 *Duzenleyen:* @ahmet                      │    │
│  │                                               │    │
│  │  ─────────────────────────────────────────    │    │
│  │                                               │    │
│  │  [🙋 Katilacagim]  [📅 Google Takvime Ekle]   │    │
│  │                                               │    │
│  └───────────────────────────────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 7. Iptal Mekanizmasi

### 7.1 Yetki (Iptal)

- **Etkinlik sahibi:** Sadece kendi etkinliklerini gorur ve iptal edebilir
- **Admin:** Tum aktif etkinlikleri gorur ve iptal edebilir

### 7.2 Iptal Akisi

1. `/event cancel` komutu girilir (ID parametresi yok)
2. Modal acilir — dropdown'da kullanicinin yetkisine gore aktif etkinlikler listelenir
3. Kullanici dropdown'dan iptal edilecek etkinligi secer ve onaylar
4. DB status → `CANCELLED`
5. Duyuru kanallarina (3.3) iptal bildirisi
6. Admin kanalina (`slack_admin_channel`) iptal bildirimi (etkinlik adi, tarih, duzenleyen, iptal eden)
7. Etkinlik sahibine Slack DM + e-posta (admin iptal ettiyse)
8. "Katilacagim" diyenlere e-posta: "Etkinlik iptal edildi"

### 7.3 Iptal Formu (Modal)

Dropdown icerigi yetkiye gore degisir:
- **Normal kullanici:** Sadece kendi olusturdugu APPROVED etkinlikler
- **Admin:** Tum APPROVED etkinlikler

Dropdown secenekleri tarihe gore siralanir. Her secenek etkinlik adi ve duzenleyenin gercek ismini icerir (Slack API'den `display_name` veya `real_name` cozumlenir).

```
┌─────────────────────────────────────────────────┐
│            Etkinlik Iptal Et                [X]  │
├─────────────────────────────────────────────────┤
│                                                  │
│  Iptal Edilecek Etkinlik *                       │
│  ┌─────────────────────────────────────────────┐ │
│  │ Etkinlik secin...                       [v] │ │
│  │                                             │ │
│  │  · 15 Nis — RAG Sohbetleri (Ahmet Yilmaz)  │ │
│  │  · 18 Nis — Python Workshop (Ayse Demir)    │ │
│  │  · 22 Nis — DevOps Sunumu (Can Kaya)        │ │
│  │                                             │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│                    [Iptal]  [Etkinligi Iptal Et]  │
└─────────────────────────────────────────────────┘
```

**Etkinlik yoksa (ephemeral):**

```
┌─ Event Bot (sadece sana gorunur) ──────────────────┐
│                                                     │
│  📭 Iptal edilebilecek aktif etkinliginiz yok.       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 7.4 Iptal Sonrasi Bildirimler

**Duyuru kanallarina giden iptal bildirisi:**

```
┌─────────────────────────────────────────────────────┐
│ #serbest-kursu                                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─ Event Bot ──────────────────────────────────┐    │
│  │                                               │    │
│  │  ❌ Etkinlik Iptal Edildi                      │    │
│  │                                               │    │
│  │  *Python ile Web Scraping Workshop*           │    │
│  │                                               │    │
│  │  📅 15 Nisan 2026 · 🕐 20:00                  │    │
│  │  👤 *Duzenleyen:* @ahmet                      │    │
│  │  🚫 *Iptal Eden:* @admin                      │    │
│  │                                               │    │
│  │  Bu etkinlik iptal edilmistir.                 │    │
│  │                                               │    │
│  │  _#EVT-a1b2_                                  │    │
│  │                                               │    │
│  └───────────────────────────────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Etkinlik sahibine iptal DM'i (admin iptal ettiyse):**

```
┌─ Event Bot → @ahmet (DM) ─────────────────────────┐
│                                                     │
│  ❌ Etkinliginiz Iptal Edildi                        │
│                                                     │
│  *Python ile Web Scraping Workshop*                  │
│  📅 15 Nisan 2026 · 🕐 20:00                        │
│                                                     │
│  Bu etkinlik admin tarafindan iptal edildi.           │
│                                                     │
│  Yeni bir etkinlik talebi icin `/event create`       │
│  komutunu kullanabilirsiniz.                         │
│  _#EVT-a1b2_                                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Kullaniciya iptal onay mesaji (kendi iptal ettiyse, ephemeral):**

```
┌─ Event Bot (sadece sana gorunur) ──────────────────┐
│                                                     │
│  ✅ Etkinlik basariyla iptal edildi.                  │
│                                                     │
│  *Python ile Web Scraping Workshop*                  │
│  📅 15 Nisan 2026 · 🕐 20:00                        │
│  _#EVT-a1b2_                                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 8. Veritabani Modelleri

### 8.1 events Tablosu

| Kolon | Tip | Aciklama |
|-------|-----|----------|
| id | String(60) PK | EVT-uuid |
| creator_slack_id | String(32) | Olusturan kullanicinin Slack ID'si |
| name | String(255) | Etkinlik adi |
| topic | String(255) | Konu |
| description | Text | Aciklama & Amac |
| date | Date | Etkinlik tarihi |
| time | Time | Baslangic saati |
| duration_minutes | Integer | Sure (dakika) |
| location_type | String(32) | Lokasyon tipi (slack_channel / zoom / youtube / google_meet / discord / other) |
| channel_id | String(32) null | Slack kanali (lokasyon slack_channel ise dolu) |
| link | String(500) null | Etkinlik linki (harici platform veya Drive linki) |
| yzta_request | Text null | YZTA'dan beklenen |
| status | Enum(EventStatus) | PENDING / APPROVED / REJECTED / CANCELLED / COMPLETED |
| admin_note | Text null | Admin onay/red notu |
| approved_by | String(32) null | Onaylayan admin slack_id |
| meta | JSONB null | Ek veriler |
| created_at | DateTime(tz) | TimestampMixin |
| updated_at | DateTime(tz) | TimestampMixin |

### 8.2 event_interest Tablosu

| Kolon | Tip | Aciklama |
|-------|-----|----------|
| id | String(60) PK | EVI-uuid |
| event_id | String(60) FK → events | Etkinlik referansi |
| slack_id | String(32) | Katilacagim diyen kullanici |
| meta | JSONB null | Ek veriler |
| created_at | DateTime(tz) | TimestampMixin |
| updated_at | DateTime(tz) | TimestampMixin |

### 8.3 EventStatus Enum

| Status | Aciklama |
|--------|----------|
| PENDING | Form gonderildi, admin onayi bekleniyor |
| APPROVED | Admin onayladi, etkinlik aktif |
| REJECTED | Admin reddetti veya 3 gun timeout |
| CANCELLED | Onay sonrasi sahip veya admin iptal etti |
| COMPLETED | Etkinlik tarihi gecti, gerceklesmis |

---

## 9. Dosya Yapisi

### 9.1 Yeni Olusturulacak Dosyalar

```
services/
  event_service/
    __init__.py
    logger.py                     Kendi log konfigurasyonu
    handlers/
      __init__.py                 Handler kayitlarini aktive eder
      commands/
        __init__.py
        event.py                  /event [create|list|my_list|history|add_me|update|cancel|help]
      events/
        __init__.py
        event.py                  Modal submit, admin onayla/reddet, katilacagim butonu
    core/
      __init__.py
      scheduler.py                Background: 3 gun timeout, gun basi hatirlatma,
                                  10dk oncesi hatirlatma, COMPLETED gecisi
    utils/
      __init__.py
      notifications.py            Duyuru, hatirlatma, iptal bildirimleri (Slack)
      email.py                    E-posta bildirimleri (packages/smtp kullanir)
      calendar.py                 Google Calendar URL olusturucu

packages/
  database/
    models/
      event.py                    Event, EventInterest, EventStatus (YENI DOSYA)
    repository/
      event.py                    EventRepository, EventInterestRepository (YENI DOSYA)

migrations/
  versions/
    0003_add_event_tables.py      YENI DOSYA
```

### 9.2 Mevcut Dosyalara Eklemeler (Sadece Ekleme)

| Dosya | Ekleme |
|-------|--------|
| `packages/settings.py` | `event_channel`, `event_reminder_enabled`, `event_approval_timeout_hours` alanlari |
| `packages/database/models/base.py` | `from packages.database.models import event as _event` (1 satir) |

Mevcut hicbir dosyada silme veya degistirme yok.

---

## 10. Scheduler (Background Gorevler)

`services/event_service/core/scheduler.py` asagidaki periyodik gorevleri calistirir:

| Gorev | Periyot | Aciklama |
|-------|---------|----------|
| Timeout kontrolu | Her saat | PENDING + 72 saat gecmis → REJECTED |
| Gun basi hatirlatma | Her gun sabah (ayarlanabilir) | O gunun etkinliklerini duyur + e-posta |
| 10dk oncesi hatirlatma | Her dakika kontrol | 10dk icinde baslayacak etkinlikleri duyur + e-posta |
| COMPLETED gecisi | Her saat | Tarihi gecmis APPROVED etkinlikleri COMPLETED yap |

---

## 11. Settings Alanlari (packages/settings.py'ye eklenecek)

| Alan | Tip | Default | Aciklama |
|------|-----|---------|----------|
| event_channel | str | — | `#serbest-kursu` kanal ID'si |
| event_reminder_enabled | bool | True | Hatirlatma sistemi acik/kapali |
| event_approval_timeout_hours | int | 72 | Admin onay suresi (saat) |
