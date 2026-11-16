"""Independent inherited-environment and authenticated contextual controls."""

import copy
import json
from pathlib import Path

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import occurrence_id
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.formal_products import formal_operation_sources
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies
from corpus_structure.semantic.construction_products import (
    CharacterizationSnapshot,
    ContextualMeaningProduct,
    PreparedConstructionProfile,
    construction_product_inputs,
    contextual_product_values,
    interpreted_member_contracts,
    interpreted_product_value,
    validate_interpreted_product,
)
from corpus_structure.semantic.constructions.evaluation import ContextualEvaluator, environment
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_product_reference import DataProductMemberReference, member_reference
from corpus_structure.semantic.declared_formal_readings import declared_formal_layers
from corpus_structure.semantic.identity import canonical_bytes
from semantic.formal_products_support import publication_context, selected as select_source


@pytest.fixture(scope="module")
def release():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    prepared = prepare_release(
        construction_product_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))),
        data_operation_dependencies(ResolvedDependencies(), python_sources=formal_operation_sources()),
        PreparationProfile(version="semantic-2"),
    )
    return PreparedConstructionProfile(prepared, bound_data_operation_model(prepared))


def literal_facts(release, *, source=None):
    """Independent graph controls positioned in an actual current selected source."""
    source = select_source(release, "all x runs") if source is None else source
    coordinate = source.value["source"]
    selector = source.value["selectors"][0]
    occurrences = []
    for start, end, text in ((0, 3, "all"), (4, 5, "x"), (6, 10, "runs")):
        extents = [dict(
            projection=coordinate["projection"], native_pointer="#/texts/0", page=1,
            start=start, end=end, text=text, synthetic=False,
        )]
        occurrences.append(dict(local_id=occurrence_id(coordinate, extents), extents=extents))

    def term(key, kind, value, children=()):
        return dict(
            local_id=key, kind=kind, value=value, vocabulary="test-linguistic-symbols",
            family="symbols", status="interpreted", occurrences=[occurrences[1]["local_id"]],
            children=[dict(role=role, target=target, structural=True) for role, target in children],
        )

    return dict(
        outcome="complete", occurrences=occurrences, annotations=[], memberships=[], roles=[],
        terms=[
            term("x", "participant", "x"), term("restrictor", "predicate", "trial"),
            term("p", "predicate", "run", [("grammatical_subject", "x")]),
            term("b1", "binder", "all", [("variable", "x"), ("restrictor", "restrictor"), ("body", "p")]),
            term("b2", "binder", "some", [("variable", "x"), ("restrictor", "restrictor"), ("body", "p")]),
            term("a1", "attribution", "Ada reports", [("content", "p")]),
            term("a2", "attribution", "Bea reports", [("content", "p")]),
        ], choices=[],
        coverage=[dict(family="symbols", operation="test.symbols", eligible=[selector],
                       examined=[selector], availability="available", outcome="complete", profile="test")],
    )


def controlled_product(release, facts, *, dependencies=None, source=None):
    """Validate literal nominal packets without claiming native/provider evidence."""
    source = select_source(release, "all x runs") if source is None else source
    dependencies = tuple((dependencies or {}).values())
    value = interpreted_product_value(
        source, copy.deepcopy(facts), interpreted_member_contracts(release.prepared, release.model), dependencies
    )
    return validate_interpreted_product(
        release.prepared, release.model, value, source, dependencies, subject_context=publication_context(source)
    )


def evaluator_for(release, products, *, symbolic_products=None, source=None):
    source = select_source(release, "all x runs") if source is None else source
    return ContextualEvaluator.from_products(
        source,
        tuple(CharacterizationSnapshot(product.semantic_id, product.content) for product in products.values()),
        symbolic_products=symbolic_products,
    )


def evaluated_product(release, products, roots, env, *, symbolic_products=None, source=None):
    source = select_source(release, "all x runs") if source is None else source
    values = tuple(products.values())
    value = contextual_product_values(
        source, tuple(CharacterizationSnapshot(product.semantic_id, product.content) for product in values),
        tuple(products) if symbolic_products is None else symbolic_products,
        interpreted_member_contracts(release.prepared, release.model), roots=roots, env=env,
    )
    return validate_interpreted_product(
        release.prepared, release.model, value, source, values, product_type=ContextualMeaningProduct,
        subject_context=publication_context(source)
    )


def test_shared_symbol_evaluates_under_two_bindings_and_reuses_same_environment(release):
    source = controlled_product(release, literal_facts(release))
    pin = source.reference
    evaluator = evaluator_for(release, {pin: source})
    env = environment()
    first = evaluator.evaluate(member_reference(pin, "b1"), env)
    second = evaluator.evaluate(member_reference(pin, "b2"), env)
    body1 = next(e["target"] for e in evaluator.terms[first]["children"] if e["role"] == "body")
    body2 = next(e["target"] for e in evaluator.terms[second]["children"] if e["role"] == "body")
    assert body1 != body2
    assert evaluator.terms[body1]["value"] == evaluator.terms[body2]["value"] == "run"
    x1 = next(
        e["target"]
        for e in evaluator.terms[body1]["children"]
        if e["role"] == "grammatical_subject"
    )
    x2 = next(
        e["target"]
        for e in evaluator.terms[body2]["children"]
        if e["role"] == "grammatical_subject"
    )
    assert x1 != x2
    assert {
        r["owner"] for r in evaluator.roles.values() if r["role"] == "linguistic-bound-variable"
    } == {x1, x2}
    count = len(evaluator.memo)
    assert evaluator.evaluate(member_reference(pin, "b1"), env) == first
    assert len(evaluator.memo) == count


def test_attribution_environments_are_order_independent_and_do_not_assert_reported_content(release):
    source = controlled_product(release, literal_facts(release))
    pin = source.reference
    left, right = evaluator_for(release, {pin: source}), evaluator_for(release, {pin: source})
    env = environment()
    for key in ("a1", "a2"):
        left.evaluate(member_reference(pin, key), env)
    for key in ("a2", "a1"):
        right.evaluate(member_reference(pin, key), env)
    assert left.terms == right.terms
    assert left.roles == right.roles
    reported = [t for t in left.terms.values() if t["value"] == "run"]
    assert len(reported) == 2
    assert all(t["status"] == "private_proposal" for t in reported)


def context_facts(release, pin):
    data = literal_facts(release)
    data["terms"] = []
    data["coverage"][0]["family"] = "context.binding"
    occurrence = data["occurrences"][1]["local_id"]

    def proxy(key, target):
        return dict(
            local_id=key,
            kind="context.symbolic_site",
            family="context.binding",
            vocabulary="contextual-source-hypotheses-1",
            status="private_proposal",
            occurrences=[occurrence],
            external_premises=[member_reference(pin, target).values()],
        )

    data["annotations"] = [
        proxy("owner", "b1"),
        proxy("member", "x"),
        proxy("wrong", "p"),
        dict(
            local_id="hypothesis",
            kind="contextual.binding_hypothesis",
            family="context.binding",
            vocabulary="contextual-source-hypotheses-1",
            status="private_proposal",
            native_scheme="contextual-source-hypotheses-1",
            native_label="declared_binding_site",
            occurrences=[occurrence],
            premises=["owner", "member"],
        ),
    ]
    data["roles"] = [
        dict(
            local_id="binding-role",
            owner="owner",
            member="member",
            role="declared_binding_site",
            family="context.binding",
            scheme="contextual-source-hypotheses-1",
            occurrences=[occurrence],
            basis=dict(
                kind="contextual_proposal", status="private_proposal", premises=["hypothesis"]
            ),
        )
    ]
    return data


def test_contextual_selected_role_keeps_private_standing_and_rejects_wrong_endpoint(release):
    source = controlled_product(release, literal_facts(release))
    pin = source.reference
    data = context_facts(release, pin)
    context = controlled_product(release, data, dependencies={pin: source})
    cpin = context.reference
    selected = environment(
        context_layers=(cpin,), hypotheses=(member_reference(cpin, "binding-role"),)
    )
    evaluator = evaluator_for(release, {pin: source, cpin: context})
    root = evaluator.evaluate(member_reference(pin, "b1"), selected)
    assert (
        next(r for r in evaluator.roles.values() if r["owner"] == root)["basis"]["status"]
        == "private_proposal"
    )
    invalid = copy.deepcopy(data)
    invalid["roles"][0]["member"] = "wrong"
    broken = controlled_product(release, invalid, dependencies={pin: source})
    bpin = broken.reference
    with pytest.raises(ValueError, match="endpoints differ"):
        evaluator_for(release, {pin: source, bpin: broken}).evaluate(
            member_reference(pin, "b1"),
            environment(
                context_layers=(bpin,), hypotheses=(member_reference(bpin, "binding-role"),)
            ),
        )


def test_evaluated_layer_uses_retained_shapes_and_exact_dependencies(release):
    source = controlled_product(release, literal_facts(release))
    pin = source.reference
    result = evaluated_product(release, {pin: source}, [member_reference(pin, "b1")], environment())
    assert json.loads(result.content)["dependencies"] == [pin.values()]
    assert result.inventory()["roles"]
    assert all(r["basis"]["status"] == "private_proposal" for r in result.inventory()["roles"])


def test_model_candidate_role_authenticates_selected_frozen_endpoints(release):
    from hashlib import sha256

    from corpus_structure.semantic.observations import source_value

    source = controlled_product(release, literal_facts(release))
    pin = source.reference
    data = context_facts(release, pin)
    focus = dict(reference=member_reference(pin, "x").values())
    candidate = dict(
        key="offered_host",
        compatibility="exclusive",
        members=[dict(reference=member_reference(pin, "p").values())],
    )
    candidate_digest = sha256(
        canonical_bytes(dict(focus=focus, alternatives=[candidate]))
    ).hexdigest()
    frozen = dict(
        focus=focus,
        candidates=[candidate],
        candidate_list_digest=candidate_digest,
        frozen_candidates=dict(focus=focus, alternatives=[candidate]),
    )
    request = dict(interpretation=frozen)
    occurrence = data["occurrences"][1]["local_id"]
    annotations = data["annotations"]
    annotations[0]["kind"] = "model.focus"
    annotations[0]["external_premises"] = [member_reference(pin, "x").values()]
    annotations[1]["kind"] = "model.candidate"
    annotations[1]["external_premises"] = [member_reference(pin, "p").values()]
    data["annotations"] = [
        *annotations[:3],
        dict(
            local_id="question",
            kind="model.question",
            vocabulary="character_host_choice_v1",
            family="context.binding",
            status="native_evidence",
            occurrences=[occurrence],
            model_answer=dict(
                family="character_host_choice_v1",
                question_key="host",
                declaration_digest="d" * 64,
                stage="0",
                answer_kind="choice",
                state="proposed",
                request_digest=sha256(
                    json.dumps(
                        request, ensure_ascii=False, separators=(",", ":"), allow_nan=False
                    ).encode()
                ).hexdigest(),
                native_answer=source_value(dict(request=request)),
                candidate_list_digest=candidate_digest,
                source_field="/source",
                selected_keys=["offered_host"],
            ),
        ),
        dict(
            local_id="proposal",
            kind="model.choice_proposal",
            vocabulary="character_host_choice_v1",
            family="context.binding",
            status="private_proposal",
            occurrences=[occurrence],
            native_label="offered_host",
            premises=["question"],
        ),
    ]
    data["roles"][0].update(
        role="unresolved_host",
        scheme="character_host_choice_v1",
        basis=dict(
            kind="contextual_proposal", status="private_proposal", premises=["question", "proposal"]
        ),
    )
    context = controlled_product(release, data, dependencies={pin: source})
    cpin = context.reference
    env = environment(
        context_layers=(cpin,), hypotheses=(member_reference(cpin, "binding-role"),)
    )
    evaluator = evaluator_for(release, {pin: source, cpin: context})
    root = evaluator.evaluate(member_reference(pin, "x"), env)
    assert any(
        r["owner"] == root and r["role"] == "unresolved_host" for r in evaluator.roles.values()
    )
    ordinary = evaluator_for(release, {pin: source, cpin: context})
    default_root = ordinary.evaluate(
        member_reference(pin, "x"), environment(context_layers=(cpin,))
    )
    assert any(
        r["owner"] == default_root and r["role"] == "unresolved_host"
        for r in ordinary.roles.values()
    )
    invalid = copy.deepcopy(data)
    invalid["annotations"][1]["external_premises"] = [
        member_reference(pin, "restrictor").values()
    ]
    broken = controlled_product(release, invalid, dependencies={pin: source})
    bpin = broken.reference
    with pytest.raises(ValueError, match="frozen alternative"):
        evaluator_for(release, {pin: source, bpin: broken}).evaluate(
            member_reference(pin, "x"),
            environment(
                context_layers=(bpin,), hypotheses=(member_reference(bpin, "binding-role"),)
            ),
        )


def test_packed_contextual_choice_preserves_upstream_requirements_and_unresolved_site(release):
    from corpus_structure.semantic.characterization import project_reading

    data = literal_facts(release)
    for key in ("left", "right"):
        data["terms"].append(
            dict(
                local_id=key,
                kind="predicate",
                vocabulary="test",
                family="symbols",
                value=key,
                status="interpreted",
                occurrences=[data["occurrences"][2]["local_id"]],
                required_choices=["select-" + key],
            )
        )
    data["terms"].append(
        dict(
            local_id="packed",
            kind="operator",
            vocabulary="test",
            family="symbols",
            value="attachment-choice",
            status="unknown",
            occurrences=[data["occurrences"][2]["local_id"]],
            children=[dict(role="target", choice_group="site", structural=True)],
        )
    )
    data["choices"] = [
        dict(
            local_id="site",
            compatibility="exclusive",
            family="symbols",
            members=[dict(local_id="select-" + key, root=key) for key in ("left", "right")],
        )
    ]
    source = controlled_product(release, data)
    pin = source.reference
    report = evaluated_product(release, {pin: source}, [member_reference(pin, "packed")], environment())
    root = next(
        t["local_id"] for t in report.inventory()["terms"] if t["value"] == "contextual-reading"
    )
    readings = declared_formal_layers((source, report), select_source(release, "all x runs"))
    assert project_reading(readings[report.reference], root, dependencies=readings)["outcome"] == "partial"
    group = report.inventory()["choices"][0]
    selected = group["members"][0]
    required = selected["required_external_choices"][0]
    reading = project_reading(
        readings[report.reference],
        root,
        choices=[selected["local_id"]],
        dependencies=readings,
        external_choices=[member_reference(pin, required["member_id"])],
    )
    assert reading["outcome"] == "complete"
    assert len([t for t in reading["terms"] if t["value"] in {"left", "right"}]) == 1
    with pytest.raises(ValueError, match="incompatible"):
        evaluator_for(release, {pin: source}).evaluate(
            member_reference(pin, "packed"),
            environment(
                choices=(
                    member_reference(pin, "select-left"),
                    member_reference(pin, "select-right"),
                )
            ),
        )


def test_context_failure_preserves_local_meaning_and_marks_dependent_family(release):
    source = controlled_product(release, literal_facts(release))
    pin = source.reference
    data = context_facts(release, pin)
    data["outcome"] = "partial"
    data["coverage"][0].update(
        outcome="failed", availability="unavailable", reason="provider runtime unavailable"
    )
    context = controlled_product(release, data, dependencies={pin: source})
    cpin = context.reference
    report = evaluated_product(release, {pin: source, cpin: context}, [member_reference(pin, "p")], environment(context_layers=(cpin,)))
    coverage = {r["family"]: r for r in report.value.model_dump(mode="python")["coverage"]}
    assert coverage["meaning.reference"]["outcome"] == "partial"
    assert coverage["meaning.predication"]["outcome"] == "complete"
    assert any(t["value"] == "run" for t in report.inventory()["terms"])


def test_context_layer_candidates_participate_by_default_without_forced_selection(release):
    source = controlled_product(release, literal_facts(release))
    pin = source.reference
    data = context_facts(release, pin)
    context = controlled_product(release, data, dependencies={pin: source})
    cpin = context.reference
    evaluator = evaluator_for(release, {pin: source, cpin: context})
    root = evaluator.evaluate(member_reference(pin, "b1"), environment(context_layers=(cpin,)))
    assert any(
        r["owner"] == root and r["role"] == "declared_binding_site"
        for r in evaluator.roles.values()
    )


def test_available_rival_hypotheses_keep_separate_upstream_choice_requirements(release):
    data = literal_facts(release)
    for node in data["terms"]:
        if node["local_id"] in {"b1", "b2"}:
            node["required_choices"] = ["select-" + node["local_id"]]
    data["terms"].append(
        dict(
            local_id="packed",
            kind="operator",
            vocabulary="test",
            family="symbols",
            value="scope-site",
            status="unknown",
            occurrences=[data["occurrences"][1]["local_id"]],
            children=[dict(role="reading", choice_group="site", structural=True)],
        )
    )
    data["choices"] = [
        dict(
            local_id="site",
            compatibility="exclusive",
            family="symbols",
            members=[dict(local_id="select-" + key, root=key) for key in ("b1", "b2")],
        )
    ]
    source = controlled_product(release, data)
    pin = source.reference
    context_data = context_facts(release, pin)
    context_data["roles"][0]["required_external_choices"] = [
        member_reference(pin, "select-b1").values()
    ]
    owner = copy.deepcopy(context_data["annotations"][0])
    owner.update(local_id="owner2", external_premises=[member_reference(pin, "b2").values()])
    hypothesis = copy.deepcopy(context_data["annotations"][-1])
    hypothesis.update(local_id="hypothesis2", premises=["owner2", "member"])
    context_data["annotations"].extend([owner, hypothesis])
    role = copy.deepcopy(context_data["roles"][0])
    role.update(
        local_id="binding-role2",
        owner="owner2",
        required_external_choices=[member_reference(pin, "select-b2").values()],
        basis=dict(kind="contextual_proposal", status="private_proposal", premises=["hypothesis2"]),
    )
    context_data["roles"].append(role)
    context = controlled_product(release, context_data, dependencies={pin: source})
    cpin = context.reference
    evaluator = evaluator_for(release, {pin: source, cpin: context})
    evaluator.evaluate(member_reference(pin, "packed"), environment(context_layers=(cpin,)))
    bindings = [r for r in evaluator.roles.values() if r["role"] == "declared_binding_site"]
    assert len(bindings) == 2
    assert {tuple(c["member_id"] for c in r["required_external_choices"]) for r in bindings} == {
        ("select-b1",),
        ("select-b2",),
    }


def test_source_first_functions_evaluate_without_any_symbolic_roots(release):
    from corpus_structure.semantic.observations import source_value

    data = literal_facts(release)
    occurrence = data["occurrences"][1]["local_id"]
    family = "character_function_v1"
    data["terms"] = []
    data["coverage"][0].update(family=family, operation="text.model_characterization")
    data["annotations"] = [
        dict(
            local_id="question",
            kind="model.question",
            vocabulary=family,
            family=family,
            status="native_evidence",
            occurrences=[occurrence],
            model_answer=dict(
                family=family,
                question_key="function",
                declaration_digest="d" * 64,
                stage="0",
                answer_kind="choice",
                state="proposed",
                request_digest="e" * 64,
                native_answer=source_value(dict()),
                source_field="/source",
                selected_keys=["assertion", "definition"],
            ),
        ),
        dict(
            local_id="proposal",
            kind="model.choice_proposal",
            vocabulary=family,
            family=family,
            status="private_proposal",
            occurrences=[occurrence],
            native_label="function",
            premises=["question"],
        ),
    ]
    model = controlled_product(release, data)
    pin = model.reference
    report = evaluated_product(release, {pin: model}, [], environment(context_layers=(pin,)))
    assert {t["value"] for t in report.inventory()["terms"]} >= {
        "function:assertion",
        "function:definition",
    }
    coverage = {r["family"]: r for r in report.value.model_dump(mode="python")["coverage"]}
    assert coverage["meaning.function"]["outcome"] == "complete"
    assert coverage["meaning.predication"]["outcome"] == "unknown"
    assert coverage["meaning.predication"]["availability"] == "unavailable"


@pytest.mark.parametrize(
    "selection,outer,inner",
    [
        ("negative_over_quantifier", "operator", "binder"),
        ("quantifier_over_negative", "binder", "operator"),
    ],
)
def test_staged_source_first_scope_builds_private_nested_terms_from_actual_question_links(
    release, selection, outer, inner
):
    from corpus_structure.semantic.observations import source_value

    data = literal_facts(release)
    family = "character_scope_v1"
    text = "not all x runs"
    selected_source = select_source(release, text)
    data["coverage"][0].update(family=family, operation="text.model_characterization")
    data["terms"] = []
    data["annotations"] = []
    data["occurrences"] = []
    seen = {}

    def occurrence(a, b):
        if (a, b) not in seen:
            extents = [
                dict(
                    projection=selected_source.value["source"]["projection"],
                    native_pointer="#/texts/0",
                    page=1,
                    start=a,
                    end=b,
                    text=text[a:b],
                    synthetic=False,
                )
            ]
            key = occurrence_id(selected_source.value["source"], extents)
            seen[a, b] = key
            data["occurrences"].append(dict(local_id=key, extents=extents))
        return seen[a, b]

    fields = [
        ("quantifier_cue", 4, 7, ()),
        ("negative_cue", 0, 3, ()),
        ("bound_participant", 8, 9, ("quantifier_cue",)),
        ("restrictor", 8, 9, ("quantifier_cue",)),
        ("quantifier_body", 8, 14, ("quantifier_cue",)),
    ]
    for name, a, b, depends in fields:
        oid = occurrence(a, b)
        data["annotations"].extend(
            [
                dict(
                    local_id="q-" + name,
                    kind="model.question",
                    family=family,
                    vocabulary=family,
                    status="native_evidence",
                    occurrences=[oid],
                    model_answer=dict(
                        family=family,
                        question_key=name,
                        declaration_digest="d" * 64,
                        stage="0" if not depends else "1",
                        answer_kind="text",
                        state="proposed",
                        request_digest="e" * 64,
                        native_answer=source_value({}),
                        source_field="/source",
                        depends_on=["q-" + key for key in depends],
                    ),
                ),
                dict(
                    local_id="p-" + name,
                    kind="model.span_proposal",
                    family=family,
                    vocabulary=family,
                    native_label=name,
                    status="private_proposal",
                    occurrences=[oid],
                    premises=["q-" + name],
                ),
            ]
        )
    oid = occurrence(0, len(text))
    data["annotations"].extend(
        [
            dict(
                local_id="q-scope",
                kind="model.question",
                family=family,
                vocabulary=family,
                status="native_evidence",
                occurrences=[oid],
                model_answer=dict(
                    family=family,
                    question_key="relative_scope",
                    declaration_digest="d" * 64,
                    stage="2",
                    answer_kind="choice",
                    state="proposed",
                    request_digest="e" * 64,
                    native_answer=source_value({}),
                    source_field="/source",
                    selected_keys=[selection],
                    depends_on=["q-quantifier_cue", "q-negative_cue"],
                ),
            ),
            dict(
                local_id="p-scope",
                kind="model.choice_proposal",
                family=family,
                vocabulary=family,
                native_label="relative_scope",
                status="private_proposal",
                occurrences=[oid],
                premises=["q-scope"],
            ),
        ]
    )
    data["coverage"][0].update(eligible=selected_source.value["selectors"], examined=selected_source.value["selectors"])
    report = controlled_product(release, data, source=selected_source)
    pin = report.reference
    result = evaluated_product(release, {pin: report}, [], environment(context_layers=(pin,)), source=selected_source)
    terms = {t["local_id"]: t for t in result.inventory()["terms"]}
    meaning = next(t for t in terms.values() if t["value"] == "relative_scope:" + selection)
    root = terms[next(e["target"] for e in meaning["children"] if e["role"] == "scoped_proposal")]
    assert root["kind"] == outer
    child = terms[
        next(
            e["target"]
            for e in root["children"]
            if e["role"] == ("target" if outer == "operator" else "body")
        )
    ]
    assert child["kind"] == inner
    assert root["status"] == child["status"] == "private_proposal"


def test_provenance_only_symbol_layer_is_not_an_implicit_reading(release):
    old = controlled_product(release, literal_facts(release))
    old_pin = old.reference
    data = literal_facts(release)
    source = controlled_product(release, data, dependencies={old_pin: old})
    pin = source.reference
    assert pin != old_pin
    assert source.inventory() == old.inventory()
    evaluator = evaluator_for(release, {old_pin: old, pin: source}, symbolic_products=(pin,))
    roots = evaluator.default_roots(environment())
    assert roots and all(isinstance(ref, DataProductMemberReference) for ref in roots)
    assert {ref.product for ref in roots} == {pin}
    result = evaluated_product(release, {old_pin: old, pin: source}, [], environment(), symbolic_products=(pin,))
    assert {ref["product_id"] for ref in json.loads(result.content)["dependencies"]} == {old.semantic_id, source.semantic_id}
    assert all(
        ref["product_id"] == source.semantic_id
        for term in result.inventory()["terms"]
        for ref in term.get("external_premises", ())
    )
