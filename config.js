/* --------------------------------------------------------------------------
   PLATFORM AVRUPA - CONFIG.JS (Merkezi Yapılandırma Dosyası)
   Versiyon: 2.0
   Açıklama: Supabase bağlantısı ve API yapılandırmaları
   
   GÜVENLİK NOTU:
   - Supabase anon key client-side'da kullanılabilir (RLS ile korunur)
   - Google Maps ve Adzuna API anahtarları için HTTP referer kısıtlaması yapın
   - Admin fonksiyonları için backend (Edge Functions) kullanın
-------------------------------------------------------------------------- */

// ============================================================================
// SUPABASE YAPILANDIRMASI
// ============================================================================

const SUPABASE_URL = 'https://vhietrqljahdmloazgpp.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoaWV0cnFsamFoZG1sb2F6Z3BwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUwNTk5MTcsImV4cCI6MjA4MDYzNTkxN30.sxpUrTnR40XuEBPUeQXj352xMziGr_lDqdA8H69ejBA';

// ============================================================================
// API ANAHTARLARI (Sadece gerekli sayfalarda kullanın)
// NOT: Bu anahtarlar için Google Cloud Console'da HTTP referer kısıtlaması yapın
// İzin verilen domain: https://www.platformavrupa.com/*
// ============================================================================

const API_KEYS = {
    // Google Maps - Sadece admin.html ve sila_yolu.html'de kullanılıyor
    // Google Cloud Console'da HTTP referer kısıtlaması yapın!
    GOOGLE_MAPS: 'AIzaSyAfadKqif0yyGgan1BQJYZNTidKRmAG2G8',
    
    // Adzuna Job API - Sadece admin.html'de kullanılıyor
    // Prod'da bu API çağrıları Supabase Edge Function üzerinden yapılmalı
    ADZUNA_ID: 'c0c66624',
    ADZUNA_KEY: '5a2d86df68a24e6fe8b1e9b4319347f0',
    
    // NewsAPI - Otomatik haber önerileri için (günde 100 ücretsiz request)
    // Türk diasporası, vatandaşlık, finans haberleri
    NEWS_API: 'fe4b9d88c63545f6a824467f7ccd25df',

    // Windy Webcam API - sila_yolu.html kamera görüntüsü için
    WINDY_WEBCAM: 'xmUfa53M3iU53yJQW9c0HfmITZdtQGEH'
};

// ============================================================================
// SUPABASE CLIENT OLUŞTURMA
// ============================================================================

let sb = null;

if (typeof supabase !== 'undefined') {
    sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
    console.log("✅ Config.js: Supabase bağlantısı hazır");
} else {
    console.error("❌ HATA: Supabase kütüphanesi yüklenmemiş!");
}

// ============================================================================
// ADMIN KORUMASI
// ============================================================================

/**
 * Kullanıcının admin olup olmadığını kontrol eder
 * @returns {Promise<boolean>}
 */
async function isAdmin() {
    if (!sb) return false;
    
    try {
        const { data: { user } } = await sb.auth.getUser();
        if (!user) return false;
        
        const { data: profile } = await sb.from('profiles')
            .select('role')
            .eq('id', user.id)
            .single();
        
        return profile?.role === 'admin';
    } catch (error) {
        console.error('Admin kontrolü hatası:', error);
        return false;
    }
}

/**
 * Admin sayfalarını korur - admin değilse yönlendirir
 */
async function requireAdmin() {
    const admin = await isAdmin();
    if (!admin) {
        alert('Bu sayfaya erişim yetkiniz yok!');
        window.location.href = 'index.html';
        return false;
    }
    return true;
}

/**
 * Kullanıcının giriş yapıp yapmadığını kontrol eder
 * @returns {Promise<object|null>} - Kullanıcı objesi veya null
 */
async function getCurrentUser() {
    if (!sb) return null;
    
    try {
        const { data: { session }, error } = await sb.auth.getSession();
        if (error) throw error;
        return session?.user || null;
    } catch (error) {
        return null;
    }
}

/**
 * Kullanıcı profilini getirir
 * @returns {Promise<object|null>}
 */
async function getCurrentProfile() {
    const user = await getCurrentUser();
    if (!user) return null;
    
    try {
        const { data: profile } = await sb.from('profiles')
            .select('*')
            .eq('id', user.id)
            .single();
        return profile;
    } catch (error) {
        return null;
    }
}

// ============================================================================
// AFFILIATE YAPILANDIRMASI
// ============================================================================

const AFFILIATE_CONFIG = {
    // Travelpayouts - Tek platformdan tüm partnerler
    // Kayıt: https://www.travelpayouts.com
    travelpayouts: {
        marker: 'SIZIN_TRAVELPAYOUTS_MARKER',  // Kayıt sonrası alacaksınız
        token: 'SIZIN_API_TOKEN'               // API erişimi için
    },
    
    // Booking.com - Otel rezervasyonları
    // Travelpayouts üzerinden veya direkt: https://www.booking.com/affiliate-program
    booking: {
        aid: '304142',                          // Platform Avrupa affiliate ID (değiştirin)
        label: 'platformavrupa'
    },
    
    // Skyscanner - Uçak bileti
    // Travelpayouts üzerinden gelir
    skyscanner: {
        // Skyscanner linki Travelpayouts üzerinden yönetilir
        // Direkt link kullanılıyor, tracking marker ile
    },
    
    // Rentalcars - Araç kiralama
    // https://www.rentalcars.com/affiliates
    rentalcars: {
        affiliateCode: 'platformavrupa',        // Kayıt sonrası alacaksınız
        preflang: 'tr',
        prefcurrency: 'EUR'
    },
    
    // Tatil Sepeti
    tatilSepeti: {
        ref: 'platformavrupa'
    },
    
    // Viator (Aktiviteler) - Opsiyonel
    viator: {
        pid: '',                                // Viator partner ID
        mcid: ''
    }
};

// ============================================================================
// AFFILIATE TRACKING HELPER FONKSİYONLARI
// ============================================================================

/**
 * Affiliate tıklamasını kaydeder
 * @param {string} partner - Partner adı (skyscanner, booking, rentalcars, tatilsepeti)
 * @param {string} page - Hangi sayfadan tıklandı
 * @param {object} metadata - Ek bilgiler (destinasyon, fiyat vb.)
 */
async function trackAffiliateClick(partner, page, metadata = {}) {
    if (!sb) return;
    
    try {
        const user = await getCurrentUser();
        
        await sb.from('affiliate_clicks').insert({
            partner: partner,
            page: page,
            user_id: user?.id || null,
            metadata: metadata,
            created_at: new Date().toISOString()
        });
        
        console.log(`✅ Affiliate tıklama kaydedildi: ${partner}`);
    } catch (error) {
        console.error('Affiliate tracking hatası:', error);
    }
}

/**
 * Skyscanner affiliate linkini oluşturur
 * @param {string} origin - Kalkış havalimanı kodu
 * @param {string} destination - Varış havalimanı kodu
 * @param {string} date - Tarih (YYMMDD formatında)
 * @param {object} options - Ek parametreler
 */
function buildSkyscannerLink(origin, destination, date, options = {}) {
    const baseUrl = 'https://www.skyscanner.com.tr/transport/flights';
    const params = new URLSearchParams({
        adultsv2: options.adults || 1,
        cabinclass: options.cabinClass || 'economy',
        ref: 'day-view'
    });
    
    if (options.children) {
        params.append('childrenv2', options.children);
    }
    
    return `${baseUrl}/${origin}/${destination}/${date}?${params.toString()}`;
}

/**
 * Booking.com affiliate linkini oluşturur
 * @param {string} destination - Şehir veya otel adı
 * @param {string} checkIn - Giriş tarihi (YYYY-MM-DD)
 * @param {string} checkOut - Çıkış tarihi (YYYY-MM-DD)
 * @param {object} options - Ek parametreler
 */
function buildBookingLink(destination, checkIn, checkOut, options = {}) {
    const baseUrl = 'https://www.booking.com/searchresults.html';
    const params = new URLSearchParams({
        ss: destination,
        checkin: checkIn,
        checkout: checkOut,
        group_adults: options.adults || 2,
        group_children: options.children || 0,
        no_rooms: options.rooms || 1,
        aid: AFFILIATE_CONFIG.booking.aid,
        label: AFFILIATE_CONFIG.booking.label
    });
    
    return `${baseUrl}?${params.toString()}`;
}

/**
 * Rentalcars affiliate linkini oluşturur
 * @param {string} pickupLocation - Alış yeri
 * @param {string} pickupDate - Alış tarihi
 * @param {string} dropoffDate - Teslim tarihi
 */
function buildRentalcarsLink(pickupLocation, pickupDate, dropoffDate) {
    const baseUrl = 'https://www.rentalcars.com/search-results';
    const params = new URLSearchParams({
        searchType: 'location',
        pickupPlace: pickupLocation,
        pickupDate: pickupDate,
        dropoffDate: dropoffDate,
        driversAge: 30,
        affiliateCode: AFFILIATE_CONFIG.rentalcars.affiliateCode,
        preflang: AFFILIATE_CONFIG.rentalcars.preflang,
        prefcurrency: AFFILIATE_CONFIG.rentalcars.prefcurrency
    });
    
    return `${baseUrl}?${params.toString()}`;
}

/**
 * Tatil Sepeti affiliate linkini oluşturur
 * @param {string} slug - Tur slug'ı (ör: ege-turlari)
 */
function buildTatilSepetiLink(slug) {
    return `https://www.tatilsepeti.com/${slug}?ref=${AFFILIATE_CONFIG.tatilSepeti.ref}`;
}

// ============================================================================
// GLOBAL EXPORTS
// ============================================================================

window.SUPABASE_URL = SUPABASE_URL;
window.SUPABASE_KEY = SUPABASE_KEY;
window.API_KEYS = API_KEYS;
window.AFFILIATE_CONFIG = AFFILIATE_CONFIG;
window.sb = sb;
window.isAdmin = isAdmin;
window.requireAdmin = requireAdmin;
window.getCurrentUser = getCurrentUser;
// ============================================================================
// SAĞLIK TURİZMİ - WHATSAPP ENTEGRASYONU
// ============================================================================

// Sağlık Turizmi Ayarları
const HEALTH_TOURISM_CONFIG = {
    whatsappNumber: '+32XXXXXXXXX', // PlatformAvrupa WhatsApp Business numarası (DÜZENLENECEK)
    whatsappMessage: {
        default: 'Merhaba, PlatformAvrupa üzerinden sağlık turizmi danışmanlığı almak istiyorum.',
        sac_ekimi: 'Merhaba, PlatformAvrupa üzerinden saç ekimi hakkında bilgi almak istiyorum.',
        dis: 'Merhaba, PlatformAvrupa üzerinden diş tedavisi hakkında bilgi almak istiyorum.',
        estetik: 'Merhaba, PlatformAvrupa üzerinden estetik cerrahi hakkında bilgi almak istiyorum.',
        erkek_cinsel: 'Merhaba, PlatformAvrupa üzerinden erkek cinsel sağlık konusunda danışmanlık almak istiyorum.',
        kadin_cinsel: 'Merhaba, PlatformAvrupa üzerinden kadın cinsel sağlık konusunda danışmanlık almak istiyorum.',
        tup_bebek: 'Merhaba, PlatformAvrupa üzerinden tüp bebek tedavisi hakkında bilgi almak istiyorum.'
    }
};

/**
 * WhatsApp link oluşturucu
 * @param {string} category - Tedavi kategorisi ('sac_ekimi', 'dis', 'estetik', vb.)
 * @param {string} referenceCode - Referans kodu (opsiyonel)
 * @returns {string} WhatsApp linki
 */
function buildWhatsAppLink(category = 'default', referenceCode = null) {
    const baseUrl = 'https://wa.me/';
    const phone = HEALTH_TOURISM_CONFIG.whatsappNumber.replace(/[^0-9]/g, '');
    const message = HEALTH_TOURISM_CONFIG.whatsappMessage[category] || HEALTH_TOURISM_CONFIG.whatsappMessage.default;
    
    let fullMessage = message;
    if (referenceCode) {
        fullMessage += `\n\nReferans Kodu: ${referenceCode}`;
    }
    
    const encodedMessage = encodeURIComponent(fullMessage);
    return `${baseUrl}${phone}?text=${encodedMessage}`;
}

/**
 * Referans kodu oluşturucu
 * @returns {string} "HT-YYYY-NNNNNN" formatında referans kodu
 */
function generateHealthReferenceCode() {
    const year = new Date().getFullYear();
    const randomNum = Math.floor(100000 + Math.random() * 900000);
    return `HT-${year}-${randomNum}`;
}

window.getCurrentProfile = getCurrentProfile;
window.trackAffiliateClick = trackAffiliateClick;
window.buildSkyscannerLink = buildSkyscannerLink;
window.buildBookingLink = buildBookingLink;
window.buildRentalcarsLink = buildRentalcarsLink;
window.buildTatilSepetiLink = buildTatilSepetiLink;
window.buildWhatsAppLink = buildWhatsAppLink;
window.generateHealthReferenceCode = generateHealthReferenceCode;
window.HEALTH_TOURISM_CONFIG = HEALTH_TOURISM_CONFIG;