/* --------------------------------------------------------------------------
   PLATFORM AVRUPA - FAVORITES.JS (Favori Sistemi)
   Versiyon: 1.0
   Açıklama: İlan favorileme, çıkarma ve listeleme fonksiyonları
   
   Kullanım:
   1. HTML'de önce Supabase, config.js, utils.js, auth.js yükleyin
   2. Sonra favorites.js'i yükleyin
   3. <script src="favorites.js"></script>
   
   NOT: Bu sistem supabase_rls_policies.sql'de oluşturulan 'favorites' tablosunu kullanır.
-------------------------------------------------------------------------- */

// ============================================================================
// FAVORİ İŞLEMLERİ
// ============================================================================

/**
 * İlanı favorilere ekler
 * @param {string} ilanId - İlan ID'si
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function favoriEkle(ilanId) {
    if (!sb) return { success: false, error: 'Bağlantı hatası' };
    
    const user = await getCurrentUser();
    if (!user) {
        return { success: false, error: 'Giriş yapmalısınız' };
    }
    
    try {
        const { error } = await sb.from('favorites').insert([{
            user_id: user.id,
            ilan_id: ilanId
        }]);
        
        if (error) {
            // Duplicate key hatası - zaten favorilerde
            if (error.code === '23505') {
                return { success: false, error: 'Zaten favorilerinizde' };
            }
            throw error;
        }
        
        console.log('✅ Favorilere eklendi:', ilanId);
        return { success: true };
        
    } catch (error) {
        console.error('Favori ekleme hatası:', error);
        return { success: false, error: error.message };
    }
}

/**
 * İlanı favorilerden çıkarır
 * @param {string} ilanId - İlan ID'si
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function favoriCikar(ilanId) {
    if (!sb) return { success: false, error: 'Bağlantı hatası' };
    
    const user = await getCurrentUser();
    if (!user) {
        return { success: false, error: 'Giriş yapmalısınız' };
    }
    
    try {
        const { error } = await sb.from('favorites')
            .delete()
            .eq('user_id', user.id)
            .eq('ilan_id', ilanId);
        
        if (error) throw error;
        
        console.log('✅ Favorilerden çıkarıldı:', ilanId);
        return { success: true };
        
    } catch (error) {
        console.error('Favori çıkarma hatası:', error);
        return { success: false, error: error.message };
    }
}

/**
 * Favori durumunu değiştirir (ekle/çıkar toggle)
 * @param {string} ilanId - İlan ID'si
 * @param {HTMLElement} buttonElement - Güncellencek buton elementi
 * @returns {Promise<boolean>} - Yeni durum (true = favorilerde, false = değil)
 */
async function favoriToggle(ilanId, buttonElement = null) {
    const isFav = await favorideMi(ilanId);
    
    if (isFav) {
        const result = await favoriCikar(ilanId);
        if (result.success && buttonElement) {
            buttonElement.innerHTML = '<i class="fa-regular fa-heart"></i>';
            buttonElement.classList.remove('text-red-500');
            buttonElement.classList.add('text-slate-400');
            buttonElement.title = 'Favorilere Ekle';
        }
        return !result.success; // Başarılıysa false döner (artık favoride değil)
    } else {
        const result = await favoriEkle(ilanId);
        if (result.success && buttonElement) {
            buttonElement.innerHTML = '<i class="fa-solid fa-heart"></i>';
            buttonElement.classList.remove('text-slate-400');
            buttonElement.classList.add('text-red-500');
            buttonElement.title = 'Favorilerden Çıkar';
        } else if (!result.success && result.error === 'Giriş yapmalısınız') {
            alert('Favorilere eklemek için giriş yapmalısınız.');
            window.location.href = 'login.html';
        }
        return result.success; // Başarılıysa true döner (favoride)
    }
}

/**
 * İlanın favorilerde olup olmadığını kontrol eder
 * @param {string} ilanId - İlan ID'si
 * @returns {Promise<boolean>}
 */
async function favorideMi(ilanId) {
    if (!sb) return false;
    
    const user = await getCurrentUser();
    if (!user) return false;
    
    try {
        const { data, error } = await sb.from('favorites')
            .select('id')
            .eq('user_id', user.id)
            .eq('ilan_id', ilanId)
            .single();
        
        return !error && data !== null;
        
    } catch (error) {
        return false;
    }
}

/**
 * Kullanıcının tüm favorilerini getirir
 * @returns {Promise<Array>} - Favori ilan ID'leri dizisi
 */
async function favorileriGetir() {
    if (!sb) return [];
    
    const user = await getCurrentUser();
    if (!user) return [];
    
    try {
        const { data, error } = await sb.from('favorites')
            .select('ilan_id')
            .eq('user_id', user.id)
            .order('created_at', { ascending: false });
        
        if (error) throw error;
        
        return data ? data.map(f => f.ilan_id) : [];
        
    } catch (error) {
        console.error('Favoriler getirme hatası:', error);
        return [];
    }
}

/**
 * Kullanıcının favori ilanlarını detaylı getirir
 * @returns {Promise<Array>} - İlan detayları dizisi
 */
async function favoriIlanlariGetir() {
    if (!sb) return [];
    
    const user = await getCurrentUser();
    if (!user) return [];
    
    try {
        // Önce favori ID'lerini al
        const { data: favs, error: favError } = await sb.from('favorites')
            .select('ilan_id')
            .eq('user_id', user.id)
            .order('created_at', { ascending: false });
        
        if (favError) throw favError;
        if (!favs || favs.length === 0) return [];
        
        // Sonra ilanları getir
        const ilanIds = favs.map(f => f.ilan_id);
        const { data: ilanlar, error: ilanError } = await sb.from('ilanlar')
            .select('*')
            .in('id', ilanIds);
        
        if (ilanError) throw ilanError;
        
        return ilanlar || [];
        
    } catch (error) {
        console.error('Favori ilanları getirme hatası:', error);
        return [];
    }
}

/**
 * Favori sayısını getirir
 * @returns {Promise<number>}
 */
async function favoriSayisi() {
    if (!sb) return 0;
    
    const user = await getCurrentUser();
    if (!user) return 0;
    
    try {
        const { count, error } = await sb.from('favorites')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', user.id);
        
        if (error) throw error;
        
        return count || 0;
        
    } catch (error) {
        return 0;
    }
}

// ============================================================================
// FAVORİ BUTON OLUŞTURMA
// ============================================================================

/**
 * Favori buton HTML'i oluşturur
 * @param {string} ilanId - İlan ID'si
 * @param {boolean} isFavorite - Şu an favoride mi
 * @param {string} size - Buton boyutu ('sm', 'md', 'lg')
 * @returns {string} - HTML string
 */
function favoriButonHTML(ilanId, isFavorite = false, size = 'md') {
    const sizeClasses = {
        sm: 'w-6 h-6 text-sm',
        md: 'w-8 h-8 text-base',
        lg: 'w-10 h-10 text-lg'
    };
    
    const iconClass = isFavorite ? 'fa-solid fa-heart' : 'fa-regular fa-heart';
    const colorClass = isFavorite ? 'text-red-500' : 'text-slate-400 hover:text-red-400';
    const title = isFavorite ? 'Favorilerden Çıkar' : 'Favorilere Ekle';
    
    return `
        <button 
            onclick="favoriToggle('${sanitize(ilanId)}', this); event.stopPropagation(); event.preventDefault();" 
            class="fav-btn ${sizeClasses[size]} rounded-full bg-white/90 backdrop-blur shadow flex items-center justify-center ${colorClass} transition hover:scale-110"
            title="${title}"
            data-ilan-id="${sanitize(ilanId)}"
        >
            <i class="${iconClass}"></i>
        </button>`;
}

/**
 * Sayfadaki tüm favori butonlarını günceller
 * @param {Array} favoriIds - Favori ilan ID'leri
 */
function favoriBuronlariGuncelle(favoriIds = []) {
    document.querySelectorAll('.fav-btn').forEach(btn => {
        const ilanId = btn.dataset.ilanId;
        const isFav = favoriIds.includes(ilanId);
        
        if (isFav) {
            btn.innerHTML = '<i class="fa-solid fa-heart"></i>';
            btn.classList.add('text-red-500');
            btn.classList.remove('text-slate-400');
            btn.title = 'Favorilerden Çıkar';
        } else {
            btn.innerHTML = '<i class="fa-regular fa-heart"></i>';
            btn.classList.remove('text-red-500');
            btn.classList.add('text-slate-400');
            btn.title = 'Favorilere Ekle';
        }
    });
}

// ============================================================================
// GLOBAL EXPORTS
// ============================================================================

window.favoriEkle = favoriEkle;
window.favoriCikar = favoriCikar;
window.favoriToggle = favoriToggle;
window.favorideMi = favorideMi;
window.favorileriGetir = favorileriGetir;
window.favoriIlanlariGetir = favoriIlanlariGetir;
window.favoriSayisi = favoriSayisi;
window.favoriButonHTML = favoriButonHTML;
window.favoriBuronlariGuncelle = favoriBuronlariGuncelle;

console.log('✅ Favorites.js yüklendi - Favori sistemi aktif');
