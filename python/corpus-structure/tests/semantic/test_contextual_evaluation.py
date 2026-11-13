"""Independent inherited-environment and authenticated contextual controls."""

import copy
from pathlib import Path

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import (
    AnnotationReference,
    characterization_inputs,
    occurrence_id,
    validate_layer,
)
from corpus_structure.semantic.constructions.evaluation import ContextualEvaluator, environment


@pytest.fixture(scope="module")
def release():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )


def payload(release):
    base = dict(task_id=7, product_key="document", content_digest="a" * 64)
    projection = "b" * 64
    selector = dict(projection=projection, native_pointer="#/texts/0", start=0, end=10)
    scope = dict(
        source_view_ids=[11],
        source_views=[
            dict(
                source_view_id=11,
                key="source",
                base_document=base,
                section_pointer="#/groups/0",
                membership="descendants",
                projection_digest=projection,
                recipe_digest="c" * 64,
            )
        ],
        profile="full",
        selectors=[selector],
    )
    occurrences = []
    for start, end, text in ((0, 3, "all"), (4, 5, "x"), (6, 10, "runs")):
        extents = [
            dict(
                projection=projection,
                source_view_id=11,
                native_pointer="#/texts/0",
                page=3,
                start=start,
                end=end,
                text=text,
                synthetic=False,
            )
        ]
        occurrences.append(dict(local_id=occurrence_id(base, extents), extents=extents))

    def term(key, kind, value, children=()):
        return dict(
            local_id=key,
            kind=kind,
            value=value,
            vocabulary="test-linguistic-symbols",
            family="symbols",
            status="interpreted",
            occurrences=[occurrences[1]["local_id"]],
            children=[dict(role=role, target=target, structural=True) for role, target in children],
        )

    terms = [
        term("x", "participant", "x"),
        term("restrictor", "predicate", "trial"),
        term("p", "predicate", "run", [("grammatical_subject", "x")]),
        term(
            "b1", "binder", "all", [("variable", "x"), ("restrictor", "restrictor"), ("body", "p")]
        ),
        term(
            "b2", "binder", "some", [("variable", "x"), ("restrictor", "restrictor"), ("body", "p")]
        ),
        term("a1", "attribution", "Ada reports", [("content", "p")]),
        term("a2", "attribution", "Bea reports", [("content", "p")]),
    ]
    operation = dict(
        key="test.symbols",
        version="1",
        runtime="test",
        model="none",
        grammar="symbols-1",
        configuration="cfg",
        input="input",
        context="source",
        produced_families=["symbols"],
        result_determinants=["grammar", "input"],
        outcomes=["complete", "partial", "failed"],
    )
    return dict(
        format="characterization-layer-v1",
        base_document=base,
        release_id=release.release_id,
        source_scope=scope,
        operation=operation,
        outcome="complete",
        occurrences=occurrences,
        annotations=[],
        memberships=[],
        roles=[],
        terms=terms,
        choices=[],
        dependencies=[],
        coverage=[
            dict(
                family="symbols",
                operation="test.symbols",
                eligible=[selector],
                examined=[selector],
                availability="available",
                outcome="complete",
                profile="test",
            )
        ],
    )


def test_shared_symbol_evaluates_under_two_bindings_and_reuses_same_environment(release):
    source = validate_layer(release, payload(release))
    pin = source.reference(101)
    evaluator = ContextualEvaluator({pin: source})
    env = environment()
    first = evaluator.evaluate(AnnotationReference(pin, "b1"), env)
    second = evaluator.evaluate(AnnotationReference(pin, "b2"), env)
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
    assert evaluator.evaluate(AnnotationReference(pin, "b1"), env) == first
    assert len(evaluator.memo) == count


def test_attribution_environments_are_order_independent_and_do_not_assert_reported_content(release):
    source = validate_layer(release, payload(release))
    pin = source.reference(101)
    left, right = ContextualEvaluator({pin: source}), ContextualEvaluator({pin: source})
    env = environment()
    for key in ("a1", "a2"):
        left.evaluate(AnnotationReference(pin, key), env)
    for key in ("a2", "a1"):
        right.evaluate(AnnotationReference(pin, key), env)
    assert left.terms == right.terms
    assert left.roles == right.roles
    reported = [t for t in left.terms.values() if t["value"] == "run"]
    assert len(reported) == 2
    assert all(t["status"] == "private_proposal" for t in reported)


def context_payload(release, source, pin):
    data = payload(release)
    data["terms"] = []
    data["operation"]["produced_families"] = ["context.binding"]
    data["dependencies"] = [pin.values()]
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
            external_premises=[dict(layer=pin.values(), local_id=target)],
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
    source = validate_layer(release, payload(release))
    pin = source.reference(101)
    data = context_payload(release, source, pin)
    context = validate_layer(release, data, dependencies={pin: source})
    cpin = context.reference(102)
    selected = environment(
        context_layers=(cpin,), hypotheses=(AnnotationReference(cpin, "binding-role"),)
    )
    evaluator = ContextualEvaluator({pin: source, cpin: context})
    root = evaluator.evaluate(AnnotationReference(pin, "b1"), selected)
    assert (
        next(r for r in evaluator.roles.values() if r["owner"] == root)["basis"]["status"]
        == "private_proposal"
    )
    invalid = copy.deepcopy(data)
    invalid["roles"][0]["member"] = "wrong"
    broken = validate_layer(release, invalid, dependencies={pin: source})
    bpin = broken.reference(102)
    with pytest.raises(ValueError, match="endpoints differ"):
        ContextualEvaluator({pin: source, bpin: broken}).evaluate(
            AnnotationReference(pin, "b1"),
            environment(
                context_layers=(bpin,), hypotheses=(AnnotationReference(bpin, "binding-role"),)
            ),
        )


def test_evaluated_layer_uses_retained_shapes_and_exact_dependencies(release):
    source = validate_layer(release, payload(release))
    pin = source.reference(101)
    original = source.payload
    evaluator = ContextualEvaluator({pin: source})
    operation = {**original["operation"], "key": "text.evaluate_context"}
    result = evaluator.finish(
        release,
        original["source_scope"],
        operation,
        [AnnotationReference(pin, "b1")],
        environment(),
    )
    assert result.payload["dependencies"] == [pin.values()]
    assert result.payload["roles"]
    assert all(r["basis"]["status"] == "private_proposal" for r in result.payload["roles"])


def test_model_candidate_role_authenticates_selected_frozen_endpoints(release):
    import json
    from hashlib import sha256

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.observations import source_value

    source = validate_layer(release, payload(release))
    pin = source.reference(101)
    data = context_payload(release, source, pin)
    focus = dict(reference=dict(layer=pin.values(), local_id="x"))
    candidate = dict(
        key="offered_host",
        compatibility="exclusive",
        members=[dict(reference=dict(layer=pin.values(), local_id="p"))],
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
    annotations[0]["external_premises"] = [dict(layer=pin.values(), local_id="x")]
    annotations[1]["kind"] = "model.candidate"
    annotations[1]["external_premises"] = [dict(layer=pin.values(), local_id="p")]
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
    context = validate_layer(release, data, dependencies={pin: source})
    cpin = context.reference(102)
    env = environment(
        context_layers=(cpin,), hypotheses=(AnnotationReference(cpin, "binding-role"),)
    )
    evaluator = ContextualEvaluator({pin: source, cpin: context})
    root = evaluator.evaluate(AnnotationReference(pin, "x"), env)
    assert any(
        r["owner"] == root and r["role"] == "unresolved_host" for r in evaluator.roles.values()
    )
    ordinary = ContextualEvaluator({pin: source, cpin: context})
    default_root = ordinary.evaluate(
        AnnotationReference(pin, "x"), environment(context_layers=(cpin,))
    )
    assert any(
        r["owner"] == default_root and r["role"] == "unresolved_host"
        for r in ordinary.roles.values()
    )
    invalid = copy.deepcopy(data)
    invalid["annotations"][1]["external_premises"] = [
        dict(layer=pin.values(), local_id="restrictor")
    ]
    broken = validate_layer(release, invalid, dependencies={pin: source})
    bpin = broken.reference(102)
    with pytest.raises(ValueError, match="frozen alternative"):
        ContextualEvaluator({pin: source, bpin: broken}).evaluate(
            AnnotationReference(pin, "x"),
            environment(
                context_layers=(bpin,), hypotheses=(AnnotationReference(bpin, "binding-role"),)
            ),
        )


def test_packed_contextual_choice_preserves_upstream_requirements_and_unresolved_site(release):
    from corpus_structure.semantic.characterization import project_reading

    data = payload(release)
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
    source = validate_layer(release, data)
    pin = source.reference(101)
    evaluator = ContextualEvaluator({pin: source})
    report = evaluator.finish(
        release,
        data["source_scope"],
        {**data["operation"], "key": "text.evaluate_context"},
        [AnnotationReference(pin, "packed")],
        environment(),
    )
    root = next(
        t["local_id"] for t in report.payload["terms"] if t["value"] == "contextual-reading"
    )
    assert project_reading(report, root, dependencies={pin: source})["outcome"] == "partial"
    group = report.payload["choices"][0]
    selected = group["members"][0]
    required = selected["required_external_choices"][0]
    reading = project_reading(
        report,
        root,
        choices=[selected["local_id"]],
        dependencies={pin: source},
        external_choices=[AnnotationReference(pin, required["local_id"])],
    )
    assert reading["outcome"] == "complete"
    assert len([t for t in reading["terms"] if t["value"] in {"left", "right"}]) == 1
    with pytest.raises(ValueError, match="incompatible"):
        ContextualEvaluator({pin: source}).evaluate(
            AnnotationReference(pin, "packed"),
            environment(
                choices=(
                    AnnotationReference(pin, "select-left"),
                    AnnotationReference(pin, "select-right"),
                )
            ),
        )


def test_context_failure_preserves_local_meaning_and_marks_dependent_family(release):
    source = validate_layer(release, payload(release))
    pin = source.reference(101)
    data = context_payload(release, source, pin)
    data["outcome"] = "partial"
    data["coverage"][0].update(
        outcome="failed", availability="unavailable", reason="provider runtime unavailable"
    )
    context = validate_layer(release, data, dependencies={pin: source})
    cpin = context.reference(102)
    evaluator = ContextualEvaluator({pin: source, cpin: context})
    report = evaluator.finish(
        release,
        data["source_scope"],
        {**data["operation"], "key": "text.evaluate_context"},
        [AnnotationReference(pin, "p")],
        environment(context_layers=(cpin,)),
    )
    coverage = {r["family"]: r for r in report.payload["coverage"]}
    assert coverage["meaning.reference"]["outcome"] == "partial"
    assert coverage["meaning.predication"]["outcome"] == "complete"
    assert any(t["value"] == "run" for t in report.payload["terms"])


def test_context_layer_candidates_participate_by_default_without_forced_selection(release):
    source = validate_layer(release, payload(release))
    pin = source.reference(101)
    data = context_payload(release, source, pin)
    context = validate_layer(release, data, dependencies={pin: source})
    cpin = context.reference(102)
    evaluator = ContextualEvaluator({pin: source, cpin: context})
    root = evaluator.evaluate(AnnotationReference(pin, "b1"), environment(context_layers=(cpin,)))
    assert any(
        r["owner"] == root and r["role"] == "declared_binding_site"
        for r in evaluator.roles.values()
    )


def test_available_rival_hypotheses_keep_separate_upstream_choice_requirements(release):
    data = payload(release)
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
    source = validate_layer(release, data)
    pin = source.reference(101)
    context_data = context_payload(release, source, pin)
    context_data["roles"][0]["required_external_choices"] = [
        dict(layer=pin.values(), local_id="select-b1")
    ]
    owner = copy.deepcopy(context_data["annotations"][0])
    owner.update(local_id="owner2", external_premises=[dict(layer=pin.values(), local_id="b2")])
    hypothesis = copy.deepcopy(context_data["annotations"][-1])
    hypothesis.update(local_id="hypothesis2", premises=["owner2", "member"])
    context_data["annotations"].extend([owner, hypothesis])
    role = copy.deepcopy(context_data["roles"][0])
    role.update(
        local_id="binding-role2",
        owner="owner2",
        required_external_choices=[dict(layer=pin.values(), local_id="select-b2")],
        basis=dict(kind="contextual_proposal", status="private_proposal", premises=["hypothesis2"]),
    )
    context_data["roles"].append(role)
    context = validate_layer(release, context_data, dependencies={pin: source})
    cpin = context.reference(102)
    evaluator = ContextualEvaluator({pin: source, cpin: context})
    evaluator.evaluate(AnnotationReference(pin, "packed"), environment(context_layers=(cpin,)))
    bindings = [r for r in evaluator.roles.values() if r["role"] == "declared_binding_site"]
    assert len(bindings) == 2
    assert {tuple(c["local_id"] for c in r["required_external_choices"]) for r in bindings} == {
        ("select-b1",),
        ("select-b2",),
    }


def test_source_first_functions_evaluate_without_any_symbolic_roots(release):
    from corpus_structure.semantic.observations import source_value

    data = payload(release)
    occurrence = data["occurrences"][1]["local_id"]
    family = "character_function_v1"
    data["terms"] = []
    data["operation"].update(key="text.model_characterization", produced_families=[family])
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
    model = validate_layer(release, data)
    pin = model.reference(101)
    evaluator = ContextualEvaluator({pin: model})
    report = evaluator.finish(
        release,
        data["source_scope"],
        {**data["operation"], "key": "text.evaluate_context"},
        [],
        environment(context_layers=(pin,)),
    )
    assert {t["value"] for t in report.payload["terms"]} >= {
        "function:assertion",
        "function:definition",
    }
    coverage = {r["family"]: r for r in report.payload["coverage"]}
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

    data = payload(release)
    family = "character_scope_v1"
    text = "not all x runs"
    data["source_scope"]["selectors"][0]["end"] = len(text)
    data["coverage"][0].update(family=family, operation="text.model_characterization")
    data["operation"].update(key="text.model_characterization", produced_families=[family])
    data["terms"] = []
    data["annotations"] = []
    data["occurrences"] = []
    seen = {}

    def occurrence(a, b):
        if (a, b) not in seen:
            extents = [
                dict(
                    projection="b" * 64,
                    source_view_id=11,
                    native_pointer="#/texts/0",
                    page=3,
                    start=a,
                    end=b,
                    text=text[a:b],
                    synthetic=False,
                )
            ]
            key = occurrence_id(data["base_document"], extents)
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
    report = validate_layer(release, data)
    pin = report.reference(101)
    result = ContextualEvaluator({pin: report}).finish(
        release,
        data["source_scope"],
        {**data["operation"], "key": "text.evaluate_context"},
        [],
        environment(context_layers=(pin,)),
    )
    terms = {t["local_id"]: t for t in result.payload["terms"]}
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
    old = validate_layer(release, payload(release))
    old_pin = old.reference(101)
    data = payload(release)
    data["operation"]["input"] = "new-rules"
    data["dependencies"] = [old_pin.values()]
    source = validate_layer(release, data, dependencies={old_pin: old})
    pin = source.reference(102)
    evaluator = ContextualEvaluator({old_pin: old, pin: source}, symbolic_layers=(pin,))
    roots = evaluator.default_roots(environment())
    assert roots and all(isinstance(ref, AnnotationReference) for ref in roots)
    assert {ref.product for ref in roots} == {pin}
    result = evaluator.finish(release, data["source_scope"], data["operation"], [], environment())
    assert {ref["task_id"] for ref in result.payload["dependencies"]} == {101, 102}
    assert all(
        ref["layer"]["task_id"] == 102
        for term in result.payload["terms"]
        for ref in term.get("external_premises", ())
    )
