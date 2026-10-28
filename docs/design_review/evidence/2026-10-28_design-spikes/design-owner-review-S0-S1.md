# S0 and S1 — design owner's review

**Date:** 2026-10-28. **By:** the design owner (Claude, project conversation). **For:** the in-repo
agent, to turn into plans. This review does not edit the design: every item names the document and
section to change and why.

**Read for this review:** the [S1 report](S1-report.md), [S0 report](S0-report.md),
[S0-R2 report](S0-R2-report.md), [summary for the design owner](summary-for-design-owner.md), the
gap analysis (`results/s0/gaps.md`), the v1 reference batches, the spike profile and schema copies
under `code/`, ADR-0009–0011, and the X1 fold-in as it stands in D0–D9, the trace and the
design-phase plan (commits after `3af52c1`).

## Verdict

The spikes answered what they were asked, and the fold-in is mostly faithful. S1 confirms the
evidence model on all 78 pages. S0 and S0-R2 show that the claim model holds and that the
determinacy problem was in the inputs: the remedy (guideline v1, a generated annotator reference,
query-assembled context, rule warnings) is the right one and is well evidenced. ADR-0009, ADR-0010
and ADR-0011 fit the design's direction.

Three things need attention before phase 0 is planned:

1. **Phase 0 now depends on methods the design schedules for phase 1.** The math grammar, M09 and
   M13 are needed for golden and agent packets and for canonical form (A1).
2. **Keys again depend on parser coverage** through the new canonical-form rule (B1).
3. **Three inconsistencies came out of the fold-in:** parameter naming (B2), statement identity
   (B3), and the trace's acceptance answers (B4–B6).

Priorities used below:

- **P0-blocking:** must be settled before the phase 0 plan is written.
- **Phase 0:** belongs in the phase 0 build.
- **Revision:** goes into the next guideline or schema revision.
- **Later:** has a named trigger.

## A. Follow-ups the evidence calls for

### A1 · Bring the math grammar, M09 and M13 into phase 0 · P0-blocking

**Why.**
- D4 §4.1 and D7 §3.2 (ADR-0011) assemble standing context from M13 binding sites. M13 reads M09's
  symbol occurrences from the math grammar.
- D1 §6.2 writes canonical form, and so claim keys, through the same grammar.
- D4 §3 still lists M09, M11 and M13 as phase 1, D9 §5 has none of them, and D5 §11 runs no M13 in
  phase 0.
- Without them, phase 0 golden packets and M24 packets have no standing context. S0 showed this
  costs qualifier agreement: SP 0.37 against SV 0.77 at full tier.

**Change.**
- In D4 §3, move M09 and M13 to phase 0, and M11 too for its grammar part (validation, canonical
  form, symbols). SymPy conversion can stay phase 1.
- Add a D9 §5 step after P0.5, "math grammar and scoping", ported from `code/mathgrammar/` and
  `code/m13_binders.py`. Acceptance:
  - the S0 M13 probe reproduces 20 of 20 scopes;
  - S1's math span results are reproduced: 28,948 `ok` and 8 `partial`.
- Add a `scope` stage to D6 §2 for phase 0.
- D5 §11 can keep taking scopes from proposals for consolidation; only packet context needs M13.

### A2 · Phase 0 steps for the ADR-0011 tooling · P0-blocking

ADR-0011 marks the generator and the golden tools as phase 0 work, but D9 §5 has no step for them.

| Step | Add |
|---|---|
| P0.4 | **Annotator-reference compiler** (D2 §7.5, §10.10): port `code/s0r2_inputs.py` to compile from the LinkML schema. Acceptance: its output for schema v0 carries the same information as `results/s0r2/inputs/packet_v1/reference.md`; the worked examples are included. |
| P0.4 | **Guideline warning rules** (D2 §7.4): port `code/s0r2_rules.py` into a `guideline:` group of `rules.yaml`. Acceptance: the v1 reference and examples give 0 warnings, and seeded violations are each caught. |
| P0.7 | `read_golden_unit` serves the guideline, the reference and the query-assembled packet. `write_golden` records the model and the input digest (B7). |
| P0.10 | The golden sampler respects reserved pages (A4). |

### A3 · Port list: the spike instruments · Phase 0

D9 §7 lists only corpus-intelligence sources. The spikes produced tested code that phase 0 should
port against the D-document contracts, keeping their tests (`code/tests_instruments`):

| Spike code | Becomes |
|---|---|
| `code/s1_adapter.py`, `code/profile/siegrist.yaml` | M01, M03, `domains/statistics/methods.yaml` |
| `code/mathgrammar/` | the one math grammar (M09, M11, canonical form) |
| `code/m13_binders.py`, `code/s0r2_sample.py` | M13; packet standing context |
| `code/s0_locate.py` | the quote cascade (`methods.llm.parse`, D4 §4.3) |
| `code/instruments/` (align, conditions, keys, values, validate, scores) | `evaluate/` alignment and scoring; `core` keys and canonical JSON; the batch validator |
| `code/s0r2_inputs.py`, `code/s0r2_rules.py` | A2 |

### A4 · Reserve pages for examples and held-out checks · P0-blocking

The annotator reference's worked examples come from the Weibull page. S0-R2's held-out units come
from Pareto and ChiSquare. D7 §3.1 assigns every first-pass page to dev or test, so Weibull could
land in test, and its examples would then sit in every prompt.

- **D7 §3.1 and §4:** pages used for worked examples are `reserved`: they are in no split, are
  never golden units, and are never test. Pages used to write or check guideline rules (the four
  spike pages, Pareto, ChiSquare) are forced to dev.
- **D3:** add `reserved` to the `eval.document_split.split` CHECK.

### A5 · Merge S1's source profile into D2 §12.1 · Phase 0

`code/profile/siegrist.yaml` keeps D2 §12.1 verbatim plus `s1_additions`, which were not merged
back:

- `ul.map` exclusion;
- the `align`/`align*` display environments;
- `p.stat` → theorem;
- `p.Proof` → proof.

ADR-0009 also requires that the rendering conventions of D1 §3.1 become profile data rather than
adapter code: the `a.ref` → `[n]` marker, `<q>` quotes, `ol.sub` "(a) " markers, the `details`
summary as a heading, and orphan-text handling.

The work:
- **Vocabulary, in D4 M01.** Declare the profile's role vocabulary, including the NIST-probe roles
  `layout`, `verbatim`, list markers and `img_alt` rendering with their defaults.
- **Values, in D2 §12.1.** Write Siegrist's values for those roles.
- **Code.** Make `sectionize` read the profile's `sections` key (S1 follow-up).

HTML-07 stays open until this is done (B13).

### A6 · Schema v0.2 from the S0 schema gaps · Revision

These are ranked as in `results/s0/gaps.md` §5; each needs a D2 §9 change and a row of its own
(B12).

| Gap | Change |
|---|---|
| SG-3 (rank 7) | `ParamValue.value` accepts a number with a unit, not only a formula (U7, U8). D1 §6's own example is rejected today. |
| SG-1 (rank 9) | An `asks_for` predicate for what an exercise asks. Guideline v1 records it as `unsupported` for now, so `posed` is unused (B11). |
| SG-4 | A standard-deviation property predicate; decide on skewness and kurtosis together. |
| SG-2 | Independence stated as a setup fact (U8) against guideline v1's "independence is a condition only". Decide, with RG-2. |
| SG-9 | A standard member without a stated constraint ("standard lognormal"): is it a relation, or nothing? |
| SG-5, SG-8 | "Y is the standard score of X" and notation ("Ω is the set of outcomes"): concept-of and notation predicates, or out of scope. U6 needs the first. |
| SG-10 | A `RandomVariable` without a symbol. |
| SG-11 (OPEN-D2-10) | Document the shapes of `param_mapping`, `param_symbols` and `param_constraints` so the reference generator can state them. |

### A7 · Representation gaps in D1 · Revision; RG-1 P0-blocking for the guideline

| Gap | Change |
|---|---|
| **RG-1 external references (rank 1)** | D1 has no way to point outside a batch. Context premises (D2 §7.3 `cN`) cover only suppositions in the standing context. "The last result", "definition [1]" and the `[14]` links in U6, U7, U9 and U12 still cannot be represented. Add an external-reference value `{t: "extref", target}`, whose target is a D6 §8 locator or an author link target, usable as a `refers_to`/`follows_from` object, as a `claim` node target, and as a binding target. Consolidation resolves it to a key and reports unresolved ones. INV-09 is extended: a claim whose premise is an unresolved external reference counts as conditional. New item OPEN-D1-5. |
| RG-2 indexed families (rank 3; OPEN-D2-7) | An indexed local entity (`index`, `index_set`); `forall` with a `claim` body; an indexed-set argument for condition predicates; an `instance_of_param` binding. Then one guideline form. |
| RG-3 | A `bound` binding kind for symbols bound inside the formula (Σ, ∏, ∫, set-builder), excluded from completeness. Cheap: D1 §6.1 and `BindKind` in core.yaml. |
| RG-4 | A `defined_by` binding for "where μ = …" clauses. |
| RG-5 | `param_of` targeting a premise claim other than `has_distribution`. |
| RG-6 | An extent covering a run of sibling statements. |
| RG-7 (with GG-5) | A family's parameterizations, so canonical parameter names are stable across units. |

### A8 · Guideline v2 points · Revision

These are the open points of OPEN-D2-8 and OPEN-D2-9:

- the premises a claim actually uses (OPEN-D2-8);
- the scope of section-level suppositions that nothing references;
- restricting phrases (GG-16);
- recalled definitions (GG-12);
- what counts as an explicit claim in framing text (GG-8);
- the same fact stated in two predicate forms (GG-10).

Each revision is checked by the procedure in A11.

### A9 · Make consolidation reproduce the guideline's conventions · Phase 0 (scopes) / phase 1 (bindings)

D5 was written before guideline v1, and the pipeline must produce what the goldens encode.

| Section | Change |
|---|---|
| D5 §4 | Rewrite the binding algorithm as guideline §10.7's rows, in order, using each symbol's first appearance. Today's algorithm makes T1's `a` and `b` `free`; v1 and the trace make them `family_param`. |
| D5 §3.5 | Statement segmentation as in guideline §10.3: one statement per kind in a mixed unit, plus context-premise `assumption` statements. Statement identity follows B3. |
| D5 §9 | Derived claims inherit conditions under §10.7's rules 1–4. A derived family-structure claim carries no `claim` nodes. |

### A10 · Score context premises once · Phase 0

- **The problem.** Context-premise claims cite `cN` sentences outside the unit (D2 §7.3), and every
  golden unit depending on the same supposition records it again. D7 §5.1's predicted set counts
  only claims anchored in the unit, so these golden items are false negatives. If the predicted
  set is widened instead, they count twice.
- **The rule, in D7 §5.1.** A context-premise golden item is scored as an item only in the golden
  unit whose own text states it. Elsewhere it is scored only through the `claim` nodes that
  reference it, at full tier.
- **The flag.** Golden items get a `context` flag (D3 `eval.golden_item`).

### A11 · Make the S0-R2 procedure the guideline-revision check · Phase 0

Move this from D7 §5's "Reading agreement" paragraph into D7 §2 as the rule for every guideline
revision of the rule class. It needs:

- a Sonnet pass and a Haiku pass from packets;
- units used to write the change, plus held-out dev units from other pages;
- pass against pass reported beside pass against reference;
- reference corrections reported with the figures before them.

Give the result an evidence record (ADR-0010).

### A12 · Rerun the 78-page corpus run with html5lib · Phase 0, before M01 is frozen

D4 M01 states html5lib, but the 78-page S1 run used libxml2, and the parsers differ on 4 pages.

- Rerun S1-D with html5lib as the default parser.
- Confirm that counts, invariants and locators hold.
- Regenerate `sample.json` if any offset moves.

### A13 · Output budgets · S3

- **D4 §4.1 and D8 §3.** State an output cap beside each input cap. Batches reached about 2,500
  Qwen tokens on the core units, two to nineteen times the unit.
- **S3.** Confirm the p99 on more units, and set `max_tokens` for M10 and M24 from it.

### A14 · Non-LaTeX math notation · Later

Trigger: a second source with image or HTML math.

S1-F proposes `attrs.notation` ∈ {latex, html, image, plain} and the use of `alt` text for image
math. Record it as a deferred item with this trigger, not in D1 now.

## B. Corrections to the current documents

### B1 · Keys depend on grammar coverage again · P0-blocking

**Where:** D1 §6.2; ADR-0009 Decision; `code/mathgrammar/api.py` `canonical()`.

**What is wrong.**
- Canonical form is written from the parse tree when a value parses, and by token normalization
  otherwise.
- Only 976 of 1,532 spans parse on the 78-page sample, and coverage will grow as S5 extends the
  grammar.
- Each value that starts to parse switches canonicalizer, so its claim keys change. Judgments
  keyed to them are orphaned (D5 §7.3).
- This contradicts D1 §6.2's own sentence that a parser change never changes keys.

**Fix.**
- Keys use the token canonicalization for every value: it is total, needs only the rendition's
  macro table and never depends on parse success.
- The tree serves validation, slot typing, SymPy conversion and the equivalence fusion of
  D5 §5.3.
- Add a property test: for every parsed value, the tree printer and the token form agree; where
  they cannot, the token form wins.
- Amend ADR-0009's Decision line accordingly.

### B2 · Parameter naming: guideline v1 against the v1 reference and the trace · P0-blocking

**What is wrong.**
- Guideline §10.4 says the canonical name is "the role word if the unit states one for that
  parameter **anywhere**".
- T4's unit states "The parameter σ is the shape parameter" in its list item 1, so by the rule σ
  is `shape`.
- Yet trace T4 and `results/s0r2/reference_model_v1/T4.json` name it `sigma` and add a
  `parameter_role` claim, which the same section says to add only when the role differs from the
  canonical name.

**Fix.** Recommended rule: the role word in the phrase that first names the symbol a parameter of
the family; otherwise the symbol. Roles stated later are `parameter_role` claims.
- This matches the reference and the trace.
- It keeps a parameter's identity fixed when a later sentence names its role, which is also what
  makes names stable across units (RG-7).

**Then:**
- reword §10.4 and the §7.4 warning rule;
- check SV and HV against the reworded rule (likely no change);
- reopen OPEN-D1-3 until both are done.

### B3 · Statement identity · P0-blocking

**Where:** D1 §10.1, D5 §3.5.

**What is wrong.**
- **Two statements in one block collide.** Guideline v1 yields several statements per unit when
  kinds mix, and context-premise `assumption` statements anchored at `cN` sentences. D1 keys a
  statement by "the smallest segment covering the anchor", so two statements in one paragraph get
  the same key.
- **An assumption can collide with a statement already there.** An assumption anchored inside a
  paragraph that is itself a statement (T2's paragraph supplies other units' context) gets that
  paragraph's key with a different kind.
- **"The unit" and its sentences can still key apart.** A unit holding a paragraph and a
  `details` block is covered by the unit segment, while its sentences are covered by the
  paragraph. "Unit" and "its sentences" then still key differently, despite the rule's intent.

**Fix.** Define a statement's anchor segment explicitly:
- the `unit` for statements inside a unit;
- the `details` for proofs and solutions;
- the paragraph outside units.

The key is (anchor segment key, the ordinal of the statement's first sentence within it).

A context-premise assumption whose sentences fall inside an existing statement's anchor is that
statement: it adds claims, not a statement.

Update D5 §3.5 to match, and the S0 key-variant figures if they change.

### B4 · D8 §5.3: stale expected answers

- **T2:** v1 drops C2 and C3, because `has_parameter` is stated only in a definition.
  `family_profile(normal)` must therefore answer from the `FamilyParameter` entities and C4–C5, or
  the trace slice must include the Normal page's defining unit. Choose one.
- **T4** now runs C1–C17 (with SN, SLN, and the domains C11–C12).
- **T1's** C5–C8 have role `definiens`.

### B5 · trace.md, "Expected observations"

- The M10 row (C1–C8, C1–C5, C1–C4, C1–C10) is stale.
- The M09 row says "S1 confirms": fill it in from `sample.json`.
- The M13 row for T4 lacks Z and W.

### B6 · D1 §12 and D3 §10: C2's conditions

- **D1 §12:** the worked example shows C2 (`defined_as a + b X`) without conditions.
- **D3 §10:** the `clm:C2` row has qualifiers `{"modality":"defined"}` only.

Under v1, C2 carries its restrictions `a ∈ ℝ` and `b ∈ ℝ ∖ {0}` (trace T3). Update both.

### B7 · D3: the golden pass does not record its model or inputs

ADR-0011, D7 §3.2 and D8 §2.2 say the model is recorded per pass, but `eval.golden_pass` has no
column for it.

- Add `model text NOT NULL`.
- Add `inputs jsonb NOT NULL`: guideline version, reference hash, packet hash and the M13 version
  that chose the context.
- Add `reserved` to `eval.document_split` (A4).
- Add a `context` flag to `eval.golden_item` (A10).

### B8 · D8 wording

- **§2.1:** `read_instructions` still lists "schema inventory"; it is now the generated annotator
  reference.
- **§2.2:** the `> Decision: [ADR-0011]` line absorbed the sentence "Test-split units are served
  only to golden passes…". Make it its own paragraph again.

### B9 · Evidence retention: ADR-0010 against the operator's direction

ADR-0010 and DESIGN §2 say records "retire with their folder (ADR-0001)". AGENTS.md (2026-10-28,
operator direction) says plans and evidence are never deleted. The summary lists this as waiting on
the operator, but the direction is already given.

- Write the ADR that supersedes ADR-0001's retention clause for plans and evidence.
- Update DESIGN §2's evidence paragraph.
- Correct ADR-0010's last bullet.

### B10 · D4 §3 and D6 §2 phases

These follow A1: change the phase column for M09, M11 and M13, and add the phase 0 stage list.

### B11 · `posed` modality

D1 §5.2 and core.yaml keep `posed`, but guideline v1 records asked quantities as `unsupported`.
Mark `posed` reserved until `asks_for` lands (A6, SG-1), or remove it. Either way, say which.

### B12 · OPEN-D2-9 bundles eight points

One row cannot carry eight dispositions. Split it into one row per point, and add rows for the
untracked gaps (section C).

### B13 · HTML-07 is marked closed in the findings table

D2 §12.1 still lacks S1's profile additions (A5). Reopen it until the merge is done.

### B14 · pylatexenc 3.0b2 is a pre-release

D9 §2 lists it for M01, for the page macro tables and the span balance check.

- Record it as a hold in `docs/pins.md`, with "3.0 final" as the trigger.
- Or confirm that M01 needs nothing that 2.x lacks, since the grammar now reads the math.

### B15 · Spike README

- The status line still says S1, S0, S4 and S6 "can run now".
- The Ready column should now say that S2, S3 and S5 are ready and that S7 waits on S2.
- It should name the v1 reference (`results/s0r2/reference_v1/`) as the reference later spikes
  score against.

### B16 · D7 §3.2: golden packets do use one pipeline output

D7 §3.2 says golden packets carry "no pipeline output", yet their context comes from M13.

- Say so in D7 §3.2.
- Record the M13 version on the pass (B7).
- Note in D7 §5.4 that M13's scope accuracy against goldens is not fully independent: goldens'
  extents are written from context M13 chose.

## C. Gaps not tracked anywhere

These come from `results/s0/gaps.md`. None of them has a findings row today; propose one each in
the design-phase plan's table.

| Gap | Proposed home | Priority |
|---|---|---|
| RG-1 external references (rank 1) | D1, as OPEN-D1-5 (A7) | P0-blocking for guideline completeness |
| GG-11 statement segmentation and kind (rank 10) | D5 §3.5 and B3; guideline §10.3 already rules on it | P0-blocking with B3 |
| RG-3 bound variables; RG-4 `where` definitions; RG-5; RG-6 | D1 §6.1 and §4.2 (A7) | Revision |
| SG-1, SG-2, SG-3, SG-4, SG-5, SG-8, SG-9, SG-10 | D2 §9 (A6) | Revision; SG-3 and SG-1 first |
| GG-8, GG-10, GG-12, GG-16 | Guideline v2 (A8) | Revision |
| RG-7 parameterizations | D2 §9 with B2 | Revision |
| Non-LaTeX math notation (S1-F) | Deferred, trigger in A14 | Later |

## D. Spike briefs S2–S7 after S0 and S1

| Brief | Update |
|---|---|
| S2 | Score against the v1 reference (`results/s0r2/reference_v1/`, stored form) as well as the v0 reference, and with and without contested items (decisions marked `guideline_gap`). Add math variant (d), Unicode-rendered (`code/s1_sentences.py`), to raw and masked. Use `extract_long` for the 153 units over 512 GLiNER2 tokens. Take offsets from `sample.json`. |
| S3 | Build packets and prompts from inputs v1: guideline v1 core sections, the generated reference, query-assembled context and the worked examples (`code/s0r2_inputs.py`, `code/s0r2_sample.py`). Score against the v1 reference, with SV (Sonnet) as the upper reference point. Add the offsets-without-tools probe S0 deferred. Set `max_tokens` from the S0 batch sizes (A13). Use the validator's rule warnings in the repair retry. Run the judge test on the S0 A/B and S0-R2 SV/HV differences. |
| S4 | Start from `code/schema/*.yaml`, which equal D2. Generate the annotator reference from `SchemaView` and compare it with S0-R2's `reference.md` (A2). Compile the `s0r2_rules.py` checks as rule-engine `guideline:` warnings. Extend the JSON Schema to `cN` citations, `alternatives` and `extent`. Validate the v1 reference batches and examples. |
| S5 | Re-scope to ADR-0009: measure the extended grammar (`code/mathgrammar/`) on all 28,956 spans with the per-rendition macro tables, with ambiguity and failure categories and the 8 partial spans; the ANTLR backend only as the OPEN-D4-3 revisit check. Add the B1 property check (tree against token canonical form). Run the equivalence tiers on the S0 and S0-R2 value pairs, M13 on math-heavy units, and the verifiers and z3 as briefed. |
| S6 | Trace rows on v1 (T3 C2 with conditions; T4 C11–C17; `cN` evidence outside the unit). Use the B7 columns. Record the S0 key-variant counts as input to OPEN-D3-4. |
| S7 | Link gold from the v1 reference's global entities, with parameter names under B2. Include cross-unit parameter naming (RG-7) as linking cases. |

## E. The items the summary left for the design owner

**Dispositions in the design-phase plan.** I agree with them, except:
- reopen OPEN-D1-3 (B2) and HTML-07 (B13);
- split OPEN-D2-9 (B12);
- add the section C rows.

OPEN-D4-4 is rightly closed only for golden and agent packets; S3 settles the local LLM.

**ADR-0009, ADR-0010 and ADR-0011 against the Q8 decisions.**

| ADR | Fit | Action |
|---|---|---|
| ADR-0009 | Fits | Amend for B1 |
| ADR-0010 | Fits | Amend for B9 |
| ADR-0011 | Fits, and lowers the circularity risk D7 §1 names | Its consequences need A1, A2, A4, A10 and B7 to be buildable |

**Q8 still owes ADRs** for the decisions D0 takes but no record holds, to be written once S4 and S6
report:
- methods write observations and only consolidation writes knowledge;
- PostgreSQL is the single authority;
- domains are LinkML packs compiled to every consumer;
- the pipeline never calls Opus, which works a queue through MCP;
- escalation is routed by policies on measurements.
