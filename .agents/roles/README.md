# Agent roles and coordination

Use delegation when another context, capability or perspective can advance the outcome enough
to justify briefing and integration. It can supply useful progress, earlier learning or independent
judgment, including when work proceeds serially. No role sequence or minimum agent count applies.

Shape contributions around useful results, shared decisions and dependencies. Components,
documents and roles offer possible boundaries; choose boundaries that let workers reason and act
coherently. Deliberately overlapping investigations can supply independent judgment. Concurrent
editing still needs explicit ownership and coordination.

Readiness depends on the result being requested. An investigation can resolve an open contract;
consumer preparation may need agreed semantics, while working integration needs implemented
prerequisites. Establish the shared meaning that dependent work relies on and identify consequential
provisional assumptions. Avoid turning a convenient package order into unnecessary barriers.

Give workers discretion within accepted outcomes, contracts and delegated decision authority.
Reconcile changes affecting other contributions or semantic owners with the coordinator and those
owners. The coordinator remains accountable for design coherence, integration and acceptance.

Coordinate conflicting effects and shared resources through the repository's operating rules.
Worktree isolation, contract publication, generated-file ownership and validation rules protect
particular effects; they do not prescribe the task decomposition. Prepare near-term work enough
to begin, and develop later assignments as their prerequisites become clearer. Reconsider a split
when repeated negotiation dominates useful progress, its premises change or its result loses its
consumer. Continue independent authorized work whose assumptions still hold.

## Roles and runtime routing

Read the relevant shared contract when assigning work. Workers load [the common contract](worker.md)
and their role; native definitions carry model and effort settings only.

| Responsibility | Shared contract | Codex model / effort |
|---|---|---|
| Repository evidence and dependency mapping | [code-mapper](code-mapper.md) | `gpt-6-luna` / high |
| Library capabilities, contracts and alternatives | [library-research](library-research.md) | `gpt-6.1-sol` / medium |
| Independent architecture and domain assessment | [design-reviewer](design-reviewer.md) | `gpt-6.1-sol` / high |
| Bounded implementation with local discretion | [executor](executor.md) | `gpt-6.1-sol` / high |
| Correctness and regression review | [implementation-reviewer](implementation-reviewer.md) | `gpt-6.1-sol` / high |
| Functional verification and failure diagnosis | [test-agent](test-agent.md) | `gpt-6.1-sol` / medium |

Codex definitions live in [`.codex/agents/`](../../.codex/agents/). The coordinator defaults to
Astra/high; use greater effort when the actual reasoning warrants it. These are policy defaults,
not measured cost or quality claims. Revisit them for concrete failures or model/runtime
availability changes; no calibration exercise is required. Preserve a user's explicit runtime choice.

Prefer the named native role. If the available delegation tool has no role selector, supply the
shared contract paths and choose the table's model and effort explicitly. With Codex's collaboration
tool, use a focused brief with `fork_turns="none"` when selecting a different model; a full-history
fork inherits the parent. If the runtime cannot select a model, disclose the fallback. Do not assume
editing configuration changes agents already running. Native role files carry no permission
restrictions: Codex roles inherit the session's sandbox and approval settings (Codex ignores
sandbox keys in role files). The shared contracts alone define each role's permitted effects;
live parent permission overrides take precedence.

## Coordinate the work

Give each assignment an outcome, bounded scope, relevant authorities, settled decisions, delegated
decision scope and exact baseline (including relevant uncommitted changes), permitted files/effects, sibling ownership,
dependencies and useful completion evidence. Provide enough context to act independently without
copying the whole conversation. Reuse a worker for coherent follow-up; use fresh context for an
independent review, giving requirements and source evidence without steering its verdict.

State the completion boundary explicitly: targeted checks end the worker's slice; the coordinator
owns assembled-tree acceptance, qualification and handoff. Preserve native command/environment
choice within assigned effects. Resume through [STATUS](../../STATUS.md) → owning active plan →
semantic owner; workers start from the brief and expand for dependencies. [Command guidance](../../AGENTS.md#commands)
supplies discovery and examples without another loader, launch hook or task register.

Name an owner for shared model declarations, manifests, generated surfaces and integration.
Coordinate write scopes explicitly. Follow AGENTS.md for worktree isolation, contract/dependency
publication and shared-resource use. Give reviewers concrete acceptance criteria, affected consumers
and relevant failure cases. Review or test a stable revision or identified tree; re-evaluate affected evidence after integration changes it.
Keep a single writer for the final plan, shared status and finding disposition unless ownership is
explicitly partitioned. Existing plans own scheduled work; do not create a second task ledger.

Read decisive evidence and reconcile results rather than accepting a worker's completion message
as verification. Resolve architectural contradictions through the existing decision and review
process; retain unresolved findings and their effects on acceptance. Workers exercise delegated judgment
within their brief. Surface consequential absence claims, conflicting evidence,
unresolved ownership or contract decisions, and a second failed attempt at the same repair. The
coordinator chooses whether to narrow the question, inspect sources, run a focused functional check,
handle it directly or route stronger work. These are reassessment triggers, not automatic reruns.

### Stronger-worker routing

Codex custom roles pin their model and effort, overriding spawn-time choices. For stronger evidence
work, use the built-in `default` role with `gpt-6.1-sol` / `high`, `fork_turns="none"`, and a focused
brief supplying the common and relevant evidence-role contracts, sources and the evidence role's
permitted effects.
Use the built-in `worker` only for authorized edits with explicit ownership. Do not create duplicate
higher-tier roles or assume an override changes a named custom role.

## Workflow integration

The [design principles](../../docs/design_review/design_principles/core/design-principles.md) together with
the [heuristic companion](../../docs/design_review/design_principles/core/efficient-architecture-heuristics.md)
guide consequential design and implementation choices before physical organization becomes
entrenched. Briefs should carry relevant settled decisions and open questions; execution uses
only consequential open choices or material mismatches, without restarting settled reviews.
This is qualitative guidance, not an exhaustive checklist, cost model or proof requirement.

| Workflow | Typical contribution |
|---|---|
| Design principle audit | Bounded evidence and diagnostic contributions inform one coordinator-published baseline account |
| Review planning and design review | The refreshed audit informs solution inquiry; a fresh reviewer assesses alternatives within the operator's selected focus |
| Functional-extension review preparation and review | A reviewer explores useful capabilities within the operator's chosen scope and compares realizations; no diagnostic audit prerequisite |
| Library leverage | Mappers identify concrete opportunities, library researchers assess focused mechanisms, and a reviewer compares complete options; the coordinator publishes evergreen accounts and shared additional patterns under the three leverage skills |
| Design-review recommendation audit | A fresh design reviewer assesses recommendations and omissions; the coordinator publishes net changes and the attributed integrated revision |
| Plan preparation and creation | Evidence workers inform options and the integral foundation assessment; focused design advice addresses consequential questions; one author assembles the document |
| Execution planning and execution | The coordinator orders ready packages; executors implement; implementation reviewers and test agents assess stable work; design review follows the binding's cadence |
| Plan-improvement review | A reviewer assesses alignment, general enhancements and execution improvements across the remaining change footprint; the coordinator publishes a standalone review, with plan revision separately instructed |
| Plan-completion audit | A fresh implementation reviewer examines claimed accepted scope across consumers and packages; the coordinator corrects the same plan's current account |

The [process skills](../../.claude/skills/README.md) own each workflow. Planning companions produce
an adaptable conversational approach and can use the available planning interface. Skills do not
switch the runtime into Plan mode. The applicable broad or test-scope audit precedes a new diagnostic design-review engagement under the binding;
functional-extension review, plan-improvement review, ordinary implementation and focused plan advice do not initiate it.
No extra planning artifact or hook is required.
Recommendation and completion audits are deliberate requested or explicitly planned boundaries,
not recurring slice reviews or automatic handoff steps. They reuse these roles without new adapters;
their skills own publication and the difference between editorial and execution disposition.

Configuration reference, consulted 2026-09-30:
[Codex custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Local adapters target Codex (ADR-0007). The tracked `.claude/skills` directory remains the
process-skill source used by `.agents/skills`; central library skills remain inactive references;
its name does not introduce a second runtime obligation.
