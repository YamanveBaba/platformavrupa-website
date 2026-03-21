# Platform Avrupa – SEO Uygulama Notları

Bu dosya, yapılan SEO değişiklikleri ve sizin yapmanız gereken bir adımı özetler.

## Yapılanlar

- **robots.txt**: Oluşturuldu. Admin/video yönetimi sayfaları `Disallow` ile kapatıldı. Sitemap adresi eklendi.
- **sitemap.xml**: Tüm public sayfalar eklendi. `https://www.platformavrupa.com/sitemap.xml` üzerinden erişilebilir.
- **Canonical URL**: Tüm public HTML sayfalarına `<link rel="canonical" href="https://www.platformavrupa.com/...">` eklendi.
- **Meta description**: Ana sayfa ve modül sayfalarına benzersiz, 150–160 karakterlik açıklamalar eklendi.
- **Open Graph ve Twitter Card**: Tüm public sayfalara `og:title`, `og:description`, `og:url`, `og:image`, `og:locale` ve Twitter card meta etiketleri eklendi.
- **JSON-LD**: 
  - Ana sayfa: `WebSite` + `Organization`
  - Duyuru detay: `Article`
  - Akademi video: `VideoObject`
- **netlify.toml**: Tüm istekleri `index.html`e yönlendiren redirect kaldırıldı; her `.html` dosyası doğrudan sunuluyor (SEO ve doğrudan linkler için).

## Sizin Yapmanız Gereken

### 1. Paylaşım görseli (og-image.png)

Tüm sayfalarda paylaşım görseli olarak `https://www.platformavrupa.com/og-image.png` kullanılıyor. Bu dosyayı **proje köküne** eklemeniz gerekir.

- **Önerilen boyut:** 1200 x 630 piksel
- **İçerik:** Logo + kısa metin (örn. "Platform Avrupa – Avrupa'daki Türklerin Buluşma Noktası")
- **Format:** PNG veya JPG

Dosyayı eklemeden önce meta etiketleri yine çalışır; sosyal ağlar varsayılan veya boş görsel gösterebilir. `og-image.png` ekledikten sonra paylaşımlarda bu görsel kullanılır.

### 2. Google Search Console ve Bing

- [Google Search Console](https://search.google.com/search-console): Siteyi ekleyin, `sitemap.xml` adresini gönderin.
- [Bing Webmaster Tools](https://www.bing.com/webmasters): İsteğe bağlı; sitemap ekleyebilirsiniz.

Bu adımlardan sonra indexleme ve sorgu raporlarını bu araçlardan takip edebilirsiniz.
