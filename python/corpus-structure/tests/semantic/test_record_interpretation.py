"""Independent tiny distributions for the private M1 retained-candidate operation."""

from dataclasses import replace
from itertools import product
from math import inf, log
from threading import Event

import pytest

from corpus_structure.semantic import record_interpretation as ri


def decision(key, *resolved, identity=False):
    return ri.Decision(
        key,
        (
            *(ri.Candidate(value) for value in resolved),
            *((ri.Candidate("local", ri.CandidateKind.LOCAL_NEW),) if identity else ()),
            ri.Candidate("?", ri.CandidateKind.UNRESOLVED, "insufficient source evidence"),
        ),
    )


def value_template(*, auxiliary=(), qualifiers=()):
    return ri.ValuePropertyReferentCondition(
        decision("value", "12", "10"),
        decision("property", "pressure"),
        decision("referent", "pump", identity=True),
        decision("condition", "below", "above"),
        qualifiers=qualifiers,
        auxiliary=auxiliary,
    )


def decisions(template):
    if isinstance(template, ri.ValuePropertyReferentCondition):
        roles = (template.value, template.property, template.referent, template.condition)
    elif isinstance(template, ri.MentionIdentityTypeRelation):
        roles = (template.identity, template.type, template.relation)
    else:
        roles = (
            template.header,
            template.row_identity,
            template.cell_value,
            template.unit,
            template.note,
        )
    return (*roles, *template.qualifiers, *template.auxiliary)


def request(template, weights, *, events=()):
    """Independent expected table fixture; all unlisted assignments have hard zero weight."""
    ds = decisions(template)
    values = tuple(
        log(weights[state]) if weights.get(state, 0) > 0 else -inf
        for state in product(*(tuple(c.key for c in d.candidates) for d in ds))
    )
    deps = tuple(
        ri.Dependency(key, kind, "fixture-v1")
        for key, kind in (
            ("model", ri.DependencyKind.MODEL),
            ("ontology", ri.DependencyKind.ONTOLOGY),
            ("policy", ri.DependencyKind.POLICY),
            ("observation", ri.DependencyKind.OBSERVATION),
            ("counter", ri.DependencyKind.COUNTEREVIDENCE),
            ("rejected", ri.DependencyKind.REJECTED_ALTERNATIVE),
            ("retrieval", ri.DependencyKind.RETRIEVAL),
            ("selection", ri.DependencyKind.SELECTION),
        )
    )
    return ri.InterpretationRequest(
        template=template,
        potentials=(
            ri.LogPotential(
                "joint", tuple(d.key for d in ds), values, ("observation", "counter", "rejected")
            ),
        ),
        constraints=(),
        events=events,
        dependencies=deps,
        selection=ri.CandidateSelection(
            "passage-1",
            ("selection", "retrieval"),
            retrieval_limit=12,
            exclusions=("outside passage",),
            truncations=("upstream retrieval top 12",),
        ),
        model_dependency_id="model",
        ontology_dependency_id="ontology",
        policy_dependency_id="policy",
    )


def event(key="record", *, value="12", condition="below", extra=()):
    return ri.RecordEvent(
        key,
        (
            (
                ri.Choice("value", value),
                ri.Choice("property", "pressure"),
                ri.Choice("referent", "pump"),
                ri.Choice("condition", condition),
                *extra,
            ),
        ),
    )


def probabilities(result):
    return {p.event: p.probability for p in result.event_probabilities}


def assert_no_partial(result):
    assert result.event_probabilities == result.marginals == result.alternatives == ()
    assert result.log_partition is None
    assert result.exact_retained_support is False


def test_hand_calculated_joint_event_and_marginals_do_not_multiply():
    # Rows sum to value12=3/10; below sums to 4/10; their joint is 1/10, not 12/100.
    req = request(
        value_template(),
        {
            ("12", "pressure", "pump", "below"): 1,
            ("12", "pressure", "pump", "above"): 2,
            ("10", "pressure", "pump", "below"): 3,
            ("10", "pressure", "pump", "above"): 4,
        },
        events=(event(),),
    )
    result = ri.interpret_records(req)
    assert result.outcome is ri.Outcome.COMPLETED
    assert result.exact_retained_support is True
    assert probabilities(result)["record"] == pytest.approx(0.1)
    marginals = {(m.decision, m.candidate): m.probability for m in result.marginals}
    assert marginals["value", "12"] == pytest.approx(0.3)
    assert marginals["condition", "below"] == pytest.approx(0.4)
    assert result.log_partition == pytest.approx(log(10))
    assert result.search.positive_states == 4
    assert result.search.examined_states == result.search.retained_states
    assert result.probability_standing == "provisional_candidate_relative"
    assert result.omitted_candidate_mass == "unknown"
    assert result.dependencies == req.dependencies
    assert result.selection == req.selection


def test_event_sum_beats_map_duplicate_overlapping_derivations_count_once():
    template = value_template(auxiliary=(decision("evidence", "a", "b"),))
    reading = event()
    # Broad and narrow derivations overlap; all three describe the same qualified reading.
    reading = replace(
        reading,
        derivations=(
            reading.derivations[0],
            reading.derivations[0],
            (*reading.derivations[0], ri.Choice("evidence", "a")),
        ),
    )
    req = request(
        template,
        {
            ("12", "pressure", "pump", "below", "a"): 3,
            ("12", "pressure", "pump", "below", "b"): 3,
            ("10", "pressure", "pump", "below", "a"): 4,
        },
        events=(reading, event("other", value="10")),
    )
    result = ri.interpret_records(replace(req, limits=ri.SearchLimits(displayed_alternatives=1)))
    assert probabilities(result) == pytest.approx({"record": 0.6, "other": 0.4})
    assert result.alternatives[0].probability == pytest.approx(0.4)
    assert ri.Choice("value", "10") in result.alternatives[0].choices
    assert sum(a.probability for a in result.alternatives) < 1


def test_qualifier_is_part_of_event_and_cannot_be_omitted():
    template = value_template(qualifiers=(decision("modality", "may", "does"),))
    may = event(extra=(ri.Choice("modality", "may"),))
    req = request(
        template,
        {
            ("12", "pressure", "pump", "below", "may"): 1,
            ("12", "pressure", "pump", "below", "does"): 3,
        },
        events=(may,),
    )
    assert probabilities(ri.interpret_records(req))["record"] == pytest.approx(0.25)
    invalid = ri.interpret_records(replace(req, events=(event(),)))
    assert invalid.outcome is ri.Outcome.INVALID_INPUT
    assert_no_partial(invalid)
    mixed = replace(
        may,
        derivations=(
            may.derivations[0],
            (
                *event().derivations[0],
                ri.Choice("modality", "does"),
            ),
        ),
    )
    assert ri.interpret_records(replace(req, events=(mixed,))).outcome is ri.Outcome.INVALID_INPUT


def test_state_axis_and_block_permutations_preserve_named_probabilities():
    req = request(
        value_template(),
        {
            ("12", "pressure", "pump", "below"): 1,
            ("12", "pressure", "pump", "above"): 2,
            ("10", "pressure", "pump", "below"): 3,
            ("10", "pressure", "pump", "above"): 4,
        },
        events=(event(),),
    )
    original = ri.interpret_records(req)
    assert isinstance(req.template, ri.ValuePropertyReferentCondition)
    template = replace(
        req.template,
        value=replace(
            req.template.value, candidates=tuple(reversed(req.template.value.candidates))
        ),
    )
    # Rebuild the same named table under reversed axis and state orders independently.
    ds = tuple(reversed(decisions(template)))
    named_weights = {
        ("12", "below"): 1,
        ("12", "above"): 2,
        ("10", "below"): 3,
        ("10", "above"): 4,
    }
    values = []
    for state in product(*(tuple(c.key for c in d.candidates) for d in ds)):
        binding = dict(zip((d.key for d in ds), state, strict=True))
        weight = (
            named_weights.get((binding["value"], binding["condition"]), 0)
            if binding["property"] == "pressure" and binding["referent"] == "pump"
            else 0
        )
        values.append(log(weight) if weight else -inf)
    permuted = ri.interpret_records(
        replace(
            req,
            template=template,
            potentials=(
                replace(req.potentials[0], scope=tuple(d.key for d in ds), values=tuple(values)),
            ),
            limits=ri.SearchLimits(block_states=1),
        )
    )
    assert probabilities(permuted) == pytest.approx(probabilities(original))
    assert {(m.decision, m.candidate): m.probability for m in permuted.marginals} == pytest.approx(
        {(m.decision, m.candidate): m.probability for m in original.marginals}
    )


@pytest.mark.parametrize(
    "template",
    [
        ri.MentionIdentityTypeRelation(
            "mention-1",
            decision("identity", "known", identity=True),
            decision("type", "pump"),
            decision("relation", "has"),
        ),
        ri.TableHeaderRowCellUnitNote(
            "table-1",
            decision("header", "flow"),
            decision("row", "A", identity=True),
            decision("cell", "12"),
            decision("unit", "bar"),
            decision("note", "rated"),
        ),
    ],
)
def test_other_two_typed_templates_retain_local_identity_and_complete_roles(template):
    ds = decisions(template)
    state = tuple(
        "local" if "local" in {c.key for c in d.candidates} else d.candidates[0].key for d in ds
    )
    reading = ri.RecordEvent(
        "local-record", (tuple(ri.Choice(d.key, c) for d, c in zip(ds, state, strict=True)),)
    )
    result = ri.interpret_records(request(template, {state: 1}, events=(reading,)))
    assert result.outcome is ri.Outcome.COMPLETED
    assert probabilities(result) == {"local-record": 1}
    assert "local" in {c.candidate for c in result.alternatives[0].choices}


def test_assignment_relative_hard_constraint_hard_zero_and_infeasible_are_distinct():
    req = request(
        value_template(),
        {
            ("12", "pressure", "pump", "below"): 1,
            ("10", "pressure", "pump", "below"): 3,
        },
        events=(event(),),
    )
    mask = ri.HardConstraint("value-meaning", ("value",), (True, False, False), ("ontology",))
    result = ri.interpret_records(replace(req, constraints=(mask,)))
    assert result.outcome is ri.Outcome.COMPLETED
    assert probabilities(result)["record"] == 1
    assert result.search.positive_states == 1
    # The second event is impossible under supplied hard-zero support, not a numeric error.
    zero_event = ri.interpret_records(replace(req, events=(event(value="?"),)))
    assert probabilities(zero_event)["record"] == 0
    infeasible = ri.interpret_records(
        replace(req, constraints=(replace(mask, allowed=(False, False, False)),))
    )
    assert infeasible.outcome is ri.Outcome.INFEASIBLE
    assert_no_partial(infeasible)
    all_zero = ri.interpret_records(request(value_template(), {}, events=(event(),)))
    assert all_zero.outcome is ri.Outcome.INFEASIBLE
    assert_no_partial(all_zero)


@pytest.mark.parametrize("bad", [float("nan"), inf])
def test_invalid_nonfinite_potential_is_numeric_failure_even_on_impossible_state(bad):
    req = request(value_template(), {}, events=(event(),))
    req = replace(
        req, potentials=(replace(req.potentials[0], values=(bad, *req.potentials[0].values[1:])),)
    )
    result = ri.interpret_records(req)
    assert result.outcome is ri.Outcome.NUMERICAL_FAILURE
    assert_no_partial(result)


@pytest.mark.parametrize("offset", [-1000.0, 1000.0, 1e200])
def test_extreme_common_offsets_normalize_without_uniform_fallback(offset):
    req = request(
        value_template(),
        {
            ("12", "pressure", "pump", "below"): 1,
            ("10", "pressure", "pump", "below"): 1,
        },
        events=(event(),),
    )
    req = replace(
        req,
        potentials=(
            replace(
                req.potentials[0],
                values=tuple(
                    value + offset if value != -inf else -inf for value in req.potentials[0].values
                ),
            ),
        ),
    )
    result = ri.interpret_records(req)
    assert result.outcome is ri.Outcome.COMPLETED
    assert probabilities(result)["record"] == pytest.approx(0.5)
    assert sum(a.probability for a in result.alternatives) == pytest.approx(1)


def test_arithmetic_overflow_is_not_mislabelled_as_hard_zero():
    req = request(value_template(), {}, events=(event(),))
    huge = replace(req.potentials[0], values=tuple(-1e308 for _ in req.potentials[0].values))
    result = ri.interpret_records(replace(req, potentials=(huge, replace(huge, key="second"))))
    assert result.outcome is ri.Outcome.NUMERICAL_FAILURE
    assert_no_partial(result)


def test_hard_zero_precedes_unused_overflow_regardless_of_factor_order():
    req = request(value_template(), {}, events=(event(),))
    zero = req.potentials[0]
    huge = replace(zero, key="huge", values=tuple(-1e308 for _ in zero.values))
    second = replace(huge, key="second")
    for tables in ((huge, second, zero), (zero, second, huge)):
        result = ri.interpret_records(replace(req, potentials=tables))
        assert result.outcome is ri.Outcome.INFEASIBLE
        assert_no_partial(result)
    mask = ri.HardConstraint("impossible", ("value",), (False,) * 3, ("ontology",))
    result = ri.interpret_records(replace(req, potentials=(huge, second), constraints=(mask,)))
    assert result.outcome is ri.Outcome.INFEASIBLE


def test_extremely_unequal_weights_retain_positive_support_without_fallback():
    req = request(
        value_template(),
        {
            ("12", "pressure", "pump", "below"): 1,
            ("10", "pressure", "pump", "below"): 1,
        },
        events=(event(), event("other", value="10")),
    )
    values = list(req.potentials[0].values)
    # Independent flat coordinates: value=12 at 0 and value=10 at 18.
    values[0] = -1000.0
    values[18] = 1000.0
    result = ri.interpret_records(
        replace(req, potentials=(replace(req.potentials[0], values=tuple(values)),))
    )
    assert result.outcome is ri.Outcome.COMPLETED
    assert probabilities(result) == {"record": 0.0, "other": 1.0}
    assert result.search.positive_states == 2


def test_workspace_guard_precedes_factor_array_allocation_and_guard_is_configurable(monkeypatch):
    req = request(
        value_template(),
        {
            ("12", "pressure", "pump", "below"): 1,
        },
        events=(event(),),
    )

    def allocation_is_a_bug(*args, **kwargs):
        pytest.fail("guard should run before converting factor arrays")

    with monkeypatch.context() as patch:
        patch.setattr(ri.np, "asarray", allocation_is_a_bug)
        result = ri.interpret_records(replace(req, limits=ri.SearchLimits(max_workspace_bytes=1)))
    assert result.outcome is ri.Outcome.RESOURCE_LIMIT
    total = 3 * 2 * 3 * 3
    exact_guard = ri.interpret_records(replace(req, limits=ri.SearchLimits(max_states=total)))
    assert exact_guard.outcome is ri.Outcome.COMPLETED
    below_guard = ri.interpret_records(replace(req, limits=ri.SearchLimits(max_states=total - 1)))
    assert below_guard.outcome is ri.Outcome.RESOURCE_LIMIT


def test_components_use_real_factor_constraint_and_dependence_scopes_not_metadata():
    req = request(value_template(), {}, events=(event(),))
    unary = tuple(
        ri.LogPotential(d.key, (d.key,), tuple(0.0 for _ in d.candidates), ("model",))
        for d in decisions(req.template)
    )
    independent = ri.interpret_records(replace(req, potentials=unary))
    assert independent.search.components == (
        ("condition",),
        ("property",),
        ("referent",),
        ("value",),
    )
    coupling = ri.LogPotential("coupled", ("value", "property"), (0.0,) * 6, ("observation",))
    constraint = ri.HardConstraint("scope", ("condition", "referent"), (True,) * 9, ("ontology",))
    dependence = ri.DependenceScope(("property", "referent"), ("counter",), "shared OCR context")
    connected = ri.interpret_records(
        replace(
            req,
            potentials=(*unary, coupling),
            constraints=(constraint,),
            dependence_scopes=(dependence,),
        )
    )
    assert connected.search.components == (("condition", "property", "referent", "value"),)
    assert connected.outcome is ri.Outcome.COMPLETED


@pytest.mark.parametrize(
    "limits,detail",
    [
        (ri.SearchLimits(max_states=1), "state guard"),
        (ri.SearchLimits(max_workspace_bytes=1), "memory limit"),
        (ri.SearchLimits(max_seconds=0), "time limit"),
    ],
)
def test_limits_are_explicit_without_partial_or_empty_success(limits, detail):
    req = request(value_template(), {}, events=(event(),))
    result = ri.interpret_records(replace(req, limits=limits))
    assert result.outcome is ri.Outcome.RESOURCE_LIMIT
    assert detail in result.detail
    assert_no_partial(result)


def test_cancellation_before_and_during_work_has_no_partial_probabilities(monkeypatch):
    req = request(value_template(), {}, events=(event(),))
    cancelled = Event()
    cancelled.set()
    result = ri.interpret_records(req, cancellation=cancelled)
    assert result.outcome is ri.Outcome.CANCELLED
    assert result.search.examined_states == 0
    assert_no_partial(result)
    # Cancel as the second enumeration block starts; one complete block was examined.
    cancelled.clear()
    calls = 0
    unravel = ri.np.unravel_index

    def cancel_second_block(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            cancelled.set()
        return unravel(*args, **kwargs)

    monkeypatch.setattr(ri.np, "unravel_index", cancel_second_block)
    req = replace(req, limits=ri.SearchLimits(block_states=4))
    result = ri.interpret_records(req, cancellation=cancelled)
    assert result.outcome is ri.Outcome.CANCELLED
    assert result.search.examined_states > 0
    assert_no_partial(result)


def test_elapsed_limit_during_work_and_allocation_failure(monkeypatch):
    req = request(value_template(), {}, events=(event(),))
    elapsed = 0.0
    calls = 0
    unravel = ri.np.unravel_index

    def expire_second_block(*args, **kwargs):
        nonlocal elapsed, calls
        calls += 1
        if calls == 2:
            elapsed = 1.0
        return unravel(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(ri, "monotonic", lambda: elapsed)
        patch.setattr(ri.np, "unravel_index", expire_second_block)
        result = ri.interpret_records(
            replace(req, limits=ri.SearchLimits(max_seconds=0.5, block_states=4))
        )
    assert result.outcome is ri.Outcome.RESOURCE_LIMIT
    assert result.search.examined_states == 4
    assert "time" in result.detail
    assert_no_partial(result)

    def allocation_failure(*args, **kwargs):
        raise MemoryError

    monkeypatch.setattr(ri.np, "asarray", allocation_failure)
    result = ri.interpret_records(req)
    assert result.outcome is ri.Outcome.RESOURCE_LIMIT
    assert "allocation" in result.detail
    assert_no_partial(result)


@pytest.mark.parametrize("change", ["unresolved", "local", "shape", "dependency", "coverage"])
def test_missing_semantic_or_dependency_inputs_fail_explicitly(change):
    req = request(value_template(), {}, events=(event(),))
    assert isinstance(req.template, ri.ValuePropertyReferentCondition)
    if change == "unresolved":
        req = replace(
            req,
            template=replace(
                req.template, value=replace(req.template.value, candidates=(ri.Candidate("12"),))
            ),
        )
    elif change == "local":
        req = replace(req, template=replace(req.template, referent=decision("referent", "pump")))
    elif change == "shape":
        req = replace(req, potentials=(replace(req.potentials[0], values=(0.0,)),))
    elif change == "dependency":
        req = replace(req, dependencies=tuple(d for d in req.dependencies if d.key != "counter"))
    else:
        req = replace(req, potentials=())
    result = ri.interpret_records(req)
    assert result.outcome is ri.Outcome.INVALID_INPUT
    assert_no_partial(result)


@pytest.mark.parametrize(
    "field",
    [
        "max_states",
        "block_states",
        "max_workspace_bytes",
        "displayed_alternatives",
    ],
)
@pytest.mark.parametrize("malformed", [1.5, float("nan"), True])
def test_malformed_integer_limits_are_rejected_before_numerical_allocation(
    field, malformed, monkeypatch
):
    req = request(
        value_template(),
        {
            ("12", "pressure", "pump", "below"): 1,
            ("10", "pressure", "pump", "below"): 1,
        },
        events=(event(),),
    )

    def allocation_is_a_bug(*args, **kwargs):
        pytest.fail("malformed limits reached numerical allocation")

    monkeypatch.setattr(ri.np, "asarray", allocation_is_a_bug)
    limits = replace(ri.SearchLimits(), **{field: malformed})
    result = ri.interpret_records(replace(req, limits=limits))
    assert result.outcome is ri.Outcome.INVALID_INPUT
    assert result.search.examined_states == 0
    assert_no_partial(result)


@pytest.mark.parametrize("duration", [float("nan"), inf, -inf, -1.0, "1", None, True, 10**400])
def test_malformed_duration_is_invalid_input_not_runtime_numeric_failure(duration):
    req = request(value_template(), {}, events=(event(),))
    result = ri.interpret_records(replace(req, limits=ri.SearchLimits(max_seconds=duration)))
    assert result.outcome is ri.Outcome.INVALID_INPUT
    assert result.search.examined_states == 0
    assert_no_partial(result)


@pytest.mark.parametrize("potential", ["0.0", None, True, 1j])
def test_nonnumeric_potential_is_explicit_invalid_input(potential):
    req = request(value_template(), {}, events=(event(),))
    table = replace(req.potentials[0], values=(potential, *req.potentials[0].values[1:]))
    result = ri.interpret_records(replace(req, potentials=(table,)))
    assert result.outcome is ri.Outcome.INVALID_INPUT
    assert_no_partial(result)


@pytest.mark.parametrize("retrieval_limit", [1.5, float("nan"), True])
def test_retrieval_count_metadata_cannot_bypass_exact_integer_boundary(retrieval_limit):
    req = request(value_template(), {}, events=(event(),))
    result = ri.interpret_records(
        replace(req, selection=replace(req.selection, retrieval_limit=retrieval_limit))
    )
    assert result.outcome is ri.Outcome.INVALID_INPUT
    assert_no_partial(result)
