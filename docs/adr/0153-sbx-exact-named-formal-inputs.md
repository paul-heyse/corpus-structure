---
id: ADR-0153
title: Select independent formal analyses as an exact named input set
status: accepted
date: 2026-11-22
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
revisit: An admitted construction workflow needs multiple independently configured producer selections within one demand.
---

## Context

Construction can bind multiple eligible formal reports from the same source scope. The ordinary
source discovery route selects one frozen configuration per operation within a demand. A caller
also needs to compose reports from independent analyses, each with its own producing request,
runtime and rule witnesses. Both scalar results can emit at position zero and use the same
member key. [Formal set decision](0151-sbx-discovered-formal-inputs.md)

## Options

1. Select one configured formal report per construction demand. This uses ordinary discovery alone
   and gives up the ability to compose independent reports.
2. Extend a single demand to schedule several configurations of one operation. This adds another
   identity to every operation selection, obligation and propagation edge. It would support a wider
   orchestration workflow if required.
3. Let construction name an exact existing source set for the `formal` role. This uses the
   same source-set proof, binding and selected-read machinery that already admits retained
   inputs from other demands. Each producer keeps its original scope and rule custody.

## Decision

The formal producer freezes the existing grammar `math_start` choice with the ordinary request.
The default is `any_value`. Both direct execution and the spawned worker use the captured choice.

The construction `formal` role declares `construction-formal-evidence` as an optional named
scope with original-source association. An omitted scope uses its ordinary discovered inputs.
A supplied scope establishes its complete selected population through the existing exact
source-set proof, including when it is empty. The bound source, subject and analyzed scope remain
part of eligibility. Required frozen source-set roles continue to require an explicit scope.

The construction result cites the exact original ledger occurrence and member. The read owner
compares the original product, member and multiplicity to the current selected use.

## Consequences

This composes independently produced alternatives without adding a producer priority, a second
construction operation or another scheduler identity. The same source-set checks serve original
and retained acquisition, including proof failures and explicit empty selection. The [SBX-05
plan](../plans/set-based-execution/references-and-projection-keys.md#sbx-05) owns the integrated
two-report publication and selected readback.
