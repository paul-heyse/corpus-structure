# Architecture map

Use the [design principles](../design_review/design_principles/core/design-principles.md) and [efficient-architecture heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md) together
when assessing consequential choices; consider physical realization early alongside ownership
and contracts.

**Proposed:** no responsibilities are assigned yet. [DESIGN](DESIGN.md) holds scope, the binding
decisions and durable deferrals; add a focused owner under `sections/` when a responsibility
needs more than a DESIGN section. [STATUS](../../STATUS.md) and the active plan own completion
claims and the disposition of known defects.

| Responsibility | Owner | Source entry / adjacent consumer |
|---|---|---|
| Scope, binding decisions, deferrals | [DESIGN §1, §2, §13](DESIGN.md) | Every owner below; ADRs govern its §B sections |

Record the dependency direction here once there is more than one owner. This table describes
intended ownership; it is not a certificate of current architectural conformance.

## Reading and extending

For a change, identify the semantic owner, its consumer contract and the expected extension axis.
Read that owner plus affected consumers, then the ADR that governs the section
([index](../adr/README.md)); reuse or compose existing capabilities where their semantics fit.
Detailed fields and invariants belong in executable declarations. Update the owner when meaning or
boundaries change, and follow the existing review cadence. Internal refactors need no additional
proof packet. Section IDs never renumber; a moved live section keeps a relocation pointer, and
retired material is recovered from Git ([historical recovery](../README.md#historical-recovery)).
