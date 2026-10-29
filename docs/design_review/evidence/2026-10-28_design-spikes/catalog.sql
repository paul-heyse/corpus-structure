-- Catalog views over this folder's results (ADR-0010). Rendered by `just evidence catalog` with
-- {{ "{{ folder }}" }} = this folder's path; created in the folder's own schema.

-- Comparisons of S0 (results/s0/compare) and its revisit S0-R2 (results/s0r2/compare; names do not collide).

-- Every comparison's tier scores: precision, recall, F1 with 95% bootstrap intervals over units.
CREATE TABLE comparison_scores AS
WITH s AS (
    SELECT regexp_extract(filename, 'compare/([^/]+)/score.json', 1) AS comparison, j
    FROM read_json(['{{ folder }}/results/s0/compare/*/score.json', '{{ folder }}/results/s0r2/compare/*/score.json'],
                   format = 'auto', filename = true, records = false, columns = {'j': 'JSON'})
)
SELECT comparison, tier,
       CAST(j -> 'tiers' -> tier -> 'precision' ->> 'value' AS DOUBLE) AS precision,
       CAST(j -> 'tiers' -> tier -> 'recall' ->> 'value' AS DOUBLE) AS recall,
       CAST(j -> 'tiers' -> tier -> 'f1' ->> 'value' AS DOUBLE) AS f1,
       CAST(j -> 'tiers' -> tier -> 'f1' -> 'ci95' ->> 0 AS DOUBLE) AS f1_lo,
       CAST(j -> 'tiers' -> tier -> 'f1' -> 'ci95' ->> 1 AS DOUBLE) AS f1_hi,
       CAST(j -> 'tiers' -> tier -> 'totals' ->> 'n_ref' AS INTEGER) AS n_ref,
       CAST(j -> 'tiers' -> tier -> 'totals' ->> 'n_pred' AS INTEGER) AS n_pred,
       CAST(j -> 'symmetrized' -> tier ->> 'agreement' AS DOUBLE) AS symmetrized_f1,
       json_array_length(j -> 'units') AS n_units
FROM s, (VALUES ('core'), ('full'), ('evidence')) t(tier);

-- Accuracy figures on aligned pairs, the cascade count and pending value decisions.
CREATE TABLE comparison_accuracy AS
WITH s AS (
    SELECT regexp_extract(filename, 'compare/([^/]+)/score.json', 1) AS comparison, j
    FROM read_json(['{{ folder }}/results/s0/compare/*/score.json', '{{ folder }}/results/s0r2/compare/*/score.json'],
                   format = 'auto', filename = true, records = false, columns = {'j': 'JSON'})
)
SELECT comparison,
       CAST(j -> 'binding_accuracy' ->> 'value' AS DOUBLE) AS binding_accuracy,
       CAST(j -> 'binding_accuracy' -> 'totals' ->> 1 AS INTEGER) AS bindings,
       CAST(j -> 'scope_accuracy' ->> 'value' AS DOUBLE) AS scope_accuracy,
       CAST(j -> 'scope_accuracy' -> 'totals' ->> 1 AS INTEGER) AS scopes,
       CAST(j -> 'unsupported_recall' ->> 'value' AS DOUBLE) AS unsupported_recall,
       CAST(j -> 'unsupported_recall' -> 'totals' ->> 0 AS INTEGER) AS unsupported_matched,
       CAST(j -> 'unsupported_recall' -> 'totals' ->> 1 AS INTEGER) AS unsupported_ref,
       CAST(j -> 'kappa' -> 'modality' ->> 'kappa' AS DOUBLE) AS kappa_modality,
       CAST(j -> 'kappa' -> 'statement_role' ->> 'kappa' AS DOUBLE) AS kappa_statement_role,
       CAST(j -> 'cascade' ->> 'cascaded' AS INTEGER) AS cascaded,
       CAST(j -> 'field_breakdown' ->> 'core_matched' AS INTEGER) AS core_matched,
       json_array_length(j -> 'pending_value_comparisons') AS pending_values
FROM s;

-- Full-tier failures on core-matched pairs, by field.
CREATE TABLE comparison_field_failures AS
WITH s AS (
    SELECT regexp_extract(filename, 'compare/([^/]+)/score.json', 1) AS comparison, j
    FROM read_json(['{{ folder }}/results/s0/compare/*/score.json', '{{ folder }}/results/s0r2/compare/*/score.json'],
                   format = 'auto', filename = true, records = false, columns = {'j': 'JSON'})
)
SELECT comparison, k AS field, CAST(j -> 'field_breakdown' -> 'failures' ->> k AS INTEGER) AS failures
FROM s, unnest(json_keys(j -> 'field_breakdown' -> 'failures')) AS t(k);

-- Claim- and meaning-key agreement on aligned pairs, raw and under the key variants.
CREATE TABLE key_agreement AS
WITH s AS (
    SELECT regexp_extract(filename, 'compare/([^/]+)/score.json', 1) AS comparison, j
    FROM read_json(['{{ folder }}/results/s0/compare/*/score.json', '{{ folder }}/results/s0r2/compare/*/score.json'],
                   format = 'auto', filename = true, records = false, columns = {'j': 'JSON'})
)
SELECT comparison, tier,
       CAST(j -> ('keys_' || tier) ->> 'pairs' AS INTEGER) AS pairs,
       CAST(j -> ('keys_' || tier) ->> 'claim_key_equal' AS INTEGER) AS claim_key_equal,
       CAST(j -> ('keys_' || tier) ->> 'meaning_key_equal' AS INTEGER) AS meaning_key_equal
FROM s, (VALUES ('core'), ('full')) t(tier);

-- Per-unit, per-predicate counts behind every comparison.
CREATE TABLE agreement_rows AS
SELECT regexp_extract(filename, 'compare/([^/]+)/agreement.tsv', 1) AS comparison, * EXCLUDE (filename)
FROM read_csv(['{{ folder }}/results/s0/compare/*/agreement.tsv', '{{ folder }}/results/s0r2/compare/*/agreement.tsv'],
              delim = '\t', header = true, filename = true);

-- Batch and packet sizes per unit and pass.
CREATE TABLE sizes AS SELECT * FROM read_csv('{{ folder }}/results/s0/size.tsv', delim = '\t', header = true);

-- M13 probe rows by input and variant.
CREATE TABLE m13_rows AS
SELECT regexp_extract(filename, 'm13_probe\.([^.]+)\.(.+)\.tsv', 1) AS input,
       regexp_extract(filename, 'm13_probe\.([^.]+)\.(.+)\.tsv', 2) AS variant,
       * EXCLUDE (filename)
FROM read_csv('{{ folder }}/results/s0/m13_probe.*.tsv', delim = '\t', header = true, filename = true,
              union_by_name = true, all_varchar = true);

-- Value comparisons not decided by canonical form (OPEN-D7-2): tier, outcome and the two values.
CREATE TABLE value_decisions AS
WITH s AS (
    SELECT regexp_extract(filename, 'compare/([^/]+)/score.json', 1) AS comparison, j
    FROM read_json(['{{ folder }}/results/s0/compare/*/score.json', '{{ folder }}/results/s0r2/compare/*/score.json'],
                   format = 'auto', filename = true, records = false, columns = {'j': 'JSON'})
)
SELECT comparison, d ->> 0 AS unit, d ->> 1 AS tier, d ->> 2 AS equal, d ->> 3 AS a, d ->> 4 AS b
FROM s, unnest(CAST(j -> 'non_canonical_value_decisions' AS JSON[])) AS t(d);

-- Full-tier condition failures against the reference, classified by shape (code/s0_condition_classes.py).
CREATE TABLE condition_classes AS
SELECT * FROM read_csv('{{ folder }}/results/s0/condition_classes.tsv', delim = '\t', header = true);

-- S6 Storage smoke (results/s6; code/s6*.py).

-- Constraint sweep: every bad row, the error expected and the one observed.
CREATE TABLE s6_constraints AS
SELECT * FROM read_csv('{{ folder }}/results/s6/constraints.tsv', delim = '\t', header = true, all_varchar = true);

-- Vector loads and filtered top-10 queries by dimension, index layout and iterative scan.
CREATE TABLE s6_vectors AS
SELECT * FROM read_csv('{{ folder }}/results/s6/vectors.tsv', delim = '\t', header = true);

-- Binary COPY timings and queries at run scale.
CREATE TABLE s6_volume AS
SELECT * FROM read_csv('{{ folder }}/results/s6/volume.tsv', delim = '\t', header = true, all_varchar = true);

-- Table, index and column sizes after the volume load.
CREATE TABLE s6_sizes AS
SELECT * FROM read_csv('{{ folder }}/results/s6/sizes.tsv', delim = '\t', header = true, all_varchar = true);

-- ==== S4 LinkML compilation (results/s4; code/s4*.py) — block owned by S4 ====

-- Batch validation: one row per batch, form and variant (as written, and canonical after the recorded V1/V2 rewrites).
CREATE TABLE s4_validation AS
SELECT * FROM read_csv('{{ folder }}/results/s4/validation.tsv', delim = '\t', header = true);

-- Validation per batch set and variant.
CREATE VIEW s4_validation_by_set AS
SELECT "set", variant, count(*) AS batches, sum(claims) AS claims,
       count(*) FILTER (WHERE pydantic = 'valid') AS pydantic_valid,
       count(*) FILTER (WHERE jsonschema = 'valid') AS jsonschema_valid,
       count(*) FILTER (WHERE sidetable = 'ok') AS sidetable_ok,
       count(*) FILTER (WHERE validators_agree) AS validators_agree,
       sum(rewrites) AS rewrites
FROM s4_validation GROUP BY "set", variant;

-- Rules: rule x claim x call site, unseeded (expected pass) and seeded (expected fire).
CREATE TABLE s4_rules AS
SELECT * FROM read_csv('{{ folder }}/results/s4/rules.tsv', delim = '\t', header = true, all_varchar = true);

CREATE VIEW s4_rules_by_rule AS
SELECT rule, grp, count(*) FILTER (WHERE expected = 'pass') AS evaluations,
       count(*) FILTER (WHERE expected = 'pass' AND result = 'fire') AS unexpected_fires,
       count(*) FILTER (WHERE expected = 'fire' AND result = 'fire') AS seeds_caught,
       count(*) FILTER (WHERE expected = 'fire') AS seeds
FROM s4_rules GROUP BY rule, grp;

-- Artifact sizes in bytes and Qwen3.5-9B tokens.
CREATE TABLE s4_sizes AS
SELECT * FROM read_csv('{{ folder }}/results/s4/sizes.tsv', delim = '\t', header = true, all_varchar = true);
-- ==== end S4 ====

-- Claim- and meaning-key agreement on the 70 aligned A/B pairs under the S0 variants and the revised statement key (S6-F).
CREATE TABLE s6_keys AS
SELECT * FROM read_csv('{{ folder }}/results/s6/keys.tsv', delim = '\t', header = true, all_varchar = true);

-- ==== S5 ====
-- S5-A grammar coverage per math span (results/s5/parse.tsv): status under the baseline grammar (V1 edited,
-- V2 tokenizer reader, identical to the spike grammar) and under the extended grammar (S5 extensions).
CREATE TABLE s5_parse AS
SELECT * FROM read_csv('{{ folder }}/results/s5/parse.tsv', delim = '\t', header = true, quote = '', escape = '',
                       all_varchar = true);

CREATE VIEW s5_coverage AS
SELECT 'baseline' AS grammar, kind, status_baseline AS status, count(*) AS spans FROM s5_parse GROUP BY ALL
UNION ALL
SELECT 'extended' AS grammar, kind, status, count(*) AS spans FROM s5_parse GROUP BY ALL;

-- S5-A tree/token property per span the extended grammar reads (results/s5/canonical.tsv).
CREATE TABLE s5_canonical AS
SELECT * FROM read_csv('{{ folder }}/results/s5/canonical.tsv', delim = '\t', header = true, quote = '', escape = '',
                       all_varchar = true);
-- ==== end S5 ====
