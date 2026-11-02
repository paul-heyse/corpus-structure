"""Independent context, demand and authored-support counterexamples."""

from dataclasses import replace

import pytest
import yaml

from corpus_structure.semantic.analysis_contracts import (
    bind_analysis_family,
    prepare_interpretation_context,
)
from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import PreparationError, RegistryRow


def context(**kwargs):
    return prepare_interpretation_context(macros={}, **kwargs)


def source_role(role, **extra):
    return {
        "symbol": "f",
        "role": role,
        "authority": "source",
        "evidence": "observation:1",
        "source_id": "rendition:1",
        "scope": "statement:1",
        **extra,
    }


def test_function_without_entity_and_scoped_authority():
    function = context(
        source_id="rendition:1", scope="statement:1", declarations=[source_role("function")]
    )
    variable = context(
        source_id="rendition:1", scope="statement:1", declarations=[source_role("variable")]
    )
    assert "f" in function.grammar_context.functions
    assert "f" in variable.grammar_context.variables
    assert function.key() != variable.key()
    outside = context(
        source_id="rendition:2", scope="statement:1", declarations=[source_role("function")]
    )
    assert "f" not in outside.grammar_context.functions


def test_conflicting_evidence_retains_ambiguity():
    prepared = context(
        source_id="rendition:1",
        scope="statement:1",
        declarations=[source_role("function"), source_role("variable", evidence="observation:2")],
    )
    assert prepared.conflicts == {"f"}
    assert "f" not in prepared.grammar_context.functions | prepared.grammar_context.variables


def test_binding_semantic_identity_is_a_dependency():
    a = context(bindings=[{"kind": "variable", "symbol": "x", "entity": "entity:a"}])
    b = context(bindings=[{"kind": "variable", "symbol": "x", "entity": "entity:b"}])
    assert a.key() != b.key()
    assert a.stage_key("lexical") == b.stage_key("lexical")
    unresolved = context(bindings=[{"kind": "unresolved", "symbol": "x"}])
    assert "x" not in unresolved.grammar_context.variables
    assert unresolved.unresolved == {"x"}


def test_role_defaults_yield_to_explicit_evidenced_declaration():
    prepared = context(
        source_id="rendition:1",
        scope="statement:1",
        bindings=[{"kind": "variable", "symbol": "f", "entity": "entity:f"}],
        declarations=[source_role("function")],
    )
    assert "f" in prepared.grammar_context.functions
    assert "f" not in prepared.grammar_context.variables


def test_source_declaration_requires_custody_and_ordered_extent():
    with pytest.raises(PreparationError):
        context(
            declarations=[
                {
                    "symbol": "f",
                    "role": "function",
                    "authority": "source",
                    "evidence": "observation:1",
                }
            ]
        )
    with pytest.raises(PreparationError):
        context(declarations=[source_role("function", start=12, end=3)])
    prepared = context(
        source_id="rendition:1",
        scope="statement:1",
        offset=20,
        declarations=[source_role("function", start=1, end=10)],
    )
    assert "f" not in prepared.grammar_context.functions


def test_demand_completion_is_separate_from_interpretation():
    occurrences = context(demand="occurrences")
    occurrences.validate_result(
        produced=["lexical", "syntax", "occurrences"], interpretation="unanalysed"
    )
    with pytest.raises(PreparationError):
        occurrences.validate_result(
            produced=["lexical", "occurrences"], interpretation="unanalysed"
        )
    with pytest.raises(PreparationError):
        occurrences.validate_result(
            produced=["lexical", "syntax", "occurrences"], interpretation="ok"
        )
    with pytest.raises(PreparationError):
        context(demand="symbolic").validate_result(
            produced=["lexical", "syntax", "occurrences", "interpretation"], interpretation="ok"
        )
    context(demand="symbolic").validate_result(
        produced=[], interpretation="unsupported", completeness="unsupported"
    )
    with pytest.raises(PreparationError):
        context(demand="invented")


def test_scientific_key_requires_policy_and_conditions():
    prepared = context()
    with pytest.raises(PreparationError):
        prepared.stage_key("scientific")
    first = prepared.stage_key(
        "scientific", conditions=[], precision=30, sampling="seeded-1", decision_policy="reference"
    )
    second = prepared.stage_key(
        "scientific", conditions=[], precision=50, sampling="seeded-1", decision_policy="reference"
    )
    assert first != second


def test_dependency_and_callable_capabilities_are_not_self_attested():
    inputs = trusted_execution_inputs()
    body = yaml.safe_load(inputs.catalog.content)
    occurrences = next(
        d for d in body["analysis_profiles"][0]["demands"] if d["id"] == "occurrences"
    )
    occurrences["dependencies"].remove("scope")
    with pytest.raises(PreparationError, match="consequential dependencies"):
        compile_execution_model(
            replace(inputs, catalog=replace(inputs.catalog, content=yaml.safe_dump(body).encode()))
        )


def test_owned_input_enforces_exact_release_and_dependencies():
    model = compile_execution_model(trusted_execution_inputs())
    base = prepare_release(trusted_execution_inputs().schema)
    prepared = replace(
        base,
        release_id="release:1",
        execution_model_id=model.model_id,
        registry_rows=(
            *base.registry_rows,
            RegistryRow("execution_model", model.model_id, model.content),
        ),
    )
    owner = bind_analysis_family(prepared, "publication")
    owned = owner.prepare(release="release:1", snapshot="snapshot:1", content="sha256:1")
    assert owned.family == "publication"
    assert owned.lifetime == "operation"
    with pytest.raises(PreparationError):
        owner.prepare(release="release:2", snapshot="snapshot:1", content="sha256:1")
    with pytest.raises(PreparationError):
        owner.prepare(release="release:1", content="sha256:1")


def test_schema_only_and_retired_composed_profiles_refuse_execution():
    base = prepare_release(trusted_execution_inputs().schema)
    with pytest.raises(PreparationError, match="composed execution binding"):
        prepare_interpretation_context(base, macros={})
    import json

    from corpus_structure.semantic.identity import canonical_bytes

    historical_manifest = json.loads(base.manifest)
    historical_manifest["profile"]["compiler_version"] = "12"
    with pytest.raises(PreparationError):
        prepare_interpretation_context(
            replace(base, manifest=canonical_bytes(historical_manifest)), macros={}
        )
    model = compile_execution_model(trusted_execution_inputs())
    historic = json.loads(model.content)
    for effect in historic["effect_definitions"]:
        if effect["id"] == "schedule_pending_or_reused_or_skipped":
            effect["version"] = "1"
    historic["inputs"]["compiler_version"] = "4"
    historic.pop("analysis_profiles")
    archived = replace(
        base,
        execution_model_id=model.model_id,
        registry_rows=(
            *base.registry_rows,
            RegistryRow("execution_model", model.model_id, canonical_bytes(historic)),
        ),
    )
    with pytest.raises(PreparationError, match="current compiler 23; regenerate the release"):
        prepare_interpretation_context(archived, macros={})


def test_unknown_result_and_binding_kind_refuse():
    with pytest.raises(PreparationError):
        context().validate_result(
            produced=["lexical", "occurrences", "interpretation"], interpretation="invented"
        )
    with pytest.raises(PreparationError):
        context(bindings=[{"kind": "invented", "symbol": "x"}])


def test_caller_cannot_override_prepared_dependency_identity():
    prepared = context()
    for name in ("grammar", "profile", "macros", "declarations"):
        with pytest.raises(PreparationError):
            prepared.stage_key("scientific", **{name: "forged"})


def test_ownership_declaration_cannot_change_implemented_lifetime():
    inputs = trusted_execution_inputs()
    body = yaml.safe_load(inputs.catalog.content)
    body["analysis_profiles"][0]["ownership"][3]["lifetime"] = "batch"
    with pytest.raises(PreparationError, match="producer/consumer ownership"):
        compile_execution_model(
            replace(inputs, catalog=replace(inputs.catalog, content=yaml.safe_dump(body).encode()))
        )


def test_unknown_execution_abi_refuses_before_model_binding():
    import json

    from corpus_structure.semantic.contracts import _bound_execution_model
    from corpus_structure.semantic.identity import canonical_bytes

    model = compile_execution_model(trusted_execution_inputs())
    changed = json.loads(model.content)
    changed["inputs"]["compiler_version"] = "999"
    with pytest.raises(PreparationError, match="current compiler 23; regenerate the release"):
        _bound_execution_model(canonical_bytes(changed), model.model_id)


@pytest.mark.parametrize("authority", ["profile", "expression_local", "binding"])
def test_external_declarations_cannot_claim_owned_authority(authority):
    declaration = source_role("function", authority=authority, evidence="made-up")
    with pytest.raises(PreparationError, match="external declarations require source evidence"):
        context(source_id="rendition:1", scope="statement:1", declarations=[declaration])


def test_historical_abi_cannot_self_attest_analysis_capabilities():
    import json

    from corpus_structure.semantic.identity import canonical_bytes

    base = prepare_release(trusted_execution_inputs().schema)
    model = compile_execution_model(trusted_execution_inputs())
    changed = json.loads(model.content)
    for effect in changed["effect_definitions"]:
        if effect["id"] == "schedule_pending_or_reused_or_skipped":
            effect["version"] = "1"
    changed["inputs"]["compiler_version"] = "4"
    # Leave all compiler-5 declarations present: their presence does not grant support.
    archived = replace(
        base,
        execution_model_id=model.model_id,
        registry_rows=(
            *base.registry_rows,
            RegistryRow("execution_model", model.model_id, canonical_bytes(changed)),
        ),
    )
    with pytest.raises(PreparationError, match="current compiler 23; regenerate the release"):
        prepare_interpretation_context(archived, macros={})


def test_explicit_implementation_bytes_are_part_of_identity_and_runtime_support():

    from corpus_structure.semantic.types import RegistryRow

    inputs = trusted_execution_inputs()
    model = compile_execution_model(inputs)
    changed_inputs = replace(
        inputs,
        implementations=(
            replace(inputs.implementations[0], content=inputs.implementations[0].content + b"\n"),
            *inputs.implementations[1:],
        ),
    )
    changed = compile_execution_model(changed_inputs)
    assert model.model_id != changed.model_id
    base = prepare_release(inputs.schema)
    prepared = replace(
        base,
        execution_model_id=changed.model_id,
        registry_rows=(
            *base.registry_rows,
            RegistryRow("execution_model", changed.model_id, changed.content),
        ),
    )
    with pytest.raises(PreparationError, match="admitted implementation bytes"):
        prepare_interpretation_context(prepared, macros={})


def test_scientific_profile_and_source_sharing_are_admitted_data():
    from corpus_structure.semantic.analysis_contracts import scientific_computation_profile

    computation = scientific_computation_profile("reference-evidence-2")
    assert computation.minimum_valid_points == 12
    assert computation.numeric_requires == "no-restrictions"
    assert context().profile.shared_consumers == ("normalize.formula", "extract.math")


def test_candidate_scientific_parameters_rebind_supplied_recipe_without_ambient_acquisition(
    monkeypatch,
):
    import json
    from pathlib import Path

    from corpus_structure.semantic.analysis_contracts import scientific_computation_profile
    from corpus_structure.semantic.regeneration import acquire_pack, compose_pack_inputs
    from corpus_structure.semantic.scientific_evidence import require_scientific_policy

    pack = Path(__file__).resolve().parents[4] / "domains/statistics"
    acquired = acquire_pack(pack)
    data = yaml.safe_load(acquired.execution.catalog.content)
    data["analysis_profiles"][0]["scientific_profiles"][0]["minimum_valid_points"] = 7
    execution = replace(
        acquired.execution,
        catalog=replace(acquired.execution.catalog, content=yaml.safe_dump(data).encode()),
    )
    candidate = replace(acquired, execution=execution)
    monkeypatch.setattr(
        "corpus_structure.semantic.regeneration.trusted_execution_inputs",
        lambda: pytest.fail("composition acquired installed inputs"),
    )
    bundle, dependencies, profile = compose_pack_inputs((candidate,))
    prepared = prepare_release(bundle, dependencies, profile)
    recipe = next(
        item for item in prepared.artifacts if item.kind == "operation/scientific-policy.json"
    )
    decoded = json.loads(recipe.content)
    assert decoded["consolidation"]["minimum_valid_points"] == 7
    assert decoded["computation_profiles"][0]["minimum_valid_points"] == 7
    assert (
        scientific_computation_profile("consolidation-evidence-2", prepared).minimum_valid_points
        == 7
    )
    require_scientific_policy(prepared)
    decoded["consolidation"]["minimum_valid_points"] = 6
    from corpus_structure.semantic.identity import canonical_bytes

    altered = replace(
        prepared,
        artifacts=tuple(
            replace(item, content=canonical_bytes(decoded)) if item is recipe else item
            for item in prepared.artifacts
        ),
    )
    with pytest.raises(ValueError, match="recipe is unsupported"):
        require_scientific_policy(altered)


def test_current_compilation_and_preparation_refuse_retained_analysis_profile():
    import json

    from corpus_structure.semantic.identity import canonical_bytes

    inputs = trusted_execution_inputs()
    data = yaml.safe_load(inputs.catalog.content)
    data["analysis_profiles"][0]["version"] = "1"
    with pytest.raises(PreparationError, match="required analysis preparation profile"):
        compile_execution_model(
            replace(inputs, catalog=replace(inputs.catalog, content=yaml.safe_dump(data).encode()))
        )
    current = compile_execution_model(inputs)
    body = json.loads(current.content)
    body["analysis_profiles"][0]["version"] = "1"
    base = prepare_release(inputs.schema)
    altered = replace(
        base,
        execution_model_id=current.model_id,
        registry_rows=(
            *base.registry_rows,
            RegistryRow("execution_model", current.model_id, canonical_bytes(body)),
        ),
    )
    # Retained profiles cannot supply current analytical execution authority.
    with pytest.raises(PreparationError, match="admitted analysis profile"):
        prepare_interpretation_context(altered, macros={})


def test_invocation_identity_is_disjoint_and_binds_complete_decisions():
    from corpus_structure.semantic.analysis_contracts import invocation_identity

    dependencies = dict(
        source={"revision": 1},
        configuration={"method": "agent.opus", "model": "declared"},
        policy={"classification": "unknown", "limit": 1},
        unit={"id": 3},
    )
    skipped = invocation_identity(
        None, release="release:one", **dependencies, skip_reason="limit", packet_hash=None
    )
    executable = invocation_identity(
        None, release="release:one", **dependencies, skip_reason=None, packet_hash="packet:one"
    )
    assert skipped != executable
    for key, replacement in (
        ("source", {"revision": 2}),
        ("configuration", {"model": "other"}),
        ("policy", {"classification": "known", "limit": 1}),
        ("unit", {"id": 4}),
    ):
        assert (
            invocation_identity(
                None,
                release="release:one",
                **{**dependencies, key: replacement},
                skip_reason="limit",
                packet_hash=None,
            )
            != skipped
        )
    with pytest.raises(ValueError, match="packet presence"):
        invocation_identity(
            None, release="release:one", **dependencies, skip_reason="limit", packet_hash="forged"
        )
    with pytest.raises(ValueError, match="packet presence"):
        invocation_identity(
            None, release="release:one", **dependencies, skip_reason=None, packet_hash=None
        )
