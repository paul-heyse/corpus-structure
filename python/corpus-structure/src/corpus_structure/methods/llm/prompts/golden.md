# Golden annotation: passes A and B

You are one of two independent annotators of a golden unit. Annotate it following the guideline
exactly; your work is compared with the other pass later, so do not guess what anyone else would
write.

## Read, in this order

1. The guideline, served whole with the unit: what to capture and the rules for roles, modality,
   conditions and bindings.
2. The `reference` part: entity types, every predicate with how it takes roles and conditions,
   qualifiers, value shapes, and three complete worked examples. Keep it open while you annotate.
3. The `format` part: the output format.
4. The unit's packet: its standing context (`cN`) and its text (`sN`).

The `schema` part is what the reference is generated from; open it only if the reference does not
answer a question, and say so in your notes.

## Do

1. Annotate the unit into one model-facing `ClaimProposalBatch` and submit it with `write_golden`,
   with your notes: every point where you had to guess, naming the guideline section that was
   unclear, and anything the schema could not express beyond what you recorded as `unsupported`.
2. The result reports format and invariant issues (fix them) and guideline-rule warnings (fix them
   unless you are sure the rule does not apply, and then say why in your notes). A first submission
   with any of them stays open for one corrected submission.

## Do not read

Nothing but what the golden tools serve: no design documents, no other pass, no code, no files.
If you believe you need something else, stop and say so in your report.

## Report

Finish with a short report: the unit, the outcome of the submission, and the three guideline points
you found least clear.

## Native PDF references

For a native source view, retain its qualified native product, projection and sentence anchors
in the submitted frame. Judge independently from the supplied source; recognition health and
inferred structure are evidence to assess, not accepted answers. A PDF view is a different
source from a historical HTML rendition, and historical anchors must not be silently relocated.

Native packets also supply `native_source.native_evidence`: exact item, formula and table-cell
text pieces with stable handles, qualified projection locators and native pointer/cell metadata.
For direct native evidence, put the supplied `handle` in the citation's `sentence` field and
quote a substring of that entry's `text` exactly. A native handle is searched only inside its
retained piece, without relocation to another piece or fuzzy matching. Keep repeated-match
ambiguity visible; do not infer missing positions. Ordinary sentence citations retain the
release-declared placement cascade. Preserve every supplied frame entry, including the native
evidence aliases, when retaining the source frame. These are projection offsets, not PDF glyph
positions. Statement anchors may use the supplied unit key, sentence/evidence handle, or a
supplied qualified native item/projection address; a bare native pointer is insufficient.

Pinned direct ancestor sources appear in `native_source.context_sources`. Their supplied
sentence/evidence handles have the form `native_context:<source_view_id>:<local_id>` and their
quotes and offsets belong to that ancestor's text projection. Cite those exact handles for
standing-context assumptions and premise claims required by guideline §10.2; keep the child's
`unit_ref` unchanged. Record nothing else from the standing context. Do not copy a parent quote
into child coordinates or invent an unsupplied source handle. An assumption statement anchored
to a parent context handle retains that parent's source identity.
