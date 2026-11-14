"""Shared controlled inputs and builders for record contracts support."""

from functools import cache
from pathlib import Path

from corpus_structure.semantic import (
    PreparationProfile,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    bind_record_candidates,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)

ROOT = Path(__file__).resolve().parents[4]


MODEL = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic"


PIN = {
    "source": "source:table",
    "native_product_task_id": 23,
    "product_key": "organized",
    "product_digest": "a" * 64,
    "projection_digest": "b" * 64,
    "recipe_digest": "c" * 64,
    "source_view_id": 7,
}


@cache
def release_inputs():
    bundle = observation_inputs(
        SourceBundle(
            "statistics_semantic",
            (
                SourceArtifact(
                    "statistics_semantic", (ROOT / "domains/statistics/semantic.yaml").read_bytes()
                ),
                SourceArtifact("semantic_core", (MODEL / "core.yaml").read_bytes()),
                SourceArtifact(
                    "statistics_terminology",
                    (ROOT / "domains/statistics/terminology.yaml").read_bytes(),
                ),
            ),
        )
    )
    profile = PreparationProfile()
    return bundle, profile, prepare_release(bundle, profile=profile)


def anchor(pointer, text=None, start=None, end=None, *, space="native", precision="exact"):
    row = {"pin": dict(PIN), "space": space, "pointer": pointer, "precision": precision}
    if text is not None:
        row["source_piece"] = text
    if start is not None:
        row.update(start=start, end=end)
    row["anchor_id"] = anchor_identity(row)
    return row


def field(
    role,
    value=None,
    *,
    kind="literal",
    state="present",
    evidence=(),
    original=None,
    originals=None,
    meaning=True,
):
    row = {
        "role": role,
        "kind": kind,
        "state": state,
        "meaning_changing": meaning,
        "evidence_status": "available" if evidence else "unavailable",
        "evidence_sets": tuple(evidence),
    }
    if value is not None:
        row["value"] = value
    if original is not None:
        row["original"] = original
    if originals is not None:
        row["original_pieces"] = tuple(originals)
    if state != "present":
        row["reason"] = "not stated in the explicitly inspected source"
    return row


def finish(record):
    record["record_id"] = record_identity(release_inputs()[2].release_id, record)
    record["interpretation_id"] = interpretation_identity(record)
    return record


def table_record():
    # Two repeated numeric strings have independently specified positions/cells.
    pieces = {
        "table": anchor("#/tables/0", precision="item"),
        "cell": anchor("#/tables/0/cells/3", precision="item"),
        "row_label": anchor("#/tables/0/cells/0", "Group A", 0, 7),
        "parent": anchor("#/tables/0/cells/1", "Population", 0, 10),
        "child": anchor("#/tables/0/cells/2", "mean", 0, 4),
        "value": anchor("#/tables/0/cells/3", "12", 0, 2),
        "note": anchor("#/texts/4", "hypothetical", 0, 12),
    }
    memberships = {
        "table": ("table",),
        "cell": ("cell",),
        "row_label": ("row_label",),
        "header_path": ("parent", "child"),
        "cell_value": ("value",),
        "note": ("note",),
    }
    sets = []
    by_role = {}
    for role, names in memberships.items():
        evidence = {
            "role": role,
            "ordering": "ordered",
            "usage": "native" if role in {"table", "cell"} else "literal",
            "anchors": tuple(pieces[name]["anchor_id"] for name in names),
        }
        evidence["set_id"] = evidence_set_identity(evidence)
        sets.append(evidence)
        by_role[role] = (evidence["set_id"],)
    fields = (
        field(
            "table",
            {"kind": "native_location", "pointer": "#/tables/0"},
            kind="native",
            evidence=by_role["table"],
        ),
        field(
            "cell",
            {"kind": "native_location", "pointer": "#/tables/0/cells/3"},
            kind="native",
            evidence=by_role["cell"],
        ),
        field(
            "row_label",
            {"kind": "text", "text": "Group A"},
            original="Group A",
            evidence=by_role["row_label"],
        ),
        field(
            "header_path",
            {"kind": "text_sequence", "items": ("Population", "mean")},
            originals=("Population", "mean"),
            evidence=by_role["header_path"],
        ),
        field(
            "cell_value",
            {"kind": "decimal", "lexical": "12"},
            original="12",
            evidence=by_role["cell_value"],
        ),
        field(
            "note",
            {"kind": "text", "text": "hypothetical"},
            original="hypothetical",
            evidence=by_role["note"],
        ),
        field("unit", state="unstated"),
        field("caption", state="inapplicable"),
    )
    record = {
        "contract": "TableRecordFields",
        "family": "table",
        "occurrence_recipe": "source-anchor-membership-1",
        "pin": dict(PIN),
        "occurrence_anchors": (pieces["cell"]["anchor_id"],),
        "standing": "accepted",
        "policy_version": "reading-1",
        "fields": fields,
        "anchors": tuple(pieces.values()),
        "evidence_sets": tuple(sets),
        "computation_dependencies": ("observation:rejected-header-alternative",),
        "assertion_members": ("fact:value", "fact:condition"),
    }
    contexts = tuple(
        {"pin": dict(PIN), "space": "native", "pointer": pointer, "text": text}
        for pointer, text in (
            ("#/tables/0/cells/0", "Group A"),
            ("#/tables/0/cells/1", "Population"),
            ("#/tables/0/cells/2", "mean"),
            ("#/tables/0/cells/3", "12"),
            ("#/texts/4", "hypothetical"),
        )
    )
    return finish(record), contexts


def bind(record, contexts=(), release=None):
    return bind_record_candidates(
        release or release_inputs()[2],
        source=PIN["source"],
        records=(record,),
        coordinate_texts=contexts,
    )[0]


def record_from_fields(contract, family, specifications, absent):
    """Fixture coordinates and role expectations are authored independently below."""
    anchors, sets, fields, contexts = [], [], [], []
    for role, kind, pointer, space, text, value in specifications:
        piece = anchor(
            pointer,
            text,
            0 if text is not None else None,
            len(text) if text is not None else None,
            space=space,
            precision="exact" if text is not None else "item",
        )
        anchors.append(piece)
        evidence = {
            "role": role,
            "ordering": "ordered",
            "usage": "classification_cue" if kind == "classified" else kind,
            "anchors": (piece["anchor_id"],),
        }
        evidence["set_id"] = evidence_set_identity(evidence)
        sets.append(evidence)
        fields.append(
            field(
                role,
                value,
                kind=kind,
                evidence=(evidence["set_id"],),
                original=text if kind == "literal" else None,
            )
        )
        if text is not None:
            contexts.append({"pin": dict(PIN), "space": space, "pointer": pointer, "text": text})
    for role, kind, meaning in absent:
        fields.append(field(role, state="unstated", kind=kind, meaning=meaning))
    return finish(
        {
            "contract": contract,
            "family": family,
            "occurrence_recipe": "source-anchor-membership-1",
            "pin": dict(PIN),
            "occurrence_anchors": (anchors[0]["anchor_id"],),
            "standing": "accepted",
            "policy_version": "reading-1",
            "fields": tuple(fields),
            "anchors": tuple(anchors),
            "evidence_sets": tuple(sets),
        }
    ), tuple(contexts)


def formula_record():
    return record_from_fields(
        "FormulaRecordFields",
        "formula_context",
        (
            (
                "formula",
                "literal",
                "#/formulas/2",
                "recognized_text",
                "f(x)=x²",
                {"kind": "text", "text": "f(x)=x²"},
            ),
            (
                "scope",
                "native",
                "#/groups/3",
                "native",
                None,
                {"kind": "native_location", "pointer": "#/groups/3"},
            ),
            (
                "symbol",
                "literal",
                "#/texts/8",
                "selected_projection",
                "x",
                {"kind": "text", "text": "x"},
            ),
            (
                "meaning",
                "literal",
                "#/texts/9",
                "selected_projection",
                "input value",
                {"kind": "text", "text": "input value"},
            ),
            (
                "domain",
                "literal",
                "#/texts/10",
                "selected_projection",
                "real",
                {"kind": "text", "text": "real"},
            ),
        ),
        (("assumption", "literal", True),),
    )


def measurement_record():
    return record_from_fields(
        "MeasurementRecordFields",
        "measurement",
        (
            (
                "referent",
                "literal",
                "#/texts/1",
                "native",
                "bottle",
                {"kind": "text", "text": "bottle"},
            ),
            (
                "property",
                "literal",
                "#/texts/2",
                "native",
                "volume",
                {"kind": "text", "text": "volume"},
            ),
            (
                "original_value",
                "literal",
                "#/texts/3",
                "native",
                "1.234567890123456789e-400",
                {"kind": "decimal", "lexical": "1.234567890123456789e-400"},
            ),
            (
                "value_role",
                "classified",
                "#/texts/4",
                "native",
                "average",
                {"kind": "measurement_value_role", "label": "mean"},
            ),
        ),
        (
            ("unit", "literal", True),
            ("comparator", "literal", True),
            ("uncertainty", "literal", True),
            ("reference_quantity", "literal", True),
            ("condition", "literal", True),
            ("normalized_value", "normalized", False),
        ),
    )
