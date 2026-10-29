---
id: ADR-0019
title: "Identity follows content: renditions are content-addressed, statements and scopes are anchored by locators, authored batches are the authority"
status: superseded
date: 2026-10-28
supersedes: []
superseded-by: ADR-0024
design: []
evidence: Proposed
revisit: Locator regeneration moves statement or local-entity keys on real content edits often enough to orphan judgments or goldens, or a source's blocks have neither author ids nor distinctive opening text, so locators become long or ordinal-heavy.
---

## Context

ADR-0013 makes keys "hashes of canonical JSON of meaning-bearing parts" (D1 §10.1). Under the
design at `7e3dc23`, the evidence part of every key was physical provenance rather than meaning:

- **Renditions** were keyed by (document key, adapter configuration hash), and D1 §3.2 said two
  content-identical renditions "still differ when their adapter configurations do". The adapter
  configuration includes the M03 spaCy version and model (D4 M03) and every profile convention.
- **Downstream keys inherited it.** Segment keys hash the rendition key; statement keys hashed the
  anchor segment key; local-entity keys hashed the scope segment key; claim keys hash subject and
  statement keys.
- **Goldens were stored located.** `eval.golden_pass.batch` and `eval.golden_item.payload` held
  the stored (offset) form on one rendition, and a golden unit was "one annotation unit of one
  rendition" (D7 §3.1). The authored artifact, the model-facing batch citing `sN`/`cN` sentences,
  was not kept, and its citation frame was not recorded.
- **Locators had no owner.** The `page#id` / `page@u:` / `page@p:` grammar lived in D6 §8, while
  slices, fixtures, query evidence, `extref` and (now) keys each needed to resolve it.

The expected change is routine: phase 0 ports M01, M03 and M13 during the phase, bumps spaCy,
fixes profiles, and later adds sources. Each such change produced a new rendition and new keys for
nearly every claim in the corpus, even where the canonical text, segments and sentences were
identical (the relation S1 tested, record `s1.rendition-identity`). Judgments were orphaned
(D5 §7.3), golden sampling order (`sha256(unit_key + seed)`, D7 §3.1) changed, goldens detached
from runs on the new rendition so recall would drop silently (D7 §5.1), and `kb.embedding` had no
stable target. The design already routed around this for slices, fixtures and the acceptance test
by using locators, without drawing the consequence for keys, goldens or reuse.

Source: the phase 0 contract-layer review
(`docs/design_review/reviews/design_review_phase0-contract-layer_2026-10-28.md`), findings P0CL-01,
P0CL-03 and P0CL-04, rule changes RC01, RC03 and RC14, which the operator confirmed on 2026-10-28.
Owners: D1 §3.1, §3.2, §3.4, §10.1, §10.3 and D3 §5, §7. Consumers: D2 §7.3 (batch forms), D4 M01,
M03 and §4.3 (ingest, quote cascade), D5 §3.4–§3.5 (local entities, statements), D6 §8 (slices),
D7 §3 and §5.1 (goldens, predicted set), D8 §5 (query evidence). Nothing is built; P0-F2 is the
package that would freeze the key function.

## Options

1. **Keep the current design.** Simplest to state, but every ingest change re-keys the corpus and
   re-detaches goldens and judgments; slices, fixtures and goldens each route around keys in their
   own way. The recurring operator and agent cost, and evaluation that breaks silently, rule it out.
2. **Freeze the adapter configuration for phase 0** (the simplest viable alternative): a pins hold
   on spaCy and its model, a profile freeze beside the schema and guideline freeze, renditions
   frozen while goldens exist, and a locator-based key-migration mapping at each deliberate change.
   It contains the churn within phase 0 but recurs after it, makes a migration mapping a second
   identity mechanism, and turns every port or profile fix into operator work.
3. **Content-addressed renditions only.** Rendition identity becomes the document plus a digest of
   the content-identity relation, with adapter configurations as provenance. Content-preserving
   changes then keep every row and key, which removes the spurious churn; but statement and
   local-entity keys still hash physical segment keys, so any real edit to a page's content moves
   every key on that page through offset shifts, and goldens still bind to one rendition's offsets.
4. **Content-addressed renditions, locator-anchored statement and scope keys, and authored batches
   as the authority** (chosen). Option 3, plus: statement and local-entity keys hash locators of
   their anchors instead of segment keys; one locator contract with an owner; goldens, fixtures and
   proposals kept in the form they were authored, with a citation frame, and located per rendition.
   The added machinery is one provenance relation and a deterministic locator generator and
   resolver, both small and local; in exchange only real content changes move keys, and mostly
   only near the change.

Option 4 costs more than option 3 in one place, the locator generator, and keeps a benefit option 3
lacks: an edit to one block no longer moves the keys of the others on its page. It also replaces
three ad hoc locator uses with one contract, so the total burden is lower than options 1 and 2.

## Decision

- **Renditions are content-addressed** (D1 §3.1, §3.2; D3 §5). Rendition key = (document key,
  content digest); the content digest is the SHA-256 of canonical JSON of the content-identity
  relation: canonical text; the segment tree with kinds, offsets, parse statuses and
  non-diagnostic attributes; sentence segments; and the macro table, which canonical forms expand
  by (D1 §6.2, ADR-0012). Adapter configurations are provenance: `kb.rendition_build` records each
  (document, configuration) build with its task and `parse_detail`, many builds to one rendition.
  Ingest deduplicates by content, so a content-preserving change keeps every row and key.
- **Statements and local entities are anchored by locators; segments stay physical** (D1 §3.4,
  §10.1). Statement key = (document key, anchor locator, ordinal of the first sentence within the
  anchor). Local-entity key = (type, scope locator, normalized symbol or label). In keys a locator
  enters in structured form carrying the document key. Segment keys stay (rendition key, kind,
  start, end).
- **One locator contract** (D1 §3.4), owned in the build by ingest and math as a core-level
  function over a rendition's segments: the forms `page`, `page#id` (author id first),
  `page@kind:prefix` and `page@kind[n]:prefix`; a generator (unique author id, else the shortest
  unique whole-word prefix, else an ordinal among segments the whole text cannot be separated
  from); a resolver; refusal on ambiguity, never a nearest match. D6 §8 cites it. An annotation
  unit's unit key is its generated locator's string form.
- **Authored batches are the authority** (D1 §10.3; D3 §6.2, §7). Golden passes, fixtures and agent
  proposals keep the model-facing batch with its citation frame (each `sN`/`cN` mapped to the
  cited sentence's locator and text). The stored form is derived per rendition by the production
  quote cascade (D4 §4.3). A golden unit is identified by its unit key, with its authoring
  rendition as provenance; `eval.golden_item` is a derived projection of one pass c batch on one
  rendition. A frame that no longer resolves on a run's rendition marks the unit stale (re-locate,
  else re-author; D7 §3.5). The predicted set of D7 §5.1 uses the derived stored form on the run's
  rendition.

This refines ADR-0013's keys clause, which stays true: it settles which parts of evidence identity
are meaning-bearing. It does not supersede ADR-0013, and ADR-0012's token form is unchanged.

## Consequences

- **Easier:** ports, spaCy bumps and profile fixes that change nothing keep every key, judgment,
  golden and reused task; a real edit moves the keys of the edited block, not those of its page;
  slices, fixtures, goldens, query evidence and `extref` resolve through one function; golden
  sampling order and embeddings have stable targets.
- **Harder:** ingest computes the digest over the combined M01 and M03 output before writing; the
  locator generator must be deterministic and is part of the frozen key function; goldens and
  proposals are stored twice (authored and derived), and items are derived per rendition before
  alignment.
- **Limits.** A generated prefix is the shortest unique one, so an edit can lengthen or shorten
  the prefix of another block of the same kind on the page and move its keys. New original bytes
  are a new document whose key every locator carries, so a re-fetched page re-keys; a migration
  for that case is not designed. Segment keys and spans still move with any content change.
- **Evidence:** the content-identity relation is Tested for canonical text, segments and sentences
  on seven pages under two HTML parsers (record `s1.rendition-identity`, 2026-10-28), and the
  `#id`, `@u:` and `@p:` locator forms on the four spike pages (records `s1.adapter`,
  `s1.rendition-identity`). The rest is Proposed.
- **Not yet built:** locators (ingest and math, I0), keys and canonical JSON (foundations, F2),
  content-addressed ingest with build provenance (I1), the parse package from authored batch and
  frame to stored form (agent interface, A0), goldens keyed by unit key with derived items
  (evaluation, E1). Closure needs the property tests named in D1 §10.1 and a golden authored on
  one rendition that aligns unchanged against a content-identical rendition and against one edited
  elsewhere on the page. Disposition of P0CL-01 and P0CL-03 is in the design-phase plan's findings
  table, and of P0CL-04 in the phase 0 coordinator's §11; acceptance of this record closes none of
  them.
- **Revisit** (front matter): locator regeneration that moves keys on real edits often enough to
  orphan judgments or goldens, or a source (email quoting, generated tables) whose blocks have no
  author ids and no distinctive opening text.
