-- Kategori hiyerarşi sütunları (L1-L4)
-- Supabase SQL Editor -> New Query -> Run

ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS category_l1 TEXT;
ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS category_l2 TEXT;
ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS category_l3 TEXT;
ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS category_l4 TEXT;

CREATE INDEX IF NOT EXISTS idx_mcp_cat_l1 ON market_chain_products(category_l1);
CREATE INDEX IF NOT EXISTS idx_mcp_cat_l2 ON market_chain_products(category_l2);
CREATE INDEX IF NOT EXISTS idx_mcp_cat_l3 ON market_chain_products(category_l3);
