# -*- coding: utf-8 -*-
"""
Carrefour BE — DOM yapısı analizi
Verbolia sayfası + ana kategori sayfasının DOM'unu incele.
python carrefour_dom_analiz.py
"""
from __future__ import annotations
import json, os, re, time, random
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))

SAYFALAR = [
    "https://www.carrefour.be/nl/vb/melk-kopen",
    "https://www.carrefour.be/nl/al-onze-promoties",
    "https://www.carrefour.be/nl/",
]

def main():
    from camoufox.sync_api import Camoufox

    sonuclar = {}

    with Camoufox(
        headless=False,
        firefox_user_prefs={
            "browser.startup.page": 0,
            "browser.sessionstore.resume_from_crash": False,
            "browser.sessionstore.enabled": False,
        },
    ) as browser:
        page = browser.new_page()
        time.sleep(2)

        for url in SAYFALAR:
            print(f"\n{'='*60}\n[SAYFA] {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            except Exception as e:
                print(f"  [hata] {e}")
                continue
            time.sleep(4)

            # Cookie
            for sel in ('button:has-text("Alles accepteren")', '#onetrust-accept-btn-handler'):
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible(timeout=2000):
                        loc.click(); time.sleep(1.5); break
                except Exception: pass

            print(f"  Başlık: {page.title()}")
            print(f"  URL: {page.url}")

            # Scroll yap
            for _ in range(10):
                page.evaluate("window.scrollBy(0, 600)")
                time.sleep(0.8)

            # DOM analizi
            analiz = page.evaluate("""
            () => {
                const counts = {};
                // Olası ürün container'ları say
                const selectors = [
                    '[data-pid]', '[data-product-id]', '[data-article-id]',
                    '.product-tile', '.product-card', '.product-item',
                    '[class*="product-tile"]', '[class*="ProductCard"]',
                    '[class*="product-card"]', '[class*="product-item"]',
                    '[class*="article-tile"]', '[class*="ArticleTile"]',
                    '.js-product', '[data-tracking-product]',
                    '[itemtype*="Product"]', 'article.product',
                    '[class*="product-grid"] > *', '[class*="ProductGrid"] > *',
                    '[class*="search-result"]', '[class*="SearchResult"]',
                ];
                selectors.forEach(sel => {
                    try { counts[sel] = document.querySelectorAll(sel).length; } catch(e) {}
                });

                // İlk ilginç elementi göster
                let sample = null;
                const interesting = Object.entries(counts)
                    .filter(([k,v]) => v > 0)
                    .sort((a,b) => b[1]-a[1]);

                if (interesting.length > 0) {
                    const topSel = interesting[0][0];
                    const el = document.querySelector(topSel);
                    if (el) {
                        // Tüm attribute'ları al
                        const attrs = {};
                        Array.from(el.attributes).forEach(a => {
                            attrs[a.name] = a.value.slice(0, 200);
                        });
                        // İlk 800 karakter HTML
                        sample = {
                            selector: topSel,
                            attrs: attrs,
                            html_ilk: el.outerHTML.slice(0, 800),
                        };
                    }
                }

                // Nav linkleri
                const navLinks = [];
                document.querySelectorAll('nav a, [class*="nav"] a, [class*="category"] a, header a').forEach(a => {
                    const href = a.href || '';
                    const text = (a.textContent || '').trim();
                    if (href.includes('carrefour.be') && text.length > 1 && text.length < 60) {
                        navLinks.push({href, text});
                    }
                });

                // Window değişkenleri
                const windowVars = [];
                ['__NEXT_DATA__','__NUXT_DATA__','__APP_STATE__','__INITIAL_STATE__',
                 'digitalData','dataLayer','Granite','window.__sf'].forEach(v => {
                    try {
                        const val = eval(v);
                        if (val) windowVars.push({var: v, type: typeof val, len: JSON.stringify(val).length});
                    } catch(e) {}
                });

                return {counts, sample, navLinks: navLinks.slice(0, 50), windowVars};
            }
            """)

            # Selectors
            nonzero = {k: v for k, v in analiz.get("counts", {}).items() if v > 0}
            print(f"\n  Bulunan selectors (sıfır olmayan):")
            for sel, cnt in sorted(nonzero.items(), key=lambda x: -x[1]):
                print(f"    {cnt:4d}  {sel}")

            # Sample
            sample = analiz.get("sample")
            if sample:
                print(f"\n  En çok eleman ({sample['selector']}):")
                print(f"    Attributes: {sample['attrs']}")
                print(f"    HTML[0:400]: {sample['html_ilk'][:400]}")

            # Nav linkleri
            nav = analiz.get("navLinks", [])
            carrefour_nav = [l for l in nav if '/nl/' in l.get('href','')]
            print(f"\n  Nav linkleri ({len(carrefour_nav)} adet /nl/ içerenler):")
            for l in carrefour_nav[:20]:
                print(f"    {l['href'][:80]}  [{l['text']}]")

            # Window vars
            wvars = analiz.get("windowVars", [])
            if wvars:
                print(f"\n  Window değişkenleri: {wvars}")

            sonuclar[url] = analiz
            time.sleep(2)

    # Sonuçları kaydet
    out = os.path.join(script_dir, "carrefour_dom_analiz.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(sonuclar, f, ensure_ascii=False, indent=2)
    print(f"\n\nSonuçlar kaydedildi: {out}")

if __name__ == "__main__":
    main()
