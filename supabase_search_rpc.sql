-- ============================================================
-- Platform Avrupa — Market Arama RPC Fonksiyonları
-- Supabase Dashboard > SQL Editor'a yapıştır ve çalıştır
-- ============================================================

-- 1. ANA ARAMA — öncelik kademeleri:
--    P1: name_tr "sorgu" ile BAŞLIYOR              → "Yumurta 6 adet"
--    P2: name_tr'de sorgu, önünde sadece 1 kelime  → "Organik Yumurta"
--    P3: name (Hollandaca) sorgu ile BAŞLIYOR      → "Eieren vrije uitloop"
--    P4: Hollandaca alias ile başlıyor             → "Scharreleieren..."
--    P5: Herhangi yerde geçiyor                   → "Mayonez met yumurta"

CREATE OR REPLACE FUNCTION search_market_products(
  q            TEXT,
  aliases      TEXT[]  DEFAULT NULL,   -- TR_ALIAS Hollandaca karşılıkları
  chain_filter TEXT    DEFAULT NULL,
  lim          INT     DEFAULT 300
)
RETURNS TABLE (
  name             TEXT,
  name_tr          TEXT,
  price            NUMERIC,
  promo_price      NUMERIC,
  in_promo         BOOLEAN,
  chain_slug       TEXT,
  image_url        TEXT,
  unit_or_content  TEXT,
  currency         TEXT
)
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  WITH ranked AS (
    SELECT
      name, name_tr, price, promo_price, in_promo, chain_slug,
      image_url, unit_or_content, currency,
      CASE
        -- P1: name_tr tam olarak sorguyla başlıyor ("Yumurta 6 adet")
        WHEN LOWER(name_tr) LIKE LOWER(q) || '%'
          THEN 1

        -- P2: name_tr'de sorgu var, önünde tam 1 kelime ("Organik Yumurta")
        WHEN LOWER(name_tr) LIKE '% ' || LOWER(q) || '%'
          AND array_length(
                string_to_array(
                  TRIM(SUBSTRING(LOWER(name_tr) FROM 1 FOR
                    GREATEST(0, POSITION(LOWER(q) IN LOWER(name_tr)) - 2)
                  )),
                  ' '
                ), 1
              ) = 1
          THEN 2

        -- P3: Hollandaca isim sorguyla başlıyor ("Eieren...")
        WHEN LOWER(name) LIKE LOWER(q) || '%'
          THEN 3

        -- P4: Alias kelimesiyle başlıyor (Türkçe→Hollandaca eşleşmesi)
        WHEN aliases IS NOT NULL
          AND EXISTS (
            SELECT 1 FROM unnest(aliases) a(term)
            WHERE LOWER(name) LIKE LOWER(term) || '%'
               OR LOWER(name_tr) LIKE LOWER(term) || '%'
          )
          THEN 4

        -- P5: Herhangi yerde geçiyor ("Mayonez met yumurta")
        ELSE 5
      END AS prio
    FROM market_chain_products
    WHERE
      (chain_filter IS NULL OR chain_slug = chain_filter)
      AND (
        -- Ana sorgu: Türkçe veya Hollandaca isimde geçiyor
        LOWER(name_tr) LIKE '%' || LOWER(q) || '%'
        OR LOWER(name) LIKE '%' || LOWER(q) || '%'
        -- Alias'lar: Hollandaca karşılıklar ("eieren", "melk" vb.)
        -- LENGTH >= 4 kontrolü: "ei" gibi kısa aliaslar "aardbei" içinde eşleşmesin
        OR (
          aliases IS NOT NULL
          AND EXISTS (
            SELECT 1 FROM unnest(aliases) a(term)
            WHERE (
              (LENGTH(term) >= 4 AND LOWER(name) LIKE '%' || LOWER(term) || '%')
              OR LOWER(name) LIKE LOWER(term) || ' %'
              OR LOWER(name) = LOWER(term)
            )
            OR (LENGTH(term) >= 4 AND LOWER(name_tr) LIKE '%' || LOWER(term) || '%')
          )
        )
      )
  )
  SELECT name, name_tr, price, promo_price, in_promo, chain_slug,
         image_url, unit_or_content, currency
  FROM ranked
  ORDER BY prio ASC, price ASC
  LIMIT lim;
$$;

-- ============================================================
-- 2. AUTOCOMPLETE — öneri listesi, alaka düzeye göre sıralı
-- DISTINCT ON yerine ROW_NUMBER() OVER kullanılır:
-- DISTINCT ON, ORDER BY'ı alfabetik sıralamaya zorlar → relevance bozulur.
-- ROW_NUMBER() ile önce prio hesaplanır, sonra dışarıda relevance sırası korunur.
-- ============================================================

CREATE OR REPLACE FUNCTION autocomplete_market_products(
  q       TEXT,
  aliases TEXT[] DEFAULT NULL,
  lim     INT    DEFAULT 8
)
RETURNS TABLE (name TEXT, name_tr TEXT)
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  WITH filtered AS (
    SELECT
      name, name_tr,
      CASE
        WHEN LOWER(name_tr) LIKE LOWER(q) || '%' THEN 1
        WHEN LOWER(name)    LIKE LOWER(q) || '%' THEN 2
        WHEN aliases IS NOT NULL AND EXISTS (
          SELECT 1 FROM unnest(aliases) a(term)
          WHERE LOWER(name_tr) LIKE LOWER(term) || '%'
             OR LOWER(name)    LIKE LOWER(term) || '%'
        ) THEN 3
        ELSE 4
      END AS prio
    FROM market_chain_products
    WHERE
      LOWER(name_tr) LIKE '%' || LOWER(q) || '%'
      OR LOWER(name)    LIKE '%' || LOWER(q) || '%'
      OR (
        aliases IS NOT NULL AND EXISTS (
          SELECT 1 FROM unnest(aliases) a(term)
          WHERE (
            (LENGTH(term) >= 4 AND LOWER(name) LIKE '%' || LOWER(term) || '%')
            OR LOWER(name) LIKE LOWER(term) || ' %'
            OR LOWER(name) = LOWER(term)
          )
        )
      )
  ),
  dedup AS (
    SELECT
      name, name_tr, prio,
      ROW_NUMBER() OVER (
        PARTITION BY LOWER(COALESCE(name_tr, name))
        ORDER BY prio ASC, LENGTH(COALESCE(name_tr, name)) ASC
      ) AS rn
    FROM filtered
  )
  SELECT name, name_tr
  FROM dedup
  WHERE rn = 1
  ORDER BY prio ASC, LENGTH(COALESCE(name_tr, name)) ASC
  LIMIT lim;
$$;

-- ============================================================
-- Test sorguları:
-- SELECT name_tr, name, price FROM search_market_products('yumurta', ARRAY['eieren','ei']) LIMIT 20;
-- SELECT name_tr, name FROM autocomplete_market_products('yum', ARRAY['eieren','ei']);
-- ============================================================
