"""
Supabase şema güncelleme scripti.
market_chain_products tablosuna yeni sütunlar ekler.
price_history ve product_families tablolarını oluşturur.

Çalıştırma: python supabase_sema_guncelle.py
"""

import os
import sys
import json
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from json_to_supabase_yukle import load_secrets


def rpc_sql(url: str, key: str, sql: str) -> dict:
    payload = json.dumps({"query": sql}).encode()
    req = urllib.request.Request(
        f"{url}/rest/v1/rpc/exec_sql",
        data=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return {"ok": True, "status": r.status}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return {"ok": False, "status": e.code, "body": body}


def alter_via_postgrest(url: str, key: str, sql: str, label: str) -> bool:
    """
    Supabase REST API üzerinden DDL çalıştırır.
    exec_sql RPC yoksa hata döner — kullanıcıya SQL'i manuel çalıştırması söylenir.
    """
    result = rpc_sql(url, key, sql)
    if result["ok"]:
        print(f"  [OK] {label}")
        return True
    body = result.get("body", "")
    # "does not exist" → RPC yok; "already exists" → zaten yapılmış
    if "already exists" in body or "duplicate column" in body.lower():
        print(f"  [SKIP] {label} — zaten mevcut")
        return True
    if "exec_sql" in body and "does not exist" in body:
        print(f"  [MANUAL] {label} — exec_sql RPC yok, SQL'i Supabase SQL Editor'da çalıştırın")
        return False
    print(f"  [ERR] {label}: HTTP {result['status']} — {body[:200]}")
    return False


# ─── DDL listesi ─────────────────────────────────────────────────────────────

ALTER_STATEMENTS = [
    # Promo alanları
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS promo_price DECIMAL(8,2)",
     "promo_price sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS promo_valid_from DATE",
     "promo_valid_from sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS promo_valid_until DATE",
     "promo_valid_until sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS promo_type TEXT",
     "promo_type sütunu"),
    # Besin & skor
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS nutriscore CHAR(1)",
     "nutriscore sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS ecoscore CHAR(1)",
     "ecoscore sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS energy_kcal_100g INT",
     "energy_kcal_100g sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS fat_g_100g DECIMAL(5,2)",
     "fat_g_100g sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS saturated_fat_g DECIMAL(5,2)",
     "saturated_fat_g sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS sugars_g_100g DECIMAL(5,2)",
     "sugars_g_100g sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS salt_g_100g DECIMAL(5,2)",
     "salt_g_100g sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS protein_g_100g DECIMAL(5,2)",
     "protein_g_100g sütunu"),
    # Diyet bayrakları
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS palm_oil_free BOOLEAN DEFAULT FALSE",
     "palm_oil_free sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS is_fodmap_friendly BOOLEAN DEFAULT FALSE",
     "is_fodmap_friendly sütunu"),
    # Sertifika & ödül
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS regional_cert TEXT[]",
     "regional_cert sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS award_label TEXT[]",
     "award_label sütunu"),
    # İçecek özgün
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS alcohol_pct DECIMAL(4,1)",
     "alcohol_pct sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS vintage SMALLINT",
     "vintage sütunu"),
    # Ambalaj
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS packaging_material TEXT",
     "packaging_material sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS recycle_code TEXT",
     "recycle_code sütunu"),
    # Meta
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS availability TEXT DEFAULT 'in_stock'",
     "availability sütunu"),
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS last_updated_at TIMESTAMPTZ DEFAULT now()",
     "last_updated_at sütunu"),
    # Ürün ailesi
    ("ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS product_family_id UUID",
     "product_family_id sütunu"),
]

CREATE_TABLES = [
    ("""
CREATE TABLE IF NOT EXISTS product_families (
    family_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ean              TEXT,
    canonical_name   TEXT,
    brand            TEXT,
    category_l1      TEXT,
    created_at       TIMESTAMPTZ DEFAULT now()
)
""", "product_families tablosu"),

    ("""
CREATE TABLE IF NOT EXISTS price_history (
    id                   BIGSERIAL PRIMARY KEY,
    external_product_id  TEXT NOT NULL,
    chain_slug           TEXT NOT NULL,
    price                DECIMAL(8,2),
    promo_price          DECIMAL(8,2),
    recorded_at          DATE DEFAULT CURRENT_DATE,
    UNIQUE(external_product_id, chain_slug, recorded_at)
)
""", "price_history tablosu"),

    ("""
CREATE INDEX IF NOT EXISTS idx_mcp_nutriscore
    ON market_chain_products(nutriscore)
    WHERE nutriscore IS NOT NULL
""", "nutriscore index"),

    ("""
CREATE INDEX IF NOT EXISTS idx_mcp_promo
    ON market_chain_products(promo_price)
    WHERE promo_price IS NOT NULL
""", "promo index"),

    ("""
CREATE INDEX IF NOT EXISTS idx_ph_product
    ON price_history(external_product_id, chain_slug)
""", "price_history index"),
]

MANUAL_SQL = """
-- Supabase SQL Editor'da çalıştırın:
-- (Dashboard -> SQL Editor -> New Query)

"""


def main():
    url, key = load_secrets(SCRIPT_DIR)
    print(f"Supabase: {url}")
    print()

    # exec_sql RPC mevcut mu test et
    test = rpc_sql(url, key, "SELECT 1")
    use_rpc = test["ok"]
    if not use_rpc:
        body = test.get("body", "")
        if "exec_sql" in body and "does not exist" in body:
            use_rpc = False
        elif test["status"] == 200:
            use_rpc = True

    if not use_rpc:
        # RPC yok — SQL dosyasına yaz, kullanıcı manuel çalıştırır
        sql_path = os.path.join(SCRIPT_DIR, "supabase_manual_migration.sql")
        all_sql = MANUAL_SQL
        for sql, _ in ALTER_STATEMENTS + CREATE_TABLES:
            all_sql += sql.strip() + ";\n\n"
        with open(sql_path, "w", encoding="utf-8") as f:
            f.write(all_sql)
        print("exec_sql RPC bulunamadi. SQL dosyasi olusturuldu:")
        print(f"  {sql_path}")
        print()
        print("Yapilacaklar:")
        print("  1. Supabase Dashboard -> SQL Editor -> New Query")
        print(f"  2. {sql_path} dosyasinin icerigini yapistir ve calistir")
        return

    print("ALTER TABLE islemleri:")
    basarili = 0
    for sql, label in ALTER_STATEMENTS:
        ok = alter_via_postgrest(url, key, sql, label)
        if ok:
            basarili += 1

    print()
    print("Yeni tablolar ve indexler:")
    for sql, label in CREATE_TABLES:
        alter_via_postgrest(url, key, sql, label)

    print()
    print(f"Tamamlandi. {basarili}/{len(ALTER_STATEMENTS)} ALTER islemi basarili.")


if __name__ == "__main__":
    main()
