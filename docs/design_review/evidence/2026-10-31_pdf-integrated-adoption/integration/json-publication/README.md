# Bounded JSON-text PDF publication — ADR-0041

**Tested — 2026-11-01; archived 2026-11-01T04:24Z.** Implementation: `67d0e030`, with
coordinator changes `9fa64bfa` and `26b62e59` included before final 0060 authoring.
The coordinator owns deployment, actual whole-book publication and assembled qualification.

## Delivered mechanism

The canonical wire bytes/digest, one Docling content graph, mandatory companion contract and
read ABI remain unchanged. Protected publication parses the envelope as PostgreSQL JSON text
and caches a compact JSONB header, separate JSON-text collections and bounded JSONB content.
Each collection record becomes JSONB independently. The same effective model supplies complete
envelope fields/types/cardinalities and every row's closed/nested shape guard; row validation
runs inside the corresponding protected publication loop. No dummy collections substitute for
the actual arrays. Task fences, exact replay/artifacts, all input pins, endpoints, selected
inventory, decisions and coverage checks remain active.

Per-occurrence lookups use one cached native document. Per-endpoint input resolution uses the
immutable normalized input relation rather than reparsing the input array. The physical model's
descriptor CHECK calls an immutable, owner-restricted helper which extracts the exact compact
descriptor from JSON text. Its body/owner/ACL/strictness join native admission. The selected-content
view likewise narrows only the content field. New forward `semantic_0060` realizes these changes;
frozen 0057, 0058 and 0059 remain unchanged.

JSON parsing, row validation and atomic relational publication still perform required work.
Temporary materialization, one bytea artifact and each individually narrowed JSONB record/content
retain their own PostgreSQL limits. No throughput, universal scale or source-fidelity improvement
is claimed by these controls.

## Bounded functional results

**passed:** 68 controls on the stable 9af8e4e plus 0060 implementation, covering protected PDF
publication and negative attacks, scoped readers, source views, integrated consumers, closed
JSON presence/null/unknown/nested types, effective-model min/max cardinalities, exact helper-drift
refusal, native closure and actual schema CLI generation. [Functional output](raw/functional.log).

The run explicitly supplied the retained task86 witness from the coordinator's main checkout:
558,190,320 canonical bytes, SHA256
`c8f19ca1703206e9007b416eecb7c0d286de57d7ce82b006a605335efe7da524`, including270,447 relations.
The new descriptor helper and narrow content extraction passed an actual read-only database
check under the publisher role: exact independent descriptor equality,137,752,426 JSONB content
bytes and183,280 native text nodes. This is **not** protected whole-book publication and uses
no fabricated input custody or production database clone. The actual protected book producer
remains the coordinator's retry7 obligation.

```sh
env -u BASH_ENV PYTHONPATH=python/corpus-structure/src \
  CORPUS_PDF_REPLAY_PAYLOAD=/home/paul/corpus-structure/docs/design_review/evidence/2026-10-31_pdf-integrated-adoption/integration/raw/book-task86-prepared.json.gz \
  /home/paul/corpus-structure/.venv/bin/python -m pytest \
  python/corpus-structure/tests/semantic/test_pdf_integrated.py \
  python/corpus-structure/tests/semantic/test_pdf_json_publication.py \
  python/corpus-structure/tests/semantic/test_native_closure.py \
  python/corpus-structure/tests/semantic/test_schema_product_cli.py \
  python/corpus-structure/tests/semantic/test_source_views.py \
  python/corpus-structure/tests/semantic/test_integrated_consumers.py \
  -o addopts='' -q --disable-warnings --tb=short
```

After incorporating the coordinator's narrow adoption read and shared-provenance transform
correction, only unfrozen0060 was regenerated. **passed:** 20 fresh native-closure, candidate CLI
and descriptor-helper admission controls on that final authoring basis.
[Final-head output](raw/final-head.log). The coordinator separately owns the affected read/reuse
and mapping controls for those changes; the two result sets are not summed as unique coverage.

**passed:** scoped warning-inclusive Pyrefly with0 diagnostics and Ruff on the changed Python
files. [Final typing output](raw/types-final.log), [Ruff output](raw/lint.log). The type tool's
PYTHONPATH notice records the explicitly selected worktree source. The shared root interpreter
and site-packages were selected explicitly; no environment synchronization or installation ran.

## Preserved attempts and boundaries

[Initial PDF output](raw/initial-pdf-controls.log) passed35 controls. Two new helper-drift test
setup attempts are preserved: [wrong import](raw/helper-import-failure.log) and
[missing owner role](raw/helper-owner-failure.log). The test was corrected to invoke the actual
execution-admission API and perform deliberate drift as the function owner. Its expected admission
refusal remained intact and passed in the combined and final-head runs.

Current deployment descriptor SHA256 is
`4b484e59ed4d4efcff35b11d5638432181d342a3e822adea569e1ea790376e04`.
The worker used isolated pytest databases only. No production deployment, inference, section
chunking, evidence truncation, alternate graph model or full-production database clone occurred.
