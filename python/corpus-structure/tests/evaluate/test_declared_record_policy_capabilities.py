"""Resource/transport refusals, independent of native permission qualification."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from evaluate.declared_record_policy_support import source, training_grade
from semantic.record_policy_support import algorithm, fitted

from corpus_structure.evaluate.declared_record_policy import (
    DdoRecordFeatureFitRequest,
    DdoRecordFitSpecification,
    DdoRecordGrade,
    DdoRecordGradeSelection,
    RecordPolicyFitPlan,
    _check_source_coordinates,
    prepare_record_feature_policy,
    reacquire_record_feature_grade,
)
from corpus_structure.semantic.data_operation_model import (
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_policy_authority import DdoRecordPolicyApplicability


def selection(grade):
    cut = CutSelection(
        canonical_bytes(
            dict(
                project_id="project:one",
                demand_id="demand:grade",
                read_id="read:grade",
                release_id="release:selection",
                runtime_id="runtime:selection",
                selection={},
                trust_snapshot={},
                read_snapshot="1:2:",
                frontier_at="2026-11-15T00:00:00Z",
                scope={"product_ids": ["product:grade"]},
            )
        )
    )
    return DdoRecordGradeSelection(
        project_id="project:one",
        demand_id="demand:grade",
        read_id="read:grade",
        use_id="use:grade",
        derivation_id="derivation:grade",
        product_id="product:grade",
        expected_cut=cut.identity,
        cut_canonical_json=cut.content.decode(),
        frame_digest=grade.frame_digest,
    )


class AcquiredEngine:
    def __init__(self, connection):
        self.connection = connection
        self.borrows = 0

    @contextmanager
    def begin(self):
        self.borrows += 1
        yield self.connection


def test_fit_refuses_missing_fitter_without_borrowing_evaluator():
    evaluator = AcquiredEngine(object())
    plan = RecordPolicyFitPlan().plan(
        SimpleNamespace(arguments={}),
        binding=None,
        check_active=lambda: None,
        execution_owner=SimpleNamespace(engine=evaluator, fitter_engine=None),
    )
    with pytest.raises(ValueError, match="separately acquired fitter engine"):
        next(plan)
    assert evaluator.borrows == 0


def test_fit_acquires_feature_labels_only_through_explicit_fitter_resource(monkeypatch):
    import corpus_structure.evaluate.declared_record_policy as owner

    grade = DdoRecordGrade.from_frame(training_grade().frame)
    selected = selection(grade)
    spec = DdoRecordFitSpecification(
        feature_selection=selected,
        calibration_selection=selected,
        frozen_feature=fitted(),
        applicability=DdoRecordPolicyApplicability(
            project_id="project:one", sources=(source(900),)
        ),
        family_contract=grade.frame.family_contract,
        reading_recipe=grade.frame.reading_recipe,
        event_procedure="procedure:whole-reading",
        assumptions="controlled complete source population",
        threshold=0.99,
        threshold_procedure="predeclared-threshold",
    )
    support = ComputationalSupportReference(
        derivation_id=selected.derivation_id, admission_use_id=None
    )
    member = BoundRoleMember(
        selected.product_id,
        "kind:grade",
        "knowledge-universe",
        None,
        b"{}",
        b"{}",
        (selected.derivation_id,),
        b"{}",
        subject_definition="knowledge-universe",
        support_references=(support,),
    )
    binding = SimpleNamespace(
        sufficient=True,
        subject_context=SubjectContext(
            "project:one",
            "knowledge-universe",
            None,
            b"{}",
            subject_definition="knowledge-universe",
        ),
        roles=(
            ResolvedRoleBinding("feature_grade", "present", (member,)),
            ResolvedRoleBinding("calibration_grade", "present", (member,)),
        ),
    )
    feature_connection, evaluator_connection = object(), object()
    fitter, evaluator = AcquiredEngine(feature_connection), AcquiredEngine(evaluator_connection)

    class CapturedRestrictedRead(Exception):
        pass

    def restricted(connection, actual):
        assert connection is feature_connection
        assert actual == selected
        raise CapturedRestrictedRead

    monkeypatch.setattr(owner, "reacquire_record_feature_grade", restricted)
    values = SimpleNamespace(arguments={"specification": spec.model_dump(mode="json")})
    plan = owner.RecordPolicyFitPlan().plan(
        values,
        binding=binding,
        check_active=lambda: None,
        execution_owner=SimpleNamespace(engine=evaluator, fitter_engine=fitter),
    )
    with pytest.raises(CapturedRestrictedRead):
        next(plan)
    assert fitter.borrows == 1 and evaluator.borrows == 0


def test_restricted_read_preserves_actual_cut_bytes_and_exact_frame(monkeypatch):
    import corpus_structure.semantic.record_policy_native as native

    grade = training_grade()
    selected = selection(grade)
    connection = object()
    calls = []

    def boundary(actual, **parameters):
        assert actual is connection
        assert parameters.pop("cut").content == selected.cut_canonical_json.encode()
        assert parameters == selected.model_dump(mode="python", exclude={"cut_canonical_json"})
        calls.append(parameters)
        return {
            "product_id": selected.product_id,
            "derivation_id": selected.derivation_id,
            "frame": grade.model_dump(mode="json"),
        }

    monkeypatch.setattr(native, "read_record_feature_fit_frame", boundary)
    assert reacquire_record_feature_grade(connection, selected) == grade
    assert len(calls) == 1
    with pytest.raises(ValueError, match="original acquired cut bytes"):
        reacquire_record_feature_grade(
            connection, selected.model_copy(update={"expected_cut": "other-cut"})
        )
    assert len(calls) == 1


def test_preliminary_fit_emits_current_policy_without_changing_original_lineage(monkeypatch):
    import corpus_structure.evaluate.declared_record_policy as owner

    grade = training_grade()
    selected = selection(grade)
    connection = object()

    def acquired(actual, actual_selection):
        assert actual is connection and actual_selection == selected
        return grade

    monkeypatch.setattr(owner, "reacquire_record_feature_grade", acquired)
    result = prepare_record_feature_policy(
        connection,
        DdoRecordFeatureFitRequest(
            selection=selected,
            algorithm=algorithm(),
            assumptions="independent complete source census",
        ),
    )
    assert result["fit"]["instance"]["applicability"]["release_id"] == "release:test"
    policy = result["reading_policy"]
    assert isinstance(policy, dict)
    assert policy["version"] == "reading-feature-policy-2"
    from corpus_structure.semantic.observations import source_python

    encoded = policy["feature_instances"]
    assert isinstance(encoded, dict)
    (instance,) = source_python(encoded)
    assert instance["family_contract"] == grade.frame.family_contract
    assert instance["reading_recipe"] == grade.frame.reading_recipe
    assert instance["feature"]["fit"]["frame_digest"] == grade.frame_digest


def test_evaluator_mcp_fitting_uses_separate_fit_connection(monkeypatch):
    import json

    import anyio
    from fastmcp import Client

    import corpus_structure.intervene.selected_assessment_server as adapter

    fit_connection, evaluator_connection = object(), object()
    fit, evaluator = AcquiredEngine(fit_connection), AcquiredEngine(evaluator_connection)
    request = DdoRecordFeatureFitRequest(
        selection=selection(training_grade()),
        algorithm=algorithm(),
        assumptions="predeclared source-only frame",
    )
    calls = []

    def prepare(connection, actual):
        assert connection is fit_connection and actual == request
        calls.append(actual)
        return {"fit": {"diagnostics": {"standing": "provisional"}}, "reading_policy": None}

    monkeypatch.setattr(adapter, "prepare_record_feature_policy", prepare)

    async def journey():
        async with Client(
            adapter.build_evaluator_server(
                project="project:one", evaluator_engine=evaluator, fitter_engine=fit
            )
        ) as client:
            tools = {tool.name for tool in await client.list_tools()}
            assert tools == {"compare_selected_reference", "fit_complete_record_features"}
            result = await client.call_tool(
                "fit_complete_record_features", {"request": request.model_dump(mode="json")}
            )
            assert result.structured_content is not None
            body = json.loads(result.structured_content["exact_json"])
            assert body["fit"]["diagnostics"]["standing"] == "provisional"
            assert body["reading_policy"] is None

    anyio.run(journey)
    assert len(calls) == 1 and fit.borrows == 1 and evaluator.borrows == 0


def test_native_source_text_authentication_and_exact_observation_refusal():
    from evaluate.declared_record_grading_support import current

    from corpus_structure.semantic.source_products import FrozenNativeSource

    prepared, _ = current()
    native = FrozenNativeSource.from_projection(
        prepared,
        document="original:1",
        section_pointer="#/groups/0",
        membership="descendants",
        text="Hello",
        pieces=[
            dict(kind="native_text", start=0, end=5, item_ref="#/texts/0", source_field="text")
        ],
        items=[dict(self_ref="#/texts/0", label="text", text="Hello", orig="Hello", prov=[])],
    )
    pin = (
        source(1)
        .model_copy(update={"projection_digest": native.value["source"]["projection"]})
        .model_dump(mode="json", exclude_none=True)
    )
    coordinate = dict(pin=pin, space="native", pointer="#/texts/0", text="Hello")
    _check_source_coordinates(prepared, ((pin, native.value),), (coordinate,))
    with pytest.raises(ValueError, match="actual retained source bytes"):
        _check_source_coordinates(
            prepared, ((pin, native.value),), ({**coordinate, "text": "invented"},)
        )
    with pytest.raises(ValueError, match="separately admitted observation"):
        _check_source_coordinates(
            prepared, ((pin, native.value),), ({**coordinate, "space": "captured_recognition"},)
        )
    with pytest.raises(ValueError, match="synthetic or another source item"):
        _check_source_coordinates(
            prepared,
            ((pin, native.value),),
            (coordinate,),
            (
                dict(
                    pin=pin,
                    space="selected_projection",
                    pointer="#/texts/0",
                    precision="exact",
                    start=0,
                    end=6,
                ),
            ),
        )


def test_record_policy_boundary_owns_refusals_and_preserves_unexpected_value_error(monkeypatch):
    import corpus_structure.evaluate.declared_record_policy as owner
    from corpus_structure.semantic.refusals import SemanticRefusal

    grade = training_grade()
    selected = selection(grade)
    with pytest.raises(SemanticRefusal, match="original acquired cut bytes"):
        owner.reacquire_record_feature_grade(
            object(), selected.model_copy(update={"expected_cut": "different"})
        )
    unexpected = ValueError("internal acquisition implementation error")

    def broken(*_args):
        raise unexpected

    monkeypatch.setattr(owner, "reacquire_record_feature_grade", broken)
    request = DdoRecordFeatureFitRequest(
        selection=selected, algorithm=algorithm(), assumptions="complete source population"
    )
    with pytest.raises(ValueError) as observed:
        owner.prepare_record_feature_policy(object(), request)
    assert observed.value is unexpected
    assert not isinstance(observed.value, SemanticRefusal)


@pytest.mark.parametrize(
    "targets,first_purpose",
    [
        (("record_policy.grade",), "evaluate"),
        (("record_policy.fit",), "fit"),
        (("record_policy.fit", "record_policy.authorize"), "fit"),
    ],
)
def test_registered_record_cli_accepts_genuine_fit_authorize_and_acquires_fit_resource(
    cli, monkeypatch, tmp_path, targets, first_purpose
):
    import corpus_structure.semantic.runtime as runtime
    from corpus_structure.semantic.data_operation_service import DemandRoot, NativeDemandRequest

    request = NativeDemandRequest(
        project_id="unadmitted-project",
        release_id="unadmitted-release",
        runtime_id="unadmitted-runtime",
        roots=(
            DemandRoot(subject="unadmitted-knowledge", original_source=None, analyzed_scope={}),
        ),
        targets=targets,
        execution_profile="controlled-adapter",
    )
    path = tmp_path / "record-request.json"
    path.write_bytes(canonical_bytes(request.model_dump(mode="json")))
    acquired = []
    sentinel = RuntimeError("stop before database acquisition")

    def acquire(*_args, purpose, **_kwargs):
        acquired.append(purpose)
        raise sentinel

    monkeypatch.setattr(runtime, "open_runtime_engine", acquire)
    result = cli(
        "eval", "records", "--request", str(path), "--source-root", str(tmp_path), "--json"
    )
    assert acquired == [first_purpose]
    assert result.exception is sentinel
