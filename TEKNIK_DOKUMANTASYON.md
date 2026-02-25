# PLATFORMAVRUPA - KAPSAMLI PROJE DOKÜMANTASYONU

**Versiyon:** 3.0 Final  
**Tarih:** 2026-02-04  
**Web:** www.platformavrupa.com  
**Domain:** platformavrupa.com, platformavrupa.eu (yedek)  
**Hedef:** Avrupa'daki Türk diasporası için "Süper Uygulama"  
**Durum:** Production Ready ✅

---

## 📋 İÇİNDEKİLER

1. [Proje Özeti](#proje-özeti)
2. [Teknoloji Stack](#teknoloji-stack)
3. [Mimari Yapı](#mimari-yapı)
4. [Modüller ve Özellikler](#modüller-ve-özellikler)
5. [Veritabanı Yapısı](#veritabanı-yapısı)
6. [Dosya Yapısı](#dosya-yapısı)
7. [API Entegrasyonları](#api-entegrasyonları)
8. [Güvenlik](#güvenlik)
9. [Deployment](#deployment)
10. [Mobil Dönüşüm](#mobil-dönüşüm)
11. [Geliştirme Notları](#geliştirme-notları)
12. [Gelecek Planlar](#gelecek-planlar)

---

## 🎯 PROJE ÖZETİ

### Proje Kimliği
- **Ad:** Platform Avrupa
- **Misyon:** Avrupa'da yaşayan Türk diasporası için kapsamlı dijital platform
- **Hedef Kitle:** Avrupa'da yerleşik, çalışma izni olan Türkler
- **Vizyon:** Web (PWA) ile başlandı, nihai hedef **Native Mobil Uygulama**
- **Domain:** www.platformavrupa.com (aktif), www.platformavrupa.eu (yedek)
- **Email:** info@platformavrupa.com (Zoho)

### Temel Özellikler
- ✅ İlan Yönetimi (7 kategori: Emlak, Araç, İş, Hizmet, Eşya, Yemek, Diğer)
- ✅ Topluluk Sohbeti (Genel + Şehir bazlı)
- ✅ Yol Arkadaşı (BlaBlaCar benzeri, bagaj odaklı)
- ✅ Kargo & Emanet (Türkiye'ye evrak/anahtar/koli gönderimi)
- ✅ Yol Yardım & SOS (Topluluk destekli acil yardım)
- ✅ Waze Benzeri Yol Bildirimleri (Radar, kaza, trafik, yol çalışması)
- ✅ Market Fiyatları & İndirimler (30 ülke, 100+ market zinciri)
- ✅ Akademi (Video eğitimler: Dil, Resmi İşlemler, Kariyer, Finans, Yaşam, Sıla Yolu, Hukuk, Aile)
- ✅ Döviz & Altın Fiyatları (Canlı, grafikli)
- ✅ Sıla Yolu (Gümrük kapıları, kameralar, rota planlama)
- ✅ Hukuk Danışmanlığı (Avukat rehberi)
- ✅ Sağlık Turizmi (Saç ekimi, diş, estetik, cinsel sağlık, tüp bebek)
- ✅ Affiliate Sistemi (Uçak, Otel, Araç, Tatil)
- ✅ Duyurular (Otomatik haber önerileri)
- ✅ Admin Paneli (Kapsamlı yönetim)

---

## 🛠 TEKNOLOJİ STACK

### Frontend
- **HTML5** - Semantic markup
- **Vanilla JavaScript (ES6+)** - Framework-free, derleme gerektirmeyen
- **Tailwind CSS** - Utility-first CSS framework (CDN)
- **Font Awesome 6.5.0** - İkonlar
- **Plus Jakarta Sans / Inter / Space Grotesk** - Google Fonts
- **SweetAlert2** - Modern alert/modal
- **Chart.js** - Grafikler (Döviz/Altın, Analytics)

### Backend & Database
- **Supabase** - PostgreSQL veritabanı
  - Authentication (Email/Password)
  - Row Level Security (RLS)
  - Realtime Subscriptions
  - Storage (gelecekte)
  - Edge Functions (Deno)
- **PostgreSQL** - İlişkisel veritabanı

### Harita & Konum
- **Google Maps JavaScript API** - Harita görselleştirme
- **Google Distance Matrix API** - Mesafe hesaplama
- **Leaflet.js** - Alternatif harita kütüphanesi (Sıla Yolu)
- **Nominatim OpenStreetMap API** - Geocoding
- **Browser Geolocation API** - Kullanıcı konumu

### Harici API'ler
- **NewsAPI** - Otomatik haber önerileri (100 req/gün ücretsiz)
- **ExchangeRate-API** - Döviz kurları
- **Frankfurter API** - Tarihsel döviz verileri
- **Travelpayouts API** - Uçak bileti fırsatları (yapılandırma gerekli)
- **Booking.com Deals API** - Otel promosyonları (yapılandırma gerekli)
- **Adzuna API** - İş ilanları (admin paneli)
- **Rentalcars.com** - Araç kiralama affiliate
- **Supabase Edge Functions** - Backend proxy (altın fiyatları, CORS bypass)

### PWA & Mobil
- **Progressive Web App (PWA)** - manifest.json + service-worker.js
- **Capacitor** - Native mobil dönüşüm için hazır (capacitor.config.json)
- **Service Worker** - Offline destek, cache yönetimi

### Hosting & CDN
- **Netlify** - Statik hosting
- **CDN** - Tailwind, Font Awesome, Supabase JS (CDN üzerinden)

---

## 🏗 MİMARİ YAPI

### Mimari Yaklaşım
- **Client-Side Rendering** - Tüm işlemler tarayıcıda
- **SPA Benzeri Yapı** - app-core.js ile routing
- **Merkezi Yapılandırma** - config.js, auth.js, utils.js
- **Component-Based** - components.js (Navbar, Footer, Bottom Nav)
- **Serverless** - Supabase Edge Functions ile backend işlemleri

### Dosya Organizasyonu

```
proje-klasoru/
├── Core Files (Çekirdek)
│   ├── config.js          # Supabase, API keys, Affiliate config
│   ├── auth.js            # Authentication logic
│   ├── utils.js           # Utility functions (sanitize, XSS koruma)
│   ├── components.js      # Reusable UI components
│   ├── app-core.js        # SPA routing, PWA, Capacitor hazırlığı
│   ├── favorites.js       # Favori yönetimi
│   └── service-worker.js  # PWA offline desteği
│
├── Data Files (Veri)
│   ├── genel_veriler.js   # Ülke/şehir, telefon kodları, market zincirleri
│   ├── supabase_rls_policies.sql  # Veritabanı şeması ve RLS
│   └── supabase_health_sample_data.sql  # Sağlık turizmi örnek veriler
│
├── Pages (Sayfalar) - 57 HTML dosyası
│   ├── index.html         # Ana sayfa
│   ├── login.html         # Giriş
│   ├── kayit.html         # Kayıt
│   ├── profil.html        # Kullanıcı profili
│   ├── admin.html         # Admin paneli
│   ├── sohbet.html        # Topluluk sohbeti
│   ├── ilanlar.html       # İlan listesi
│   ├── ilan_giris.html    # İlan verme seçimi
│   ├── ilan_*.html        # Kategori bazlı ilan formları (7 kategori)
│   ├── *_vitrini.html     # Kategori vitrinleri
│   ├── akademi*.html      # Akademi sayfaları
│   ├── yol_*.html         # Yol arkadaşı, yol yardım
│   ├── kargo_*.html       # Kargo & Emanet
│   ├── market.html        # Market fiyatları
│   ├── doviz_altin.html   # Döviz & Altın
│   ├── sila_yolu.html     # Sıla Yolu
│   ├── saglik_turizmi.html  # Sağlık Turizmi
│   ├── arac_kiralama.html  # Araç Kiralama
│   └── ... (diğer sayfalar)
│
├── Config Files (Yapılandırma)
│   ├── manifest.json      # PWA manifest
│   ├── capacitor.config.json  # Capacitor config
│   └── _headers           # Netlify cache headers
│
├── Supabase Functions (Edge Functions)
│   └── supabase/functions/gold-price/index.ts  # Altın fiyatları backend proxy
│
└── Assets (Varlıklar)
    └── logo.png           # Logo
```

---

## 📦 MODÜLLER VE ÖZELLİKLER

### 1. İlan Yönetimi
**Kategoriler:**
- Emlak (Satılık, Kiralık, Günlük Kiralık)
- Araç (Satılık, Kiralık)
- İş (Tam Zamanlı, Yarı Zamanlı, Freelance)
- Hizmet (Tamirci, Çekici, Temizlik, vb.)
- Eşya (Satılık, Takas)
- Yemek (Restoran, Ev Yemeği)
- Diğer

**Özellikler:**
- Filtreleme (kategori, şehir, fiyat, tarih)
- Favorilere ekleme
- Detaylı ilan sayfası
- Kullanıcı ilanları yönetimi
- Admin onayı sistemi

### 2. Topluluk Sohbeti
- Genel sohbet odası
- Şehir bazlı sohbet odaları
- Gerçek zamanlı mesajlaşma (Supabase Realtime)
- Emoji desteği
- Admin mesaj yönetimi

### 3. Yol Arkadaşı
- BlaBlaCar benzeri sistem
- Bagaj odaklı ilan yapısı
- Filtreler: Cinsiyet, sigara, müzik, evcil hayvan
- Rezervasyon sistemi
- Mesafe hesaplama (Google Distance Matrix)

### 4. Kargo & Emanet
- Türkiye'ye evrak/anahtar/koli gönderimi
- Paket kabul edenler ve gönderenler eşleştirme
- Takip numarası
- Güvenlik: Paket kontrolü uyarısı
- Ödeme: Nakit (araç başında)

### 5. Yol Yardım & SOS
- Acil yardım talepleri
- Yakındaki kullanıcılara bildirim (50km çap)
- Doğrulanmış tamirci/çekici veritabanı
- Yıldız/puanlama sistemi
- Acil numaralar (30 ülke)

### 6. Waze Benzeri Yol Bildirimleri
- Radar uyarıları
- Kaza bildirimleri
- Trafik yoğunluğu
- Yol çalışması
- Harita üzerinde görselleştirme

### 7. Market Fiyatları & İndirimler
- 30 Avrupa ülkesi
- 100+ market zinciri
- Haftalık broşürler
- Otomatik konum tespiti
- Direkt broşür linkleri

### 8. Akademi
**Kategoriler:**
- Dil Eğitimi
- Resmi İşlemler
- Kariyer
- Finans
- Yaşam
- Sıla Yolu
- Hukuk
- Aile

**Özellikler:**
- Video serileri (YouTube embed)
- İzlenme takibi
- Kullanıcı talepleri
- Admin video yönetimi

### 9. Döviz & Altın Fiyatları
- Canlı döviz kurları (30+ para birimi)
- Altın fiyatları (Gram, Çeyrek, Yarım, Tam, Cumhuriyet, Ata, vb.)
- 30 günlük grafik
- Otomatik güncelleme (30 dakikada bir)
- Supabase Edge Function ile backend proxy

### 10. Sıla Yolu
- Gümrük kapıları yoğunluk takibi
- Canlı kamera görüntüleri
- Akıllı rota önerileri
- Mesafe hesaplama
- Trafik durumu

### 11. Hukuk Danışmanlığı
- Avukat rehberi
- Uzmanlık alanları
- İletişim bilgileri
- Değerlendirme sistemi

### 12. Sağlık Turizmi
**Kategoriler:**
- Saç Ekimi (FUE, DHI, vb.)
- Diş Tedavisi
- Estetik Cerrahi
- Erkek Cinsel Sağlık
- Kadın Cinsel Sağlık
- Tüp Bebek

**Özellikler:**
- Klinik rehberi
- Ücretsiz danışmanlık formu
- WhatsApp entegrasyonu
- Referans kodu sistemi
- Komisyon takibi
- Bypass korumalı sistem (klinik bilgileri gizli)

### 13. Affiliate Sistemi
- Skyscanner (Uçak bileti)
- Booking.com (Otel)
- Rentalcars.com (Araç kiralama)
- Tatil Sepeti (Tatil paketleri)
- Viator (Turlar)

**Özellikler:**
- Tıklama takibi
- Referans kodu
- Komisyon hesaplama

### 14. Admin Paneli
**Modüller:**
- Genel Bakış (Dashboard)
- Market & İndirim
- Kullanıcılar
- İlan Yönetimi
- Sınır Kapıları
- Kameralar
- Yolculuk & Kargo
- Yol Yardım & SOS
- Canlı Yol Bildirimleri
- Bot & Entegrasyon
- Sohbet Yönetimi
- Seyahat & Turlar
- Akademi & Eğitim
- Hukuk
- Sağlık Turizmi
- Duyurular
- Raporlar

---

## 🗄 VERİTABANI YAPISI

### Supabase PostgreSQL Tabloları

#### Kullanıcı & Kimlik Doğrulama
- `auth.users` - Supabase auth tablosu
- `profiles` - Kullanıcı profilleri
  - `id` (UUID, PK)
  - `role` (TEXT: 'user', 'admin')
  - `status` (TEXT: 'active', 'banned')
  - `country` (TEXT)
  - `city` (TEXT)
  - `real_name` (TEXT)
  - `avatar_url` (TEXT)

#### İlanlar
- `listings` - Tüm ilanlar
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `category` (TEXT: 'emlak', 'araba', 'is', 'hizmet', 'esya', 'yemek', 'diger')
  - `title` (TEXT)
  - `description` (TEXT)
  - `price` (DECIMAL)
  - `currency` (TEXT)
  - `location` (TEXT)
  - `city` (TEXT)
  - `country` (TEXT)
  - `image_url` (TEXT[])
  - `status` (TEXT: 'pending', 'active', 'sold', 'deleted')
  - `created_at` (TIMESTAMP)

- `favorites` - Kullanıcı favorileri
  - `id` (UUID, PK)
  - `user_id` (UUID, FK)
  - `ilan_id` (BIGINT, FK)

#### Topluluk
- `messages` - Sohbet mesajları
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `room_id` (TEXT: 'genel' veya şehir adı)
  - `message` (TEXT)
  - `created_at` (TIMESTAMP)

- `announcements` - Duyurular
  - `id` (BIGSERIAL, PK)
  - `title` (TEXT)
  - `content` (TEXT)
  - `image_url` (TEXT)
  - `status` (TEXT: 'draft', 'published')
  - `created_at` (TIMESTAMP)

#### Yolculuk & Kargo
- `trips` - Yol arkadaşı ilanları
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `from_location` (TEXT)
  - `to_location` (TEXT)
  - `from_lat` (DECIMAL)
  - `from_lng` (DECIMAL)
  - `to_lat` (DECIMAL)
  - `to_lng` (DECIMAL)
  - `departure_date` (DATE)
  - `departure_time` (TIME)
  - `available_seats` (INTEGER)
  - `price_per_seat` (DECIMAL)
  - `currency` (TEXT)
  - `phone` (TEXT)
  - `travel_time` (TEXT)
  - `stops` (TEXT)
  - `car_brand` (TEXT)
  - `car_model` (TEXT)
  - `car_color` (TEXT)
  - `no_smoking` (BOOLEAN)
  - `music_allowed` (BOOLEAN)
  - `pets_allowed` (BOOLEAN)
  - `notes` (TEXT)
  - `status` (TEXT: 'active', 'completed', 'cancelled')

- `trip_reservations` - Yol rezervasyonları
  - `id` (UUID, PK)
  - `trip_id` (BIGINT, FK)
  - `passenger_id` (UUID, FK)
  - `passenger_name` (TEXT)
  - `passenger_phone` (TEXT)
  - `seats_requested` (INTEGER)
  - `status` (TEXT: 'pending', 'approved', 'rejected', 'cancelled')
  - `message` (TEXT)

- `shipments` - Kargo & Emanet talepleri
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `type` (TEXT: 'request', 'offer')
  - `from_location` (TEXT)
  - `to_location` (TEXT)
  - `from_lat` (DECIMAL)
  - `from_lng` (DECIMAL)
  - `to_lat` (DECIMAL)
  - `to_lng` (DECIMAL)
  - `departure_date` (DATE)
  - `weight` (DECIMAL)
  - `size` (TEXT)
  - `package_count` (INTEGER)
  - `is_fragile` (BOOLEAN)
  - `price_offer` (DECIMAL)
  - `insurance` (TEXT)
  - `phone` (TEXT)
  - `delivery_preference` (TEXT)
  - `notes` (TEXT)
  - `tracking_number` (TEXT, UNIQUE)
  - `status` (TEXT: 'active', 'matched', 'completed', 'cancelled')

#### Yol Yardım & SOS
- `sos_alerts` - Acil yardım talepleri
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `location` (TEXT)
  - `lat` (DECIMAL)
  - `lng` (DECIMAL)
  - `problem_type` (TEXT)
  - `description` (TEXT)
  - `phone` (TEXT)
  - `status` (TEXT: 'active', 'resolved', 'cancelled')
  - `created_at` (TIMESTAMP)

- `help_responses` - Yardım teklifleri
  - `id` (BIGSERIAL, PK)
  - `alert_id` (BIGINT, FK)
  - `user_id` (UUID, FK)
  - `message` (TEXT)
  - `phone` (TEXT)
  - `status` (TEXT: 'pending', 'accepted', 'rejected')

- `emergency_numbers` - Acil numaralar (30 ülke)
  - `id` (BIGSERIAL, PK)
  - `country` (TEXT)
  - `police` (TEXT)
  - `ambulance` (TEXT)
  - `fire` (TEXT)
  - `other` (JSONB)

- `user_locations` - Kullanıcı konumları
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `lat` (DECIMAL)
  - `lng` (DECIMAL)
  - `updated_at` (TIMESTAMP)

#### Yol Bildirimleri
- `road_reports` - Waze benzeri yol bildirimleri
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `report_type` (TEXT: 'radar', 'accident', 'traffic', 'roadwork', 'hazard')
  - `location` (TEXT)
  - `lat` (DECIMAL)
  - `lng` (DECIMAL)
  - `description` (TEXT)
  - `verified_count` (INTEGER)
  - `created_at` (TIMESTAMP)

#### Market & İndirimler
- `market_chains` - Market zincirleri (30 ülke)
  - `id` (BIGSERIAL, PK)
  - `name` (TEXT)
  - `country` (TEXT)
  - `logo_url` (TEXT)
  - `website` (TEXT)
  - `brochure_url` (TEXT)
  - `is_active` (BOOLEAN)

- `user_deals` - Kullanıcı paylaşımları
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `market_id` (BIGINT, FK)
  - `product_name` (TEXT)
  - `old_price` (DECIMAL)
  - `new_price` (DECIMAL)
  - `image_url` (TEXT)
  - `location` (TEXT)
  - `status` (TEXT: 'pending', 'approved', 'rejected')

- `user_points` - Gamification
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `points` (INTEGER)
  - `badges` (TEXT[])

#### Akademi
- `academy_categories` - Eğitim kategorileri
  - `id` (BIGSERIAL, PK)
  - `name` (TEXT)
  - `description` (TEXT)
  - `icon` (TEXT)

- `academy_series` - Video serileri
  - `id` (BIGSERIAL, PK)
  - `category_id` (BIGINT, FK)
  - `title` (TEXT)
  - `description` (TEXT)
  - `thumbnail_url` (TEXT)
  - `order` (INTEGER)

- `academy_videos` - Videolar
  - `id` (BIGSERIAL, PK)
  - `series_id` (BIGINT, FK)
  - `title` (TEXT)
  - `description` (TEXT)
  - `youtube_id` (TEXT)
  - `duration` (INTEGER)
  - `order` (INTEGER)

- `academy_views` - İzlenme takibi
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `video_id` (BIGINT, FK)
  - `watched_at` (TIMESTAMP)

- `academy_requests` - Kullanıcı talepleri
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `category` (TEXT)
  - `request_text` (TEXT)
  - `status` (TEXT: 'pending', 'in_progress', 'completed')

#### Affiliate & Monetizasyon
- `affiliate_clicks` - Tıklama takibi
  - `id` (BIGSERIAL, PK)
  - `user_id` (UUID, FK)
  - `partner` (TEXT)
  - `click_url` (TEXT)
  - `referral_code` (TEXT)
  - `clicked_at` (TIMESTAMP)

- `promotions` - Promosyonlar
  - `id` (BIGSERIAL, PK)
  - `type` (TEXT: 'flight', 'hotel', 'car', 'vacation')
  - `title` (TEXT)
  - `description` (TEXT)
  - `image_url` (TEXT)
  - `affiliate_url` (TEXT)
  - `is_active` (BOOLEAN)

#### Sağlık Turizmi
- `health_clinics` - Klinikler
  - `id` (UUID, PK)
  - `display_name` (TEXT) - Kullanıcıya gösterilen isim
  - `internal_name` (TEXT) - Gerçek klinik ismi (sadece admin)
  - `slug` (TEXT, UNIQUE)
  - `city` (TEXT)
  - `district` (TEXT)
  - `country` (TEXT, DEFAULT 'TR')
  - `specialties` (TEXT[]) - ['saç_ekimi', 'diş', 'estetik', 'erkek_cinsel', 'kadın_cinsel', 'tüp_bebek']
  - `description` (TEXT)
  - `internal_address` (TEXT) - Sadece admin
  - `internal_phone` (TEXT) - Sadece admin
  - `internal_email` (TEXT) - Sadece admin
  - `internal_website` (TEXT) - Sadece admin
  - `logo_url` (TEXT)
  - `images` (TEXT[])
  - `accreditations` (TEXT[])
  - `price_range_min` (DECIMAL)
  - `price_range_max` (DECIMAL)
  - `currency` (TEXT, DEFAULT 'EUR')
  - `rating` (DECIMAL(3,2))
  - `review_count` (INTEGER, DEFAULT 0)
  - `languages` (TEXT[])
  - `services` (JSONB)
  - `packages` (JSONB)
  - `commission_rate` (DECIMAL(5,2))
  - `commission_type` (TEXT, DEFAULT 'percentage')
  - `minimum_commission` (DECIMAL(10,2))
  - `is_verified` (BOOLEAN, DEFAULT false)
  - `is_active` (BOOLEAN, DEFAULT true)

- `health_leads` - Danışmanlık talepleri
  - `id` (UUID, PK)
  - `user_id` (UUID, FK)
  - `clinic_id` (UUID, FK)
  - `treatment_category` (TEXT)
  - `treatment_type` (TEXT)
  - `reference_code` (TEXT, UNIQUE)
  - `full_name` (TEXT)
  - `email` (TEXT)
  - `phone` (TEXT)
  - `whatsapp` (TEXT)
  - `country_code` (TEXT)
  - `photos` (TEXT[])
  - `description` (TEXT)
  - `preferred_date` (DATE)
  - `status` (TEXT, DEFAULT 'new')
  - `clinic_contacted_at` (TIMESTAMP)
  - `clinic_quote` (DECIMAL)
  - `clinic_quote_currency` (TEXT, DEFAULT 'EUR')
  - `commission_amount` (DECIMAL(10,2))
  - `commission_paid` (BOOLEAN, DEFAULT false)
  - `commission_paid_at` (TIMESTAMP)
  - `admin_notes` (TEXT)

- `health_treatments` - Tedavi türleri
  - `id` (UUID, PK)
  - `clinic_id` (UUID, FK)
  - `category` (TEXT)
  - `subcategory` (TEXT)
  - `name` (TEXT)
  - `description` (TEXT)
  - `duration_days` (INTEGER)
  - `price_min` (DECIMAL)
  - `price_max` (DECIMAL)
  - `display_price_range` (TEXT)
  - `currency` (TEXT, DEFAULT 'EUR')
  - `techniques` (TEXT[])

- `health_reservations` - Rezervasyonlar
  - `id` (UUID, PK)
  - `lead_id` (UUID, FK)
  - `user_id` (UUID, FK)
  - `clinic_id` (UUID, FK)
  - `treatment_id` (UUID, FK)
  - `reference_code` (TEXT, UNIQUE)
  - `full_name` (TEXT)
  - `email` (TEXT)
  - `phone` (TEXT)
  - `preferred_date` (DATE)
  - `preferred_time` (TIME)
  - `notes` (TEXT)
  - `status` (TEXT, DEFAULT 'pending')
  - `commission_amount` (DECIMAL(10,2))
  - `commission_paid` (BOOLEAN, DEFAULT false)

- `health_reviews` - Değerlendirmeler
  - `id` (UUID, PK)
  - `clinic_id` (UUID, FK)
  - `user_id` (UUID, FK)
  - `treatment_id` (UUID, FK)
  - `lead_id` (UUID, FK)
  - `rating` (INTEGER, CHECK 1-5)
  - `comment` (TEXT)
  - `before_after_images` (TEXT[])
  - `is_verified` (BOOLEAN, DEFAULT false)

- `health_commission_log` - Komisyon logları
  - `id` (UUID, PK)
  - `lead_id` (UUID, FK)
  - `reservation_id` (UUID, FK)
  - `clinic_id` (UUID, FK)
  - `amount` (DECIMAL(10,2))
  - `currency` (TEXT, DEFAULT 'EUR')
  - `status` (TEXT, DEFAULT 'pending')
  - `paid_at` (TIMESTAMP)
  - `payment_method` (TEXT)
  - `notes` (TEXT)

#### Diğer
- `borders` - Sınır kapıları
  - `id` (BIGSERIAL, PK)
  - `name` (TEXT)
  - `country` (TEXT)
  - `lat` (DECIMAL)
  - `lng` (DECIMAL)
  - `current_queue` (INTEGER)
  - `estimated_wait_time` (INTEGER)
  - `last_updated` (TIMESTAMP)

- `cameras` - Gümrük kameraları
  - `id` (BIGSERIAL, PK)
  - `border_id` (BIGINT, FK)
  - `name` (TEXT)
  - `stream_url` (TEXT)
  - `is_active` (BOOLEAN)

### Row Level Security (RLS)
- Tüm tablolarda RLS aktif
- Admin-only: `profiles.role = 'admin'` kontrolü
- User-specific: `auth.uid() = user_id` kontrolü
- Public read: Bazı tablolar herkese açık (listings, announcements)
- Sağlık Turizmi: `internal_*` alanları sadece admin görür

---

## 📁 DOSYA YAPISI

### Toplam Dosya Sayısı
- **HTML Sayfaları:** 57
- **JavaScript Modülleri:** 8
- **SQL Dosyaları:** 2 (supabase_rls_policies.sql, supabase_health_sample_data.sql)
- **Config Dosyaları:** 3 (manifest.json, capacitor.config.json, _headers)
- **Edge Functions:** 1 (supabase/functions/gold-price/index.ts)

### Önemli Dosyalar

#### config.js
- Supabase bağlantısı
- API anahtarları (Google Maps, Adzuna, NewsAPI)
- Affiliate yapılandırması
- Helper fonksiyonlar (isAdmin, getCurrentUser, trackAffiliateClick)
- WhatsApp link builder (Sağlık Turizmi)

#### auth.js
- Authentication state yönetimi
- UI güncellemeleri (login/logout)
- requireAuth() fonksiyonu
- getCurrentUser() fonksiyonu

#### utils.js
- `sanitize()` - XSS koruması
- `sanitizeURL()` - URL doğrulama
- `sanitizePhone()` - Telefon formatı
- `escapeHTML()` - HTML escape

#### components.js
- `getNavbarHTML()` - Navbar component
- `getFooterHTML()` - Footer component
- `getBottomNavHTML()` - Mobil alt navigasyon

#### app-core.js
- Platform detection (Web/Native/iOS/Android)
- Basit routing
- PWA lifecycle
- Capacitor entegrasyonu hazırlığı

#### genel_veriler.js
- 30 Avrupa ülkesi ve şehirleri
- Telefon kodları
- Market zincirleri ve broşür linkleri
- Acil numaralar (30 ülke)
- Bildirim türleri (Waze benzeri)
- Altın türleri ve para birimleri
- Ziyaretçi takip sistemi

#### service-worker.js
- Offline cache yönetimi
- External API bypass (CORS önleme)
- Supabase Edge Function bypass
- Market broşür siteleri bypass

---

## 🔌 API ENTEGRASYONLARI

### Google Maps API
- **Kullanım:** Harita görselleştirme, mesafe hesaplama
- **Sayfalar:** admin.html, sila_yolu.html, yol_yardim.html
- **Güvenlik:** HTTP referer kısıtlaması önerilir
- **Key:** AIzaSyDhMlLszA1wpS9lk_T7yJIc8hb8gIiatgc

### Supabase Realtime
- **Kullanım:** Canlı sohbet, bildirimler
- **Channels:** `public:messages`, `public:sos_alerts`, `public:road_reports`
- **Subscription:** JavaScript client-side

### NewsAPI
- **Kullanım:** Otomatik haber önerileri (admin paneli)
- **Limit:** 100 request/gün (ücretsiz)
- **Filtreler:** Türkçe, Avrupa ülkeleri, özelleştirilebilir
- **Key:** fe4b9d88c63545f6a824467f7ccd25df

### ExchangeRate-API
- **Kullanım:** Canlı döviz kurları
- **Sayfa:** doviz_altin.html
- **Güncelleme:** Sayfa yüklendiğinde + 30 dakikada bir
- **Endpoint:** https://api.exchangerate-api.com/v4/latest/EUR

### Frankfurter API
- **Kullanım:** Tarihsel döviz verileri (grafik için)
- **Sayfa:** doviz_altin.html
- **Endpoint:** https://api.frankfurter.app/latest?from=EUR&to=TRY

### Supabase Edge Functions
- **gold-price** - Altın fiyatları backend proxy
  - Metals API (primary)
  - FreeGoldAPI (fallback)
  - TCMB (fallback)
  - CORS bypass
  - Deno runtime

### Adzuna API
- **Kullanım:** İş ilanları (admin paneli)
- **Sayfa:** admin.html
- **ID:** c0c66624
- **Key:** 5a2d86df68a24e6fe8b1e9b4319347f0

### Rentalcars.com
- **Kullanım:** Araç kiralama affiliate
- **Sayfa:** arac_kiralama.html
- **Affiliate Code:** Yapılandırma gerekli

### WhatsApp Business API
- **Kullanım:** Sağlık Turizmi danışmanlık talepleri
- **Sayfa:** saglik_turizmi.html
- **Yöntem:** WhatsApp link (wa.me)

---

## 🔒 GÜVENLİK

### XSS Koruması
- Tüm kullanıcı girdileri `sanitize()` ile temizleniyor
- `utils.js` içinde merkezi sanitization fonksiyonları
- HTML escape için `escapeHTML()`
- URL doğrulama için `sanitizeURL()`

### Authentication
- Supabase Auth ile email/password
- JWT token tabanlı
- `auth.js` ile merkezi yönetim
- Session yönetimi

### Row Level Security (RLS)
- Tüm tablolarda RLS aktif
- Admin-only işlemler: `profiles.role = 'admin'` kontrolü
- User-specific veriler: `auth.uid() = user_id` kontrolü
- Public read: Bazı tablolar herkese açık (listings, announcements)
- Sağlık Turizmi: `internal_*` alanları sadece admin görür

### API Key Güvenliği
- Google Maps: HTTP referer kısıtlaması önerilir
- Adzuna: Sadece admin panelinde kullanılıyor
- NewsAPI: Ücretsiz plan (100 req/gün)
- Supabase anon key: Client-side'da güvenli (RLS ile korunur)

### Admin Koruması
- `isAdmin()` fonksiyonu ile kontrol
- `requireAdmin()` ile sayfa koruması
- Admin paneli: admin.html
- RLS policies ile backend koruması

### CORS Yönetimi
- Service worker ile external API bypass
- Supabase Edge Functions ile backend proxy
- CORS proxy kullanımı (api.allorigins.win)

---

## 🚀 DEPLOYMENT

### Hosting
- **Platform:** Netlify
- **Yöntem:** Manuel sürükle-bırak veya Git entegrasyonu
- **Domain:** platformavrupa.com
- **SSL:** Otomatik (Netlify)

### Cache Yönetimi
- **Dosya:** `_headers`
- **HTML:** no-cache (her zaman güncel)
- **JS/CSS:** 1 saat cache
- **Resimler:** 1 gün cache

### Build Process
- **Build Tool:** Yok (statik HTML)
- **Derleme:** Gerektirmiyor
- **CDN:** Tailwind, Font Awesome, Supabase JS

### Environment Variables
- Supabase URL/Key: `config.js` içinde
- API Keys: `config.js` içinde
- Production'da environment variables kullanılabilir (Netlify)

### Supabase Edge Functions Deployment
- **Platform:** Supabase Dashboard
- **Runtime:** Deno
- **Deployment:** `supabase functions deploy gold-price`

---

## 📱 MOBİL DÖNÜŞÜM

### PWA (Progressive Web App)
- ✅ manifest.json mevcut
- ✅ service-worker.js mevcut
- ✅ Offline destek hazır
- ✅ Install prompt hazır
- ✅ Theme color ayarlı

### Capacitor Hazırlığı
- ✅ capacitor.config.json mevcut
- ✅ app-core.js platform detection içeriyor
- ✅ Native plugin entegrasyonu için hazır
- ✅ App ID: com.platformavrupa.app

### Mobil Optimizasyon
- ✅ Responsive design (Tailwind CSS)
- ✅ Mobil-first yaklaşım
- ✅ Touch-friendly UI
- ✅ Bottom navigation (mobil)
- ✅ Viewport meta tag

### Native Özellikler (Gelecek)
- Push notifications (Capacitor Push)
- Geolocation (Capacitor Geolocation)
- Camera (Capacitor Camera)
- File System (Capacitor Filesystem)
- Background tasks

---

## 📊 İSTATİSTİKLER

### Kod İstatistikleri
- **Toplam HTML Sayfası:** 57
- **JavaScript Modülü:** 8
- **SQL Tablo Sayısı:** 40+
- **Toplam Kod Satırı:** ~20,000+ (tahmini)

### Özellikler
- **İlan Kategorisi:** 7 (Emlak, Araç, İş, Hizmet, Eşya, Yemek, Diğer)
- **Akademi Kategorisi:** 8 (Dil, Resmi İşlemler, Kariyer, Finans, Yaşam, Sıla Yolu, Hukuk, Aile)
- **Sağlık Turizmi Kategorisi:** 6 (Saç Ekimi, Diş, Estetik, Erkek Cinsel, Kadın Cinsel, Tüp Bebek)
- **Desteklenen Ülke:** 30 Avrupa ülkesi
- **Market Zinciri:** 100+
- **Affiliate Partner:** 5 (Skyscanner, Booking, Rentalcars, Tatil Sepeti, Viator)

---

## 🔄 GELİŞTİRME NOTLARI

### Kod Standartları
- **Dil:** Türkçe (değişken isimleri, yorumlar)
- **Format:** ES6+ JavaScript
- **Stil:** Tailwind utility classes
- **Naming:** camelCase (JavaScript), kebab-case (HTML dosyaları)

### Best Practices
- ✅ Merkezi yapılandırma (config.js)
- ✅ Component reusability (components.js)
- ✅ XSS koruması (utils.js)
- ✅ RLS ile güvenlik
- ✅ Mobile-first design
- ✅ Service worker ile offline destek
- ✅ Error handling (try-catch)
- ✅ Console logging (debug için)

### Önemli Notlar
- **Asla Bozma:** Mevcut çalışan fonksiyonlara dokunma, sadece üzerine ekle
- **Mobil First:** Yazdığın her kod mobilde (telefonda) kusursuz görünmeli
- **Sadelik:** Karmaşık frameworkler kurma. CDN kullan
- **Backend Vizyonu:** İstemci tarafında (client-side) çalışıyoruz ama veritabanı sorgularını optimize et

---

## 🚧 GELECEK PLANLAR

### Kısa Vadeli (1-3 Ay)
- [ ] Native mobil uygulama (Capacitor)
- [ ] Push notifications
- [ ] Image optimization
- [ ] SEO iyileştirmeleri
- [ ] Analytics entegrasyonu (Google Analytics)
- [ ] Error tracking (Sentry)

### Orta Vadeli (3-6 Ay)
- [ ] Offline-first yaklaşım
- [ ] Sınır kapıları otomatik veri çekme (web scraping)
- [ ] Gümrük kameraları canlı yayın
- [ ] Waze benzeri bildirim sistemi tam entegrasyon
- [ ] Çoklu dil desteği (Türkçe, Almanca, Fransızca)

### Uzun Vadeli (6-12 Ay)
- [ ] AI chatbot (dil desteği, soru-cevap)
- [ ] Ödeme sistemi entegrasyonu
- [ ] Video streaming (Akademi)
- [ ] Sosyal medya entegrasyonu
- [ ] API dokümantasyonu
- [ ] Developer portal

---

## 📞 TEKNİK DESTEK

### Önemli Dosyalar
- **Config:** `config.js`
- **Auth:** `auth.js`
- **Utils:** `utils.js`
- **Database:** `supabase_rls_policies.sql`
- **Health Tourism:** `supabase_health_sample_data.sql`

### Loglama
- Console.log ile debug
- Supabase dashboard'da loglar
- Netlify'da deploy logları
- Service worker logları

### Hata Ayıklama
- Browser DevTools (F12)
- Supabase Dashboard > Logs
- Netlify Functions Logs
- Service Worker DevTools

---

## 📝 EK BİLGİLER

### Domain Bilgileri
- **Aktif Domain:** www.platformavrupa.com
- **Yedek Domain:** www.platformavrupa.eu (henüz kullanılmıyor)
- **Email:** info@platformavrupa.com (Zoho)

### Master Plan (15.01.2026)
1. **Akıllı Sınır Kapıları Sistemi** - Gümrük yoğunluk takibi, kameralar, rota önerileri
2. **Yol Arkadaşım & Emanet** - Bagaj odaklı yolculuk paylaşımı, kargo/emanet eşleştirme
3. **Yol Yardım & SOS** - Topluluk destekli acil yardım, doğrulanmış tamirci/çekici veritabanı
4. **Mobil Uygulama & Waze Özellikleri** - Native app, anlık yol bildirimleri

### Test Dosyaları
- `TEST_RESULTS_YOL_ARKADASI.md` - Yol Arkadaşı modülü test sonuçları
- `YOL_ARKADASI_TEST_OZETI.md` - Yol Arkadaşı test özeti
- `MOBILE_TEST_CHECKLIST.md` - Mobil test checklist

---

**Son Güncelleme:** 2026-02-04  
**Versiyon:** 3.0 Final  
**Durum:** Production Ready ✅  
**Hazırlayan:** AI Assistant (Cursor)  
**Proje Sahibi:** PlatformAvrupa Team

---

## 📌 NOTLAR

Bu dokümantasyon Gemini AI ile paylaşım için hazırlanmıştır. Projenin tüm teknik detaylarını, mimarisini, veritabanı yapısını ve gelecek planlarını içermektedir. Güncellemeler yapıldıkça bu dokümantasyon da güncellenmelidir.
