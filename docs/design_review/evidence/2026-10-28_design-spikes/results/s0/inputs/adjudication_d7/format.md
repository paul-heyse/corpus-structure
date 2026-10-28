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
- `extent` on a local entity is `statement` (scoped to the statement that binds it) or `section`
  (the enclosing section, from the binding sentence on), as D1 §4.2 and the guideline describe.
- Values are D1 §6 tagged objects (`{{"t": "formula", "latex": "…", "symbols": {{…}}}}` etc.);
  condition trees are D1 §7 nodes keyed by `op`; `claim` nodes and symbol bindings use local refs.
- `alternatives` lists groups of claim local refs that are competing readings of the same text,
  with a one-line reason (guideline §10.8).
- `unsupported` records text the schema cannot state, with a reason (guideline §10.5).
- Evidence roles: `primary`, `supporting`, `condition`, `definition` (D1 §5.1).
