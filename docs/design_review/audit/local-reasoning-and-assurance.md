# Local reasoning and assurance

**Source `fbd3f2a98`, 2026-11-17** ([baseline and limits](README.md#baseline)). This page is
navigation by responsibility, not another finding register:

- [Current model owners](domain-model-map.md) and
  [semantic definitions and their consumers](semantic-model-and-authority.md).
- [Outcomes, policy and claim ownership](structure-and-invariants.md).
- [Native custody, admission and recovery](native-integrity.md).
- [Served identity and evaluation policy](served-claims.md).
- [Composition, hosts and superseded machinery](boundaries-and-composition.md).
- [Necessary versus repeated work](execution-fit.md).
- [The domain model and execution together, with the test account](model-and-execution.md).

Whether the tests would detect a wrong implementation of the mechanisms described in this
account is the subject of the separate [test account](../test-audit/README.md), refreshed in
the same engagement at the same source commit. Production source reasoning is not an
independent oracle for semantic correctness, and static inspection is not database, provider,
CLI, MCP or release qualification. No test campaign follows from this refresh.

Two assurance observations from this refresh belong to the test account and are linked, not
repeated: several reuse and skip mechanisms are tested only on the path where reuse is correct
([DTA-044](../test-audit/evidence-and-discrimination.md#dta-044)), and several commits that
introduced them record `runtime not_run`.

<a id="da-021"></a>
<a id="da-022"></a>
<a id="da-023"></a>

| ID | Status at `fbd3f2a98` | Note |
|---|---|---|
| DA-021 | Not re-examined | Historical correction of 2026-10-29 |
| DA-022 | Not re-examined | Historical correction of 2026-10-29 |
| DA-023 | Not re-examined | Historical correction |

Earlier text is in Git at `fbd3f2a98`.
