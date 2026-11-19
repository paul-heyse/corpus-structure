"""Independent controls for the declared operation grammar and openness contracts."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import Literal

import pytest
import yaml

from corpus_structure.model.compiled import compiled_model, running_model
from corpus_structure.schema.operation_declarations import (
    check_declared_openness,
    check_literal_members,
    vocabulary,
)
from corpus_structure.schema.operation_declarations import (
    declarations as grammar,
)
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.operation_reporting import validation_report
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import (
    PreparationError,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from semantic.data_operation_declaration_support import contract, declarations


@pytest.mark.parametrize(
    ("filename", "logical_filename"),
    [
        ("/installed/sample/member.py", "sample/member.py"),
        ("/installed/sample/member/__init__.py", "sample/member/__init__.py"),
    ],
)
def test_captured_python_sources_compose_with_their_acquired_origin(filename, logical_filename):
    from corpus_structure.semantic.composed import read_data_operation_inputs
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    source = PythonSource("sample.member", b"from . import sibling\n", filename, b"value: int\n")
    acquired = PythonSourceCollection((source,))
    dependencies = data_operation_dependencies(ResolvedDependencies(), python_sources=acquired)
    decoded = read_data_operation_inputs(dependencies)
    assert decoded is not None and decoded[1] is not None
    captured = decoded[1]
    assert captured.sources == (replace(source, filename=logical_filename),)
    assert combine_primary_sources(captured, acquired).sources == acquired.sources
    assert combine_primary_sources(acquired, captured).sources == acquired.sources


@pytest.mark.parametrize(
    "change",
    [
        {"content": b"value = 2\n"},
        {"stub": b"value: str\n"},
        {"filename": "sample/member/__init__.py"},
    ],
)
def test_captured_python_composition_refuses_different_module_meaning(change):
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    source = PythonSource("sample.member", b"value = 1\n", "sample/member.py", b"value: int\n")
    with pytest.raises(ValueError, match="disagree on a captured module"):
        combine_primary_sources(
            PythonSourceCollection((source,)), PythonSourceCollection((replace(source, **change),))
        )


def test_captured_python_composition_preserves_interpretation_and_custody_conflicts():
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    acquired = PythonSourceCollection(
        (PythonSource("sample.member", b"value = 1\n", "sample/member.py"),),
        boundary_contracts=(SourceArtifact("sample/custody", b"first"),),
    )
    with pytest.raises(ValueError, match="incompatible interpretation"):
        combine_primary_sources(acquired, replace(acquired, interpretation="other"))
    with pytest.raises(ValueError, match="disagree on acquired custody"):
        combine_primary_sources(
            acquired,
            replace(acquired, boundary_contracts=(SourceArtifact("sample/custody", b"other"),)),
        )


def test_captured_python_composition_refuses_different_acquired_module_origins():
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    first = PythonSource("sample.member", b"value = 1\n", "/first/sample/member.py")
    second = replace(first, filename="/second/sample/member.py")
    for sources in ((first, second), (second, first)):
        with pytest.raises(ValueError, match="disagree on acquired module origin"):
            combine_primary_sources(*(PythonSourceCollection((source,)) for source in sources))


def test_captured_python_package_preserves_relative_import_resolution():
    from corpus_structure.semantic.composed import read_data_operation_inputs
    from corpus_structure.semantic.python_operation_sources import (
        ClosedPythonSources,
        PythonSource,
        PythonSourceCollection,
    )

    acquired = PythonSourceCollection(
        (
            PythonSource("sample", b"from .sibling import run\n", "/installed/sample/__init__.py"),
            PythonSource(
                "sample.sibling",
                b"def run() -> int:\n    return 1\n",
                "/installed/sample/sibling.py",
            ),
        )
    )
    decoded = read_data_operation_inputs(
        data_operation_dependencies(ResolvedDependencies(), python_sources=acquired)
    )
    assert decoded is not None and decoded[1] is not None
    captured = ClosedPythonSources(decoded[1], resolve_relative_imports=True)
    assert captured.resolve("sample.run").canonical_path == "sample.sibling.run"


def operation(**changes):
    changes = {"validity_family": ["none"], **changes}
    value = contract(**changes)
    value["capabilities"] = {
        **value["capabilities"],
        "preparation": "resource",
        "ownership": "immutable",
    }
    return value


def changed_model(source_name, update):
    sources = dict(running_model().sources)
    document = yaml.safe_load(sources[source_name])
    update(document)
    sources[source_name] = yaml.safe_dump(document).encode()
    return compiled_model(sources)


@pytest.mark.parametrize("field", ["precision", "profile_alias"])
def test_extra_top_level_fields_refuse(field):
    with pytest.raises(PreparationError, match="unsupported fields: " + field):
        compile_data_operations(declarations=declarations(operation(**{field: "extra"})))


def test_nested_record_is_closed_and_located():
    value = operation()
    value["roles"][0]["extra"] = True
    with pytest.raises(PreparationError, match="unsupported fields: extra") as caught:
        compile_data_operations(declarations=declarations(value))
    assert caught.value.diagnostics[0].location.endswith("/roles/0")


def test_closed_profile_refuses_but_descriptive_terms_remain_open():
    with pytest.raises(PreparationError, match="profile"):
        compile_data_operations(declarations=declarations(operation(profile="experimental")))
    value = operation()
    value["capabilities"].update(ownership="experimental-shared", preparation="new-preparation")
    value["capabilities"]["cancellation"] = "arbitrary description without an interpreter"
    model = compile_data_operations(declarations=declarations(value))
    assert [(item.code, item.outcome) for item in model.diagnostics] == [
        ("ownership_unknown_term", "advisory"),
        ("preparation_unknown_term", "advisory"),
    ]
    assert model.operations[0].capabilities.ownership == "experimental-shared"
    assert (
        model.operations[0].capabilities.cancellation
        == "arbitrary description without an interpreter"
    )


def test_declared_form_perturbation_changes_actual_compiler_acceptance():
    changed = changed_model(
        "operation-vocabularies.yaml",
        lambda value: value["enums"]["Form"]["permissible_values"].update(vector={}),
    )
    value = operation()
    value["capabilities"]["forms"] = ["vector"]
    with pytest.raises(PreparationError):
        compile_data_operations(declarations=declarations(value))
    model = compile_data_operations(declarations=declarations(value), declaration_model=changed)
    assert model.operations[0].capabilities.forms == ("vector",)
    with pytest.raises(ValueError, match=r"missing=.*vector"):
        check_literal_members("Form", Literal["scalar", "batch", "stream"], changed)


def test_release_preparation_uses_the_captured_vocabulary():
    changed = changed_model(
        "operation-vocabularies.yaml",
        lambda value: value["enums"]["Ownership"]["permissible_values"].update(captured={}),
    )
    value = operation()
    value["capabilities"]["ownership"] = "captured"
    schema = SourceBundle(
        "test.yaml",
        (SourceArtifact("test.yaml", b"id: https://example.org/test\nname: test\nclasses: {}\n"),),
    )
    original = prepare_release(
        schema, data_operation_dependencies(ResolvedDependencies(), declarations(value))
    )
    prepared = prepare_release(
        schema,
        data_operation_dependencies(
            ResolvedDependencies(), declarations(value), declaration_model=changed
        ),
    )
    assert [item.code for item in original.diagnostics] == ["ownership_unknown_term"]
    assert prepared.diagnostics == ()
    assert prepared.release_id != original.release_id


def test_replacing_operation_inputs_preserves_exact_captured_grammar():
    from corpus_structure.schema.operation_declarations import (
        captured_declaration_model,
        declaration_sources,
    )
    from corpus_structure.semantic.composed import read_data_operation_inputs

    changed = changed_model(
        "operation-vocabularies.yaml",
        lambda value: value["enums"]["Ownership"]["permissible_values"].update(captured={}),
    )
    original = data_operation_dependencies(
        ResolvedDependencies(), declarations(operation()), declaration_model=changed
    )
    retained = ResolvedDependencies(
        tuple(item for item in original.artifacts if not item.name.startswith("data-operations/"))
    )
    replacement = operation(parameters={"revision": "replacement"})
    replacement["capabilities"]["ownership"] = "captured"
    recomposed = data_operation_dependencies(retained, declarations(replacement))
    assert (
        tuple(item for item in recomposed.artifacts if item in retained.artifacts)
        == retained.artifacts
    )
    assert retained.artifacts == declaration_sources(changed)
    decoded = read_data_operation_inputs(recomposed)
    assert decoded is not None
    supplied, _ = decoded
    model = compile_data_operations(
        declarations=supplied,
        declaration_model=captured_declaration_model(recomposed.artifacts),
    )
    assert model.diagnostics == ()
    assert model.operations[0].parameters == b'{"revision":"replacement"}'
    # Explicitly supplying the same grammar does not duplicate the capture.
    assert (
        data_operation_dependencies(
            retained, declarations(replacement), declaration_model=changed
        ).artifacts
        == recomposed.artifacts
    )
    with pytest.raises(ValueError, match="conflicts with captured"):
        data_operation_dependencies(
            retained, declarations(replacement), declaration_model=running_model()
        )


@pytest.mark.parametrize("malformation", ["partial", "duplicate"])
def test_recomposition_refuses_malformed_captured_grammar(malformation):
    from corpus_structure.schema.operation_declarations import declaration_sources

    sources = declaration_sources()
    malformed = sources[:-1] if malformation == "partial" else (*sources, sources[0])
    with pytest.raises(ValueError, match="exactly the operation declaration grammar"):
        data_operation_dependencies(ResolvedDependencies(malformed), declarations(operation()))


def test_recommended_validity_warning_has_one_nonrefusing_owner():
    changed = changed_model(
        "operation-declarations.yaml",
        lambda value: value["classes"]["DataOperationDeclaration"]["attributes"][
            "validity_family"
        ].update(recommended=True),
    )
    absent = operation()
    absent.pop("validity_family")
    missing = compile_data_operations(declarations=declarations(absent), declaration_model=changed)
    assert [(item.code, item.outcome) for item in missing.diagnostics] == [
        ("validity_undetermined", "advisory")
    ]
    explicit = compile_data_operations(
        declarations=declarations(operation(validity_family=["none"])), declaration_model=changed
    )
    assert explicit.diagnostics == ()
    assert compile_data_operations(declarations=declarations(operation())).diagnostics == ()


def test_preparation_retains_nonrefusing_diagnostics_for_its_report():
    value = operation()
    value["capabilities"]["ownership"] = "experimental-shared"
    schema = SourceBundle(
        "test.yaml",
        (SourceArtifact("test.yaml", b"id: https://example.org/test\nname: test\nclasses: {}\n"),),
    )
    dependencies = data_operation_dependencies(ResolvedDependencies(), declarations(value))
    prepared = prepare_release(schema, dependencies)
    assert [(item.code, item.outcome) for item in prepared.diagnostics] == [
        ("ownership_unknown_term", "advisory")
    ]
    report = validation_report(prepared.diagnostics, prepared=prepared).model_dump(mode="json")
    assert report["complete"] is False
    assert report["observations"][0]["category"] == "unassessed"
    assert report["observations"][0]["code"] == "ownership_unknown_term"


def test_diagnostics_are_not_semantic_model_archive_fields():
    value = operation()
    value["capabilities"]["ownership"] = "experimental-shared"
    model = compile_data_operations(declarations=declarations(value))
    assert model.diagnostics
    assert b'"diagnostics"' not in model.content
    from corpus_structure.semantic.data_operation_model import read_effective_data_operations

    restored = read_effective_data_operations(model.content)
    assert restored.content == model.content
    assert restored.diagnostics == ()


@pytest.mark.parametrize("openness,refuses", [("closed", True), ("pack-extensible", False)])
def test_released_pack_extension_follows_declared_openness(openness, refuses):
    base = {
        "id": "https://example.org/base",
        "name": "base",
        "enums": {
            "Base": {"annotations": {"cs:openness": openness}, "permissible_values": {"known": {}}}
        },
    }
    pack = {
        "id": "https://example.org/pack",
        "name": "pack",
        "imports": ["base"],
        "enums": {"Extended": {"inherits": ["Base"], "permissible_values": {"new": {}}}},
    }
    sources = {"base": yaml.safe_dump(base).encode(), "pack": yaml.safe_dump(pack).encode()}
    bundle = SourceBundle(
        "pack", tuple(SourceArtifact(name, body) for name, body in sources.items())
    )
    if refuses:
        with pytest.raises(PreparationError, match="cannot extend closed vocabulary Base"):
            prepare_release(bundle)
    else:
        prepared = prepare_release(bundle)
        assert {
            member.value
            for item in prepared.vocabularies
            if item.enum == "Extended"
            for member in item.members
        } == {"known", "new"}


@pytest.mark.parametrize(
    "enum_name,slot",
    [
        ("Ownership", {"range": "Ownership"}),
        ("Profile", {"any_of": [{"range": "Profile"}, {"range": "string"}]}),
    ],
)
def test_declared_openness_cannot_disagree_with_range(enum_name, slot):
    model = changed_model(
        "operation-declarations.yaml",
        lambda value: value["classes"].update(Bad={"attributes": {"value": slot}}),
    )
    with pytest.raises(PreparationError, match="vocabulary"):
        check_declared_openness(model.private_view("operation-declarations.yaml"))


def test_projection_reuses_one_validator_and_reports_provisional_members():
    assert grammar() is grammar()
    assert vocabulary("Ownership").openness == "open"
    assert dict(vocabulary("Ownership").statuses)["immutable"] is None
    assert dict(vocabulary("Ownership").statuses)["owned-pdf-build"] == "provisional"


def test_current_complete_python_literals_follow_the_declared_structural_grammar():
    root = Path(__file__).parents[2] / "src/corpus_structure"
    observed = []
    unknown_terms = set()
    for path in root.rglob("*.py"):
        source = path.read_text()
        if "__data_operation__" not in source:
            continue
        for node in ast.walk(ast.parse(source)):
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
                if isinstance(node, ast.AnnAssign)
                else []
            )
            if not any(
                isinstance(target, ast.Name) and target.id.endswith("__data_operation__")
                for target in targets
            ):
                continue
            assert isinstance(node, (ast.Assign, ast.AnnAssign))
            assert node.value is not None
            value = ast.literal_eval(node.value)
            # Abstract and inherited overlays are combined by the independently
            # tested closed Python front end, not complete declaration records.
            if value.get("abstract") or "id" not in value or "role_overrides" in value:
                continue
            observed.append(value["id"])
            unknown_terms.update(
                (item.code, item.message) for item in grammar().validate(value, value["id"])
            )
    assert "text.compose_view/full-native" in observed
    assert "reference.snapshot/declared" in observed
    assert unknown_terms == {
        ("preparation_unknown_term", "open vocabulary term is not assessed: schema")
    }


def test_enum_only_import_does_not_create_physical_tables_or_columns():
    sources = dict(running_model().sources)
    document = yaml.safe_load(sources["physical.yaml"])
    document["imports"].append("operation-vocabularies")
    sources["physical.yaml"] = yaml.safe_dump(document, sort_keys=False).encode()
    ordinary = running_model().physical()
    candidate = compiled_model(sources).physical()
    assert {(name, tuple(table.columns.keys())) for name, table in candidate.tables.items()} == {
        (name, tuple(table.columns.keys())) for name, table in ordinary.tables.items()
    }


def test_pdf_capture_and_native_contract_share_one_outcome_vocabulary():
    from corpus_structure.semantic.pdf_capture import pdf_capture_inputs

    bundle = pdf_capture_inputs(
        SourceBundle("core", (SourceArtifact("core", running_model().sources["core.yaml"]),))
    )
    prepared = prepare_release(bundle)
    outcome = next(item for item in prepared.vocabularies if item.enum == "PdfObservationOutcome")
    assert {member.value for member in outcome.members} == {
        "succeeded",
        "partial",
        "failed",
        "unknown",
        "unsupported",
    }
    assert not any(item.enum == "DdoPdfObservationOutcome" for item in prepared.vocabularies)
    for root, slots in (
        (
            "data-operation-pdf-capture.yaml",
            (("DdoPdfObservedRequest", "outcome"), ("DdoPdfObservedPage", "outcome")),
        ),
        (
            "pdf-products.yaml",
            (("PdfRecognitionObservation", "outcome"), ("PdfProductHealth", "execution_outcome")),
        ),
    ):
        view = (
            compiled_model({source.name: source.content for source in bundle.sources}).view(
                bundle.root
            )
            if root == "data-operation-pdf-capture.yaml"
            else running_model().view(root)
        )
        enum = view.get_enum("PdfObservationOutcome")
        assert enum is not None
        assert set(enum.permissible_values or {}) == {
            "succeeded",
            "partial",
            "failed",
            "unknown",
            "unsupported",
        }
        for name, slot in slots:
            assert view.induced_slot(slot, name).range == "PdfObservationOutcome"


def test_validity_claim_is_definition_meaning_and_excluded_from_recipe():
    explicit = compile_data_operations(declarations=declarations(operation()))
    claimed = compile_data_operations(
        declarations=declarations(operation(validity_family=["definition", "contextual"]))
    )
    left, right = explicit.operations[0], claimed.operations[0]
    assert right.validity.families == ("contextual", "definition")
    assert right.validity.conservative is False
    assert left.recipe == right.recipe
    assert left.definition != right.definition
    from corpus_structure.semantic.data_operation_model import read_effective_data_operations

    assert read_effective_data_operations(claimed.content).operations[0].validity == right.validity


@pytest.mark.parametrize(
    "claim", [["none", "contextual"], ["undetermined", "contextual"], [], ["rich", "rich"]]
)
def test_validity_claim_rejects_inconsistent_sets(claim):
    with pytest.raises(PreparationError, match="validity_family"):
        compile_data_operations(declarations=declarations(operation(validity_family=claim)))


def test_validity_claim_enforces_declared_requirements():
    with pytest.raises(PreparationError, match="requires profile"):
        compile_data_operations(
            declarations=declarations(
                operation(profile="discovery", validity_family=["definition"])
            )
        )


def test_explicit_undetermined_and_provisional_have_one_advisory():
    unknown = compile_data_operations(
        declarations=declarations(operation(validity_family=["undetermined"]))
    )
    assert unknown.operations[0].validity.conservative
    assert [item.code for item in unknown.diagnostics] == ["validity_undetermined"]
    changed = changed_model(
        "operation-vocabularies.yaml",
        lambda value: value["enums"]["ValidityFamily"]["permissible_values"].update(
            future={"status": "provisional"}
        ),
    )
    pending = compile_data_operations(
        declarations=declarations(operation(validity_family=["future", "definition"])),
        declaration_model=changed,
    )
    assert pending.operations[0].validity.families == ("definition",)
    assert pending.operations[0].validity.conservative
    assert [item.code for item in pending.diagnostics] == ["validity_family_provisional"]


def test_requested_operation_closure_preserves_dependencies_and_alternatives():
    from corpus_structure.semantic.identity import canonical_bytes

    selected = (
        operation(id="root", dependencies=["dependency"], potential_dependencies=["alternative"]),
        operation(id="dependency"),
        operation(id="alternative"),
        operation(id="unrelated"),
    )
    model = compile_data_operations(
        declarations=declarations(*selected),
        captured_contracts=(SourceArtifact("operation-selection.json", canonical_bytes(["root"])),),
    )
    assert {item.semantic_id for item in model.operations} == {"root", "dependency", "alternative"}
    with pytest.raises(PreparationError, match="outside captured"):
        compile_data_operations(
            declarations=declarations(*selected),
            captured_contracts=(
                SourceArtifact("operation-selection.json", canonical_bytes(["missing"])),
            ),
        )


def test_existing_validity_declarations_match_the_reviewed_n29_memberships():
    expected = {
        "record-grade": {"record_policy.grade"},
        "record-fit": {"record_policy.fit"},
        "operation-event": {
            "operation_event.frame",
            "operation_event.fit",
            "operation_event.authorize",
            "urn:corpus:operation:score-operation-event",
        },
        "contextual": {
            "retrieve.contextual_query/declared",
            "retrieve.contextual_query/selected-context",
            "retrieve.contextual_target_vector/declared",
            "retrieve.contextual_vectors/selection",
            "retrieve.contextual_targets/curated",
            "retrieve.contextual_targets/components",
            "retrieve.contextual_target/declared",
            "retrieve.contextual_inventory/declared",
            "retrieve.contextual_scores/declared",
            "retrieve.contextual/declared",
            "retrieve.contextual_witnesses/declared",
            "retrieve.contextual/with-witnesses",
        },
        "definition": {
            "structure.definition_applicability/declared",
            "structure.definition_declaration_components/declared",
            "structure.definition_components/declared",
            "structure.definition_named_components/declared",
        },
        "artifact": {"structure.artifact_identity/declared"},
        "rich": {
            "rich.admit",
            "rich.consolidate",
            "prepare.external_extraction",
            "locate.external_extraction",
        },
    }
    actual = {family: set() for family in expected}
    root = Path(__file__).parents[2] / "src" / "corpus_structure"
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Dict):
                continue
            try:
                record = ast.literal_eval(node)
            except ValueError, TypeError:
                continue
            if (
                not isinstance(record, dict)
                or not {"id", "profile", "capabilities", "behavior"} <= record.keys()
            ):
                continue
            claim = record["validity_family"]
            if claim != ["none"]:
                assert len(claim) == 1
                actual[claim[0]].add(record["id"])
    assert actual == expected
