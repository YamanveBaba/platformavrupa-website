# -*- coding: utf-8 -*-
"""
Verbolia sayfasındaki DOM yapısını hızlı test et.
python carrefour_verbolia_test.py
"""
import json, time
from camoufox.sync_api import Camoufox

URL = "https://www.carrefour.be/nl/vb/melk-kopen"

with Camoufox(headless=False, firefox_user_prefs={
    "browser.startup.page": 0,
    "browser.sessionstore.enabled": False,
}) as browser:
    page = browser.new_page()
    time.sleep(2)
    page.goto(URL, wait_until="domcontentloaded", timeout=90_000)
    time.sleep(4)

    # Cookie
    for sel in ('button:has-text("Alles accepteren")', '#onetrust-accept-btn-handler'):
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=2000):
                loc.click(); time.sleep(1.5); break
        except: pass

    # 5 scroll
    for _ in range(5):
        page.evaluate("window.scrollBy(0, 600)"); time.sleep(0.8)

    # 1 kez "Meer tonen" bas
    for sel in ('button:has-text("Meer tonen")', 'button:has-text("Toon meer")',
                'button:has-text("Laad meer")', 'button:has-text("meer")'):
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=2000):
                print(f"Buton bulundu: {sel}")
                loc.click(); time.sleep(3); break
        except: pass

    analiz = page.evaluate("""
    () => {
        const result = {};
        // Olası product selectors — SFCC + Verbolia + generic
        const sels = [
            '[data-pid]','[data-product-id]','[data-article-id]','[data-sku]',
            '[data-verbolia-id]','[data-tracking-product-id]','[data-gtm-product-id]',
            '.product-tile','[class*="product-tile"]','[class*="ProductTile"]',
            '.product-card','[class*="product-card"]','[class*="ProductCard"]',
            '.product-item','[class*="product-item"]','[class*="ProductItem"]',
            'article[class*="tile"]','article[class*="product"]',
            '[class*="article-tile"]','[class*="ArticleTile"]',
            'li[class*="product"]','li[class*="article"]',
            'article.product','[itemtype*="Product"]',
            '[class*="search-result"] > li','[class*="product-grid"] > *',
            '[class*="product-list"] > li','[class*="ProductList"] > *',
            '[class*="ProductGrid"] > *','[class*="product-grid"] > article',
            '.js-product','[data-tracking]','[data-analytics]',
            'ul[class*="product"] > li', 'ul[class*="article"] > li',
            '[class*="tile"]:not(html):not(body)',
        ];
        sels.forEach(s => {
            try {
                const n = document.querySelectorAll(s).length;
                if (n > 0) result[s] = n;
            } catch(e) {}
        });

        // Top 5 selectors — her birinden örnek al
        const sorted = Object.entries(result).sort((a,b) => b[1]-a[1]);
        const samples = [];
        for (const [sel, cnt] of sorted.slice(0, 5)) {
            const el = document.querySelector(sel);
            if (el) {
                const attrs = {};
                Array.from(el.attributes).forEach(a => attrs[a.name] = a.value.slice(0,120));
                samples.push({sel, count: cnt, attrs, html: el.outerHTML.slice(0,800)});
            }
        }

        // Fiyat içeren elementler
        const priceEls = [];
        document.querySelectorAll('[class*="price"],[class*="Price"],[class*="prijs"]').forEach(el => {
            const txt = el.textContent.trim();
            if (txt.match(/\\d+[.,]\\d{2}/)) {
                priceEls.push({tag: el.tagName, class: el.className.slice(0,80), text: txt.slice(0,50)});
            }
        });

        // data-* attribute'ları olan elementler (Verbolia custom attrs)
        const dataAttrs = {};
        document.querySelectorAll('article, li, div[class*="tile"], div[class*="card"]').forEach(el => {
            Array.from(el.attributes).forEach(a => {
                if (a.name.startsWith('data-')) {
                    dataAttrs[a.name] = (dataAttrs[a.name] || 0) + 1;
                }
            });
        });

        return {counts: result, samples, priceEls: priceEls.slice(0,15),
                dataAttrs, url: window.location.href};
    }
    """)

    print(f"\nURL: {analiz['url']}")
    print(f"\nBulunan selectors (toplam {len(analiz['counts'])} adet):")
    for k, v in sorted(analiz['counts'].items(), key=lambda x: -x[1])[:25]:
        print(f"  {v:4d}  {k}")

    print(f"\n=== Top 5 Selector Örnekleri ===")
    for s in analiz['samples']:
        print(f"\n[{s['count']}x] {s['sel']}")
        print(f"  Attrs: {s['attrs']}")
        print(f"  HTML[0:500]:\n{s['html'][:500]}")
        print()

    print(f"\n=== data-* attribute sıklığı (article/li/tile/card) ===")
    for k, v in sorted(analiz['dataAttrs'].items(), key=lambda x: -x[1])[:20]:
        print(f"  {v:4d}  {k}")

    print(f"\n=== Fiyat elementleri (ilk 10) ===")
    for p in analiz['priceEls'][:10]:
        print(f"  <{p['tag']}> class={p['class']!r:60}  text={p['text']!r}")

    # .product-price'ın üst elemanlarına bak — container'ı bul
    ustler = page.evaluate("""
    () => {
        const priceEls = [...document.querySelectorAll('.product-price')];
        if (!priceEls.length) return [];
        const result = [];
        // İlk 3 fiyat elementinin üst zincirini incele
        for (const el of priceEls.slice(0, 3)) {
            const chain = [];
            let p = el.parentElement;
            for (let i = 0; i < 8; i++) {
                if (!p || p === document.body) break;
                const attrs = {};
                Array.from(p.attributes).forEach(a => attrs[a.name] = a.value.slice(0,150));
                chain.push({
                    level: i+1,
                    tag: p.tagName,
                    class: p.className.slice(0,120),
                    attrs,
                    childCount: p.children.length,
                });
                p = p.parentElement;
            }
            result.push(chain);
        }
        return result;
    }
    """)

    print(f"\n=== .product-price üst zinciri (container bulmak için) ===")
    for i, chain in enumerate(ustler):
        print(f"\n  [Fiyat el #{i+1}]")
        for node in chain:
            print(f"    +{node['level']}  <{node['tag']}> class={node['class']!r}  attrs={node['attrs']}  children={node['childCount']}")

    # Ayrıca: kaç tane .product-price var?
    adet = page.evaluate("() => document.querySelectorAll('.product-price').length")
    print(f"\n  Toplam .product-price elementi: {adet}")
