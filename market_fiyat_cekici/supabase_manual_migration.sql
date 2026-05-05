
-- Supabase SQL Editor'da çalıştırın:
-- (Dashboard -> SQL Editor -> New Query)

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS promo_price DECIMAL(8,2);

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS promo_valid_from DATE;

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS promo_valid_until DATE;

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS promo_type TEXT;

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS nutriscore CHAR(1);

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS ecoscore CHAR(1);

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS energy_kcal_100g INT;

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS fat_g_100g DECIMAL(5,2);

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS saturated_fat_g DECIMAL(5,2);

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS sugars_g_100g DECIMAL(5,2);

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS salt_g_100g DECIMAL(5,2);

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS protein_g_100g DECIMAL(5,2);

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS palm_oil_free BOOLEAN DEFAULT FALSE;

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS is_fodmap_friendly BOOLEAN DEFAULT FALSE;

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS regional_cert TEXT[];

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS award_label TEXT[];

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS alcohol_pct DECIMAL(4,1);

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS vintage SMALLINT;

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS packaging_material TEXT;

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS recycle_code TEXT;

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS availability TEXT DEFAULT 'in_stock';

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS last_updated_at TIMESTAMPTZ DEFAULT now();

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS product_family_id UUID;

CREATE TABLE IF NOT EXISTS product_families (
    family_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ean              TEXT,
    canonical_name   TEXT,
    brand            TEXT,
    category_l1      TEXT,
    created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS price_history (
    id                   BIGSERIAL PRIMARY KEY,
    external_product_id  TEXT NOT NULL,
    chain_slug           TEXT NOT NULL,
    price                DECIMAL(8,2),
    promo_price          DECIMAL(8,2),
    recorded_at          DATE DEFAULT CURRENT_DATE,
    UNIQUE(external_product_id, chain_slug, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_mcp_nutriscore
    ON market_chain_products(nutriscore)
    WHERE nutriscore IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_mcp_promo
    ON market_chain_products(promo_price)
    WHERE promo_price IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ph_product
    ON price_history(external_product_id, chain_slug);

