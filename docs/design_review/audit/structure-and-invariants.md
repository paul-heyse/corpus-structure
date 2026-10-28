# Structure and invariants

Findings about distinctions, state, lifecycle and enforcement: FP-05, DP-02, DP-03, DP-05, DP-09,
DP-12 and DP-19–DP-21. Baseline, scope and scenarios are in the [README](README.md).

<a id="da-012"></a>

## DA-012 — Operational closed sets have uneven authority and enforcement

**Principles:** DP-02, DP-03, DP-08.
**Subject:** accepted target and proposed design (D3, D4, D6); `payloads.py` is implemented.

**Diagnosis.**
- **Unchecked columns.** `ops.task.stage` has no CHECK and no enum (D3 line 527), yet views filter
  on literal stage names. `ops.policy_rule.unit_type` has no CHECK, while `ops.task.unit_type` has
  one.
- **D4 disagrees with `TaskUnitType`.** D4's `Method.unit_type` list has `span`, which
  `TaskUnitType` lacks. It lacks `document` (M01's own unit), `identity_group`, `observation` and
  `golden_unit`. Its `family` field is an untyped `str`.
- **Policy vocabulary is not closed.**
  - The policy symbol `judgment(m)` returns "decision or confidence" (D6 §7), and the example mixes
    `'unsure'` with `'low'`.
  - String literals in rule-engine conditions, such as `target.kind == 'alternative_group'`, are
    type-checked only as strings.
- **Constraints that are only comments.** "Always `warning` in group `guideline`" is a comment, not
  a constraint (D3 §3).
- **Mixed identifier types.** `InterventionTarget.ref` and `JudgmentTarget.ref` are `str | int`,
  mixing semantic keys with row ids (`payloads.py:68`, `:226`).

**Consequence.** **S4, add a method or a model tier:** the unit type and family are interpreted per
consumer, and a policy typo compiles and never matches.

**Counterevidence.** Every `vocab.py` enum matches its D3 CHECK today, and 0001 is planned to
generate the CHECKs ([map](domain-model-map.md#strengths-to-keep)).

**Leads:** stage names and method unit types as enums that D3 and D4 consume; policy literals
checked against them at compile time.

**Related:** [DA-002](semantic-model-and-authority.md#da-002).

<a id="da-013"></a>

## DA-013 — Keying and frame outcomes are prose where consumers must count them

**Principles:** DP-21, DP-02, FP-02.
**Subject:** implemented; the consumer (C1's `PassReport`) is the accepted target.

**Diagnosis.**
- `Keys.dropped` and `Keys.dropped_members` hold `str(error)` (`keys.py:571`, `:598`, `:611`,
  `:644`, `:654`, `:661`), for example "condition reference cycle: a -> b -> a" or
  "predicate 'x' is not in the schema".
- `FrameFailure.reason` mixes `LocatorRefused`'s typed reasons with free text (`frame.py:27`,
  `:50-85`).

D5 §5.2 and §8.3 require drops to be counted by reason. The phase 0 consolidation package names
codes (`condition_cycle`, `orphaned_premise`, …), so C1 would have to classify prose.

**Consequence.** **S1, S6:** a new keying failure is miscounted or lumped in with others, and
`explain` cannot say why a claim was dropped.

**Counterevidence.** `LocatorRefused` already carries a typed reason, so the codebase has the
pattern.

**Leads:** a reason code on `KeyingError` and `FrameFailure`, with the message derived from it.

**Related:** [DA-007](semantic-model-and-authority.md#da-007).

<a id="da-014"></a>

## DA-014 — Locator identity limits are stated more narrowly than a plan's closure check assumes

**Principles:** DP-04.
**Subject:** implemented (`core/locators.py`, `core/keys.py:374-405`); accepted target (ADR-0019).

**Diagnosis.**
- **Already stated** in D1 §10.3 and ADR-0019: generated prefixes depend on sibling blocks of the
  same kind.
- **Not stated:** a statement's first-sentence ordinal shifts for later statements in the same
  anchor when a sentence is inserted earlier in that anchor, or when sentence segmentation changes.
- **The mismatch.** The design-phase plan's P0CL-01 closure check reads "an edit to one paragraph
  leaves other statements' keys unchanged". D1 §10.1's property is narrower: an edit "that leaves
  every block's opening words unchanged".

**Consequence.** **S3:** a segmenter change moves statement keys within an anchor, and the closure
check as worded would pass on a property the design does not claim.

**Related:** IR-13 (phase 0 plan §11, empty-text segments).

<a id="da-015"></a>

## DA-015 — Readers of M19 verdicts have no rule for selecting the current pass (suspected)

**Principles:** DP-19, DP-05.
**Subject:** accepted target; arises in phase 1.

**Diagnosis.** Each finalize pass writes one M19 task's refuted-only `verification` rows. Those rows
become effective observations of the run through `kb.run_observation` (D3 §8). Neither D5 §8.1 nor
D4 M19 says how readers such as `explain` (D8) or coverage choose the current pass's M19 task. Phase
0 has one finalize pass; route iterations (up to three) and derive's incremental pass start in phase
1.

**Consequence.** **S6:** `explain` could show a refutation from pass 1 for a claim that a later pass
accepted, and per-rule coverage could double-count across passes.

**Uncertainty.** The plans may scope readers to the last pass somewhere not inspected.

<a id="da-016"></a>

## DA-016 — Confidence "policy data" is split between the policy file and prose (proposed design)

**Principles:** DP-05, DP-01.
**Subject:** proposed (phase 1).

**Diagnosis.** D5 §6.3 says the multipliers and caps "are policy data, not code". The `policies.yaml`
shape in D6 §7.1 holds only `priors`. They are keyed by a source vocabulary (`agent`,
`local_llm_full`, …) that is defined nowhere and has no stated mapping from methods or
configurations.

**Consequence.** **S4:** a new tier's prior has no declared key to attach to.

<a id="da-017"></a>

## DA-017 — The `agent_reuse: by_unit` option overrides the reuse key without defining it (suspected)

**Principles:** DP-09.
**Subject:** accepted target (D6 §4).

**Diagnosis.** D6 introduces `agent_reuse: by_unit` (D6 line 255) and implies reuse across differing
prompt-part hashes ("asked only where the operator's change applies"). The option's matching rule
is defined nowhere in D6, D7 or D8 (grep, 2026-10-28).

**Consequence.** **S4 and S5:** with the option set, a stale agent result can be reused under a
changed prompt, and nothing defines when that is correct.
