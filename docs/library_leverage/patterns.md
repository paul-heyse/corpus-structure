# Codebase opportunity patterns for library leverage

**Adopted discovery guidance · edition 0.2.** Portable guidance for recognizing and investigating
opportunities. These patterns do not establish defects, prove library suitability or require an
adoption. Their benefit as agent guidance has not been tested or measured.

These are the base patterns. The working set also includes additional patterns maintained in
assessment outputs at the location bound by the project's framework. Read and use relevant
additional patterns alongside these, with the same reasoning role and stated-scope limits.
They require no prior inclusion in this document or a skill to be useful.

## Governing objective

Find better ways to fulfill a codebase's intended responsibilities by using established
capabilities where their semantics and total integration fit. Seek less unnecessary independent
machinery, stronger guarantees, better execution and useful new behavior. Preserve authority over
domain meaning while considering library mechanisms throughout the implementation.

## Discovery principles

1. **Ground in a responsibility and its consumers.** Establish the operation, intended outcome
   and why improvement would matter. Distinguish current needs, accepted planned needs and new
   proposals. Availability alone does not create a requirement.
2. **Preserve consequential meaning while questioning incidental mechanisms.** Identify inputs,
   outputs, invariants, identity, effects and failure behavior that constrain alternatives. Current
   code and tests are evidence; a protocol or historical quirk is not automatically a guarantee.
3. **Look across scales and through complete operations.** A local call, shared mechanism, domain
   algorithm or whole workflow can contain useful leverage. Trace enough preparation, execution,
   conversion, recovery and change to see the actual responsibility and burden.
4. **Treat recognizable shapes as leads.** Names, loops, duplication, private API use and old
   versions nominate investigation. Establish the actual work and contrary evidence before
   concluding that an opportunity exists or a capability fits.
5. **Compare complete realizations.** Consider configuration, native extension, composition,
   useful existing code and residual custom work. Include semantic surface, resource lifetime,
   developer/operator work and credible change. Larger adoption and fewer source lines are not
   intrinsic benefits.
6. **Keep inquiry open and proportionate.** Patterns organize attention without limiting it.
   Several can describe one opportunity; a useful observation can expose a missing pattern.
   Choose research and evidence that could change a decision, without exhaustive inventories,
   numerical scoring or mandatory probes.

## Pattern index

| Pattern | Recognizable opportunity | Potential source of leverage |
| --- | --- | --- |
| LOP-01 | Generic capability implemented locally | Delegate an established mechanism or kernel |
| LOP-02 | Mechanical structure maintained in several forms | Derive those forms from an authoritative declaration |
| LOP-03 | Adopted functionality reconstructed or bypassed | Use more of the existing capability and its guarantees |
| LOP-04 | Collective work coordinated item by item | Express useful bulk, vectorized or set operations |
| LOP-05 | Intent lost before the executing mechanism sees it | Preserve native planning, lazy composition and selective execution |
| LOP-06 | Representations repeatedly translated or expanded | Align models, interchange and operation-shaped representations |
| LOP-07 | Stable work repeatedly prepared or inconsistently reused | Use preparation and reuse at a valid lifetime |
| LOP-08 | Resource and failure lifecycles coordinated locally | Delegate coherent lifecycle and coordination responsibilities |
| LOP-09 | Equivalent responsibilities fragmented across consumers | Consolidate compatible behavior through a shared capability |
| LOP-10 | Custom integration fights a mechanism's model | Use appropriate extension points or reconsider the mechanism |
| LOP-11 | Historical compatibility machinery retains obsolete premises | Use supported behavior and retire unnecessary scaffolding |
| LOP-12 | An intended capability is absent or difficult to compose | Enable a useful workflow through established capabilities |

## LOP-01 — Generic capability implemented locally

**Articulation.** Code implements a generally useful algorithm, standard behavior or execution
mechanism that an established library or native system may already provide.

**Recognize.** Handwritten parsers, solvers, traversals, matching algorithms, caches, retry
mechanisms, query builders or framework infrastructure. Include generic kernels embedded in
domain-specific algorithms, developer tools and tests; package names and product criticality
do not determine whether a mechanism is generic.

**Investigate.** Can an established implementation discharge the actual operation while the
codebase retains its domain policy? Consider a complete capability as well as a reusable kernel.

**Counterconditions.** A similar API may implement different semantics. A small specialized
algorithm can remain appropriate when the integration burden or contract gap is larger than
the work delegated. Identify that gap rather than assuming either replacement or preservation.

## LOP-02 — Mechanical structure maintained in several forms

**Articulation.** One meaning is repeatedly expressed through construction, validation,
serialization, mapping, command handling or other mechanically related forms.

**Recognize.** Adding a field, operation or kind requires parallel edits to several lists,
switches, schemas, codecs or fixtures. Distinguish independent domain decisions from repeated
expressions of the same decision.

**Investigate.** Could a schema, type model, declarative facility, introspection or generation
mechanism derive the mechanical forms from one authority? What domain rules would still need
owned operations, and what does the generated realization require at runtime?

**Counterconditions.** Similar representations can intentionally encode different contracts.
Independent test expectations provide assurance. Removing independent expectations or forcing
distinct models into one schema can erase meaning rather than remove upkeep.

## LOP-03 — Adopted functionality reconstructed or bypassed

**Articulation.** Code uses a library but independently performs work or recreates guarantees
that an available feature may already discharge.

**Recognize.** Wrapper-side parsing, validation, aggregation, adaptation, retries, metadata
reconstruction or result computation surrounding lower-level calls. A feature can be underused
even when the library has many imports; a library used in two places can be fully sufficient.

**Investigate.** Which specific feature owns the same obligation? What code and lifecycle state
could disappear if that feature were used? Check configuration and version conditions before
assuming the feature is available in the selected realization.

**Counterconditions.** Similar checks can enforce different trust boundaries or policies.
Library defaults can be inappropriate. Separate an actual residual obligation from defensive
duplication before proposing deletion.

## LOP-04 — Collective work coordinated item by item

**Articulation.** Callers coordinate repeated scalar operations although the intended work may
be expressible as a useful bulk, vectorized, set-oriented or grouped operation.

**Recognize.** Repeated calls, round trips, tiny tasks, Python-object loops or per-record
transactions over a coherent population. Ask what the complete operation requires, rather than
assuming every loop should disappear.

**Investigate.** Can a native collective operation preserve ordering, multiplicity, failure
attribution, effects and resource constraints while removing repeated crossings or preparation?
Does its implementation actually execute collectively or merely hide the same scalar work?

**Counterconditions.** Independent effects, low latency, cancellation or partial results can
justify smaller units. Large batches can worsen memory, contention or recovery scope. Choose
the useful execution unit from the contract and workload.

## LOP-05 — Intent lost before execution

**Articulation.** Interfaces or intermediate steps erase useful intent before a mechanism can
plan the complete operation or avoid unnecessary work.

**Recognize.** Eager loading followed by filtering, materialized intermediates between composable
operators, opaque callbacks, premature conversion into scalar values, or interfaces that cannot
carry selection, projection or a composed expression.

**Investigate.** Could expressions, queries, lazy plans, demand or native composition keep intent
visible through the responsible engine? Compare the complete operation, including source access,
intermediates and consumer needs, rather than the final function alone.

**Counterconditions.** A materialization can enable reuse, isolation or a necessary semantic
boundary. Pushdown can change effects or errors; a query does not guarantee an efficient plan.
Establish the relevant semantics and execution route.

## LOP-06 — Representations repeatedly translated or expanded

**Articulation.** Conversion or expansion creates substantial mechanical work, duplicated
interpretation or unnecessary movement between representations.

**Recognize.** Repeated object-to-row-to-dictionary conversions, encoding/decoding cycles,
full hydration for a narrow operation, copied schema metadata, incompatible neighboring models
or caller-maintained identity translations.

**Investigate.** Could supported adaptation, shared types, native interchange, extension types
or a more suitable physical representation remove conversions? Identify exactly which identity,
null, precision, ordering, metadata and ownership properties survive the path.

**Counterconditions.** Translation can protect a deliberate contract, detach a large backing
allocation, enforce a trust boundary or separate volatile details. Zero-copy and one universal
representation are not objectives by themselves.

## LOP-07 — Stable work repeatedly prepared or inconsistently reused

**Articulation.** Work independent of changing inputs is repeatedly reconstructed, or local
reuse machinery reproduces capabilities available in an established mechanism.

**Recognize.** Repeated compilation, parsing, schema construction, planning, indexing or
resolution; overlapping caches; manual invalidation and preparation rebuilt at each item or
layer despite a longer valid lifetime.

**Investigate.** Could native prepared operations, compiled models, incremental facilities or
scoped caches reuse work under complete dependencies? Distinguish preparation from results and
include lookup, invalidation, retention and cleanup in the comparison.

**Counterconditions.** Premises may change between calls; context-dependent preparation cannot
be safely shared merely because its inputs look similar. Cheap recomputation can cost less than
maintaining reuse. Never infer validity from an unchanged label alone.

## LOP-08 — Resource and failure lifecycles coordinated locally

**Articulation.** Acquisition, execution, concurrency, cancellation, failure handling or recovery
is coordinated through custom state that an established capability may be able to own coherently.

**Recognize.** Scattered open/close logic, polling, retry loops, task registries, transaction
coordination, pool management, bespoke scheduling or cleanup repeated through several layers.

**Investigate.** What lifecycle can a managed resource, task group, pool, transaction facility
or engine actually discharge? Establish who owns cancellation, capacity, idempotency, partial
effects and recovery after delegation. Examine nested mechanisms for multiplying work.

**Counterconditions.** Project-specific durable outcomes or failure domains can require owned
coordination. A framework may introduce services, persistent state or recovery obligations beyond
the need. Compare whole lifecycles and actual participants.

## LOP-09 — Equivalent responsibilities fragmented across consumers

**Articulation.** Multiple places independently serve a substantially equivalent need, creating
inconsistent behavior or repeated maintenance that a coherent capability could consolidate.

**Recognize.** Several helpers, overlapping dependencies, partial adoption, repeated configuration
or different implementations of the same intent. Similar-looking code can hide different intent;
different-looking code can implement the same responsibility.

**Investigate.** Which semantics and policy are truly shared? Could a suitable library capability
serve the consumers with explicit variation and fewer independent decisions? Consider existing
facilities before adding another shared layer.

**Counterconditions.** Different contexts can legitimately require different contracts, versions
or isolation. A single package does not create one authority, and consolidating incompatible
responsibilities can increase coupling.

## LOP-10 — Integration fights the mechanism's model

**Articulation.** Custom integration works around a library's abstractions, extension model or
lifecycle, suggesting an overlooked extension route or a mismatch in mechanism selection.

**Recognize.** Private API use, monkey-patching, internals-heavy subclasses, repeated escape
hatches, elaborate adapters, custom rules encoded around a library that expects another model,
or restrictions that disable its useful composition.

**Investigate.** Could public hooks, strategies, custom types, policy configuration or a companion
integration express the actual variation? If not, compare a more suitable mechanism and deliberate
custom implementation. Keep domain interpretation with its authority.

**Counterconditions.** Public extension points can be insufficient or impose their own contract
cost. Working with a library's grain is useful only if that grain fits the intended responsibility.
Private access is a reason to investigate, not proof of an available public replacement.

## LOP-11 — Historical compatibility machinery retains obsolete premises

**Articulation.** A workaround, compatibility path or older usage form may persist after the
conditions that required it have changed.

**Recognize.** Version branches, conditional imports, shims, copied upstream fixes, deprecated
calls or comments promising removal after an upstream change. A deliberately pinned version is
context; its age alone does not establish an opportunity.

**Investigate.** Does the selected or credibly proposed version remove the original limitation?
What consumers still need the old behavior? Consider migration, defaults, support policy and the
full dependency family before recommending an upgrade or removal.

**Counterconditions.** The workaround may preserve a deliberate semantic difference or support a
real older consumer. A fix can exist only on an unreleased branch or in a different build. Record
the supported version conditions and remaining premise.

## LOP-12 — An intended capability is absent or difficult to compose

**Articulation.** A current or credible proposed activity lacks useful support, or existing
primitives cannot be assembled into a satisfactory workflow. Established capabilities may make
that activity feasible or substantially simpler.

**Recognize.** Manual operator steps, recurring investigative work, unsupported desired behavior,
awkward developer/test workflows, missing integration, or planned consumers that cannot use
available primitives through a coherent operation.

**Investigate.** Who would use the capability, what would they accomplish and why would it matter?
Which library mechanisms could enable it, and what product behavior, domain policy and ongoing
operation would still need definition? Existing source code need not exist for a genuine gap.

**Counterconditions.** Features common to similar systems are prompts, not demonstrated demand.
Library availability does not establish functional value. State proposed needs and uncertainty
plainly, and preserve the distinction from accepted product scope.

## Use and evolution

Patterns describe overlapping recognition shapes. Concern families such as data integrity,
computation, persistence, concurrency and engineering support locate their subjects. Altitude
describes footprint; reinvention, under-use, drift, fragmentation, friction and gaps describe
relationships to existing mechanisms. These dimensions need no exhaustive tagging.

An opportunity needs a concrete account of value and constraints, even when no matching library
is yet known. A pattern match alone supplies no positive or negative architectural verdict.
Applicability assessment establishes candidate fit; comparative review judges complete options
using the governing design criteria and intended outcomes.

During codebase opportunity identification and library applicability assessment, assess whether
the working patterns miss or obscure a useful framing. Comparing a codebase operation with
library functionality can reveal that the earlier opportunity analysis was too narrow. Comparative
review can likewise expose a missing pattern. Record useful additions or refinements in the shared
assessment output and apply them to affected work; keep their definition outside skill documents.

Give additional patterns stable identities, useful scope, articulation, recognition guidance,
investigation questions and counterconditions. Explain their origin and distinction from existing
patterns. Extend an existing output pattern when that improves the framing; no new-pattern quota
or exhaustive coverage claim follows. Useful additions survive retirement of their first occurrences.

The operator can later select additional patterns for manual inclusion in this base framework
and skill guidance. Preserve the originating ID and its mapping on promotion. Until then, use them
on the same footing as relevant base patterns. Changes to the base framework remain separately
instructed maintenance; keep language- and library-specific search cues in supporting guidance.
The framework creates no new linting, evidence campaign, scoring system or acceptance process.
