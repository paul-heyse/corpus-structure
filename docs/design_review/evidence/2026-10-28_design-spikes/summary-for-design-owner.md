# S0 and S1 — summary for the design owner

**Date:** 2026-10-28. **From:** the spike lane (S0/S1 plan series). **For:** design-phase Q5 (fold-in 1)
and X1 of the [spike plan](../../../plans/design-spikes-s0-s1_2026-10-28.md). The two reports hold the
evidence; this page says what they decide, what has already changed in the design and what waits
for you.

## Reports and how to query them

- [S1 report](S1-report.md): ingest and segmentation of the 78 Siegrist pages.
- [S0 report](S0-report.md): reference annotations of the twelve core units, blind passes on three
  models, adjudication, M13, keys, sizes, gaps. Every figure is rendered from the evidence catalog.
- Every finalized result is a record in [records/](records/) (question, the OPEN items it informs,
  method, commands, agents, hashed inputs and outputs, results, conclusion); the folder README
  indexes them. `just evidence` rebuilds `build/evidence.duckdb`; for example
  `SELECT * FROM records_for('OPEN-D1-2')` lists the evidence for one item (ADR-0010).

## Answers to the scheduled items

| Item | Answer (detail and evidence in the report) |
|---|---|
| OPEN-D1-1 | Closed in favour of b′: inline math merged into one token before the parser; F1 1.0 against 0.80 for raw text (S1) |
| OPEN-D1-2 | A `section` extent is needed; M13 reproduces the annotated scopes with section-wide and reopen binders (S0) |
| OPEN-D1-3 | Unsettled by v0 (`sigma` against `shape`); rule proposed: name by the role the source states, else the symbol (S0, GG-5) |
| OPEN-D1-4 | `section` under nested h3/h4 synthesis; `document` never needed (S0) |
| OPEN-D2-4 | Keep property predicates; add a standard-deviation property (S0) |
| OPEN-D2-5 | Standardized families as families of their own worked everywhere; "standard" does not mean parameter-free (S0) |
| OPEN-D3-4 | Evidence for D3/D5: meaning keys are more stable than claim keys; two D1 §10.1 key rules cause most differences (S0) |
| OPEN-D4-4 | The unit is the right packet: all fit the local cap and lose nothing on what is claimed; without the pages Sonnet loses some qualifier agreement (roles, bindings), which the standing context should carry; size the output budget from batches (S0) |
| OPEN-D4-5 | Rule-based scoping suffices with two additions (sentence-initial "if"; paragraph statements) (S0) |
| OPEN-D5-1 | Not tested by these units (S0) |
| OPEN-D7-2 | Evidence for S5: canonical form decides nearly every value comparison; numeric and manual tiers needed a handful of times (S0) |
| OPEN-D8-3 | Fresh subagent per pass, one input and one output folder, transcript audit of every file opened (S0) |
| OPEN-D9-1 | Resolved for the S0/S1 libraries on Python 3.14.10 (recorded in D9 §2); gliner2, z3, pgmpy and splink remain for S2, S4, S5 |
| HTML-01…07 | Seven HTML rules D1/D4 did not state, each specified in the S1 report; these rows exist only in the spike plan and should join your findings table |

## What the spike lane already changed in the design (operator-authorized)

| Change | Where | Commit | Label now |
|---|---|---|---|
| Canonical form written from the parse tree of one math grammar; slot-range validation | D1 §6.2 | 9150048 | Tested (spike instruments) |
| Sentence-initial "if" in the binder lexicon | D2 §12.1 | 9150048 | Measured (M13 probe) |
| Quote-location cascade that keeps source offsets | D4 §4.3 | 9150048 | Tested (733 of 735 quotes exact) |
| Math delimiting generated from the source profile; source facts as profile data | D4 M01 | 9150048 | Tested (S1 adapter) |
| Symbols and math kinds from the grammar | D4 M09 | 9150048 | Implemented (spike) |
| One Lark grammar extending SymPy's, ambiguity explicit, failures categorized | D4 M11 | 9150048 | Measured (parse rate on 78 pages) |
| Binder patterns as spaCy `Matcher` rules; paragraph statements | D4 M13 | 9150048 | Measured (20 of 20 scopes) |
| Evidence records and catalog | DESIGN §2 | 77e3e5c | Implemented and Tested |
| SymPy 1.14.0 hold | pins.md | 9150048 | — |

The reasons and rejected alternatives are in [ADR-0009](../../../adr/0009-math-grammar-authority.md) and
[ADR-0010](../../../adr/0010-evidence-records.md). Library realization stays in the D4 cards with the
design it serves.

## Proposed for the fold-in (not yet in the design)

The S0 report's "Design implications" table is the full list; in short:

- **D2 §10 guideline:** rules G1–G5 and the top-ranked gaps (binding of symbols named as parameters
  later, modality inside definitions, restrictions in premises, structural claims, formulas without
  the generated variable, a statement-role table by kind, references outside the unit).
- **D2 §9 schema:** number values with units; an independence predicate; `posed` claims; a
  standard-deviation property. **D1 §7:** an indexed-set argument for `independent`.
- **D1 §10.1 keys:** key a statement by the segment its anchor covers; drop a global entity's label
  from its key when its identity is complete.
- **D4:** the M13 paragraph rule; output budgets sized from batches; the seven HTML rules in M01–M03.
- **trace.md:** T1 gains `parameter_role` claims; T4 includes its second paragraph.

## A finding that changes D7 and D2 §10.10: the inputs, not the models

Sonnet 5.5 matches Opus on what is claimed (core F1 0.91–0.92 against the reference, Opus 0.93) and,
as adjudicator, reaches core 0.97 and full 0.82 against the root. Sonnet and Haiku trail on
qualifiers, but Sonnet against an Opus pass is not far below Opus against Opus, and the losses sit
where the inputs leave a decision to inference:

- which claims carry a condition tree (Sonnet conditions definientia on their premise; the reference conditions conclusions only);
- statement roles, which no rule assigns;
- the binding kinds, explained only in a table deep in the model excerpt;
- standing context chosen by position, which brought one exercise the setup of another;
- no generated per-predicate inventory (D2 §10.10 was a placeholder) and no worked example.

Proposed: generate the annotator reference from the schema; write those rules; assemble standing
context by query over the segment and scope indexes, each item citable by id; and serve the same
lookups to agents as D8 tools. Then rerun a Sonnet and a Haiku pass, including units from outside
the twelve. This bears on D7 §3's golden author, which the plan currently names as Opus.

## Waiting on decisions

- **Operator:** review of both reports, which gates X1; the golden author after the rerun above; and
  whether finalized evidence records outlive their folder (this would supersede ADR-0001's clause).
- **Design owner:** the dispositions of the items above in your findings table, and whether ADR-0009
  and ADR-0010 fit the Q8 decisions. Both ADRs were written in the spike lane with the operator's
  approval.
