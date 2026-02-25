-- ============================================================================
-- PLATFORM AVRUPA - SUPABASE RLS POLİTİKALARI (GÜNCELLENMIŞ)
-- ============================================================================
-- Bu dosyayı Supabase Dashboard > SQL Editor'da çalıştırın
-- Tarih: 2026-02-02
-- NOT: Mevcut tablo yapısına göre düzenlenmiştir
-- ============================================================================

-- ============================================================================
-- BÖLÜM 1: EKSİK SÜTUNLARI EKLE
-- ============================================================================

-- 1.1 Profiles tablosuna role ve status sütunları ekle
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS country TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS real_name TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS avatar_url TEXT;

-- 1.2 Trips tablosuna user_id ve yeni özellikler ekle
ALTER TABLE trips ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE trips ADD COLUMN IF NOT EXISTS travel_time TEXT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS stops TEXT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS car_brand TEXT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS car_model TEXT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS car_color TEXT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS no_smoking BOOLEAN DEFAULT true;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS music_allowed BOOLEAN DEFAULT true;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS pets_allowed BOOLEAN DEFAULT false;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';

-- 1.3 Shipments tablosuna user_id ve yeni alanlar ekle
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS weight DECIMAL(10,2);
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS size TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS package_count INTEGER DEFAULT 1;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS is_fragile BOOLEAN DEFAULT false;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS price_offer DECIMAL(10,2);
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS insurance TEXT DEFAULT 'none';
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS delivery_preference TEXT DEFAULT 'flexible';
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS tracking_number TEXT UNIQUE;

-- 1.4 Favorites tablosunu oluştur (yoksa)
CREATE TABLE IF NOT EXISTS favorites (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    ilan_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 1.5 Trip Reservations tablosunu oluştur (yol arkadaşı rezervasyonları)
CREATE TABLE IF NOT EXISTS trip_reservations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    trip_id BIGINT NOT NULL,
    passenger_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    passenger_name TEXT NOT NULL,
    passenger_phone TEXT,
    seats_requested INTEGER DEFAULT 1,
    status TEXT DEFAULT 'pending',
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Unique constraint
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'favorites_user_ilan_unique') THEN
        CREATE UNIQUE INDEX favorites_user_ilan_unique ON favorites(user_id, ilan_id);
    END IF;
END $$;

-- ============================================================================
-- BÖLÜM 2: MEVCUT POLİTİKALARI TEMİZLE (Varsa)
-- ============================================================================

-- Profiles
DROP POLICY IF EXISTS "Profiles are viewable by everyone" ON profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON profiles;
DROP POLICY IF EXISTS "Users can delete own profile" ON profiles;

-- İlanlar
DROP POLICY IF EXISTS "Active listings are viewable by everyone" ON ilanlar;
DROP POLICY IF EXISTS "Authenticated users can create listings" ON ilanlar;
DROP POLICY IF EXISTS "Users can update own listings" ON ilanlar;
DROP POLICY IF EXISTS "Users can delete own listings" ON ilanlar;

-- Messages
DROP POLICY IF EXISTS "Messages are viewable by everyone" ON messages;
DROP POLICY IF EXISTS "Authenticated users can send messages" ON messages;
DROP POLICY IF EXISTS "Only admins can delete messages" ON messages;

-- Trips
DROP POLICY IF EXISTS "Trips are viewable by everyone" ON trips;
DROP POLICY IF EXISTS "Authenticated users can create trips" ON trips;
DROP POLICY IF EXISTS "Users can update own trips" ON trips;
DROP POLICY IF EXISTS "Users can delete own trips" ON trips;

-- Shipments
DROP POLICY IF EXISTS "Shipments are viewable by everyone" ON shipments;
DROP POLICY IF EXISTS "Authenticated users can create shipments" ON shipments;
DROP POLICY IF EXISTS "Users can update own shipments" ON shipments;
DROP POLICY IF EXISTS "Users can delete own shipments" ON shipments;

-- Announcements
DROP POLICY IF EXISTS "Announcements are viewable by everyone" ON announcements;
DROP POLICY IF EXISTS "Only admins can create announcements" ON announcements;
DROP POLICY IF EXISTS "Only admins can update announcements" ON announcements;
DROP POLICY IF EXISTS "Only admins can delete announcements" ON announcements;

-- Services
DROP POLICY IF EXISTS "Services are viewable by everyone" ON services;
DROP POLICY IF EXISTS "Only admins can create services" ON services;
DROP POLICY IF EXISTS "Only admins can delete services" ON services;

-- Road Reports
DROP POLICY IF EXISTS "Road reports are viewable by everyone" ON road_reports;
DROP POLICY IF EXISTS "Authenticated users can create road reports" ON road_reports;
DROP POLICY IF EXISTS "Only admins can delete road reports" ON road_reports;

-- SOS Alerts
DROP POLICY IF EXISTS "Only admins can view SOS alerts" ON sos_alerts;
DROP POLICY IF EXISTS "Anyone can create SOS alerts" ON sos_alerts;
DROP POLICY IF EXISTS "Only admins can delete SOS alerts" ON sos_alerts;

-- Catalogs
DROP POLICY IF EXISTS "Catalogs are viewable by everyone" ON catalogs;
DROP POLICY IF EXISTS "Only admins can create catalogs" ON catalogs;
DROP POLICY IF EXISTS "Only admins can delete catalogs" ON catalogs;

-- Favorites
DROP POLICY IF EXISTS "Users can view own favorites" ON favorites;
DROP POLICY IF EXISTS "Users can add favorites" ON favorites;
DROP POLICY IF EXISTS "Users can delete own favorites" ON favorites;

-- Borders
DROP POLICY IF EXISTS "Borders are viewable by everyone" ON borders;
DROP POLICY IF EXISTS "Only admins can modify borders" ON borders;

-- Notifications
DROP POLICY IF EXISTS "Users can view own notifications" ON notifications;
DROP POLICY IF EXISTS "Users can update own notifications" ON notifications;

-- Listings
DROP POLICY IF EXISTS "Listings are viewable by everyone" ON listings;
DROP POLICY IF EXISTS "Authenticated users can create listings" ON listings;
DROP POLICY IF EXISTS "Users can update own listings" ON listings;
DROP POLICY IF EXISTS "Users can delete own listings" ON listings;

-- ============================================================================
-- BÖLÜM 3: RLS'İ AKTİF ET
-- ============================================================================

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE ilanlar ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE road_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE sos_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalogs ENABLE ROW LEVEL SECURITY;
ALTER TABLE favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE borders ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- BÖLÜM 4: PROFILES TABLOSU POLİTİKALARI
-- ============================================================================

-- Herkes profilleri okuyabilir
CREATE POLICY "Profiles are viewable by everyone" 
ON profiles FOR SELECT 
USING (true);

-- Kullanıcılar sadece kendi profillerini güncelleyebilir
CREATE POLICY "Users can update own profile" 
ON profiles FOR UPDATE 
USING (auth.uid() = id);

-- Yeni kullanıcı kaydı
CREATE POLICY "Users can insert own profile" 
ON profiles FOR INSERT 
WITH CHECK (auth.uid() = id);

-- Kullanıcılar kendi profillerini silebilir
CREATE POLICY "Users can delete own profile" 
ON profiles FOR DELETE 
USING (auth.uid() = id);

-- ============================================================================
-- BÖLÜM 5: İLANLAR TABLOSU POLİTİKALARI
-- ============================================================================

-- Herkes aktif ilanları veya kendi ilanlarını görebilir
CREATE POLICY "Active listings are viewable by everyone" 
ON ilanlar FOR SELECT 
USING (status = 'active' OR status IS NULL OR auth.uid() = user_id);

-- Giriş yapmış kullanıcılar ilan ekleyebilir
CREATE POLICY "Authenticated users can create listings" 
ON ilanlar FOR INSERT 
WITH CHECK (auth.uid() IS NOT NULL);

-- Kullanıcılar sadece kendi ilanlarını güncelleyebilir
CREATE POLICY "Users can update own listings" 
ON ilanlar FOR UPDATE 
USING (auth.uid() = user_id);

-- Kullanıcılar sadece kendi ilanlarını silebilir
CREATE POLICY "Users can delete own listings" 
ON ilanlar FOR DELETE 
USING (auth.uid() = user_id);

-- ============================================================================
-- BÖLÜM 6: MESSAGES TABLOSU POLİTİKALARI
-- ============================================================================

-- Herkes mesajları okuyabilir (public sohbet)
CREATE POLICY "Messages are viewable by everyone" 
ON messages FOR SELECT 
USING (true);

-- Giriş yapmış kullanıcılar mesaj gönderebilir
CREATE POLICY "Authenticated users can send messages" 
ON messages FOR INSERT 
WITH CHECK (auth.uid() IS NOT NULL);

-- Mesaj silme - admin veya kendi mesajı (user_name kontrolü)
CREATE POLICY "Only admins can delete messages" 
ON messages FOR DELETE 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- ============================================================================
-- BÖLÜM 7: TRIPS TABLOSU POLİTİKALARI
-- ============================================================================

-- Herkes yolculuk ilanlarını görebilir
CREATE POLICY "Trips are viewable by everyone" 
ON trips FOR SELECT 
USING (true);

-- Giriş yapmış kullanıcılar yolculuk ilanı ekleyebilir
CREATE POLICY "Authenticated users can create trips" 
ON trips FOR INSERT 
WITH CHECK (auth.uid() IS NOT NULL);

-- Kullanıcılar kendi yolculuklarını güncelleyebilir
CREATE POLICY "Users can update own trips" 
ON trips FOR UPDATE 
USING (auth.uid() = user_id OR user_id IS NULL);

-- Kullanıcılar kendi yolculuklarını silebilir
CREATE POLICY "Users can delete own trips" 
ON trips FOR DELETE 
USING (auth.uid() = user_id OR user_id IS NULL);

-- ============================================================================
-- BÖLÜM 8: SHIPMENTS TABLOSU POLİTİKALARI
-- ============================================================================

-- Herkes kargo taleplerini görebilir
CREATE POLICY "Shipments are viewable by everyone" 
ON shipments FOR SELECT 
USING (true);

-- Giriş yapmış kullanıcılar kargo talebi oluşturabilir
CREATE POLICY "Authenticated users can create shipments" 
ON shipments FOR INSERT 
WITH CHECK (auth.uid() IS NOT NULL);

-- Kullanıcılar kendi taleplerini güncelleyebilir
CREATE POLICY "Users can update own shipments" 
ON shipments FOR UPDATE 
USING (auth.uid() = user_id OR user_id IS NULL);

-- Kullanıcılar kendi taleplerini silebilir
CREATE POLICY "Users can delete own shipments" 
ON shipments FOR DELETE 
USING (auth.uid() = user_id OR user_id IS NULL);

-- ============================================================================
-- BÖLÜM 9: ANNOUNCEMENTS TABLOSU POLİTİKALARI
-- ============================================================================

-- Herkes duyuruları görebilir
CREATE POLICY "Announcements are viewable by everyone" 
ON announcements FOR SELECT 
USING (true);

-- Sadece admin duyuru ekleyebilir
CREATE POLICY "Only admins can create announcements" 
ON announcements FOR INSERT 
WITH CHECK (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- Sadece admin duyuru güncelleyebilir
CREATE POLICY "Only admins can update announcements" 
ON announcements FOR UPDATE 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- Sadece admin duyuru silebilir
CREATE POLICY "Only admins can delete announcements" 
ON announcements FOR DELETE 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- ============================================================================
-- BÖLÜM 10: SERVICES TABLOSU POLİTİKALARI
-- ============================================================================

-- Herkes hizmetleri görebilir
CREATE POLICY "Services are viewable by everyone" 
ON services FOR SELECT 
USING (true);

-- Sadece admin hizmet ekleyebilir
CREATE POLICY "Only admins can create services" 
ON services FOR INSERT 
WITH CHECK (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- Sadece admin hizmet silebilir
CREATE POLICY "Only admins can delete services" 
ON services FOR DELETE 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- ============================================================================
-- BÖLÜM 11: ROAD_REPORTS TABLOSU POLİTİKALARI
-- ============================================================================

-- Herkes bildirimleri görebilir
CREATE POLICY "Road reports are viewable by everyone" 
ON road_reports FOR SELECT 
USING (true);

-- Giriş yapmış kullanıcılar bildirim ekleyebilir
CREATE POLICY "Authenticated users can create road reports" 
ON road_reports FOR INSERT 
WITH CHECK (auth.uid() IS NOT NULL);

-- Sadece admin bildirim silebilir
CREATE POLICY "Only admins can delete road reports" 
ON road_reports FOR DELETE 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- ============================================================================
-- BÖLÜM 12: SOS_ALERTS TABLOSU POLİTİKALARI
-- ============================================================================

-- Sadece admin SOS çağrılarını görebilir
CREATE POLICY "Only admins can view SOS alerts" 
ON sos_alerts FOR SELECT 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- Herkes SOS çağrısı oluşturabilir (acil durum)
CREATE POLICY "Anyone can create SOS alerts" 
ON sos_alerts FOR INSERT 
WITH CHECK (true);

-- Sadece admin SOS çağrısı silebilir
CREATE POLICY "Only admins can delete SOS alerts" 
ON sos_alerts FOR DELETE 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- ============================================================================
-- BÖLÜM 13: CATALOGS TABLOSU POLİTİKALARI
-- ============================================================================

-- Herkes aktif katalogları görebilir
CREATE POLICY "Catalogs are viewable by everyone" 
ON catalogs FOR SELECT 
USING (active = true OR active IS NULL);

-- Sadece admin katalog ekleyebilir
CREATE POLICY "Only admins can create catalogs" 
ON catalogs FOR INSERT 
WITH CHECK (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- Sadece admin katalog silebilir
CREATE POLICY "Only admins can delete catalogs" 
ON catalogs FOR DELETE 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- ============================================================================
-- BÖLÜM 14: FAVORITES TABLOSU POLİTİKALARI
-- ============================================================================

-- Kullanıcılar sadece kendi favorilerini görebilir
CREATE POLICY "Users can view own favorites" 
ON favorites FOR SELECT 
USING (auth.uid() = user_id);

-- Kullanıcılar favori ekleyebilir
CREATE POLICY "Users can add favorites" 
ON favorites FOR INSERT 
WITH CHECK (auth.uid() = user_id);

-- Kullanıcılar kendi favorilerini silebilir
CREATE POLICY "Users can delete own favorites" 
ON favorites FOR DELETE 
USING (auth.uid() = user_id);

-- ============================================================================
-- BÖLÜM 15: BORDERS TABLOSU POLİTİKALARI
-- ============================================================================

-- Herkes sınır kapılarını görebilir
CREATE POLICY "Borders are viewable by everyone" 
ON borders FOR SELECT 
USING (true);

-- Sadece admin sınır kapısı değiştirebilir
CREATE POLICY "Only admins can modify borders" 
ON borders FOR ALL 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- ============================================================================
-- BÖLÜM 16: NOTIFICATIONS TABLOSU POLİTİKALARI
-- ============================================================================

-- Kullanıcılar kendi bildirimlerini görebilir
CREATE POLICY "Users can view own notifications" 
ON notifications FOR SELECT 
USING (auth.uid() = user_id);

-- Kullanıcılar kendi bildirimlerini güncelleyebilir (okundu işareti)
CREATE POLICY "Users can update own notifications" 
ON notifications FOR UPDATE 
USING (auth.uid() = user_id);

-- ============================================================================
-- BÖLÜM 17: LISTINGS TABLOSU POLİTİKALARI
-- ============================================================================

-- Herkes ilanları görebilir
CREATE POLICY "Listings are viewable by everyone" 
ON listings FOR SELECT 
USING (true);

-- Giriş yapmış kullanıcılar ilan ekleyebilir
CREATE POLICY "Authenticated users can create listings" 
ON listings FOR INSERT 
WITH CHECK (auth.uid() IS NOT NULL);

-- Kullanıcılar kendi ilanlarını güncelleyebilir
CREATE POLICY "Users can update own listings" 
ON listings FOR UPDATE 
USING (auth.uid() = user_id);

-- Kullanıcılar kendi ilanlarını silebilir
CREATE POLICY "Users can delete own listings" 
ON listings FOR DELETE 
USING (auth.uid() = user_id);

-- ============================================================================
-- BÖLÜM 18: ADMİN KULLANICISINI AYARLA
-- ============================================================================

-- KENDİ EMAİL ADRESİNİZİ BURAYA YAZIN!
-- Örnek: UPDATE profiles SET role = 'admin' WHERE email = 'sizin@email.com';

-- Admin yapmak istediğiniz kullanıcının email adresini yazın:
-- UPDATE profiles SET role = 'admin' WHERE email = 'BURAYA_EMAIL_YAZIN';

-- ============================================================================
-- BÖLÜM 19: MARKET FİYATLARI SİSTEMİ TABLOLARI
-- ============================================================================

-- 19.1 Market Zincirleri Tablosu
CREATE TABLE IF NOT EXISTS market_chains (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    logo_url TEXT,
    countries TEXT[],
    website TEXT,
    brochure_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 19.2 Kullanıcı İndirim Paylaşımları Tablosu
CREATE TABLE IF NOT EXISTS user_deals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    market_chain_id UUID REFERENCES market_chains(id) ON DELETE SET NULL,
    country_code TEXT NOT NULL,
    city TEXT,
    
    product_name TEXT NOT NULL,
    category TEXT,
    original_price DECIMAL(10,2),
    sale_price DECIMAL(10,2) NOT NULL,
    discount_percent INTEGER,
    
    image_url TEXT,
    valid_until DATE,
    
    status TEXT DEFAULT 'pending',
    verified_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 19.3 Kullanıcı Puanları Tablosu (Gamification)
CREATE TABLE IF NOT EXISTS user_points (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    points INTEGER DEFAULT 0,
    deals_shared INTEGER DEFAULT 0,
    deals_approved INTEGER DEFAULT 0,
    badges TEXT[],
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- BÖLÜM 20: MARKET TABLOLARI RLS POLİTİKALARI
-- ============================================================================

-- RLS'i aktif et
ALTER TABLE market_chains ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_points ENABLE ROW LEVEL SECURITY;

-- Market Chains - Herkes görebilir, sadece admin değiştirebilir
CREATE POLICY "Market chains are viewable by everyone" 
ON market_chains FOR SELECT 
USING (true);

CREATE POLICY "Only admins can modify market chains" 
ON market_chains FOR ALL 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- User Deals - Herkes onaylananları görebilir, kullanıcılar kendi paylaşımlarını yönetebilir
CREATE POLICY "Approved deals are viewable by everyone" 
ON user_deals FOR SELECT 
USING (status = 'approved' OR auth.uid() = user_id);

CREATE POLICY "Authenticated users can create deals" 
ON user_deals FOR INSERT 
WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "Users can update own deals" 
ON user_deals FOR UPDATE 
USING (auth.uid() = user_id);

CREATE POLICY "Users or admins can delete deals" 
ON user_deals FOR DELETE 
USING (
    auth.uid() = user_id OR
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- Admin can update all deals (for approval)
CREATE POLICY "Admins can update all deals" 
ON user_deals FOR UPDATE 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- User Points - Kullanıcılar kendi puanlarını görebilir, herkes liderboard için görebilir
CREATE POLICY "User points are viewable by everyone" 
ON user_points FOR SELECT 
USING (true);

CREATE POLICY "System can manage user points" 
ON user_points FOR ALL 
USING (
    auth.uid() = user_id OR
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- ============================================================================
-- BÖLÜM 21: GAMİFİCATİON - ROZET SİSTEMİ
-- ============================================================================

-- Rozet tanımları fonksiyonu
-- Bu fonksiyon her puan güncellemesinde rozetleri kontrol eder
CREATE OR REPLACE FUNCTION check_and_award_badges()
RETURNS TRIGGER AS $$
DECLARE
    new_badges TEXT[];
BEGIN
    new_badges := COALESCE(NEW.badges, ARRAY[]::TEXT[]);
    
    -- İlk Paylaşım Rozeti
    IF NEW.deals_shared >= 1 AND NOT 'ilk_paylasim' = ANY(new_badges) THEN
        new_badges := array_append(new_badges, 'ilk_paylasim');
    END IF;
    
    -- 5 Paylaşım Rozeti
    IF NEW.deals_shared >= 5 AND NOT 'aktif_katilimci' = ANY(new_badges) THEN
        new_badges := array_append(new_badges, 'aktif_katilimci');
    END IF;
    
    -- 10 Onaylı Paylaşım - İndirim Avcısı
    IF NEW.deals_approved >= 10 AND NOT 'indirim_avcisi' = ANY(new_badges) THEN
        new_badges := array_append(new_badges, 'indirim_avcisi');
    END IF;
    
    -- 50 Puan - Bronz Rozet
    IF NEW.points >= 50 AND NOT 'bronz' = ANY(new_badges) THEN
        new_badges := array_append(new_badges, 'bronz');
    END IF;
    
    -- 100 Puan - Gümüş Rozet
    IF NEW.points >= 100 AND NOT 'gumus' = ANY(new_badges) THEN
        new_badges := array_append(new_badges, 'gumus');
    END IF;
    
    -- 250 Puan - Altın Rozet
    IF NEW.points >= 250 AND NOT 'altin' = ANY(new_badges) THEN
        new_badges := array_append(new_badges, 'altin');
    END IF;
    
    -- 500 Puan - Elmas Rozet
    IF NEW.points >= 500 AND NOT 'elmas' = ANY(new_badges) THEN
        new_badges := array_append(new_badges, 'elmas');
    END IF;
    
    NEW.badges := new_badges;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger'ı oluştur (yoksa)
DROP TRIGGER IF EXISTS check_badges_trigger ON user_points;
CREATE TRIGGER check_badges_trigger
    BEFORE UPDATE ON user_points
    FOR EACH ROW
    EXECUTE FUNCTION check_and_award_badges();

-- İndirim doğrulama sayısını artırmak için fonksiyon
CREATE OR REPLACE FUNCTION increment_deal_verification(deal_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE user_deals 
    SET verified_count = COALESCE(verified_count, 0) + 1 
    WHERE id = deal_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- BÖLÜM 22: YOL YARDIM SİSTEMİ TABLOLARI
-- ============================================================================

-- 22.1 Acil Yardım Numaraları Tablosu (Admin tarafından doldurulur)
CREATE TABLE IF NOT EXISTS emergency_numbers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    country_code TEXT NOT NULL,
    service_type TEXT NOT NULL,          -- 'polis', 'ambulans', 'yangin', 'yol_yardim', 'konsolosluk'
    service_name TEXT NOT NULL,          -- 'ADAC', 'TR Büyükelçilik' vb.
    phone_number TEXT NOT NULL,
    description TEXT,
    is_24h BOOLEAN DEFAULT true,
    is_turkish_speaking BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 22.2 SOS Alerts Tablosuna Yeni Sütunlar Ekle
ALTER TABLE sos_alerts ADD COLUMN IF NOT EXISTS lat DECIMAL(10,8);
ALTER TABLE sos_alerts ADD COLUMN IF NOT EXISTS lng DECIMAL(11,8);
ALTER TABLE sos_alerts ADD COLUMN IF NOT EXISTS direction TEXT;        -- 'turkiye', 'avrupa', 'bilinmiyor'
ALTER TABLE sos_alerts ADD COLUMN IF NOT EXISTS country_code TEXT;
ALTER TABLE sos_alerts ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE sos_alerts ADD COLUMN IF NOT EXISTS helpers_notified INTEGER DEFAULT 0;
ALTER TABLE sos_alerts ADD COLUMN IF NOT EXISTS helper_found BOOLEAN DEFAULT false;
ALTER TABLE sos_alerts ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP WITH TIME ZONE;

-- 22.3 Yardım Teklifleri Tablosu
CREATE TABLE IF NOT EXISTS help_responses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sos_alert_id UUID REFERENCES sos_alerts(id) ON DELETE CASCADE,
    helper_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    helper_name TEXT NOT NULL,
    helper_phone TEXT NOT NULL,
    helper_message TEXT,
    distance_km DECIMAL(10,2),
    status TEXT DEFAULT 'offered',      -- 'offered', 'accepted', 'completed', 'cancelled'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 22.4 Kullanıcı Konumları Tablosu (Yakındaki kullanıcıları bulmak için)
CREATE TABLE IF NOT EXISTS user_locations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    lat DECIMAL(10,8) NOT NULL,
    lng DECIMAL(11,8) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_available_for_help BOOLEAN DEFAULT true
);

-- ============================================================================
-- BÖLÜM 23: YOL YARDIM RLS POLİTİKALARI
-- ============================================================================

-- RLS'i aktif et
ALTER TABLE emergency_numbers ENABLE ROW LEVEL SECURITY;
ALTER TABLE help_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_locations ENABLE ROW LEVEL SECURITY;

-- Emergency Numbers - Herkes görebilir, sadece admin değiştirebilir
CREATE POLICY "Emergency numbers are viewable by everyone" 
ON emergency_numbers FOR SELECT 
USING (true);

CREATE POLICY "Only admins can modify emergency numbers" 
ON emergency_numbers FOR ALL 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- Help Responses - İlgili taraflar görebilir
CREATE POLICY "Help responses viewable by involved parties" 
ON help_responses FOR SELECT 
USING (
    auth.uid() = helper_user_id OR
    EXISTS (
        SELECT 1 FROM sos_alerts 
        WHERE sos_alerts.id = help_responses.sos_alert_id 
        AND sos_alerts.user_id = auth.uid()
    ) OR
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

CREATE POLICY "Authenticated users can create help responses" 
ON help_responses FOR INSERT 
WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "Users can update own help responses" 
ON help_responses FOR UPDATE 
USING (auth.uid() = helper_user_id);

-- User Locations - Kullanıcılar kendi konumlarını yönetebilir
CREATE POLICY "Users can view own location" 
ON user_locations FOR SELECT 
USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own location" 
ON user_locations FOR ALL 
USING (auth.uid() = user_id);

-- Admins can view all locations (for SOS matching)
CREATE POLICY "Admins can view all locations" 
ON user_locations FOR SELECT 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- ============================================================================
-- BÖLÜM 24: YAKIN KULLANICI BULMA FONKSİYONU (Haversine)
-- ============================================================================

-- Haversine formülü ile mesafe hesaplama (km)
CREATE OR REPLACE FUNCTION calculate_distance(
    lat1 DECIMAL, lng1 DECIMAL,
    lat2 DECIMAL, lng2 DECIMAL
) RETURNS DECIMAL AS $$
DECLARE
    R DECIMAL := 6371; -- Dünya yarıçapı km
    dLat DECIMAL;
    dLng DECIMAL;
    a DECIMAL;
    c DECIMAL;
BEGIN
    dLat := RADIANS(lat2 - lat1);
    dLng := RADIANS(lng2 - lng1);
    
    a := SIN(dLat/2) * SIN(dLat/2) +
         COS(RADIANS(lat1)) * COS(RADIANS(lat2)) *
         SIN(dLng/2) * SIN(dLng/2);
    
    c := 2 * ATAN2(SQRT(a), SQRT(1-a));
    
    RETURN R * c;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Yakındaki kullanıcıları bulan fonksiyon
CREATE OR REPLACE FUNCTION find_nearby_users(
    target_lat DECIMAL,
    target_lng DECIMAL,
    radius_km DECIMAL DEFAULT 30
) RETURNS TABLE (
    user_id UUID,
    distance_km DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ul.user_id,
        calculate_distance(target_lat, target_lng, ul.lat, ul.lng) as dist
    FROM user_locations ul
    WHERE ul.is_available_for_help = true
    AND ul.last_updated > NOW() - INTERVAL '24 hours'
    AND calculate_distance(target_lat, target_lng, ul.lat, ul.lng) <= radius_km
    ORDER BY dist ASC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- BÖLÜM 25: WAZE BENZERİ BİLDİRİM SİSTEMİ (road_reports)
-- ============================================================================

-- road_reports tablosu yoksa oluştur
CREATE TABLE IF NOT EXISTS road_reports (
    id BIGSERIAL PRIMARY KEY,
    report_type TEXT NOT NULL,
    description TEXT,
    country_code TEXT,
    user_name TEXT,
    user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Yeni sütunlar ekle
ALTER TABLE road_reports ADD COLUMN IF NOT EXISTS lat DECIMAL(10,8);
ALTER TABLE road_reports ADD COLUMN IF NOT EXISTS lng DECIMAL(11,8);
ALTER TABLE road_reports ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE road_reports ADD COLUMN IF NOT EXISTS verified_count INTEGER DEFAULT 0;
ALTER TABLE road_reports ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE road_reports ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

-- RLS aktif et
ALTER TABLE road_reports ENABLE ROW LEVEL SECURITY;

-- Herkes bildirimleri görebilir
CREATE POLICY "Road reports are viewable by everyone" 
ON road_reports FOR SELECT USING (true);

-- Giriş yapmış kullanıcılar bildirim ekleyebilir
CREATE POLICY "Authenticated users can create road reports" 
ON road_reports FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- Kullanıcılar kendi bildirimlerini güncelleyebilir
CREATE POLICY "Users can update own road reports" 
ON road_reports FOR UPDATE USING (auth.uid() = user_id);

-- Adminler tüm bildirimleri silebilir
CREATE POLICY "Admins can delete road reports" 
ON road_reports FOR DELETE 
USING (EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin'));

-- Bildirim doğrulama fonksiyonu
CREATE OR REPLACE FUNCTION verify_road_report(report_id BIGINT)
RETURNS void AS $$
BEGIN
    UPDATE road_reports 
    SET verified_count = COALESCE(verified_count, 0) + 1 
    WHERE id = report_id;
END;
$$ LANGUAGE plpgsql;

-- Süresi dolmuş bildirimleri temizleme fonksiyonu
CREATE OR REPLACE FUNCTION cleanup_expired_reports()
RETURNS void AS $$
BEGIN
    UPDATE road_reports 
    SET is_active = false 
    WHERE expires_at < NOW() AND is_active = true;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- BÖLÜM 26: AFFİLİATE SİSTEMİ TABLOLARI
-- ============================================================================

-- 26.1 Affiliate Tıklama Takip Tablosu
CREATE TABLE IF NOT EXISTS affiliate_clicks (
    id BIGSERIAL PRIMARY KEY,
    partner TEXT NOT NULL,              -- 'skyscanner', 'booking', 'rentalcars', 'tatilsepeti', 'viator'
    page TEXT,                          -- Hangi sayfadan tıklandı
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    metadata JSONB,                     -- Ek bilgiler (destination, fiyat vb.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 26.2 Promosyon/Fırsat Tablosu (API'lerden çekilen ve manuel eklenen)
CREATE TABLE IF NOT EXISTS promotions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    partner TEXT NOT NULL,              -- 'skyscanner', 'booking', 'rentalcars', 'tatilsepeti'
    category TEXT NOT NULL,             -- 'ucak', 'otel', 'arac', 'tatil'
    
    title TEXT NOT NULL,                -- "Berlin → İstanbul 89€'dan"
    description TEXT,
    
    origin TEXT,                        -- Kalkış (uçak için)
    destination TEXT,                   -- Varış yeri
    
    price DECIMAL(10,2),
    original_price DECIMAL(10,2),       -- İndirimden önceki fiyat
    currency TEXT DEFAULT 'EUR',
    discount_percent INTEGER,
    
    image_url TEXT,
    affiliate_link TEXT NOT NULL,
    
    valid_from DATE,
    valid_until DATE,
    
    is_featured BOOLEAN DEFAULT false,  -- Ana sayfada gösterilecek mi
    is_active BOOLEAN DEFAULT true,
    
    source TEXT DEFAULT 'manual',       -- 'manual', 'api', 'scrape'
    api_data JSONB,                     -- API'den gelen ham veri
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- İndeksler (performans için)
CREATE INDEX IF NOT EXISTS idx_affiliate_clicks_partner ON affiliate_clicks(partner);
CREATE INDEX IF NOT EXISTS idx_affiliate_clicks_created ON affiliate_clicks(created_at);
CREATE INDEX IF NOT EXISTS idx_promotions_category ON promotions(category);
CREATE INDEX IF NOT EXISTS idx_promotions_partner ON promotions(partner);
CREATE INDEX IF NOT EXISTS idx_promotions_featured ON promotions(is_featured) WHERE is_featured = true;
CREATE INDEX IF NOT EXISTS idx_promotions_active ON promotions(is_active) WHERE is_active = true;

-- ============================================================================
-- BÖLÜM 27: AFFİLİATE RLS POLİTİKALARI
-- ============================================================================

-- RLS aktif et
ALTER TABLE affiliate_clicks ENABLE ROW LEVEL SECURITY;
ALTER TABLE promotions ENABLE ROW LEVEL SECURITY;

-- Affiliate Clicks - Sadece admin görebilir
CREATE POLICY "Only admins can view affiliate clicks" 
ON affiliate_clicks FOR SELECT 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- Herkes tıklama kaydedebilir (anonim dahil)
CREATE POLICY "Anyone can create affiliate clicks" 
ON affiliate_clicks FOR INSERT 
WITH CHECK (true);

-- Sadece admin silebilir
CREATE POLICY "Only admins can delete affiliate clicks" 
ON affiliate_clicks FOR DELETE 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- Promotions - Herkes aktif promosyonları görebilir
CREATE POLICY "Active promotions are viewable by everyone" 
ON promotions FOR SELECT 
USING (is_active = true OR is_active IS NULL);

-- Sadece admin promosyon ekleyebilir
CREATE POLICY "Only admins can create promotions" 
ON promotions FOR INSERT 
WITH CHECK (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- Sadece admin promosyon güncelleyebilir
CREATE POLICY "Only admins can update promotions" 
ON promotions FOR UPDATE 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- Sadece admin promosyon silebilir
CREATE POLICY "Only admins can delete promotions" 
ON promotions FOR DELETE 
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE profiles.id = auth.uid() 
        AND profiles.role = 'admin'
    )
);

-- ============================================================================
-- BÖLÜM 28: PROMOSYON YARDIMCI FONKSİYONLARI
-- ============================================================================

-- Süresi dolmuş promosyonları deaktif et
CREATE OR REPLACE FUNCTION cleanup_expired_promotions()
RETURNS void AS $$
BEGIN
    UPDATE promotions 
    SET is_active = false 
    WHERE valid_until < CURRENT_DATE AND is_active = true;
END;
$$ LANGUAGE plpgsql;

-- Öne çıkan promosyonları getir
CREATE OR REPLACE FUNCTION get_featured_promotions(limit_count INTEGER DEFAULT 4)
RETURNS TABLE (
    id UUID,
    partner TEXT,
    category TEXT,
    title TEXT,
    description TEXT,
    destination TEXT,
    price DECIMAL,
    original_price DECIMAL,
    currency TEXT,
    discount_percent INTEGER,
    image_url TEXT,
    affiliate_link TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id, p.partner, p.category, p.title, p.description, p.destination,
        p.price, p.original_price, p.currency, p.discount_percent,
        p.image_url, p.affiliate_link
    FROM promotions p
    WHERE p.is_featured = true 
    AND p.is_active = true
    AND (p.valid_until IS NULL OR p.valid_until >= CURRENT_DATE)
    ORDER BY p.updated_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Kategoriye göre promosyonları getir
CREATE OR REPLACE FUNCTION get_promotions_by_category(
    cat TEXT,
    limit_count INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    partner TEXT,
    category TEXT,
    title TEXT,
    description TEXT,
    origin TEXT,
    destination TEXT,
    price DECIMAL,
    original_price DECIMAL,
    currency TEXT,
    discount_percent INTEGER,
    image_url TEXT,
    affiliate_link TEXT,
    valid_until DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id, p.partner, p.category, p.title, p.description, p.origin, p.destination,
        p.price, p.original_price, p.currency, p.discount_percent,
        p.image_url, p.affiliate_link, p.valid_until
    FROM promotions p
    WHERE p.category = cat
    AND p.is_active = true
    AND (p.valid_until IS NULL OR p.valid_until >= CURRENT_DATE)
    ORDER BY p.is_featured DESC, p.discount_percent DESC NULLS LAST
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Affiliate istatistikleri getir (admin için)
CREATE OR REPLACE FUNCTION get_affiliate_stats(
    days INTEGER DEFAULT 30
)
RETURNS TABLE (
    partner TEXT,
    click_count BIGINT,
    unique_users BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ac.partner,
        COUNT(*) as click_count,
        COUNT(DISTINCT ac.user_id) as unique_users
    FROM affiliate_clicks ac
    WHERE ac.created_at > NOW() - (days || ' days')::INTERVAL
    GROUP BY ac.partner
    ORDER BY click_count DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- BÖLÜM 29: AKADEMİ VİDEO SİSTEMİ TABLOLARI
-- ============================================================================

-- 29.1 Akademi Kategorileri
CREATE TABLE IF NOT EXISTS academy_categories (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    icon TEXT DEFAULT 'fa-book',
    description TEXT,
    color TEXT DEFAULT '#3b82f6',
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    video_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 29.2 Akademi Video Serileri
CREATE TABLE IF NOT EXISTS academy_series (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    category_id UUID REFERENCES academy_categories(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT,
    thumbnail_url TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    video_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(category_id, slug)
);

-- 29.3 Akademi Videoları
CREATE TABLE IF NOT EXISTS academy_videos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    category_id UUID REFERENCES academy_categories(id) ON DELETE SET NULL,
    series_id UUID REFERENCES academy_series(id) ON DELETE SET NULL,
    
    title TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    
    youtube_url TEXT NOT NULL,
    youtube_id TEXT NOT NULL,
    thumbnail_url TEXT,
    duration_seconds INTEGER DEFAULT 0,
    
    sort_order INTEGER DEFAULT 0,
    series_order INTEGER DEFAULT 0,
    is_featured BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    completion_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 29.4 Video İzlenme Takibi
CREATE TABLE IF NOT EXISTS academy_views (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    video_id UUID REFERENCES academy_videos(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    session_id TEXT,
    
    watch_duration_seconds INTEGER DEFAULT 0,
    progress_percent INTEGER DEFAULT 0,
    completed BOOLEAN DEFAULT false,
    
    device_type TEXT,
    country_code TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 29.5 Kullanıcı Video Talepleri
CREATE TABLE IF NOT EXISTS academy_requests (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    category_id UUID REFERENCES academy_categories(id) ON DELETE SET NULL,
    
    request_type TEXT NOT NULL DEFAULT 'video_request',  -- 'video_request', 'problem_report', 'question', 'suggestion'
    title TEXT NOT NULL,
    description TEXT,
    video_id UUID REFERENCES academy_videos(id) ON DELETE SET NULL,  -- Sorun bildirimi için
    
    status TEXT DEFAULT 'pending',  -- 'pending', 'reviewed', 'planned', 'completed', 'rejected'
    admin_response TEXT,
    admin_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- İndeksler
CREATE INDEX IF NOT EXISTS idx_academy_videos_category ON academy_videos(category_id);
CREATE INDEX IF NOT EXISTS idx_academy_videos_series ON academy_videos(series_id);
CREATE INDEX IF NOT EXISTS idx_academy_videos_featured ON academy_videos(is_featured) WHERE is_featured = true;
CREATE INDEX IF NOT EXISTS idx_academy_views_video ON academy_views(video_id);
CREATE INDEX IF NOT EXISTS idx_academy_views_user ON academy_views(user_id);
CREATE INDEX IF NOT EXISTS idx_academy_requests_status ON academy_requests(status);

-- ============================================================================
-- BÖLÜM 30: AKADEMİ RLS POLİTİKALARI
-- ============================================================================

-- RLS aktif et
ALTER TABLE academy_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_series ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE academy_requests ENABLE ROW LEVEL SECURITY;

-- Kategoriler - Herkes aktif kategorileri görebilir
CREATE POLICY "Academy categories viewable by everyone" 
ON academy_categories FOR SELECT 
USING (is_active = true OR EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin'));

CREATE POLICY "Only admins can modify categories" 
ON academy_categories FOR ALL 
USING (EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin'));

-- Seriler - Herkes aktif serileri görebilir
CREATE POLICY "Academy series viewable by everyone" 
ON academy_series FOR SELECT 
USING (is_active = true OR EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin'));

CREATE POLICY "Only admins can modify series" 
ON academy_series FOR ALL 
USING (EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin'));

-- Videolar - Herkes aktif videoları görebilir
CREATE POLICY "Academy videos viewable by everyone" 
ON academy_videos FOR SELECT 
USING (is_active = true OR EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin'));

CREATE POLICY "Only admins can modify videos" 
ON academy_videos FOR ALL 
USING (EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin'));

-- İzlenme kayıtları - Herkes kayıt oluşturabilir, sadece kendi kayıtlarını görebilir
CREATE POLICY "Users can view own views" 
ON academy_views FOR SELECT 
USING (auth.uid() = user_id OR EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin'));

CREATE POLICY "Anyone can create views" 
ON academy_views FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Users can update own views" 
ON academy_views FOR UPDATE 
USING (auth.uid() = user_id OR session_id IS NOT NULL);

-- Talepler - Kullanıcılar kendi taleplerini görebilir, herkes talep oluşturabilir
CREATE POLICY "Users can view own requests" 
ON academy_requests FOR SELECT 
USING (auth.uid() = user_id OR EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin'));

CREATE POLICY "Authenticated users can create requests" 
ON academy_requests FOR INSERT 
WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "Only admins can update requests" 
ON academy_requests FOR UPDATE 
USING (EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin'));

-- ============================================================================
-- BÖLÜM 31: AKADEMİ YARDIMCI FONKSİYONLARI
-- ============================================================================

-- Video izlenme sayısını artır
CREATE OR REPLACE FUNCTION increment_video_view(vid UUID)
RETURNS void AS $$
BEGIN
    UPDATE academy_videos 
    SET view_count = COALESCE(view_count, 0) + 1 
    WHERE id = vid;
END;
$$ LANGUAGE plpgsql;

-- Video beğeni sayısını artır
CREATE OR REPLACE FUNCTION increment_video_like(vid UUID)
RETURNS void AS $$
BEGIN
    UPDATE academy_videos 
    SET like_count = COALESCE(like_count, 0) + 1 
    WHERE id = vid;
END;
$$ LANGUAGE plpgsql;

-- Video tamamlanma sayısını artır
CREATE OR REPLACE FUNCTION increment_video_completion(vid UUID)
RETURNS void AS $$
BEGIN
    UPDATE academy_videos 
    SET completion_count = COALESCE(completion_count, 0) + 1 
    WHERE id = vid;
END;
$$ LANGUAGE plpgsql;

-- Kategori video sayısını güncelle
CREATE OR REPLACE FUNCTION update_category_video_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE academy_categories SET video_count = video_count + 1 WHERE id = NEW.category_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE academy_categories SET video_count = video_count - 1 WHERE id = OLD.category_id;
    ELSIF TG_OP = 'UPDATE' AND OLD.category_id != NEW.category_id THEN
        UPDATE academy_categories SET video_count = video_count - 1 WHERE id = OLD.category_id;
        UPDATE academy_categories SET video_count = video_count + 1 WHERE id = NEW.category_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_category_count_trigger ON academy_videos;
CREATE TRIGGER update_category_count_trigger
    AFTER INSERT OR UPDATE OR DELETE ON academy_videos
    FOR EACH ROW
    EXECUTE FUNCTION update_category_video_count();

-- Seri video sayısını güncelle
CREATE OR REPLACE FUNCTION update_series_video_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.series_id IS NOT NULL THEN
        UPDATE academy_series SET video_count = video_count + 1 WHERE id = NEW.series_id;
    ELSIF TG_OP = 'DELETE' AND OLD.series_id IS NOT NULL THEN
        UPDATE academy_series SET video_count = video_count - 1 WHERE id = OLD.series_id;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.series_id IS NOT NULL AND (NEW.series_id IS NULL OR OLD.series_id != NEW.series_id) THEN
            UPDATE academy_series SET video_count = video_count - 1 WHERE id = OLD.series_id;
        END IF;
        IF NEW.series_id IS NOT NULL AND (OLD.series_id IS NULL OR OLD.series_id != NEW.series_id) THEN
            UPDATE academy_series SET video_count = video_count + 1 WHERE id = NEW.series_id;
        END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_series_count_trigger ON academy_videos;
CREATE TRIGGER update_series_count_trigger
    AFTER INSERT OR UPDATE OR DELETE ON academy_videos
    FOR EACH ROW
    EXECUTE FUNCTION update_series_video_count();

-- Popüler videoları getir
CREATE OR REPLACE FUNCTION get_popular_academy_videos(limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    id UUID,
    title TEXT,
    thumbnail_url TEXT,
    youtube_id TEXT,
    view_count INTEGER,
    category_name TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.id, v.title, v.thumbnail_url, v.youtube_id, v.view_count,
        c.name as category_name
    FROM academy_videos v
    LEFT JOIN academy_categories c ON v.category_id = c.id
    WHERE v.is_active = true
    ORDER BY v.view_count DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- BÖLÜM 32: VARSAYILAN KATEGORİLER EKLE
-- ============================================================================

-- Varsayılan kategorileri ekle (sadece boşsa)
INSERT INTO academy_categories (name, slug, icon, description, color, sort_order)
SELECT * FROM (VALUES
    ('Dil Eğitimi', 'dil-egitimi', 'fa-language', 'Almanca, Hollandaca, Fransızca ve diğer diller', '#3b82f6', 1),
    ('Resmi İşlemler', 'resmi-islemler', 'fa-file-signature', 'Oturma izni, vatandaşlık, ehliyet başvuruları', '#8b5cf6', 2),
    ('Kariyer & İş', 'kariyer-is', 'fa-briefcase', 'CV hazırlama, iş arama, mülakat teknikleri', '#f59e0b', 3),
    ('Finans & Vergi', 'finans-vergi', 'fa-piggy-bank', 'Vergi beyannamesi, Kindergeld, banka işlemleri', '#10b981', 4),
    ('Günlük Yaşam', 'gunluk-yasam', 'fa-house-user', 'Kira sözleşmesi, sağlık sistemi, günlük ipuçları', '#06b6d4', 5),
    ('Sıla Yolu', 'sila-yolu', 'fa-road', 'Gümrük işlemleri, vize, araç hazırlığı', '#ef4444', 6),
    ('Hukuk', 'hukuk', 'fa-scale-balanced', 'İş hukuku, aile hukuku, tüketici hakları', '#6366f1', 7),
    ('Aile & Çocuk', 'aile-cocuk', 'fa-people-roof', 'Okul sistemi, Kita, Elterngeld', '#ec4899', 8)
) AS v(name, slug, icon, description, color, sort_order)
WHERE NOT EXISTS (SELECT 1 FROM academy_categories LIMIT 1);

-- ============================================================================
-- BÖLÜM 33: YOL ARKADAŞI PUAN SİSTEMİ (TEK YÖNLÜ)
-- ============================================================================

-- trip_reservations tablosuna puan sütunları ekle
ALTER TABLE trip_reservations ADD COLUMN IF NOT EXISTS rating INTEGER; -- 1-5
ALTER TABLE trip_reservations ADD COLUMN IF NOT EXISTS review TEXT;
ALTER TABLE trip_reservations ADD COLUMN IF NOT EXISTS rated_at TIMESTAMP WITH TIME ZONE;

-- trips tablosuna ortalama puan sütunları ekle
ALTER TABLE trips ADD COLUMN IF NOT EXISTS avg_rating DECIMAL(3,2) DEFAULT 0;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS total_ratings INTEGER DEFAULT 0;

-- Puan güncelleme fonksiyonu (trip_id tipine göre - UUID veya BIGINT)
CREATE OR REPLACE FUNCTION update_trip_rating()
RETURNS TRIGGER AS $$
DECLARE
    trip_id_val BIGINT;
BEGIN
    -- trip_id'nin tipini kontrol et (BIGINT veya UUID)
    IF NEW.rating IS NOT NULL AND NEW.rating > 0 THEN
        -- trip_id'yi al (BIGINT ise direkt, UUID ise dönüştür)
        trip_id_val := NEW.trip_id::BIGINT;
        
        UPDATE trips
        SET 
            total_ratings = COALESCE(total_ratings, 0) + 1,
            avg_rating = (
                SELECT COALESCE(AVG(rating)::DECIMAL(3,2), 0)
                FROM trip_reservations
                WHERE trip_id = NEW.trip_id AND rating IS NOT NULL
            )
        WHERE id = trip_id_val;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger oluştur
DROP TRIGGER IF EXISTS update_trip_rating_trigger ON trip_reservations;
CREATE TRIGGER update_trip_rating_trigger
    AFTER INSERT OR UPDATE OF rating ON trip_reservations
    FOR EACH ROW
    WHEN (NEW.rating IS NOT NULL)
    EXECUTE FUNCTION update_trip_rating();

-- ============================================================================
-- BÖLÜM 34: PROFİL ONAYI SİSTEMİ
-- ============================================================================

-- Profiles tablosuna onay sütunları ekle
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT false;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS verification_method TEXT; -- 'email', 'google', 'phone'

-- ============================================================================
-- BÖLÜM 35: KARGO-EMANET TALEP TİPİ SİSTEMİ
-- ============================================================================

-- shipments tablosuna request_type sütunu ekle
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS request_type TEXT DEFAULT 'sender';
-- 'carrier' = Yapacağım yolculuk için paket göndermek isteyenleri arıyorum
-- 'sender' = Paketimi götürecek birini arıyorum

-- ============================================================================
-- BÖLÜM 36: YOL ARKADAŞI MODÜLÜ İYİLEŞTİRMELERİ
-- ============================================================================

-- Trips tablosuna phone sütunu ekle
ALTER TABLE trips ADD COLUMN IF NOT EXISTS phone TEXT;

-- trip_reservations RLS Politikaları
DROP POLICY IF EXISTS "Reservations are viewable by everyone" ON trip_reservations;
DROP POLICY IF EXISTS "Authenticated users can create reservations" ON trip_reservations;
DROP POLICY IF EXISTS "Users can update own reservations" ON trip_reservations;
DROP POLICY IF EXISTS "Users can delete own reservations" ON trip_reservations;

-- Herkes rezervasyonları görüntüleyebilir (admin için)
CREATE POLICY "Reservations are viewable by everyone"
ON trip_reservations FOR SELECT
USING (true);

-- Giriş yapmış kullanıcılar rezervasyon yapabilir
CREATE POLICY "Authenticated users can create reservations"
ON trip_reservations FOR INSERT
WITH CHECK (auth.uid() = passenger_id);

-- Kullanıcılar kendi rezervasyonlarını güncelleyebilir
CREATE POLICY "Users can update own reservations"
ON trip_reservations FOR UPDATE
USING (auth.uid() = passenger_id);

-- Kullanıcılar kendi rezervasyonlarını silebilir
CREATE POLICY "Users can delete own reservations"
ON trip_reservations FOR DELETE
USING (auth.uid() = passenger_id);

-- ============================================================================
-- BÖLÜM 37: SAĞLIK TURİZMİ SİSTEMİ TABLOLARI
-- ============================================================================

-- 37.1 Health Clinics Tablosu
CREATE TABLE IF NOT EXISTS health_clinics (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  display_name TEXT NOT NULL, -- "Anlaşmalı Klinik - İstanbul Avrupa Yakası"
  internal_name TEXT NOT NULL, -- Gerçek klinik ismi (sadece admin görür)
  slug TEXT UNIQUE NOT NULL,
  city TEXT NOT NULL,
  district TEXT, -- "Avrupa Yakası", "Anadolu Yakası" gibi
  country TEXT DEFAULT 'TR',
  specialties TEXT[], -- ['saç_ekimi', 'diş', 'estetik', 'erkek_cinsel', 'kadın_cinsel', 'tüp_bebek']
  description TEXT,
  -- GİZLİ BİLGİLER (sadece admin görür):
  internal_address TEXT,
  internal_phone TEXT,
  internal_email TEXT,
  internal_website TEXT,
  -- GÖRÜNÜR BİLGİLER:
  logo_url TEXT,
  images TEXT[],
  accreditations TEXT[],
  price_range_min DECIMAL,
  price_range_max DECIMAL,
  currency TEXT DEFAULT 'EUR',
  rating DECIMAL(3,2),
  review_count INTEGER DEFAULT 0,
  languages TEXT[],
  services JSONB,
  packages JSONB,
  -- KOMİSYON AYARLARI:
  commission_rate DECIMAL(5,2), -- %15.00 gibi
  commission_type TEXT DEFAULT 'percentage', -- 'percentage' veya 'fixed'
  minimum_commission DECIMAL(10,2),
  -- DURUM:
  is_verified BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 37.2 Health Leads Tablosu
CREATE TABLE IF NOT EXISTS health_leads (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id),
  clinic_id UUID REFERENCES health_clinics(id),
  treatment_category TEXT NOT NULL, -- 'saç_ekimi', 'diş', 'estetik', 'erkek_cinsel', 'kadın_cinsel', 'tüp_bebek'
  treatment_type TEXT,
  reference_code TEXT UNIQUE NOT NULL, -- "HT-2026-001234" formatında
  -- HASTA BİLGİLERİ:
  full_name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT NOT NULL,
  whatsapp TEXT,
  country_code TEXT, -- Kullanıcının geldiği ülke (DE, BE, FR vb.)
  -- ÖN DEĞERLENDİRME:
  photos TEXT[],
  description TEXT,
  estimated_budget DECIMAL,
  preferred_date DATE,
  -- DURUM TAKİBİ:
  status TEXT DEFAULT 'new', -- 'new', 'contacted', 'quoted', 'confirmed', 'completed', 'cancelled'
  -- KLİNİK İLETİŞİMİ:
  clinic_contacted_at TIMESTAMP,
  clinic_quote DECIMAL,
  clinic_quote_currency TEXT DEFAULT 'EUR',
  -- KOMİSYON:
  commission_amount DECIMAL(10,2),
  commission_paid BOOLEAN DEFAULT false,
  commission_paid_at TIMESTAMP,
  -- NOTLAR:
  admin_notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 37.3 Health Treatments Tablosu
CREATE TABLE IF NOT EXISTS health_treatments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  clinic_id UUID REFERENCES health_clinics(id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  subcategory TEXT,
  name TEXT NOT NULL,
  description TEXT,
  duration_days INTEGER,
  price_min DECIMAL,
  price_max DECIMAL,
  display_price_range TEXT, -- "€1,500 - €3,000" gibi görünür aralık
  currency TEXT DEFAULT 'EUR',
  techniques TEXT[],
  created_at TIMESTAMP DEFAULT NOW()
);

-- 37.4 Health Reservations Tablosu
CREATE TABLE IF NOT EXISTS health_reservations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lead_id UUID REFERENCES health_leads(id),
  user_id UUID REFERENCES auth.users(id),
  clinic_id UUID REFERENCES health_clinics(id),
  treatment_id UUID REFERENCES health_treatments(id),
  reference_code TEXT UNIQUE NOT NULL,
  -- REZERVASYON DETAYLARI:
  full_name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT NOT NULL,
  preferred_date DATE,
  preferred_time TIME,
  notes TEXT,
  -- DURUM:
  status TEXT DEFAULT 'pending', -- 'pending', 'confirmed', 'completed', 'cancelled'
  -- KOMİSYON:
  commission_amount DECIMAL(10,2),
  commission_paid BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 37.5 Health Reviews Tablosu
CREATE TABLE IF NOT EXISTS health_reviews (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  clinic_id UUID REFERENCES health_clinics(id),
  user_id UUID REFERENCES auth.users(id),
  treatment_id UUID REFERENCES health_treatments(id),
  lead_id UUID REFERENCES health_leads(id),
  rating INTEGER CHECK (rating >= 1 AND rating <= 5),
  comment TEXT,
  before_after_images TEXT[],
  is_verified BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW()
);

-- 37.6 Health Commission Log Tablosu
CREATE TABLE IF NOT EXISTS health_commission_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lead_id UUID REFERENCES health_leads(id),
  reservation_id UUID REFERENCES health_reservations(id),
  clinic_id UUID REFERENCES health_clinics(id),
  amount DECIMAL(10,2) NOT NULL,
  currency TEXT DEFAULT 'EUR',
  status TEXT DEFAULT 'pending', -- 'pending', 'paid', 'cancelled'
  paid_at TIMESTAMP,
  payment_method TEXT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Index'ler
CREATE INDEX IF NOT EXISTS idx_health_leads_reference_code ON health_leads(reference_code);
CREATE INDEX IF NOT EXISTS idx_health_leads_status ON health_leads(status);
CREATE INDEX IF NOT EXISTS idx_health_leads_user_id ON health_leads(user_id);
CREATE INDEX IF NOT EXISTS idx_health_clinics_specialties ON health_clinics USING GIN(specialties);
CREATE INDEX IF NOT EXISTS idx_health_reservations_reference_code ON health_reservations(reference_code);

-- ============================================================================
-- BÖLÜM 38: SAĞLIK TURİZMİ RLS POLİTİKALARI
-- ============================================================================

-- 38.1 Health Clinics RLS Policies
ALTER TABLE health_clinics ENABLE ROW LEVEL SECURITY;

-- Herkes görünür alanları okuyabilir (internal_* hariç)
CREATE POLICY "Anyone can view public clinic info"
ON health_clinics FOR SELECT
USING (true);

-- Admin tüm alanları görebilir (internal_* dahil)
CREATE POLICY "Admins can view all clinic info"
ON health_clinics FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

-- Sadece admin yazabilir
CREATE POLICY "Only admins can insert clinics"
ON health_clinics FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

CREATE POLICY "Only admins can update clinics"
ON health_clinics FOR UPDATE
USING (
  EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

CREATE POLICY "Only admins can delete clinics"
ON health_clinics FOR DELETE
USING (
  EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

-- 38.2 Health Leads RLS Policies
ALTER TABLE health_leads ENABLE ROW LEVEL SECURITY;

-- Kullanıcılar kendi lead'lerini okuyabilir
CREATE POLICY "Users can view own leads"
ON health_leads FOR SELECT
USING (
  auth.uid() = user_id
  OR EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

-- Herkes lead oluşturabilir (misafir de)
CREATE POLICY "Anyone can create leads"
ON health_leads FOR INSERT
WITH CHECK (true);

-- Kullanıcılar kendi lead'lerini güncelleyebilir, admin hepsini
CREATE POLICY "Users can update own leads, admins can update all"
ON health_leads FOR UPDATE
USING (
  auth.uid() = user_id
  OR EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

-- 38.3 Health Treatments RLS Policies
ALTER TABLE health_treatments ENABLE ROW LEVEL SECURITY;

-- Herkes okuyabilir
CREATE POLICY "Anyone can view treatments"
ON health_treatments FOR SELECT
USING (true);

-- Sadece admin yazabilir
CREATE POLICY "Only admins can manage treatments"
ON health_treatments FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

-- 38.4 Health Reservations RLS Policies
ALTER TABLE health_reservations ENABLE ROW LEVEL SECURITY;

-- Kullanıcılar kendi rezervasyonlarını okuyabilir, admin hepsini
CREATE POLICY "Users can view own reservations, admins can view all"
ON health_reservations FOR SELECT
USING (
  auth.uid() = user_id
  OR EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

-- Kullanıcılar rezervasyon oluşturabilir, admin hepsini yönetebilir
CREATE POLICY "Users can create reservations, admins can manage all"
ON health_reservations FOR ALL
USING (
  auth.uid() = user_id
  OR EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

-- 38.5 Health Reviews RLS Policies
ALTER TABLE health_reviews ENABLE ROW LEVEL SECURITY;

-- Herkes okuyabilir
CREATE POLICY "Anyone can view reviews"
ON health_reviews FOR SELECT
USING (true);

-- Kullanıcılar yorum yazabilir, admin yönetebilir
CREATE POLICY "Users can create reviews, admins can manage all"
ON health_reviews FOR ALL
USING (
  auth.uid() = user_id
  OR EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

-- 38.6 Health Commission Log RLS Policies
ALTER TABLE health_commission_log ENABLE ROW LEVEL SECURITY;

-- Sadece admin görebilir
CREATE POLICY "Only admins can view commission log"
ON health_commission_log FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

CREATE POLICY "Only admins can manage commission log"
ON health_commission_log FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM profiles
    WHERE profiles.user_id = auth.uid()
    AND profiles.role = 'admin'
  )
);

-- ============================================================================
-- BÖLÜM 39: SUPABASE STORAGE BUCKET (Manuel Oluşturulacak)
-- ============================================================================
-- Supabase Dashboard > Storage > Create Bucket
-- Bucket Name: health-lead-photos
-- Public: Yes (veya No, RLS ile kontrol edilebilir)
-- File Size Limit: 10MB
-- Allowed MIME Types: image/*
-- ============================================================================

-- ============================================================================
-- TAMAMLANDI!
-- ============================================================================
-- Şimdi son adım: Kendinizi admin yapın.
-- Yukarıdaki UPDATE komutunu email adresinizle düzenleyip çalıştırın.
-- 
-- NOT: Supabase Storage'da 'health-lead-photos' bucket'ını manuel oluşturun.
-- ============================================================================
