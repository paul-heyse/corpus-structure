"""Closed value sets: every list a migration-0001 CHECK names (D3; foundations §3.5).

One string enum per list, so the Pydantic types and the CHECKs (built from these in P0-F-4) cannot
disagree. A list several columns share is one enum; each class names the columns it serves. The
outcome codes at the end (`DropReason`, `FrameFailureReason`) are closed sets no CHECK names yet.
"""

from __future__ import annotations

from enum import StrEnum


class VersionState(StrEnum):
    """`meta.schema_version.state`, `meta.guideline_version.state`, `ops.policy_version.state`."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    REJECTED = "rejected"
    RETIRED = "retired"


class SchemaClassKind(StrEnum):
    """`meta.schema_class.kind`."""

    ENTITY = "entity"
    VALUE = "value"
    ABSTRACT = "abstract"


class EntityScope(StrEnum):
    """`meta.schema_class.scope`, `kb.entity.scope`."""

    GLOBAL = "global"
    LOCAL = "local"


class SlotRole(StrEnum):
    """`meta.schema_slot.role`."""

    PREDICATE = "predicate"
    QUALIFIER = "qualifier"
    IDENTITY = "identity"
    FIELD = "field"


class RuleGroup(StrEnum):
    """`meta.schema_rule.grp`."""

    RULES = "rules"
    GUIDELINE = "guideline"
    DERIVE = "derive"


class RuleSeverity(StrEnum):
    """`meta.schema_rule.severity`."""

    WARNING = "warning"
    ERROR = "error"


class MethodFamily(StrEnum):
    """`ops.method.family`."""

    INGEST = "ingest"
    PROFILE = "profile"
    EXTRACT = "extract"
    NORMALIZE = "normalize"
    RESOLVE = "resolve"
    CONSOLIDATE = "consolidate"
    VALIDATE = "validate"
    VERIFY = "verify"
    MEASURE = "measure"
    LLM = "llm"
    AGENT = "agent"
    HUMAN = "human"
    EVAL = "eval"


class MethodTier(StrEnum):
    """`ops.method_config.tier`."""

    DETERMINISTIC = "deterministic"
    ENCODER = "encoder"
    LOCAL_LLM = "local_llm"
    AGENT = "agent"
    HOSTED_LLM = "hosted_llm"
    HUMAN = "human"


class PolicyChain(StrEnum):
    """`ops.policy_rule.chain`."""

    PROPOSE = "propose"
    ESCALATE = "escalate"
    ADJUDICATE = "adjudicate"
    IDENTITY = "identity"
    GAPS = "gaps"


class RunKind(StrEnum):
    """`ops.run.kind`."""

    INGEST = "ingest"
    FULL = "full"
    SLICE = "slice"
    EXPERIMENT = "experiment"
    RESCORE = "rescore"
    GOLDEN = "golden"


class RunStatus(StrEnum):
    """`ops.run.status`."""

    CREATED = "created"
    RUNNING = "running"
    AWAITING_AGENT = "awaiting_agent"
    CONSOLIDATING = "consolidating"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SegmentParseStatus(StrEnum):
    """`kb.rendition.parse_status`, `kb.segment.parse_status`."""

    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


class EmbeddingTarget(StrEnum):
    """`kb.embedding.target_type`."""

    SEGMENT = "segment"
    ENTITY = "entity"
    ALIAS = "alias"


class TaskUnitType(StrEnum):
    """`ops.task.unit_type`."""

    DOCUMENT = "document"
    RENDITION = "rendition"
    SEGMENT = "segment"
    OBSERVATION = "observation"
    ENTITY = "entity"
    CLAIM = "claim"
    ALTERNATIVE_GROUP = "alternative_group"
    IDENTITY_GROUP = "identity_group"
    RUN = "run"
    GOLDEN_UNIT = "golden_unit"


class TaskStatus(StrEnum):
    """`ops.task.status`."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_AGENT = "awaiting_agent"
    DONE = "done"
    EMPTY = "empty"
    FAILED = "failed"
    SKIPPED = "skipped"
    REUSED = "reused"
    CANCELLED = "cancelled"


class ObservationKind(StrEnum):
    """`kb.observation.kind`."""

    AUTHOR_MARKUP = "author_markup"
    MENTION = "mention"
    RELATION = "relation"
    RECORD = "record"
    ATTRIBUTE = "attribute"
    CLASSIFICATION = "classification"
    VALUE = "value"
    SCOPE = "scope"
    LINK = "link"
    CLAIM_PROPOSAL = "claim_proposal"
    JUDGMENT = "judgment"
    VERIFICATION = "verification"


class ObservationOutcome(StrEnum):
    """`kb.observation.outcome`."""

    PRODUCED = "produced"
    EMPTY = "empty"
    FAILED = "failed"


class AliasKind(StrEnum):
    """`kb.entity_alias.alias_kind`."""

    LABEL = "label"
    SYMBOL = "symbol"
    ABBREVIATION = "abbreviation"
    TERM = "term"
    EXPRESSION = "expression"


class StatementRole(StrEnum):
    """`kb.claim.statement_role`."""

    PREMISE = "premise"
    CONCLUSION = "conclusion"
    DEFINIENS = "definiens"
    RESTRICTION = "restriction"
    EXAMPLE_VALUE = "example_value"


class ClaimStatus(StrEnum):
    """`kb.claim.status`."""

    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"
    UNSUPPORTED = "unsupported"


class Establishment(StrEnum):
    """`kb.claim.establishment`."""

    STATED = "stated"
    DERIVED = "derived"
    AGENT_ASSERTED = "agent_asserted"


class EvidenceRole(StrEnum):
    """`kb.claim_evidence.role`."""

    PRIMARY = "primary"
    SUPPORTING = "supporting"
    CONDITION = "condition"
    DEFINITION = "definition"


class LinkType(StrEnum):
    """`kb.claim_link.link_type`."""

    DERIVED_FROM = "derived_from"
    CONTRADICTS = "contradicts"
    EQUIVALENT_TO = "equivalent_to"
    ALTERNATIVE_OF = "alternative_of"
    REFINES = "refines"


class MeasurementScope(StrEnum):
    """`ops.measurement.scope_type`."""

    RUN = "run"
    RENDITION = "rendition"
    SEGMENT = "segment"
    ENTITY = "entity"
    CLAIM = "claim"
    PREDICATE = "predicate"
    CLASS = "class"
    STAGE = "stage"
    METHOD = "method"
    RULE = "rule"


class InterventionKind(StrEnum):
    """`ops.intervention.kind`."""

    EXTRACT = "extract"
    ADJUDICATE = "adjudicate"
    GOLDEN_WRITE = "golden_write"
    GOLDEN_ADJUDICATE = "golden_adjudicate"
    SCHEMA_PROPOSAL = "schema_proposal"
    GUIDELINE_CHANGE = "guideline_change"
    POLICY_PROPOSAL = "policy_proposal"
    EXPERIMENT_DECISION = "experiment_decision"
    PROMOTION = "promotion"
    DIRECTION = "direction"
    ACK = "ack"
    VETO = "veto"
    AUDIT = "audit"


class ExperimentDecision(StrEnum):
    """`ops.experiment.decision`."""

    PROMOTE = "promote"
    REJECT = "reject"
    INCONCLUSIVE = "inconclusive"


class DocumentSplit(StrEnum):
    """`eval.document_split.split`."""

    DEV = "dev"
    TEST = "test"
    RESERVED = "reserved"


class GoldenSplit(StrEnum):
    """`eval.golden_set.split`."""

    DEV = "dev"
    TEST = "test"


class GoldenUnitStatus(StrEnum):
    """`eval.golden_unit.status`."""

    DRAFT = "draft"
    ADJUDICATED = "adjudicated"
    STALE = "stale"
    RETIRED = "retired"


class GoldenPass(StrEnum):
    """`eval.golden_pass.pass`."""

    A = "a"
    B = "b"
    C = "c"


class GoldenItemType(StrEnum):
    """`eval.golden_item.item_type`."""

    ENTITY = "entity"
    STATEMENT = "statement"
    CLAIM = "claim"
    ALTERNATIVE = "alternative"
    UNSUPPORTED = "unsupported"


class AlignmentTarget(StrEnum):
    """`eval.alignment.target_type`."""

    ENTITY = "entity"
    CLAIM = "claim"


class AlignmentTier(StrEnum):
    """`eval.alignment.tier`."""

    NONE = "none"
    CORE = "core"
    FULL = "full"
    EVIDENCE = "evidence"


class ResultTier(StrEnum):
    """`eval.result.tier`."""

    CORE = "core"
    FULL = "full"
    EVIDENCE = "evidence"


# --- Outcome codes -----------------------------------------------------------------------------
#
# Hand-declared by P0-F-2c beside their consumers (coordinator decision 23). The names are final and
# the members provisional: M1 generates this module and takes these over with the same names and
# members. No CHECK names them yet; C1's `PassReport` counts by them.


class DropReason(StrEnum):
    """Why keying dropped a candidate or an alternative member (`core/keys.py`, D5 §5.2)."""

    UNKNOWN_PREDICATE = "unknown_predicate"  # the schema does not know the claim's predicate
    SEGMENT_NOT_ON_RENDITION = "segment_not_on_rendition"  # a segment key off this rendition
    OUTSIDE_UNRESOLVED = (
        "outside_unresolved"  # an `outside` statement consolidation has not resolved
    )
    UNKNOWN_REFERENCE = "unknown_reference"  # a reference to no candidate
    DROPPED_DEPENDENCY = "dropped_dependency"  # a reference to a candidate keying dropped
    UNKNOWN_CLAIM_REF = "unknown_claim_ref"  # a condition `claim` node naming no candidate claim
    UNKNOWN_IDENTITY_ENTITY = "unknown_identity_entity"  # an identity slot naming no entity
    IDENTITY_CYCLE = "identity_cycle"  # entity identity slots that reference each other
    CONDITION_CYCLE = "condition_cycle"  # claims whose conditions reference each other
    MALFORMED_QUALIFIER = "malformed_qualifier"  # a schema qualifier value that is no typed value


class FrameFailureReason(StrEnum):
    """Why a citation-frame entry did not resolve or re-address (`core/frame.py`, D1 §10.3)."""

    LOCATOR_SYNTAX = "locator_syntax"  # the locator string does not parse
    OTHER_PAGE = "other_page"  # the locator names another page than the rendition's
    LOCATOR_REFUSED = "locator_refused"  # it selects no segment, several, or fewer than its ordinal
    NOT_A_SENTENCE = "not_a_sentence"  # it selects a segment of another kind
    TEXT_DIFFERS = "text_differs"  # the sentence's text is not the recorded text
    NOT_IN_FRAME = "not_in_frame"  # a batch cites a sentence id its own frame lacks
    NOT_IN_PACKET = "not_in_packet"  # the served packet has no entry with that locator and text
