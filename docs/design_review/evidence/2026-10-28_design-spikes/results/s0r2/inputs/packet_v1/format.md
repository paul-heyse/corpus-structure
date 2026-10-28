# Output format: ClaimProposalBatch, model-facing form

Write one JSON object per unit, following the model-facing form below (from D2 §7.3). Cite
evidence by **sentence id and quote**: the sentence ids are the `[sN]` labels in the unit's
packet; a quote is an exact substring of that sentence (copy LaTeX exactly as written). Do not
give character offsets.

```text
ClaimProposalBatch                   model-facing form; "stored:" notes where the stored form differs
  unit_ref            string         the packet's unit key
  entities[]          { local_ref, type ∈ enum(entity classes), label, scope ∈ {global, local},
                        extent?: statement | section        local entities only (D1 §4.2)
                        symbol?, aliases[], identity{ slot: value } }
                                     stored: adds scope_segment (segment key) for local entities
  statements[]        { local_ref, kind ∈ enum(StatementKind), anchor: "unit" | [sentence ids] }
                                     stored: anchor = [segment keys]
  claims[]            oneOf per predicate:
                        { local_ref, predicate: const <p>, subject: local_ref,
                          object: { ref: local_ref } | <value of p>,
                          qualifiers: { core qualifiers, schema qualifiers of p },
                          statement?: local_ref, statement_role?,
                          evidence[]: { sentence, quote, role } }
                                     stored: evidence[] = { start, end, role, coarse? }
  alternatives[]      { refs: [claim local_refs] (2 or more), reason }
  unsupported[]       { local_ref, sentence, quote, reason }
                                     stored: start, end instead of sentence, quote
```

Notes that are part of this format:

- `unit_ref` is the unit id given in the packet header (e.g. "U5").
- Evidence cites a sentence of the unit (`sN`) or of its standing context (`cN`) and a quote that is
  an exact substring of that sentence.
- A statement's `anchor` is `"unit"` or a list of sentence ids (`["s1", "s2"]`, or `["c1"]` for a
  context premise's assumption statement, guideline §10.2).
- `extent` on a local entity is `statement` or `section` (guideline §10.4).
- `identity` holds the class's identity slots (`reference.md` §1); an entity-valued slot is a local
  ref string: `{"family": "G", "canonical_name": "shape"}`.
- `aliases` is a list of strings.
- `scope` (a qualifier) is a string: `"statement"` or `"section"`.
- Values, bindings and condition nodes have the exact shapes in `reference.md` §5.
- `alternatives` lists groups of claim local refs that are competing readings, with a one-line reason.
- `unsupported` records text the schema cannot state: `{local_ref, sentence, quote, reason}`.
- Evidence roles: `primary`, `supporting`, `condition`, `definition`.
