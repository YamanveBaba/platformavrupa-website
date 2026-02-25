-- ============================================================================
-- SAĞLIK TURİZMİ - ÖRNEK KLİNİK VERİLERİ
-- ============================================================================
-- Bu dosyayı Supabase Dashboard > SQL Editor'da çalıştırın
-- Örnek klinik verileri ekler (display_name ve internal_name ayrı)
-- ============================================================================

-- Saç Ekimi Klinikleri
INSERT INTO health_clinics (display_name, internal_name, slug, city, district, specialties, description, internal_phone, internal_email, price_range_min, price_range_max, commission_rate, is_verified, is_active) VALUES
('Anlaşmalı Klinik - İstanbul Avrupa Yakası', 'Dr. Serkan Aygin Clinic', 'anlasmali-klinik-istanbul-avrupa-yakasi', 'İstanbul', 'Avrupa Yakası', ARRAY['saç_ekimi'], '25+ yıllık deneyim, Sapphire FUE uzmanı. Yüksek graft başarı oranı.', '+90 212 XXX XX XX', 'info@serkanaygin.com', 2000, 3500, 20.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'ASMED Clinic', 'anlasmali-klinik-istanbul-asmed', 'İstanbul', 'Avrupa Yakası', ARRAY['saç_ekimi'], 'Manuel FUE ve doğal saç çizgisi tasarımıyla ünlü. JCI akreditasyonlu.', '+90 212 XXX XX XX', 'info@asmed.com', 3000, 5000, 25.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'Medart Hair Clinic', 'anlasmali-klinik-istanbul-medart', 'İstanbul', 'Avrupa Yakası', ARRAY['saç_ekimi'], 'Yapılandırılmış bakım ve sonrası takipte lider. Sapphire teknikleri.', '+90 212 XXX XX XX', 'info@medart.com', 2500, 4000, 18.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'EsteFavor Clinic', 'anlasmali-klinik-istanbul-estefavor', 'İstanbul', 'Avrupa Yakası', ARRAY['saç_ekimi'], 'Düşük hacimli, yüksek hassasiyetli işlemler. Afro saç tipleri için ideal.', '+90 212 XXX XX XX', 'info@estefavor.com', 2000, 3000, 15.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'Vera Clinic', 'anlasmali-klinik-istanbul-vera', 'İstanbul', 'Avrupa Yakası', ARRAY['saç_ekimi'], 'OxyCure yeniliğiyle tanınıyor, 40.000+ hasta. Tam paketler.', '+90 212 XXX XX XX', 'info@veraclinic.com', 2500, 4500, 20.00, true, true);

-- Diş Klinikleri
INSERT INTO health_clinics (display_name, internal_name, slug, city, district, specialties, description, internal_phone, internal_email, price_range_min, price_range_max, commission_rate, is_verified, is_active) VALUES
('Anlaşmalı Klinik - İstanbul', 'Vera Smile', 'anlasmali-klinik-istanbul-vera-smile', 'İstanbul', 'Avrupa Yakası', ARRAY['dis'], 'İmplant ve kozmetik dişçilikte lider. JCI standartları, spa benzeri deneyim.', '+90 212 XXX XX XX', 'info@verasmile.com', 500, 800, 15.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'DentSpa', 'anlasmali-klinik-istanbul-dentspa', 'İstanbul', 'Avrupa Yakası', ARRAY['dis'], 'Kişiselleştirilmiş bakım, 3D tarama. Tam ağız restorasyonu paketleri.', '+90 212 XXX XX XX', 'info@dentspa.com', 400, 700, 15.00, true, true),
('Anlaşmalı Klinik - İzmir', 'WestDent Clinic', 'anlasmali-klinik-izmir-westdent', 'İzmir', 'Merkez', ARRAY['dis'], 'Çok disiplinli ekip, implant entegrasyonu. Hızlı iyileşme odaklı.', '+90 232 XXX XX XX', 'info@westdent.com', 400, 700, 15.00, true, true),
('Anlaşmalı Klinik - Antalya', 'Dentatur', 'anlasmali-klinik-antalya-dentatur', 'Antalya', 'Merkez', ARRAY['dis'], 'İmplant destekli restorasyonlarda uzman. Tatil paketi entegrasyonu.', '+90 242 XXX XX XX', 'info@dentatur.com', 400, 700, 15.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'Dentakay', 'anlasmali-klinik-istanbul-dentakay', 'İstanbul', 'Avrupa Yakası', ARRAY['dis'], 'Dijital tasarım, hızlı işlem. Uluslararası hasta desteği.', '+90 212 XXX XX XX', 'info@dentakay.com', 300, 600, 15.00, true, true);

-- Estetik Klinikleri
INSERT INTO health_clinics (display_name, internal_name, slug, city, district, specialties, description, internal_phone, internal_email, price_range_min, price_range_max, commission_rate, is_verified, is_active) VALUES
('Anlaşmalı Klinik - İstanbul', 'Istanbul Aesthetic Plastic Surgery Center', 'anlasmali-klinik-istanbul-aesthetic', 'İstanbul', 'Avrupa Yakası', ARRAY['estetik'], 'Yüz, göğüs ve vücut işlemlerinde uzman. 3D modelleme.', '+90 212 XXX XX XX', 'info@istanbulaesthetic.com', 2500, 4000, 20.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'Doku Medical Clinic', 'anlasmali-klinik-istanbul-doku', 'İstanbul', 'Avrupa Yakası', ARRAY['estetik'], 'Estetik ve saç birleşimi, Emsculpt gibi non-invaziv seçenekler.', '+90 212 XXX XX XX', 'info@dokuclinic.com', 2000, 3500, 20.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'Orion Surgery Center', 'anlasmali-klinik-istanbul-orion', 'İstanbul', 'Avrupa Yakası', ARRAY['estetik'], 'Butik ortam, Vectra XT görüntüleme. Tam vücut şekillendirme.', '+90 212 XXX XX XX', 'info@orionsurgery.com', 3000, 5000, 20.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'Dr. Safa Manav Clinic', 'anlasmali-klinik-istanbul-safa-manav', 'İstanbul', 'Avrupa Yakası', ARRAY['estetik'], 'EBOPRAS sertifikalı, uluslararası odaklı.', '+90 212 XXX XX XX', 'info@safamanav.com', 4000, 6000, 20.00, true, true);

-- Erkek Cinsel Sağlık Klinikleri
INSERT INTO health_clinics (display_name, internal_name, slug, city, district, specialties, description, internal_phone, internal_email, price_range_min, price_range_max, commission_rate, is_verified, is_active) VALUES
('Anlaşmalı Klinik - İstanbul', 'Andromeda Androloji', 'anlasmali-klinik-istanbul-andromeda', 'İstanbul', 'Avrupa Yakası', ARRAY['erkek_cinsel'], 'Erken boşalma, erektil disfonksiyon, penis estetiği uzmanı.', '+90 212 XXX XX XX', 'info@andromeda.com', 1500, 4000, 15.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'Istanbul Andrology Center', 'anlasmali-klinik-istanbul-andrology', 'İstanbul', 'Avrupa Yakası', ARRAY['erkek_cinsel'], 'Üroloji birimleri güçlü, PRP ve penil protez uzmanı.', '+90 212 XXX XX XX', 'info@istanbulandrology.com', 2000, 5000, 15.00, true, true);

-- Kadın Cinsel Sağlık Klinikleri
INSERT INTO health_clinics (display_name, internal_name, slug, city, district, specialties, description, internal_phone, internal_email, price_range_min, price_range_max, commission_rate, is_verified, is_active) VALUES
('Anlaşmalı Klinik - İstanbul', 'Jin. Op. Dr. Süleyman Eserdağ Clinic', 'anlasmali-klinik-istanbul-eserdag', 'İstanbul', 'Avrupa Yakası', ARRAY['kadin_cinsel'], 'Vajinismus, vajinal estetik, labioplasti uzmanı.', '+90 212 XXX XX XX', 'info@eserdag.com', 1500, 4000, 15.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'Vajinusmus Tedavi Merkezi', 'anlasmali-klinik-istanbul-vajinusmus', 'İstanbul', 'Avrupa Yakası', ARRAY['kadin_cinsel'], 'Vajinismus tedavisinde uzman, cinsel terapi hizmeti.', '+90 212 XXX XX XX', 'info@vajinusmustedavi.com', 2000, 4000, 15.00, true, true);

-- Tüp Bebek Klinikleri
INSERT INTO health_clinics (display_name, internal_name, slug, city, district, specialties, description, internal_phone, internal_email, price_range_min, price_range_max, commission_rate, is_verified, is_active) VALUES
('Anlaşmalı Klinik - İstanbul', 'Bahçeci Health Group', 'anlasmali-klinik-istanbul-bahceci', 'İstanbul', 'Avrupa Yakası', ARRAY['tup_bebek'], 'IVF, ICSI, embriyo transferi. Yüksek başarı oranı.', '+90 212 XXX XX XX', 'info@bahceci.com', 3000, 6000, 10.00, true, true),
('Anlaşmalı Klinik - İstanbul', 'Memorial Healthcare Group', 'anlasmali-klinik-istanbul-memorial', 'İstanbul', 'Avrupa Yakası', ARRAY['tup_bebek'], 'Tüp bebek ve üreme sağlığı merkezi. Donasyon hizmeti.', '+90 212 XXX XX XX', 'info@memorial.com', 3500, 7000, 10.00, true, true);

-- Akreditasyon ve rating güncellemeleri
UPDATE health_clinics SET accreditations = ARRAY['JCI', 'ISO'] WHERE internal_name IN ('ASMED Clinic', 'Vera Smile', 'Istanbul Aesthetic Plastic Surgery Center');
UPDATE health_clinics SET accreditations = ARRAY['Sağlık Bakanlığı'] WHERE accreditations IS NULL;
UPDATE health_clinics SET rating = 4.5 + (RANDOM() * 0.5), review_count = FLOOR(50 + RANDOM() * 200) WHERE rating IS NULL;
