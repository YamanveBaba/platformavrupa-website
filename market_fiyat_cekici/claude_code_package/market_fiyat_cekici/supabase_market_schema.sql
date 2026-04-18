-- ============================================================
-- PLATFORM AVRUPA — MARKET ÜRÜN FİYATLARI
-- Bu dosyayı Supabase Dashboard > SQL Editor'da çalıştır
-- ============================================================

-- 1. Ana ürün tablosu
CREATE TABLE IF NOT EXISTS market_chain_products (
    id               BIGSERIAL PRIMARY KEY,
    chain_slug       TEXT NOT NULL,          -- 'colruyt_be', 'aldi_be', ...
    country_code     TEXT NOT NULL,          -- 'BE'
    product_code     TEXT NOT NULL,          -- Market'in kendi ürün kodu
    name             TEXT NOT NULL,
    brand            TEXT,
    category         TEXT,
    price            NUMERIC(10,2) NOT NULL,
    currency         TEXT DEFAULT 'EUR',
    in_promo         BOOLEAN DEFAULT false,
    promo_price      NUMERIC(10,2),
    promo_valid_from  TEXT,                  -- '2025-04-01'
    promo_valid_until TEXT,                  -- '2025-04-07'
    image_url        TEXT,
    captured_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT market_chain_products_unique UNIQUE (chain_slug, product_code)
);

-- 2. Hızlı arama indexleri
CREATE INDEX IF NOT EXISTS idx_mcp_chain    ON market_chain_products(chain_slug);
CREATE INDEX IF NOT EXISTS idx_mcp_country  ON market_chain_products(country_code);
CREATE INDEX IF NOT EXISTS idx_mcp_name     ON market_chain_products USING gin(to_tsvector('dutch', name));
CREATE INDEX IF NOT EXISTS idx_mcp_name_simple ON market_chain_products(lower(name));
CREATE INDEX IF NOT EXISTS idx_mcp_promo    ON market_chain_products(in_promo) WHERE in_promo = true;

-- 3. Haftalık istatistik view (market.html bunu kullanır)
CREATE OR REPLACE VIEW market_chain_products_stats AS
SELECT
    country_code,
    chain_slug,
    COUNT(*)          AS product_count,
    COUNT(*) FILTER (WHERE in_promo = true) AS promo_count,
    MAX(captured_at)  AS last_captured_at
FROM market_chain_products
GROUP BY country_code, chain_slug;

-- 4. RLS aktif et
ALTER TABLE market_chain_products ENABLE ROW LEVEL SECURITY;

-- Herkes okuyabilir (public)
CREATE POLICY "Market products are viewable by everyone"
ON market_chain_products FOR SELECT
USING (true);

-- Sadece service_role yazabilir (scraper)
CREATE POLICY "Only service role can insert/update"
ON market_chain_products FOR ALL
USING (auth.role() = 'service_role');

-- 5. market_chains tablosuna BE marketlerini ekle (yoksa)
INSERT INTO market_chains (name, countries, brochure_url, website)
VALUES
  ('Colruyt', ARRAY['BE'], 'https://www.colruyt.be/nl/promoties', 'https://www.colruyt.be'),
  ('ALDI',    ARRAY['BE'], 'https://www.aldi.be/nl/aanbiedingen/', 'https://www.aldi.be'),
  ('Lidl',    ARRAY['BE'], 'https://www.lidl.be/nl/aanbiedingen', 'https://www.lidl.be'),
  ('Delhaize',ARRAY['BE'], 'https://www.delhaize.be/nl/promoties', 'https://www.delhaize.be'),
  ('Carrefour',ARRAY['BE'],'https://www.carrefour.be/nl/promoties', 'https://www.carrefour.be')
ON CONFLICT DO NOTHING;

-- ============================================================
-- KONTROL: Tablo oluştu mu?
-- SELECT COUNT(*) FROM market_chain_products;
-- SELECT * FROM market_chain_products_stats;
-- ============================================================
