/* --------------------------------------------------------------------------
   PLATFORM AVRUPA - COMPONENTS.JS (Ortak Bileşenler)
   Versiyon: 1.0
   Açıklama: Navbar, Footer ve diğer ortak UI bileşenleri
   
   Kullanım:
   1. HTML'de body içine navbar için: <div id="navbar-container"></div>
   2. HTML'de body içine footer için: <div id="footer-container"></div>
   3. Script olarak ekleyin: <script src="components.js"></script>
-------------------------------------------------------------------------- */

// ============================================================================
// NAVBAR BİLEŞENİ
// ============================================================================

/**
 * Navbar HTML'ini oluşturur
 * @param {object} options - Ayarlar {dark: boolean, transparent: boolean}
 */
function getNavbarHTML(options = {}) {
    const isDark = options.dark || false;
    const isTransparent = options.transparent || false;
    
    const bgClass = isDark 
        ? 'bg-[#0f172a]' 
        : (isTransparent ? 'bg-white/90 backdrop-blur' : 'bg-white');
    const textClass = isDark ? 'text-white' : 'text-slate-800';
    const borderClass = isDark ? 'border-white/10' : 'border-slate-200';
    
    return `
    <nav class="${bgClass} border-b ${borderClass} sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            
            <!-- Logo -->
            <a href="index.html" class="flex items-center gap-2 group">
                <img src="logo.png" alt="PA" class="w-8 h-8 rounded-lg shadow-lg group-hover:scale-105 transition">
                <span class="font-bold text-lg ${textClass}">Platform<span class="text-blue-500">Avrupa</span></span>
            </a>
            
            <!-- Desktop Menu -->
            <div class="hidden md:flex items-center gap-6">
                <a href="ilanlar.html" class="${textClass} hover:text-blue-500 text-sm font-medium transition">İlanlar</a>
                <a href="firsatlar.html" class="${textClass} hover:text-orange-500 text-sm font-medium transition flex items-center gap-1">
                    <span class="text-orange-400">🔥</span> Fırsatlar
                </a>
                <a href="sila_yolu.html" class="${textClass} hover:text-blue-500 text-sm font-medium transition">Sıla Yolu</a>
                <a href="market.html" class="${textClass} hover:text-blue-500 text-sm font-medium transition">Market</a>
            </div>
            
            <!-- Auth Buttons (auth.js tarafından güncellenir) -->
            <div id="authButtons" class="flex items-center gap-3">
                <a href="login.html" class="text-sm font-bold ${textClass} hover:text-blue-500 transition">Giriş Yap</a>
            </div>
            
            <!-- Mobile Menu Button -->
            <button onclick="toggleMobileMenu()" class="md:hidden w-10 h-10 flex items-center justify-center ${textClass}">
                <i class="fa-solid fa-bars text-xl" id="menuIcon"></i>
            </button>
        </div>
        
        <!-- Mobile Menu -->
        <div id="mobileMenu" class="hidden md:hidden ${bgClass} border-t ${borderClass} pb-4">
            <div class="px-4 py-2 space-y-1">
                <a href="ilanlar.html" class="block py-3 px-4 rounded-lg ${textClass} hover:bg-white/10 font-medium">
                    <i class="fa-solid fa-list mr-3"></i> İlanlar
                </a>
                <a href="firsatlar.html" class="block py-3 px-4 rounded-lg ${textClass} hover:bg-white/10 font-medium text-orange-400">
                    <i class="fa-solid fa-fire mr-3"></i> Fırsatlar
                </a>
                <a href="sila_yolu.html" class="block py-3 px-4 rounded-lg ${textClass} hover:bg-white/10 font-medium">
                    <i class="fa-solid fa-road mr-3"></i> Sıla Yolu
                </a>
                <a href="market.html" class="block py-3 px-4 rounded-lg ${textClass} hover:bg-white/10 font-medium">
                    <i class="fa-solid fa-store mr-3"></i> Market
                </a>
                <div class="border-t ${borderClass} my-2"></div>
                <a href="ilanlarim.html" class="block py-3 px-4 rounded-lg ${textClass} hover:bg-white/10 font-medium">
                    <i class="fa-solid fa-bookmark mr-3"></i> İlanlarım
                </a>
                <a href="favorilerim.html" class="block py-3 px-4 rounded-lg ${textClass} hover:bg-white/10 font-medium">
                    <i class="fa-solid fa-heart mr-3 text-red-400"></i> Favorilerim
                </a>
                <a href="profil.html" class="block py-3 px-4 rounded-lg ${textClass} hover:bg-white/10 font-medium">
                    <i class="fa-solid fa-user mr-3"></i> Profilim
                </a>
            </div>
        </div>
    </nav>`;
}

/**
 * Mobile menüyü açıp kapatır
 */
function toggleMobileMenu() {
    const menu = document.getElementById('mobileMenu');
    const icon = document.getElementById('menuIcon');
    
    if (menu.classList.contains('hidden')) {
        menu.classList.remove('hidden');
        icon.classList.remove('fa-bars');
        icon.classList.add('fa-times');
    } else {
        menu.classList.add('hidden');
        icon.classList.remove('fa-times');
        icon.classList.add('fa-bars');
    }
}

// ============================================================================
// FOOTER BİLEŞENİ
// ============================================================================

/**
 * Footer HTML'ini oluşturur
 * @param {object} options - Ayarlar {dark: boolean}
 */
function getFooterHTML(options = {}) {
    const isDark = options.dark || false;
    
    const bgClass = isDark ? 'bg-[#0a0f1a]' : 'bg-slate-900';
    
    return `
    <footer class="${bgClass} text-white py-12">
        <div class="max-w-7xl mx-auto px-4">
            
            <div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
                
                <!-- Logo & Açıklama -->
                <div class="col-span-2 md:col-span-1">
                    <div class="flex items-center gap-2 mb-4">
                        <img src="logo.png" alt="PA" class="w-8 h-8 rounded-lg">
                        <span class="font-bold text-lg">Platform<span class="text-blue-400">Avrupa</span></span>
                    </div>
                    <p class="text-slate-400 text-sm">Avrupa'daki Türk topluluğunun buluşma noktası.</p>
                </div>
                
                <!-- Hızlı Linkler -->
                <div>
                    <h4 class="font-bold mb-4 text-slate-300">Keşfet</h4>
                    <ul class="space-y-2 text-sm">
                        <li><a href="ilanlar.html" class="text-slate-400 hover:text-white transition">İlanlar</a></li>
                        <li><a href="firsatlar.html" class="text-orange-400 hover:text-orange-300 transition">🔥 Fırsatlar</a></li>
                        <li><a href="sila_yolu.html" class="text-slate-400 hover:text-white transition">Sıla Yolu</a></li>
                        <li><a href="market.html" class="text-slate-400 hover:text-white transition">Market</a></li>
                    </ul>
                </div>
                
                <!-- Kategoriler -->
                <div>
                    <h4 class="font-bold mb-4 text-slate-300">Kategoriler</h4>
                    <ul class="space-y-2 text-sm">
                        <li><a href="is_vitrini.html" class="text-slate-400 hover:text-white transition">İş İlanları</a></li>
                        <li><a href="emlak_vitrini.html" class="text-slate-400 hover:text-white transition">Emlak</a></li>
                        <li><a href="vasita_vitrini.html" class="text-slate-400 hover:text-white transition">Araç</a></li>
                        <li><a href="hizmet_vitrini.html" class="text-slate-400 hover:text-white transition">Hizmetler</a></li>
                    </ul>
                </div>
                
                <!-- Hesap -->
                <div>
                    <h4 class="font-bold mb-4 text-slate-300">Hesap</h4>
                    <ul class="space-y-2 text-sm">
                        <li><a href="profil.html" class="text-slate-400 hover:text-white transition">Profilim</a></li>
                        <li><a href="ilanlarim.html" class="text-slate-400 hover:text-white transition">İlanlarım</a></li>
                        <li><a href="favorilerim.html" class="text-slate-400 hover:text-white transition">Favorilerim</a></li>
                        <li><a href="ilan_giris.html" class="text-slate-400 hover:text-white transition">İlan Ver</a></li>
                    </ul>
                </div>
                
            </div>
            
            <!-- Alt Bölüm -->
            <div class="border-t border-white/10 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
                <p class="text-slate-500 text-sm">© 2026 PlatformAvrupa. Tüm hakları saklıdır.</p>
                <div class="flex items-center gap-4">
                    <a href="#" class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-slate-400 hover:bg-white/10 hover:text-white transition">
                        <i class="fa-brands fa-instagram"></i>
                    </a>
                    <a href="#" class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-slate-400 hover:bg-white/10 hover:text-white transition">
                        <i class="fa-brands fa-twitter"></i>
                    </a>
                    <a href="#" class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-slate-400 hover:bg-white/10 hover:text-white transition">
                        <i class="fa-brands fa-telegram"></i>
                    </a>
                </div>
            </div>
            
        </div>
    </footer>`;
}

// ============================================================================
// BOTTOM NAV (MOBİL)
// ============================================================================

/**
 * Mobil bottom navigation HTML'ini oluşturur
 * @param {string} activePage - Aktif sayfa adı
 */
function getBottomNavHTML(activePage = '') {
    const items = [
        { id: 'home', icon: 'fa-house', label: 'Ana Sayfa', href: 'index.html' },
        { id: 'ilanlar', icon: 'fa-list', label: 'İlanlar', href: 'ilanlar.html' },
        { id: 'ekle', icon: 'fa-plus', label: 'İlan Ver', href: 'ilan_giris.html', highlight: true },
        { id: 'sohbet', icon: 'fa-comments', label: 'Sohbet', href: 'sohbet.html' },
        { id: 'profil', icon: 'fa-user', label: 'Profil', href: 'profil.html' }
    ];
    
    return `
    <nav class="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 md:hidden z-50 pb-safe">
        <div class="flex items-center justify-around h-16">
            ${items.map(item => {
                const isActive = activePage === item.id;
                
                if (item.highlight) {
                    return `
                    <a href="${item.href}" class="flex flex-col items-center justify-center -mt-6">
                        <div class="w-14 h-14 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-300">
                            <i class="fa-solid ${item.icon} text-xl"></i>
                        </div>
                    </a>`;
                }
                
                return `
                <a href="${item.href}" class="flex flex-col items-center justify-center py-2 ${isActive ? 'text-blue-600' : 'text-slate-400'}">
                    <i class="fa-solid ${item.icon} text-lg"></i>
                    <span class="text-[10px] font-medium mt-1">${item.label}</span>
                </a>`;
            }).join('')}
        </div>
    </nav>`;
}

// ============================================================================
// TAİLWİND CONFIG
// ============================================================================

/**
 * Ortak Tailwind config'i döndürür
 */
function getTailwindConfig() {
    return {
        theme: {
            extend: {
                fontFamily: {
                    sans: ['Plus Jakarta Sans', 'Inter', 'sans-serif'],
                    display: ['Space Grotesk', 'sans-serif']
                },
                colors: {
                    primary: '#3b82f6',
                    secondary: '#0f172a'
                }
            }
        }
    };
}

// ============================================================================
// OTOMATİK YÜKLEME
// ============================================================================

/**
 * Sayfa yüklendiğinde bileşenleri otomatik yerleştirir
 */
function initComponents() {
    // Navbar container varsa navbar'ı yerleştir
    const navContainer = document.getElementById('navbar-container');
    if (navContainer) {
        const isDark = navContainer.dataset.dark === 'true';
        const isTransparent = navContainer.dataset.transparent === 'true';
        navContainer.innerHTML = getNavbarHTML({ dark: isDark, transparent: isTransparent });
    }
    
    // Footer container varsa footer'ı yerleştir
    const footerContainer = document.getElementById('footer-container');
    if (footerContainer) {
        const isDark = footerContainer.dataset.dark === 'true';
        footerContainer.innerHTML = getFooterHTML({ dark: isDark });
    }
    
    // Bottom nav container varsa yerleştir
    const bottomNavContainer = document.getElementById('bottom-nav-container');
    if (bottomNavContainer) {
        const activePage = bottomNavContainer.dataset.active || '';
        bottomNavContainer.innerHTML = getBottomNavHTML(activePage);
    }
    
    // Tailwind config uygula
    if (typeof tailwind !== 'undefined') {
        tailwind.config = getTailwindConfig();
    }
}

// DOM hazır olduğunda çalıştır
document.addEventListener('DOMContentLoaded', initComponents);

// ============================================================================
// GLOBAL EXPORTS
// ============================================================================

window.getNavbarHTML = getNavbarHTML;
window.getFooterHTML = getFooterHTML;
window.getBottomNavHTML = getBottomNavHTML;
window.getTailwindConfig = getTailwindConfig;
window.toggleMobileMenu = toggleMobileMenu;
window.initComponents = initComponents;

console.log('✅ Components.js yüklendi - UI bileşenleri hazır');
