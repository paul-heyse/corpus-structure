# curies

**Realization assessed:** curies 0.15.5. It is installed transitively and is **not a declared
dependency**. It received a light pass because CBO-013 asks about prefix maps.

**Researched:** 2026-10-29 by the R3 cluster. There is no overview page. Sources were Context7, the
installed source (`curies/api.py`) and one probe
([evidence](../../../design_review/evidence/2026-10-29_library-leverage-linkml/README.md), section P6).

## Reusable opportunity types

<a id="curies-prefix-converter"></a>

### `curies/prefix-converter`

**Need.** Expand CURIEs and compact IRIs against a closed prefix map.

**Mechanism.**
- `Converter.from_prefix_map(map)` is strict by default:
  - a duplicated URI prefix raises `DuplicateURIPrefixes`;
  - a duplicated prefix raises `DuplicatePrefixes`.
- `expand(curie, strict=True)` raises `ExpansionError`, or `NoCURIEDelimiterError` when the input has
  no colon.
- `compress(uri, passthrough=True)` matches through a longest-match trie. It returns `prefix:` for an
  exact namespace (probe-observed).
- `expand_or_standardize` and `parse_uri` are also available.

**Semantic differences to watch.**
- There is no passthrough for absolute URIs: `https://…` and `urn:…` raise on `expand`.
- Undelimited input raises a different exception type.
- Duplicate namespaces are refused at construction unless `strict=False`.

## Applicability at source `d739b88`

<a id="applicability-cbo-013"></a>

### CBO-013 — archived-prefix expansion and compaction: **fits with a thin wrapper**

Opportunity: [CBO-013](../../codebase/release-preparation.md#cbo-013).

Measured against `domain_operations.compact()` and `PreparedRelease.expand_name`:

- `compress(passthrough=True)` **matches `compact()` exactly** in every probed case.
- `expand` matches for known prefixes, for empty local parts and for refusal of unknown prefixes. It
  differs in three ways:
  - it lacks the `http(s)://`/`urn:` passthrough;
  - it raises a different exception for undelimited input;
  - it refuses duplicate namespaces where the current code breaks ties.

To fit, the wrapper needs a passthrough check and an exception mapping. Duplicate namespaces would
become a refusal at preparation time. That is a deliberate change for review, and depending on
curies directly would mean declaring and pinning it.

## Coverage limits

Not tested: Unicode prefixes, case-insensitive matching and synonyms.
