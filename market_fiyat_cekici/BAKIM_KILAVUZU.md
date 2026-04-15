# Bakım Kılavuzu — Market Fiyat Çekici

Son güncelleme: 2026-04-12

---

## Her Hafta Çalıştır

```
python haftalik_tam.py
```

Hepsi bu. Script kendisi:
- Her marketi sırayla çeker
- Başarısız olursa 1 kez retry yapar
- Timeout'ta takılmaz (Delhaize 4 saat, diğerleri 30-90 dk)
- Sonunda özet rapor gösterir

---

## Sorun → Çözüm

### Lidl: "Cookie süresi dolmuş" uyarısı

**Belirti:** `haftalik_tam.py` çıktısında sarı uyarı, Lidl ürün sayısı 0

**Çözüm (2 dk):**
1. Chrome'da `lidl.be` aç
2. F12 → Network sekmesi
3. Herhangi bir ürün sayfasına git
4. Network'te `/q/api/search` isteğini bul
5. Request Headers → `Cookie` değerinin tamamını kopyala
6. `lidl_cookie.txt` dosyasına yapıştır (# satırlarını sil)

**Ne zaman?** Ayda 1 kez gerekiyor.

---

### Colruyt: Az ürün geliyor (8000'den az)

**Belirti:** Script çalışıyor ama 1000-2000 ürün civarında bitiyor

**Çözüm:**
```
python colruyt_cookie_yenile.py   # reese84 cookie tazele
python colruyt_direct.py          # tekrar dene
```

**Kök neden:** reese84 anti-bot cookie'si sürüyor. `colruyt_cookie_yenile.py` Chrome'u açıp otomatik yeniliyor.

---

### Delhaize: Çok yavaş / takılıyor

**Belirti:** Tek kategoride 1 saatten fazla bekleme

**Çözüm:**
```
python delhaize_be_v2.py --resume
```

Checkpoint sayesinde kaldığı yerden devam eder. `haftalik_tam.py` bu durumu otomatik handle eder (4 saat timeout).

**Not:** Delhaize kasıtlı yavaş (camoufox anti-bot). Normal hız: 2-3 saat, 34 kategori.

---

### Carrefour: 0 ürün / Cloudflare engeli

**Belirti:** Script hemen bitiyor, 0 ürün

**Çözüm:**
```
python carrefour_be_v2.py --no-pause
```

v2 script camoufox kullanıyor (Firefox tabanlı, Cloudflare bypass). Eski `carrefour_be_playwright_cek.py` kullanma.

---

### ALDI: Çok az ürün (800'den az)

**Belirti:** Beklenen ~1800, gelen 200-400

**Çözüm:**
1. ALDI sitesinde yeni mevsimsel kategori var mı kontrol et
2. `sayfa_kaydet.py` içindeki ALDI `kategoriler` listesine URL ekle
3. URL formatı: `aldi.be/nl/producten/KATEGORI-ADI.html`

**Bilgi:** ALDI'nin gerçek kataloğu ~1800 SKU. 10.000+ imkansız — sadece ~1800 sabit ürün var.

---

## Dosya Yapısı

```
market_fiyat_cekici/
│
├── haftalik_tam.py          ← HER HAFTA BU
├── BAKIM_KILAVUZU.md        ← bu dosya
├── BASARILI_SCRIPTLER.md    ← hangi script ne kadar ürün çekiyor
│
├── loglar/
│   └── haftalik_log_YYYY-MM-DD.txt  ← otomatik oluşur
│
├── cikti/
│   ├── delhaize_be_v2_*.json
│   ├── colruyt_Genel_p01_*.json
│   ├── carrefour_be_v2_*.json
│   ├── lidl_be_producten_*.json
│   └── aldi_be_*.json
│
├── lidl_cookie.txt          ← aylık yenile (elle)
└── colruyt_state.json       ← otomatik yenileniyor
```

---

## Beklenen Ürün Sayıları

| Market    | Beklenen | Minimum Eşik |
|-----------|----------|--------------|
| Delhaize  | ~14,600  | 10,000       |
| Colruyt   | ~12,200  | 8,000        |
| Carrefour | ~12,900  | 8,000        |
| Lidl      | ~8,700   | 5,000        |
| ALDI      | ~1,800   | 800          |
| **Toplam**| **~50,400** | —         |

---

## Windows Görev Zamanlayıcı (Opsiyonel)

Her Pazartesi sabah otomatik çalıştır:
1. `görev zamanlayıcı` aç
2. Yeni Görev Oluştur
3. Tetikleyici: Her Pazartesi 08:00
4. Eylem: `cmd /c "cd C:\Users\yaman\Desktop\04.01.2026\market_fiyat_cekici && python haftalik_tam.py"`
