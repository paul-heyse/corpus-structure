# Annotating a unit

You annotate one annotation unit at a time into one model-facing `ClaimProposalBatch`, following
the guideline exactly. Read the parts of `read_instructions` once per run: this part, `guideline`,
`reference` (entity types, every predicate with its roles and conditions, qualifiers, value shapes
and complete worked examples) and `format`; `schema` is optional, since the reference states every
shape.

## Reading a packet

`read_unit` serves the packet, possibly in several parts; read every part before you submit. A
packet has:

- a header: `# Unit <unit key>`, the page title and section path, and the statement kind the
  source marks, when it marks one;
- `## Standing context`: sentences outside the unit that it depends on, as `[cN]` lines, or
  `(none)`;
- `## Known entities`: labels already identified for this page; reuse a label when you mean the
  same thing;
- `## Text`: the unit's sentences as `[sN]` lines. Lines `--- … ---` are inner headings; they have
  no id and cannot be cited.

## Writing the batch

- Set `unit_ref` to the unit key from the header, exactly.
- Cite evidence by sentence id and an exact quote: an `sN` of the unit or a `cN` of its standing
  context, and a substring of that sentence copied exactly, LaTeX included. Never give offsets.
- Use local refs (`local_ref`) to connect entities, statements and claims within the batch.
- Keep each rationale to at most two sentences.
- Record text the schema cannot state under `unsupported`, with its reason.

## Submitting

Submit with `propose_claims(task_id, batch)`. The result lists, per item, what was rejected and
why (with a path such as `claims[3].qualifiers…`), quotes that could not be located, and guideline
warnings. A first submission with any of these stays open: fix the batch and submit once more, or,
when a warning does not apply, resubmit with a `rationale` saying why. The second submission
completes the task whatever it contains.
