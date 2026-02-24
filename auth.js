/* --------------------------------------------------------------------------
   PLATFORM AVRUPA - AUTH.JS (Merkezi Kimlik Doğrulama Modülü)
   Versiyon: 1.0
   Açıklama: Tüm sayfalarda kullanılacak merkezi auth yönetimi
   
   Kullanım:
   1. HTML'de önce Supabase, sonra config.js, sonra auth.js yükleyin
   2. <script src="https://unpkg.com/@supabase/supabase-js@2"></script>
   3. <script src="config.js"></script>
   4. <script src="auth.js"></script>
-------------------------------------------------------------------------- */

// ============================================================================
// GLOBAL DEĞİŞKENLER
// ============================================================================

let currentUser = null;      // Supabase auth user
let currentProfile = null;   // Profiles tablosundan gelen profil

// ============================================================================
// ANA AUTH FONKSİYONLARI
// ============================================================================

/**
 * Auth sistemini başlatır - sayfa yüklendiğinde otomatik çağrılır
 */
async function initAuth() {
    if (!sb) {
        console.error('❌ Auth.js: Supabase bağlantısı yok!');
        return;
    }
    
    try {
        // 1. Mevcut session'ı kontrol et
        const { data: { session }, error } = await sb.auth.getSession();
        
        if (session && session.user) {
            currentUser = session.user;
            
            // 2. Profil bilgilerini çek
            const { data: profile } = await sb.from('profiles')
                .select('*')
                .eq('id', session.user.id)
                .single();
            
            if (profile) {
                currentProfile = profile;
                
                // localStorage'ı güncelle (geriye uyumluluk için)
                localStorage.setItem('isLoggedIn', 'true');
                localStorage.setItem('userEmail', profile.email || '');
                localStorage.setItem('userName', profile.full_name || '');
                localStorage.setItem('userRealName', profile.real_name || '');
                localStorage.setItem('userCity', profile.city || '');
                localStorage.setItem('userCountry', profile.country || '');
                localStorage.setItem('userPhone', profile.phone || '');
                localStorage.setItem('userLocation', profile.city || '');
            }
        } else {
            // Session yok - temizle
            currentUser = null;
            currentProfile = null;
        }
        
        // 3. UI'ı güncelle
        updateAuthUI();
        
        // 4. Auth değişikliklerini dinle
        sb.auth.onAuthStateChange(handleAuthChange);
        
        console.log('✅ Auth.js: Başlatıldı', currentUser ? `(${currentProfile?.full_name})` : '(Misafir)');
        
    } catch (error) {
        console.error('❌ Auth.js başlatma hatası:', error);
    }
}

/**
 * Auth durumu değiştiğinde çağrılır
 */
async function handleAuthChange(event, session) {
    console.log('🔄 Auth değişikliği:', event);
    
    if (event === 'SIGNED_IN' && session) {
        currentUser = session.user;
        
        // Profil bilgilerini çek
        let { data: profile } = await sb.from('profiles')
            .select('*')
            .eq('id', session.user.id)
            .single();
        
        // Google ile giriş yapıldıysa ve profil yoksa oluştur
        if (!profile && session.user.app_metadata?.provider === 'google') {
            const fullName = session.user.user_metadata?.full_name || 
                           session.user.user_metadata?.name || 
                           session.user.email.split('@')[0];
            
            const { data: newProfile } = await sb.from('profiles').insert([{
                id: session.user.id,
                email: session.user.email,
                full_name: fullName,
                real_name: fullName,
                phone_verified: false,
                verified_at: new Date().toISOString(),
                verification_method: 'google',
                role: 'user',
                status: 'active'
            }]).select().single();
            
            profile = newProfile;
        } else if (profile && session.user.app_metadata?.provider === 'google') {
            // Google ile giriş yapıldıysa verification_method'u güncelle
            if (!profile.verification_method || profile.verification_method !== 'google') {
                await sb.from('profiles').update({
                    verification_method: 'google',
                    verified_at: new Date().toISOString()
                }).eq('id', session.user.id);
                
                profile.verification_method = 'google';
                profile.verified_at = new Date().toISOString();
            }
        }
        
        currentProfile = profile;
        updateAuthUI();
        
    } else if (event === 'SIGNED_OUT') {
        currentUser = null;
        currentProfile = null;
        localStorage.clear();
        updateAuthUI();
    }
}

/**
 * UI'daki auth alanlarını günceller
 */
function updateAuthUI() {
    const authButtons = document.getElementById('authButtons');
    if (!authButtons) return;
    
    if (currentProfile) {
        const displayName = currentProfile.full_name || 'Kullanıcı';
        const initials = displayName.substring(0, 2).toUpperCase();
        const avatarUrl = currentProfile.avatar_url || 
            `https://ui-avatars.com/api/?name=${encodeURIComponent(displayName)}&background=4f46e5&color=fff`;
        
        authButtons.innerHTML = `
            <div class="flex items-center gap-3">
                <a href="profil.html" class="flex items-center gap-2 hover:opacity-80 transition">
                    <img src="${avatarUrl}" alt="${sanitize(displayName)}" class="w-8 h-8 rounded-full border border-white/20">
                    <span class="text-white font-bold text-sm hidden md:block">${sanitize(displayName)}</span>
                </a>
                <button onclick="signOut()" class="text-red-400 text-xs hover:text-red-300 ml-2" title="Çıkış Yap">
                    <i class="fa-solid fa-right-from-bracket"></i>
                </button>
            </div>`;
    } else {
        authButtons.innerHTML = `
            <a href="login.html" class="text-sm font-bold text-white hover:text-indigo-400 transition">Giriş Yap</a>`;
    }
    
    // Özel auth-check elementlerini güncelle
    document.querySelectorAll('[data-auth-show]').forEach(el => {
        const showFor = el.dataset.authShow;
        if (showFor === 'logged-in' && currentUser) {
            el.style.display = '';
        } else if (showFor === 'logged-out' && !currentUser) {
            el.style.display = '';
        } else {
            el.style.display = 'none';
        }
    });
}

// ============================================================================
// AUTH İŞLEMLERİ
// ============================================================================

/**
 * Email ve şifre ile giriş yapar
 * @param {string} email 
 * @param {string} password 
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function signInWithEmail(email, password) {
    if (!sb) return { success: false, error: 'Bağlantı hatası' };
    
    try {
        const { data, error } = await sb.auth.signInWithPassword({
            email: email,
            password: password
        });
        
        if (error) throw error;
        
        return { success: true, user: data.user };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

/**
 * Google ile giriş yapar
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function signInWithGoogle() {
    if (!sb) return { success: false, error: 'Bağlantı hatası' };
    
    try {
        const { data, error } = await sb.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: window.location.origin + '/index.html'
            }
        });
        
        if (error) throw error;
        
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

/**
 * Yeni kullanıcı kaydı yapar
 * @param {string} email 
 * @param {string} password 
 * @param {object} profileData - Profil bilgileri
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function signUp(email, password, profileData = {}) {
    if (!sb) return { success: false, error: 'Bağlantı hatası' };
    
    try {
        // 1. Kullanıcı oluştur
        const { data, error } = await sb.auth.signUp({
            email: email,
            password: password
        });
        
        if (error) throw error;
        
        if (data.user) {
            // 2. Profil oluştur
            const { error: profileError } = await sb.from('profiles').insert([{
                id: data.user.id,
                email: email,
                full_name: profileData.full_name || '',
                real_name: profileData.real_name || '',
                country: profileData.country || '',
                city: profileData.city || '',
                phone: profileData.phone || '',
                role: 'user',
                status: 'active'
            }]);
            
            if (profileError) {
                console.error('Profil oluşturma hatası:', profileError);
            }
        }
        
        return { success: true, user: data.user };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

/**
 * Çıkış yapar
 */
async function signOut() {
    if (!sb) return;
    
    try {
        await sb.auth.signOut();
        localStorage.clear();
        currentUser = null;
        currentProfile = null;
        window.location.href = 'index.html';
    } catch (error) {
        console.error('Çıkış hatası:', error);
    }
}

/**
 * Şifre sıfırlama emaili gönderir
 * @param {string} email 
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function resetPassword(email) {
    if (!sb) return { success: false, error: 'Bağlantı hatası' };
    
    try {
        const { error } = await sb.auth.resetPasswordForEmail(email, {
            redirectTo: window.location.origin + '/sifre_yenile.html'
        });
        
        if (error) throw error;
        
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// ============================================================================
// KORUMA FONKSİYONLARI
// ============================================================================

/**
 * Giriş yapmış kullanıcı gerektirir - değilse login'e yönlendirir
 * @param {string} redirectUrl - Giriş sonrası dönülecek URL
 * @returns {boolean}
 */
function requireAuth(redirectUrl = null) {
    if (!currentUser) {
        const returnUrl = redirectUrl || window.location.href;
        localStorage.setItem('authRedirect', returnUrl);
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

/**
 * Kullanıcının belirli bir role sahip olup olmadığını kontrol eder
 * @param {string|string[]} roles - İzin verilen roller
 * @returns {boolean}
 */
function hasRole(roles) {
    if (!currentProfile) return false;
    
    if (Array.isArray(roles)) {
        return roles.includes(currentProfile.role);
    }
    return currentProfile.role === roles;
}

/**
 * Belirli bir koşul sağlanmazsa yönlendirir
 * @param {boolean} condition 
 * @param {string} redirectUrl 
 */
function requireCondition(condition, redirectUrl = 'index.html') {
    if (!condition) {
        window.location.href = redirectUrl;
        return false;
    }
    return true;
}

// ============================================================================
// YARDIMCI FONKSİYONLAR
// ============================================================================

/**
 * Giriş yapılıp yapılmadığını kontrol eder
 * @returns {boolean}
 */
function isLoggedIn() {
    return currentUser !== null;
}

/**
 * Mevcut kullanıcıyı döndürür
 * @returns {object|null}
 */
function getUser() {
    return currentUser;
}

/**
 * Mevcut profili döndürür
 * @returns {object|null}
 */
function getProfile() {
    return currentProfile;
}

/**
 * Kullanıcı ID'sini döndürür
 * @returns {string|null}
 */
function getUserId() {
    return currentUser?.id || null;
}

/**
 * Mevcut kullanıcıyı döndürür (async wrapper - geriye uyumluluk için)
 * @returns {Promise<object|null>}
 */
async function getCurrentUser() {
    // Eğer auth henüz başlatılmadıysa bekle
    if (!sb) {
        console.error('❌ Supabase bağlantısı yok!');
        return null;
    }
    
    // Mevcut session'ı kontrol et
    try {
        const { data: { session }, error } = await sb.auth.getSession();
        if (error) throw error;
        return session?.user || null;
    } catch (error) {
        console.error('❌ Kullanıcı bilgisi alınamadı:', error);
        return null;
    }
}

// ============================================================================
// SAYFA YÜKLENDİĞİNDE BAŞLAT
// ============================================================================

document.addEventListener('DOMContentLoaded', initAuth);

// ============================================================================
// GLOBAL EXPORTS
// ============================================================================

window.currentUser = currentUser;
window.currentProfile = currentProfile;
window.initAuth = initAuth;
window.signInWithEmail = signInWithEmail;
window.signInWithGoogle = signInWithGoogle;
window.signUp = signUp;
window.signOut = signOut;
window.resetPassword = resetPassword;
window.requireAuth = requireAuth;
window.hasRole = hasRole;
window.isLoggedIn = isLoggedIn;
window.getUser = getUser;
window.getCurrentUser = getCurrentUser;
window.getProfile = getProfile;
window.getUserId = getUserId;

console.log('✅ Auth.js yüklendi');
