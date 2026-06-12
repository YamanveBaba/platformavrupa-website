-- Platform Avrupa — Supabase Şema v2
-- Supabase SQL Editor'da çalıştır.
-- Mevcut market_chain_products tablosu bozulmaz.

-- ─────────────────────────────────────────────────────────────
-- 1. KANONIK ÜRÜNLER (300 sabit Türk ürünü — bir kez tanımlanır)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS canonical_products (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  slug         text        UNIQUE NOT NULL,
  name_tr      text        NOT NULL,
  tip          text        NOT NULL CHECK (tip IN ('marka', 'sepet')),
  nl_search    text        NOT NULL,
  category     text        NOT NULL,
  unit_type    text        NOT NULL,
  is_ethnic    boolean     DEFAULT false,
  created_at   timestamptz DEFAULT now()
);

COMMENT ON TABLE canonical_products IS '300 Türk ürününün kanonik tanımı. Bir kez eklenir, scraper sonuçları buna eşleştirilir.';
COMMENT ON COLUMN canonical_products.slug IS 'URL-safe benzersiz anahtar: "yari-yagli-sut"';
COMMENT ON COLUMN canonical_products.nl_search IS 'Arama terimi (Hollandaca), scraper bu terimle markette arama yapar';
COMMENT ON COLUMN canonical_products.tip IS '"marka" = birebir aynı ürün (barkodla). "sepet" = o tipteki en ucuz';
COMMENT ON COLUMN canonical_products.is_ethnic IS 'true = genellikle sadece Türk/etnik marketlerde bulunur';

-- ─────────────────────────────────────────────────────────────
-- 2. MARKET TEKLİFLERİ (her market için günlük güncellenir)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS product_offers (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_id     uuid        NOT NULL REFERENCES canonical_products(id) ON DELETE CASCADE,
  chain            text        NOT NULL,
  market_name      text        NOT NULL,
  market_name_tr   text,
  price            numeric(10,2),
  promo_price      numeric(10,2),
  in_promo         boolean     DEFAULT false,
  promo_text_nl    text,
  promo_text_tr    text,
  promo_valid_from date,
  promo_valid_until date,
  unit_price       numeric(10,4),
  image_url        text,
  source_url       text,
  last_seen_at     timestamptz DEFAULT now(),
  UNIQUE(canonical_id, chain)
);

COMMENT ON TABLE product_offers IS 'Her canonical ürünün 5 marketteki güncel fiyat/promo teklifleri';
COMMENT ON COLUMN product_offers.chain IS '"colruyt_be" | "aldi_be" | "delhaize_be" | "lidl_be" | "carrefour_be"';
COMMENT ON COLUMN product_offers.market_name IS 'Marketin kendi ürün adı (NL/FR)';
COMMENT ON COLUMN product_offers.market_name_tr IS 'Türkçe çevrilmiş ürün adı';
COMMENT ON COLUMN product_offers.unit_price IS 'Normalize birim fiyat (€/kg veya €/L)';
COMMENT ON COLUMN product_offers.last_seen_at IS 'Son çekim zamanı — eskiyen teklifleri temizlemek için kullan';

-- ─────────────────────────────────────────────────────────────
-- 3. ÇEVİRİ CACHE (bir kere çevrilir, tekrar sorulmaz)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS translations (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  source_text text        NOT NULL,
  source_lang text        NOT NULL,
  target_lang text        NOT NULL,
  target_text text        NOT NULL,
  created_at  timestamptz DEFAULT now(),
  UNIQUE(source_text, source_lang, target_lang)
);

COMMENT ON TABLE translations IS 'Çeviri cache. source_text+lang kombinasyonu bir kez çevrilir, sonraki sorgular buradan gelir.';

-- ─────────────────────────────────────────────────────────────
-- 4. İNDEKSLER
-- ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_product_offers_chain
  ON product_offers(chain);

CREATE INDEX IF NOT EXISTS idx_product_offers_canonical
  ON product_offers(canonical_id);

CREATE INDEX IF NOT EXISTS idx_product_offers_promo
  ON product_offers(in_promo, promo_valid_until)
  WHERE in_promo = true;

CREATE INDEX IF NOT EXISTS idx_product_offers_last_seen
  ON product_offers(last_seen_at);

CREATE INDEX IF NOT EXISTS idx_translations_lookup
  ON translations(source_text, source_lang, target_lang);

CREATE INDEX IF NOT EXISTS idx_canonical_category
  ON canonical_products(category);

-- ─────────────────────────────────────────────────────────────
-- 5. RLS (Row Level Security)
-- ─────────────────────────────────────────────────────────────
ALTER TABLE canonical_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_offers ENABLE ROW LEVEL SECURITY;
ALTER TABLE translations ENABLE ROW LEVEL SECURITY;

-- Public okuma (frontend'in ihtiyacı)
CREATE POLICY "public read canonical_products"
  ON canonical_products FOR SELECT USING (true);

CREATE POLICY "public read product_offers"
  ON product_offers FOR SELECT USING (true);

CREATE POLICY "public read translations"
  ON translations FOR SELECT USING (true);

-- Service role yazma (scraper'ların ihtiyacı)
CREATE POLICY "service write canonical_products"
  ON canonical_products FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "service write product_offers"
  ON product_offers FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "service write translations"
  ON translations FOR ALL
  USING (auth.role() = 'service_role');

-- ─────────────────────────────────────────────────────────────
-- 6. YARDIMCI VIEW — indirim sekmesi için
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW active_promos AS
SELECT
  cp.slug,
  cp.name_tr,
  cp.category,
  cp.unit_type,
  po.chain,
  po.market_name,
  po.market_name_tr,
  po.price,
  po.promo_price,
  po.promo_text_nl,
  po.promo_text_tr,
  po.promo_valid_from,
  po.promo_valid_until,
  po.unit_price,
  po.image_url
FROM product_offers po
JOIN canonical_products cp ON po.canonical_id = cp.id
WHERE po.in_promo = true
  AND (po.promo_valid_until IS NULL OR po.promo_valid_until >= current_date)
ORDER BY cp.category, cp.name_tr, po.chain;

-- ─────────────────────────────────────────────────────────────
-- 7. YARDIMCI VIEW — karşılaştırma tablosu
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW product_comparison AS
SELECT
  cp.id AS canonical_id,
  cp.slug,
  cp.name_tr,
  cp.tip,
  cp.category,
  cp.unit_type,
  cp.is_ethnic,
  json_agg(
    json_build_object(
      'chain',           po.chain,
      'market_name',     po.market_name,
      'market_name_tr',  po.market_name_tr,
      'price',           po.price,
      'promo_price',     po.promo_price,
      'in_promo',        po.in_promo,
      'promo_text_tr',   po.promo_text_tr,
      'promo_valid_until', po.promo_valid_until,
      'unit_price',      po.unit_price,
      'image_url',       po.image_url
    ) ORDER BY po.unit_price NULLS LAST
  ) AS offers,
  COUNT(po.chain) AS chain_count,
  MIN(COALESCE(po.promo_price, po.price)) AS min_price
FROM canonical_products cp
LEFT JOIN product_offers po ON po.canonical_id = cp.id
GROUP BY cp.id, cp.slug, cp.name_tr, cp.tip, cp.category, cp.unit_type, cp.is_ethnic
ORDER BY cp.category, cp.name_tr;
