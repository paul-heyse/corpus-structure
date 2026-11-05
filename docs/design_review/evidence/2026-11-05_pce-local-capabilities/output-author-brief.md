# Independent output-first source authoring

Use only the named source-only author packet. A and B work independently. C reads
that same packet plus the exact A/B files, records their SHA-256 hashes and gives
reasons for every conflict and correction. Do not inspect private product captures,
producer values/scores/targets, database contents, implementation, old references,
grades or other evidence. Frozen output IDs are withheld; use interest IDs only.

For every interest, answer one of its available facets from the complete native
items and governing context. The supplied extent locates the question; it is not
an assertion of correctness. Table-cell pointers require inspecting the complete
table, headers, same-row structure and ancestors. Preserve native text exactly,
including whitespace, Unicode and half-open character offsets.

`judgment` describes support/determinacy of your **source expectation**, never
correctness of the hidden output. Use `supported`, `unsupported`, `ambiguous` or
`unassessed`. Use `source_state` `stated`, `unstated`, `unresolved` or `uninspected`.
If no independent rubric or sufficient source subject is available, explain an
honest `unassessed` result. Do not force a class, role, relation or grouping.

Return JSON with this shape (replace placeholders):

```json
{
  "protocol": "pce07-independent-output-answers-1",
  "actor": "independent-A-or-B-or-C",
  "model": "actual model",
  "source_packet_sha256": "SHA256 of the exact source-only packet bytes",
  "cases": [{
    "interest_id": "packet interest ID",
    "selected_facet": "one packet available_facet",
    "source_state": "stated",
    "judgment": "supported",
    "inspected_scope": ["complete native pointers and governing context inspected"],
    "primary": [{"pointer": "native pointer", "precision": "exact", "start": 0, "end": 1, "text": "exact source text"}],
    "alternatives": [{"fields": {"semantic_type": "independently supported declared type"}}],
    "explanation": "source evidence and reasoning",
    "limitations": []
  }],
  "limitations": []
}
```

Every interest appears exactly once, including unassessed interests. Item-level
pieces use `{"pointer":"…","precision":"item"}` without text/offset claims.
Use `source_view_id` only when citing a packet's related source rather than its
primary source. Every exact piece needs its exact `text`, `start` and `end`.

- Literal fidelity: exact independent primary pieces suffice; do not infer entity
  class or contextual role from a correct literal/location.
- Entity classification: independently choose `fields.semantic_type` from
  `entity.distribution`, `entity.quantity`, `entity.condition` when supported;
  ambiguity, no supported class and insufficient context remain expressible.
- Conditional role: use `fields.value` as the plain label `defined_term` or
  `mentioned_term`, anchored to the actual located mention. Missing discovery is
  a different population. Add `anchor_endpoint_role: "mention"` and, where class
  is independently assessed, an `endpoints` entry with `role: "mention"`, its
  independently authored `anchors` and `fields.semantic_type`.
- Directed association: each alternative supplies `anchor_endpoint_role`,
  independently supported `fields.semantic_type` and an ordered `endpoints`
  array of `{"role":"declared role","anchors":[pieces],"fields":{}}`.
  Primary pieces equal the named primary port's pieces. Independently locate the
  governing target and qualifiers; do not assume a cue establishes attachment.
- Grouping and captured syntax: assess only a question the packet's rubric and
  source permit. Captured text is not original glyph fidelity, recognition,
  interpretation or scientific truth. Insufficient questions remain unassessed.

Alternative structures may provide different exact `primary` pieces. Expected
fields support `semantic_type`, plain source `value`, exact `source_pieces`,
`source_field_state` and `anchor_role`. Never author generated IDs or model scores.
For unassessed answers, `alternatives: []` is valid; retain scope and reasons.

C additionally supplies `author_inputs: [{"path":"A file","sha256":"…"},
{"path":"B file","sha256":"…"}]` and `adjudication_reasons` covering all
conflicts, retained alternatives, corrections and unresolved limitations.

## Source evidence and compared literal fields

`fields.source_pieces` means a list of plain literal strings owned by the selected
product at its independently authored primary anchors. For a directional
association, contextual justification belongs in `alternative.supporting_source_pieces`
as exact native piece objects. These are validated, preserved in protected case
provenance and frozen source scope; they are not silently discarded or compared
as product-owned literals. The endpoint-association facet does not establish
capture of all governing qualifiers or a complete scientific statement. Preserve
those qualifiers as source evidence and state that separate assessment limit;
if the chosen question cannot be answered under that limit, retain uncertainty.
A representation clarification preserves the original raw author file and names
its exact hash in `source_format_revision`.
