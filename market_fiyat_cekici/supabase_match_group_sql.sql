-- match_group_id kolonu + index
-- Supabase Dashboard -> SQL Editor -> New Query -> Run

ALTER TABLE market_chain_products
  ADD COLUMN IF NOT EXISTS match_group_id TEXT;

CREATE INDEX IF NOT EXISTS idx_mcp_match_group
  ON market_chain_products(match_group_id)
  WHERE match_group_id IS NOT NULL;
