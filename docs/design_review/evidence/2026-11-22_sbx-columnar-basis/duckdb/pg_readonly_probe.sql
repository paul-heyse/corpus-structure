-- Read-only probe of the postgres extension against corpus_structure_dev (no writes).
LOAD postgres;
ATTACH 'dbname=corpus_structure_dev port=5434 host=/var/run/postgresql' AS pg (TYPE postgres, READ_ONLY);
SET pg_debug_show_queries = true;
EXPLAIN SELECT member_id, kind_contract FROM pg.kb.data_product_member WHERE kind_contract = 'nonexistent' AND member_id > 'm';
SELECT count(*) AS n FROM pg.kb.data_product_member WHERE kind_contract = 'nonexistent';
SELECT typeof(body) AS body_type, typeof(analyzed_scope) AS scope_type FROM pg.kb.data_product_member LIMIT 1;
SELECT typeof(a) ta, a, typeof(b) tb, b, typeof(c) tc, c, typeof(d) td, d, typeof(e) te, e
FROM postgres_query('pg', 'SELECT 1.50::numeric AS a, 12345678901234567890123456789012345678901.5::numeric AS b, 1.50::numeric(10,2) AS c, ''2026-11-22 10:00:00.123456+00''::timestamptz AS d, ''{"b":1,"a":[1.0,"é"]}''::jsonb AS e');
SET pg_numeric_as_varchar = true;
SELECT typeof(a) ta, a, typeof(b) tb, b FROM postgres_query('pg', 'SELECT 1.50::numeric AS a, 12345678901234567890123456789012345678901.5::numeric AS b');
BEGIN;
SELECT count(*) FROM pg.kb.data_product_member;
SELECT count(*) FROM pg.kb.data_product WHERE false;
COMMIT;
