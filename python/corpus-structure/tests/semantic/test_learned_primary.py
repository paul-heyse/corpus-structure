"""Controlled target preparation and source projection; no provider qualification."""

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import (
    NativeProfile,
    NativeSelection,
    gliner_selection,
    pm2_selection,
)
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.primary_operations import primary_operation_inputs
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def test_learned_profile_captures_actual_provider_factories_and_private_outputs(
    tmp_path, monkeypatch
):
    from corpus_structure.methods import native_profiles
    from semantic.model_characterization_support import gliner_profile

    monkeypatch.setattr(
        native_profiles,
        "spacy_selection",
        lambda config: NativeSelection(
            NativeProfile(
                "spacy",
                {"controlled": "runtime"},
                {"files": {}},
                config.model_dump(mode="json"),
                "float32",
                "cupy",
                4,
                1,
            ),
            tmp_path,
        ),
    )
    from corpus_structure.methods.gliner import CUDA_WHITESPACE_PROFILE

    gliner = replace(gliner_profile().profile, snapshot=tmp_path, version=CUDA_WHITESPACE_PROFILE)
    artifacts = []
    for name, _ in gliner.artifact_hashes:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        content = ("controlled profile custody: " + name).encode()
        path.write_bytes(content)
        artifacts.append((name, sha256(content).hexdigest()))
    gliner = replace(gliner, artifact_hashes=tuple(artifacts))

    selected = {
        provider: pm2_selection(provider, tmp_path, {"controlled": "runtime"}, {})
        for provider in ("maverick", "dipo", "d1")
    }
    selected["gliner"] = gliner_selection(gliner, {"controlled": "runtime"})
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    inputs = primary_operation_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)),
        sentence_configuration=SentenceConfig(),
        hanlp_selection=pm2_selection("hanlp", tmp_path, {"controlled": "runtime"}, {}),
        learned_selections=selected,
    )
    from corpus_structure.semantic import data_operation_storage

    projection = data_operation_storage.data_operation_definition_projection

    def explain_incomplete(prepared, model, **options):
        try:
            return projection(prepared, model, **options)
        except ValueError as error:
            unknowns = [
                (item.root, [(row.location, row.reason) for row in item.unknowns if row.required])
                for item in model.implementation_slices
                if not item.complete
            ]
            raise ValueError(str(error) + ": " + repr(unknowns)) from error

    monkeypatch.setattr(
        data_operation_storage, "data_operation_definition_projection", explain_incomplete
    )
    prepared = prepare_release(inputs.bundle, inputs.dependencies, inputs.profile)
    model = bound_data_operation_model(prepared)
    expected = {
        "text." + name + "/source-native"
        for name in (
            "maverick",
            "dipo",
            "d1_source",
            "d1_candidates",
            "gliner_cues",
            "gliner_function",
        )
    }
    for identity in expected:
        operation = model.operation(identity)
        assert operation.capabilities.prepared_factory is not None
        assert {role.name for role in operation.roles if role.direction == "output"} == {
            "result",
            "candidates",
        }
        assert len(operation.output_witnesses) == 3
    assert model.operation("text.maverick/source-native").dependencies == (
        "segment.sentences/source-native",
    )
    assert set(model.operation("text.d1_candidates/source-native").dependencies) == {
        "text.formal_evidence/source-native",
        "text.constructions/source-native",
        "text.contextual_native/source-native",
    }
    formal_rules = {
        "text.formal_evidence/examined-scope",
        "text.formal_evidence/family-roster",
        "text.formal_evidence/lexical-inventory-links",
        "text.formal_evidence/literal-source-geometry",
        "text.formal_evidence/member-local-addresses",
        "text.formal_evidence/occurrence-origin",
        "text.formal_evidence/symbolic-inventory-positions",
    }
    for operation_id in (
        "text.d1_candidates/source-native",
        "text.contextual_native/source-native",
    ):
        (formal,) = (role for role in model.operation(operation_id).roles if role.name == "formal")
        required = (
            {"text.formal_evidence/canonical-occurrence-addresses"}
            if operation_id == "text.contextual_native/source-native"
            else set()
        )
        assert set(formal.required_rules) == formal_rules | required
    contextual_native = model.operation("text.contextual_native/source-native")
    (constructions,) = (role for role in contextual_native.roles if role.name == "constructions")
    assert constructions.required_rules == ("text.constructions/canonical-occurrence-addresses",)
    frozen = json.loads(
        next(
            artifact.content
            for artifact in inputs.sources.boundary_contracts
            if artifact.name == "learned/execution-custody"
        )
    )
    assert frozen["selections"]["d1"]["profile"]["dtype"] == "bfloat16"
    assert frozen["selections"]["maverick"]["profile"]["dtype"] == "float32"
    assert frozen["selections"]["gliner"]["profile"]["device"] == "cuda"
    from functools import partial

    from corpus_structure.semantic.learned_primary import resolve_learned_primary_port
    from semantic.test_characterization_prepared_ports import admitted

    learned = admitted(
        (inputs.bundle, inputs.sources, prepared, model, None),
        "text.d1_source/source-native",
        partial(resolve_learned_primary_port, family="d1_source", provider="d1"),
    )
    assert learned.native_selections == (selected["d1"],)
    assert any(
        file.path.name == "characterization-questions.yaml" for file in learned._verification.files
    )
    learned._verify()
    _assert_contextual_native_cpu_bracket(inputs, prepared, model, monkeypatch)


def _assert_contextual_native_cpu_bracket(inputs, prepared, model, monkeypatch):
    import os
    from types import SimpleNamespace

    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic import data_operation_prepared_products
    from corpus_structure.semantic.characterization_manifests import (
        append_manifest,
        manifest_contract,
    )
    from corpus_structure.semantic.construction_products import PreparedConstructionProfile
    from corpus_structure.semantic.contextual_native_products import resolve_contextual_native_port
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope
    from corpus_structure.semantic.data_operation_model import BoundRoleMember, ResolvedRoleBinding
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.formal_evidence import grammar_identity
    from corpus_structure.semantic.formal_products import (
        FormalEvidenceOptions,
        prepare_formal_evidence,
    )
    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.formal_products_support import selected
    from semantic.test_characterization_prepared_ports import _publication_context, admitted

    operation = "text.contextual_native/source-native"
    port = admitted(
        (inputs.bundle, inputs.sources, prepared, model, None),
        operation,
        resolve_contextual_native_port,
    )
    formal = prepare_formal_evidence(prepared, model, grammar=grammar_identity())
    source = selected(formal, "All samples are finite.")
    context = _publication_context(source)
    evidence = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    constructions = PreparedConstructionProfile(prepared, model).run(
        source, (evidence,), subject_context=context
    )
    kind_contracts = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    roles = {
        role.name: kind_contracts[role.kind]
        for role in port.operation.roles
        if role.direction == "input"
    }
    members = {
        role: BoundRoleMember(
            product,
            roles[role],
            context.subject,
            context.original_source,
            context.analyzed_scope,
            coverage=b"{}",
            subject_definition=context.subject_definition,
            support_episodes=(),
            support_evidence=b"{}",
            support_references=(),
        )
        for role, product in (
            ("source", "controlled:source"),
            ("formal", evidence.semantic_id),
            ("constructions", constructions.semantic_id),
            ("maverick", "controlled:maverick"),
            ("dipo", "controlled:dipo"),
        )
    }
    frame = DeclaredNativeFrameSource.acquire(
        prepared, source, members["source"], project=context.project_id
    )

    def observation(provider, nominal):
        return append_manifest(
            {
                "source": source.value["source"],
                "selectors": source.value["selectors"],
                "source_pin": frame.pin.values(),
                "provider": provider,
                "profile_digest": "f" * 64,
                "standing": "native_provider_observation",
                "observations": [],
                "coverage": [],
                "outcome": "complete",
                "dependencies": [],
            },
            manifest_contract(prepared, model, "Ddo" + nominal + "Manifest"),
        )

    values = tuple(
        PythonRoleValue(role, roles[role], value)
        for role, value in (
            ("source", source.value),
            ("formal", json.loads(evidence.content)),
            ("constructions", json.loads(constructions.content)),
            ("maverick", observation("maverick", "Maverick")),
            ("dipo", observation("dipo", "Dipo")),
        )
    )
    binding = SimpleNamespace(
        operation=operation,
        subject_context=context,
        roles=tuple(
            ResolvedRoleBinding(role, "present", (member,)) for role, member in members.items()
        ),
        sufficient=True,
    )
    checked = port._verification.check
    checks = []

    def observed_check():
        checks.append(True)
        checked()

    def unexpected_compile(*args, **kwargs):
        raise AssertionError("the prepared contextual native call compiled source after admission")

    monkeypatch.setattr(port._verification, "check", observed_check)
    monkeypatch.setattr(
        data_operation_prepared_products, "compile", unexpected_compile, raising=False
    )
    cpu = CPUExecutionScope(
        prepared,
        CharacterizationExecutionPolicy(
            workers=1, max_submissions=1, max_packet_bytes=8 * 1024**2, max_reply_bytes=8 * 1024**2
        ),
        retain_schema=False,
    )
    try:
        completion = drive_prepared_work(
            port.plan_python(
                values, binding=binding, execution_owner=SimpleNamespace(cpu=cpu, reservation=None)
            ),
            lambda: None,
        )
        assert checks == [True, True]
        (output,) = completion.outputs
        assert len(output.members) == 1
        body = json.loads(output.content)
        assert body["outcome"] == "partial"
        assert body["dependencies"] == [
            {"product_id": members[role].product}
            for role in ("formal", "constructions", "maverick", "dipo")
        ]
        assert canonical_bytes(body) == output.content
        assert json.loads(completion.cpu_execution_evidence)["pid"] != os.getpid()
    finally:
        cpu.close()


def test_explicit_learned_focus_keeps_context_and_unknown_remainder_separate():
    from types import SimpleNamespace

    from corpus_structure.semantic.learned_primary import (
        learned_focal_scopes,
        uncovered_focal_scopes,
    )

    frame = SimpleNamespace(
        text="First. Focus. Last.",
        source_key="native-original:book",
        projection_digest="projection",
        selected_ranges=((0, 19),),
    )
    (scope,) = learned_focal_scopes(
        frame,
        [{"focal_extent": [7, 13], "projection_extent": [0, 19]}],
        max_context_chars=64,
        exact=False,
    )
    assert scope.focal == (7, 13) and (scope.start, scope.end) == (0, 19)
    assert tuple(uncovered_focal_scopes(frame, (scope,))) == (
        {"projection": "projection", "start": 0, "end": 7},
        {"projection": "projection", "start": 13, "end": 19},
    )
    (exact,) = learned_focal_scopes(
        frame,
        [{"focal_extent": [7, 13], "projection_extent": [7, 13]}],
        max_context_chars=64,
        exact=True,
    )
    assert exact.focal == (exact.start, exact.end)


def test_explicit_learned_focus_refuses_widening_duplicate_and_inexact_gliner_scope():
    from types import SimpleNamespace

    import pytest

    from corpus_structure.semantic.learned_primary import learned_focal_scopes

    frame = SimpleNamespace(
        text="First. Focus. Last.",
        source_key="native-original:book",
        projection_digest="projection",
        selected_ranges=((7, 13),),
    )
    with pytest.raises(ValueError, match="exact admitted source"):
        learned_focal_scopes(
            frame,
            [{"focal_extent": [7, 13], "projection_extent": [0, 19]}],
            max_context_chars=64,
            exact=False,
        )
    with pytest.raises(ValueError, match="provider question scope"):
        learned_focal_scopes(
            frame,
            [{"focal_extent": [8, 12], "projection_extent": [7, 13]}],
            max_context_chars=64,
            exact=True,
        )
    selected = {"focal_extent": [7, 13], "projection_extent": [7, 13]}
    with pytest.raises(ValueError, match="repeats identical captured work"):
        learned_focal_scopes(frame, [selected, selected], max_context_chars=64, exact=True)
