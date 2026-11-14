"""Provider-shaped retained token columns must reach their own assessment families.

Column layouts follow NativeEvidenceLayer.spacy/hanlp_sentence; expected linguistic
values below are independent controls, not derived from the assessment projection.
"""

from types import SimpleNamespace

import pytest
from evaluation_characterization_assessment_support import EXTENT, PIN, VIEW, case, frame

from corpus_structure.evaluate import operation_assessment
from corpus_structure.evaluate.characterization_assessment import evaluate_characterization
from corpus_structure.semantic import characterization_store


def assess_column(
    monkeypatch,
    *,
    family,
    provider="spacy",
    scheme=None,
    columns=None,
    expected=None,
    missing=(),
    failed=False,
):
    columns = (
        dict(
            lemma="run",
            pos="VERB",
            tag="VBZ",
            morphology=["Tense=Pres"],
            dependency="ROOT",
            native_head=0,
            head_index_base=0,
        )
        if columns is None
        else dict(columns)
    )
    for column in missing:
        columns.pop(column, None)
    scheme = scheme or (
        "spacy-token-columns-1" if provider == "spacy" else "hanlp-canonical-token-1"
    )
    token = dict(
        index=0,
        container="block",
        native_run=provider,
        text="runs",
        space=False,
        whitespace="",
        source_role="prose",
        **columns,
    )
    native_family = f"{provider}.tokens"
    columns_selected = (
        ("lemma", "pos", "tag", "morphology", "dependency")
        if provider == "spacy"
        else ("lemma", "pos", "dependency")
    )
    column_families = [f"{provider}.{name}" for name in columns_selected]
    coverage = [
        dict(
            family=value,
            availability="unavailable" if failed and value == family else "available",
            outcome="failed" if failed and value == family else "complete",
            examined=[dict(projection=EXTENT["projection"], start=0, end=20)],
        )
        for value in (native_family, *column_families)
    ]
    body = dict(
        source_scope={"source_view_ids": [23]},
        operation={"produced_families": [native_family, *column_families]},
        native_runs=[dict(local_id=provider, provider=provider)],
        occurrences=[
            dict(
                local_id="location",
                extents=[dict(EXTENT, start=0, end=4, text="runs", synthetic=False)],
            )
        ],
        annotations=[
            dict(
                local_id="block",
                kind="native.block",
                family=native_family,
                native_scheme=scheme,
                status="native_evidence",
                occurrences=["location"],
            ),
            dict(
                local_id="token",
                kind="native.token",
                family=native_family,
                native_scheme=scheme,
                status="native_evidence",
                native_token=token,
                occurrences=["location"],
            ),
        ],
        terms=[],
        memberships=[],
        roles=[],
        choices=[],
        coverage=coverage,
    )
    monkeypatch.setattr(
        characterization_store,
        "read_view",
        lambda *a, **k: SimpleNamespace(payload={"layers": [PIN], "active_layers": [PIN]}),
    )
    monkeypatch.setattr(
        characterization_store, "read_layer", lambda *a, **k: SimpleNamespace(payload=body)
    )
    monkeypatch.setattr(
        characterization_store,
        "read_layer_manifest",
        lambda *a, **k: SimpleNamespace(payload={"source_scope": body["source_scope"]}),
    )
    frozen = frame()
    independent = case(
        required_family=family,
        candidate_selector={"collection": "annotations", "value": {"kind": "native.token"}},
        alternatives=({"value": {"native_token": expected}},),
    )
    snapshot = [{"unit_id": 2, "pass_id": 3, "frame_id": 4}]
    monkeypatch.setattr(
        operation_assessment,
        "_call",
        lambda _conn, sql, **kw: SimpleNamespace(
            scalar_one=lambda: snapshot if "native_reference_snapshot" in sql else 99
        ),
    )
    monkeypatch.setattr(operation_assessment, "source_units", lambda *a: [{"source_view_id": 23}])
    monkeypatch.setattr(
        operation_assessment, "read_pass", lambda *a, **k: {"payload": {"cases": [independent]}}
    )
    result = evaluate_characterization(
        None,
        project_id="book",
        run_id=5,
        set_id=6,
        completed={"cut_id": 1},
        prepared=SimpleNamespace(release_id="release-1"),
        definition={"sampling": {"partition": "development"}},
        units=[
            {
                "id": 2,
                "unit_key": "chapter5",
                "source_view_id": 23,
                "context": [operation_assessment.encode_frame(frozen)],
            }
        ],
        frames={"chapter5": frozen},
        characterization_view=VIEW,
    )
    return result.result["units"][0]["cases"][0]


@pytest.mark.parametrize(
    ("family", "expected"),
    (
        ("spacy.pos", {"pos": "VERB"}),
        ("spacy.lemma", {"lemma": "run"}),
        ("spacy.dependency", {"dependency": "ROOT", "native_head": 0}),
    ),
)
def test_spacy_nested_columns_are_available_under_their_actual_family(
    monkeypatch, family, expected
):
    result = assess_column(monkeypatch, family=family, expected=expected)
    assert result["judgment"] == "supported"
    assert result["matched_references"][0]["local_id"] == "token"


@pytest.mark.parametrize(
    ("family", "expected"), (("spacy.pos", {"pos": "NOUN"}), ("spacy.lemma", {"lemma": "walk"}))
)
def test_wrong_linguistic_value_is_a_structure_error_not_a_false_missing_output(
    monkeypatch, family, expected
):
    result = assess_column(monkeypatch, family=family, expected=expected)
    assert result["judgment"] == "unsupported"
    assert result["error_category"] == "wrong_structure"
    assert result["candidate_references"][0]["local_id"] == "token"


def test_missing_native_pos_column_remains_unavailable(monkeypatch):
    result = assess_column(
        monkeypatch, family="spacy.pos", expected={"pos": "VERB"}, missing=("pos",)
    )
    assert result["judgment"] == "unassessed"
    assert result["error_category"] == "native_column_unavailable"


def test_failed_pos_family_is_not_credited_by_complete_token_coverage(monkeypatch):
    result = assess_column(monkeypatch, family="spacy.pos", expected={"pos": "VERB"}, failed=True)
    assert result["judgment"] == "unassessed"
    assert result["error_category"] == "prediction_scope_unavailable"


def test_hanlp_pos_uses_its_native_tag_column_without_scheme_relabeling(monkeypatch):
    result = assess_column(
        monkeypatch,
        family="hanlp.pos",
        provider="hanlp",
        columns={
            "tag": "VBZ",
            "lemma": "run",
            "dependency": "root",
            "native_head": 0,
            "head_index_base": 1,
        },
        expected={"tag": "VBZ"},
    )
    assert result["judgment"] == "supported"
    foreign = assess_column(
        monkeypatch,
        family="spacy.pos",
        provider="hanlp",
        columns={"tag": "VBZ", "lemma": "run"},
        expected={"tag": "VBZ"},
    )
    assert foreign["judgment"] == "unassessed"


def test_wrong_token_scheme_cannot_supply_a_pos_family(monkeypatch):
    result = assess_column(
        monkeypatch, family="spacy.pos", scheme="penn-treebank-pos", expected={"pos": "VERB"}
    )
    assert result["judgment"] != "supported"


def test_empty_but_present_morphology_is_not_a_missing_column(monkeypatch):
    result = assess_column(
        monkeypatch,
        family="spacy.morphology",
        columns={"morphology": []},
        expected={"morphology": []},
    )
    assert result["judgment"] == "supported"
