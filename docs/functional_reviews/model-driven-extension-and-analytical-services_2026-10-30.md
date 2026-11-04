# Model-driven extension and analytical services: functional-extension review

**2026-10-30 · Proposed.** This review covers two capabilities and how they connect:

- **One validated `ci` action per sanctioned model extension.**
- **Analytical methods governed by model-declared contracts.**

It is solution reasoning. It is not an accepted decision, an implementation plan or product
qualification. It changes neither the [semantic-model pivot](../plans/semantic-model-pivot_2026-10-29.md)
nor any other plan.

## Scope, baseline and evidence boundary

The operator selected two inquiries and set their scope on 2026-10-30.

**1. Agent-actionable model extension at development time.** For every sanctioned extension, one
`ci` action performs every necessary change, and the agent makes no further edits. Everything is
validated within that action. If anything is invalid, nothing changes and the agent receives a
detailed error. Runtime proposals from corpus discovery (D8 `propose_schema_change`) are in scope
only as an interaction. The operator named libcst, tree-sitter, ast-grep-py and `ast` for code
changes, and Typer and Rich for agent guidance.

**2. All analytical methods behind model-controlled ports.** The model apparatus controls
invocation, request formatting and output routing, going "beyond standard port design". Covered:
- model-backed methods: GLiNER2.5, vLLM generation and judgment, and embeddings;
- deterministic methods: Docling/MinerU, spaCy, rapidfuzz, Splink, z3, sympy/scipy and
  pgmpy/sklearn;
- whether the methods already implemented should migrate.

**Inspected baseline.** The review began on `main` at `2bcbfe7`. It was revised at `9491143`
together with a concurrently changing dirty tree. That tree adds:
- [ADR-0034](../adr/0034-recorded-agent-supervision.md), which supersedes ADR-0015 and closes
  CA-08;
- `semantic_alembic/versions/0034_reference_source_frames.py`;
- the retirement of the legacy `orchestrate/{agent,context,fates,queue,routing,runs,tasks}.py`.

Citations are to that tree on 2026-10-30. The project MCP server failed to connect, so nothing was
inspected live.

**Evidence and method.**
- Three read-only mapping passes and coordinator source inspection.
- The supplied overviews: [typer](../libraries/python_introspection/typer.md), [rich](../libraries/python_introspection/rich.md),
  [libcst](../libraries/python_introspection/libcst.md), [tree-sitter](../libraries/python_introspection/tree-sitter.md),
  [ast-grep-py](../libraries/python_introspection/ast-grep-py.md), [ast](../libraries/python_introspection/ast.md),
  [linkml](../libraries/data_model/linkml.md), [gliner2](../libraries/parsing/gliner2.md),
  [vllm](../libraries/analytical_infrastructure/vllm.md), and the operator-supplied
  [Python concurrency and worker management](../libraries/analytical_infrastructure/Python_Concurrency_Multithreading_Multiprocessing_and_Worker_Management.md)
  overview.
- Context7 for ruamel.yaml (round-trip `CommentedMap.insert`, `yaml.indent`) and LibCST
  (`transform_module`, `AddImportsVisitor`, `CodemodTest`).
- A fresh design-reviewer independently assessed the draft. Its corrections are integrated, and
  its disagreements appear where they arise.

No probe, installation, dependency or database change, or benchmark was run. All target behaviour
is **Proposed**. Library capabilities are documentation-level evidence, and installed-stack
compatibility is not established. Earlier spike evidence is cited by record.

**Standard.** [Core 3.3](../design_review/design_principles/core/design-principles.md) and the
[heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md), as
`standard.toml` selects them. The relevant rules are FP-02, FP-04, FP-05, FP-07, A1–A4, DP-01,
DP-08, DP-14 to DP-18, DP-24, §C placement, and H3, H12, H13, H21 and H23.

## What exists today

The pivot already gives the model one editable meaning per scope (DESIGN §B5). How much work an
extension takes depends on where it lands. There are three tiers.

<a id="tier-a"></a>
### Tier A: pack data, carried by the release, no code

- **A new domain relation** is one LinkML slot in `domains/<pack>/semantic.yaml`, attached through
  the class's `slots:`. Commit `92a1d39` added toy `inspection` this way; it also touched
  `slices.yaml` and fixtures.
- **Derived artifacts.** Preparation derives Pydantic boundaries, JSON Schema, OWL/SHACL, and
  registry and projection rows (`semantic/boundary.py:202`, `semantic/prepare.py:836-1015`,
  `semantic/ontology.py:258-265`).
- **Preparation is pure and database-free** over a `SourceBundle` of bytes (`prepare_release`,
  `prepare.py:508`). It refuses unsupported constructs through private allowlists (`_ALLOWED`,
  `_SAFE_ANNOTATIONS`, `prepare.py:73,126`). It checks annotation keys but never their values.
  `cs:extract: mention|llm` has no Python consumer beyond that allowlist (`prepare.py:82,220`).
- **Pack inputs are assembled by `acquire_pack`** (`semantic/regeneration.py:67`). It reads about
  a dozen paths:
  - pack files;
  - `domains/core` rules;
  - `ingest/profile.py` `SOURCES_DIR` source profiles;
  - packaged model files;
  - the method registry (`orchestrate/phase0.py:98`).
- **The same tier covers** classes, enums, statement types, conditional rules, domain rules and
  views, and `methods.yaml` configurations. Typed queries remain Python (`domains/<pack>/queries.py`).
- **Activation runs only through regenerate.** `ci regenerate` (`cli/regenerate.py:100-215`)
  does more than activate:
  1. It persists and admits the release.
  2. It initializes the project and starts a run.
  3. It runs agent extraction (`extract_run`, line 185).
  4. Only then does it activate and select.

  No narrower prepare→admit→activate command exists.

<a id="tier-b"></a>
### Tier B: trusted execution model plus a code release

Commit `e97544a` (resolve_identity) is the ordinary operation addition. It changed the YAML,
`contracts.py` and the compiler version in `types.py`. Commits `66e12fc`, `893edcd` and `dfd2994`
built the apparatus rather than extending it, touching up to 28 files each. A new operation
touches these sites:

- **`model/semantic/execution-model.yaml`** (8.6k lines): `operations`, `implementations`,
  `effect_definitions` and `transitions`. It contains 118 PyYAML `&id` anchors and no comments.
- **`contracts.py` `approved_implementations()`**: function-local imports and a dict. A test,
  `test_contracts.py:85-91`, checks equality with the YAML and with `__qualname__`.
- **`effect_support.py` `SUPPORTED_EFFECTS`** and `SUPPORTED_EFFECT_VERSIONS`. By its own
  docstring these are "independent of candidate declarations". `_validate_effect_support`
  (`contracts.py:412-440`) requires exact equality between the YAML operation's {implementation,
  version, effects, transitions} and the support entry.
- **The implementation**, which names its operation through 22 `require_*operation("<id>")` call
  sites.
- **Occasionally:** PL/pgSQL, `_APPROVED_NATIVE_GUARDS` (`contracts.py:339`),
  `_NATIVE_CAPABILITIES` (`execution_admission.py:20`) and compiler versions.

<a id="tier-c"></a>
### Tier C: a native or physical change with a frozen migration

- **`ci schema derive --out`** writes candidate products and finishes derivation before writing
  (`cli/schema.py:149`).
- **The revision step is not a template.** Revision 0034 needed a hand-written product function,
  `reference_source_products` (`native_products.py:674-715`). It parses the previous revision's
  descriptor with pglast and rewrites body digests. Its migration also differs in shape from
  0033's, which carries grants and owner substitution. `consolidation_products()` rebuilds the
  whole chain, and `test_native_closure.py:313` byte-compares every revision.
- **Hard-coded revision constants have already drifted.** `cli/schema.py:190-191` still emits
  `predecessor: semantic_0032` / `revision: semantic_0033`, while `execution_admission.py:201`
  pins digests "through semantic_0034".

### Agent-facing surface

- `ci` is Typer with Rich output. Hand-written groups register from `cli/__init__.py:31`, and
  every command has `--json`.
- `Diagnostic` (`semantic/types.py:69`) is a rich typed refusal carrying code, location, message,
  outcome, `contract_id`, consumer, expected, actual and remedy. `cli/failures.py` emits it in full
  as JSON. In text mode, however, it prints only `refused: {error}` (line 40), which drops the
  remedies.
- No command describes extension kinds, operations or relations.
- libcst, ast-grep-py and tree-sitter are not dependencies, and ruamel.yaml is only transitive.
  The pivot left "the later choice of CLI, generator or script" open (coordinator, CA-06).

<a id="methods-today"></a>
### Analytical methods

- **Contract and execution.** Methods implement the `Method` Protocol (`core/method.py:488`).
  They register through a static tuple (`orchestrate/phase0.py:88`) and a `MethodRegistry` over
  `methods.yaml` (`orchestrate/registry.py:118`). They run synchronously in process in
  `run_source_methods` (`orchestrate/semantic.py`), where a unit error ends the run.
- **Metadata lives in Python.** It comes from the method classes and is recorded into immutable
  `ops.method` rows (`semantic/operations.py:127-157`; guard in `semantic_0025_methods.sql`).
  `execution-model.yaml:408` defines `MethodDefinition` as a run-scoped row concept. No release
  section declares methods.
- **Observation payloads are generic.** They are a `SourceObject` tree with a free-text `family`
  (`model/semantic/observations.yaml:58-72`; `semantic/observations.py:139-264`). Per-unit
  `SourceCoverage` already carries an outcome, a reason and a `required_capability` (lines 73-79).
- **Method names are hard-coded.** The dependency manifest picks libraries by method name
  (`orchestrate/semantic.py:134-146`). The propose path hard-codes `agent.opus` (lines 102, 481,
  537 and 599).
- **The agent route is a supervised session.** ADR-0034 runs a run-bound Claude process over the
  queue and MCP (`intervene/automated.py`), with process-group supervision at lines 169-187. That
  is a session over the task lifecycle, not a request/response provider.
- **No ML stack is wired in.** There is no gliner, vllm, torch or HTTP client.
  `LlmSettings.endpoint` is unused, and `paths.model_cache` (`settings.py:55`) is unused by any
  provider.
- **Pre-pivot designs**, all **Proposed**: D4 cards M04–M07, M10, M12, M14–M16 and M20–M21; D6
  §3.2 (workers) and §5 (resources); D5 §6.2 (confidence sources).
- **Spike-tested:** the LinkML → GLiNER `Schema.from_dict` compiler (D2 §7.2, `s4.gliner-roundtrip`)
  and the decoding-form transform for vLLM structured outputs (D2 §7.3, `s4.decoding-form`).
- **Pivot scope.** The pivot coordinator puts "new provider" outside its scope.

## Shared premise and the extension boundary

**One property ties the two inquiries together:** every sanctioned extension has one declared
home and one validated route.
- Part A automates the route.
- Part B moves analytical methods into declared homes, so that adding a method or provider becomes
  a small, recurring, sanctioned extension.

<a id="decision-class"></a>
**Every extension kind is offered. Some also carry a decision class** (revised after operator
feedback, 2026-10-30). Some changes trigger ADR-0033's revisit clause or alter a §B decision:
- effect semantics outside the owned profiles;
- new native custody;
- a meaning-changing rename or removal.

Those need design approval, which works as it does for any code edit: the agent asks the
operator first, conversationally, before invoking the action. The CLI does not try to enforce
that process. It makes the decision part of the change instead:
- The kind's catalog entry marks it as decision-class.
- The action requires the agent-authored ADR, plus the owning design-section amendment AGENTS.md
  requires, as inputs to the same change set.
- Validation includes the existing `adr-lint`.

So decision-level changes keep the single validated all-or-nothing action. What differs is only
what the change set must contain. An earlier draft excluded these kinds from the CLI. That added
no protection that the conversational approval and Git do not already give.

**Order of work** (DP-16):
1. Reduce incidental duplication first: the revision constants, the implementation mirror and the
   untyped method payloads.
2. Then automate what remains.
3. Keep the deliberately independent authorities independent.

<a id="atomicity"></a>
**Scope of all-or-nothing** (revised after operator feedback, 2026-10-30). The database is
derived state: releases are prepared from repository sources, and the data can be regenerated. So
the action can carry the change through to activation.

The order of an action is:
1. **Validate everything first.** Tier A runs in memory. Tiers B and C run in the shadow tree,
   with native admission on a fresh clone.
2. **Promote the tree.**
3. **Persist, admit and activate** the affected packs' releases. This uses a narrow path that
   starts no run and no extraction, unlike today's `ci regenerate`.

**When activation fails.** The compare-and-swap keeps the prior active release selected, and the
journal reverts the tree. The only residue is an unreferenced, content-addressed archive of the
never-activated release, which is harmless. Existing runs keep their bindings throughout.

**What "nothing changes" means.** A refused action leaves the tree byte-identical and the active
release unchanged.

**Beyond one action.** Wider recovery uses the same protection as code. Backups, plus a proposed
**dataset snapshot under Git LFS** (for example a `pg_dump` of the dedicated `18/corpus` cluster,
committed at checkpoints), put the data under Git history like any other edit. Evidence raw
outputs already use LFS (AGENTS.md). One content obligation applies: the snapshot must contain
the recorded LLM and agent observations. Re-running those methods does not reproduce them
(D4 rule 3), so "regenerable" means restoring recorded outputs, not recomputing them.

## Part A — agent-actionable model extension

<a id="O01"></a>
### O01 — A declared extension catalog with `ci model kinds | describe | schema`

**Value.** An agent or operator can see, for every offered kind:
- its tier and required inputs;
- the files and rows it changes;
- what is derived;
- which validation runs;
- its **compatibility class**: whether an add, modify, rename or remove changes meaning.

They can also inspect current definitions before changing them. That is DP-24's "compact,
navigable map of the sanctioned extension path for agents", which today exists only in commit
history.

**Realization.**
- **A typed specification per kind**, owned by code, carrying:
  - a Pydantic input model, whose JSON Schema `ci model schema <kind>` prints;
  - a planner that emits a change set (O02);
  - its validation set and compatibility class;
  - help and examples.
- **The read commands.** `ci model kinds` lists what is offered. `ci model describe relation owns
  --pack toy` renders the current definition and its prepared release rows, reading pack files and
  the prepared release, never the database (D8:291).
- **Allowlist consolidation.** `_ALLOWED` and `_SAFE_ANNOTATIONS` move into one shared declaration
  read by preparation refusal and by CLI choices (DP-01).
- **A declared value vocabulary for `cs:extract`.** O09 is its first real consumer.

The catalog lists only kinds whose planners exist, starting with tier A. It must not advertise a
route that nothing can carry out.

**Interaction with compatibility.** Renames and removals break `queries.py`, fixtures and
existing references, so they cannot be validated in memory. They become tier-B-validated kinds,
or refusals that name the migration decision.

<a id="O02"></a>
### O02 — Transactional change sets: plan, validate, then promote or refuse

**Value.** This is the core of the operator's requirement. One command produces a complete
change, everything is validated before the tree is touched, and a refusal leaves every file
byte-identical with diagnostics the agent can act on.

**Engine, in four steps.**

1. **Plan in memory.**
   - The planner computes new bytes for each target, as a change set of
     `{path: (expected_sha256 | absent, new_bytes)}`.
   - YAML edits use ruamel.yaml round-trip (`YAML(typ="rt")`). `CommentedMap.insert(pos, key,
     value)` positions new entries, and the packs' flow collections (`slots: [registry_id, owns]`)
     stay flow.
   - Python edits use libcst. It gives lossless output and structured
     `TransformSuccess/Failure/Skip` results ([libcst.md](../libraries/python_introspection/libcst.md) §6.1, §6.4).
   - New files come from templates.
   - Planned Python goes through `ruff format -` and `ruff check --fix` **in memory**. Otherwise
     `just turn-end` would rewrite the landed code and break the "no further edits" promise.
2. **Validate in memory** (tier A). A byte-overlay `acquire_pack` must cover all of its inputs:
   - pack files;
   - `domains/core`;
   - `SOURCES_DIR`;
   - packaged model files;
   - the method registry.

   `prepare_release` then runs over the overlay bytes.
3. **Promote with preconditions.**
   - Take a repository-level lock. Refuse to start while a journal is pending.
   - Recheck each target's hash, so concurrent edits are refused as `concurrent_edit`.
   - Refuse when a target has staged index content that differs from the working tree. Never
     stage anything.
   - Write to a temporary sibling, then `os.replace`. New files use exclusive create.
   - The journal records prior bytes, and `ci model recover` restores or completes an interrupted
     promotion.
   - SIGINT is deferred during the replace window. That needs a small new guard; the repository
     has no SIGINT deferral today, only the SIGALRM deadline at `methods/math/grammar.py:405`.
4. **Activate (optional, `--activate`).** Persist, admit and activate the affected packs on the
   narrow path. If this fails, the journal reverts the tree and the prior active release stays
   selected ([atomicity scope](#atomicity)).
5. **Report.**
   - On success, `ChangeResult` gives the paths with their before/after hashes, the **release
     delta** (registry and projection rows of the prepared releases before and after, for every
     affected pack), the validation receipts, and a suggested commit message naming the slice and
     its outcome, per AGENTS.md.
   - On refusal, the agent gets the `Diagnostic` list, `tree_unchanged: true` computed from
     hashes, and the outcome in the repository vocabulary: `failed` for an invalid change, or
     `blocked` when a prerequisite is missing.
   - `--plan` renders Rich `Syntax` unified diffs plus the delta and writes nothing. `--json`
     emits the same models.

**Extension to code tiers** (needed by O13; later O04 and O05). Importable code and tests need a
**shadow tree**: a copy of the repository-root layout outside the repository, carrying the change
set. Code finds its root through `Path(__file__).parents[N]` (for example `schema/pack.py:60`,
`core/db/extensions.py:16`), and pytest configuration and `scripts/native_test_support.py` live at
the root. The shadow tree does not need to be a Git worktree and changes no Cargo settings.

The shadow route adds several obligations:
- **Input manifest (H23).** Validation depends on untouched files that concurrent work may change.
  Record their hashes and recheck them at promotion.
- **Failure attribution.** Shadow tests run over other people's uncommitted work. Rerun the
  failing node ids on an unmodified snapshot, so that a `pre_existing_failure` is reported
  separately rather than as a refusal caused by the change.
- **Blocked prerequisites.** Tier-B/C tests need the 5434 cluster and the session template
  (`tests/conftest.py`, ADR-0032). When either is unavailable, the result is `blocked`, with the
  tree unchanged.
- **Supervised validation processes.** Each check runs as a subprocess in a new session with a
  deadline, terminated by process group. This reuses the `start_new_session` / `killpg` pattern
  already in `intervene/automated.py:169-187` ([concurrency overview](../libraries/analytical_infrastructure/Python_Concurrency_Multithreading_Multiprocessing_and_Worker_Management.md)
  §9.4, §10.2: subprocess timeouts can actually terminate work, whereas `Future.result(timeout)`
  cannot).
- **Provenance.** Outside Git, `code_commit()` reports `unknown`. Results must say that validation
  ran on a shadow copy.
- **Database residue.** Native test templates and clones are declared as cache-like residue, not
  hidden.

Running each kind's targeted tests, rather than the full suite, keeps the cost in proportion
(FP-07). `just test-all` remains the qualification route.

**Probe before scheduling.** A planning-time probe should settle two things:
- that ruamel round-trip is byte-stable outside the edited region, for one pack and for
  `execution-model.yaml`;
- that libcst 1.9 parses the repository's **PEP 758** `except A, B:` syntax (`core/provenance.py:21`
  plus two other modules). The overview does not mention PEP 758.

<a id="O03"></a>
### O03 — Tier-A authoring commands for packs

**Value.** Tier-A changes (classes, properties, relations, enums, rules and views) are the most
frequent extensions. They are already data-only, so automating them carries little risk and
returns a lot. Fidelity improves because the agent states intent instead of hand-editing YAML and
remembering to attach slots.

**Resulting interaction** (illustrative):

```text
$ ci model add relation --pack toy --name audits --domain Organization --range Asset \
    --multivalued --extract llm --constraint-scope accepted_value --plan
plan: 1 file · release delta (toy): +1 property_definition, +1 property_applicability
  domains/toy/semantic.yaml
    classes.Organization.slots: [registry_id, owns] → [registry_id, owns, audits]
    slots.audits: {domain: Organization, range: Asset, multivalued: true, annotations: {...}}
validation: prepare_release (semantic-2) passed in memory
$ ci model add relation ... --range Assett --json
{"error":{"code":"PreparationError","outcome":"failed","tree_unchanged":true,
 "diagnostics":[{"code":"unresolved_range","location":"slots/audits/range","outcome":"unresolved",
 "expected":"a class or type in the pack import closure","actual":"Assett",
 "remedy":"use one of: Asset, Organization, Source, InspectionValue, ..."}]}}
```

**Realization.**
- Planners edit `semantic.yaml` and `schema/rules.yaml`.
- Nested kinds, such as a qualified n-ary relation (completeness review §8 scenario 1), take a
  `--spec file.yaml` validated by the kind's model. Typer's cardinality forms cannot express
  nesting ([typer.md](../libraries/python_introspection/typer.md) §3.2).
- LinkML `SchemaBuilder`/`SchemaView` ([linkml.md](../libraries/data_model/linkml.md) §5.3–5.4) help build and
  check fragments. They do not serialize reviewed files.
- Changes to the `domains/core` rules fan out to every pack, so validation and the delta cover all
  affected packs.
- **`--activate` takes the narrow path** described under [atomicity scope](#atomicity): prepare,
  persist, admit and activate, with no run. Today's `ci regenerate` would also start a run and
  agent extraction, which an authoring action should not do. The same path, exposed as
  `ci model activate --pack`, fills a real gap on its own.
- **Open decision.** Whether a kind also maintains slices and fixtures, as `92a1d39` did, or
  leaves them out of scope.

<a id="O04"></a>
### O04 — Tier-B operations that compose already-supported effects

**Value.** This value is lower than the first draft claimed, on frequency grounds. Operations have
mostly been added during architecture work that also carries ADRs. Composing effect versions that
are already supported is the ordinary case. New effect semantics are a **decision-class** variant
of the same kind:
- the agent obtains the operator's approval first;
- the ADR and design amendment become inputs to the change set (see
  [decision class](#decision-class)).

**Wiring and behaviour.** The command takes the agent-authored implementation and its tests as
inputs and lands them together with the generated wiring:

```text
$ ci model add operation --spec scratch/score_alignment.yaml \
    --implementation scratch/score_alignment.py --tests scratch/test_score_alignment.py
```

**Independence, which the first draft missed.** `_validate_effect_support` is an equality check
between YAML and code. If one command generated both sides from one spec, the check would prove
nothing. Independence survives only if the code-side claim comes from the **agent-authored
implementation** and never from the spec.

The reviewer's realization is to merge the `approved_implementations` mirror and the
`SUPPORTED_EFFECTS` entry into **one declaration on the implementing callable**, for example
`@owned_implementation("score_alignment", version="1", effects=(...), transitions={...})`. The
mapping is collected from an explicit tuple of owner modules. That makes it consistent with
ADR-0031: no catalog strings and no selection by import order. Several gains follow:
- one mirror and one version copy disappear;
- the profile sits next to the code whose change it must follow, as the `effect_support.py`
  docstring asks;
- the YAML-vs-code equality compares two separately authored inputs.

**What the command does not claim.** It does not try to prove that each declared effect is
exercised. Effects such as `atomic_parent_generation_cas` need native concurrency tests, and
per-effect test tagging would be diligence-proof machinery.

**Where operation-id literals are handled.** They stay in the supplied implementation and are
enforced when the contract resolves. ast-grep-py may *locate* them for `describe`
([ast-grep-py.md](../libraries/python_introspection/ast-grep-py.md) §5.1). It must not edit them, because overlapping
edits are silently skipped (§7.3).

<a id="O05"></a>
### O05 — Derive revision identity now; defer a freeze command

**Now.** Derive the current and next revision from the Alembic script directory instead of the
constants in `cli/schema.py:190-191` and the `semantic_0033_*` names in `native_products.py`. The
existing drift proves the need. This is a DP-01/DP-16 reduction that does not depend on the CLI.

**Later.** Tier C is rare (0027, 0033, 0034). It also carries behaviour: SQL kernels, plus a
descriptor update that `reference_source_products` shows is not a template. When a freeze command
earns its place, it should follow O04's model:
- the agent-authored SQL is an input;
- the descriptor-delta step is declared;
- validation runs a fresh-clone `alembic upgrade`, `ci db check --release` and
  `test_native_closure.py`.

**Digest pins.** Recomputing `_DESCRIPTOR_SHA256` in the same command still guards *deployed*
drift. Against authoring error, however, it is tautological, so pin changes must appear explicitly
in the result.

<a id="O06"></a>
### O06 — Typer and Rich guidance an agent can act on

**Value.** `--help` should suffice to specify a change correctly the first time, and every
refusal should say how to fix it.

**Mechanisms**, all generated from the O01 catalog:
- help panels per tier (`rich_help_panel`, [rich.md](../libraries/python_introspection/rich.md) §7.4);
- `Enum`/`Literal` choices from the shared allowlists and vocabularies
  ([typer.md](../libraries/python_introspection/typer.md) §3.1);
- `autocompletion=` callbacks for class, slot and enum names that read pack files and guard
  `ctx.resilient_parsing` (§6.2, D8:291);
- epilog examples;
- `ci model schema <kind>`;
- Rich `Syntax` diffs for `--plan`.

Two smaller points:
- **Text-mode diagnostics.** `failure_boundary` should render the `Diagnostic` fields, including
  the remedy, rather than only `refused: {error}`.
- **CLI reference.** `typer corpus_structure.cli.app utils docs` (§10.2) can generate one. No new
  CI freshness check should be added (AGENTS.md: no new alignment linting).

The remaining Rich practices carry over:
- `rich.markup.escape` for user text (§6.3);
- `--json` output kept free of decoration.

Typer's help theme cannot share the application Console (§7.7). That limits presentation only.

## Part B — model-controlled analytical services

<a id="O07"></a>
### O07 — Method invocation as a declared operation family in the ADR-0033 apparatus

**Value.** A method's meaning is what the model should govern:
- what it consumes;
- which report families it produces, with typed payloads;
- its outcomes and confidence source;
- its effects, and how failures and retries behave.

With that declared, a new method's observations are typed, validated and routed without
per-method code. Consumers and evaluation read them by declared meaning.

**Realization (from the reviewer; adopted).** Do not build a parallel method contract.
**Reuse ADR-0033's apparatus.** Method kinds become declared operations in a release-scoped
section. `MethodDefinition` stays the run-scoped row they produce. The parts map like this:
- **Inputs** are the unit kinds.
- **Results** are typed report-family payloads.
- **The outcome domain** is `produced`, `empty`, `failed` or `refused-unsupported`.
- **Effects** include, for example, persisting typed source and measurement reports.
- **Implementations** sit under `implementations:`.
- **Provider failure classes** become outcome translations: out of memory, a schema-invalid
  response after repair, a timeout, or an unavailable provider.
- **Retries become declared transitions.**
- **Per-unit refusal** uses the existing `SourceCoverage` (`observations.yaml:73-79`) instead of
  ending the run.

The model then governs invocation, outcomes and retry, not just formatting. That is the
substantive meaning of "beyond standard port design".

**Ownership split** (H3, DP-15, ADR-0031/0033):

| Declared in | Owns |
|---|---|
| Domain pack | What to extract: `cs:extract` targets and values, thresholds, named `methods.yaml` configurations |
| Trusted execution model | Method operations, report families with payload classes, outcome translations, required **capability families** |
| Code | Provider adapters, their co-located capability profiles (families, features, limits, resources, as in O04), algorithms |

A release that requests a capability no code-owned profile supports is refused with a typed
diagnostic. This is "metadata alone cannot grant support" applied to providers.

<a id="O08"></a>
### O08 — Capability-family ports, classified by provider variation and resources

**Value and criterion.** A port earns its place where there is real variation (FP-02): several
providers, several checkpoints, local server versus in-process, GPU versus CPU, and a replay need.
The criterion is not "model-backed versus deterministic".

| Family | Providers | Port? |
|---|---|---|
| Span/record extraction | GLiNER2.5 `AutoExtractor.batch_extract`/`extract_long`; `JointIE`; spaCy candidates scored with `score_explicit_spans` ([gliner2.md](../libraries/parsing/gliner2.md) §2.4, §4.2, §5.2, §6.3) | Yes |
| Classification | GLiNER2 `Classifier` (constraint decoding, `feasible`/`violations`); GLiNER2.5-Decide (§4.1, §7.5) | Yes |
| Structured generation | vLLM OpenAI-compatible chat with `structured_outputs` ([vllm.md](../libraries/analytical_infrastructure/vllm.md) §7.1, §9.1) | Yes |
| Judgment/scoring | vLLM `choice` constraint; structured decisions; generative scoring (§7.1, §7.4–7.5). These are not interchangeable measures | Yes |
| Embedding | vLLM pooling `/v1/embeddings`; sentence-transformers (§6.3) | Yes |
| Document conversion | Docling; MinerU (both GPU, ML-model-backed) | Yes |
| Linking, verification, statistics, confidence | rapidfuzz, Splink on DuckDB, z3, sympy/scipy, pgmpy/sklearn | No: one provider each; they share the declared contract (O07) as owned implementations |

**The agent session is its own provider kind** (ADR-0034). It is a supervised session over the
task lifecycle, with leases, packets and protected submissions. It is not a structured-generation
call, and merging the two contracts would violate FP-02.

**Replay.** Every ported family gets a replay provider that serves recorded real responses. Three
rules, following H13/H14:
- **Key fixtures by request bytes,** not by `input_hash`. Every compiled-form change alters
  `input_hash`, so keying by it would invalidate every fixture at once.
- **Treat a fixture miss as `blocked`.**
- **Keep fixtures per scenario,** with a recording route.

Replay tests the apparatus, never the model, and a replayed provider is never `passed` for
provider qualification.

**Adapters are thin (DP-14).** They translate a compiled request (O09) into library calls and
the results back into typed responses. Thresholds, labels and routing stay in the model and
policy.

<a id="O09"></a>
### O09 — One LinkML declaration compiled into every request and response form

**Value.** This is what "the model controls formatting" means concretely. A new predicate with
`cs:extract: relation` reaches every provider without any adapter change.

**Chain.** Each artifact in the chain is a hashed release artifact that enters `input_digest`
(D4 rule 4):
1. The GLiNER extraction schema and `JointSchema` (D2 §7.2; round-trip Tested in
   `s4.gliner-roundtrip`).
2. The decoding-form JSON Schema for vLLM `structured_outputs` (D2 §7.3; Tested in xgrammar in
   `s4.decoding-form`).
3. Prompt parts and packets. The agent path already derives its request schema from the release
   (`semantic/proposals.py:342`), so that is a precedent.
4. Response validation through the boundary adapters (`types.py:423`).
5. Lowering into the O07 report-family payloads.

**Limits.**
- Valid schema output is not true output (vllm §7.1), and joint feasibility is not correctness
  (gliner2 §9.2). Consolidation and evaluation keep their roles (ADR-0014).
- The pivot's `cs:extract` vocabulary must be reconciled with the `ci:extract` vocabulary of the
  D2 compiler.

<a id="O10"></a>
### O10 — Model-declared selection and output routing

**Value.** A new method takes part in runs and feeds consolidation without edits to the
orchestrator.

**Selection.**
- ADR-0018 chains already name `<method>/<config>` in policy.
- The remaining hard-coding should go: the `agent.opus`-only branches (`orchestrate/semantic.py`
  at 102, 481, 537 and 599) and the name-keyed dependency manifest (134-146).
- Policy entries should name declared method operations.
- The dependency manifest should come from the selected provider profiles: libraries,
  checkpoints and revisions. This is a DP-15 provenance gain.

**Output routing.** Declared consumer edges say which consolidation and evaluation inputs read
which report families, as ADR-0033 does for execution edges. Observations stay append-only, and
only consolidation writes knowledge (ADR-0014).

**Agent route.** ADR-0034 settles how the agent works: the supervised session remains its own
route, selected by policy as one provider kind (O08).

<a id="O11"></a>
### O11 — Provider services and execution placement for the first consumers

**Value.** Model loading is expensive and GPU memory is shared (H12, H21). GLiNER and embedding
models hold gigabytes. vLLM is a server with its own lifecycle and continuous batching. Repeating
model loads inside the synchronous in-process `method.run` would waste both.

**Realization**, scoped to the first consumers. The full D6 cpu/encoder/llm topology is deferred
until a corpus-scale run needs it. Mechanisms from the
[concurrency overview](../libraries/analytical_infrastructure/Python_Concurrency_Multithreading_Multiprocessing_and_Worker_Management.md):

- **The durable task registry already exists.** The PostgreSQL claim with attempt/lease fencing
  (S6 `s6.queue`, Tested) separates pending, assigned, acknowledged and failed work, and a
  lost-lease worker commits nothing (§10.3). There is no need for Celery, Ray or Dask, whose
  scheduling would duplicate it (FP-03; ADR-0034 option 3). Revisit if work goes multi-node.
- **The encoder service is a persistent, actor-style worker** (§12.4). It initializes its models
  once, then consumes compact task descriptors (§12.1).
  - It runs as a **separate supervised process** on the product's Python 3.14, where gliner2
    works (operator, 2026-10-30). The process boundary exists for model lifetime, GPU ownership
    and failure isolation, not for interpreter compatibility. One open choice is whether
    `gliner2[local]` and torch join the product lockfile or form their own encoder project, as
    vLLM does.
  - Supervision reuses the process-group pattern of `intervene/automated.py`.
  - Exit monitoring uses `Process.sentinel`/`connection.wait` semantics, or subprocess exit
    status (§4.2, §10.3).
  - CUDA workers **use `spawn` explicitly**. Since Python 3.14 the Linux default is `forkserver`,
    whose preloaded state must be fork-safe (§4.1). The test-side spawn lifecycle in
    `tests/math_support.py` / `tests/math/test_workers.py` is a local precedent.
- **The vLLM service is managed like the PostgreSQL cluster**, through `ops/` plus `just` recipes,
  in its own environment (D9 `services/vllm-native`). Its client is one async loop that uses
  `asyncio.TaskGroup` with a `Semaphore` to bound the requests in flight (§9.1, §12.2). The server
  batches continuously and reuses shared packet prefixes (vllm §3.1, §3.4). Cancelling the async
  wrapper does not stop server-side work (§9.2), so deadlines are declared per request.
- **CPU methods with heavy initialization** use a persistent `ProcessPoolExecutor` with an
  `initializer` and `max_tasks_per_child` recycling (§4.3–4.4). spaCy pipelines are the example.
  `threadpoolctl` limits nested BLAS/OpenMP threads in numpy/scipy/sklearn workers (§10.5).
- **Hard deadlines.** Prefer a library's own timeout, such as z3's solver timeout. Otherwise use
  a dedicated process per task, Pebble, or AnyIO `to_process.run_sync(cancellable=True)`. A
  reusable pool cannot kill one task without losing its worker (§10.2, §11.4, §11.6).
- **Not applicable here:** free-threaded builds and subinterpreters. Extension modules such as
  torch, spaCy and GLiNER determine compatibility (§7, §8.4).
- **Provider profiles declare resources**: GPU memory, batch size and concurrency. The run records
  its GPU mode (D6 §5). vLLM sleep mode is the candidate for co-residency (vllm §11.3).
- **Failure handling maps to O07 outcome translations.** Out-of-memory errors halve the batch, and
  transient errors retry twice (D6:293).
- **Reproducibility** comes from the model id and revision in `input_digest`, batch invariance
  (vllm §11.4) and replay.
- **Model artifacts** are pinned by revision and hash into `paths.model_cache`, with an offline
  mode, so that a run never downloads unpinned weights.

This is the layer that goes beyond standard ports. The model decides what runs, how its results
are typed, how failures are classified and where outputs go. The provider decides how, and
whether, it can execute.

<a id="O12"></a>
### O12 — Move the implemented methods to the declared contract

**Value.** One method path instead of two, because DP-16 requires that replaced paths are
deleted. M01–M03, M09, M11, M13 and M19 already follow the `Method` Protocol. What they lack are
release declarations and typed payloads, so migrating them is mostly a matter of declaring report
families and payload classes. Migration should follow the first family proved under O07–O09, not
precede it.

One decision belongs here. The dormant pre-pivot LLM code in `methods/llm/{cascade,parse,packet}.py`
still has callers (`consolidate/assemble.py`, `semantic/proposals.py`). It either migrates or is
retired.

## Part A and B together

<a id="O13"></a>
### O13 — "Add a method", "add a report family" and "add a provider" as CLI kinds

This is where tier-B automation actually recurs: new providers and families keep arriving, and
architecture-level operations do not. With O07–O09 in place, the kinds split by tier:
- **A method over an existing family** is tier A: a pack configuration and annotations, validated
  in memory.
- **A new report family** is trusted-model data with payload classes.
- **A new provider** is tier B. The command takes these inputs:
  - the adapter;
  - its co-located capability profile (O04's pattern);
  - **recorded replay fixtures as the behavioural examples**.

  Validation runs the replay tests in the shadow tree.

Part B shrinks the code that Part A must automate. Part A's engine gives Part B a safe, recurring
route for new providers.

<a id="O14"></a>
### O14 — Interaction: runtime proposals rendered as authoring specs

A future D8 `propose_schema_change` record could render as `--spec` input for `ci model add`.
Discovery would then reach development through the same validated route, while authorization
stays separate, as `semantic-postgresql-model_2026-10-29.md#O01` requires.

The extraction context must refuse `ci model` write commands. That context is a supervised
ADR-0034 child process, which is read-only under D8:279–280. Development-time sessions keep their
access. This opportunity waits for the runtime proposal path.

## Mechanisms considered and their roles

| Mechanism | Role | Not used for |
|---|---|---|
| ruamel.yaml round-trip | Edit engine for packs, rules, `execution-model.yaml` | — |
| libcst | Python planners; `CodemodTest` for planner tests; `parse_template_*` | Function-local import insertion without a custom transformer |
| ruff (in memory) | Format and safe fixes on planned Python before validation | — |
| LinkML `SchemaBuilder`/`SchemaView` | Fragment construction and checks; induced slots for `describe` | Serializing reviewed files |
| ast-grep-py | Locating sites for `describe` | Edits (overlaps silently skipped); new lint rules |
| `ast`/`compile` | Cheap syntax pre-check | Rewrites |
| tree-sitter | None: edits are batch edits over valid source ([tree-sitter.md](../libraries/python_introspection/tree-sitter.md) §9.4, §11.3) | — |
| Typer / Rich | Commands, choices, completion, panels, docs; diffs and diagnostics | Deriving commands from database rows |
| subprocess + process groups, `asyncio`, `ProcessPoolExecutor`, `threadpoolctl` | Validation and provider supervision, async LLM client, CPU pools | Duplicating the PostgreSQL task registry |
| GLiNER2 2.1.0 / vLLM | Providers of O08 families | Owning thresholds, labels or routing |

**Rejected:**
- a generic plugin registry or workflow engine (FP-03, A3);
- Typer commands generated at runtime from release rows (this would couple CLI shape to database
  state);
- Celery, Ray or Dask schedulers for single-host work;
- free-threading or subinterpreters for the ML stack.

## Selection, dependencies and priorities

The coordinator and the independent reviewer agree on the order below. The draft's main error
was emphasis: it treated O04 and O05 as near peers of O03. They come last **on frequency
grounds**, and O13, not O04, is the main tier-B consumer of the engine. Decision-class kinds are
offered through the same action, so ordering is not a matter of process.

1. **Now, without any CLI:**
   - derive the revision identity (O05, first part);
   - consolidate the allowlists and add the `cs:extract` vocabulary (part of O01);
   - render text-mode diagnostics in full (part of O06);
   - write the [RC03](#RC03) ADR choosing the co-located implementation/support declaration (O04).
2. **Tier-A delivery** (Part A, one plan):
   - the O02 in-memory engine: overlay, lock, journal, in-memory ruff, index refusal, recovery;
   - O01 tier-A kinds, then O03 (with the narrow `--activate` / `ci model activate` path and
     modify/rename compatibility classes), then O06;
   - the round-trip probe on pack YAML.
3. **Part B** (its own plan and ADR):
   - O07 reusing ADR-0033;
   - O09;
   - O08 with replay for one family (GLiNER M06);
   - O10;
   - minimal O11 (the encoder service, then the vLLM service);
   - O12.
4. **O13 and the shadow-tree engine**, which depend on items 2 and 3. Run the libcst PEP 758 probe
   when this is scheduled.
5. **Wait:** a general O04 operation command, the O05 freeze command, and O14 (until the runtime
   proposal path exists).

**Conditions that would change this order:**
- If operations or native revisions start arriving as routine product work rather than
  architecture work, O04 and O05 move earlier.
- If one provider family dominates the corpus workload, O11's full worker topology moves earlier.

<a id="rule-impacts"></a>
## Rule impacts needing a decision

<a id="RC01"></a>
**RC01 — Agent writes through the CLI.** D8:279–280 says: "Opus may run read-only `ci` commands
… writes go through MCP tools". That governs the extraction agent, now the supervised or
interactive ADR-0034 session. Development-time source authoring is a different actor and effect.
*Decision:* clarify the scope of D8, and require the extraction context to refuse `ci model`
writes (O14).

<a id="RC02"></a>
**RC02 — The catalog versus "no generic introspection service"**
(`queries-and-consumers.md:22-24`). *Decision:* accept `ci model kinds|describe|schema` as the
DP-24 extension map, bounded to declared kinds and to pack files and the prepared release.

<a id="RC03"></a>
**RC03 — Support-profile independence.** *Decision (ADR amending ADR-0033):* adopt
co-located `@owned_implementation(...)` declarations that merge `approved_implementations` and
`SUPPORTED_EFFECTS`. Require that CLI-authored operations take the code-side claim from the
supplied implementation and never from the spec. Make new effect semantics a decision-class
variant: approved conversationally first, with the ADR as part of the change set.

<a id="RC04"></a>
**RC04 — "No new alignment linting."** Validation at action time reuses existing checks and kind
tests within the command. It adds no repository gate, ast-grep rule or freshness check for the
generated reference. *Decision:* confirm this reading.

<a id="RC05"></a>
**RC05 — Provider code ownership** (ADR-0031). Adapters and algorithms stay owned code. Rows
select among them by declared capability, with no import-by-string. This is consistent with the
current rules and belongs in the Part B ADR.

<a id="RC06"></a>
**RC06 — A Part B plan and ADR.** The pivot excludes new providers, so Part B needs its own plan
and an ADR adopting O07, O08 and O10. ADR-0034 already settles the agent route (CA-08 is
implemented), so no reconciliation remains.

<a id="RC07"></a>
**RC07 — Environments, dependencies and shadow validation.**
- Exact pins for new direct dependencies, named in the commit: libcst and ruamel.yaml for Part A;
  `gliner2[local]`, torch and an HTTP client for Part B.
- A separate service environment for vLLM (D9 `services/vllm-native`). The GLiNER encoder can
  share the product's Python 3.14. Whether it shares the product lockfile is a packaging choice.
- Shadow copies outside the repository rather than worktrees. This leaves the AGENTS.md concern
  about build reuse untouched.

<a id="RC08"></a>
**RC08 — Dataset snapshots under Git LFS** (operator proposal, 2026-10-30). Snapshots give the
database the same Git protection as code edits ([atomicity scope](#atomicity)). *Decision:*
- what a snapshot contains: at least the recorded LLM and agent observations, which cannot be
  recomputed;
- its form, for example a `pg_dump` of `18/corpus`;
- its checkpoint cadence;
- its LFS budget.

AGENTS.md already routes evidence raw outputs through LFS, so the decision extends an existing
route rather than adding a new mechanism.

## Demonstrating delivery

These scenarios show delivered capability. They do not fix acceptance scope.

- **A — Relation, tier A.** One `ci model add relation` changes only `domains/toy/semantic.yaml`.
  The layout is preserved and the release delta is reported. With a bad range, it is refused,
  hashes show the tree unchanged, and the JSON diagnostics carry a remedy. With `--activate`, the
  release is admitted and selected in the same action. An activation failure reverts the tree and
  leaves the prior release active.
- **B — Provider, O13.** A GLiNER2.5 provider is added with its adapter, co-located profile and
  replay fixtures. Shadow replay tests pass. A variant with a missing fixture is refused as
  `blocked`, and one whose profile contradicts the model is refused as `failed`, both with the tree
  unchanged.
- **C — M06 entity extraction.** The method is declared through O07 and its schema compiled by
  O09. The encoder service runs it, consolidation consumes the typed mention observations by
  declared routing, and an out-of-memory error maps to a declared outcome.
- **D — M16 judgment.** It reuses the decoding-form compiler and the structured-generation port,
  with no method-specific parsing.
- **E — A deterministic verifier, z3 M20.** It is declared through the same contract, with an
  in-process implementation, a native solver timeout, and no port.
- **F — Revision identity.** `ci schema derive` names the current head and the next revision
  without constants.

## Remaining uncertainty

- ruamel round-trip byte stability, and libcst support for PEP 758 syntax (probes: O02).
- The time shadow validation takes for each tier is unmeasured. It should be judged against the
  targeted test sets.
- How a declared method-operation section composes with the existing `MethodDefinition` rows and
  `ops.method` immutability (O07). The Part B ADR needs this.
- Whether tier-A kinds maintain slices and fixtures (O03).
- The encoder service's transport to the product process, and whether gliner2 and torch share
  the product lockfile (O11).
- Reconciling `cs:extract` with `ci:extract` (O01, O09).
