# Status

_Updated 2026-10-28 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Increment and slice

- Scaffolded from project-template. Scope, first binding decisions and the first plan are not
  written yet.
- Consequential choices use the [design principles](docs/design_review/design_principles/core/design-principles.md) and [efficient-architecture heuristics](docs/design_review/design_principles/core/efficient-architecture-heuristics.md) together,
  with qualitative judgment early in physical design and no added checklist or proof machinery.
- The [library-leverage workflow](docs/library_leverage/README.md) is installed with three skills
  and distinct unassessed output folders. No opportunity audit or applicability review has run.

## Last verified (2026-10-28)

| Command | Outcome and scope |
|---|---|
| `just check` | `not_run`: record the first run here. |
| `just turn-end` | `passed` (2026-10-28, after writing the S0/S1 plan series; it re-wrapped two lines in `tests/scripts/test_repo_paths.py`) |

## Known failures, blocks and decisions

- Two plans declare themselves active (design-phase and the S0/S1 execution plan). The operator
  chose on 2026-10-28 to keep both for now; design-phase's findings table governs where the two
  differ.
- The pre-execution Siegrist HTML inventory found structures D1 §3 does not cover (bare `align`
  math, unbalanced delimiters, JS-filled empty links, synthesized sections, misnested `<p>`):
  rows HTML-01…07 in the S0/S1 plan, not yet in design-phase's table.

## Design phase (2026-10-28)

- The proposed target design is written: [D0–D9 and the worked trace](docs/design/README.md),
  all **Proposed**, nothing implemented. DESIGN §1 records the objective; binding decisions (§2)
  wait for ADRs after the spikes.
- Spike briefs S0–S7 are in
  [design_review/evidence/2026-10-28_design-spikes](docs/design_review/evidence/2026-10-28_design-spikes/README.md);
  none has run.
- The active plan is [design-phase_2026-10-28](docs/plans/design-phase_2026-10-28.md): lanes,
  queue, the library-leverage brief and the disposition of every `OPEN-Dn-k` item.
- Its Q1 (S1) and Q2 (S0) are planned in detail by the
  [S0/S1 execution plan](docs/plans/design-spikes-s0-s1_2026-10-28.md) and its supporting
  documents (S1 ingest, S0 annotations, comparison instruments): HTML library selection, adapter
  and sentence variants, blind passes under the D7 protocol, alignment by D7 §5. Written
  2026-10-28; nothing executed.

## Next

- Spike lane: execute the S0/S1 plan from E0 (spike environment) and S1-A (adapter on the
  four spike pages); S0-A packets follow S1-B. S4 and S6 alongside (design-phase Q3).
- Library lane: pass 1 over D4 cards and D2 §7 compilers (plan Q4).
