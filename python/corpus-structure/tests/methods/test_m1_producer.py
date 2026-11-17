"""Real preparation/assembly with controlled decoder readings; no GLiNER provider claim."""

import json
from types import SimpleNamespace

import pytest

from corpus_structure.core.vocab import ObservationOutcome
from corpus_structure.methods import m1_source
from corpus_structure.methods.gliner import GlinerPreparation, GlinerReport
from corpus_structure.methods.gliner_worker import (
    GlinerAdmission,
    GlinerBatchResult,
    GlinerWorkerError,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.m1_products import NativeCandidateData
from methods.m1_producer_support import (
    ROOT as ROOT,
)
from methods.m1_producer_support import (
    ControlledDecoder as ControlledDecoder,
)
from methods.m1_producer_support import (
    candidate_fixture_inputs,
    candidate_fixture_product,
    context_population,
)
from methods.m1_producer_support import (
    detail_object as detail_object,
)
from methods.m1_producer_support import (
    detail_objects as detail_objects,
)
from methods.m1_producer_support import (
    release as release,
)
from methods.m1_producer_support import (
    view as view,
)
from methods.m1_source_preparation_support import projection as literal_projection
from methods.record_assembly_support import model as record_model


def test_local_schema_survives_empty_record_outputs(monkeypatch):
    """Real source preparation and native annotation restoration; controlled decoder only."""
    from methods.domain_configuration import candidate_configuration

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

    decoder = LocalDecoder("empty")
    cfg = candidate_configuration(ROOT / "domains/statistics", "default").model_copy(
        update={
            "local_schema": {"entities": ["term"]},
        }
    )
    result = candidate_fixture_product(
        candidate_fixture_inputs(source, cfg, check_active=lambda: None),
        decoder,
    )
    assert result.contributions is not None
    types = {row["semantic_type"] for row in result.contributions}
    assert "entity.term" in types
    assert not result.records
    assert result.parse_detail is not None and result.parse_detail["local_reports"]


def test_generic_role_guidance_is_an_explicit_pack_identity_with_configured_precedence():
    from corpus_structure.methods.m1_source import configured_packs
    from methods.domain_configuration import candidate_configuration
    from methods.record_assembly_support import release

    cfg = m1_source.M1Config.model_validate(
        candidate_configuration(ROOT / "domains/statistics", "default")
    )
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
    from methods.domain_configuration import candidate_configuration

    source = view()

    decoder = ControlledDecoder("empty")
    cfg = m1_source.M1Config.model_validate(
        candidate_configuration(ROOT / "domains/statistics", "default")
    )
    ctx = SimpleNamespace(check_active=lambda: None)

    baseline = candidate_fixture_product(
        candidate_fixture_inputs(source, cfg, check_active=ctx.check_active), decoder
    )
    guided = candidate_fixture_product(
        candidate_fixture_inputs(source, cfg, check_active=ctx.check_active),
        decoder,
        generic_role_guidance=True,
    )

    assert baseline.parse_detail is not None and guided.parse_detail is not None
    assert "comparison_arm" not in baseline.parse_detail
    assert guided.parse_detail["comparison_arm"] == "generic-source-role-guidance-1"
    assert "generic_role_guidance" not in cfg.model_dump(mode="json")


@pytest.mark.parametrize("fatal", [False, True])
def test_request_limit_continues_independent_context_but_worker_fault_fences_it(monkeypatch, fatal):
    from corpus_structure.semantic.contributions import bind_contributions
    from methods.domain_configuration import candidate_configuration

    first, second = "Mean is average.", "Other is distinct."
    text = first + "\n" + second
    nodes = (
        dict(self_ref="#/groups/1", label="section"),
        dict(self_ref="#/texts/1", label="text", text=first),
        dict(self_ref="#/texts/2", label="text", text=second),
    )
    pieces = (
        dict(
            kind="native_text", source_field="text", item_ref="#/texts/1", start=0, end=len(first)
        ),
        dict(kind="synthetic_separator", start=len(first), end=len(first) + 1),
        dict(
            kind="native_text",
            source_field="text",
            item_ref="#/texts/2",
            start=len(first) + 1,
            end=len(text),
        ),
    )
    source = literal_projection(text, pieces=pieces, items=nodes)

    from corpus_structure.methods.source_preparation import ContextSelection

    prepared_contexts = []
    original_context = ContextSelection.context

    def retain_prepared(selection, *args, **kwargs):
        value = original_context(selection, *args, **kwargs)
        prepared_contexts.append(value)
        return value

    monkeypatch.setattr(ContextSelection, "context", retain_prepared)

    class LimitedDecoder(ControlledDecoder):
        local_attempts = 0

        def extract(self, pack, inputs, *, threshold, check_active):
            if pack.version != "native-local-v1":
                return super().extract(pack, inputs, threshold=threshold, check_active=check_active)
            assert len(prepared_contexts) == 2
            self.local_attempts += 1
            assert len(inputs) == 2
            if fatal:
                raise GlinerWorkerError("controlled terminal fault")
            item = inputs[1]
            word = item.text.split()[0]
            return GlinerBatchResult(
                (
                    GlinerAdmission(
                        0,
                        inputs[0].context_id,
                        inputs[0].context_digest,
                        False,
                        "controlled input bound",
                    ),
                    GlinerAdmission(1, item.context_id, item.context_digest, True),
                ),
                (
                    GlinerReport(
                        item.context_id,
                        item.context_digest,
                        "controlled-local",
                        "fixture",
                        pack.fingerprint,
                        GlinerPreparation(item.text, "", 4, 4, len(item.text.encode())),
                        json.dumps(
                            {"entities": {"term": [dict(text=word, start=0, end=len(word))]}}
                        ),
                        "{}",
                        0,
                        True,
                    ),
                ),
            )

    decoder = LimitedDecoder("empty")

    decoder = decoder

    cfg = candidate_configuration(ROOT / "domains/statistics", "default").model_copy(
        update={"local_schema": {"entities": ["term"]}}
    )
    result = candidate_fixture_product(
        candidate_fixture_inputs(source, cfg, check_active=lambda: None),
        decoder,
    )
    assert result.parse_detail is not None
    local = detail_objects(result.parse_detail["local_execution"])
    assert [row["outcome"] for row in local] == (
        ["not_run", "not_run"] if fatal else ["limited", "succeeded"]
    )
    assert decoder.local_attempts == 1
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
        source=source.source_key,
        contributions=result.contributions,
        operations=result.contribution_operations,
        coordinate_texts=result.contribution_coordinate_texts,
    )


def test_current_annotation_consumer_reuses_columns_and_refuses_profile_or_source_drift(
    monkeypatch,
):
    from dataclasses import replace

    from corpus_structure.ingest import annotations
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.semantic.sentence_products import (
        retained_source_annotation_products,
        source_annotation_rows,
    )
    from corpus_structure.semantic.source_products import FrozenNativeSource
    from methods.declared_primary_fixture import source_readings

    source, products, _primary, native = source_readings("Mean is average.", AnnotationProfile())
    monkeypatch.setattr(annotations, "pipeline", lambda *_: pytest.fail("replay ran inference"))
    restored = retained_source_annotation_products(
        FrozenNativeSource(source.source_content.encode()), native
    )
    assert restored == products
    assert restored[0].tokens[0].start == 0 and restored[0].sentences[-1].end == 16
    profile = AnnotationProfile(
        native.configuration,
        execution_profile=native.value.model_dump(mode="json")["execution_profile"],
    )
    rows = source_annotation_rows(json.loads(native.content))
    for changed in (
        replace(profile, configuration=SentenceConfig(exclude=("ner",), batch_size=1)),
        replace(profile, configuration=SentenceConfig(exclude=("ner",), model_version="0.0.0")),
        replace(profile, execution_profile="another-execution"),
    ):
        with pytest.raises(ValueError, match="source/profile pin"):
            annotations.restore_annotations(rows, source=source, profile=changed)
    with pytest.raises(ValueError, match="source/profile pin"):
        annotations.restore_annotations(rows, source=view("Other source."), profile=profile)


def test_explicit_regions_execute_only_requested_primary_and_keep_unrequested_inventory(
    monkeypatch,
):
    from methods.domain_configuration import candidate_configuration

    first, second = "Mean is average.", "Other is distinct."
    text = first + "\n" + second
    nodes = (
        dict(self_ref="#/groups/1", label="section"),
        dict(self_ref="#/texts/1", label="text", text=first),
        dict(self_ref="#/texts/2", label="text", text=second),
    )
    pieces = (
        dict(
            kind="native_text", source_field="text", item_ref="#/texts/1", start=0, end=len(first)
        ),
        dict(kind="synthetic_separator", start=len(first), end=len(first) + 1),
        dict(
            kind="native_text",
            source_field="text",
            item_ref="#/texts/2",
            start=len(first) + 1,
            end=len(text),
        ),
    )
    selected = literal_projection(text, pieces=pieces, items=nodes)

    worker = ControlledDecoder("empty")
    decoder = worker
    cfg = candidate_configuration(ROOT / "domains/statistics", "default").model_copy(
        update={
            "region_pointers": ("#/texts/1",),
            "source_projection_digest": selected.projection_digest,
        }
    )
    result = candidate_fixture_product(
        candidate_fixture_inputs(selected, cfg, check_active=lambda: None),
        decoder,
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
        candidate_fixture_product(
            candidate_fixture_inputs(selected, bad, check_active=lambda: None),
            decoder,
        )
    assert worker.calls == []


def test_context_relationship_diagnostics_cross_the_source_report_boundary(monkeypatch):
    from dataclasses import replace

    from corpus_structure.semantic.observations import source_python, source_value
    from corpus_structure.semantic.source_contexts import ContextRelationship
    from methods.domain_configuration import candidate_configuration

    source = view()

    cfg = m1_source.M1Config.model_validate(
        candidate_configuration(ROOT / "domains/statistics", "default")
    )
    frozen = candidate_fixture_inputs(source, cfg)
    prepared_source = frozen["prepared_source"]
    other = view("Nearby unit.").source_key
    frozen["prepared_source"] = replace(
        prepared_source,
        selections=tuple(
            replace(row, relationships=((other, ContextRelationship.NEIGHBOR, "nearby unit"),))
            for row in prepared_source.selections
        ),
        annotation_errors=("controlled unavailable annotation",),
    )
    result = candidate_fixture_product(frozen)

    decoded = source_python(source_value(result.parse_detail))
    assert decoded["contexts"][0]["relationships"] == [[other, "neighbor", "nearby unit"]]
    assert result.outcome == ObservationOutcome.FAILED


@pytest.mark.parametrize("mode", ["definition", "empty", "failed"])
def test_producer_keeps_candidates_empty_denominator_and_failure_dispositions(monkeypatch, mode):
    source = view()

    worker = ControlledDecoder(mode)
    decoder = worker
    from methods.domain_configuration import candidate_configuration

    cfg = m1_source.M1Config.model_validate(
        candidate_configuration(ROOT / "domains/statistics", "default")
    )
    checks = []
    context = SimpleNamespace(
        check_active=lambda: checks.append("checked"),
    )
    result = candidate_fixture_product(
        candidate_fixture_inputs(source, cfg, check_active=context.check_active),
        decoder,
    )
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
        assert result.outcome == ObservationOutcome.FAILED and result.records == ()
        assert [row["outcome"] for row in detail_objects(details["execution"])] == [
            "not_run",
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
    source = literal_projection(text, pieces=pieces, items=nodes)

    worker = ControlledDecoder("empty")
    decoder = worker
    from methods.domain_configuration import candidate_configuration

    cfg = m1_source.M1Config.model_validate(
        candidate_configuration(ROOT / "domains/statistics", "default")
    )
    result = candidate_fixture_product(
        candidate_fixture_inputs(source, cfg, check_active=lambda: None),
        decoder,
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
    from corpus_structure.semantic.declared_contexts import DeclaredContextPopulation

    population = DeclaredContextPopulation(
        (source,),
        canonical_bytes(
            dict(identity="unadmitted:dense-source", complete=True, evidence={"literal": "source"})
        ),
    )
    data = NativeCandidateData.from_frame(source)
    prepared = source_preparation.prepare_source(
        data,
        source_frame=source,
        context_population=population,
        persisted_annotations=(),
        max_chars=256,
        max_pieces=64,
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
        m1_source._structural_groups(data, selection, context)
        assert captured[-1]["cells"] == tuple(t.cell_index for t in selection.table_targets)
        assert captured[-1]["row_paths"] == {
            t.cell_index: t.row_path for t in selection.table_targets
        }
        assert captured[-1]["header_paths"] == {
            t.cell_index: t.header_path for t in selection.table_targets
        }
        assert len(captured[-1]["cells"]) == 9
    assert len({index for group in captured for index in group["cells"]}) == 270


@pytest.mark.parametrize(
    "obsolete", ("annotation_rules", "formula_syntax", "formula_syntax_input_policy")
)
def test_literal_candidate_configuration_rejects_superseded_primary_branches(obsolete):
    from pydantic import ValidationError

    from methods.domain_configuration import candidate_configuration

    baseline = candidate_configuration(ROOT / "domains/statistics", "default")
    with pytest.raises(ValidationError, match=obsolete):
        m1_source.M1Config.model_validate({**baseline.model_dump(), obsolete: []})


def test_explicit_m1_kernel_consumes_prepared_inputs_without_reader_or_unit(monkeypatch):
    from corpus_structure.methods import source_preparation
    from methods.domain_configuration import candidate_configuration

    source = view()
    cfg = candidate_configuration(ROOT / "domains/statistics", "default")
    inputs = candidate_fixture_inputs(source, cfg)
    monkeypatch.setattr(
        source_preparation,
        "prepare_source",
        lambda *_a, **_k: pytest.fail("kernel prepared sources again"),
    )
    monkeypatch.setattr(
        source_preparation,
        "annotation_inputs",
        lambda *_a, **_k: pytest.fail("kernel discovered annotations again"),
    )
    worker = ControlledDecoder("definition")
    product = candidate_fixture_product(inputs, worker)
    assert isinstance(product, m1_source.M1CandidateProduct)
    assert product.outcome == ObservationOutcome.PRODUCED and not hasattr(product, "ref")
    assert product.records is not None
    (record,) = product.records
    fields = {field["role"]: field for field in record["fields"]}
    assert fields["term"]["original"] == "Mean" and fields["defining_text"]["original"] == "average"
    assert len(worker.calls) == 3


def test_m1_kernel_yields_exact_inference_question_and_receives_provider_failure():
    """No inference runs: inspect the real plan boundary and error reduction."""
    from corpus_structure.methods.source_preparation import prepare_source
    from methods.domain_configuration import candidate_configuration

    source = view()

    cfg = m1_source.M1Config.model_validate(
        candidate_configuration(ROOT / "domains/statistics", "default")
    )
    data = NativeCandidateData.from_frame(source)
    prepared_source = prepare_source(
        data,
        source_frame=source,
        context_population=context_population(source),
        persisted_annotations=(),
        policy=cfg.policy,
    )
    plan = m1_source.plan_candidates(
        prepared=release(),
        view=data,
        prepared_source=prepared_source,
        annotation_result={
            "method": "controlled-boundary",
            "input_hash": "input",
            "configuration_hash": "configuration",
        },
        cfg=cfg,
        check_active=lambda: None,
        model=record_model(),
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
        plan.send(
            m1_source.M1GlinerReply(
                failure="worker", message="deliberate provider-boundary failure"
            )
        )
    assert completed.value.value.outcome == ObservationOutcome.FAILED
    assert "deliberate provider-boundary failure" in completed.value.value.error


@pytest.mark.parametrize(
    "failure,expected",
    [("worker", ObservationOutcome.FAILED), ("refused", ObservationOutcome.EMPTY)],
)
def test_m1_typed_reply_preserves_bounded_provider_failure_dispositions(failure, expected):
    from corpus_structure.methods.source_preparation import prepare_source
    from methods.domain_configuration import candidate_configuration

    source = view()

    cfg = m1_source.M1Config.model_validate(
        candidate_configuration(ROOT / "domains/statistics", "default")
    )
    data = NativeCandidateData.from_frame(source)
    plan = m1_source.plan_candidates(
        prepared=release(),
        view=data,
        prepared_source=prepare_source(
            data,
            source_frame=source,
            context_population=context_population(source),
            persisted_annotations=(),
            policy=cfg.policy,
        ),
        annotation_result={
            "method": "controlled-boundary",
            "input_hash": "input",
            "configuration_hash": "configuration",
        },
        cfg=cfg,
        check_active=lambda: None,
        model=record_model(),
    )
    request = next(plan)
    questions = 0
    while True:
        assert isinstance(request, m1_source.M1GlinerRequest)
        questions += 1
        assert questions <= 3
        try:
            request = plan.send(
                m1_source.M1GlinerReply(failure="worker", message="deliberate typed failure")
                if failure == "worker"
                else m1_source.M1GlinerReply(
                    admissions=tuple(
                        GlinerAdmission(
                            index,
                            item.context_id,
                            item.context_digest,
                            False,
                            "deliberate typed failure",
                        )
                        for index, item in enumerate(request.inputs)
                    )
                )
            )
        except StopIteration as completed:
            assert completed.value.outcome == expected
            break
