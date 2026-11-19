"""Typed projections of released source and interpretation vocabularies."""

from enum import StrEnum
from typing import Final, cast

from linkml_runtime.linkml_model.meta import PermissibleValue

from corpus_structure.model.compiled import running_model


class StatementKind(StrEnum):
    """What the source calls a statement (D1 §4.3). Lifecycle: schema_version."""

    DEFINITION = "definition"
    THEOREM = "theorem"
    PROPOSITION = "proposition"
    LEMMA = "lemma"
    COROLLARY = "corollary"
    PROOF = "proof"
    EXAMPLE = "example"
    EXERCISE = "exercise"
    SOLUTION = "solution"
    REMARK = "remark"
    CONVENTION = "convention"
    NOTATION = "notation"
    ASSUMPTION = "assumption"
    NARRATIVE = "narrative"


class ScopeExtent(StrEnum):
    """How far a supposition reaches beyond its statement. Lifecycle: static."""

    STATEMENT = "statement"
    SECTION = "section"
    DOCUMENT = "document"


class ParseOutcome(StrEnum):
    """The math grammar's parse outcome for a formula or set value (D4 M11). Lifecycle: static."""

    OK = "ok"
    PARTIAL = "partial"
    AMBIGUOUS = "ambiguous"
    FAILED = "failed"


class SegmentKind(StrEnum):
    """The kinds of segment of a rendition (D1 §3.2), with their member properties. Lifecycle:
    static.
    """

    DOCUMENT = "document"
    SECTION = "section"
    UNIT = "unit"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    DETAILS = "details"
    MATH_DISPLAY = "math_display"
    MATH_INLINE = "math_inline"
    HEADING = "heading"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    FIGURE = "figure"
    SENTENCE = "sentence"
    EMAIL_MESSAGE = "email_message"
    QUOTED_BLOCK = "quoted_block"
    SIGNATURE = "signature"


class DelimitingStatus(StrEnum):
    """How cleanly a segment or rendition was delimited: one definition for kb.segment and
    kb.rendition parse_status (D1 §3.2), replacing evidence.ParseStatus and SegmentParseStatus.
    Lifecycle: static.
    """

    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


class CaseRule(StrEnum):
    """The values of ci:case: the case policy of a string-ranged slot or class label. Lifecycle:
    static.
    """

    FOLD = "fold"
    PRESERVE = "preserve"


class ObservationKind(StrEnum):
    """`kb.observation.kind`. Lifecycle: static."""

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
    """`kb.observation.outcome`. Lifecycle: static."""

    PRODUCED = "produced"
    EMPTY = "empty"
    FAILED = "failed"


class MeasurementScope(StrEnum):
    """Current native measurement subject kinds. Lifecycle: static."""

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
    SOURCE_VIEW = "source_view"


class DocumentSplit(StrEnum):
    """`eval.document_split.split`. Lifecycle: static."""

    DEV = "dev"
    TEST = "test"
    RESERVED = "reserved"


class MathKind(StrEnum):
    """The typed start symbol of the math grammar that read a value's span (ValuePayload.math_kind,
    M11). Lifecycle: static.
    """

    FORMULA = "formula"
    RELATION = "relation"
    MEMBERSHIP = "membership"
    SET = "set"
    LIST = "list"


class UnitFeatureKind(StrEnum):
    """The unit-feature vocabulary that guideline sections declare for by_unit (D2 §10). Lifecycle:
    static.
    """

    SEGMENT_KIND = "segment_kind"
    STATEMENT_KIND = "statement_kind"
    CLAIM_BEARING = "claim_bearing"


SECTION_LIKE: Final[frozenset[SegmentKind]] = frozenset(
    {
        SegmentKind.DOCUMENT,
        SegmentKind.SECTION,
    }
)

ANNOTATION_UNIT: Final[frozenset[SegmentKind]] = frozenset(
    {
        SegmentKind.UNIT,
        SegmentKind.EMAIL_MESSAGE,
    }
)

TOP_LEVEL_ANNOTATION_UNIT: Final[frozenset[SegmentKind]] = frozenset(
    {
        SegmentKind.PARAGRAPH,
    }
)

SECTION_LABEL: Final[frozenset[SegmentKind]] = frozenset(
    {
        SegmentKind.HEADING,
    }
)


def _check_declarations():
    model = running_model()
    vocabularies = (
        (CaseRule, "source-vocabularies.yaml", "CaseRule"),
        (DelimitingStatus, "source-vocabularies.yaml", "DelimitingStatus"),
        (DocumentSplit, "source-vocabularies.yaml", "DocumentSplit"),
        (MathKind, "source-vocabularies.yaml", "MathKind"),
        (MeasurementScope, "observations.yaml", "SourceMeasurementScope"),
        (ObservationKind, "source-vocabularies.yaml", "ObservationKind"),
        (ObservationOutcome, "source-vocabularies.yaml", "ObservationOutcome"),
        (ParseOutcome, "source-vocabularies.yaml", "ParseOutcome"),
        (ScopeExtent, "core.yaml", "ScopeExtent"),
        (SegmentKind, "source-vocabularies.yaml", "SegmentKind"),
        (StatementKind, "core.yaml", "StatementKind"),
        (UnitFeatureKind, "source-vocabularies.yaml", "UnitFeatureKind"),
    )
    for value_type, source, name in vocabularies:
        declaration = model.view(source).get_enum(name)
        if declaration is None or set(declaration.permissible_values or {}) != {
            item.value for item in value_type
        }:
            raise ValueError(name + " differs from the released vocabulary")
    declaration = model.view("source-vocabularies.yaml").get_enum("SegmentKind")
    assert declaration is not None
    members = cast(dict[str, PermissibleValue], declaration.permissible_values)
    properties = (
        ("annotation_unit", ANNOTATION_UNIT),
        ("section_label", SECTION_LABEL),
        ("section_like", SECTION_LIKE),
        ("top_level_annotation_unit", TOP_LEVEL_ANNOTATION_UNIT),
    )
    for name, actual in properties:
        expected = {key for key, member in members.items() if name in (member.in_subset or ())}
        if expected != {member.value for member in actual}:
            raise ValueError(name + " differs from released member properties")


_check_declarations()
