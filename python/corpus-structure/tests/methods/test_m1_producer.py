"""Real preparation/assembly with controlled decoder readings; no GLiNER provider claim."""

import json
from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods import m1_source
from corpus_structure.methods.gliner import GlinerPreparation, GlinerReport
from corpus_structure.methods.gliner_worker import GlinerWorkerError
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_views import PreparedSourceView
from methods.m1_producer_support import (
    ROOT as ROOT,
)
from methods.m1_producer_support import (
    ControlledDecoder as ControlledDecoder,
)
from methods.m1_producer_support import (
    detail_object as detail_object,
)
from methods.m1_producer_support import (
    detail_objects as detail_objects,
)
from methods.m1_producer_support import (
    owned_reader as owned_reader,
)
from methods.m1_producer_support import (
    release as release,
)
from methods.m1_producer_support import (
    view as view,
)


def test_local_schema_and_retained_lower_rule_products_survive_empty_record_outputs(monkeypatch):
    """Real source preparation and native annotation restoration; controlled decoder only."""
    from corpus_structure.orchestrate.m1 import registry

    class LocalDecoder(ControlledDecoder):
        def extract(self, pack, inputs, *, threshold, check_active):
            if pack.version != "native-local-v1":
                return super().extract(pack, inputs, threshold=threshold, check_active=check_active)
            (item,) = inputs
            return (
                GlinerReport(
                    item.context_id,
                    item.context_digest,
                    "controlled-local",
                    "fixture",
                    pack.fingerprint,
                    GlinerPreparation(item.text, "", 4, 4, len(item.text.encode())),
                    json.dumps({"entities": {"term": [dict(text="Mean", start=0, end=4)]}}),
                    "{}",
                    0,
                    False,
                ),
            )

    source = view()
    method = m1_source.M1Candidates()
    monkeypatch.setattr(
        method, "_resident", lambda _, *, providers, native_profile: LocalDecoder("empty")
    )
    cfg = (
        registry(ROOT / "domains/statistics")
        .overlay(method.name, "default")
        .model_copy(
            update={
                "local_schema": {"entities": ["term"]},
                "annotation_rules": (
                    m1_source.AnnotationRule(
                        rule="copula",
                        variant="is",
                        mechanism="token",
                        pattern=[{"LOWER": "is"}],
                        bindings={"cue": {"node": "match"}},
                    ),
                ),
            }
        )
    )
    (result,) = method.run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, "source:7")),),
        cfg,
        SimpleNamespace(
            reader=owned_reader(
                source,
                annotation_rules=m1_source.M1Config.model_validate(
                    cfg.model_dump()
                ).annotation_rules,
            ),
            check_active=lambda: None,
        ),
    )
    assert result.contributions is not None
    types = {row["semantic_type"] for row in result.contributions}
    assert {"source_rule.copula", "entity.term"} <= types
    assert "source_role.cue" in types
    (role,) = [row for row in result.contributions if row["semantic_type"] == "source_role.cue"]
    assert role["component"]["kind"] == "located_role"
    assert role["component"]["roles"] == (
        dict(
            role="cue",
            anchor_ids=tuple(a["anchor_id"] for a in role["anchors"]),
            head_token=1,
            expansion="exact",
            outcome="complete",
        ),
    )
    assert [(a["start"], a["end"], a["source_piece"]) for a in role["anchors"]] == [(5, 7, "is")]
    from methods.record_assembly_support import release

    release().validate_python("SourceContribution", role)
    assert role["component"]["interpretation"] == "unassessed"
    assert role["standing"] == "retained_private"
    assert result.contribution_operations is not None
    assert all(
        op["operation_version"] == "retained-annotation-rules-2"
        for op in result.contribution_operations
        if op["question"] == "propose_named_source_roles_from_retained_annotations"
    )
    assert not result.records
    assert result.parse_detail is not None and result.parse_detail["local_reports"]


def test_generic_role_guidance_is_an_explicit_pack_identity_with_configured_precedence():
    from corpus_structure.methods.m1_source import configured_packs
    from corpus_structure.orchestrate.m1 import registry
    from methods.record_assembly_support import release

    method = m1_source.M1Candidates()
    cfg = m1_source.M1Config.model_validate(registry(ROOT / "domains/statistics").overlay(method.name, "default"))
    prepared = release()
    baseline = configured_packs(prepared, cfg)
    guided = configured_packs(prepared, cfg, generic_role_guidance=True)

    baseline_assertion = json.loads(baseline["assertion"].declaration_json)["structures"][
        "assertion"
    ]
    guided_assertion = json.loads(guided["assertion"].declaration_json)["structures"]["assertion"]
    baseline_fields = {field["name"]: field for field in baseline_assertion["fields"]}
    guided_fields = {field["name"]: field for field in guided_assertion["fields"]}
    assert "generic_role_guidance" not in cfg.model_dump(mode="json")
    assert not any("description" in field for field in baseline_fields.values())
    assert guided["assertion"].fingerprint != baseline["assertion"].fingerprint
    assert "same local occurrence" in guided_fields["subject"]["description"]
    assert "same assertion" not in guided_fields["subject"]["description"]

    described_cfg = cfg.model_copy(
        update={
            "pack_descriptions": {"assertion": {"subject": "explicit reviewer wording"}},
        }
    )
    described = configured_packs(prepared, described_cfg, generic_role_guidance=True)
    described_fields = json.loads(described["assertion"].declaration_json)["structures"][
        "assertion"
    ]["fields"]
    described_fields = {field["name"]: field for field in described_fields}
    assert described_fields["subject"]["description"] == "explicit reviewer wording"
    assert "same local occurrence" in described_fields["object"]["description"]


def test_generic_role_guidance_runs_only_through_explicit_detached_helper(monkeypatch):
    from corpus_structure.orchestrate.m1 import registry

    source = view()
    method = m1_source.M1Candidates()
    monkeypatch.setattr(
        method, "_resident", lambda _, *, providers, native_profile: ControlledDecoder("empty")
    )
    cfg = m1_source.M1Config.model_validate(registry(ROOT / "domains/statistics").overlay(method.name, "default"))
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, source.ref.id, source.ref.key))
    ctx = SimpleNamespace(reader=owned_reader(source), check_active=lambda: None)

    (baseline,) = method.run((unit,), cfg, ctx)
    (guided,) = method.run_generic_role_guidance_comparison((unit,), cfg, ctx)

    assert baseline.parse_detail is not None and guided.parse_detail is not None
    assert "comparison_arm" not in baseline.parse_detail
    assert guided.parse_detail["comparison_arm"] == "generic-source-role-guidance-1"
    assert "generic_role_guidance" not in cfg.model_dump(mode="json")


@pytest.mark.parametrize("fatal", [False, True])
def test_request_limit_continues_independent_context_but_worker_fault_fences_it(monkeypatch, fatal):
    from dataclasses import replace

    from corpus_structure.methods.gliner import GlinerRefused
    from corpus_structure.orchestrate.m1 import registry
    from corpus_structure.semantic.contributions import bind_contributions

    first, second = "Mean is average.", "Other is distinct."
    text = first + "\n" + second
    nodes = (
        dict(self_ref="#/groups/1", label="section"),
        dict(self_ref="#/texts/1", label="text", text=first),
        dict(self_ref="#/texts/2", label="text", text=second),
    )
    pieces = (
        dict(kind="native_text", item_ref="#/texts/1", start=0, end=len(first)),
        dict(kind="synthetic_separator", start=len(first), end=len(first) + 1),
        dict(kind="native_text", item_ref="#/texts/2", start=len(first) + 1, end=len(text)),
    )
    projection = dict(
        text=text, pieces=pieces, items=[n["self_ref"] for n in nodes], ancestors=[], health={}
    )
    source = PreparedSourceView(
        replace(view().ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
        text,
        pieces,
        nodes,
        (),
        {},
    )

    class LimitedDecoder(ControlledDecoder):
        local_attempts = 0

        def extract(self, pack, inputs, *, threshold, check_active):
            if pack.version != "native-local-v1":
                return super().extract(pack, inputs, threshold=threshold, check_active=check_active)
            self.local_attempts += 1
            if self.local_attempts == 1:
                raise (
                    GlinerWorkerError("controlled terminal fault")
                    if fatal
                    else GlinerRefused("controlled request bound")
                )
            (item,) = inputs
            word = item.text.split()[0]
            return (
                GlinerReport(
                    item.context_id,
                    item.context_digest,
                    "controlled-local",
                    "fixture",
                    pack.fingerprint,
                    GlinerPreparation(item.text, "", 4, 4, len(item.text.encode())),
                    json.dumps({"entities": {"term": [dict(text=word, start=0, end=len(word))]}}),
                    "{}",
                    0,
                    True,
                ),
            )

    decoder = LimitedDecoder("empty")
    method = m1_source.M1Candidates()
    monkeypatch.setattr(method, "_resident", lambda _, *, providers, native_profile: decoder)
    monkeypatch.setattr(
        method, "close", lambda: pytest.fail("input refusal must not retire resident")
    )
    cfg = (
        registry(ROOT / "domains/statistics")
        .overlay(method.name, "default")
        .model_copy(update={"local_schema": {"entities": ["term"]}})
    )
    (result,) = method.run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, "source:7")),),
        cfg,
        SimpleNamespace(reader=owned_reader(source), check_active=lambda: None),
    )
    assert result.parse_detail is not None
    local = detail_objects(result.parse_detail["local_execution"])
    assert [row["outcome"] for row in local] == (
        ["failed", "not_run"] if fatal else ["limited", "succeeded"]
    )
    assert decoder.local_attempts == (1 if fatal else 2)
    assert result.contribution_operations is not None and result.contributions is not None
    limited = [
        op
        for op in result.contribution_operations
        if op["outcome"] in {"limited", "failed", "not_run"}
    ]
    assert limited and all(
        op["emitted_count"] == 0 and op["computation_dependencies"] for op in limited
    )
    assert any(row["semantic_type"] == "entity.term" for row in result.contributions) is not fatal
    bind_contributions(
        release(),
        source=source.ref.key,
        contributions=result.contributions,
        operations=result.contribution_operations,
        coordinate_texts=result.contribution_coordinate_texts,
    )


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
    # Complete retained execution parameters include the original batch size;
    # consumers may repeat that exact request but cannot relabel it as batch1.
    exact_profile = AnnotationProfile(SentenceConfig(exclude=("ner",), batch_size=64))
    reused, reused_errors, _ = consume_annotations(reader, source, exact_profile)
    assert reused == products and not reused_errors
    changed_batch = AnnotationProfile(SentenceConfig(exclude=("ner",), batch_size=1))
    with pytest.raises(ValueError, match="configuration differs from requested parameters"):
        consume_annotations(reader, source, changed_batch)
    changed_profile = AnnotationProfile(SentenceConfig(exclude=("ner",), model_version="0.0.0"))
    with pytest.raises(ValueError, match="model/runtime"):
        consume_annotations(reader, source, changed_profile)
    changed_source = replace(source, ref=replace(source.ref, recipe_digest="d" * 64))
    with pytest.raises(ValueError, match="source-view recipe and scope"):
        consume_annotations(reader, changed_source, AnnotationProfile())


def test_missing_annotation_operation_does_not_fall_back_to_inference():
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.m1_annotations import consume_annotations

    def missing_primary(*_args, **_kwargs):
        raise ValueError("no selected primary layer")

    with pytest.raises(ValueError, match="no selected primary layer"):
        consume_annotations(
            SimpleNamespace(primary_characterization=missing_primary), view(), AnnotationProfile()
        )


def test_explicit_regions_execute_only_requested_primary_and_keep_unrequested_inventory(
    monkeypatch,
):
    from dataclasses import replace

    from corpus_structure.orchestrate.m1 import registry

    first, second = "Mean is average.", "Other is distinct."
    text = first + "\n" + second
    nodes = (
        dict(self_ref="#/groups/1", label="section"),
        dict(self_ref="#/texts/1", label="text", text=first),
        dict(self_ref="#/texts/2", label="text", text=second),
    )
    pieces = (
        dict(kind="native_text", item_ref="#/texts/1", start=0, end=len(first)),
        dict(kind="synthetic_separator", start=len(first), end=len(first) + 1),
        dict(kind="native_text", item_ref="#/texts/2", start=len(first) + 1, end=len(text)),
    )
    projection = dict(
        text=text,
        pieces=pieces,
        items=[node["self_ref"] for node in nodes],
        ancestors=[],
        health={},
    )
    selected = PreparedSourceView(
        replace(view().ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
        text,
        pieces,
        nodes,
        (),
        {},
    )
    method = m1_source.M1Candidates()
    worker = ControlledDecoder("empty")
    monkeypatch.setattr(method, "_resident", lambda _, *, providers, native_profile: worker)
    cfg = (
        registry(ROOT / "domains/statistics")
        .overlay(method.name, "default")
        .model_copy(
            update={
                "region_pointers": ("#/texts/1",),
                "source_projection_digest": selected.ref.projection_digest,
            }
        )
    )
    (result,) = method.run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, "source:7")),),
        cfg,
        SimpleNamespace(reader=owned_reader(selected), check_active=lambda: None),
    )
    assert worker.calls and all(item.text == first for _, inputs in worker.calls for item in inputs)
    assert result.parse_detail is not None
    regions = detail_objects(result.parse_detail["regions"])
    unrequested = next(row for row in regions if row["pointer"] == "#/texts/2")
    assert unrequested["outcome"] == "not_requested" and not unrequested["selections"]
    assert all(row.outcome == "unknown" for row in result.coverage if row.scope == "#/texts/2")
    worker.calls.clear()
    bad = cfg.model_copy(update={"region_pointers": ("#/texts/99999",)})
    with pytest.raises(m1_source.GlinerRefused, match="unknown native region"):
        method.run(
            (SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, "source:7")),),
            bad,
            SimpleNamespace(reader=owned_reader(selected), check_active=lambda: None),
        )
    assert worker.calls == []


def test_projection_selection_is_metadata_only_and_never_silently_empty():
    from dataclasses import replace

    from corpus_structure.orchestrate.m1 import registry

    method = m1_source.M1Candidates()
    body = view().ref
    header = replace(body, id=8, key="header", projection_digest="d" * 64)
    reader = SimpleNamespace(
        source_views=lambda: (header, body),
        source_view=lambda *_: pytest.fail("selector hydrated source bodies"),
    )
    run = SimpleNamespace(reader=reader)
    cfg = (
        registry(ROOT / "domains/statistics")
        .overlay(method.name, "default")
        .model_copy(update={"source_projection_digest": body.projection_digest})
    )
    assert [ref.unit_id for ref in method.select(run, cfg)] == [body.id]
    with pytest.raises(m1_source.GlinerRefused, match="exactly one"):
        method.select(run, cfg.model_copy(update={"source_projection_digest": "e" * 64}))
    with pytest.raises(m1_source.GlinerRefused, match="exactly one"):
        method.select(
            SimpleNamespace(
                reader=SimpleNamespace(source_views=lambda: (body, replace(body, id=9)))
            ),
            cfg,
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
    cfg = m1_source.M1Config.model_validate(registry(ROOT / "domains/statistics").overlay(method.name, "default"))
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
    monkeypatch.setattr(method, "_resident", lambda profile, *, providers, native_profile: worker)
    from corpus_structure.orchestrate.m1 import registry

    cfg = m1_source.M1Config.model_validate(registry(ROOT / "domains/statistics").overlay(method.name, "default"))
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
    monkeypatch.setattr(method, "_resident", lambda profile, *, providers, native_profile: worker)
    from corpus_structure.orchestrate.m1 import registry

    cfg = m1_source.M1Config.model_validate(registry(ROOT / "domains/statistics").overlay(method.name, "default"))
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
    assert zero["row_label"]["original"] == "A"
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
    from methods.m1_source_preparation_support import dense_table_source

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


def test_witnessed_recipe_is_explicit_versioned_and_rejects_old_writer_config():
    from pydantic import ValidationError

    from corpus_structure.orchestrate.m1 import registry
    from corpus_structure.semantic.identity import canonical_bytes

    methods = registry(ROOT / "domains/statistics")
    cfg = methods.overlay("extract.m1_candidates", "witnessed")
    assert isinstance(cfg, m1_source.M1Config)
    assert m1_source.M1Candidates.version == "10"
    assert len(cfg.annotation_rules) == 15
    assert {(r.rule, r.variant) for r in cfg.annotation_rules} == {
        ("defining", "active_as"),
        ("defining", "passive_as"),
        ("defining", "active_to_be"),
        ("defining", "passive_to_be"),
        ("naming", "active_called_term"),
        ("naming", "passive_called_term"),
        ("defining", "passive_following_display"),
        ("defining", "active_following_display"),
        ("explanation", "given_following_display"),
        ("definition_context", "numbered_label"),
        ("definition_context", "labelled_copula_display"),
        ("defining", "nominal_follows"),
        ("defining", "constructive_copula"),
        ("symbol_declaration", "denotes"),
        ("condition_exception", "marked_clause"),
    }
    baseline = methods.overlay("extract.m1_candidates", "default")
    assert isinstance(baseline, m1_source.M1Config)
    assert not baseline.annotation_rules
    assert canonical_bytes(cfg.model_dump(mode="json")) != canonical_bytes(
        baseline.model_dump(mode="json")
    )
    with pytest.raises(ValidationError, match="annotation_token_rules"):
        m1_source.M1Config.model_validate({**baseline.model_dump(), "annotation_token_rules": {}})


def test_explicit_m1_kernel_consumes_prepared_inputs_without_reader_or_unit(monkeypatch):
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.m1_annotations import consume_annotations
    from corpus_structure.orchestrate.m1 import registry

    source = view()
    reader = owned_reader(source)
    method = m1_source.M1Candidates()
    cfg = m1_source.M1Config.model_validate(registry(ROOT / "domains/statistics").overlay(method.name, "default"))
    annotations, errors, annotation_result = consume_annotations(
        reader, source, AnnotationProfile(cfg.sentences)
    )
    frozen_inputs = m1_source.prepare_source(
        source,
        profile=AnnotationProfile(cfg.sentences),
        max_chars=cfg.max_context_chars,
        max_pieces=cfg.max_context_pieces,
        max_annotation_chars=cfg.max_annotation_chars,
        reader=reader,
        persisted_annotations=annotations,
        annotation_errors=errors,
        policy=cfg.policy,
        formula_prose=cfg.formula_prose,
        region_pointers=cfg.region_pointers,
    )
    prepared = reader.prepared
    # Everything consumed from the reader has been frozen before kernel execution.
    del reader
    worker = ControlledDecoder("definition")
    monkeypatch.setattr(method, "_resident", lambda profile, *, providers, native_profile: worker)
    product = method.produce_candidates(
        prepared=prepared,
        view=source,
        prepared_source=frozen_inputs,
        annotation_result=annotation_result,
        cfg=cfg,
        check_active=lambda: None,
        primary_layers={},
    )
    assert isinstance(product, m1_source.M1CandidateProduct)
    assert product.outcome == ObservationOutcome.PRODUCED
    assert not hasattr(product, "ref")
    assert product.records is not None
    (record,) = product.records
    fields = {field["role"]: field for field in record["fields"]}
    assert fields["term"]["original"] == "Mean"
    assert fields["defining_text"]["original"] == "average"
    assert len(worker.calls) == 3


def test_m1_kernel_yields_exact_inference_question_and_receives_provider_failure():
    """No inference runs: inspect the real plan boundary and error reduction."""
    from corpus_structure.methods.source_preparation import prepare_source
    from corpus_structure.orchestrate.m1 import registry

    source = view()
    method = m1_source.M1Candidates()
    cfg = m1_source.M1Config.model_validate(registry(ROOT / "domains/statistics").overlay(method.name, "default"))
    prepared_source = prepare_source(source, persisted_annotations=(), policy=cfg.policy)
    plan = method.plan_candidates(
        prepared=release(),
        view=source,
        prepared_source=prepared_source,
        annotation_result={
            "method": "controlled-boundary",
            "input_hash": "input",
            "configuration_hash": "configuration",
        },
        cfg=cfg,
        check_active=lambda: None,
        primary_layers={},
    )
    request = next(plan)
    assert isinstance(request, m1_source.M1GlinerRequest)
    assert request.profile == cfg.profile()
    assert request.threshold == cfg.threshold
    assert len(request.inputs) == 1
    assert request.inputs[0].text == "Mean is average."
    assert request.pack.fingerprint in {
        pack.fingerprint
        for variants in m1_source.configured_pack_variants(release(), cfg).values()
        for _, _, pack in variants
    }
    with pytest.raises(StopIteration) as completed:
        plan.throw(GlinerWorkerError("deliberate provider-boundary failure"))
    assert completed.value.value.outcome == ObservationOutcome.FAILED
    assert "deliberate provider-boundary failure" in completed.value.value.error


@pytest.mark.parametrize(
    "failure,expected",
    [("worker", ObservationOutcome.FAILED), ("refused", ObservationOutcome.EMPTY)],
)
def test_m1_typed_reply_preserves_bounded_provider_failure_dispositions(failure, expected):
    from corpus_structure.methods.source_preparation import prepare_source
    from corpus_structure.orchestrate.m1 import registry

    source = view()
    method = m1_source.M1Candidates()
    cfg = m1_source.M1Config.model_validate(registry(ROOT / "domains/statistics").overlay(method.name, "default"))
    plan = method.plan_candidate_replies(
        prepared=release(),
        view=source,
        prepared_source=prepare_source(source, persisted_annotations=(), policy=cfg.policy),
        annotation_result={
            "method": "controlled-boundary",
            "input_hash": "input",
            "configuration_hash": "configuration",
        },
        cfg=cfg,
        check_active=lambda: None,
        primary_layers={},
    )
    request = next(plan)
    questions = 0
    while True:
        assert isinstance(request, m1_source.M1GlinerRequest)
        questions += 1
        assert questions <= 3
        try:
            request = plan.send(
                m1_source.M1GlinerReply(failure=failure, message="deliberate typed failure")
            )
        except StopIteration as completed:
            assert completed.value.outcome == expected
            break
