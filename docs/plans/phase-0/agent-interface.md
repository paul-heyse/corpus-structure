# Phase 0: agent interface

**Status:** Proposed (2026-10-28). Part of the [phase 0 series](../phase-0_2026-10-28.md), which
owns shared decisions, contracts, the dependency graph and build findings.

This document builds D9 §5 step P0.7: the parse step that turns an authored batch and its citation
frame into the stored form on a rendition, M24's method definition and the packet it serves, the
prompts, the MCP server the Claude Code session works through, the golden server and its tools,
the session's working instructions, and the OPEN-D8-2 comparison. Its packages are P0-A-0 to
P0-A-3 (coordinator §7, rows A0–A3).

## 1. What this document builds

**Responsibilities.**

- **Parse (A0).** `methods.llm.parse`: a pure, schema-free function from a rendition, an authored
  model-facing batch and its citation frame to the stored batch on that rendition, with a report
  of how every citation resolved and every quote was located ([D4 §4.3](../../design/D4-method-catalog.md#43-output-form-and-post-processing),
  [D2 §7.3](../../design/D2-schema-and-guidelines.md#73-to-json-schema-for-llm-claim-proposals),
  [D1 §10.3](../../design/D1-knowledge-representation.md#103-stability-limits); ADR-0019). It is
  early because fixtures, consolidation and golden items all derive stored forms with it
  (coordinator decisions 2 and 6).
- **M24 and its packet (A1).** The `agent.opus` method definition (`select`, `input_digest`,
  configuration) and `methods.llm.packet`, the assembler, as a pure function of recorded inputs
  with caps in characters ([D4 §4.1](../../design/D4-method-catalog.md#41-the-packet),
  [D4 M24](../../design/D4-method-catalog.md#m24-agentopus), [D8 §3](../../design/D8-agent-and-query-interfaces.md#3-work-packets-and-size-caps);
  coordinator decision 5).
- **Prompts (A1).** `methods/llm/prompts/`: the extract instructions, the output format, the golden
  pass and adjudication instructions; the prompt parts and their hashes ([D4 §4.2](../../design/D4-method-catalog.md#42-the-prompt)).
- **The main MCP server (A1).** `intervene`: the queue tools, `read_instructions`, `propose_claims`
  with M19 at the batch call site and the one submission transaction, `release`, `record_direction`;
  `ci mcp serve`, `ci direct` and `.mcp.json` ([D8 §1–§3](../../design/D8-agent-and-query-interfaces.md); ADR-0015).
- **The submission harness (A1).** `intervene.testing`: drives `queue_next`, `read_unit` and
  `propose_claims` through the shared in-process `Client(mcp)` and maps an authored batch's sentence
  ids onto the served packet, for the deterministic acceptance test (coordinator decision 8) and
  evaluation's live-run answers, inside or outside pytest.
- **The golden server (A2).** The golden-only profile, its instance id as the session reference,
  the `golden.pass` method, `golden_next`, `read_golden_unit` and `write_golden`, which computes the
  unit's agreement and creates the pass-C task, and the page-text variant evaluation uses for
  OPEN-D7-5 ([D8 §2.2](../../design/D8-agent-and-query-interfaces.md#22-goldens-d7-3),
  [D7 §3.2–§3.4](../../design/D7-evaluation-goldens-outer-loop.md#32-pass-a-and-pass-b-blind); ADR-0011).
- **Working instructions (A2).** `.claude/skills/work-queue/SKILL.md` and the golden agent file
  `.claude/agents/golden-pass.md`, and the probe that observes golden-server separation (review
  Observation 9).
- **The OPEN-D8-2 comparison (A3).** Whether grouping units in one `queue_next` lowers quality, on
  `core12`, scored against the dev goldens ([D8 §7](../../design/D8-agent-and-query-interfaces.md#7-open-questions)).

**Where they end.** This document does not route units (policies, P0-O-2), own task state, leases
or twin settlement (P0-O-1's completion primitive, which A1 and A2 call), validate batches (the
conformance, reference and type checks, the batch→candidate adapter and M19 are `validate`'s,
P0-S-2), choose standing-context sentences (P0-I-2a), generate or resolve locators (P0-I-0), write
knowledge rows (consolidation), derive golden items or score anything (evaluation, which calls
A0), or create golden sets, golden runs and pass A/B tasks (P0-E-1). The main server never imports
the math grammar; the golden server reaches it only through one spawned worker process (§3.7).

**Change scenarios** (DESIGN §1.3 and the phase 1 additions):

| Change | Where it is expressed | What it reuses | What stays unaffected |
|---|---|---|---|
| The local tier (M10, phase 1) | M10's method and a token counter in the assembler (`encode_batch_fast` over the served model's `tokenizer.json`, D4 §4.1) | The packet layout, the prompt parts, A0, `validate`'s batch checks | The MCP server; M24 |
| Adjudication (phase 1) | M24's `adjudicate` configuration, the judge packet's Alternatives section, the `adjudicate` tool | Leasing, the completion primitive, the packet assembler | `propose_claims`, A0 |
| A hosted model replaces the session (ADR-0015 revisit) | An M10/M16 configuration against a hosted endpoint, called by the pipeline | Packets, prompts, A0 | The queue tools remain for the session's work |
| A second domain pack | The pack's guideline (its `<!-- core -->` sections), schema, compiled reference and worked examples | Everything here: packets, prompts and parse name no predicate | — |
| An email thread's segment kinds | The packet header names the segment kind; locators carry kinds (D1 §3.4) | The cascade, which is text-based | — |
| Another golden author model | `golden.pass`'s declared `model` and the agent file's `model:` (an ADR-0011 revisit) | The golden tools | — |

## 2. Contracts

### 2.1 Consumed

| Contract | Owner (design; this series) | Used by |
|---|---|---|
| Canonical JSON, content digest, segment keys, `core/tex.py` tokenizer and drop list | D1 §10.1, coordinator decision 13; [foundations](foundations.md) P0-F-2a | A0 (token step, stored anchors), A1 (packet hash, digests) |
| D1 value, condition and binding shapes; batch items in both forms; the citation-frame model; the generic stored-item models | D1 §5–§7, D2 §7.3; foundations P0-F-2b | A0, A1, A2 |
| Locator generator and resolver with refusal, over a rendition's segments, including `sentence` segments | D1 §3.4; [ingest and math](ingest-and-math.md) P0-I-0 | A0 (frame resolution), A1/A2 (frames for served packets) |
| Rendition content (canonical text, segment tree with kinds, attributes and statement-kind hints, sentences), title and section path, the per-rendition macro table, `author_markup` observations | D1 §3, D4 M01–M03, D3 §6.2; ingest and math P0-I-1a (functions), P0-I-1b (rows) | A0, A1 |
| The standing-context function (unit → at most six `cN` sentences from the rendition's recorded `scope` observations) and the M13 version | D4 §4.1, M13; ingest and math P0-I-2a | A1, A2 |
| Method-contract types (`Method`, `UnitView`, `RunView`, `Digest(bytes, packet_hash)`, …) and the registry interface | D4 §1 as amended for the packet hash; [orchestration](orchestration.md) P0-O-0 | A1 (M24), A2 (`golden.pass`) |
| Compiled artifacts per schema version, resolved from a method config's (compiler, kind) references: the model-facing JSON Schema, the annotator reference, the rule set, with hashes | D2 §7, §7.5, D3 §3; [schema and rules](schema-and-rules.md) P0-S-1, P0-S-1b | A1 (prompt parts, digest), A2 |
| Batch conformance, reference and type checks with item paths; the batch→candidate adapter; M19 at `at: batch` with the `guideline:` group, reading symbols with `core/tex.py` | D2 §7.4, D5 §8.2, D4 §4.3 steps 1 and 3 as amended; coordinator decision 3; schema and rules P0-S-2 | A1 (`propose_claims`), A2 (`write_golden`) |
| Repository writes on the caller's connection: `claim_proposal` observations (`batch`, `authored`, `citation_frame`, `rejected`, `rationale`), `ops.intervention`, `eval.golden_pass`, golden-unit status and agreement | D1 §10.2, D3 §5 (Writers), §6–§7; foundations P0-F-4 | A1, A2 |
| Runs with `reference_run_id`; task creation calling `select` and `input_digest` and recording `packet_hash`; agent leases (30 minutes, renewed by any call, `attempt` fencing, release), leasing restricted to a candidate set; the agent completion primitive in the caller's transaction (fenced completion, the held-open outcome that keeps the first rejection in `ops.task.error`, twin settlement, `NOTIFY cs_agent_task_done`) | D6 §3–§4, D3 §4, §8; coordinator decisions 4, 15, 16; orchestration P0-O-1 | A1, A2 |
| Golden sets and units (unit key, authored rendition, split); the golden run (kind `golden`, `parent_run_id` naming the run whose renditions and M13 output its packets read) and its pass A and B tasks | D7 §3.1, D3 §7, §8; [evaluation and goldens](evaluation-and-goldens.md) P0-E-1 | A2 |
| Alignment of two claim sets: agreement by tier and predicate, and the diff (matched with differing fields, A-only, B-only, entities) | D7 §3.3–§3.4, §5; evaluation and goldens P0-E-2a | A2 (agreement, the pass-C packet), A3 |
| Adjudicated dev goldens for `core12` | D7 §3; evaluation and goldens P0-E-3 | A3 |
| Fixture proposals (`fixtures/s0`: authored batches with citation frames) | coordinator decision 6; foundations P0-F-3 | A1 and A2 tests |
| Settings, the `ci` Typer app, the shared conftest and database fixtures | D9 §3, §4; foundations P0-F-1 | A1, A2 |

### 2.2 Produced

| Contract | Design owner | What this document implements | Consumers |
|---|---|---|---|
| Parse: (rendition, authored batch, frame) → stored batch + citation report | D4 §4.3, D2 §7.3, D1 §10.3, D5 §5.6; ADR-0019 | `methods.llm.parse` (A0) | foundations P0-F-3 (fixture acceptance), consolidation P0-C-1 (fixture and reused proposals), evaluation P0-E-1/E-2b (golden items, D3 §7), A1, A2 |
| M24 `agent.opus` | D4 M24, §1; D2 §12.1 | the method, its configuration model and digest, registered with the registry (A1) | orchestration P0-O-1/O-2 (task creation, reuse, policies) |
| The packet, agent and golden modes, caps in characters | D4 §4.1, D8 §3 | `methods.llm.packet` (A1) | M24's digest, `read_unit`, `read_golden_unit`; M10 in phase 1 |
| Prompt parts with hashes | D4 §4.2, D2 §10 | `methods/llm/prompts/` and the part assembly (A1) | M24's and `golden.pass`'s digests; `read_instructions`, `read_golden_unit` |
| The main MCP server | D8 §1–§3; ADR-0015 | `intervene` main profile, `ci mcp serve`, `ci direct`, `.mcp.json`, the in-process `Client(mcp)` fixture (A1) | the session; orchestration's agent barrier (`NOTIFY`) |
| The submission harness | D8 §2.1 (the sentence map), D9 §4 (acceptance); coordinator decision 8 | `intervene.testing` (A1) | consolidation P0-C-3 (the acceptance test), evaluation P0-E-2b (live-run answers through the same path) |
| The golden server, `golden.pass`, agreement and pass-C creation | D8 §2.2, D7 §3.2–§3.4, D3 §8; ADR-0011 | `intervene` golden profile and its page-text variant (A2) | evaluation P0-E-3 (dev golden authoring, the OPEN-D7-5 comparison) and its item derivation |
| Working instructions | D8 §3, D9 §1; ADR-0011 | the work-queue skill, `.claude/agents/golden-pass.md` (A2) | the session, golden subagents |
| OPEN-D8-2 evidence | D8 §7 | the comparison and its evidence record (A3) | the design owner (D8 §3's `queue_next` bound) |

## 3. Design of the parts

Everything in this section is **Proposed** (2026-10-28) unless a statement carries another label;
labelled statements give their evidence.

### 3.1 Parse (A0)

**Inputs and output.** A rendition view (canonical text, segments with keys and kinds, sentences,
macro table), the authored batch (P0-F-2b's model-facing items, generic: no compiled schema) and
its citation frame (each `sN`/`cN` → the sentence's locator and text). The output is the stored
batch (P0-F-2b's generic stored items, which P0-S-1's stored-form adapter validates) and a report.
The function reads no database, clock or randomness that reaches its output; per-quote timings are
report-only diagnostics.

**Frame resolution first.** Each frame entry is resolved with P0-I-0's resolver on the rendition and
checked against its recorded text (D1 §10.3). Outcomes: `resolved`; `relocated`, when the locator is
refused or selects a sentence with other text but exactly one sentence of the rendition carries the
recorded text (the D7 §3.5 rule, applied to every authored batch; the new locator is reported so a
consumer can rewrite its frame); `unresolved` otherwise. The batch's `unit_ref` resolves the same way
to the unit segment. A consumer decides what `unresolved` means: evaluation marks the golden unit
stale (D7 §3.5); consolidation falls back as D5 §5.6 states; submission cannot meet it, because the
frame was generated on the same rendition. The case it exists for: a reused proposal whose packet
text is unchanged while an edit elsewhere on the page lengthened a sentence locator's prefix (D1
§10.3), so packet hash and reuse hold but the old locator is ambiguous. *Proposed.*

**The cascade** follows D4 §4.3's order (*Tested* in the spike instruments for the exact and
spacing steps on 735 real S0 quotes, record `s0.stored`; the token step *Measured on synthetic
perturbations only*, text-math note L-10, record `parse.regex-probe`):

1. exact in the cited sentence;
2. exact in the frame's other sentences (the unit's sentences and the standing context), nearest the
   cited sentence first, so a `cN` quote is found where the spike's unit-only fallback could not
   (D4 §4.3 as amended);
3. exact up to spacing: the quote's non-space characters joined by optional whitespace, spacing
   commands and math delimiters, a math delimiter in the quote matching optionally, matched in the
   original text, so no offset map exists (`regex`, with `timeout`);
4. the same with the rendition's zero-argument macros matching either spelling (`\R` or
   `\mathbb{R}`), the pack's fallback macro map beneath the page's table;
5. the token-sequence step: quote and cited sentence tokenized with `core/tex.py`'s tokenizer
   (control word, control symbol, word, other non-space character), each distinct token mapped to
   one private-use character; `rapidfuzz.fuzz.partial_ratio_alignment(score_cutoff=80)` picks the
   window, widened by three tokens, and `rapidfuzz.distance.Levenshtein.opcodes` aligns the quote
   inside it; the span runs from the token aligned to the quote's first token to the one aligned to
   its last, mapped back to character offsets;
6. the character step when 5 finds nothing or scores below its cutoff: `partial_ratio_alignment`
   (cutoff 85, trailing `.,;:` stripped) for the window, refined by `regex` `BESTMATCH` with an error
   bound of a share of the quote's length and a `timeout`; `fuzzy_counts` recorded;
7. when the cited sentence yields nothing, `rapidfuzz.process.extractOne(quote, frame sentences,
   scorer=fuzz.partial_ratio, score_cutoff=…)` picks a sentence, and steps 5–6 run there.

Every span is snapped outward to word boundaries; several equal matches are recorded as ambiguity
(`matches > 1`), and a fuzzy score is never treated as identity. A regex `TimeoutError` is a recorded
step outcome and the cascade continues. Using the same tokenizer as the token form keeps one
definition of a TeX token (coordinator decision 13).

**Unlocated quotes** get the cited sentence's span with `coarse: true`; an item without a valid cited
sentence is dropped and counted (D2 §7.3's `coarse?`, D5 §5.6; D4 §4.3 as amended). Phrase leaves
(`{"t": "phrase", "text", "sentence"?}` and condition `phrase` nodes) are located the same way, from
their cited sentence or, without one, over the frame's sentences, and stored with `start`, `end`,
`text` and optional `coarse`.

**Conversion.** Statement anchors `"unit"` → the unit segment's key, sentence ids → sentence segment
keys; a local entity's `extent` and a `scope` qualifier resolve to `scope_segment`: `statement` → the
smallest segment enclosing the binding statement's anchors, `section` → the smallest section
containing the entity's earliest evidence, `document` → the document segment. The binding statement
of a local entity is the earliest statement among the claims that mention it (subject, object,
entity-valued qualifiers, `variable`/`family_param` bindings, `pred` arguments), as the spike does.
An extent that cannot be resolved is reported and the field left out, never guessed.

**The report** lists per citation the frame outcome, and per located item its path
(`claims[3].evidence[0]`), quote, cited sentence, step, matches, scores, fuzzy counts, timeouts and
coarse or dropped. Submission turns it into the result's unlocated quotes; consolidation counts
coarse and dropped items; evaluation reads frame outcomes.

### 3.2 M24 and its digest (A1)

`agent.opus` (family `agent`, tier `agent`, unit type `segment` for an annotation unit, version
bumped on any change to its packet rendering or prompts) implements the D4 §1 contract through
P0-O-0's types.

- **Configuration** (`agent.opus/extract` in D2 §12.1): `mode`, `examples: reference`,
  `hints: none`, `packet_cap_chars`, a declared `model` (default `claude-opus-5-5`; the server
  cannot observe the session's model, so the value is a declaration, recorded with every
  intervention), `max_units` (1 until A3 decides), and artifact references by (compiler, kind) for
  the annotator reference, the model-facing JSON Schema and the rule set, which the registry resolves
  against the run's schema version. Defaults live with the method; `methods.yaml` overrides.
- **`select`** returns the annotation units (`unit` segments and paragraphs outside units) of the
  run's renditions; the phase 0 policy narrows them to claim-bearing units of the run's scope (D6
  §7.5).
- **`input_digest`** assembles the packet (§3.3) once per unit view, caches it, and returns
  `Digest(bytes, packet_hash)`: the digest is the hash of the canonical JSON of the packet hash, the
  prompt-part hashes (§3.4), the artifact hashes and the declared model; orchestration adds method
  name, version and configuration hash (D6 §4) and records `packet_hash` on the task (D4 §1 as
  amended). Task ids never enter it, so re-running M13 with identical output leaves M24 tasks reused,
  while a guideline, schema, rule, prompt or packet change requests new proposals (D4 §1 rule 4,
  coordinator decision 15). *Proposed.*

### 3.3 The packet assembler (A1)

**Recorded inputs only** (D4 §4.1, coordinator decisions 5 and 16). For a task: the run's rendition
of the unit's page (`kb.run_rendition`), the unit segment, its sentences and inner headings, the
document title and section path, the statement-kind hint, the standing context from P0-I-2a's
function over the rendition's `scope` observations read through `kb.run_observation` for the run,
and the known entities. Nothing read at serving time enters: no queue order, no promoted pointer, no
proposal of the same run.

**Known entities.** With a non-null `reference_run_id`: the reference run's global entities that have
a claim whose evidence lies on the reference run's rendition of the same page, ordered by key, at
most 30, each as its class, canonical label and aliases. With a null reference run (the bootstrap):
the page title and the `dfn` terms from the rendition's `author_markup` observations, as terms
without a class. The read is a small query over D3 tables in `methods.llm.packet`, so A1 does not
depend on consolidation's queries. No phase 0 run has a reference run, because nothing is promoted
before the gate, so live phase 0 packets always carry the bootstrap list; the reference-run path is
exercised by tests with a synthetic reference run. Golden-mode packets have no known entities
(D7 §3.2).

**Rendering.** D4 §4.1's sections and header, which are the S0-R2 v1 inputs' rendering (*Measured*,
records `s0r2.inputs`, `s0r2.scores`): a header line with the unit key (`unit_ref`), document title, section
path and the source's statement-kind hint; `## Standing context` with its one-line explanation and
`[cN]` lines or `(none)`; `## Known entities` (agent mode only); `## Text` with `[sN]` lines and inner
headings as `--- heading ---` lines that carry no id and cannot be cited. Hints and Alternatives are
absent in phase 0 (hints off for proposals, no judge packets). The worked examples in the pack's
`reference/E*` are packets in this rendering, so the golden-mode assembler must reproduce them byte
for byte on the reserved page's rendition; a divergence is corrected in the data, never by a special
case in the assembler.

**Parts and the cap.** `packet_cap_chars` (18,000 for `extract`) is the one cap authority (D8 §3,
D2 §12.1). A unit whose packet exceeds it is split at sentence boundaries into parts; every part
repeats the header (with "part i of n"), the standing context and the known entities; sentence ids
run through the parts (`s1` … `sN`), so a task has one batch and one frame. A single sentence longer
than the room left in a part is its own part and is served whole and flagged, because cutting it
would make its quotes unlocatable; the unit sizes measured so far make this a guard, not a path
(record `s0.sizes`). If header, standing context and known entities alone exceed the cap, the
assembler raises and the task creation fails for that unit with that reason.

**The sentence map** is produced with the packet: each `sN` and `cN` mapped to the sentence's
locator (generated by P0-I-0 on that rendition) and text. `read_unit` and `read_golden_unit` return
it as structured content beside the packet text (D8 §2.1 as amended), and the citation frame is
built from it: the frame of a submission is the map's entries for the ids the batch cites. The
author never writes a frame; `propose_claims` and `write_golden` attach the one built from the map
of the packet they served.

**The hash** is SHA-256 over the canonical JSON of the list of part texts. It identifies exactly what
the session reads.

**Serving re-assembles.** D3 stores only `packet_hash`, so `read_unit` assembles the packet again in
the server and compares the hash with the task's; the inputs are immutable rows (renditions,
observations kept while referenced, and the reference run's materialized rows, which D3 §8 never
deletes while a kept run references it). A mismatch is an infrastructure error naming the task; it
signals a changed input, never a reason to serve the new text. Storing packet text instead would add
a column and a second copy of what the inputs already determine.

### 3.4 Prompt parts (A1)

| Part | Source | Served to |
|---|---|---|
| `system` | `methods/llm/prompts/extract.md` (how to read a packet, cite `sN`/`cN` with exact quotes, use local refs, set `unit_ref` to the unit key, keep rationales to two sentences, fix or explain warnings) | `read_instructions` |
| `guideline` | the run's guideline version, the §10 sections tagged `<!-- core -->` (D2 §10) | `read_instructions` |
| `reference` | the compiled annotator reference with its worked examples (D2 §7.5; phase 0 `examples: reference`) | `read_instructions`, `read_golden_unit` |
| `format` | `methods/llm/prompts/format.md`: the D2 §7.3 outline and the notes that are part of the format | `read_instructions`, `read_golden_unit` |
| `schema` | the compiled model-facing JSON Schema; optional reading, since the reference states every exact shape | `read_instructions`, `read_golden_unit` |
| `golden` | `methods/llm/prompts/golden.md` (passes A and B) or `golden_c.md` (pass C), and the full guideline (D7 §3.2) | `read_golden_unit` |

Each part has a hash: of its text, or the compiled artifact's hash. They are identical for all tasks
of a run and mode, so the session reads them once per run. Each part is served on its own and
paginated at 24,000 characters (about 8,000 tokens at D8 §3's conservative three characters per
token), below Claude Code's 10,000-token warning and its 50,000-character file threshold (interfaces
note IE-3; D8 §3 as amended). The reference alone is about 35,600 characters in S0-R2's inputs, and the schema
tens of kilobytes, which is why no part is served whole. S4's `s4.sizes` gives the production sizes.

### 3.5 The main server (A1)

**Process and identity.** `ci mcp serve` starts a FastMCP 4.1.3 stdio server registered in
`.mcp.json`; one process per Claude Code session, separate from the orchestrator (D6 §1, coordinator
decision 4). The lifespan (`fastmcp.server.lifespan.lifespan`, read through `ctx.lifespan_context`)
builds settings once, opens P0-F-4's pool (one per process, small), mints the instance id and holds
the in-memory record of what this instance served. Tools are synchronous and run on worker threads,
calling the same application functions as the CLI (*Tested*, interfaces note P1). Nothing is printed
at import or lifespan time; logging goes to stderr; `mcp.run(show_banner=False)` (*Tested*, P2). The
main profile registers no golden tools, so the Opus session cannot write a golden pass, and imports
nothing that imports the math grammar.

**Tools** (D8 §2.1, §2.3):

- `queue_status(run?)`: counts of `awaiting_agent` M24 tasks by mode and stage, and the budget left
  (D6 §7.4).
- `queue_next(mode?, run?, max_units?)`: leases up to `min(max_units, config max_units)` tasks of one
  page through P0-O-1, `claimed_by` the instance id; returns task ids, unit keys and packet sizes
  (parts, characters). Without `run`, the newest run with awaiting M24 tasks; a named slice run
  serves only its tasks.
- `read_unit(task_id, part?)`: one part as `ToolResult(content=<packet text>,
  structured_content={task_id, part, parts, hash, sentences})`, where `sentences` is the part's
  sentence map (§3.3), so the model reads text, not escaped JSON (*Tested*, P1), while a program
  reads the map; renews the lease.
- `read_instructions(task_id, part?, page?)`: the part list with sizes and hashes, then a part's
  pages; renews the lease.
- `propose_claims(task_id, batch, schema_hash?, rationale?)`: §3.6.
- `release(task_id, reason)`: returns the task to `awaiting_agent` through P0-O-1.
- `record_direction(text, scope?)`: an `ops.intervention` of kind `direction` and an entry appended to
  `domains/<name>/directions.md`, outside the guideline's hash (D2 §10.11, D7 §8.2); `ci direct "TEXT"
  [--scope S]` calls the same function.

`ci ack`, `ci veto`, D8 §2.3's proposal tools, D8 §2.4's inspection tools and `adjudicate` wait for
phase 1: under the phase 0 freeze nothing is pending to acknowledge, and Opus inspects through
read-only `ci query` and `ci explain` (D8 §4).

**Errors.** `isError` is reserved for envelope and infrastructure failures: an unknown task, a lease
not held by this instance, a stale `schema_hash`, a packet hash mismatch, a database failure. Every
content problem is a successful call with a typed result (*Tested*, interfaces note §1.1, IE-1). Tool
descriptions stay under 4,096 characters and say where the schema comes from; server instructions
point to the work-queue skill. FastMCP's response-limiting middleware is registered only as a byte
backstop well above the bounds.

### 3.6 Submission (A1)

`batch` is a plain object parameter; the body validates item by item, because a strict model
parameter fails the whole call before the body runs and bypasses the resubmission rule (*Tested*,
interfaces note §1.1). The pipeline, outside any transaction:

1. **Envelope.** The lease is held by this instance and this instance served every part of the task's
   packet (the frame attached is the one served); `schema_hash`, when given, equals the run's;
   `unit_ref` equals the task's unit key (else an error at path `unit_ref`).
2. **Conformance, references and types** through P0-S-2 against the run's schema version: rejected
   items with D8-style paths (`claims[3].qualifiers.param_values.mean: …`).
3. **Parse** (A0) on the task's rendition with the served frame: the stored form of the accepted
   items, and the unlocated quotes.
4. **M19 at the batch call site** through P0-S-2's adapter and runner: `guideline:` warnings and rule
   errors per item. Symbols are read with `core/tex.py`, and grammar-dependent rules are
   `at: [finalize]`, so the call never parses a formula with the grammar (coordinator decision 3,
   P0CL-14).

**Outcomes.** A first submission with any error, unlocated quote or warning is held open: P0-O-1's
primitive records the result in `ops.task.error`, keeps the task `awaiting_agent` and renews the
lease, and the result says `task_open: true`. Warnings count because D2 §7.4 asks the author to fix
the batch or say why the rule does not apply; a batch kept on purpose is resubmitted with a
`rationale` saying why. A second submission, or a clean first one, completes the task: `done` with a
`claim_proposal` observation whose stored `batch` holds the accepted items (unlocated quotes as coarse
spans), `authored` and `citation_frame` the submission as served, and `rejected` the rest; `empty`
with no observation when a clean batch has no items (D4 §1 rule 2). An all-rejected second submission
is still `done`, so the malformed-output rate counts it and no later run asks for the packet again.
The unlocated-quote reading (D7 §7) therefore counts the stored batches, after the one correction.

**The transaction.** One transaction on one pooled connection: P0-O-1's completion primitive first
(fenced on `attempt`; it settles every `awaiting_agent` twin with the same method configuration and
input hash as `reused` and sends `NOTIFY cs_agent_task_done`, delivered at commit), then P0-F-4's
writes of the observation and of an `ops.intervention` (kind `extract`, actor from the declared model,
`session_ref` the instance id, `refs` the observation). If the fenced completion finds the lease
lost, or the task already `reused` from a twin, nothing is written and the result says so. A failure
after the fence rolls everything back; the task stays leased and the session may resubmit.

**Failure bound for a pathological formula** (P0CL-14). The main server imports no grammar and calls
nothing whose runtime depends on formula structure beyond the total TeX tokenizer and the cascade's
regex steps, each under a `timeout`; the grammar API itself raises when called off a process's main
thread (ingest and math). FastMCP's per-tool `timeout` cannot stop a running synchronous thread
(FastMCP overview §2.1), so the bound has to come from what the tool calls, not from a timeout around
it.

**The submission harness** (`intervene.testing`). The deterministic acceptance test (consolidation
P0-C-3, coordinator decision 8) and evaluation's live-run answers (P0-E-2b, which submit the trace
and core units' pass-C batches as the proposals of a golden-expectation run, possibly outside pytest)
both submit authored batches as the session would. The harness takes a run id and authored batches
with their citation frames keyed by unit key, and for each one drives `queue_next`, every part of
`read_unit` and `propose_claims` through one in-process `Client(mcp)`. It maps the batch's sentence
ids onto the served packet with the sentence map: each frame entry is matched to the served entry
with the same locator, else the one with the same recorded text; an entry with no match, or with
several, stops the harness with an error naming the unit and the id, because the fixture does not
fit the packet. The ids are then rewritten at every position that cites a sentence (evidence,
statement anchors, phrase leaves, `unsupported`), walking the F2b model-facing models. It returns the
submission results and leaves resubmission to its caller, which for fixtures means a held-open result
is a failure to report. It is a product module, not test code, because evaluation calls it outside
pytest; an async core with a synchronous wrapper (`anyio.run`) serves both. The served frame, not the
fixture's, is what the stored proposal records, so the proposal means what the session would have
submitted.

### 3.7 The golden server and `golden.pass` (A2)

**Profile and identity.** `ci mcp serve --profile golden --declared-model <model>` registers only
`golden_next`, `read_golden_unit` and `write_golden`, and refuses to start without a declared model.
The golden agent file declares this server inline, so each subagent invocation starts its own process
and the lifespan's instance id is the session reference recorded on every lease and pass (D8 §2.2;
*Interface-checked*: the one-process-per-invocation behaviour is documented by Claude Code and not
yet observed, interfaces note §1.7). The probe in A2 observes it.

**`golden.pass`** (family `eval`, tier `agent`, unit type `golden_unit`; configurations
`golden.pass/a`, `/b`, `/c` with a declared `model`, default `claude-sonnet-5-5`, and
`packet_cap_chars`). P0-E-1 creates the A and B tasks through P0-O-1 when it creates the golden run;
`write_golden` creates C. Its `input_digest` returns `Digest` over the golden packet hash, the
prompt-part hashes (`golden`, the full guideline, `reference`, `format`), the declared model and the
golden set label with the unit key, with the golden packet hash as `packet_hash`. The set and unit
are in the digest because a pass row belongs to one golden unit: reuse may only re-find that unit's
own pass, for example when a golden run is recreated, never another set's.

**Golden packets** are the golden-mode packets of §3.3, read from the golden run's `parent_run_id`:
its rendition of the page (which P0-E-1 records as the unit's authored rendition) and its M13
observations.

**`golden_next(set, pass)`** computes the candidate tasks of the set's golden run for that pass,
leaving out units whose earlier passes carry this instance id (pass B: A's; pass C: A's or B's), and
leases one through P0-O-1's candidate-set lease.

**`read_golden_unit(unit, pass, part?, page?)`** serves parts paginated at 24,000 characters:
`instructions` (the pass's instructions, the full guideline, the reference and the format, with
hashes; identical across a set's units, read once per subagent), `packet` (the golden-mode packet,
by packet part, with its sentence map as structured content), and for pass C `passes` (the authored batches of A and B and the diff, rendered as
S0-R2's adjudication inputs did: matched claims with the fields that differ, claims only in A or in
B, entities and unsupported counts). Test-set goldens are served only here, so the session never sees
them (D7 §4).

**`write_golden(unit, pass, batch, decisions?)`**:

1. The envelope as §3.6, plus: the instance served this unit's `instructions` and `packet` under the
   lease (they are the inputs it records); pass B is refused when pass A of the unit carries this
   instance id, pass C when A or B does; pass C requires `decisions` (keep A, keep B, keep both, drop
   both, rewrite, each with a reason and `guideline_gap` marks, D7 §3.4).
2. Conformance and type checks, parse on the unit's authored rendition, and M19's `guideline:`
   warnings, as §3.6. A first write with errors, unlocated quotes or warnings is held open once
   (D7 §3.2).
3. One transaction: lock the `eval.golden_unit` row (`SELECT … FOR UPDATE`), so two subagents writing
   A and B of one unit at the same moment serialize; insert `eval.golden_pass` (authored batch,
   frame, `decisions`, `session_ref`, `model`, `inputs`: guideline version, reference hash, packet
   hash, M13 version, and for C the A and B pass ids); write an intervention (`golden_write` or
   `golden_adjudicate`); call the completion primitive. When this is the second of A and B, compute
   the agreement (below), store it on the unit as the alignment returned it, and create the pass-C
   task through P0-O-1 in the same transaction. Pass C sets the unit `adjudicated`. Golden items are
   not written here; evaluation derives them with A0 before it aligns a run (D3 §7).

**Agreement in a spawned worker.** E2a's value equivalence uses the math grammar and SymPy, whose
timeout needs a main thread, so the golden server runs E2a in one `concurrent.futures.ProcessPoolExecutor(max_workers=1,
mp_context=multiprocessing.get_context("spawn"))` started in the lifespan; the worker module imports
`evaluate`'s alignment and the grammar, the server's own modules never do. Both passes' stored forms
(A0 on the authored rendition) are sent to the worker; the call waits with a wall-clock bound held
under the row lock. On timeout or a worker crash the pool is replaced, the transaction rolls back
and the call fails as an infrastructure error, so the subagent retries and nothing half-written
remains. Storing the diff with the agreement means pass C reads exactly what the agreement measured
and `read_golden_unit` needs no worker. *Proposed.*

**The page-text variant for OPEN-D7-5.** Evaluation's OPEN-D7-5 comparison (whether the page's full
text still helps golden passes, D7 §10) runs through `--profile golden --variant page-text`. The
variant adds a `page` part (the authored rendition's canonical text, paginated at 24,000 characters)
to `read_golden_unit`, serves the set's units without leasing tasks, and makes `write_golden` a check:
it validates, parses and returns the result as usual but stores no pass, completes no task and creates
nothing. The subagent writes its batches to the evidence folder its instructions name, and evaluation
scores them there, so the comparison's results never become goldens.

### 3.8 Working instructions (A2)

**`.claude/skills/work-queue/SKILL.md`** (tracked through a `!/.claude/skills/work-queue/` line in
`.gitignore`, and listed with the tracked skills in AGENTS.md): read `read_instructions` once per run
and mode; loop `queue_next` → every part of `read_unit` → one batch → `propose_claims`, fixing what
the result names once or explaining in `rationale`; `release` what cannot be finished; keep rationales
to two sentences; never ask for or read test golden items or test errors; read-only `ci status`,
`ci query` and `ci explain` for inspection; dispatch golden passes to fresh golden-pass subagents,
one subagent per pass over a batch of units, A and B always separate subagents and C a third (ADR-0011,
D8 §3); audit each subagent from its transcript's tool calls rather than its report (OPEN-D8-3's
practice).

**`.claude/agents/golden-pass.md`**: `model: sonnet`; an inline `mcpServers` entry running
`ci mcp serve --profile golden --declared-model claude-sonnet-5-5`; tools narrowed so the main
server's tools are hidden (`disallowedTools: mcp__corpus-structure__*`) and no file outside its task
is read; the instructions part of `read_golden_unit` carries the pass's task (interfaces note IE-2).
Inline servers from `.claude/agents/` load only once the folder is trusted.

**The separation probe** (review Observation 9) runs in a Claude Code session: two golden-pass
subagents in parallel and two in sequence each lease from a probe golden set and record their
instance id and process id; the probe passes when every invocation shows its own id, none equals the
main server's, and the main server's tools are not visible to them. Its folder is
`docs/design_review/evidence/<date>_golden-server-separation/` with a README and a record (ADR-0010);
until it passes, pass separation rests on the documented behaviour plus the transcript audit.

### 3.9 The OPEN-D8-2 comparison (A3)

Two arms over the `core12` slice, each a slice run with `agent_mode: complete`: `agent.opus/extract`
(`max_units: 1`) and `agent.opus/extract-grouped` (`max_units: 5`, units of one page whose packets
together fit one cap, D8 §3). The arms differ by configuration, so their input hashes differ and the
second arm cannot reuse the first's tasks. Each arm is worked in a fresh context (a new session or an
Opus subagent per arm) so neither carries the other's packets. Both arms' proposals are derived on
the run's renditions with A0 and aligned with E2a against `core12`'s pass-C batches; the readings
are full- and core-tier F1 per arm, the unlocated-quote and warning rates, and the per-unit
differences. The decision rule is written in the evidence README before the runs; with thirteen
annotation units only a large loss is detectable, so "no loss detected" makes grouping an operator
choice, not a result. `max_units` stays 1 until the operator decides; D8 §7 is then updated by the
design owner. The record lives in `docs/design_review/evidence/<date>_open-d8-2-grouping/`.

## 4. Ports

| Spike module (`docs/design_review/evidence/2026-10-28_design-spikes/code/`) | Product module | Behaviour and tests kept | Not ported |
|---|---|---|---|
| `s0_locate.py` (`locate_quote`, `spacing_pattern`, `snap`, `to_stored`, `LocateReport`) | `methods/llm/parse.py` | Steps 1–4 (the spacing pattern's joiner, optional delimiters, nargs-0 macros with the fallback map beneath), word snapping, ambiguity counts, stored conversion of anchors, scope qualifiers, extents, phrase leaves and unsupported items, coarse and dropped outcomes; `tests_instruments/test_locate.py` (planted cases, T2/T3 extents, unresolvable extents reported, coarse and dropped, phrase leaves), `test_locate_real.py` with `real_text_cases.py` (corpus-gated, on production renditions), `test_locate_cascade.py`'s kinds and its probe reproduction (expectations updated to the token step) | The character-level fuzzy step as primary and the `fuzzy_window` fallback; `_search_all` swallowing `TimeoutError`; the unit-only fallback ranges; `reanchor`'s manual loop (frames make stored-to-stored re-anchoring unnecessary); dict walking over untyped JSON; the CLI and `context_from_json`; the speed-dependent refine-timeout test |
| `s0r2_inputs.py`: `packet()`, `FORMAT_V1`, `INSTRUCTIONS` | `methods/llm/packet.py`; `prompts/format.md`; `prompts/golden.md` | The v1 rendering (header, standing-context note, `[cN]`/`[sN]` lines, inner headings); the format notes; the annotator's instructions recast for tools | The spike unit labels (`U5`) in the header; reading from result folders; file-path instructions; `reference()` and `card()`, which schema and rules ports |
| `s0r2_adjudication_inputs.py`: `INSTRUCTIONS`, `diff()` | `prompts/golden_c.md`; the pass-C diff rendering in `intervene` | The decision vocabulary and the diff's sections | Parsing the instrument's text output with `eval`; E2a returns a typed result |
| `s0r2_sample.py` | — (`context_for` is ingest and math's) | Its output `results/s0r2/sample.json` and `results/s0r2/inputs/packet_v1/units/*.md` are A1's expected packets | — |

## 5. Packages

| Package | Scope | Prerequisites | Acceptance | Revealing failure case |
|---|---|---|---|---|
| P0-A-0 | Parse: frame resolution with re-location, the cascade, stored conversion, the report | P0-F-2b, P0-I-0, P0-I-1a | Re-deriving the S0 batch sets on the production renditions reproduces the spike's stored offsets and step counts (`s0.stored`: 733 exact, 2 at spacing), and the S0-R2 sets their stored forms, with anchors equal by locator; the perturbation set reaches the L-10 figures (at least 523 found and 428 exact, at least 514 at IoU ≥ 0.9, no mid-word cut); on a rendition with an edit elsewhere on the page the spans are the same text at shifted offsets; a frame whose sentence text changed is `unresolved`, one whose locator lengthened is `relocated` | A dropped-word quote longer than 64 characters: a character-level window comes back one token short, the token step must return the whole span; a `c1` quote whose text also occurs in the unit must land in the context sentence |
| P0-A-1 | M24, the packet assembler with its sentence map, prompt parts, the main server and its tools, submission, the submission harness (`intervene.testing`), `record_direction`, `ci mcp serve`, `ci direct`, `.mcp.json`, the `Client(mcp)` fixture | P0-O-1 (with P0-O-0), P0-S-1, P0-S-1b, P0-S-2, P0-I-1a, P0-I-2a, P0-A-0; P0-I-2b for the M13-rerun reuse test | D9 P0.7's: a v1 reference batch completes a task, errors and warnings come back per item; golden-mode packets reproduce `packet_v1/units/*.md` (unit key in the header) and the pack's `reference/E*` exactly; P0CL-05's packet half (identical packet hashes whatever order the queue is worked in, and after a promotion during the run); P0CL-02's M24 half (an M13 rerun with identical output leaves M24 tasks `reused`); P0CL-14 (a pathological formula returns within its bound, and a fresh interpreter importing the main server and serving a submission has no grammar module loaded); twins settled end to end across two `complete` runs; the harness submits every `fixtures/s0` trace batch through the tools and each completes on its first submission | A promotion between task creation and `read_unit`: an assembler reading the promoted pointer serves a packet whose hash differs from the task's |
| P0-A-2 | The golden profile and its page-text variant, `golden.pass`, the golden tools, agreement in the spawned worker, pass-C creation, the work-queue skill, the golden agent file, the separation probe | P0-A-1, P0-E-1, P0-E-2a | D9 P0.7's: a golden pass without model or inputs is refused; pass B from pass A's instance is refused; concurrent A and B writes for one unit yield exactly one pass-C task; the stored agreement equals E2a's result computed directly; a worker timeout leaves no pass and the next call succeeds; the page-text variant writes no `eval` row and changes no task; the probe record shows a distinct instance id per subagent invocation | Two subagents writing A and B of one unit at once: without the unit-row lock neither sees the other and no pass C is ever created |
| P0-A-3 | The OPEN-D8-2 comparison on `core12` | P0-A-1, P0-E-2a, P0-E-3 | The evidence record with both arms' readings, the pre-registered rule and the operator's decision; `max_units` set accordingly | Arms sharing one configuration: the second arm's tasks are reused from the first and the comparison measures nothing |

**P0-A-0.** Mechanisms: `regex` 2026.9.29 patterns with `timeout` and `BESTMATCH`/`fuzzy_counts`;
rapidfuzz 3.14.6 `fuzz.partial_ratio_alignment`, `distance.Levenshtein.opcodes`,
`process.extractOne` (D4 §4.3; text-math note §6, L-10); `core/tex.py`'s tokenizer. Evidence:
`s0.stored`, `parse.regex-probe`, `s1.rendition-identity` (production canonical text equals the spike
renditions, so offsets are comparable), and `s5.keys-property` through the frozen `core/tex.py`.

**P0-A-1.** Mechanisms: FastMCP 4.1.3 lifespan with the pool, synchronous tools, Pydantic results,
`ToolResult` packets, the loose batch parameter, in-process `Client(mcp)` (D8 §1; interfaces note
§1.1–§1.6, IE-1, IE-3, IE-4); psycopg 3.3 `NOTIFY` inside the submission transaction (through P0-O-1);
Typer 0.27 for the two commands. Evidence: `s0r2.inputs`, `s0r2.scores` (the rendering),
`s0.sizes` (output budget), `s4.reference-diff` and `s4.sizes` (prompt parts and their pages),
`s4.batch-validation` and `s4.rules` (through P0-S-1/S-2), `s6.queue` (leasing and fencing through
P0-O-1).

**P0-A-2.** Mechanisms: the inline per-subagent stdio server and the lifespan instance id (IE-2);
`ProcessPoolExecutor` with the `spawn` context; `SELECT … FOR UPDATE` on the golden unit. Evidence:
`s0r2.adjudication` (what pass C is for), `s0r2.inputs`, `s5.equivalence` (through P0-E-2a),
`s6.queue`; it produces the separation record.

**P0-A-3.** Mechanisms: two M24 configurations, A0, E2a. Evidence: `core12`'s adjudicated goldens;
it produces the OPEN-D8-2 record.

## 6. Tests

Shared fixtures come from foundations' conftest: the per-session test database, the trace slice and
a compiled schema. This document adds thin fixtures: `mcp_client` (one in-process `Client(mcp)` per
module for the main profile, since sequential clients re-enter the lifespan), `golden_client`, and a
synthetic reference run builder. Async tests use anyio's pytest plugin, which `mcp` already installs.

- **P0-A-0** establishes that each cascade step finds what it should and nothing it should not
  (inline sentences per step, ambiguity, word snapping, a regex timeout forced by a tiny bound and
  recorded), that conversion resolves anchors, scopes and extents, that frame outcomes are classified
  correctly, and the identity and perturbation checks above (corpus-gated, skipped without
  `docs/statistics_corpus`). A Hypothesis property draws word-aligned substrings of real sentences and
  respaced or delimiter-swapped variants: the exact or spacing step must return the original span,
  and no result cuts a word. Expected spans come from the original text, never from a second run of
  the cascade.
- **P0-A-1** establishes the packet (golden-mode equality with the v1 packets and `reference/E*`;
  agent mode with the bootstrap list and with a synthetic reference run; splitting under the cap with
  shared context and continuous ids; hash equality across two processes with different hash seeds),
  the digest (a prompt-part change gives a new digest; an identical M13 rerun gives the same), and the
  tools through `mcp_client`: leasing and renewal, parts and pagination at 24,000 characters,
  per-item results with paths, the held-open first submission and its record in `ops.task.error`,
  completion, a lost lease committing nothing, twins, `NOTIFY` received by a listening connection at
  commit and never on rollback, the pathological-formula bound and the import check, `record_direction`
  and `ci direct` through Typer's `CliRunner`; the sentence map in `read_unit`'s structured content
  equals the stored proposal's frame; the harness maps a fixture whose locator lengthened by recorded
  text and stops on a fixture sentence the packet does not hold. One stdio smoke test runs `ci mcp serve` as a subprocess
  and checks that nothing reaches stdout before the handshake.
- **P0-A-2** establishes the profiles' tool sets, distinct instance ids across two server processes,
  the pass-identity refusals, the row lock (two connections writing A and B concurrently), agreement
  equality with E2a called directly, the worker timeout path, the held-open write, that the page-text
  variant leaves `eval` and `ops.task` unchanged, and that the golden server's parent process never
  loads the grammar.
- **P0-A-3** is an evidence run, not a test.

## 7. Indicative size

| Package | Product lines (tests excluded) |
|---|---|
| P0-A-0 parse | 450 |
| P0-A-1 M24, packet, prompt parts | 450 |
| P0-A-1 main server, submission, commands | 550 |
| P0-A-1 submission harness | 100 |
| P0-A-2 golden profile, `golden.pass`, worker | 400 |
| P0-A-3 comparison harness | 50 |
| **Total** | about 2,000, the coordinator's budget |

Prompts, the skill and the agent file are Markdown and not counted. The largest risk is the
submission path, where envelope checks, held-open bookkeeping and the transaction meet; it stays
small by leaving validation to `validate` and task state to the completion primitive.

## 8. Choices left to implementation

- Module names inside `methods/llm/` and `intervene/`, and where `agent.opus` and `golden.pass` live
  in `methods/`.
- The page-token form for parts and pages, and the in-lifespan cache of assembled packets.
- The exact wording of `extract.md`, `format.md`, `golden.md`, `golden_c.md`, the tool descriptions
  and the skill, within the content stated above.
- The worker's wall-clock bound, and the BESTMATCH error share and regex timeouts, starting from the
  spike's values.
- FastMCP 4.1.3 or 4.1.4 (interfaces note §1.8).
- The record ids of the separation probe and the comparison.
