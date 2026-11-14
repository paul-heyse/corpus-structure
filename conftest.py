"""Scheduling boundaries shared by the root and package test trees."""

import os
from collections.abc import Generator

import pytest

# Consumer paths qualify local generic names; shared support fixtures have
# distinctive names and follow their complete dependency closure across modules.
PREPARATION_AFFINITY = (
    *(
        (name, None, "math_preparation")
        for name in (
            "spike_readings",
            "spike_extraction",
            "spike_scoped",
            "s0r2_readings",
            "s0r2_extraction",
            "s0r2_scoped",
        )
    ),
    ("statistics_pack_inputs", None, "statistics_pack"),
    ("statistics_pack_prepared", None, "statistics_pack"),
    ("statistics_rules_policy", None, "statistics_pack"),
    ("profile", "python/corpus-structure/tests/semantic/test_hanlp_products.py", "hanlp_profile"),
    ("source_release", "tests/test_native_run_scope.py", "trusted_execution_model"),
    ("local_semantic_sql_batch", None, "local_semantic_sql"),
    ("record_custody_case", None, "record_custody"),
    ("record_identity_case", None, "record_identity"),
    ("record_graph_case", None, "record_graph"),
    ("contextual_atomic_case", None, "contextual_atomic"),
    ("local_witness_case", None, "local_witness"),
    ("judged_semantic_case", None, "judged_semantic"),
    ("interpretation_source_case", None, "interpretation_source"),
    ("runtime_registration_case", None, "runtime_registration"),
    ("unbound_arrow_case", None, "unbound_arrow"),
    (
        "native_read",
        "python/corpus-structure/tests/semantic/test_contextual_workflow_native.py",
        "named_cue_read",
    ),
    ("domain_default_case", None, "domain_default"),
    ("domain_formula_source", None, "domain_formulas"),
    ("resubmission_case", None, "resubmission_source"),
    ("resubmission_historical_source", None, "resubmission_source"),
    ("exclusion_case", None, "exclusion_source"),
    ("exclusion_read_case", None, "exclusion_source"),
    ("exclusion_literal_case", None, "exclusion_source"),
    ("exclusion_refusal_family", None, "exclusion_source"),
    ("occurrence_case", None, "occurrence_source"),
    ("occurrence_refusal_family", None, "occurrence_source"),
    ("imported_declaration_case", None, "imported_membership"),
    ("imported_membership_case", None, "imported_membership"),
    ("declared_membership_case", None, "declared_membership"),
    ("binding_native_connection", None, "ddo_binding_source"),
    ("selected_graph_case", None, "ddo_selected_graph"),
)


def _preparation_group(item: pytest.Item, root) -> str | None:
    fixtures = set(getattr(item, "fixturenames", ()))
    consumer = item.path.relative_to(root).as_posix()
    groups = {
        group
        for fixture, module, group in PREPARATION_AFFINITY
        if fixture in fixtures and (module is None or module == consumer)
    }
    groups.update(
        str(mark.args[0] if mark.args else mark.kwargs.get("name", "default"))
        for mark in item.iter_markers("xdist_group")
    )
    if len(groups) > 1:
        raise pytest.UsageError(
            f"{item.nodeid}: conflicting preparation affinity groups: {', '.join(sorted(groups))}"
        )
    return next(iter(groups), None)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    # xdist allocates worker scratch before any descendant test conftest can help.
    if config.option.basetemp is not None or "PYTEST_DEBUG_TEMPROOT" in os.environ:
        return
    root = config.rootpath / "build" / "tmp" / "pytest"
    root.mkdir(parents=True, exist_ok=True)
    environment = pytest.MonkeyPatch()
    config.add_cleanup(environment.undo)
    environment.setenv("PYTEST_DEBUG_TEMPROOT", str(root))


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> Generator[None]:
    for item in items:
        group = _preparation_group(item, config.rootpath)
        if group is not None and not any(item.iter_markers("xdist_group")):
            item.add_marker(pytest.mark.xdist_group(group))
    yield
    # Check after pytest's marker deselection: ordinary parallel runs omit these controls.
    faults = [item for item in items if item.get_closest_marker("shared_cluster_fault")]
    if faults and (config.getoption("numprocesses") or hasattr(config, "workerinput")):
        raise pytest.UsageError(
            "shared_cluster_fault controls require an exclusive serial invocation; "
            "use just test-native-faults (or -n 0 -m shared_cluster_fault)"
        )
    if faults and len(faults) != len(items):
        raise pytest.UsageError(
            "shared_cluster_fault controls must run separately from ordinary tests; "
            "use just test-native-faults"
        )
