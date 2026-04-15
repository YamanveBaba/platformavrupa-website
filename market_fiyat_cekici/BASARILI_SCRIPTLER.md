# Başarılı Script Kayıtları

Son güncelleme: 2026-04-12

---

## ALDI BE — ~1,800 ürün (gerçek katalog boyutu budur)

| Tarih | Script | Sonuç | Not |
|-------|--------|-------|-----|
| 2026-03-15 | `aldi_tum_yeme_icme_cek.py` (kaybolmuş) | **1,880 ürün** | En iyi sonuç |
| 2026-04-01 | `aldi_scraper.py` (claude_code_package/) | 651 ürün | Sadece fiyatlı ürünler |
| 2026-04-12 | `sayfa_kaydet.py + html_analiz.py` | ~1,145 ürün | Snippet API |

**Gerçek durum:** ALDI BE discount market — katalog gerçekten ~1,800 SKU. 10,000 değil.
**Çalışan yöntem:** `sayfa_kaydet.py --market aldi` → `html_analiz.py --market aldi`

---

## Colruyt BE — 12,229 ürün ✅

| Tarih | Script | Sonuç |
|-------|--------|-------|
| 2026-04-12 | `colruyt_cookie_yenile.py` + `colruyt_direct.py` | **12,229 ürün** |

**Çalışan yöntem:**
```
python colruyt_cookie_yenile.py
python colruyt_direct.py
python html_analiz.py --market colruyt
```
Cookie süresi: her hafta yenilenmeli (otomatik)

---

## Delhaize BE — 11,443 ürün ✅

| Tarih | Script | Sonuç | Not |
|-------|--------|-------|-----|
| 2026-04-02 | `delhaize_be_v2.py` | 14,607 ürün | v2DAI tam geldi |
| 2026-04-13 | `delhaize_be_v2.py --resume` | **11,443 ürün** | v2DAI timeout (40 ürün), v2MEA atlandı |

**Çalışan yöntem:**
```
python delhaize_be_v2.py --resume
python json_to_supabase_yukle.py --no-pause cikti\delhaize_be_v2_*.json
```
- camoufox + GraphQL interception, 34 kategori
- set_default_timeout(25s) ile takılma koruması eklendi (2026-04-13)
- Checkpoint var — Ctrl+C → --resume ile kaldığı yerden devam
- Tipik süre: 2-3 saat, bazen kategoriler API timeout ile atlanıyor (normal)
- **v2DAI (süt/peynir) ve v2MEA (et) bazen timeout** — çözüm: --resume ile tekrar dene

---

## Lidl BE — 8,705-9,006 ürün ✅

| Tarih | Script | Sonuç |
|-------|--------|-------|
| 2026-03-22 | `lidl_be_mindshift_api_cek.py` | 9,006 ürün |
| 2026-04-12 | `lidl_be_mindshift_api_cek.py` | **8,705 ürün** |

**Çalışan yöntem:**
```
python haftalik_lidl_supabase.py
```
Cookie: ayda 1 yenile (F12 → lidl.be → /q/api/search → Cookie header → lidl_cookie.txt)

---

## Carrefour BE — 12,918 ürün ✅

| Tarih | Script | Sonuç |
|-------|--------|-------|
| 2026-04-02 | `carrefour_be_v2.py` | **12,918 ürün** |

**Çalışan yöntem:**
```
python haftalik_carrefour_supabase.py
```
(carrefour_be_v2.py çağırır — camoufox + Meer tonen tıklama)

---

## Haftalık Rutin

```
python haftalik_tam.py
```

Bu script hepsini sırayla çalıştırır, timeout korur, özet rapor verir.

Sıra (haftalik_tam.py içinde):
1. Delhaize — 2-3 saat (4h timeout)
2. Carrefour — 1-2 saat (2.5h timeout)
3. Lidl — 30 dk (cookie aylık yenilenmeli)
4. Colruyt — 5 dk (reese84 cookie otomatik yenilenir)
5. ALDI — 30 dk (sayfa_kaydet + html_analiz)

**Toplam DB:** ~50,000 ürün (5 market)

## Son Güncelleme Sonuçları (2026-04-13)

| Market | Ürün | Not |
|--------|------|-----|
| Lidl ✅ | 8,705 | Cookie yenilendi |
| Colruyt ✅ | 12,229 | Tam geldi |
| ALDI ✅ | 1,990 | Kategori listesi genişletildi |
| Delhaize ✅ | 11,443 | v2MEA timeout atlandı |
| Carrefour ⏳ | - | Devam ediyor |

## Bilinen Sorunlar & Çözümleri

| Sorun | Çözüm |
|-------|-------|
| Delhaize takılıyor | Ctrl+C → `python delhaize_be_v2.py --resume` |
| Lidl 0 ürün | lidl_cookie.txt güncelle (F12→Network→Cookie) |
| Colruyt az ürün | `python colruyt_cookie_yenile.py` → `colruyt_direct.py` |
| Carrefour 0 ürün | `carrefour_be_v2.py` kullan, eski script değil |
