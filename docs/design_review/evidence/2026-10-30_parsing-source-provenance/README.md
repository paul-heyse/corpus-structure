# HTML5 source-provenance seams

**Scoped Tested · 2026-10-30.** This PP-02 investigation selects narrow instrumentation
of the pinned html5lib 1.1 tokenizer and lxml 6.1.3 tree builder as the next implementation
route. It demonstrates useful positive hooks without replacing HTML5 tokenization or tree
construction. It does **not** qualify PP-03's complete original-to-canonical product.

Run from the repository root:

```sh
uv run python docs/design_review/evidence/2026-10-30_parsing-source-provenance/probe.py
```

**passed:** nine bounded cases; observed output is [result.json](result.json). The
[probe](probe.py) asserts normalized cursor lengths, retained duplicate attribute occurrences,
independent literal token envelopes, the buffered-text origin bridge, explicit synthetic
`tbody`, a formatting clone, encoding restart, and decoder contribution coverage. Native
instrumented/uninstrumented lxml serialization and parser diagnostics are identical in these
cases. That comparison establishes preservation against the pinned implementation; it is not
an independent proof of WHATWG correctness or corpus compatibility.

## Observations and selected seams

1. **Tokenization remains upstream.** `TrackedParser._parse` injects a tokenizer subclass;
   `TrackedTokenizer.__iter__` observes the existing state loop. No tokenizer state or HTML5
   tree-construction phase is copied. These are private/version-bound seams: production
   ownership must review `_parse`, `__iter__`, stream consumption and the relevant native
   phase when changing html5lib. No global monkeypatch is needed.
2. **A cursor proxy can account for reconsume.** `char`, `charsUntil` and `unget` track offsets
   in the native newline-normalized decoded representation. Undoing ownership on `unget`
   and assigning the final consuming state preserves the observed source extent. The UTF-8
   case independently asserts `<P A="x" a='y' empty="">`, multibyte text, CRLF normalization,
   both a single-character and multicodepoint character reference, an end tag and a comment.
   Emission position alone would not supply these starts. `emitCurrentToken` can preserve the
   pre-deduplication attribute list: both `a` occurrences survive in the sidecar while native
   DOM semantics retain the first value. Original capitalization and quoting are sliced from
   the retained buffer rather than inferred from those already-normalized attribute names.
3. **State consumption supplies an implementable lexical classification seam.** The probe
   emits a complete, coalesced partition of its normalized representation and recognizes
   attribute names, values, quotes, equals signs, separators, tag names/delimiters, comments,
   doctypes, text and character references in the exercised states. This uses the existing
   state machine; it is not a second parser. The classifier is deliberately bounded and is
   **not** the full vocabulary implementation. All tokenizer states, error paths, entity
   consumption within attribute values and shared-state multi-token emissions must receive
   deliberate categories before claiming complete supported lexical distinctions. A fallback
   `unknown` retains evidence but cannot stand in for that work. Token envelopes with multiple
   outputs from one state are marked `shared_state_output`; they must not be promoted to
   separate exact source occurrences merely because they have the same enclosing span.
4. **Tree mutation hooks retain distinguishable node occurrences.** Per-operation subclasses
   of the lxml builder's element class observe element construction, insertion, removal,
   `insertBefore`, `cloneNode`, `insertText` and `reparentChildren` while calling native methods.
   Implied `html`/`head`/`body`/`tbody` have no lexical source-token identity. The adoption case
   records a new clone occurrence and its source node, rather than aliasing the occurrences.
   The probe records mutation events; it does not yet maintain final text-slot lineage.
5. **Buffered table text has a narrow positive bridge.** A current-token association is wrong:
   `<table>a&amp;b<tr><td>x</table>` inserts joined `a&b` while processing `<tr>`. However,
   `InTableTextPhase.characterTokens` still contains the original marked token dictionaries.
   A subclass wrapping **only `flushCharacters`** pushes their ordered IDs around the native
   join and insertion, then restores the context. The assertion establishes source IDs
   `[1, 2, 3]` for `a&b`, while the active token is `4`. This preserves origin through this
   buffering mechanism without copying its algorithm or aligning strings afterward.
6. **Decoding can remain a separate adapter.** Native selection is preserved with
   `useChardet=False`; the cases cover UTF-8 BOM, windows-1252, UTF-8 replacement and a late
   meta declaration causing a windows-1252 → UTF-8 restart. The restarted parse has its own
   source pass and cursor; abandoned pass tokens must not enter the final product. A separate
   incremental-codec candidate retains grouped byte-to-decoded contributions and an explicit
   BOM exclusion. The malformed UTF-8 bytes `E2 41` produce the grouped contribution `�A`,
   illustrating why one byte ↔ one codepoint is invalid. Replacement output is a declared
   decoding result, not a claim that the decoded text equals the original bytes. The selected
   cases reconstruct native decoded text and cover all input bytes. They do not establish all
   HTML encodings or codec streamreader equivalence for every malformed sequence.

The probe deliberately uses per-character diagnostic observations and a byte-at-a-time decoder
so its mechanism is inspectable. **Production should retain immutable buffers and merged
contribution runs**, not persist an event/row per character or dispatch work per byte. Cursor
tracking can aggregate bulk `charsUntil` regions, and emission/state transitions can delimit
runs. No performance claim follows from this probe.

## Concrete implementation responsibilities

The evidence supports a qualified partial producer using these seams now. A full producer still
needs the following connected work; these are implementable responsibilities, not an assertion
that a library feature is absent:

- Complete the state-to-category table and lexical occurrences, including attribute entities,
  empty values, malformed tags, raw-text/RCDATA/foreign tokenization and ambiguous multi-output
  state spans. Preserve raw spelling independently of normalized token values. Validate actual
  categories with independent extents, rather than only reconstruction.
- Compose original-byte decoder contribution groups with pre-normalization decoded extents and
  CRLF/CR → LF contributions. Discard abandoned pass products, preserve restart diagnostics,
  and qualify the admitted encoding/error-policy set. The probe verifies lengths, not this full
  composed map. A partial adapter must state its encoding support and refuse exact consumers
  outside it.
- Replace mutation-only logs with final per-node text/tail contribution runs. Update them at
  native insertions, coalescing, foster insertion, cloning and `reparentChildren`; retain
  explicit synthetic/derived lineage. Account for parser transformations such as dropping the
  first newline in `pre`/`textarea` and ignoring NUL rather than treating a subset as a full
  token copy. The positive table flush wrapper is required in addition to generic tree hooks.
- Emit canonical contribution sets **inside** existing whitespace/NFC processing and canonical
  serialization. Separators/markers receive producing-rule origins; exclusions retain source
  extents and reasons. This probe does not exercise source-profile exclusions, macro custody
  or canonical serialization and supplies no fabricated maps for them.
- Integrate the resulting immutable product with PP-01 enforcement, PP-04 build-specific storage
  and restricted publication/read selection. An unavailable origin is explicit. A consumer
  requiring exact full provenance must refuse a partial product.

None of these findings justifies switching to an independent HTML parser by default. The pinned
native algorithm remains viable for narrow instrumentation; no broad copied tokenizer/tree
algorithm was necessary for the positive mechanisms tested. Complete maintainability and
coverage remain obligations of the implementation, not established by nine cases.

## Sources and evidence limits

Context7 was resolved and queried on 2026-10-30 (`/html5lib/html5lib-python`) for custom
builders, exact positions and reparsing. Its result correctly distinguishes parser error
positions from absent token/node extents. Consequential behavior was checked against the
installed pinned sources and these corresponding tagged upstream locations:

- [`HTMLParser._parse` / `InTableTextPhase.flushCharacters`](https://github.com/html5lib/html5lib-python/blob/1.1/html5lib/html5parser.py)
- [`HTMLTokenizer.__iter__` / `emitCurrentToken` and states](https://github.com/html5lib/html5lib-python/blob/1.1/html5lib/_tokenizer.py)
- [`HTMLBinaryInputStream.changeEncoding` / newline normalization](https://github.com/html5lib/html5lib-python/blob/1.1/html5lib/_inputstream.py)
- [Native lxml builder and clone behavior](https://github.com/html5lib/html5lib-python/blob/1.1/html5lib/treebuilders/etree_lxml.py)
- [Native text/tail insertion and reparent behavior](https://github.com/html5lib/html5lib-python/blob/1.1/html5lib/treebuilders/etree.py)

The fixture set includes UTF-8/multibyte/BOM, CRLF, replacement, windows-1252, late encoding
restart, duplicate and empty quoted attributes, character references, comments/doctype,
script raw text, SVG CDATA, implied `tbody`, foster parenting, a formatting clone and malformed
unclosed markup. It is a bounded feasibility investigation, not complete HTML5, corpus,
production pipeline, database or provider qualification. PP-02 can use this selected route;
PP-03's complete mapping acceptance remains open.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**parsing-pipeline**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Native HTML5 source-provenance instrumentation seams](records/html.provenance-seams.json) | PP-02 | partial | PP-02, ADR-0036 | 2026-10-30 |
<!-- evidence-index:end -->
