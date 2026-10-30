# Citation preparation —2026-10-30

**Measured, bounded synthetic operation.** `compare.py` executes the prior cascade from
`ea2d306` and the current prepared cascade using the same installed library environment.
Run from the repository root with:

```sh
uv run python docs/design_review/evidence/2026-10-30_citation-preparation/compare.py
```

`results.json` retains three measurements per implementation/workload. Each measurement
constructs a fresh complete citation frame and locates every requested quote. Imports and
baseline loading are outside the timer; sentence slicing, preparation, tokenization, lookup,
alignment and per-occurrence reporting are inside it. Later measurements use warm Python/library
state, while each owns a new frame and empty operation caches.

One workload is one sentence/one citation. The second is 80 sentences and 400 repeated fuzzy
citations across eight cited anchors. The latter deliberately exercises operation-local reuse;
it is not a representative corpus sample or a pipeline throughput claim. Neither workload
contains macros or timeout outcomes. Independent functional tests cover those semantics.

For every citation, all `Located` fields except report-only elapsed milliseconds must equal the
baseline: absolute code-point spans, step, selected sentence, match counts, score, fuzzy edit
counts, picked flag and timeouts. This excludes no source or semantic result field.

## Mechanism disposition

Retain direct native `extractOne`: the production cascade has staged exact/regex/fuzzy fallback
and returns at its deciding step. `cpdist` would require already paired pending work;
`cdist` would materialize scores for citations that may finish before fuzzy selection. No
existing batch consumer supplies that pending-only workload. Eager Cartesian scoring would
add work and intermediate storage, so neither processor matrix API is selected here.
Native scorer identity is preserved with a typing-only cast; no scorer capsules are copied.
The existing cascade version stays1 because policies, thresholds and located-source behavior
are preserved.

This evidence does not establish assembled PE-12 qualification or a corpus-wide speedup.
