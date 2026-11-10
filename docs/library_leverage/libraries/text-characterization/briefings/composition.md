# Characterization before conceptual enrichment

**Proposed research, 2026-11-10.** Consumes the [shared baseline](../briefing.md#baseline-and-evidence).
This is a target inquiry, not an accepted replacement architecture or applicability verdict.

## The substantive boundary

The proposed foundation retains fundamental units and how they are expressed: tokens, language
attributes, grammatical phrases/clauses, overlapping mentions, cue spans, reference syntax,
formal expressions and positioned symbol occurrences. Later operations combine these into
definition membership, condition applicability, conceptual groupings, cross-reference targets,
scientific relationships and analytics over those results. Classifier names do not determine
placement: a POS label characterizes language; a theorem's conceptual role interprets it.

Some work straddles the boundary. A dependency parser supplies predicted syntactic attachment;
choosing which assertion a condition qualifies establishes a different relationship. Reference
syntax can be characterized before identifying the referenced section. Pronoun/mention clusters
can be retained linguistic hypotheses while canonical entity identity remains downstream.
Discourse structure can supply attributed rhetorical observations without asserting the truth of
the propositions it connects. These are meanings to make explicit in future assessment, not a
reason to force all relationship-shaped outputs into the same stage.

The foundation may have internally dependent passes. Pipeline stages distinguish semantic
responsibility without demanding one invocation, table, process or durable task per distinction.
The test of the proposed separation is whether a consumer can ask for characterized units and
their dependencies, then explain its conceptual decision without privately inventing another
text recognizer. Raw text can remain available for inspection and witnesses. New language
requirements extend an explicit characterization operation and its consumers.

## TC-01/02/03: broader reusable fundamental units

Current detached linguistic columns and local native views are useful foundations. Extend the
research beyond tokens to explicit phrase heads and membership, coordination, clauses, modifiers,
negation/modality cues, terminology occurrences, reference designators, quantity syntax, interval
endpoints and formal-expression alternatives. A scientific term's surface occurrence is distinct
from its concept ID; a parsed comparator is distinct from the condition's scope of applicability.

spaCy's matchers and structural traversals could characterize reusable configurations. Lark's
lexical/grammar output could characterize nested or formally constrained units with source
metadata. Controlled vocabularies and domain extensions can contribute characterization recipes
without embedding the statistics book into the core implementation.

**Potential value:** several consumers reuse a stable unit rather than each expanding its own
noun phrase, identifying a cue, scanning a numeric field or extracting a reference designator.
This could improve consistency as well as remove repeated matching. It is not evidence of faster
execution or better extraction quality.

**Defeating condition:** expansions that look similar may encode different promised roles or
context. Hoisting a domain-specific stop rule into a universal phrase definition would spread a
semantic error. Small literal recognizers may already be sufficient; replacing every regex with
a grammar is not the objective.

**Next question:** for the definition, conditional and citation journeys, identify the exact
shared unit required by each consumer and compare it with the existing rule outputs. Separate
the invariant characterization from the consuming role/attachment policy before proposing a
shared producer. Preserve useful independent expectations when replacing mechanism-specific tests.

## TC-04: three compositional options

| Arrangement | Mechanism and useful contribution | Countercondition and next question |
| --- | --- | --- |
| Independent characterization | spaCy analyzes language; Lark analyzes captured formal regions and explicit lexical/structural families; join through exact source occurrences | May repeat cheap region selection, but preserves independent recall. Which useful structures can either discover without the other's proposals? |
| Linguistic guidance into grammar | spaCy rules/phrases nominate exact regions for a Lark start symbol, or a custom lexer provides typed language/math/reference units | Proposal misses can become an invisible ceiling; custom token streams must carry faithful geometry. Which source-first reference cases are excluded before grammar recognition? |
| Grammar output into linguistic passes | Positioned Lark results supply formal-unit spans, normalized lexical attributes or candidate annotations to downstream spaCy components | Changing token boundaries can invalidate model behavior and retained offsets. Can additions remain separate span/custom annotations over the unchanged source layout? |

Do not assume a single custom lexer unifies all responsibilities. Contextual LALR and dynamic
Earley have different contracts; postlexing can change Earley's automatic lexer choice. Existing
math parsing may legitimately retain a separate generalized parser while small field grammars
use deterministic parsing. Shared semantic units do not require one universal grammar.

## TC-05: preserve the information needed for later composition

Future product assessment should examine the following interface effects together:

| Proposed interface capability | Required meaning and consumer consequence |
| --- | --- |
| Addressable characterization units | Source/view/item/piece occurrence and exact ordered extents; repeated spellings remain separate occurrences |
| Rich annotation families | Native scheme, producer/configuration and availability remain discoverable; reconstructed native objects do not fabricate unavailable columns |
| Overlap and alternatives | Multiple candidates can coexist; discontinuous roles need ordered pieces beyond a single spaCy Span; forest alternatives retain correlation rather than becoming unrelated facts |
| Derived structure | Dependence on source, layout, grammar, model, rules and context is explicit; a new recipe yields a new product under existing release/custody ownership |
| Compositional reads | Consumers can select units and necessary context without reparsing source or opening every optional neural intermediate |
| Honest coverage | Not requested, unavailable, unsupported, failed, ambiguous and examined-empty remain distinct; absence requires the declared scope to have been examined |

These are proposed contract effects, not a selected wire schema. Compare native Doc/Span/Tree
execution, compact retained columns, typed domain projections and explicit source mappings.
One authoritative meaning may have several operation-shaped physical forms. `DocBin` need not
replace database reads; Lark trees need not become the only durable record; extension hooks need
not hide application policy inside familiar native properties.

## TC-06/07/08: learning and lifecycle without premature commitment

Investigate learned components now as part of the broad functional target. Distinguish boundary
proposal, label prediction, conceptual classification and binding. A larger encoder cannot
recover an excluded candidate, and a span classifier does not choose a directed pair simply by
labeling both endpoints. Supervision must distinguish unknown labels from explicit negatives;
NER's missing states do not automatically supply a mask for stock span classification.

Representation-sharing, native configuration/factories, trained artifact packaging, batching,
component prerequisites and valid-lifetime preparation can simplify a richer foundation. Compare
their whole lifecycle with existing orchestration and custody. Avoid a parallel spaCy Projects
workflow, cache or provider lifecycle unless it has a distinct consumer. Cleanup must occur after
the last tensor/native-object consumer; memory-zone objects cannot escape their lifetime.

No fitting, hosted calls, companion installation or exhaustive performance experiment is needed
to identify these directions. Contextual fit can require those later. Existing GLiNER, HanLP,
Maverick, Dipo, d1 and Docling implementations are credible complementary or incumbent options;
their current assignment is not a reason to exclude a potentially better target composition.

## How to assess the hypothesis next

Use the [five consumer journeys](consumer-journeys.md) first. For each, follow source → available
characterizations → reconstructed/missing units → conceptual operation → reader. Ask whether a
new shared characterization changes the consumer contract and removes a private recognizer.
Then challenge overlap, repeated spelling, discontinuity, missing columns, competing parses and
cross-item source mapping with independent expectations. Keep the ordinary source-produced route
separate from reviewed-candidate injection or diagnostic ceilings.

If source and official contracts settle a question, retain that reasoning. A focused probe is
appropriate only for unresolved coordinate/serialization behavior, native reconstruction,
grammar composition or ambiguity handling that would change a recommendation. Use the existing
dated evidence route and native outcome reporting. No new probe or benchmark was run here.

The next comparative inquiry must consider both a richer shared foundation and a coherent
retained-column/demand-driven alternative, including preparation, normal reads, model changes,
partial failure and consumer migration. A replacement includes removal of superseded matching,
configuration and adapters when no historical-data obligation needs them. Discovery neither
schedules that migration nor changes existing scientific/admission authority.
