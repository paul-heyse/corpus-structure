# `fixtures/s0`: the v1 reference as authored batches with citation frames

The S0-R2 v1 reference batches (12 spike units of `core12`) as 13 files, one per annotation unit
(foundations §3.7, package P0-F-3; coordinator decisions 2 and 6). The spike's T1 is two
annotation units, so it is two files. Consumers: S1 and S2 tests, A0 and A1 tests, C1, C3's
acceptance test, E3 (the v1 witness), I1a and F-Q6.

The authority is what an author wrote plus its frame (ADR-0019): each file holds an authored
(model-facing) batch and its citation frame, never stored offsets. The stored form is derived per
rendition by the production quote cascade (A0).

| File | Unit key (`unit_ref`) | Spike unit |
|---|---|---|
| `T1-leadin.json` | `special/LocationScale.html@p:As usual,` | T1 (lead-in paragraph) |
| `T1-dfn1.json` | `special/LocationScale.html#dfn1` | T1 (`#dfn1`) |
| `T2.json` | `special/Normal.html@p:Suppose again` | T2 |
| `T3.json` | `special/Normal.html#rel1` | T3 |
| `T4.json` | `special/LogNormal.html#dfn` | T4 |
| `U5.json` | `special/Normal.html#rel2` | U5 |
| `U6.json` | `special/Normal.html@p:Recall` | U6 |
| `U7.json` | `special/Normal.html@p:In some` | U7 |
| `U8.json` | `special/Normal.html@u:A` | U8 |
| `U9.json` | `special/LogNormal.html@u:Suppose that \(n` | U9 |
| `U10.json` | `special/Gamma.html#dfn4` | U10 |
| `U11.json` | `special/Gamma.html#rel2` | U11 |
| `U12.json` | `special/Gamma.html#mom1` | U12 |

## File shape

```json
{
  "unit_key": "<the unit segment's generated locator (D1 §3.4)>",
  "batch": { "...an AuthoredBatch; unit_ref equals unit_key..." },
  "frame": { "s1": {"locator": "<sentence locator>", "text": "<exact canonical text>"} },
  "provenance": { "spike_unit", "source", "packet", "stored_reference", "rendition", "decisions", "migrations", "split"? }
}
```

- **`frame`** maps every sentence id the batch cites (`cited_sentences`, an `outside` item's
  descriptor sentence included) to the sentence's generated locator and its exact canonical text.
  `cN` ids are the standing context's; only U12 cites one (`c1`).
- **The `outside` item** appears only in `U6.json`: `e_last_result`, an `ExternalReference` node
  (D1 §4.4, D2 §7.3) with no kind and its descriptor, the citing sentence and quote (`s2`, "the
  last result"; the source has no link there, so no `target`).
- **`provenance`** names the v1 source batch, its packet, the stored v1 reference used by the
  offset identity check, the S1 rendition (page, source URI, the spike's document and rendition
  keys, the sentence variant), the `decisions_v1.json` entries that touched the unit, the
  migrations applied, and for T1 the split.

The reader and its models are `python/corpus-structure/tests/fixtures/support.py` (`S0Fixture`).

## Conversion route

`build.py` (`uv run python fixtures/s0/build.py`) wrote these files once; the committed JSON is the
authority from then on and the script is kept only as provenance. It reads the spike results as
data and imports no spike code:

1. Each page's frozen S1 rendition (`results/s1/canonical`, `segments`, the provisional
   `sentences` the references are stored on, all in the design-spikes evidence) is rebuilt as a
   `RenditionContent`: the diagnostic attributes `tag`, `sid`, `sourceline` and `roles` are dropped
   as in `python/corpus-structure/tests/data/locators/build.py`, and the sentence segments are added
   under their parent keys.
2. The product generator (`corpus_structure.core.locators.LocatorIndex`) gives the unit key (each
   unit is checked to be one of `annotation_units()`) and each cited sentence's locator. The
   sentence offsets come from `results/s0r2/sample.json`, which records the packets' `sN` and `cN`
   numbering.
3. The batch is `results/s0r2/reference_model_v1/<U>.json` with these changes, each listed in the
   file's `migrations`:
   - `unit_ref` is the unit key, not the spike's `T1`…`U12`;
   - S4's V1: `{"t": "entity", "ref": r}` becomes `{"ref": r}` (T1's `base_variable`; U5's and
     U11's `pred` arguments), as `results/s4/validation_errors.jsonl` lists for set `v1.model`;
   - S4's V2: U6's `Statement` entity `e_last_result` becomes a `statements[]` `outside` item
     with its descriptor and no kind (P0-F-2e), keeping its local ref.
4. **T1 split.** The lead-in file holds `st1`, `Z`, `c_Z_values` and the three unsupported items
   (all on `s1`–`s3`). The `#dfn1` file holds `st2`, the definition's entities and claims, and
   redeclares `Z` (local, extent `section`) because `c_X_def` and `c_constr` bind it. Sentence ids
   stay as authored, so the `#dfn1` file cites `s4`–`s6`; the frame makes them absolute. T1's one
   decision (the removed `c_role_*` claims) is recorded on the `#dfn1` file.

Every batch converted cleanly. A check run during conversion (not kept as a test, since it reads
the S1 rendition, not a production one) found every frame resolving on the S1 rendition, every
frame text equal to the packet's `[sN]` line, and every evidence quote's exact position equal to
`reference_v1`'s stored offsets (2026-10-28).

## Checked now

`uv run pytest python/corpus-structure/tests/fixtures` (`test_fixtures.py`):
- the 13 files exist, and each validates as `AuthoredBatch` and `CitationFrame` with
  `unit_ref == unit_key`;
- every locator parses, prints back unchanged and names the file's page;
- the frame covers exactly the cited sentences, and every quote occurs in its frame text;
- every `outside` item's descriptor quote occurs in its sentence's frame text;
- each file keeps the v1 batch's items one for one (V2 counted as a move), and T1's two files
  together keep T1's items plus the redeclared `Z`, which is identical in both;
- only U12 cites the standing context.

## Pending acceptance (gated; not written as tests)

Repository policy fails rather than skips, so the gated checks are not in the test module. They
belong to the acceptance listed in `fixtures/trace/README.md`.
