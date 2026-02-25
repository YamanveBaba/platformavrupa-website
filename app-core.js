/* --------------------------------------------------------------------------
   PLATFORM AVRUPA - APP-CORE.JS (Uygulama Çekirdeği)
   Versiyon: 1.0
   Açıklama: SPA benzeri yapı ve native mobil geçiş için temel altyapı
   
   Bu dosya şunları sağlar:
   - Basit client-side routing
   - Sayfa geçişleri için preloading
   - Capacitor/Cordova ile uyumluluk
   - PWA desteği
   
   Native Mobil Dönüşüm Notları:
   - Bu yapı Capacitor ile wrapper olarak kullanılabilir
   - Tüm API çağrıları merkezi auth.js ve config.js üzerinden yapılmalı
   - Offline desteği için service-worker.js kullanılıyor
-------------------------------------------------------------------------- */

// ============================================================================
// PLATFORM BİLGİSİ
// ============================================================================

const Platform = {
    // Çalışma ortamını tespit et
    isWeb: typeof window !== 'undefined' && !window.Capacitor,
    isCapacitor: typeof window !== 'undefined' && window.Capacitor,
    isCordova: typeof window !== 'undefined' && window.cordova,
    isNative: false,
    
    // Cihaz bilgisi
    isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent),
    isAndroid: /Android/.test(navigator.userAgent),
    isMobile: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
    
    // Ekran bilgisi
    isSmallScreen: window.innerWidth < 768,
    
    // Platform başlatma
    async init() {
        this.isNative = this.isCapacitor || this.isCordova;
        
        // Capacitor eklentilerini yükle
        if (this.isCapacitor && window.Capacitor.Plugins) {
            this.plugins = window.Capacitor.Plugins;
        }
        
        console.log('📱 Platform:', this.isNative ? 'Native' : 'Web', 
                    '| Mobil:', this.isMobile, 
                    '| OS:', this.isIOS ? 'iOS' : (this.isAndroid ? 'Android' : 'Other'));
        
        return this;
    }
};

// ============================================================================
// BASİT ROUTER (NATIVE HAZIRLIK)
// ============================================================================

const Router = {
    currentPage: null,
    history: [],
    
    // Sayfa navigasyonu
    async navigate(url, options = {}) {
        const { replace = false, data = null } = options;
        
        // Native'de farklı davranış olabilir
        if (Platform.isNative && Platform.plugins?.App) {
            // Native navigation kullanılabilir
        }
        
        // Web için standart navigasyon
        if (replace) {
            window.location.replace(url);
        } else {
            window.location.href = url;
        }
    },
    
    // Geri git
    back() {
        if (this.history.length > 1) {
            this.history.pop();
            const prevPage = this.history[this.history.length - 1];
            this.navigate(prevPage, { replace: true });
        } else {
            window.history.back();
        }
    },
    
    // Mevcut sayfayı kaydet
    trackPage() {
        this.currentPage = window.location.pathname;
        this.history.push(this.currentPage);
        
        // Max 20 sayfa tut
        if (this.history.length > 20) {
            this.history.shift();
        }
    }
};

// ============================================================================
// OFFLINE DESTEK
// ============================================================================

const OfflineManager = {
    isOnline: navigator.onLine,
    
    init() {
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
        
        // Başlangıç durumunu kontrol et
        if (!this.isOnline) {
            this.showOfflineBar();
        }
    },
    
    handleOnline() {
        this.isOnline = true;
        this.hideOfflineBar();
        console.log('📶 Çevrimiçi');
        
        // Bekleyen işlemleri senkronize et
        this.syncPendingActions();
    },
    
    handleOffline() {
        this.isOnline = false;
        this.showOfflineBar();
        console.log('📴 Çevrimdışı');
    },
    
    showOfflineBar() {
        if (document.getElementById('offline-bar')) return;
        
        const bar = document.createElement('div');
        bar.id = 'offline-bar';
        bar.className = 'fixed top-0 left-0 right-0 bg-amber-500 text-white text-center py-2 text-sm font-bold z-[9999]';
        bar.innerHTML = '<i class="fa-solid fa-wifi-slash mr-2"></i> İnternet bağlantınız yok';
        document.body.prepend(bar);
        
        // Navbar'ı aşağı it
        document.body.style.marginTop = '40px';
    },
    
    hideOfflineBar() {
        const bar = document.getElementById('offline-bar');
        if (bar) {
            bar.remove();
            document.body.style.marginTop = '0';
        }
    },
    
    // Bekleyen işlemleri senkronize et
    async syncPendingActions() {
        const pending = JSON.parse(localStorage.getItem('pendingActions') || '[]');
        
        if (pending.length === 0) return;
        
        console.log(`🔄 ${pending.length} bekleyen işlem senkronize ediliyor...`);
        
        for (const action of pending) {
            try {
                // İşlemi yeniden dene
                if (action.type === 'insert') {
                    await sb.from(action.table).insert(action.data);
                } else if (action.type === 'update') {
                    await sb.from(action.table).update(action.data).eq('id', action.id);
                } else if (action.type === 'delete') {
                    await sb.from(action.table).delete().eq('id', action.id);
                }
            } catch (error) {
                console.error('Senkronizasyon hatası:', error);
            }
        }
        
        // Temizle
        localStorage.removeItem('pendingActions');
    },
    
    // Offline'da işlem kaydet
    queueAction(action) {
        const pending = JSON.parse(localStorage.getItem('pendingActions') || '[]');
        pending.push({ ...action, timestamp: Date.now() });
        localStorage.setItem('pendingActions', JSON.stringify(pending));
    }
};

// ============================================================================
// PUSH NOTIFICATIONS (NATIVE)
// ============================================================================

const NotificationManager = {
    hasPermission: false,
    
    async init() {
        // Web Push için izin iste
        if ('Notification' in window && !Platform.isNative) {
            if (Notification.permission === 'granted') {
                this.hasPermission = true;
            } else if (Notification.permission !== 'denied') {
                // İzin iste (kullanıcı etkileşimi gerektirir)
            }
        }
        
        // Capacitor Push Notifications
        if (Platform.isNative && Platform.plugins?.PushNotifications) {
            await this.initNativePush();
        }
    },
    
    async initNativePush() {
        const { PushNotifications } = Platform.plugins;
        
        // İzin iste
        const result = await PushNotifications.requestPermissions();
        
        if (result.receive === 'granted') {
            await PushNotifications.register();
            this.hasPermission = true;
            
            // Token al
            PushNotifications.addListener('registration', (token) => {
                console.log('📱 Push token:', token.value);
                // Token'ı sunucuya kaydet
                this.saveToken(token.value);
            });
            
            // Bildirim geldiğinde
            PushNotifications.addListener('pushNotificationReceived', (notification) => {
                console.log('🔔 Bildirim:', notification);
            });
        }
    },
    
    async saveToken(token) {
        const user = await getCurrentUser();
        if (user && sb) {
            await sb.from('profiles').update({ push_token: token }).eq('id', user.id);
        }
    },
    
    // Lokal bildirim göster
    async showLocal(title, body, data = {}) {
        if (Platform.isNative && Platform.plugins?.LocalNotifications) {
            await Platform.plugins.LocalNotifications.schedule({
                notifications: [{
                    title,
                    body,
                    id: Date.now(),
                    extra: data
                }]
            });
        } else if (this.hasPermission && !Platform.isNative) {
            new Notification(title, { body, icon: 'logo.png' });
        }
    }
};

// ============================================================================
// UYGULAMA YAŞAM DÖNGÜSÜ
// ============================================================================

const AppLifecycle = {
    init() {
        // Sayfa görünürlük değişikliği
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.onPause();
            } else {
                this.onResume();
            }
        });
        
        // Capacitor yaşam döngüsü
        if (Platform.isNative && Platform.plugins?.App) {
            Platform.plugins.App.addListener('appStateChange', ({ isActive }) => {
                if (isActive) {
                    this.onResume();
                } else {
                    this.onPause();
                }
            });
            
            // Geri tuşu (Android)
            Platform.plugins.App.addListener('backButton', () => {
                if (Router.history.length > 1) {
                    Router.back();
                } else {
                    Platform.plugins.App.exitApp();
                }
            });
        }
    },
    
    onPause() {
        console.log('⏸️ Uygulama arka plana alındı');
        // Verileri kaydet
        localStorage.setItem('lastActive', Date.now().toString());
    },
    
    onResume() {
        console.log('▶️ Uygulama ön plana geldi');
        
        // Session kontrolü
        const lastActive = parseInt(localStorage.getItem('lastActive') || '0');
        const inactiveTime = Date.now() - lastActive;
        
        // 30 dakikadan fazla inaktifse session yenile
        if (inactiveTime > 30 * 60 * 1000 && typeof initAuth === 'function') {
            initAuth();
        }
    }
};

// ============================================================================
// DEEPLİNK DESTEK
// ============================================================================

const DeepLinkHandler = {
    init() {
        // Web URL parametrelerini işle
        this.handleWebParams();
        
        // Capacitor deep links
        if (Platform.isNative && Platform.plugins?.App) {
            Platform.plugins.App.addListener('appUrlOpen', (data) => {
                this.handleDeepLink(data.url);
            });
        }
    },
    
    handleWebParams() {
        const params = new URLSearchParams(window.location.search);
        
        // Örnek: ?ilan=123 -> ilan detay sayfasına yönlendir
        if (params.has('ilan')) {
            const ilanId = params.get('ilan');
            if (window.location.pathname !== '/ilan_detay.html') {
                Router.navigate(`ilan_detay.html?id=${ilanId}`);
            }
        }
    },
    
    handleDeepLink(url) {
        console.log('🔗 Deep link:', url);
        
        // URL'i parse et
        const parsedUrl = new URL(url);
        const path = parsedUrl.pathname;
        
        // Yönlendirme kuralları
        if (path.includes('/ilan/')) {
            const ilanId = path.split('/ilan/')[1];
            Router.navigate(`ilan_detay.html?id=${ilanId}`);
        } else if (path.includes('/profil/')) {
            const userId = path.split('/profil/')[1];
            Router.navigate(`profil.html?id=${userId}`);
        }
    }
};

// ============================================================================
// ANA UYGULAMA BAŞLATICI
// ============================================================================

const App = {
    version: '1.0.0',
    
    async init() {
        console.log('🚀 Platform Avrupa v' + this.version + ' başlatılıyor...');
        
        // Platform bilgisini al
        await Platform.init();
        
        // Router'ı başlat
        Router.trackPage();
        
        // Offline yönetimini başlat
        OfflineManager.init();
        
        // Yaşam döngüsünü başlat
        AppLifecycle.init();
        
        // Deep link desteğini başlat
        DeepLinkHandler.init();
        
        // Bildirim sistemini başlat (opsiyonel)
        // await NotificationManager.init();
        
        console.log('✅ Uygulama hazır');
        
        return this;
    }
};

// ============================================================================
// GLOBAL EXPORTS
// ============================================================================

window.Platform = Platform;
window.Router = Router;
window.OfflineManager = OfflineManager;
window.NotificationManager = NotificationManager;
window.AppLifecycle = AppLifecycle;
window.DeepLinkHandler = DeepLinkHandler;
window.App = App;

// Otomatik başlat
document.addEventListener('DOMContentLoaded', () => App.init());

console.log('✅ App-core.js yüklendi - Native mobil altyapısı hazır');
