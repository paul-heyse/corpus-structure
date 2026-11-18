# Design principle audit

The living diagnostic account maintained by the
[audit skill](../../../.claude/skills/design-principle-audit/SKILL.md). The
[repository binding](../design_principles/binding/corpus-structure.md#design-principle-audit)
owns freshness and disposition. This account diagnoses current design; reviews own solution
reasoning, and implementation plans own scheduled work and closure evidence. It certifies
nothing and authorizes no change.

<a id="baseline"></a>

## Baseline

| Item | Inspected state |
|---|---|
| Date | 2026-11-17 |
| Audited source | `fbd3f2a98362da44d9c9bdb9f59bab1ff305bd36`, committed `main`, clean tree. Contributors read a frozen export of that commit, so cited lines are exact for it. The operator stated during the audit that production edits were in progress; later source is outside this refresh |
| Excluded | The untracked `docs/libraries/analytical_infrastructure/cachetools.md` (read as a library overview, not audited); the migration trees beyond their shape; Chandra OCR as scheduled work |
| Standard | Core 3.3; efficient-architecture heuristics 1.0; code-intelligence 1.4; repository binding. Test-assessment 1.2 applies through the test account |
| Previous broad baseline | `67cbe680e` (2026-11-08), about 2,000 commits earlier, followed by ten scoped refreshes to 2026-11-12. All of that text is in Git at `fbd3f2a98` |
| Kind | Broad refresh by static source reading. No test, database command, provider call or benchmark was run |
| Emphasis (operator, 2026-11-17) | The comprehensive domain data model, and efficiency of execution, assessed together with the [test account](../test-audit/README.md) at the same commit |
| Publication | The commit that publishes this account, distinct from the audited source |
| Scoped refresh, 2026-11-18 | `d78c98765b2543a0a86515134257259debe75dfd`, committed `main`, read in a frozen export of that commit. DA-068 to DA-081, DA-033 and DA-058 were re-read, and the typed-program and generator layer was audited as new scope. The 27 earlier identities not re-examined are unchanged. Static reading only. See [the refresh](#refresh-2026-11-18) |
| Update, 2026-11-18 | `5139eaba3097e457574feb9daef58c1c49dcc150`, committed `main`, read in a frozen export of that commit, 127 commits after the scoped refresh. Every production finding, DA-001 to DA-086, was re-read, and the reference inventories were rebuilt. Static reading only. This is the current baseline of every topic page. See [the update](#update-2026-11-18-5139eaba3) |

The refresh of 2026-11-17 replaced the stacked scoped entries of the earlier README with one
current account. It was needed because the declared-data-operations work replaced most of the code
those entries described: since the 2026-11-12 entry, 364 production files were added, 149
deleted and 307 modified, and the owners cited by the earlier domain model map were removed on
2026-11-16.

Observations on the topic pages are **Interface-checked by source inspection, 2026-11-18**, at
`5139eaba3`, unless a sentence says it was read earlier, in which case it keeps the date it
gives. Nothing here is labelled Tested or Measured. Counts state their method, and statements
of cost are structural: counts of repeated work read from code paths, never timings.

<a id="update-2026-11-18-5139eaba3"></a>

## Update of 2026-11-18 at `5139eaba3`

**Kind.** A full re-read of every production finding, DA-001 to DA-086, against source
`5139eaba3097e457574feb9daef58c1c49dcc150`, which is 127 commits after the last refresh at
`d78c98765`. In that range 113 production files changed: the admission modules were
regenerated as typed programs, the directory `semantic/sql/` was removed, and the native stage
advanced from revision N13 to N29. The last eleven files of that directory were removed in
commit `c25cada3f`, whose message describes a documentation change; the deletion was another
session's staged work. The three reference inventories (identities, caches and
prepared state, fact ownership with library roles) were rebuilt, and the analytical map was
updated row by row. **Interface-checked by source inspection, 2026-11-18.** Static reading
only: no test, database command, provider call or benchmark was run, and nothing is Tested or
Measured. The standard versions are those of the [baseline](#baseline).

Five read-only contributors read a frozen export of the commit: one each for identity and
reuse (DA-068, 069, 075 to 078, 082, 083, 033, 058), model authority (DA-070 to 074, 081, 085,
086), generators and remaining SQL (DA-079, 080, 084 and the analytical delta), and the older
identities in two halves (DA-001 to 040 and DA-041 to 067). For the older identities each
contributor took the original diagnosis from its first publication in Git and then looked, by
name and by concept, for the same structural cause in the code that replaced the cited
subject. The lines that decide a status on DA-068 to DA-086, and the current sites of each
recurrence among the older identities, were then checked again in the snapshot; where a
contributor marked a statement as inferred or low-confidence, the page keeps that label.

### Status of all 86 identities

Six status words are used. *Corrected, holds*: a recorded correction was checked and still
describes the code. *Partly corrected*: part of the cause was removed and part remains.
*Changed footprint*: the cause is found at different sites than those first cited. *Stands*:
the diagnosis holds, with "wider" or "changed footprint" in the note where that applies.
*No longer applicable*: the subject was removed and the cause was not found in its
replacement. *Superseded*: a newer finding is now the home of the cause.

| Finding | Status at `5139eaba3` | Note |
|---|---|---|
| [DA-001](semantic-model-and-authority.md#da-001) | Changed footprint | The per-predicate qualifier lists are compiled and validated, and nothing reads them |
| [DA-002](semantic-model-and-authority.md#da-002) | Superseded | By DA-072, with DA-085 and DA-086; the reference-split divergence no longer applies |
| [DA-003](semantic-model-and-authority.md#da-003) | Partly corrected | Roles are read through declared subsets; three subsets are unread and one evidence role is a literal |
| [DA-004](semantic-model-and-authority.md#da-004) | Changed footprint | Each rich consumer still decodes raw annotation strings (36 sites) |
| [DA-005](semantic-model-and-authority.md#da-005) | Corrected, holds | Context translations are owned by the rule-view module |
| [DA-006](semantic-model-and-authority.md#da-006) | Corrected, holds | References are typed by a declared role and foreign keys |
| [DA-007](semantic-model-and-authority.md#da-007) | Corrected, holds | Identity decisions are typed; the outcome set is written three times (low weight, DA-086) |
| [DA-008](semantic-model-and-authority.md#da-008) | Corrected, holds | Case is folded only where declared |
| [DA-009](semantic-model-and-authority.md#da-009) | Partly corrected | Determinants have one owner; the Unicode parity check has no caller, and canonical JSON has two implementations |
| [DA-010](semantic-model-and-authority.md#da-010) | Corrected, holds | Closed acquisition manifest |
| [DA-011](semantic-model-and-authority.md#da-011) | Corrected, holds | For the version restatement; the whole design collection was not examined |
| [DA-012](structure-and-invariants.md#da-012) | Superseded | By DA-072 and DA-086 |
| [DA-013](structure-and-invariants.md#da-013) | Partly corrected | The CLI classifies failures; domain code still mostly refuses with plain errors; DA-079 is an instance |
| [DA-014](structure-and-invariants.md#da-014) | No longer applicable | Locator machinery removed (`48be40472` and earlier); an unused branch is footprint of DA-080 |
| [DA-015](structure-and-invariants.md#da-015) | No longer applicable | `consolidate/finalize.py` removed (`9268b15bf`) |
| [DA-016](structure-and-invariants.md#da-016) | No longer applicable | Policy routes removed (`a49758618`) |
| [DA-017](structure-and-invariants.md#da-017) | No longer applicable | `orchestrate/semantic.py` removed (`8b7b369a9`) |
| [DA-018](boundaries-and-composition.md#da-018) | Corrected, holds | Extension versions pinned and reconciled; read from source, not provisioned |
| [DA-019](boundaries-and-composition.md#da-019) | No longer applicable | To this account: owned by the test account, not checked here |
| [DA-020](boundaries-and-composition.md#da-020) | Changed footprint | Analytics resource settings are declared and unread; principal names moved to DA-074 |
| [DA-021](local-reasoning-and-assurance.md#da-021) | Corrected, holds | Evidence citations have a resolver (file present; not run) |
| [DA-022](local-reasoning-and-assurance.md#da-022) | Corrected, holds | The dependency check covers the uv workspace and Cargo |
| [DA-023](local-reasoning-and-assurance.md#da-023) | Corrected, holds | The binding map is populated |
| [DA-024](execution-fit.md#da-024) | No longer applicable | `semantic/publication.py` removed (`47dc7b873`) |
| [DA-025](execution-fit.md#da-025) | No longer applicable | Rendition keying is off the current path; the surviving module belongs to DA-072 and DA-080 |
| [DA-026](semantic-model-and-authority.md#da-026) | Partly corrected | Binding is a compiled release product; a raw-YAML `is_a` inference and name defaults remain |
| [DA-027](semantic-model-and-authority.md#da-027) | Stands | As a limit: enforcement claims are typed, and almost all are documentation |
| [DA-028](semantic-model-and-authority.md#da-028) | Changed footprint | The source-demand path reads the working tree's `slices.yaml`, not the release's archived copy |
| [DA-029](native-integrity.md#da-029) | Corrected, holds | Mechanism changed: triggers are generated from the declared immutability class |
| [DA-030](native-integrity.md#da-030) | Corrected, holds | Explicit per-purpose credentials and a native principal check |
| [DA-031](native-integrity.md#da-031) | Corrected, holds | Extended to indexes |
| [DA-032](native-integrity.md#da-032) | Partly corrected | Results carry kernel digests, not the deployment; the open question goes with DA-068 |
| [DA-033](execution-fit.md#da-033) | Changed footprint | Substance stands: the release guard is fully generated and performs the same re-proof per call |
| [DA-034](semantic-model-and-authority.md#da-034) | Corrected, holds | One scientific owner; the successor issue is DA-077 |
| [DA-035](served-claims.md#da-035) | No longer applicable | `serve/journey.py` removed (`bcff594c2`); successor checked lightly |
| [DA-036](served-claims.md#da-036) | No longer applicable | `semantic/query.py` removed (`957ff2231`); served rows carry a per-population standing label; a per-fact selection status was not examined |
| [DA-037](served-claims.md#da-037) | No longer applicable | `evaluate/semantic.py` removed (`7fc25ca02`); successor evaluation not examined |
| [DA-038](served-claims.md#da-038) | No longer applicable | Read modules removed (`bcff594c2`); a private cursor codec is a low-weight residue |
| [DA-039](served-claims.md#da-039) | No longer applicable | Explanation and path queries removed (`5aae3c780`, `bcff594c2`); successor reads are bounded |
| [DA-040](structure-and-invariants.md#da-040) | Partly corrected | Establishment is checked; unbounded decimal expansion persists: the hand-written body at `d78c98765` was equally unbounded and was transcribed; the Python codec is unbounded too |
| [DA-041](structure-and-invariants.md#da-041) | No longer applicable | Run and task machinery removed (`64455a0f1`, `8b7b369a9`); the cause does not recur |
| [DA-042](execution-fit.md#da-042) | Changed footprint | Partly corrected: readers open releases; full derivation remains at registration, basis and setup sites |
| [DA-043](execution-fit.md#da-043) | No longer applicable | Owners removed (`64455a0f1`, `47dc7b873`); the successor's scaling was sampled, not audited |
| [DA-044](structure-and-invariants.md#da-044) | Corrected, holds | At new sites: representatives are a named policy |
| [DA-045](boundaries-and-composition.md#da-045) | Changed footprint | The legacy packages are gone; upward imports recur at new sites; the contract half is DA-072 |
| [DA-046](semantic-model-and-authority.md#da-046) | Stands | An open boundary question: the semantic core still holds statistics and mathematical vocabulary |
| [DA-047](boundaries-and-composition.md#da-047) | Superseded | By DA-080, which now records the two recurring sites |
| [DA-048](semantic-model-and-authority.md#da-048) | Changed footprint | Partly corrected: shared inputs coalesce; an unshared input and its check are still read by root name only |
| [DA-049](semantic-model-and-authority.md#da-049) | Corrected, holds | By decision: ADR-0047 declares current-only operation |
| [DA-050](served-claims.md#da-050) | No longer applicable | Explanation adapters removed (`bcdc8d214`, `bcff594c2`); reads bind an exact demand |
| [DA-051](served-claims.md#da-051) | Corrected, holds | Identity assurance and labelled assertions; not traced end to end |
| [DA-052](boundaries-and-composition.md#da-052) | No longer applicable | Nothing imports the producer binding; the leftover modules are footprint of DA-080 |
| [DA-053](structure-and-invariants.md#da-053) | Corrected, holds | At new sites: claims are owned on commit; a small inferred residual in hydration |
| [DA-054](execution-fit.md#da-054) | Superseded | By DA-078, with DA-069 |
| [DA-055](witnessed-enrichment.md#DA-055) | Corrected, holds | Separate axes for attachments that can apply together |
| [DA-056](witnessed-enrichment.md#DA-056) | Corrected, holds | Corrected in `f3f2d1ca5`; the page's "open" note was stale; the native counterpart was removed |
| [DA-057](witnessed-enrichment.md#DA-057) | Corrected, holds | Member identity includes interpretation and applicability |
| [DA-058](execution-fit.md#da-058) | Stands | Unchanged; no commit to its owners; Chandra remains outside scope |
| [DA-059](boundaries-and-composition.md#da-059) | Corrected, holds | Managed receipts carry the acquired target, effects and cleanup state |
| [DA-060](boundaries-and-composition.md#da-060) | Corrected, holds | Promotion refuses unless custody is settled |
| [DA-061](served-claims.md#da-061) | Corrected, holds | Corrected in `8dc0bac00`: a list of witnesses, resolved from the retained release |
| [DA-062](semantic-model-and-authority.md#da-062) | Corrected, holds | The native codec is generated from the LinkML layout and keeps field positions |
| [DA-063](native-integrity.md#da-063) | Corrected, holds | The expectation is selected by the acquired revision or body fingerprint |
| [DA-064](served-claims.md#da-064) | Corrected, holds | A skip requires every cue to be negative |
| [DA-065](semantic-model-and-authority.md#da-065) | Changed footprint | Independent native witness verification was retired; the production producer always attaches a witness and admission checks the attested CPU reply, so the scenario is not reachable today |
| [DA-066](served-claims.md#da-066) | Corrected, holds | Selection is pushed into the native read; the scan's cost was not examined |
| [DA-067](native-integrity.md#da-067) | Corrected, holds | Analysis compiles the captured physical sources |
| [DA-068](execution-fit.md#da-068) | Stands | Wider: 99 captured modules by a stated method that the challenge reproduced; native revision N29 changed no generated statement and restamped two digests; the shared seal builder did not narrow the key |
| [DA-069](execution-fit.md#da-069) | Stands | One module was added by hand to a view operation's sources |
| [DA-070](semantic-model-and-authority.md#da-070) | Stands | Changed footprint and wider: twelve lists; early-return guards skip an unlisted operation (confirmed at the guard sites, not end to end) |
| [DA-071](semantic-model-and-authority.md#da-071) | Stands | Three encodings; the change-impact disagreement is unchanged; a narrow fourth walk was located |
| [DA-072](semantic-model-and-authority.md#da-072) | Stands | Unchanged; 41 importing modules at both commits |
| [DA-073](semantic-model-and-authority.md#da-073) | Stands | Slightly wider: one more hand-added source |
| [DA-074](native-integrity.md#da-074) | Stands | Changed footprint: role literals moved from SQL files into more Python modules, and the total fell from 246 to 199; no role, guard or grant fact entered the model |
| [DA-075](execution-fit.md#da-075) | Stands | Unchanged; no commit to the key sites |
| [DA-076](served-claims.md#da-076) | Stands | Unchanged; the ordinary-edit case occurred in the range |
| [DA-077](served-claims.md#da-077) | Stands | Unchanged; no commit to its owners |
| [DA-078](execution-fit.md#da-078) | Stands | Changed footprint: a role-matched component was added; the operation-granular component and the kernel component remain |
| [DA-079](boundaries-and-composition.md#da-079) | Stands | Unchanged; no commit to its owners |
| [DA-080](boundaries-and-composition.md#da-080) | Partly corrected | Changed footprint: three groups removed; six stand; six items added, among them a preview explanation that walks a removed directory and a native fitting path with no caller |
| [DA-081](semantic-model-and-authority.md#da-081) | Stands | Wider: more hand-listed names and a new dependency on boundary-comment text; the scratch-table transform is corrected |
| [DA-082](execution-fit.md#da-082) | Stands | Unchanged list; both the too-narrow and the too-broad half were exercised in the range |
| [DA-083](execution-fit.md#da-083) | Stands | Unchanged in structure; each rebuild is larger |
| [DA-084](boundaries-and-composition.md#da-084) | Partly corrected | Hand-written SQL fell from about 3,700 lines (about 2,430 inside Python and 1,293 in sixteen `.sql` files) to about 180; one small item remains; its consequence moved to DA-070 and DA-074 |
| [DA-085](semantic-model-and-authority.md#da-085) | Stands | Unchanged; the kernel generators receive table metadata only |
| [DA-086](semantic-model-and-authority.md#da-086) | Stands | Wider in count. The task guard already read the declared lifecycle; its conversion to a typed program belongs to DA-084 |

| Status | Count | Identities |
|---|---|---|
| Corrected, holds | 29 | 005, 006, 007, 008, 010, 011, 018, 021, 022, 023, 029, 030, 031, 034, 044, 049, 051, 053, 055, 056, 057, 059, 060, 061, 062, 063, 064, 066, 067 |
| Partly corrected | 8 | 003, 009, 013, 026, 032, 040, 080, 084 |
| Changed footprint | 9 | 001, 004, 020, 028, 033, 042, 045, 048, 065 |
| Stands | 20 | 027, 046, 058, 068, 069, 070, 071, 072, 073, 074, 075, 076, 077, 078, 079, 081, 082, 083, 085, 086 |
| No longer applicable | 16 | 014, 015, 016, 017, 019, 024, 025, 035, 036, 037, 038, 039, 041, 043, 050, 052 |
| Superseded | 4 | 002, 012, 047, 054 |
| Total | 86 | |

A search that finds nothing does not show that a cause is absent, and "no longer applicable"
is firm for the removed subject only; the topic pages say where a successor was examined
lightly or not at all.

### New findings

None. No new identity was assigned, and the next new identity remains DA-087. The contributors
proposed four candidate causes; each has a home in an existing identity, so none was opened:

| Candidate | Home |
|---|---|
| Typed construction without a fact owner: statements are generated, while family, entry-point, role and state facts are transcribed per module | [DA-070](semantic-model-and-authority.md#da-070), [DA-074](native-integrity.md#da-074) and [DA-086](semantic-model-and-authority.md#da-086) |
| A statement boundary recovered from emitted comment text | [DA-081](semantic-model-and-authority.md#da-081) |
| The preview's SQL change explanation bound to a removed directory | [DA-080](boundaries-and-composition.md#da-080) |
| Frozen revisions that each freeze the full catalog state again, and that call live verifiers | Recorded as facts for the lifecycle owner under [DA-080](boundaries-and-composition.md#da-080) and [DA-032](native-integrity.md#da-032) |

Five earlier identities gained a full section because their cause was found at current sites:
[DA-028](semantic-model-and-authority.md#da-028),
[DA-001](semantic-model-and-authority.md#da-001),
[DA-004](semantic-model-and-authority.md#da-004),
[DA-040](structure-and-invariants.md#da-040) and
[DA-020](boundaries-and-composition.md#da-020); and
[DA-065](semantic-model-and-authority.md#da-065) has one that states what was lost and what
still holds.

### Revised diagnostic synthesis

**The observation of the previous refresh still holds, in sharper form: the conversion changed
how statements are written, and relations and columns now come from the model, but not where
membership facts come from.**

- *What the conversion achieved.* Hand-written SQL inside Python modules fell from about 2,430
  lines to about 180, and the sixteen `.sql` files (about 1,290 lines) went to none: about
  3,700 lines became about 180. Two counting methods, the contributor's and the challenger's,
  agree on the figures inside Python. What is left is mostly permitted control SQL and SQLite
  ([DA-084](boundaries-and-composition.md#da-084)). Statements in the regenerated admission
  modules are built with typed APIs, and a renamed column or relation now fails at generation.
- *What did not move.* The membership facts those statements use (operation-family lists,
  entry points, role tuples, state literals) are still hand lists in Python. The model gained
  no family or role declaration. Role-name literals moved from the deleted SQL files into
  Python: 199 occurrences in 47 modules now, against 176 in 39 modules plus 70 in `.sql` files
  at `d78c98765`, so 246 before and 199 now ([DA-074](native-integrity.md#da-074)). The
  generators receive only table metadata, so no operation fact can be derived where the
  statements are built ([DA-070](semantic-model-and-authority.md#da-070),
  [DA-085](semantic-model-and-authority.md#da-085)). This is the consequence, predicted in
  the previous refresh, of converting before declaring. It is not a divergence from ADR-0131,
  whose decision governs physical types and call correspondence.
- *The fail-open shape remains.* An unlisted operation is still treated as valid: by a null
  family and a default-true dispatch as before, and now also by early returns in several
  family guards, which skip an operation that is not on their list (confirmed at the guard
  sites, not end to end; DA-070).
- *What a declared fact looks like when it governs.* The task guard already read the declared
  lifecycle before the range and is now a typed program over captured columns; two guards
  select by a declared effect, and four operation families already declare such an effect
  (DA-070). These show the pattern the family lists lack.
- *Identity.* The kernel digest is wider (99 captured modules by a stated method). Native
  revision N29 is an instance of digest-only churn in installed objects: it changed no
  generated statement and restamped two digests, the kernel digest and the source hashes of
  four authoring modules recorded in the execution-contract descriptor
  ([DA-068](execution-fit.md#da-068)). The rebuild of the native capture at every acquisition
  is unchanged ([DA-083](execution-fit.md#da-083)).
- *The older identities.* Of DA-001 to DA-067, 29 are corrections that hold and 16 no longer
  apply. The causes that recur do so in two families that match the findings above: a
  declaration that governs nothing or is decoded by each consumer (DA-001, DA-004, DA-020), and
  an input or check that is outside the identity it is attributed to (DA-028, DA-048). Two are
  value and failure boundaries (DA-040, DA-013).

The three recurring causes of the 2026-11-17 synthesis stand. The integrated argument, with
the rebuilt inventories and the analytical map, is on the [joint page](model-and-execution.md);
the current owner of every model fact, and where the model is open and where the kernel closes
it, are on the [domain model map](domain-model-map.md).

### Relation to the test account

The [test account](../test-audit/README.md) was refreshed on 2026-11-18 by another engagement,
at a different source commit, and is not edited here
([its refresh](../test-audit/README.md#tdm-refresh-2026-11-18)). That refresh touches three
production subjects of this account: test readers of the removed SQL files now use their
generating owners (the test side of [DA-084](boundaries-and-composition.md#da-084) and
[DA-080](boundaries-and-composition.md#da-080)); test obligations that depend on a finer
production identity or validity stay with the production owner (the subject of
[DA-068](execution-fit.md#da-068), [DA-069](execution-fit.md#da-069) and
[DA-070](semantic-model-and-authority.md#da-070)); and a test that assumes an input the
selected operation never declares is kept as evidence of an open production prerequisite. The
test account does not cite these DA identities by number; the correspondence is this account's
reading, and nothing from it is duplicated here.

### Limits of this update

- **Not read.** Generator bodies for equivalence with the SQL they replaced; most regenerated
  module bodies beyond the functions cited; migration revision bodies other than N29;
  `semantic_alembic/` contents; `schema/model_change.py` (no commit in the range); the serving
  consumers of the query cache beyond their key lines; change impact; established validity;
  tests.
- **Not established.** Replay volumes and the cost of one replay or one capture rebuild; call
  counts per run; what layers beyond the family guards do with an unlisted operation; whether
  a third query encoder would in fact be refused; whether native admission of
  local interpretation reports is still needed (DA-056); the NaN item of DA-040; whether
  `public_disclosure` enters the cut pins.
- **Counted by script or search.** Every count states its method on its page. The SQL-text
  counts undercount lowercase or fragmented SQL. "No caller" rests on searches of `src`,
  `tests` and `scripts`; dynamic imports were not excluded.
- **Not rerun.** The probes of 2026-10 (canonical JSON numerics among them). Successors of
  several removed subjects were sampled, not audited (DA-035, DA-037, DA-043, DA-044).
- **Reported figures that were reconciled.** One contributor counted role names by lines (166
  in 47 files) and another by occurrences (199 in 47 files); occurrences is the method of the
  earlier 176 and is the one used, together with the 70 occurrences that sat in `.sql` files
  at `d78c98765`. One contributor counted 28 names in the authoring capture list and another
  32 over a longer range; 28 is the count of the module-name tuple.
- **Not examined by the challenge.** Generator bodies for equivalence beyond the N28-to-N29
  byte identity; DA-033, 042, 045, 048, 071 to 073, 075 to 079, 081, 082 and 085 beyond their
  status lines; the analytical delta; the library-roles table; the successors of the removed
  subjects; and the older identities outside its sample of 21.

<a id="update-challenge"></a>

### Independent challenge

A separate reviewer challenged the drafted pages before publication. It formed each view from
source first, with its own recounts (a second SQL counting method, a static count of the
captured modules, an object-by-object comparison of the N28 and N29 revisions) and its own
reading of the cited lines at `5139eaba3`, with a read-only export of `d78c98765` as the
baseline; it opened the contributors' reports only afterwards. Nothing was run. Its effect:

- **Confirmed:** the main synthesis. Membership facts are hand lists, the model gained no
  family or role declaration, an unlisted operation is treated as valid at the sites cited,
  the capture holds 99 modules, and the acquisition check rebuilds it and ignores the release.
- **Corrected or narrowed, four claims.** The SQL recount now states both populations (about
  3,700 lines to about 180, not only the lines inside Python). Native revision N29 is
  presented as digest-only churn in installed objects with two restamped digests, not as a
  revision that existed only to restamp; the plan gives it a purpose, and the masking caveat
  was dropped because every substitution maps one to one. Role names did not rise: they moved
  from SQL files into Python, 246 before and 199 now. And `methods/llm/producer.py` has a test
  importer, so it has no production importer, not no importer.
- **One status withdrawn:** DA-086 is not partly corrected. The task guard read the declared
  lifecycle already at `d78c98765`; its conversion to a typed program belongs to DA-084.
- **One item moved to another finding:** the `operation_fitting` calls are dead code that
  calls functions the deployed tree does not define, so they left DA-084, which now has one
  real remaining item, and joined DA-080.
- **One identity's status changed:** DA-065, from possibly regressed to changed footprint. The
  production producer always attaches a witness and admission checks the attested reply; what
  was lost is the independent enforcement at three retired sites.
- **Counts corrected** to match: 8 partly corrected, 9 with a changed footprint, 20 standing.
- **Added:** under DA-070, that policy authorization also selects by a declared effect and
  that four families already declare a native effect per operation; under DA-068, a second
  stamped identity (the authoring-source digests, identity inventory row 30) and
  ADR-0092 `:27`; and smaller fixes to DA-040, DA-036 and two fact-ownership rows.

### Sound designs added in the range

- Relation and column resolution against captured metadata in every regenerated module, with
  raw SQL text and unresolved bind parameters refused by the compiler
  (`semantic/native_program.py:128–131`).
- The task guard, which already read the protocol lifecycle, as a typed program over the
  captured task columns (`semantic/data_operation_protocol.py:117–128`).
- The typed catalog-verification conversion of native revision N29 produced generated output
  byte-identical to N28's, which is evidence that it preserved behavior.
- Selection by a declared effect read from the lowered definition
  (`semantic/rich_admission_native.py:1136–1145`;
  `semantic/record_policy_completion_native.py:425–441`), operation constants taken from the
  operation's owner module, and one table shared by the Python validator and the native
  generator (`semantic/declared_structural_admission.py:276`).
- A closed-set check at generation of the structural disclosure fields
  (`semantic/structural_admission_native.py:1680–1694`).
- Declared variability: read-selection variants and an explicit undisclosed authority state in
  the protocol, the `public_disclosure` column, and `collection: set` read from the role
  ([map](domain-model-map.md#openness)).
- The shared seal builder, one definition used by the writer and the checker (`b294ab4e2`).
- Cancellation bound to each CPU invocation, with the shared mutable request global removed
  (`semantic/cpu_execution.py:359`; `5c5443d16`).
- Generators that take the captured physical metadata; the content-keyed companion projection
  holder; native selection asset custody through verified files (`188ec73c2`).
- Release admission generated predicate for predicate, with its receipt recorded only if
  absent; shared typed catalog observation (`semantic/native_catalog.py`).
- Scratch relations retargeted on the parse tree (`semantic/native_authoring.py:303–328`), and
  the source-admission capture program inserted by locating a parsed declaration, with no
  marker (`semantic/data_operation_source_native.py:69–77`).
- Set-wise improvements: independent optional binding roles selected without a cross product
  (`1d3640990`); access edges and the archived model materialized once per call
  (`66c36d4c8`, `a31503daf`).

<a id="refresh-2026-11-18"></a>

## Refresh of 2026-11-18 at `d78c98765`

**Superseded as the current statement by the
[update at `5139eaba3`](#update-2026-11-18-5139eaba3).** This was a scoped refresh at
`d78c98765b2543a0a86515134257259debe75dfd`, 163 commits after the delta below. It re-read
DA-068 to DA-081, DA-033 and DA-058, audited the typed-program and generator layer as new
scope, and added DA-082 to DA-086. Its status table, new-findings table, synthesis and limits
were replaced by those of the update and are in Git at the publication of that refresh. What
remains below is the record of its independent challenge, which shaped DA-081, DA-084 and
DA-085, and its list of sound designs. One statement of that refresh is corrected by the
update: the kernel capture was described as "about 75 to 85" modules, which was an undercount
by the method now stated ([DA-068](execution-fit.md#da-068)).

<a id="refresh-challenge"></a>

### Independent challenge

A separate reviewer challenged the drafted pages before publication. It read source at
`d78c98765` and the plans and decision records first, did not read the contributors' reports,
and tried to refute each new finding, each status claim and samples of the three inventory
tables. Its effect:

- **Reframed:** DA-084. The drafts had taken the conversion to be complete and presented the
  remaining hand-written PostgreSQL as a defect outside ADR-0131. The ADR and the DDO plan
  record it as open, scheduled work. The finding now states that, and offers what the plan
  lacks: the inventory, the fact that model changes do not reach it, and that it holds the
  family and role lists.
- **Narrowed:** DA-085. Two authoring routes for operations compiled into one effective model
  is the accepted decision of ADR-0092 and moved to contrary evidence. The finding is now the
  per-consumer LinkML composition and the constraints held as JSON strings.
- **Merged:** a drafted finding on text as the handoff between generation and installation
  was folded into DA-081, since both come from the absence of a typed registry of programs.
  The refresh therefore adds five identities, not six.
- **Withdrawn:** the claim, in DA-080 and DA-081, that installation dispatches on a stale
  `scientific_layout.sql` key. The name is a label for a generated artifact.
- **Corrected:** DA-081's contrary evidence (the required-set check accepts an unexpected
  artifact, and omits six that are concatenated, which is now part of the footprint); DA-070's
  statement that a second list was new; DA-086's field-kind item (the model does declare it);
  DA-082's earlier entry count and the consequence stated for one omitted module; and counts
  of hand-written SQL lines, splice sites, operation-declaring modules, role-name occurrences
  and concatenated artifacts.
- **Re-located:** three facts whose generators the drafts had not found (the renew program;
  that a directly revoked producer cannot be rehabilitated; that only revocation takes an
  exclusive lock on the trust scope).
- **Nothing else refuted.** DA-082, DA-083 and the status claims for DA-068, DA-072, DA-074,
  DA-075 and DA-080 were confirmed. DA-071, DA-073, DA-076 to DA-079, DA-033 and DA-058 were
  spot-checked by line only.
- **Not checked by the challenger:** the analytical section, the production-efficiency state
  table and the superseded planned-change table on the joint page; generator bodies for
  equivalence; `domains/`.

### Sound designs worth preserving

As recorded at `d78c98765`; line references are of that commit. The designs added since are
listed [above](#update-2026-11-18-5139eaba3).

- The semantic request key, which excludes release and runtime
  (`semantic/binding_admission_native.py:213`).
- The program compiler's rule that Core and parsed nodes own statements and the compiler owns
  only procedural framing, with raw text refused (`semantic/native_program.py:1–5, 126–131`).
- Server-side normalization and static checking in a rollback-only scope, exact frozen
  statements and catalog snapshots in migration custody, and deployment that imports no
  generator (`semantic/native_objects.py:1–5, 950–1121`).
- Derivations that already work and show the pattern: immutability and archive triggers from
  declared classes; physical value sets from the protocol; protocol function grants from
  declared purposes; the SourceValue codec's closed-set check against LinkML; universe validity
  read from a typed literal; Arrow schemas for PDF records and exports from compiled metadata
  ([map](domain-model-map.md#strengths)).
- The read kernel pin, which turns kernel drift into reacquisition instead of a wrong answer
  (`semantic/data_read_boundary_native.py:84–92`).
- File custody with stat identity, and query custody's loader that compiles exactly the hashed
  bytes and refuses a reload (`semantic/file_custody.py:79–137`; `_query_custody.py:136–200`).
- The capture's required-set check and its equality check against the physical model
  (`semantic/data_operation_storage.py:569–692`), and generated bytes captured beside their
  generators.
- The rich assets' identity over the parsed meaning of a module, the finest implementation
  identity in the codebase (`semantic/python_module_projection.py:111–120`).
- The selected-query cache's byte accounting and immutable encoded entries; wire-protocol
  caches keyed by content; deployment expectations cached by file digest and stat.
- Submitted read-only SQL admitted through a parsed allowlist and bound by PostgreSQL in a
  read-only transaction (`semantic/authored_sql.py`).
- Per-invocation DuckDB connections with private spill directories and cancellation checks,
  and DuckDB used through its relational API with no SQL text.

<a id="delta-1afa63f88"></a>

## Delta of 2026-11-17 at `1afa63f88`

A scoped re-read, not a refresh. `main` moved 34 commits from `fbd3f2a98` to
`1afa63f883f07873c8b4d3cccb9fc6622b558d50` (70 production files changed) while the model-owned
SQL conversion ([ADR-0131](../../adr/0131-model-owned-postgresql-programs.md)) was in progress.
Only DA-068 to DA-080, DA-033 and DA-058 were re-read, in a frozen export of the pin.
**Interface-checked by source inspection, 2026-11-17.** Nothing was run. Later commits and
uncommitted work are outside this delta.

The conversion so far changes how statements are written, not where their facts come from. The
hand lists behind DA-070, DA-071 and DA-074 are all still in place.

| Finding | Status at `1afa63f88` |
|---|---|
| [DA-068](execution-fit.md#da-068) | Wider: generators, three model files and three library versions joined the digest; the program layer also joined the PDF lowering identity |
| [DA-069](execution-fit.md#da-069) | Stands; footprint grew |
| [DA-070](semantic-model-and-authority.md#da-070) | Stands unchanged (`semantic/sql/data_operations.sql:345–353, 2311–2328`). The "typed validity" commits convert product validation, a different mechanism |
| [DA-071](semantic-model-and-authority.md#da-071), [DA-072](semantic-model-and-authority.md#da-072), [DA-073](semantic-model-and-authority.md#da-073) | Stand; cited code unchanged. The new generators read only the released model |
| [DA-074](native-integrity.md#da-074) | Stands; statement rendering changed, membership lists did not |
| [DA-033](execution-fit.md#da-033) | Changed footprint; substance stands |
| [DA-080](boundaries-and-composition.md#da-080) | Partly corrected (one of fourteen unreferenced SQL files deleted) |
| [DA-078](execution-fit.md#da-078) | Indirectly wider, because its watermark includes the kernel digest (inferred) |
| DA-075, 076, 077, 079, 058 | Not affected by the diff |
| [DA-081](semantic-model-and-authority.md#da-081) | New: generated native facades registered a second time by hand |

Eighty-one DA identities existed after this delta. Sound designs added in the range, worth preserving:
rendering that refuses raw SQL text and requires each step to parse as one statement
(`semantic/native_program.py:87–122`); generated bytes kept in custody beside their generators;
captured metadata refused when it differs from its inputs
(`semantic/data_operation_projections.py:2474–2479`); one generated wire validation point;
typed CHECK and index predicates compared with the bound catalog; one type table for
declarations and grants (`semantic/native_call_contracts.py`).

Not read: the large generator bodies for equivalence with the SQL they replace, the DuckDB
modules, and whether PDF search reads carry a served implementation identity. What the
remaining planned steps would do to these findings is on the
[joint page](model-and-execution.md#planned-change), which the
[refresh of 2026-11-18](#refresh-2026-11-18) has since superseded.

## Scope and method

The functional target is unchanged: progressively enriched, attributed source knowledge under
an executable domain release, delivered through typed interfaces to one operator and to agents
on one host. The development workload is one 518-page book. Agents reach the system through
the `ci` CLI, which runs one process per command, and through a long-lived MCP server.

Five read-only contributors each read one area against a shared set of ten questions: four on
the domain model (what is declared, what is restated by hand, where scope is decided without
the declared dependencies, whether each identity is complete for what it keys), four on
execution (what repeats while its inputs are unchanged, what is examined in whole where a
subset is known, the facts of every cache and prepared holder, where assurance is re-proved or
dropped), and two on where they meet (which model facts could key or invalidate work, and
which caches key on something the model does not govern).

| Area | Read |
|---|---|
| Model declaration and compilation | Model owners, the compiler and effective model, wire generation, static preparation, release preparation |
| Dependency, validity, reuse, change impact | Change impact, projections, the demand planner, established validity, demand results, the validity and closure SQL |
| Execution host and method runtime | The process host and executor, CPU execution, native model hosts, math and construction grammars, PDF capture and recognition |
| Native storage, admission, publication | Storage, ports, admission, installation, PDF publication and reading, the admission and binding SQL |
| Serving, evaluation, CLI | The query cache and its six consumers, query custody, the archive reader, reporting, scientific evidence, the MCP servers, CLI entry |

The coordinator read the decisive source behind each published finding, checked stored test
results where a finding claimed a test could not pass, and reconciled candidates by structural
cause across both accounts. A fresh reviewer then challenged the draft against source before
publication; its effect is recorded under [Independent challenge](#independent-challenge).

## How the foundations were assessed

- **FP-04 / A2, domain model and semantic authority (priority).** By mapping where each kind of
  fact is declared, compiled and realized ([domain model map](domain-model-map.md)), then
  looking for the same meaning held twice and for decisions taken without the declaration.
  Findings: [DA-070](semantic-model-and-authority.md#da-070),
  [DA-071](semantic-model-and-authority.md#da-071),
  [DA-072](semantic-model-and-authority.md#da-072),
  [DA-073](semantic-model-and-authority.md#da-073), [DA-074](native-integrity.md#da-074),
  [DA-076](served-claims.md#da-076), [DA-077](served-claims.md#da-077).
- **FP-07 / A4, execution fit (priority).** By following what a change invalidates and what a
  repeated request recomputes, using H5 (smallest sufficient scope), H12 (stable preparation
  kept apart from changing values), H13 (identity matched to what varies), H18 and H19
  (assurance placed once and carried while its premises hold) and H21 (shared capacity).
  Findings: [DA-068](execution-fit.md#da-068), [DA-069](execution-fit.md#da-069),
  [DA-075](execution-fit.md#da-075), [DA-078](execution-fit.md#da-078),
  [DA-033](execution-fit.md#da-033), [DA-058](execution-fit.md#da-058).
- **FP-01 / FP-03, responsibility and composition.** By asking which code still has a consumer:
  [DA-080](boundaries-and-composition.md#da-080).
- **FP-02, contracts.** The wire boundary validates once on each side and the native read has
  one entry point; no new finding.
- **FP-05, explicit failure.** [DA-079](boundaries-and-composition.md#da-079); and the fail-open
  direction of DA-070.
- **FP-06, local reasoning.** Addressed mainly through the test account. On the production
  side, the hand lists of DA-070, DA-073 and DA-074 are what a reader cannot infer locally.
- **Code-intelligence profile.** Pinned serving (CI-13) and attributable evidence (CI-10, CI-11)
  informed DA-076, DA-077 and the contrary evidence for DA-068. Unknown is kept distinct from
  absent in the served reports read.

## Diagnostic synthesis

This is the synthesis of 2026-11-17 at `fbd3f2a98`. The
[update of 2026-11-18](#update-2026-11-18-5139eaba3) revises it for `5139eaba3`; figures below
such as "about forty modules" are those of the earlier reading. The integrated argument, with
the test account, is on the [joint page](model-and-execution.md). In brief:

- **The model's core is sound and should be preserved.** One compiled model per release, typed
  origins, refusal of conflicting owners, and a result identity that excludes release and
  runtime. Where a dependency is expressed through that identity, reuse is exact.
- **Run-time governance is not yet in the model.** Which validity rules apply to an operation,
  what a support edge means, which relations are guarded, and which code an answer depends on
  are held as hand-written lists. An omission from the validity lists fails open (DA-070).
- **Several identities are far coarser than their premise.** A digest over about forty modules
  stands for the kernel; whole files and library versions stand for an operation's
  implementation; the read instance stands for the content of a served result. Each discards
  valid work on an unrelated edit, and the first also forces indefinite re-validation of
  history.
- **Two identities are narrower than their premise.** The served implementation identity and
  the scientific policy both miss code that shapes results.
- **Immutable release content is re-proved on every admission and binding** although receipts
  that record the proof already exist.
- **The new query cache rarely hits** on five of its six paths, and never for the CLI, because
  of how it is keyed and because every cache in the system is process-local.

## New and changed findings

Summaries are current at `5139eaba3` ([update](#update-2026-11-18-5139eaba3)). This table
lists the findings established since the broad refresh of 2026-11-17 and the earlier
identities whose cause was found at current sites. The status of every identity is in the
[status table](#update-2026-11-18-5139eaba3).

| Finding | Summary |
|---|---|
| [DA-068](execution-fit.md#da-068) (stands, wider) | One digest over every captured native source, 99 modules and six library versions, keys admission, read acquisition and carried assurance; native revision N29 changed no generated statement and restamped two digests in installed objects |
| [DA-069](execution-fit.md#da-069) (stands) | Implementation identity of construction and formal operations takes whole files, whole model files and library versions |
| [DA-070](semantic-model-and-authority.md#da-070) (stands, changed footprint and wider) | Validity families are assigned from twelve hand-written lists of operation ids; an unlisted operation is treated as valid, and family guards return early for it |
| [DA-071](semantic-model-and-authority.md#da-071) (stands) | Support-graph meaning is encoded three times and the change-impact copy disagrees |
| [DA-072](semantic-model-and-authority.md#da-072) (stands) | The earlier core and system model is still live, with the same closed sets declared in both |
| [DA-073](semantic-model-and-authority.md#da-073) (stands, slightly wider) | Release operation membership is composed by hand-written flag logic |
| [DA-074](native-integrity.md#da-074) (stands, changed footprint) | Native authorization and guard membership, including role names and execute grants, are code lists outside the declaration; role literals moved from SQL files into more Python modules, and their total fell from 246 to 199 |
| [DA-075](execution-fit.md#da-075) (stands) | Five of six query cache keys include the acquisition instance, so identical fresh requests do not share an entry |
| [DA-076](served-claims.md#da-076) (stands) | The implementation identity of a served read omits modules that shape the answer |
| [DA-077](served-claims.md#da-077) (stands) | The archived scientific policy describes the kernel instead of deriving from it |
| [DA-078](execution-fit.md#da-078) (stands, changed footprint) | The readiness watermark is coarser than the declared role dependencies; a role-matched component was added beside the coarse one |
| [DA-079](boundaries-and-composition.md#da-079) (stands) | The process host refuses a second concurrent run with an unclassified error |
| [DA-080](boundaries-and-composition.md#da-080) (partly corrected, changed footprint) | Superseded machinery remains, kept alive only by tests or by nothing; the model preview's SQL change explanation walks a removed directory, so its empty result reads as "no SQL change"; a native fitting path with no caller calls functions the deployed tree does not define |
| [DA-081](semantic-model-and-authority.md#da-081) (stands, wider) | The native program set and its generated outputs have no typed registry: they are listed by hand in several places and their facts, now including a statement boundary, are recovered from text |
| [DA-082](execution-fit.md#da-082) (stands) | The PDF lowering identity is a hand-kept file list with no completeness check, at once too narrow and too broad |
| [DA-083](execution-fit.md#da-083) (stands) | The native source capture has no holder and no file custody, and is rebuilt at every acquisition |
| [DA-084](boundaries-and-composition.md#da-084) (partly corrected) | The conversion of hand-written PostgreSQL: statement text is almost all converted (about 3,700 lines to about 180), one small item remains, and the hand-held facts moved into Python lists that are the footprint of DA-070 and DA-074 |
| [DA-085](semantic-model-and-authority.md#da-085) (stands) | The LinkML part of the released model is composed separately by each consumer, holds its physical constraints as JSON strings, and is not one object with the effective operation model |
| [DA-086](semantic-model-and-authority.md#da-086) (stands, wider) | Generators and analytical modules restate as Python literals facts that the model declares or that a typed source already carries; the task guard, which reads the declared lifecycle, remains the one counter-example |
| [DA-033](execution-fit.md#da-033) (changed footprint) | Admission and binding re-prove immutable release content |
| [DA-058](execution-fit.md#da-058) (stands) | Visual recognition re-prepares its runtime every four packets |
| [DA-028](semantic-model-and-authority.md#da-028) (changed footprint) | The source-demand path reads the working tree's `slices.yaml`, matched to the release by name only, while the release archives its own copy |
| [DA-040](structure-and-invariants.md#da-040) (partly corrected) | Unbounded decimal expansion persists in the native canonicalizer, transcribed from an equally unbounded hand-written body, and in the Python codec |
| [DA-001](semantic-model-and-authority.md#da-001) (changed footprint) | Per-predicate qualifier lists are compiled and validated but govern nothing |
| [DA-004](semantic-model-and-authority.md#da-004) (changed footprint) | Each rich consumer decodes raw release annotation strings for itself |
| [DA-020](boundaries-and-composition.md#da-020) (changed footprint) | Analytics resource settings are declared and read nowhere, and the DuckDB limits are literals |
| [DA-065](semantic-model-and-authority.md#da-065) (changed footprint) | The witness of a named or geometry definition basis is no longer verified independently; assurance moved to producer attestation, and the unwitnessed scenario is not reachable through production admission today |

Eighty DA identities existed at `fbd3f2a98`, eighty-one after the [delta](#delta-1afa63f88),
and eighty-six after the [refresh of 2026-11-18](#refresh-2026-11-18), which added DA-082 to
DA-086. The [update at `5139eaba3`](#update-2026-11-18-5139eaba3) added none, so eighty-six
exist; none is reused, and the next new identity is DA-087. All eighty-six were re-read at
`5139eaba3`: 29 are corrections that hold, 8 are partly corrected, 9 have a changed footprint,
20 stand, 16 no longer apply and 4 are superseded by a newer finding. Of DA-001 to DA-067
alone: 29 corrected, 6 partly corrected, 9 with a changed footprint, 3 standing, 16 no longer
applicable and 4 superseded. Each topic page
lists its own.

<a id="deviations"></a>

## Limits

- **Read in part or not at all.** Most model YAML bodies and the generators; `ontology.py` and
  `conditional_rules.py`; the planner's batch, settle and hydrate bodies; family validators
  other than contextual; most PDF storage and record SQL bodies; the GLiNER, HanLP and PM2
  method bodies; `cli/model.py`, `cli/managed.py` and `cli/schema.py`; consolidation and the
  rich rule evaluator; every migration revision except the most recent.
- **Not established.** Whether equal outputs stop recomputation below the formal operations;
  whether a content-based cache key is sound; whether any relation is wrongly outside the
  frontier guard; whether concurrent MCP renders actually overlap; how large any of the
  repeated work is. Each finding states its own uncertainty.
- **Not run.** Product tests, native or provider runs, fault injection, measurement and
  integrated qualification. Several commits that introduced the mechanisms read here record
  `runtime not_run`; this account judges their design, not whether they currently pass.
- **Inherited.** None at `5139eaba3`: every identity was re-read in the
  [update](#update-2026-11-18-5139eaba3), whose own limits say where a successor was only
  sampled. The limits in this list are those of the broad refresh of 2026-11-17.

<a id="independent-challenge"></a>

## Independent challenge

A fresh reviewer, given the criteria and the drafted pages but not the contributors' reports,
opened the cited sources and tried to refute each new finding and each "corrected" or "no
longer applicable" claim. Its effect on the published account is recorded here.

- **Withdrawn:** none.
- **Reframed as documented choices:** DA-068 (the plan chose the kernel digest for the seal and
  the full battery on mismatch; the finding is now what that digest covers and one divergence
  from the plan), DA-078 (the watermark's granularity is the plan's specification) and DA-079
  (one run per host is ADR-0125's stated trade).
- **Corrected:** DA-070's claim that the other lists fail closed (an omission fails open at
  completion too), with the consequence now split by family; DA-071's statement of which
  projection the planner consumes, and the divergence shown to run both ways; DA-080's count of
  unreferenced SQL files (fourteen, not twelve); DA-069's list of captured files; three line
  references in the earlier-identity tables.
- **Narrowed:** DA-075 from six paths to five, because the exclusion comparison keys on content
  stamps and can hit; that also shows the "open premise" is already relied on once. DA-058's
  mechanism: building the runtime only hashes the checkpoints, and the model load follows on
  first inference.
- **Sharpened:** DA-033 (the finalization receipt is read immediately before the re-proof it
  could carry).
- **Removed as a residual:** the release being derived at registration and again per host
  basis, which the production-efficiency review records as a deliberate boundary.
- **Confirmed as drafted:** DA-072, DA-073, DA-076, DA-077.
- **Not checked by the challenger:** the domain model map beyond a skim, and the PE-F12, F14
  and F24 rows of the state table.

## Reading routes

| Topic | Current use |
|---|---|
| [The domain model and execution](model-and-execution.md) | Integrated analysis with the test account; cache inventory; identity inventory; analytical and set-wise computation; state of the production-efficiency mechanisms |
| [Domain model map](domain-model-map.md) | Declaration owners, composition, compiler paths, what generators receive, what is generated from what, LinkML features used, fact ownership and data-model library roles, and where the model is open and the kernel closes it, at `5139eaba3` |
| [Semantic model and authority](semantic-model-and-authority.md) | Model facts restated by hand (DA-070 to 073, DA-086); no typed registry of programs (DA-081); per-consumer LinkML composition (DA-085); earlier identities with current sites (DA-028, DA-001, DA-004, DA-065) |
| [Execution fit](execution-fit.md) | Coarse and hand-kept identities, the query cache, re-proved assurance, the unheld native capture (DA-068, 069, 075, 078, 033, 058, 082, 083) |
| [Native integrity](native-integrity.md) | Guard, role and grant lists (DA-074); native strengths |
| [Served claims](served-claims.md) | Implementation and policy identity of served results (DA-076, 077) |
| [Boundaries and composition](boundaries-and-composition.md) | Host concurrency (DA-079); superseded machinery (DA-080); the residue of the SQL conversion (DA-084); unread settings (DA-020) |
| [Structure and invariants](structure-and-invariants.md) | Unbounded decimal expansion (DA-040); earlier identities |
| [Witnessed enrichment](witnessed-enrichment.md) | Earlier identities, all corrected |
| [Local reasoning and assurance](local-reasoning-and-assurance.md) | Navigation and the boundary with the test account |

## Ownership and reuse

Each cause has one primary home across this account and the test account. IDs are never
reused. Removing a diagnosis here does not close a plan obligation. The findings DA-068 to
DA-086, and the earlier identities whose cause was found at current sites, are unscheduled as
findings: no plan owns them until the operator asks for a review or a plan revision, and their
revisit trigger is the next design-review engagement on the declared-data-operations target.
For DA-084 the conversion itself is the plan's work and is nearly done by the plan's own
account; what the audit holds is the recount and the one remaining item. Findings of the
production-efficiency review keep their `PE-Fnn` identities and their disposition in the
[DDO plan](../../plans/declared-data-operations_2026-11-12.md); this account reports their
state in source and does not re-own them. Consuming reviews cite this account's publication
revision and stable anchors, and reconcile intervening source changes.

## Earlier engagement anchors

These preserve existing links. The entries they named described source that has since been
replaced; their text and dates are in Git at `fbd3f2a98` and earlier.

<a id="declared-data-operations-entry-refresh"></a>
<a id="book-ready-execution-refresh"></a>
<a id="book-execution-entry-refresh"></a>
<a id="text-characterization-entry-refresh"></a>
<a id="cld-assembled-refresh"></a>
<a id="cld-entry-refresh"></a>
<a id="domain-data-model-assembled-refresh"></a>
<a id="domain-data-model-interpretation-correction-refresh"></a>
<a id="domain-data-model-construction-terminology-refresh"></a>
<a id="domain-data-model-entry-refresh"></a>
<a id="ptd-assembled-refresh"></a>
<a id="pm2-parser-refresh"></a>
<a id="pm2-foundation-refresh"></a>
<a id="ghv-follow-on-publication-refresh"></a>
<a id="documentation-publication-refresh--2026-11-08"></a>
<a id="text-characterization-producer-reconciliation"></a>
<a id="m1-admission-refresh"></a>
<a id="m1-public-reference-refresh"></a>
<a id="m1-source-evidence-refresh"></a>
<a id="m1-initial-target-refresh"></a>
<a id="unified-model-refresh"></a>
<a id="sql-authoring-refresh"></a>
