"""Real preparation/assembly with controlled decoder readings; no GLiNER provider claim."""

import json
from functools import cache
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import JsonValue

from corpus_structure.core.method import SourceViewRef, UnitRef
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods import m1_source
from corpus_structure.methods.gliner import GlinerPreparation, GlinerReport
from corpus_structure.methods.gliner_worker import GlinerWorkerError
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView

ROOT = Path(__file__).resolve().parents[4]


def detail_object(value: JsonValue) -> dict[str, JsonValue]:
    assert isinstance(value, dict)
    return value


def detail_objects(value: JsonValue) -> tuple[dict[str, JsonValue], ...]:
    assert isinstance(value, list)
    return tuple(detail_object(item) for item in value)


@cache
def release():
    model = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic"
    return prepare_release(
        observation_inputs(
            SourceBundle(
                "statistics_semantic",
                (
                    SourceArtifact(
                        "statistics_semantic",
                        (ROOT / "domains/statistics/semantic.yaml").read_bytes(),
                    ),
                    SourceArtifact("semantic_core", (model / "core.yaml").read_bytes()),
                ),
            )
        )
    )


def view():
    text = "Mean is average."
    nodes = (
        dict(self_ref="#/groups/1", label="section"),
        dict(self_ref="#/texts/1", label="text", text=text),
    )
    pieces = (dict(kind="native_text", item_ref="#/texts/1", start=0, end=len(text)),)
    projection = dict(
        text=text, pieces=pieces, items=[n["self_ref"] for n in nodes], ancestors=[], health={}
    )
    ref = SourceViewRef(
        7,
        "source:7",
        1,
        ProductReference(23, "integrated", "a" * 64),
        "#/groups/1",
        "descendants",
        sha256(canonical_bytes(projection)).hexdigest(),
        "c" * 64,
    )
    return PreparedSourceView(ref, text, pieces, nodes, (), {})


class ControlledDecoder:
    """A unit-fixture report source, not actual model inference."""

    def __init__(self, mode):
        self.mode = mode
        self.calls = []

    def extract(self, pack, inputs, *, threshold, check_active):
        check_active()
        self.calls.append((pack, inputs))
        if self.mode == "failed":
            raise GlinerWorkerError("controlled worker failure")
        family = next(iter(json.loads(pack.declaration_json)["structures"]))
        raw = {family: []}
        if self.mode == "definition" and family == "definition":
            raw[family] = [
                dict(
                    term=dict(start=0, end=4, text="Mean"),
                    defining_text=dict(start=8, end=15, text="average"),
                )
            ]
        (item,) = inputs
        return (
            GlinerReport(
                item.context_id,
                item.context_digest,
                "controlled-computation",
                "controlled-profile",
                pack.fingerprint,
                GlinerPreparation(item.text, "", 4, 6, len(item.text.encode())),
                json.dumps(raw),
                "{}",
                0,
                False,
            ),
        )


def owned_reader(source):
    """Persisted-operation-shaped fixture with actual local linguistic columns."""
    from corpus_structure.methods.m1_annotations import M1Annotations
    from corpus_structure.orchestrate.m1 import registry
    from corpus_structure.semantic.source_contexts import RetrievalOutcome, SourceContextRead

    reader = SimpleNamespace(prepared=release(), source_view=lambda _: source)
    producer = M1Annotations()
    cfg = registry(ROOT / "domains/statistics").overlay(producer.name, "default")
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, source.ref.id, source.ref.key))
    (product,) = producer.run(
        (unit,), cfg, SimpleNamespace(reader=reader, check_active=lambda: None)
    )
    reader.source_result = lambda *_: dict(
        method=producer.name,
        input_hash="controlled-upstream-input",
        configuration_hash="controlled-upstream-configuration",
        outcome=product.outcome.value,
        parse_detail=product.parse_detail,
    )
    reader.context_sources = lambda *_args, **_kwargs: SourceContextRead(
        (), (), "a" * 64, RetrievalOutcome.NO_MATCH, "controlled empty related-source universe"
    )
    reader.source_context_membership = lambda _: "a" * 64
    return reader


def test_owned_annotation_consumer_reuses_columns_and_refuses_profile_or_source_drift(monkeypatch):
    from dataclasses import replace

    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods import source_preparation
    from corpus_structure.methods.m1_annotations import consume_annotations

    source = view()
    reader = owned_reader(source)
    products, errors, _ = consume_annotations(reader, source, AnnotationProfile())
    assert products and not errors

    def must_not_recompute(*_, **__):
        raise AssertionError("consumer must not rerun source layout or annotation pipeline")

    monkeypatch.setattr(source_preparation, "pipeline", must_not_recompute)
    monkeypatch.setattr(source_preparation, "annotate", must_not_recompute)
    result = source_preparation.prepare_source(source, persisted_annotations=products)
    assert result.annotations == products
    assert result.annotations[0].tokens[0].start == 0
    assert result.annotations[0].sentences[-1].end == 16
    changed_profile = AnnotationProfile(SentenceConfig(exclude=("ner",), batch_size=1))
    with pytest.raises(ValueError, match="source/profile"):
        consume_annotations(reader, source, changed_profile)
    changed_source = replace(source, ref=replace(source.ref, recipe_digest="d" * 64))
    with pytest.raises(ValueError, match="source binding"):
        consume_annotations(reader, changed_source, AnnotationProfile())


def test_missing_annotation_operation_does_not_fall_back_to_inference():
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.m1_annotations import consume_annotations

    with pytest.raises(ValueError, match="no source result"):
        consume_annotations(
            SimpleNamespace(source_result=lambda *_: None), view(), AnnotationProfile()
        )


def test_context_relationship_diagnostics_cross_the_source_report_boundary(monkeypatch):
    from dataclasses import replace

    from corpus_structure.orchestrate.m1 import registry
    from corpus_structure.semantic.observations import source_python, source_value
    from corpus_structure.semantic.source_contexts import ContextRelationship

    source = view()
    method = m1_source.M1Candidates()
    reader = owned_reader(source)
    prepare = m1_source.prepare_source

    def with_related_diagnostic(*args, **kwargs):
        prepared = prepare(*args, **kwargs)
        return replace(
            prepared,
            selections=tuple(
                replace(row, relationships=((8, ContextRelationship.NEIGHBOR, "nearby unit"),))
                for row in prepared.selections
            ),
            annotation_errors=("controlled unavailable annotation",),
        )

    monkeypatch.setattr(m1_source, "prepare_source", with_related_diagnostic)
    cfg = registry(ROOT / "domains/statistics").overlay(method.name, "default")
    (result,) = method.run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, "source:7")),),
        cfg,
        SimpleNamespace(reader=reader, check_active=lambda: None),
    )
    decoded = source_python(source_value(result.parse_detail))
    assert decoded["contexts"][0]["relationships"] == [[8, "neighbor", "nearby unit"]]
    assert result.outcome == ObservationOutcome.FAILED


@pytest.mark.parametrize("mode", ["definition", "empty", "failed"])
def test_producer_keeps_candidates_empty_denominator_and_failure_dispositions(monkeypatch, mode):
    source = view()
    method = m1_source.M1Candidates()
    worker = ControlledDecoder(mode)
    monkeypatch.setattr(method, "_resident", lambda profile: worker)
    from corpus_structure.orchestrate.m1 import registry

    cfg = registry(ROOT / "domains/statistics").overlay(method.name, "default")
    checks = []
    context = SimpleNamespace(
        reader=owned_reader(source),
        check_active=lambda: checks.append("checked"),
    )
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, "source:7"))
    (result,) = method.run((unit,), cfg, context)
    details = result.parse_detail
    assert details is not None
    regions = details["regions"]
    assert isinstance(regions, list)
    assert checks and len(regions) == 2
    for report in detail_objects(details["reports"]):
        if "report" in report:
            reading = detail_object(report["report"])
            preparation = detail_object(reading["preparation"])
            assert "consumed_text" not in preparation
            text_digest = preparation["consumed_text_sha256"]
            assert isinstance(text_digest, str) and len(text_digest) == 64
            profile_ref = reading["effective_profile_ref"]
            assert isinstance(profile_ref, str)
            assert profile_ref in detail_object(details["effective_profiles"])
    if mode == "definition":
        assert result.records is not None
        assert result.outcome == ObservationOutcome.PRODUCED and len(result.records) == 1
        record = result.records[0]
        fields = {field["role"]: field for field in record["fields"]}
        assert record["standing"] == "candidate"
        assert fields["term"]["original"] == "Mean"
        assert fields["defining_text"]["original"] == "average"
        assert fields["scope"]["state"] == "present"
        assert fields["alias"]["state"] == "unresolved"
        assert len(worker.calls) == 3
    elif mode == "empty":
        assert result.outcome == ObservationOutcome.EMPTY and result.records == ()
        assert [row["outcome"] for row in detail_objects(details["execution"])] == ["complete"] * 3
        assert len(worker.calls) == 3
    else:
        assert result.outcome == ObservationOutcome.FAILED and result.records is None
        assert [row["outcome"] for row in detail_objects(details["execution"])] == [
            "failed",
            "not_run",
            "not_run",
        ]
        assert len(worker.calls) == 1


def test_native_table_geometry_produces_zero_and_inspected_blank_without_decoder_output(
    monkeypatch,
):
    source = view()

    def cell(text, row, col, **flags):
        return dict(
            text=text,
            start_row_offset_idx=row,
            end_row_offset_idx=row + 1,
            start_col_offset_idx=col,
            end_col_offset_idx=col + 1,
            **flags,
        )

    cells = (
        cell("Pressure", 0, 1, column_header=True),
        cell("A", 1, 0, row_header=True),
        cell("0", 1, 1),
        cell("B", 2, 0, row_header=True),
        cell("", 2, 1),
    )
    nodes = (
        dict(self_ref="#/groups/1", label="section"),
        dict(self_ref="#/tables/1", label="table", data=dict(table_cells=cells)),
    )
    text = "Pressure\nA\n0\nB"
    pieces = []
    for index, (a, b) in enumerate(((0, 8), (9, 10), (11, 12), (13, 14))):
        if a:
            pieces.append(dict(kind="synthetic_separator", start=a - 1, end=a))
        pieces.append(
            dict(
                kind="native_text",
                item_ref="#/tables/1",
                cell_index=index,
                source_field="cell_text",
                start=a,
                end=b,
            )
        )
    projection = dict(
        text=text, pieces=pieces, items=[n["self_ref"] for n in nodes], ancestors=[], health={}
    )
    from dataclasses import replace

    source = replace(
        source,
        text=text,
        items=nodes,
        pieces=tuple(pieces),
        ref=replace(source.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
    )
    method = m1_source.M1Candidates()
    worker = ControlledDecoder("empty")
    monkeypatch.setattr(method, "_resident", lambda profile: worker)
    from corpus_structure.orchestrate.m1 import registry

    cfg = registry(ROOT / "domains/statistics").overlay(method.name, "default")
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, "source:7"))
    (result,) = method.run(
        (unit,),
        cfg,
        SimpleNamespace(
            reader=owned_reader(source),
            check_active=lambda: None,
        ),
    )
    assert result.records is not None
    assert len(worker.calls) == 1 and len(result.records) == 2
    zero, blank = ({f["role"]: f for f in row["fields"]} for row in result.records)
    assert zero["cell_value"]["original"] == "0"
    assert zero["row_identity"]["original"] == "A"
    assert zero["header_path"]["original"] == "Pressure"
    assert blank["cell_value"]["state"] == "unstated"
    assert blank["note"]["state"] == "unresolved"
    details = result.parse_detail
    assert details is not None
    execution = detail_objects(details["execution"])
    assert execution[0]["outcome"] == "partial"
    assert execution[0]["reason"] == "candidate output"


def test_dense_native_structure_emits_only_the_explicit_context_target_cells(monkeypatch):
    from corpus_structure.methods import source_preparation

    from .test_m1_source_preparation import dense_table_source

    source = dense_table_source()
    prepared = source_preparation.prepare_source(
        source, persisted_annotations=(), max_chars=256, max_pieces=64
    )
    selections = [s for s in prepared.selections if s.families == ("table",)]
    assert len(selections) == 30
    captured = []

    def native_groups(context, **kwargs):
        captured.append(kwargs)
        return ()

    monkeypatch.setattr(
        "corpus_structure.methods.record_assembly.native_table_groups", native_groups
    )
    # Preparation owns geometry; structural consumption must not rescan/infer all
    # cell paths for every row context or manufacture candidates from other rows.
    monkeypatch.setattr(
        m1_source, "native_table_geometry", lambda *_: pytest.fail("geometry repeated")
    )
    for selection in selections:
        assert selection.table_targets is not None
        context = selection.context(
            prepared.source, preparation=prepared.preparation, max_chars=256, max_pieces=64
        )
        m1_source._structural_groups(source, selection, context)
        assert captured[-1]["cells"] == tuple(t.cell_index for t in selection.table_targets)
        assert captured[-1]["row_paths"] == {
            t.cell_index: t.row_path for t in selection.table_targets
        }
        assert captured[-1]["header_paths"] == {
            t.cell_index: t.header_path for t in selection.table_targets
        }
        assert len(captured[-1]["cells"]) == 9
    assert len({index for group in captured for index in group["cells"]}) == 270
