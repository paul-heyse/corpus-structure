# Target design registers

These seven registers capture the active rows in section 3 of the Notion design as of 2026-11-03. They retain
source statuses, populated design properties and record notes, with a source link per row. Fields left blank
in the source are omitted. Entry links use the Notion record ID so they survive title and order changes.
Catalog relationships outside section 3 link to their Notion entries. One supporting Dropbox folder is cited
through its Notion record, which holds the original shared link.

The earlier full stack and nine-tier rollout are a capability map and experiment backlog. The November 3
[first production milestone](../first-production-milestone.md) sets out the proposed deployment. Statuses such
as Target, Proposed and Prototyped carry the original design or prototype scope.

| Register | Records | Contents |
| --- | ---: | --- |
| [Design questions and decisions](design-questions-and-decisions.md) | 77 | Design questions, risks, and decisions with their rationale, options, dispositions, and dependencies. |
| [Pipeline streams](pipeline-streams.md) | 39 | Each producer’s annotation layer, join key, cost, licence, evidence, and downstream consumers. |
| [Stream combinations](stream-combinations.md) | 84 | The nine-tier capability map, with what each combination adds, its inputs, join keys, and evidence. |
| [Interpretation components](interpretation-components.md) | 10 | Interpretation responsibilities, contracts, mathematics, libraries, and prototype references. |
| [Decision types](decision-types.md) | 30 | Typed decisions, candidate generators, outcomes, and the templates that resolve them. |
| [Inference templates](inference-templates.md) | 10 | Local factor graphs, evidence groups, cross-decision factors, hard constraints, and measures. |
| [Stages](stages.md) | 9 | The earlier tier-by-tier rollout, including record outputs, formal gates, and hand and operational tests. |

[Target pipeline design](../README.md) · [Notion section 3](https://app.notion.com/p/40a141b5836981e8bea1fef28ec39471)
