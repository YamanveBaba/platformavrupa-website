# platformavrupa.com – Netlify’a Bu Projeden Deploy

> **Güncel (2026-02):** Canlı site **Cloudflare Pages** (`platformavrupa-website`) ve DNS **Cloudflare** üzerinden yayınlanıyor olabilir. Bu dosya **Netlify** kullananlar için arşiv rehberidir. Yeni kurulum için önce `PLATFORMAVRUPA_PROJE_DOKUMANTASYONU.md` → **Deployment** bölümüne bakın.

Bu klasör **Platform Avrupa** statik sitesidir. platformavrupa.com’un WorldMonitor yerine bu projeyi göstermesi için aşağıdakileri uygula.

---

## 1. GitHub’a gönder

1. GitHub’da yeni bir repo oluştur (örn. `platformavrupa-website` veya `platformavrupa`). **worldmonitor** adını kullanma.
2. Bu klasörde terminal açıp:

```bash
git add .
git commit -m "Platform Avrupa statik site - Netlify deploy için"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADIN/repo_adi.git
git push -u origin main
```

`KULLANICI_ADIN` ve `repo_adi` yerine kendi GitHub kullanıcı adın ve repo adını yaz.

---

## 2. Netlify’da site kaynağını değiştir

1. [app.netlify.com](https://app.netlify.com) → platformavrupa.com için kullandığın **site’ı** aç.
2. **Site configuration** (veya **Site settings**) → **Build & deploy** → **Continuous deployment**.
3. **Link repository** / **Change repository** / **Connect to different repo** ile **worldmonitor** bağlantısını kaldır.
4. **Yeni oluşturduğun repo**yu seç (bu klasörün push edildiği repo). Branch: `main`.
5. Build settings’te **netlify.toml kullan** seçili olsun (build command yok, publish = `"."`).
6. **Save** → **Trigger deploy** → **Deploy project without cache**.

---

## 3. Kontrol

- Birkaç dakika sonra platformavrupa.com’u aç (sert yenile: Ctrl+Shift+R veya gizli pencere).
- Başlık: **PlatformAvrupa | Dijital Yol Arkadaşınız** ve içerik tamamen Platform Avrupa olmalı; MONITOR / WorldMonitor görünmemeli.

---

## Notlar

- **netlify.toml** bu klasörde; statik site için ayarlı (`publish = "."`, build yok).
- Domain (platformavrupa.com) zaten Netlify’a bağlıysa DNS’e dokunmana gerek yok; sadece hangi reponun deploy edildiğini değiştiriyorsun.
- İleride güncelleme: Bu klasörde değişiklik yap → `git add .` → `git commit -m "..."` → `git push` → Netlify otomatik deploy alır.
