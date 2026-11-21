# Cutover and qualification

**Status:** Proposed. Companion of [Set-based execution](../set-based-execution_2026-11-21.md).
**Created:** 2026-11-21.

This companion owns how the series lands: the native revisions, regeneration, retirement and the
assembled evidence. It owns SBX-20 to SBX-22.

## Cutover policy

Direct cutover (operator, 2026-11-21). No compatibility layer and no dual shapes. Products of
every changed kind are regenerated through the new path; retained products of the old shapes are
not read by the new code. Data is regenerable, and the cost of the pivot is regeneration and one
qualification.

**Testing during development** follows the repository's rule: compile checks and targeted
functional tests for the scope just implemented, no integrated gate after a slice. Native
candidates are authored against the working database with rollback-only authoring until a
revision is registered.

## Native revisions

A revision is needed when installed programs, the physical model, privileges or descriptors
change. A change to the model and Python alone needs the release re-prepared, not a revision.

| Revision | Carries | Why together |
|---|---|---|
| A, identity | Partition table and admission; rule and proof tables, form evaluators, establish routine, required proofs in binding; the reference carrier in admission and completion programs; projection digests in binding and attachment; retirement of the projection family tables, their checks and readers | Each changes what a product body holds or what a request key hashes. Product ids and request keys move once. |
| B, reads | The outputs, partitions, derivation-facts and proofs programs; the support export's relation list; the read closure membership | Program changes with no identity change; outstanding receipts and cursors are invalidated once. |
| C, PDF | The paged row read for the rebuild; access derivation and the reduced checker; staging without build columns and the adopt program; typed capture reads | Lowering identity and the standard producer contract move once. |

Revisions A and C are independent and may be registered in either order. B follows A, since the
partition and proof programs read A's tables.

*Alternative rejected.* A revision per package: each identity-changing package would regenerate
and re-key everything downstream again, and outstanding receipts would be invalidated repeatedly.

<a id="sbx-20"></a>
## SBX-20 — Register the revisions and regenerate

**Order of regeneration.** PDF capture and publication under revision C; then the operation
chains under A in dependency order, each product admitted with its partitions and proofs;
reads and exports under B. The retained book's project binding is recreated, not migrated.

**Checks at each registration.** The repository's native candidate comparison shows only the
programs the revision intends to change; the release prepares under the new kernel; a fresh
target installs from the chain.

**Evidence.** For each revision: the candidate comparison, with the list of changed programs
matching the table above; installation on a fresh target; and one end-to-end run of the smallest
real unit the revision affects (one source view through one chain for A; one selected read and
one export with verification for B; one document's capture, publication, validation and a
recovery for C).

<a id="sbx-21"></a>
## SBX-21 — Retirement sweep

Each package removes what it supersedes. This package removes what no single package owns and
confirms nothing was left behind.

- Code with no production caller that the review recorded: `evaluate/record_statistics.py`;
  `evaluate/alignment_preparation.py` and `semantic_values.py` with the parts of
  `semantic_alignment.py` that only they reach; the per-frame identity read; the unused parts of
  `semantic/record_projection.py`, after a reader search at the execution head. The
  `select_pdf_integration` path stays while the streaming reconciliation tests use it as their
  independent check.
- Smaller items: the recognition replay's duplicated sort-key column; the stale duplicate of the
  duckdb hold in `docs/pins.md`; the served-row codec's reference to a disk tier.
- A search, made once and not added to the repository checks, for each retired name: the member
  packet classes, the reference classes, the SQLite read index, the receipt format, the
  projection family tables.
- Design sections and decision records that describe the retired mechanisms are updated in the
  commits that retire them; this package confirms the collection reads true.

**Evidence.** Importing every production module succeeds. The searches find no reference to a
retired name outside history. The documentation check passes.

<a id="sbx-22"></a>
## SBX-22 — Assembled qualification

Qualification establishes that the assembled system works and that the design does what it was
built to do. It is run once, on final source, after the revisions are registered.

**Functional.** The repository's functional and check routes on final source, with results
accounted for by identity as the repository requires. Real providers are exercised where the
changed paths reach them: spaCy and HanLP for the first populations, Docling for the PDF path.

**The whole book.** The retained book is processed end to end through the new path, with a
controlled interruption and an unchanged repeat that produces no new work.

**The four change scenarios.** These are the evidence for the design's two tests. Each states its
expectation from the declarations before it is run.

| Scenario | Expectation |
|---|---|
| A rule's parameter is edited and the release re-prepared | That rule's fingerprint changes and no other. The establish routine evaluates that rule on each partition once. No product id, request key or other proof moves. No operation re-runs. |
| A model field read by one rule and no consumer is edited | The rule's fingerprint changes. Consumers' keys are unchanged, and no operation re-runs. |
| An upstream product changes only in a field group a consumer does not read | The consumer's request key is unchanged and its existing derivation attaches with no new attempt. A consumer that reads the group re-runs. |
| One block of a source document changes | Its partition digest changes and no other. Block-local producers run for that block (if SBX-07 is adopted). Proofs for unchanged partitions still match. A consumer keyed on the whole collection re-runs. |

**The point check.** Establishing one rule for one partition, and resolving one reference, each
decode at most one partition; asserted by counting decodes and database statements.

**What qualification does not claim.** No timing or capacity statement is made without a
measurement with its conditions. The scenarios show that work is avoided, counted in operations,
evaluations and decodes; they do not put a figure on time saved.

**Completion.** The series is complete when the evidence above is recorded, the kernel trial's
decision is recorded, and the owning design sections and decision records describe the
implemented state.
