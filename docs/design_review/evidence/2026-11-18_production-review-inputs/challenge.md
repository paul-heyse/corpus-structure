# Independent challenge of the 2026-11-18 audit refresh drafts

Challenger: design-reviewer (focused advice, not a formal review). Read-only. Source facts from
the frozen snapshot `snap5/` of `d78c98765`; history by read-only `git` with explicit commits.
Paths below omit `python/corpus-structure/src/corpus_structure/` unless they start with `docs/`.
I did not read any `LANE_*`, `LIB_*` or `MAP_*` report, before or after forming these views.
Line counts of hand SQL used a throwaway Python `ast` walk: lines spanned by string constants or
f-strings containing at least two of SELECT/INSERT/UPDATE/DELETE/CREATE/BEGIN/RETURN/PERFORM/
RAISE/DECLARE/LANGUAGE (script deleted after use).

Verdicts: **holds**, **holds with correction**, **overstated**, **withdraw**. Ordered by
consequence for the design review that will start from these pages.

## 1. DA-084 and the "conversion completed" premise — overstated (reframe)

What source shows is accurate: eleven `*_native.py` modules hold hand PL/pgSQL in Python strings
and import nothing from the program compiler (`grep -L native_program semantic/*_native.py`
also lists four non-SQL modules), ten `.sql` files are loaded, and none of the eleven has a
commit in `fbd3f2a98..d78c98765` (checked per file). The deployment routes cited
(`data_operation_storage.py:249–352`, `pdf_staging_native.py:168–170`) hold.

The framing does not hold. The residue is recorded as **open remaining work**, not as finished
conversion:

- ADR-0131 itself: "Convert remaining maintained owners forward and remove their superseded SQL
  sources" (`docs/adr/0131-model-owned-postgresql-programs.md:40–41`) and "This decision records
  the target while conversion is open" (`:51`). The draft cites `:41–42` and `:46` but not these.
- The DDO coordinator at `d78c98765` (not in the snapshot; `git show d78c98765:docs/plans/declared-data-operations_2026-11-12.md`):
  status line `:3` "Remaining consumers, **residual SQL authoring**, whole-book execution and
  DDO-12 assembled qualification stay open"; `:100–103` "The remaining authoring conversion
  covers … PDF publication, DDO kernels, physical checks and indexes, **native admission and
  privileges, scientific routines** and administrative paths"; `:191–195` "The authoring
  conversion remains open. The outstanding owners include … **general native admission**,
  scientific scoring and native fixture provisioning".
- STATUS.md and the companion (`postgresql-realization-and-retirement.md:401–403`) are
  consistent with that; the companion sentence the draft quotes is the categorical hand-off,
  and the coordinator owns the remaining-work list.

So "'conversion complete' overstates what was converted" attacks a claim no project owner
makes; it came from the brief (`COMMON.md`: "That conversion is complete and under
validation"), which is itself wrong, and from README `:43–44` ("in that range the model-owned
SQL conversion … completed"). The plan's sentence is classified as remaining work by its owner.

Narrowed finding worth keeping (or moving to the map as state of scheduled work): the plan
names categories only; the audit's contribution is (a) the inventory (which modules, which
files, which splice sites), (b) that this residue is exactly where the DA-070 family lists and
DA-074 role literals live, so converting it before family membership and roles are declared
would transcribe them again (the draft's DA-070 "ordering observation" — this is the most
useful design-review input on the page), and (c) that ADR-0131's consequence (`:46`) does not
yet hold there. Severity should read as "scheduled, not inventoried", not as a defect outside
the ADR. Per the project rule that the owning plan's findings table holds disposition of
scheduled work, the coordinator should decide whether DA-084 remains a DA identity at all.

Counts in DA-084:
- "about 1,940 lines in thirteen modules": order of magnitude holds; method-dependent. My AST
  count (string constants or f-strings with ≥2 SQL keywords): **1,826 lines in the eleven
  non-compiler `*_native.py` modules**; top six exactly match the draft (474, 444, 229, 136, 132,
  130); `archive_native.py` 99 (draft 124; 105 counting all multi-line strings). Adding
  `pdf_publication_native.py` (46), `data_operation_cpu_basis.py` (166) and
  `execution_evidence_leaf.py` (49) gives about 2,090. Say "about 1,800–2,100 lines, depending on
  what is counted; 1,826 in the eleven `*_native.py` modules that do not use the program compiler".
- "57 of the 69 `*_native.py` modules that hold statements import the program compiler": 57 of
  72 import it; 15 do not (eleven hand-SQL, four others). Fine if "hold statements" is defined.
- Ten loaded files "about 88 KB": holds (87,447 bytes, 1,008 lines).
- "Thirteen text replacements in eight modules": **eleven splice sites in seven modules, nineteen
  `.replace` calls counting chains** (`native_admission.py:419, 428, 439, 444`;
  `data_operation_protocol.py:129, 156`; `alembic_privileges.py:589`;
  `data_operation_source_native.py:72`; `contextual_linguistics_native.py:49–51` (2);
  `pdf_publication_native.py:562–564` (2); `structural_admission_native.py:482–494` (7)).

## 2. DA-085 — overstated (a documented choice is presented as a defect)

The inventory holds (43 LinkML schemas by header out of 50 YAML files; the protocol is 3,007
lines with `operations:` at `:2783`; `ph:foreign_keys` 117, `ph:checks` 68, `ph:indexes` 32;
three near-identical closure routines at `prepare.py:350–373`, `native_call_sources.py:95–117`,
`projection_analysis_products.py:85–107`; 16 `SchemaView(` sites).

But the plurality of authoring formalisms for operations is the accepted decision
**ADR-0092** (`docs/adr/0092-ddo-operation-authority.md:19–25`): option 2, "Make Python the sole
authoring source", and option 1 were rejected; the selected option "compile both admitted
authoring routes [declaration-owned model protocols and implementation-owned typed Python
definitions] into one effective model". The page does not cite it. "Operations and the
protocol are outside LinkML altogether, so no LinkML generator or validator can reach them" and
"no single compiled authority" therefore contradict a documented design without engaging it.

Narrow to what is not decided: (a) the *LinkML part* is composed separately by each consumer
through copied closure routines (with a hand file-name map at `native_call_sources.py:57–64`),
(b) physical constraints are JSON strings in annotations, and (c) the effective operation model
and the LinkML views are not one object that generators read together. Add ADR-0092 under
contrary evidence and state that challenging the two-route authoring is an ADR revisit, not an
audit defect. Also note that separate per-artifact closures partly serve custody (each captured
closure is what that artifact's identity covers), so "every new consumer adds another closure"
is partly by design.

Count: "operations … in 85 Python modules" — **85 modules mention `__data_operation__`; about 62
declare one** (89 `__data_operation__: ClassVar[...]` class attributes and one module-level
dict; `grep -rlE '__data_operation__\s*[=:]'`). Same correction on `domain-model-map.md:62` and
its fact-ownership "Operation" row.

## 3. DA-080 / DA-081 "stale dispatch key `scientific_layout.sql`" — withdraw

`target_installation.py:230, 235–236` uses `"scientific_layout.sql"` as a label that selects the
captured artifact `authoring/scientific-layout.sql`, generated by
`archive_projection_native.py:74` and captured at `native_products.py:179`. `"closure-native.sql"`
(`:214–218`) is the same kind of label for a generated artifact (`target_installation.py:86`)
and no file of that name exists either. Nothing is stale; at most the label style is
misleading (it reads as a file name and appears in `source="target-current:" + filename`).
Remove the bullet from DA-080 and the clause from DA-081.

## 4. DA-081 — holds with correction (contrary evidence wrong; footprint stronger)

The contrary evidence says the required-set check "refuses a missing or unexpected artifact".
`_captured` refuses duplicates and missing names only (`data_operation_storage.py:570–572, 683`:
`if not required <= result.keys()`); an extra artifact is accepted. Moreover the required set is
itself a sixth hand list of the program set, and it **already disagrees** with `native_sql`: six
artifacts that `native_sql` concatenates are not required (`data-attempt-release.sql`,
`data-claim-batch.sql`, `data-claim.sql`, `data-completion-settlement.sql`,
`data-operation-renewal.sql`, `data-read-boundary.sql`; compare `:573–682` with `:758–796`). A
missing one would surface as a `KeyError` in `native_sql`, not as the classified refusal. This
is a concrete instance of the "caught only where a later step happens to need it" consequence.
Facade part holds (`model_change.py:53–61, 538–552`).

## 5. DA-070 — holds with correction

Classification tuple (seven families, 27 ids, no `ELSE`; `data_operation_compiler_native.py:468–520`),
dispatch with `else_=True` (`data_validity_native.py:272–288`), and the optional unconstrained
column (`data-operation-physical.yaml:88`) all hold; no declared family source exists (search for
`validity_family` finds only the column, the generators and two readers). The status sentence
"There are therefore two lists of family names where there was one" is wrong: at `1afa63f88` the
deleted SQL already had both, the dispatch `CASE def.validity_family … ELSE true`
(`git show 1afa63f88:…/semantic/sql/data_operations.sql`, about `:345–353`) and
`ddo_classify_validity … ELSE NULL` (about `:2311–2328`). Replace with: "Both lists existed in
the deleted SQL; the conversion transcribed both into Python tuples."
Caution for the "per-operation family contract" lead and map row: the contextual `CASE`
(`contextual_admission_native.py:23–44`) is compared with the admitted definition, so it acts as
an independent pin. Deriving it from the effective model keeps a meaningful check only if the
kernel's captured model and the admitted release are distinct inputs; say so rather than
"derivable".

## 6. DA-086 — holds with correction (one item misclassified)

Task states (`data-operation-native.yaml:5–14`; `"running"` at `data_claim_native.py:77`; guard
rendered from the lifecycle at `data_operation_protocol.py:114–160`), codec tags
(`data_operation_value_native.py:44–50` vs `source_value_native.py:55–66`), `_PROFILES` (`:85`)
and `_KIND_UNIVERSES` (`:341`) beside `data_operation_model.py:497` and the check at
`data-operation-physical.yaml:71` all hold.
Field kind to type: the model **does** declare this. Types carry `uri` and `ph:sql_type`
(e.g. `json_payload` at `model/semantic/physical.yaml:33–36`), resolved by the physical compiler
(`schema/relational.py:79–89` `URI_TYPES`, `:437–440`). So the four maps restate a declared fact
and its existing resolver; this item fits DA-086's definition better than the draft says, but
the map row is wrong ("Declared in the model: —"; "Derivable from: any one of the four"). Correct
to "Declared: LinkML type `uri` and `ph:sql_type`; derivable from the physical compiler's type
resolution".
The "about 37 state literals across twelve generators" is method-dependent: quoted
`pending|running|done|empty|failed|cancelled` gives 62 in 16 generator modules (including
outcome uses of `empty`/`failed`); `pending|running` alone 22. Prefer the narrower number.
Separation from DA-070/073/074 (declared-but-unread versus undeclared) is sound.

## 7. DA-087 — overstated as a separate cause

Sites hold (`data_operation_storage.py:715–748, 753–812, 1873–1914`;
`native_authoring.py:293–313`). But grants-by-name after re-parse, the inventory re-parse, and the
entry-point rename are the same missing thing as DA-081's program-set lists: no typed registry of
program objects (name, schema, purposes/grants, provider order) carried from generation to
installation. With such a registry both go; without it neither does. Recommend folding those
bullets into DA-081 (or homing both under one cause) and keeping DA-087 only if the per-statement
re-parse cost is wanted as its own execution observation. The digest-marker ordering is a
necessary self-reference (a digest cannot cover its own value), so "held only by the order of
statements in one function" is low weight. Count: `native_sql` joins **37 named artifacts in its
tuple plus two appended (external, search projection)**, not "about 33".

## 8. DA-082 — holds with correction

70 entries (64/5/1) and 14 libraries hold (`pdf_lowering.py:15–30, 33–104`); omissions hold:
`pdf_staging_native.py:168–170` appends `pdf_spool_native_sql()`; `pdf_domain.py` is imported by
listed `pdf_publication_native.py:415` and `pdf_domain_native.py:24` and does not capture its own
bytes. Refusal paths hold (`:276–310`). Corrections: the list had **58** entries at `1afa63f88`
(not about 56); ten commits touched the file in `1afa63f88..d78c98765` (twelve from `fbd3f2a98`).
Narrow the "too narrow" consequence for `pdf_spool_native.py`: it produces deployed SQL, so its
effect on produced work arrives through native deployment, whose own identity the draft did not
examine; say "the lowering identity does not change" rather than "certification accepts work
produced by different code". Relation: the closer sibling for the too-broad half is DA-069
(whole files and library versions as implementation identity), not DA-068; add DA-069 to the
"not a manifestation of" sentence or name the shared cause (hand-kept code closure) with DA-069
and DA-076 on the joint page.

## 9. DA-083 — holds

Two rebuilds per `require_data_operation_native` (`data_operation_storage.py:1128, 1131`), three
per definition admission (`:1548, 1558`), callers at `data_operation_admission.py:285, 354, 390`,
no memo on `native_protocol_sources` or `compile_physical`; port creation once per operation per
context and recheck when not yet admitted (`orchestrate/data_operations.py:698–785`). Only the
wire module caches (`data_operation_wire.py:46…485`). Separate from DA-068 (cost and custody,
not breadth). The "third rebuild in a preview" stays marked as untraced.

## 10. Status claims of re-read findings

- **DA-068 wider — holds.** 57 `read_bytes` in the storage module (45 at `1afa63f88`); six library
  versions (`:206–214`, `:537–546`, `pdf_source_search.py:63`); seven use sites spot-checked
  (`demand_result_native.py:209`, `data_derivation_native.py:614`, `data_operation_storage.py:982`,
  `data_operation_projections.py:1932`, settlement `:685` stable).
- **DA-070 stands — holds** with the §5 correction.
- **DA-072 — holds.** 39 modules import `core.vocab|core._model|core.keys` by dotted search (draft
  40); `native_call_generation.py:106` holds.
- **DA-074 wider — holds.** `ph:read_roles` is `'[]'` on all 84 relations that carry it; positive
  table grants come from `DEFAULT_READ_ROLES` for unannotated relations (`alembic_privileges.py:25–35, 74–75`);
  `pending-content` on exactly two relations (`physical.yaml:1757, 1776`), carried into `info`
  (`schema/relational.py:492`) and not used to choose shared-stream triggers
  (`target_installation.py:350`); the immutability trigger test at `:335` excludes it implicitly.
  Role-name count: **176 occurrences of `corpus_(sem|data|ops)_*` in 39 modules**, including
  constants, comments and SQL strings — say "occurrences", not "literals".
- **DA-075 — holds** (keys at `rich_queries.py:225`, `contribution_facets.py:263`,
  `interpretations.py:207`, `structural_products.py:282`, `demand_queries.py:202`; exclusions at
  `identity_exclusion_comparison.py:155`).
- **DA-080 partly corrected — holds** except §3: six unloaded files (285 lines), ten loaded;
  `semantic_alembic/` 286 files, 1.8 GB, no path reference (only the version-table name);
  `target_alembic` root has `down_revision = None`; `disagreements`/`fuse` called only from
  `tests/semantic/test_rich_relations.py`; `AnalyticsSettings` readers as stated.
- **DA-081 wider — holds** with §3/§4 corrections.
- DA-071, DA-073, DA-076–079, DA-033, DA-058: not re-verified beyond line spot-checks; I found
  nothing contradicting them.

## 11. The three facts the drafter could not re-locate — all found

- **Renew program:** `semantic/data_operation_renewal.py:37` (`renewal_native_sql`), captured as
  `native/data-operation-renewal.sql` (`data_operation_storage.py:485–489`) and concatenated at
  `:777`. Typed program (exclusive request/task locks at `:165, 172`).
- **"A directly revoked producer cannot be rehabilitated":** settlement refuses when the producing
  runtime or recipe has a revocation in scope (`data_derivation_native.py:200–216`, refusal at
  `:354` "producing runtime or recipe was directly revoked"); revocation rows are
  `ph:immutability: intrinsic` (`data-operation-physical.yaml:513–531`), so the immutability
  trigger (`target_installation.py:335`) forbids removing one.
- **"Only revocation takes exclusive locks" (on trust scope):** `revoke_data_support` takes
  `FOR UPDATE` on `ops.data_trust_scope` and bumps the epoch (`demand_result_native.py:298–440`,
  lock `:403`, update `:407–413`); every other lock on that relation is `FOR SHARE`
  (`demand_result_native.py:230`; `data_read_boundary_native.py:126`;
  `demand_registration_native.py:824`; `request_attachment_native.py:1866`;
  `support_trust_native.py:180`). Holds, by search.

## 12. Table spot-checks

**Fact ownership (`domain-model-map.md:177–204`), twelve rows.** Validity family, shared-stream
membership, frontier guard, task states, trust-scope key (`support_trust_native.py:100–118` vs
`change_impact.py:427`), search configuration (`physical.yaml:1733`), identity determinants
(`data_operation_compilation.py:2138`), graph-projection catalog (`data_operation_model.py:705–725`),
value-codec, table read grants: hold. **Field kind to type: wrong** (§6). **Operation: count**
(§2). **Per-operation family contract: caution** (§5). Validity-family "guard tuple (`:537–553`)"
holds (fourteen names at `:538–553`).

**Identity inventory (`model-and-execution.md:220–243`), rows 2, 6, 7, 12, 14, 17, 19/20, 21.**
All hold. Row 2's "On mismatch: Not traced" can be filled: the demand programs compare the
release's `lowering_digest` with the compiled-in value (`demand_authority_native.py:137–138`;
`demand_registration_native.py:602`). Row 6: eight generator modules hold
(`data_operation_artifacts.py:22–31, 73–81`). Row 21: holds (`schema/source_migrations.py:168–198`).

**Cache inventory (`model-and-execution.md:131–155`), rows 1–8, 10, 12.** Hold: `SELECTED_QUERY_CACHE`
(`LRUCache` with `getsizeof`, hand `popitem`, `RLock`), `_installed_read_basis` 64,
`_current_boundary` 1, `_prepared_lowering_sources` 4, `_prepare_release_cached` 8,
`_bound_data_operation_calls` 8, the four `execution_admission` caches, wire caches 1/16/16/16/1/256,
file custody `RLock` and 2 s racy window. Counts: 94 `functools` cache decorators and 76
`cached_property` lines by my search, consistent with "about 94" and "about 75".

## 13. Anything sound reported as a problem; anything missing

- Sound reported as a problem: the `scientific_layout.sql` key (§3); the digest-marker ordering
  (§7); the two-route operation authoring (§2, ADR-0092); the residue as "outside" ADR-0131
  rather than scheduled (§1).
- Missing: the required-set/concatenation disagreement (§4) is a concrete, current instance the
  pages lack. No further structural problem of finding weight surfaced in what I read.
- For the coordinator: the brief's premise that the conversion is complete is contradicted by the
  coordinator plan's own status line; other pages that inherited it should be checked.

## Corrections ready to apply

1. README.md `:41–44`: replace "and in that range the model-owned SQL conversion (ADR-0131)
   completed" with "and in that range most of the model-owned SQL conversion (ADR-0131) landed;
   the DDO coordinator records residual SQL authoring as open (status line; remaining-conversion
   paragraphs)".
2. README.md new-findings row DA-084 and boundaries-and-composition.md DA-084 title/summary:
   "Hand-written PostgreSQL that ADR-0131 schedules for conversion is still deployed, is not
   inventoried by the plan, and holds the family and role lists; model changes do not reach it".
3. boundaries-and-composition.md DA-084 Consequence: delete "and 'conversion complete' overstates
   what was converted" and "does not classify the residue as an exception or as remaining work";
   add the ADR-0131 `:40–41, :51` and coordinator `:3, :100–103, :191–195` citations.
4. boundaries-and-composition.md DA-084 counts: "about 1,940 lines in thirteen `*_native.py`
   modules" → "about 1,830 lines in the eleven `*_native.py` modules that do not use the program
   compiler (about 2,090 including `pdf_publication_native.py`, `data_operation_cpu_basis.py` and
   `execution_evidence_leaf.py`)"; "Thirteen text replacements in eight modules" → "Eleven splice
   sites in seven modules (nineteen replacements counting chains)"; "57 of the 69" → "57 of the 72".
5. semantic-model-and-authority.md DA-085: add ADR-0092 (`:19–25`) under Contrary evidence;
   change "Operations and the protocol are outside LinkML altogether, so no LinkML generator or
   validator can reach them" to "Operations and the protocol are outside LinkML by the two-route
   design of ADR-0092; the open question is whether the LinkML part and the effective operation
   model are one object generators read"; "85 Python modules" → "about 62 Python modules (85
   mention the name)". Same number in domain-model-map.md `:62` and the "Operation" row.
6. boundaries-and-composition.md DA-080: delete the "A stale dispatch key" bullet.
   semantic-model-and-authority.md DA-081: delete ", which still dispatches on the name
   `scientific_layout.sql` (`:230, 236`) although no file of that name exists".
7. semantic-model-and-authority.md DA-081 Contrary evidence: "refuses a missing or unexpected
   artifact" → "refuses a missing or duplicated artifact; an extra one is accepted. The required
   set is itself a hand list and omits six artifacts that `native_sql` concatenates
   (`data_operation_storage.py:573–682` against `:758–796`)"; add it to the list of places.
8. semantic-model-and-authority.md DA-070 refresh: "There are therefore two lists of family names
   where there was one" → "Both lists already existed in the deleted SQL; the conversion
   transcribed both". Same in README status row DA-070 ("and a second Python tuple now does the
   dispatch" → "and the dispatch `CASE` became a second Python tuple").
9. semantic-model-and-authority.md DA-086 field-kind bullet and domain-model-map.md field-kind
   row: model declares type `uri` and `ph:sql_type` (`physical.yaml:33–36`), resolved at
   `schema/relational.py:79–89, 437–440`; "Derivable from" → that resolution.
10. boundaries-and-composition.md DA-087: "about 33 named artifacts" → "37 named artifacts, then
    two appended"; move the grant-by-name, inventory and rename bullets under DA-081's cause or
    state the shared cause explicitly.
11. execution-fit.md DA-082: "about 56 entries" → "58 entries"; narrow the spool consequence as in
    §8; mention DA-069 as the sibling.
12. native-integrity.md DA-074 and domain-model-map.md role row: "about 175 role literals" →
    "176 occurrences of role names (literals, constants, comments and SQL strings)".
13. structure-and-invariants.md `:13`, domain-model-map.md `:335–336`, native-integrity.md
    `:103–106`: replace "not located/not re-read" with the §11 locations.
14. model-and-execution.md identity row 2 "Not traced" → the lowering-digest comparisons in §12.
15. semantic-model-and-authority.md DA-072: "Forty modules" → "39 modules by dotted-path search".

## What I did not examine

The lane, library and map reports; `analytical` and `pe-state` sections and the "planned change"
table; DA-071, DA-073, DA-076–079, DA-033 and DA-058 beyond line spot-checks; generator bodies for
equivalence; `native_objects.py`, `native_inventory.py`, `native_authoring.py:171–199`;
`model_change.py` preview rebuild counts; `schema/model_deployment.py`; migration revision bodies;
`domains/` (not in the snapshot); whether `pdf_spool_native.py` edits are caught by a deployment
identity; whether the native deployment refuses on the six required-set omissions before
`native_sql` runs. Principle identifiers on new findings were not re-derived.
