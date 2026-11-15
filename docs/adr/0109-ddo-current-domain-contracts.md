---
id: ADR-0109
title: Checked domain contracts and target-native adoption replace legacy compatibility
status: accepted
date: 2026-11-15
supersedes: [ADR-0095]
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A maintained target capability cannot preserve its required semantic or native custody guarantees without an obsolete interpreter.
---

## Context

The operator accepted Domain-model I01/I09 and authorized complete DDO-00–08 execution, including
DDO-09/10 successor contracts needed for code retirement. ADR-0095 required preservation-led
adoption. Generated historical data is useful where convertible but does not warrant permanent
legacy architecture. The audited review at4f32589d0 distinguishes semantic correction from data
transport and preserves native protection independently of backward compatibility.

## Options

1. Preserve old decoders, operation compiler and sealed readers. Rejected: historical generated
state would continue to determine the target and every new contract's maintenance burden.
2. Delete all data. Unnecessary: useful faithful target-native conversion can preserve meaning.
3. One current model with selective import/regeneration and complete code retirement. Selected.
Preparation, normal reads and testing avoid obsolete interpretation machinery; native failure,
trust and concurrency guarantees remain required. Migration has finite usefulness rather than
becoming a second supported application.

## Decision

Checked subject definitions and explicit role/population relations govern discovery and identity.
Enforcement references resolve existing binding/schema/native/implementation owners with revisions
and parameters. Meaningful coverage/numerical contracts replace labels before those labels retire.
Slice-owned descriptive prose is not semantic definition/recipe identity; reflection-sensitive
facts and nonslice/native/external behavior revisions remain determinants. Current compact governing
facts and exact source/runtime artifacts remain separate. No whole-runtime salt or second registry.

Consolidation and cut materialization remain declared operations over exact values, support,
alternatives, population and policy. Currentness names its comparison target; reuse/reverse impact
share those contracts, include new/absent population members and stop at equal admissible value/support.
These surviving ADR-0095 currentness decisions remain in force.

The target supports one current encoding family and target-native interfaces. Multiple releases
and result histories within that basis retain exact attribution; old-format interpreters do not.
Import useful data only where source/evidence/bindings establish target meaning. Regenerate or
reassess changed question/input/output/policy bases; do not fabricate target execution/support or
accepted standing. Old bytes may remain inert or be discarded. Optional conversion completeness
never blocks target design or independent code retirement. Finite converters leave normal execution
and are removed after their selected use.

Fence/drain old writers at separately authorized adoption, install a supported target (clean baseline
where an old upgrade chain retains legacy dependencies), verify maintained consumers and retire old
catalogs/compilers/facades/decoders/writers/grants/configuration and mechanism-only tests. Do not edit
frozen revisions in place or infer instance preservation from file retention. Native permissions,
lease/attempt fences, unknown-effect handling, source fidelity and protected evaluation independence
remain required. Retain original plans/evidence and failed/interrupted receipts.

This decision qualifies historical-reader clauses in ADR-0092/0098/0105/0107/0108; their mixed
frontends, compact identities, binary staging, source-analysis, graph and native-trust decisions
remain authoritative. It replaces ADR-0095's mandatory preservation closure with selected target-native
transition. Prior censuses retain their dates and evidence, not ongoing recovery obligations.

## Consequences

The DDO coordinator owns execution, scoped qualification and remaining work. Acceptance is a rule
change, not implementation or verified closure. Native successors use existing authoring/candidate/
registration owners. No persistent deployment, activation, data reset or migration is performed by
this record. Complete functional/native/provider/public qualification remains separately evidenced.
Benefits are Proposed, qualitative and unmeasured.
