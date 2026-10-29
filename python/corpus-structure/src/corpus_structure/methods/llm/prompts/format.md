# Output format: ClaimProposalBatch, model-facing form

Write one JSON object per unit in the model-facing form below (D2 §7.3). Cite evidence by
**sentence id and quote**: the ids are the packet's `[sN]` and `[cN]` labels, and a quote is an
exact substring of that sentence (copy LaTeX exactly as written). Do not give character offsets.

```text
ClaimProposalBatch                   model-facing form; "stored:" notes where the stored form differs
  unit_ref            string         the packet's unit key
  entities[]          { local_ref, type ∈ enum(entity classes except Statement), label, scope ∈ {global, local},
                        extent?: statement | section        local entities only (D1 §4.2)
                        symbol?, aliases?, identity?{ slot: value } }
                                     stored: adds scope_segment (segment key) for local entities
  statements[]        { local_ref, kind ∈ enum(StatementKind), anchor: "unit" | [sentence ids] }
                      | { local_ref, anchor: "outside", descriptor: { sentence, quote, target? } }
                                     an ExternalReference (D1 §4.4); sentence: the citing sN or cN
                                     stored: anchor = [segment keys] | "outside", descriptor = { start, end, coarse?, target? }
  claims[]            oneOf per predicate:
                        { local_ref, predicate: const <p>, subject: local_ref,
                          object: <entity ref {ref}> | <value of p>,
                          qualifiers: { core qualifiers, schema qualifiers of p },
                          statement?: local_ref, statement_role?,
                          evidence[]: { sentence, quote, role } }   sentence: sN of the unit or cN of its standing context
                                     stored: evidence[] = { start, end, role, coarse? }
  alternatives[]      { refs: [claim local_refs] (2 or more), reason }
  unsupported[]       { local_ref, sentence, quote, reason }
                                     stored: start, end instead of sentence, quote
  (optional fields are absent, never null)
```

Notes that are part of this format:

- `unit_ref` is the unit key in the packet header.
- Evidence cites a sentence of the unit (`sN`) or of its standing context (`cN`) and a quote that is
  an exact substring of that sentence.
- A statement's `anchor` is `"unit"` or a list of sentence ids (`["s1", "s2"]`, or `["c1"]` for a
  context premise's assumption statement, guideline §10.2).
- A statement the unit refers to but that lies outside it ("the last result", a cited "[14]") is a
  `statements[]` item with `anchor: "outside"` and no `kind`: an external reference whose
  `descriptor` gives the citing sentence (`sN` or `cN`), the quote that refers to it and, when the
  text gives one, the link `target`.
- `extent` on a local entity is `statement` or `section` (guideline §10.4).
- `identity` holds the class's identity slots (the reference, §1); an entity-valued slot is a local
  ref string: `{"family": "G", "canonical_name": "shape"}`.
- `aliases` is a list of strings.
- `scope` (a qualifier) is a string: `"statement"` or `"section"`.
- Values, bindings and condition nodes have the exact shapes in the reference, §5.
- `alternatives` lists groups of claim local refs that are competing readings, with a one-line
  reason.
- `unsupported` records text the schema cannot state: `{local_ref, sentence, quote, reason}`.
- Evidence roles: `primary`, `supporting`, `condition`, `definition`.
- Optional fields are absent, never null.
