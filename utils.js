/* --------------------------------------------------------------------------
   PLATFORM AVRUPA - UTILS.JS (Güvenlik ve Yardımcı Fonksiyonlar)
   Versiyon: 1.0
   Açıklama: XSS koruması, sanitization ve ortak yardımcı fonksiyonlar
-------------------------------------------------------------------------- */

// ============================================================================
// 1. XSS KORUMASI - HTML SANITIZATION
// ============================================================================

/**
 * HTML özel karakterlerini escape eder - XSS saldırılarına karşı koruma
 * @param {string} str - Temizlenecek string
 * @returns {string} - Güvenli string
 */
function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * Kullanıcı girdisini güvenli hale getirir (XSS koruması)
 * @param {string} input - Kullanıcı girdisi
 * @returns {string} - Sanitize edilmiş string
 */
function sanitize(input) {
    if (input === null || input === undefined) return '';
    if (typeof input !== 'string') input = String(input);
    
    // HTML özel karakterlerini escape et
    return input
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;')
        .replace(/\//g, '&#x2F;');
}

/**
 * URL'i güvenli hale getirir (javascript: gibi tehlikeli protokolleri engeller)
 * @param {string} url - Kontrol edilecek URL
 * @returns {string} - Güvenli URL veya boş string
 */
function sanitizeURL(url) {
    if (!url) return '';
    
    // Tehlikeli protokolleri kontrol et
    const dangerousProtocols = ['javascript:', 'data:', 'vbscript:'];
    const lowerURL = url.toLowerCase().trim();
    
    for (const protocol of dangerousProtocols) {
        if (lowerURL.startsWith(protocol)) {
            console.warn('Tehlikeli URL engellendi:', url);
            return '';
        }
    }
    
    return url;
}

/**
 * Telefon numarasını güvenli formata getirir
 * @param {string} phone - Telefon numarası
 * @returns {string} - Sadece rakam ve + içeren string
 */
function sanitizePhone(phone) {
    if (!phone) return '';
    return phone.replace(/[^\d+\-\s]/g, '');
}

/**
 * Email adresini doğrular
 * @param {string} email - Email adresi
 * @returns {boolean} - Geçerli mi?
 */
function isValidEmail(email) {
    if (!email) return false;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// ============================================================================
// 2. GÜVENLİ DOM MANİPÜLASYONU
// ============================================================================

/**
 * Güvenli innerHTML alternatifi - kullanıcı verisini sanitize ederek ekler
 * @param {HTMLElement} element - Hedef element
 * @param {string} html - HTML içeriği (güvenilir kaynak)
 * @param {object} data - Değiştirilecek veriler (sanitize edilecek)
 */
function safeInnerHTML(element, template, data = {}) {
    if (!element) return;
    
    let result = template;
    
    // Tüm data değerlerini sanitize et ve template'e yerleştir
    for (const [key, value] of Object.entries(data)) {
        const placeholder = new RegExp(`{{${key}}}`, 'g');
        result = result.replace(placeholder, sanitize(value));
    }
    
    element.innerHTML = result;
}

/**
 * Güvenli textContent ayarlama
 * @param {HTMLElement} element - Hedef element
 * @param {string} text - Metin
 */
function safeText(element, text) {
    if (!element) return;
    element.textContent = text || '';
}

/**
 * Güvenli element oluşturma
 * @param {string} tag - HTML tag adı
 * @param {object} attrs - Attributes
 * @param {string} text - İçerik metni
 * @returns {HTMLElement}
 */
function createElement(tag, attrs = {}, text = '') {
    const el = document.createElement(tag);
    
    for (const [key, value] of Object.entries(attrs)) {
        if (key === 'className') {
            el.className = value;
        } else if (key === 'dataset') {
            for (const [dataKey, dataValue] of Object.entries(value)) {
                el.dataset[dataKey] = dataValue;
            }
        } else if (key.startsWith('on')) {
            // Event listener'lar için güvenlik kontrolü
            if (typeof value === 'function') {
                el.addEventListener(key.substring(2).toLowerCase(), value);
            }
        } else {
            el.setAttribute(key, value);
        }
    }
    
    if (text) {
        el.textContent = text;
    }
    
    return el;
}

// ============================================================================
// 3. YARDIMCI FONKSİYONLAR
// ============================================================================

/**
 * Tarih formatlama
 * @param {string|Date} date - Tarih
 * @param {string} format - Format tipi ('short', 'long', 'time', 'datetime', 'chartShort', 'weekdayShort')
 * @returns {string}
 */
function formatDate(date, format = 'short') {
    if (!date) return '';
    
    const d = new Date(date);
    if (isNaN(d.getTime())) return '';
    
    const options = {
        short: { day: '2-digit', month: '2-digit', year: 'numeric' },
        long: { day: 'numeric', month: 'long', year: 'numeric' },
        time: { hour: '2-digit', minute: '2-digit' },
        datetime: { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' },
        chartShort: { day: 'numeric', month: 'short' },
        weekdayShort: { weekday: 'short', day: 'numeric' }
    };
    
    return d.toLocaleString('tr-TR', options[format] || options.long);
}

/**
 * Para formatı
 * @param {number} amount - Miktar
 * @param {string} currency - Para birimi
 * @returns {string}
 */
function formatCurrency(amount, currency = 'EUR') {
    if (amount === null || amount === undefined) return '';
    
    const symbols = { EUR: '€', TRY: '₺', USD: '$', GBP: '£' };
    const symbol = symbols[currency] || currency;
    
    return `${Number(amount).toLocaleString('tr-TR')} ${symbol}`;
}

/**
 * Metin kısaltma
 * @param {string} text - Metin
 * @param {number} maxLength - Maksimum uzunluk
 * @returns {string}
 */
function truncateText(text, maxLength = 100) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
}

/**
 * Debounce fonksiyonu - performans için
 * @param {Function} func - Çalıştırılacak fonksiyon
 * @param {number} wait - Bekleme süresi (ms)
 * @returns {Function}
 */
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Loading spinner göster/gizle
 * @param {HTMLElement} element - Hedef element
 * @param {boolean} show - Göster/gizle
 */
function setLoading(element, show = true) {
    if (!element) return;
    
    if (show) {
        element.dataset.originalContent = element.innerHTML;
        element.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        element.disabled = true;
    } else {
        element.innerHTML = element.dataset.originalContent || element.innerHTML;
        element.disabled = false;
    }
}

// ============================================================================
// 4. SOHBET/MESAJ İÇİN ÖZEL FONKSİYONLAR
// ============================================================================

/**
 * Sohbet mesajı için güvenli HTML oluşturur
 * @param {object} msg - Mesaj objesi
 * @param {string} currentUserName - Mevcut kullanıcı adı
 * @returns {string} - Güvenli HTML
 */
function createChatMessageHTML(msg, currentUserName) {
    const isMine = msg.user_name === currentUserName;
    const time = formatDate(msg.created_at, 'time');
    const safeName = sanitize(msg.user_name);
    const safeContent = sanitize(msg.content);
    
    if (isMine) {
        return `
        <div class="flex justify-end">
            <div class="msg-bubble msg-own shadow-lg">
                <p>${safeContent}</p>
                <div class="text-[9px] text-white/60 text-right mt-1">${time}</div>
            </div>
        </div>`;
    } else {
        return `
        <div class="flex justify-start">
            <div class="msg-bubble msg-other shadow-md">
                <span class="text-[10px] font-bold text-indigo-400 block mb-1">${safeName}</span>
                <p class="text-slate-300">${safeContent}</p>
                <div class="text-[9px] text-slate-500 mt-1">${time}</div>
            </div>
        </div>`;
    }
}

/**
 * İlan kartı için güvenli HTML oluşturur
 * @param {object} ilan - İlan objesi
 * @returns {string} - Güvenli HTML
 */
function createIlanCardHTML(ilan) {
    const safeTitle = sanitize(ilan.title);
    const safePrice = sanitize(ilan.price);
    const safeCategory = sanitize(ilan.category);
    const safeCity = sanitize(ilan.city);
    const safeImage = sanitizeURL(ilan.image) || 'https://via.placeholder.com/300x200?text=Resim+Yok';
    
    return `
    <a href="ilan_detay.html?id=${sanitize(ilan.id)}" class="block bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-lg transition group">
        <div class="h-48 overflow-hidden bg-slate-100">
            <img src="${safeImage}" alt="${safeTitle}" class="w-full h-full object-cover group-hover:scale-105 transition" loading="lazy">
        </div>
        <div class="p-4">
            <h3 class="font-bold text-slate-900 line-clamp-1">${safeTitle}</h3>
            <p class="text-sm text-slate-500 mt-1">${safeCategory} • ${safeCity}</p>
            <p class="text-lg font-bold text-emerald-600 mt-2">${safePrice}</p>
        </div>
    </a>`;
}

// ============================================================================
// 5. EXPORT (Global scope'a ekle)
// ============================================================================

// Tüm fonksiyonları global scope'a ekle
window.escapeHTML = escapeHTML;
window.sanitize = sanitize;
window.sanitizeURL = sanitizeURL;
window.sanitizePhone = sanitizePhone;
window.isValidEmail = isValidEmail;
window.safeInnerHTML = safeInnerHTML;
window.safeText = safeText;
window.createElement = createElement;
window.formatDate = formatDate;
window.formatCurrency = formatCurrency;
window.truncateText = truncateText;
window.debounce = debounce;
window.setLoading = setLoading;
window.createChatMessageHTML = createChatMessageHTML;
window.createIlanCardHTML = createIlanCardHTML;

console.log('✅ Utils.js yüklendi - XSS koruması aktif');
