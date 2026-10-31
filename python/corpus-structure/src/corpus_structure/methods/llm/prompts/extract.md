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

## Native PDF source packets

A native packet carries `native_source` with its immutable product/projection pins, section
ancestry, items, table cells, formulas, captions and recognition health. These are structured
source observations. Inferred block labels and recognized LaTeX do not establish mathematical
truth. Use the supplied qualified anchors; do not manufacture HTML locators or convert formula
boxes into character positions. Read all transport pages of the intact section. Pinned source
inspection and optional region rendering can clarify evidence without changing its identity.

`native_source.native_evidence` lists direct evidence entries for retained native text pieces.
Each entry supplies a `handle`, its native `pointer`, optional `cell_index`, `source_field`,
exact `text`, and a qualified projection `locator`. Put that supplied handle in evidence's
`sentence` field and copy a substring of that entry's `text` exactly. This places the quote
only within that item, formula or table cell piece; it cannot relocate into another piece or
use fuzzy matching. Repeated matches retain their reported ambiguity; do not guess a location.
The supplied offsets describe the retained text projection, not PDF glyph positions. Ordinary
sentence ids continue to use the release-declared evidence placement cascade.

For a statement's `anchor`, use the supplied unit key, sentence id, native evidence handle,
or supplied qualified native item/projection address. Preserve its product/view pins; do not
construct an anchor from a bare `#/...` pointer.

Pinned direct ancestor sources appear in `native_source.context_sources`. Their supplied
sentence/evidence handles have the form `native_context:<source_view_id>:<local_id>` and their
quotes and offsets belong to that ancestor's text projection. Cite those exact handles for
standing-context assumptions and premise claims required by guideline §10.2; keep the child's
`unit_ref` unchanged. Record nothing else from the standing context. Do not copy a parent quote
into child coordinates or invent an unsupplied source handle. An assumption statement anchored
to a parent context handle retains that parent's source identity.
