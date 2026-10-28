# Domain model map

The domain model as found at the [audited baseline](README.md#baseline), for the follow-up design
work. It is descriptive: who owns each meaning, how each concept is represented in each context,
which definitions claim authority over it, which translations connect the contexts, and how much
of it is realized. Deviations are diagnosed in the topic pages and linked by `DA-nnn`. A cell
labelled *target* is accepted design; *proposed* is design not yet accepted; *implemented* is code
at `024bb33` (existence only, unless a test is named).

## Contexts

One concept appears in several contexts. The design names them, but only some of the translations
between them have an owner ([DA-005](semantic-model-and-authority.md#da-005)).

| Context | What it is | Names | Where defined | Status |
|---|---|---|---|---|
| Authored batch | What a model, agent or annotator writes: sentence ids, local refs | local (`has_distribution`) | `core/batch.py` (`AuthoredBatch`), D2 §7.3 | implemented |
| Stored batch | The authored batch re-addressed to segments and offsets by the quote cascade | prefixed (`stat:has_distribution`, `core:modality`) | `core/batch.py` (`StoredBatch`), D1 §10.3 | implemented shape; cascade (A0) not built |
| Keyed candidate set | The pool consolidation and both rule call sites read | prefixed | `core/candidates.py` | implemented, partial ([DA-005](semantic-model-and-authority.md#da-005)) |
| Consolidated knowledge | `kb.entity`, `kb.claim`, links, alternatives, groups | prefixed | D3 §5, D5 | target; migration 0001 not built |
| Rule view | The flattened object rule-engine evaluates | prefixed classes; local qualifier attributes | D5 §8.2, D2 §7.4 | target |
| Decoding form | The JSON Schema constrained decoding uses | local | D2 §7.3 | target |
| Served answer | Rows with claim keys, evidence locators, coverage | prefixed | D8 §5 | target |
| Evidence records | Spike and probe results behind design claims (second domain) | record ids | `tools/evidence` (`Record`) | implemented |

## Concepts

| Concept | Meaning owner | Representations | Authorities | Translations | Status |
|---|---|---|---|---|---|
| Document, rendition | D1 §3.1–§3.2, ADR-0019 | `RenditionContent`; `doc:`/`ren:` keys (content digest) | `core/evidence.py` | build → rendition by digest | implemented (keys, digest); ingest not built |
| Segment, segment kind | D1 §3.2 | `Segment` tree; `seg:` key; locator; annotation unit | `SegmentKind` (`core/evidence.py`); D3 CHECK; role subsets in `locators.py`, `keys.py`, D3 BM25, D4 targets, `ci:target` strings | segment ↔ locator (`LocatorIndex`) | implemented; roles scattered ([DA-003](semantic-model-and-authority.md#da-003)) |
| Delimiting parse status | D1 §3.1 | `Segment.parse_status` | `evidence.ParseStatus` (used), `vocab.SegmentParseStatus` (unused), D3 CHECKs | — | duplicated ([DA-002](semantic-model-and-authority.md#da-002)) |
| Sentence citation | D1 §10.3 | authored `sN`/`cN` plus `CitationFrame`; stored offsets | `core/frame.py`; citation positions found by JSON key name | frame → segment (`resolve_frame`); authored → stored (cascade) | frame implemented ([DA-004](semantic-model-and-authority.md#da-004)); cascade not built |
| Entity (global, local) | D1 §4, D5 §3 | authored/stored item; `CandidateEntity`; `ent:` key; `kb.entity` | identity slots: pack `unique_keys` plus `KeySchema.entity_identity` | local ref → key; local → prefixed type (X2-01) | keys implemented; resolution not built |
| Statement, statement kind | D1 §4.3, §10.1 | item with anchor (sentence ids, `"unit"`, `"outside"`); `stm:` key | kind: `str` in core, enum in the pack; `ci:claim_bearing` in the pack; source-profile hints ([DA-010](semantic-model-and-authority.md#da-010)) | anchor → locator plus ordinal; `"outside"` → unowned | keys implemented ([DA-007](semantic-model-and-authority.md#da-007), [DA-014](structure-and-invariants.md#da-014)) |
| Claim | D1 §5, DESIGN §B1 | authored/stored claim; `CandidateClaim`; `clm:` key; rule view; `kb.claim` | shapes: `core/batch.py`; identity: `core/keys.py` code plus pack data plus D1/D5 prose ([DA-001](semantic-model-and-authority.md#da-001)) | batch → candidate (S2/C1); candidate → view (validate) | shapes and keys implemented; adapters not built |
| Core qualifier (modality, polarity, conditions, …) | D1 §5.2 | local in authored, `core:`-prefixed in stored | `CORE_QUALIFIERS`, `StoredQualifiers`, `keys.py` constants, core.yaml slots, D3 §6.1 ([DA-002](semantic-model-and-authority.md#da-002)) | local → prefixed (core models) | implemented |
| Modality behaviour (premise, cited, conflict) | D1 §5.2, D5 §5.1–§5.5 | — | each consumer's membership test ([DA-003](semantic-model-and-authority.md#da-003)) | — | not modelled |
| Schema qualifier | D1 §5.3, D2 §4 | raw JSON extras until S1 types them | pack (`ci:identity_qualifiers`); canonical form chosen by JSON shape ([DA-001](semantic-model-and-authority.md#da-001)) | local → prefixed (X2-01, P0-S-1) | partial |
| Value, condition, binding | D1 §6–§7 | value union and condition tree per form | `core/values.py` (owner) and the core.yaml mirror; canonical forms re-dispatched in `keys.py` ([DA-004](semantic-model-and-authority.md#da-004)) | canonical forms (`keys.py`, `tex.py`) | implemented |
| Reference (entity, statement, claim) | D1 §5, §10.3 | bare strings: local refs, then keys | no kind in the type; side-table owner named twice ([DA-006](semantic-model-and-authority.md#da-006)) | ref → key (`Keys.of`) | implemented, untyped |
| Alternative, identity group | D1 §5.5, D5 §5.3–§5.4 | `AlternativeItem`; `Member`; `alt:`/`idg:` keys | `core/batch.py`, `core/keys.py` | batch alternatives are not in the candidate set ([DA-005](semantic-model-and-authority.md#da-005)) | partial |
| Observation, task, run | D1 §2, §9; D3 §4–§6; D6 | payload per kind; `ops.*` rows | `PAYLOADS`, `vocab.py` enums mirrored by D3 CHECKs (generated in P0-F-4); operational sets partly unchecked ([DA-012](structure-and-invariants.md#da-012)) | — | payloads implemented |
| Policy, confidence parameters | D6 §7, D5 §6 | `policies.yaml`, rule-engine chains | split between policy file and prose ([DA-016](structure-and-invariants.md#da-016)) | — | target / proposed |
| Key scheme and derivations | D1 §10, D5 §5–§7 | `ent`/`stm`/`clm`/`alt`/`idg` keys; derived stored batches; golden items | no version of the scheme or of derivations ([DA-009](semantic-model-and-authority.md#da-009)) | — | implemented without versions |

## Strengths to keep

These bound later remedies:
- **One canonical JSON function** (NFC, sorted keys, floats refused) behind every key, digest and
  configuration hash (`core/canonical.py`).
- **Content-addressed renditions**, whose digest covers whole segments and leaves defaults out.
- **Frozen models** with `extra="forbid"`; absent fields are MISSING, never null; one form factory
  shares every non-anchored shape between the authored and stored forms.
- **One locator contract** that refuses ambiguity with typed reasons and candidates, prepared once
  per rendition (`LocatorIndex`).
- **Pure key functions** that receive schema facts and label rules as data (`KeySchema`,
  `LabelRules`); `core` imports no effects.
- **One enum per D3 CHECK list.** All 39 CHECK lists matched `vocab.py` and `SegmentKind` on
  2026-10-28 (contributor comparison script, not retained), and 0001 is planned to generate them.
- **Key tests with relational oracles** (equalities and inequalities over independently built
  renditions) and an independent parity fixture for the token form.
- **ADR-0017's division of ownership:** the pack owns domain vocabulary, Pydantic owns the core
  shapes.
