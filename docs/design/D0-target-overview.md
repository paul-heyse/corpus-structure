# D0 · Target overview

**Proposed (2026-10-28).** Repository copy of the target design agreed in conversation on
2026-10-28. From this commit the repository is authoritative; the claude.ai document of the same
name is a superseded draft.

## Bottom line

The domain model is data, and every method is a measured, swappable producer of observations
about it.

1. **Output.** A qualified-claim knowledge graph: a LinkML schema, resolved entities, and claims
   that carry qualifiers (conditions, modality, scope, attribution, time) and evidence spans.
   Goldens, Opus interventions and every method's output use this same representation, so
   evaluation is a diff ([D1](D1-knowledge-representation.md)).
2. **Analysis.** One schema-driven loop: ingest → profile → schema → extract → normalize →
   resolve → consolidate → validate → measure → route. The LinkML schema compiles into the
   GLiNER2 extraction schema, the JSON Schema for LLM output and the validation rules, so one
   source drives all three ([D2](D2-schema-and-guidelines.md), [D4](D4-method-catalog.md)).
3. **Conditional use.** Cheap methods run on everything. Measured gaps (coverage, confidence,
   disagreement, constraint violation, identity grey zone, parse failure) trigger escalation
   through rule-engine policies stored as data, up a ladder from a local LLM on the RTX 5090 to
   Opus in the Claude Code session ([D6](D6-orchestration-metrics-policies.md)).
4. **Store.** One PostgreSQL 18 database with JSONB, pgvector and pg_textsearch. The operations
   are data too: methods, configurations, policy rules, tasks with the metrics that triggered
   them, measurements, interventions, goldens and experiments ([D3](D3-database.md)).
5. **Scaling.** A walking skeleton first, in which Opus does most of the work through recorded
   tools. Each stage then passes to cheaper methods only when golden-set evaluation shows they
   match or beat Opus. Intervention share sits beside F1 as the headline metric
   ([D7](D7-evaluation-goldens-outer-loop.md), [D9](D9-repository-and-phase0.md)).

## Why a fresh build

The previous repository (`corpus-intelligence`, read-only from 2026-10-28) holds 566k product
lines and 646k test lines for 70 KB of source text, and no corpus journey ever ran end to end.
Four causes:

| Cause | Response in this design |
|---|---|
| Meaning lived in Python classes, so each new distinction was a code, codec and migration change | Schema as data (LinkML) and one generic claim representation |
| Guarantees (custody, exact replay, sealed publication) were built before any output existed | Append-only observations plus run-scoped materializations; heavier guarantees only for a named consumer |
| Tools were adopted per gap as separate stages and never compared on a shared scoreboard | Every method emits the same observation type; policies route; golden-set evaluation decides promotion |
| Domain mechanisms were hard-coded for statistics | A generic core plus domain packs (schema, guideline, policies, verifiers) |

What carries over is the set of distinctions the old plans protected: source fidelity,
mathematical validity, applicability, acceptance, execution success and usefulness are different
things, and unavailable, empty, ambiguous, unsupported, failed and unreviewed are different
non-positive states. Here they are fields and statuses
([D1 §8](D1-knowledge-representation.md#8-statuses-and-non-positive-states)), not subsystems.

## The loop

| # | Stage | Primary method | Escalation on a measured gap | Writes |
|---|---|---|---|---|
| 1 | Ingest and segment | lxml + pylatexenc (HTML), Docling (PDF), spaCy sentences | MinerU VLM for failed layouts | documents, renditions, segments, spans |
| 2 | Profile | GLiNER2 unit classification, term statistics, embeddings | Opus domain brief | profile observations |
| 3 | Schema | LinkML domain pack | Opus schema proposals from coverage gaps | schema version |
| 4 | Extract | GLiNER2 compiled from the schema; `JointIE`; spaCy patterns; math spans | LLM claim extraction (local, then Opus) | observations |
| 5 | Normalize | sympy (LaTeX), pint, lark, dates | LLM normalization | value observations |
| 6 | Resolve | symbol scoping, alias and pgvector linking, Splink for records | LLM adjudication | link observations |
| 7 | Consolidate | claim keys, corroboration, pgmpy latent-truth confidence | — | entities, claims |
| 8 | Validate | JSON Schema, rule-engine rules, z3 conditions, sympy and domain verifiers | Opus reviews conflicts | statuses, conflicts |
| 9 | Measure and route | metrics; rule-engine policy chain | — | measurements, next tasks |

Stages 3 and 4 iterate: schema-driven extraction exposes what the schema misses, which feeds the
next schema version.

## Model tiers

| Tier | Realization now | Role now | Role later |
|---|---|---|---|
| Encoders and deterministic methods | spaCy, GLiNER2.5, pint, lark, sympy, z3, Splink | Every unit | Unchanged |
| Local LLM | vLLM 0.31 on the RTX 5090 (32 GB), starting from Qwen3.5-9B; a larger quantized model tested in spike S3 | First escalation: verification, qualifiers, pre-adjudication with a rationale | Directional proxy for hosted-model prompts and evidence packing |
| Opus 5.5 | The Claude Code session, working a queue through MCP tools ([D8](D8-agent-and-query-interfaces.md)) | Final adjudication, goldens, guidelines, schema proposals | Goldens and guidelines |
| Hosted APIs | — | — | Production escalation tier |

All LLM tiers share one prompt and evidence-packet format compiled from the schema. The pipeline
never calls Opus: it queues tasks as `awaiting_agent`, and a run waits at a barrier or completes
with those items explicitly unresolved.

## Phases

| Phase | Adds | Opus mainly | Gate |
|---|---|---|---|
| 0 · Skeleton | Meta-model in PostgreSQL, HTML ingest, Opus intervention tools, query API, evaluation harness | Extracts all claims; drafts schema, guideline, goldens | The trace units and the spike pages answer their typed questions from the database; evaluation runs |
| 1 · Baseline | Compiled GLiNER2 schemas, spaCy, math and table readers, the local LLM tier | Adjudicates what the local LLM could not settle | F1 and intervention share measured per type and stage |
| 2 · Consolidation | Linking, claim fusion, pgmpy confidence, rule validation | Grey-zone identities and conflicts | Identity errors measured; confidence calibrated on goldens |
| 3 · Distillation | Escalation ladders across tiers, GLiNER2 LoRA adapters, gepa prompt tuning | Goldens for the errors metrics surface | Intervention share falls at equal or better F1 |
| 4 · Schema depth | Coverage-gap discovery, schema versions with migrations, statistics verifiers | Schema and guideline proposals | Coverage rises; new types reach target F1 |
| 5 · Second corpus | A corpus chosen for where statistics struggled; later hosted models and tenants | New domain packs | A new pack built with bounded interventions |

## Decisions taken (2026-10-28)

| Question | Decision | Effect |
|---|---|---|
| Model hosting | Hosted long term; near term Opus in Claude Code is the strong model and a local LLM runs on the RTX 5090 | Three-tier ladder, one shared prompt and evidence format, `awaiting_agent` tasks |
| Corpus | Statistics only until it stands up; a more NLP-natural corpus later, sooner if math density stalls progress | Phases 0–4 on Siegrist first-pass chapters |
| Golden verification | No per-item human verification; the operator steers through guidelines from an outer loop | Blind two-pass Opus authoring, versioned guidelines, re-scoring on change, independent witnesses ([D7](D7-evaluation-goldens-outer-loop.md)) |
| Opus cost | Opus from the Claude Code session; the constraint is output size during debugging | Bounded work packets, pagination, debug slices |
| Repository | New repository `corpus-structure`; the old one read-only | Port list in [D9](D9-repository-and-phase0.md) |

## Deliberately left out until a gap asks for it

PSL, AMIE rule mining, cvxpy family selection, causal discovery, MinHash source dependence,
retrieval fusion and reranking, sealed publication, exact replay of historical executors. Each
is a plausible later method; none enters until a measured gap names it and a golden-set
experiment shows it helps.
