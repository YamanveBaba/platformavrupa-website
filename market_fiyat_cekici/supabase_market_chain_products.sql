-- Platform Avrupa — Zincir market ürün + fiyat tabloları
-- Supabase SQL Editor'da çalıştırın; ardından RLS politikalarını ekleyin.

-- Ana tablo: son bilinen fiyat (haftalık upsert)
CREATE TABLE IF NOT EXISTS public.market_chain_products (
  id BIGSERIAL PRIMARY KEY,
  chain_slug TEXT NOT NULL,
  country_code TEXT NOT NULL DEFAULT 'BE',
  external_product_id TEXT NOT NULL,
  place_or_store_ref TEXT,
  name TEXT NOT NULL,
  brand TEXT,
  unit_or_content TEXT,
  price NUMERIC NOT NULL,
  currency TEXT NOT NULL DEFAULT 'EUR',
  promo_price NUMERIC,
  in_promo BOOLEAN NOT NULL DEFAULT false,
  promo_valid_until DATE,
  promo_valid_from DATE,
  category_name TEXT,
  image_url TEXT,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  import_run_id UUID,
  raw_json JSONB,
  CONSTRAINT market_chain_products_chain_ext_unique UNIQUE (chain_slug, external_product_id)
);

CREATE INDEX IF NOT EXISTS idx_market_chain_products_chain ON public.market_chain_products (chain_slug);
CREATE INDEX IF NOT EXISTS idx_market_chain_products_captured ON public.market_chain_products (captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_market_chain_products_name_search ON public.market_chain_products USING gin (to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(brand, '')));

COMMENT ON TABLE public.market_chain_products IS 'Zincir market scraper çıktısı; site sadece okur. Yazım service_role veya Edge Function ile.';

-- Mevcut projede tablo daha önce oluşturulduysa bir kez çalıştırın:
-- ALTER TABLE public.market_chain_products ADD COLUMN IF NOT EXISTS promo_valid_from DATE;

-- İsteğe bağlı: job logları
CREATE TABLE IF NOT EXISTS public.market_price_import_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chain_slug TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  row_count INTEGER DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'partial', 'failed')),
  notes TEXT
);

-- RLS
ALTER TABLE public.market_chain_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.market_price_import_runs ENABLE ROW LEVEL SECURITY;

-- Herkes okuyabilsin (karşılaştırma ekranı için)
CREATE POLICY "market_chain_products_select_anon"
  ON public.market_chain_products FOR SELECT
  TO anon, authenticated
  USING (true);

-- Yazım: Supabase Dashboard veya laptop scriptinde **service_role** anahtarı ile REST upsert.
-- service_role RLS'i bypass eder; tarayıcıdaki anon key asla yazamaz.

-- import_runs: RLS açık, policy yok → yalnızca service_role erişir (logları sadece sen görürsün)
