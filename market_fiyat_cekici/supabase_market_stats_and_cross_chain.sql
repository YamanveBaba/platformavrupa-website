-- Platform Avrupa — istatistik görünümü + çapraz zincir eşleme (Faz 2/3)
-- Supabase SQL Editor'da çalıştırın (market_chain_products tablosu mevcut olmalı).

-- ---------------------------------------------------------------------------
-- 1) Ülke / zincir bazında ürün sayısı ve son güncelleme (frontend özet için)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.market_chain_products_stats AS
SELECT
  country_code,
  chain_slug,
  COUNT(*)::bigint AS product_count,
  MAX(captured_at) AS last_captured_at
FROM public.market_chain_products
GROUP BY country_code, chain_slug;

COMMENT ON VIEW public.market_chain_products_stats IS
  'market.html Belçika paneli: zincir başına ürün sayısı ve son veri zamanı.';

-- Anon okuma (market sayfası)
GRANT SELECT ON public.market_chain_products_stats TO anon, authenticated;

-- ---------------------------------------------------------------------------
-- 2) İsteğe bağlı: aynı mantıksal ürünü farklı zincirlerde eşlemek (GTIN / manuel)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.product_cross_chain_match (
  id BIGSERIAL PRIMARY KEY,
  canonical_name TEXT,
  gtin TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT product_cross_chain_match_gtin_unique UNIQUE (gtin)
);

CREATE TABLE IF NOT EXISTS public.product_cross_chain_match_item (
  id BIGSERIAL PRIMARY KEY,
  match_id BIGINT NOT NULL REFERENCES public.product_cross_chain_match (id) ON DELETE CASCADE,
  chain_slug TEXT NOT NULL,
  external_product_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT product_cross_chain_match_item_unique UNIQUE (chain_slug, external_product_id)
);

CREATE INDEX IF NOT EXISTS idx_cross_match_item_lookup
  ON public.product_cross_chain_match_item (chain_slug, external_product_id);

COMMENT ON TABLE public.product_cross_chain_match IS
  'Aynı ürünün farklı zincirlerdeki external_product_id eşlemesi; GTIN doluysa benzersiz.';

ALTER TABLE public.product_cross_chain_match ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_cross_chain_match_item ENABLE ROW LEVEL SECURITY;

-- Karşılaştırma UI'si için herkese okuma (sadece eşleme tabloları; hassas veri yok)
CREATE POLICY "product_cross_chain_match_select_anon"
  ON public.product_cross_chain_match FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE POLICY "product_cross_chain_match_item_select_anon"
  ON public.product_cross_chain_match_item FOR SELECT
  TO anon, authenticated
  USING (true);

-- Yazım: yalnızca service_role veya Dashboard (policy yok = RLS açık, client yazamaz)
