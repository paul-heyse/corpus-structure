# Test code design principle audit

This is the separate living diagnostic account for test code, test evidence and shared test
infrastructure. The [skill](../../../.claude/skills/design-principle-audit-tests/SKILL.md) owns
the audit method; the [repository binding](../design_principles/binding/corpus-structure.md#test-code-design-principle-audit)
owns invocation, finding identity and follow-up routes. The
[test-assessment companion](../design_principles/core/test-assessment.md) supplies the test-specific
interpretation of the selected core and applicable domain profiles.

## Baseline and coverage

**No test audit has been performed.** This directory is an installed process scaffold, not
evidence of alignment or a diagnosis of the current suite. There is no audited source revision,
publication baseline, coverage claim or finding yet. Creating it neither refreshes nor replaces
the [broad audit](../audit/README.md), whose observations retain their own baseline and limits.

The first audit replaces this paragraph with its source commit, included uncommitted changes,
date, applied standard and companion versions, meaningful inspected scope and exclusions. Identify
the separate publication revision when consumed by a review. On refresh, distinguish newly
examined evidence from inherited observations and retain the latter's original date and limits.

Scope follows testing responsibilities, including relevant inline tests and support outside
test directories. Production contracts and dependencies are context for judging the claims;
this account does not imply that the enclosing production system was audited or qualified.

## Reading the account

Start with the baseline and a short synthesis of material causes and assurance consequences.
Add topic pages when actual findings justify them; no empty category pages or dated audit
directories are required. Useful topics might concern oracle independence, shared support,
assertion strength, boundary fidelity, isolation or execution fit. These are possible reading
routes, not a required document structure or inspection quota.

Findings explain what claim is at risk, why the structural cause matters, the inspected footprint,
decisive sources, contrary evidence and material uncertainty. Use the standard's evidence
vocabulary and cite applicable core/profile principles plus relevant companion sections.
Source reasoning can establish a structural weakness without running the suite; a passing
suite does not establish its evidential quality.

## Finding ownership and history

New test findings use stable DTA-nnn identities, beginning with DTA-001. Give each finding one
primary home and link it from an index when that improves navigation. Keep identity and lineage
as explanations or topic boundaries change; never reuse retired IDs.

The broad and test accounts can examine related paths at different baselines. If the structural
cause is already a finding in the broad account, retain its identity and home and link to it here.
State what was reexamined and any applicability limit without copying the diagnosis or claiming
to refresh the other account. A new, distinct cause may deserve its own finding; sharing a
component or principle is insufficient reason to merge diagnoses. A move records its lineage
and leaves a route from the former home.

The account owns diagnosis at its stated baseline. Reviews own correction alternatives and
judgment; implementation plans own scheduled disposition, progress and closure evidence. Link
those owners without copying mutable status. Remove resolved material only on evidence, retaining
recoverable closure through the removal commit. Git holds earlier accounts; there is no separate
audit archive or execution register.

Ordinary implementation does not maintain this collection as a recurring gate. A test-scope audit
or a subsequent review uses the binding's deliberate invocation and freshness rules. Installing
this directory performs no audit, starts no repairs and establishes no scientific or product
qualification.
