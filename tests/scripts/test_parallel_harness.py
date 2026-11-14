"""Real isolated serial/xdist controls for public collection and journal contracts."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from test_receipts import ROOT, classify_receipt, read_stream, run_python


@pytest.mark.parametrize(
    "kind, expected, sweep_rule",
    [
        ("session", "ci_test_42", "unleased"),
        ("infra", "cs_sem_infra_42_0123456789ab", "unleased"),
        ("infra_case", "cs_sem_infra_case_42_0123456789ab", "unleased"),
        ("test", "cs_sem_test_42_0123456789ab", "unleased"),
        ("bare", "cs_sem_bare_42_0123456789ab", "unleased"),
        ("revision", "cs_sem_revision_42_0123456789ab", "unleased"),
        ("init", "cs_sem_init_42_0123456789ab", "unleased"),
        ("build", "cs_sem_build_42_0123456789ab", "unleased"),
        ("reusable_head", "cs_sem_head_aaaaaaaaaaaaaaaa", "retained"),
        ("run_private_head", "cs_sem_head_aaaaaaaaaaaaaaaa_bbbbbbbb", "unleased"),
        ("stale", "cs_sem_stale_42_0123456789ab", "unleased"),
        ("seed", "cs_sem_seed_42_0123456789ab", "unleased"),
    ],
)
def test_database_naming_roundtrips_lifecycle_authority(kind, expected, sweep_rule):
    from native_test_support import database_name, recognize_database_name

    identity = database_name(kind, pid=42, token="0123456789ab", key="a" * 64, run="b" * 32)
    assert identity.name == expected
    assert identity.lease_key == expected
    assert identity.sweep_rule == sweep_rule
    assert recognize_database_name(expected) == identity


@pytest.mark.parametrize(
    "name",
    [
        "ci_test_42_1",
        "ci_test_",
        "cs_sem_test_42_abc",
        "other_project_42",
        "cs_sem_head_aaaaaaaaaaaaaaaa_extra",
    ],
)
def test_database_naming_does_not_adopt_unrecognized_names(name):
    from native_test_support import recognize_database_name

    assert recognize_database_name(name) is None


@pytest.mark.parametrize(
    "kind, kwargs",
    [
        ("test", {"pid": 0}),
        ("test", {"token": "not_hex"}),
        ("reusable_head", {"key": "short"}),
        ("run_private_head", {"key": "a" * 16, "run": "short"}),
    ],
)
def test_database_naming_rejects_invalid_kind_parameters(kind, kwargs):
    from native_test_support import database_name

    with pytest.raises(ValueError):
        database_name(kind, **kwargs)


def isolated(
    tmp_path, source, workers, *, conftest="", args=(), timeout=40, test_timeout=15, extra_files=()
):
    case = tmp_path / "case"
    case.mkdir()
    (case / "pytest.ini").write_text(
        "[pytest]\naddopts =\nmarkers =\n    db: actual database acquisition\n"
        "    shared_cluster_fault: exclusive cluster controls\n"
    )
    (case / "test_case.py").write_text(source)
    (case / "conftest.py").write_text(conftest)
    for name, content in extra_files:
        (case / name).write_text(content)
    output = tmp_path / "receipt"
    output.mkdir()
    run_python(
        output,
        [
            "-c",
            str(case / "pytest.ini"),
            "-o",
            "addopts=",
            "-n",
            str(workers),
            "--dist=loadgroup",
            "--max-worker-restart=0",
            str(case),
            *args,
        ],
        cwd=case,
        timeout=timeout,
        test_timeout=test_timeout,
    )
    retained = os.environ.get("QUALIFICATION_CONTROL_RECEIPTS")
    if retained:
        shutil.copytree(output, Path(retained) / f"{tmp_path.name}-{workers}-{uuid4().hex}")
    return output


def events(output):
    return [event for file in output.glob("events-*.jsonl") for event in read_stream(file)[0]]


@pytest.mark.parametrize("workers", [0, 2])
@pytest.mark.db
def test_real_collection_group_identity_and_native_acquisition(tmp_path, workers, monkeypatch):
    # The enclosing item and every child own their acquisition and clone lifetime.
    from native_test_support import PgAdmin, database_name, server_url

    server = PgAdmin(server_url(), "template0", {})
    with (
        server.database(database_name("bare").name, "template0") as engine,
        engine.connect() as connection,
    ):
        assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
    source = """import os
import time
from contextlib import contextmanager
import pytest
from native_test_support import PgAdmin, database_name, server_url

@contextmanager
def acquired_clone():
    server = PgAdmin(server_url(), "template0", {})
    with server.database(database_name("bare").name, "template0") as engine:
        with engine.connect() as connection:
            yield connection

@pytest.fixture(params=[pytest.param("value", marks=pytest.mark.xdist_group("fixture"))])
def grouped(request):
    return request.param

@pytest.mark.db
@pytest.mark.xdist_group("shared")
@pytest.mark.parametrize("value", ["literal@shared", "literal@x_y"])
def test_native(value):
    with acquired_clone() as connection:
        connection.exec_driver_sql("SELECT pg_sleep(0.15)")

@pytest.mark.db
@pytest.mark.xdist_group("extra")
def test_composite(grouped):
    with acquired_clone() as connection:
        connection.exec_driver_sql("SELECT pg_sleep(0.15)")

@pytest.mark.xdist_group("fixture")
@pytest.mark.xdist_group("extra")
def test_composite_sibling():
    time.sleep(0.15)

@pytest.mark.parametrize("value", range(4))
def test_ungrouped(value):
    time.sleep(0.15)

def test_deselected():
    raise AssertionError("must not execute")
"""
    inherited_identity = {
        "PYTEST_XDIST_WORKER": "harness-parent-worker",
        "PYTEST_XDIST_WORKER_COUNT": "73",
        "PYTEST_XDIST_TESTRUNUID": "harness-parent-session",
    }
    if workers == 0:
        for name, value in inherited_identity.items():
            monkeypatch.setenv(name, value)
        source += (
            "\nassert 'PYTEST_XDIST_WORKER' not in os.environ\n"
            "assert 'PYTEST_XDIST_WORKER_COUNT' not in os.environ\n"
            "assert 'PYTEST_XDIST_TESTRUNUID' not in os.environ\n"
        )
    # Shared native DROP can await a forced checkpoint; the retained repair attempt
    # observed 20.521s. Keep this native watchdog separate from failure/loss controls.
    output = isolated(
        tmp_path, source, workers, args=("-k", "not deselected"), timeout=180, test_timeout=60
    )
    result = classify_receipt(output)
    assert result["status"] == "passed", (output / "pytest.stdout").read_text()
    assert len(result["selected"]) == 8
    assert any("literal@shared]" in node for node in result["selected"])
    assert len(result["deselected"]) == 1
    assert result["native_provenance"]["status"] == "complete"
    assert len(result["native_provenance"]["required"]) == 3
    journal = events(output)
    manifests = [event for event in journal if event["event"] == "collection_finish"]
    for manifest in manifests:
        expected = [
            "test_case.py::test_native[literal@shared]",
            "test_case.py::test_native[literal@x_y]",
            "test_case.py::test_composite[value]",
            "test_case.py::test_composite_sibling",
            *[f"test_case.py::test_ungrouped[{i}]" for i in range(4)],
        ]
        assert sorted(manifest["nodeid_aliases"].values()) == sorted(expected)
    if workers:
        assert result["worker_facts"]["created"][0]["count"] == 2
        assert result["worker_facts"]["executing"] == ["gw0", "gw1"]
        assert len({entry["pid"] for entry in result["worker_facts"]["executing_processes"]}) == 2
        assert result["worker_facts"]["observed_peak_overlap"] == 2
        for part in ("test_native", "test_composite"):
            owners = {
                e["worker"] for e in journal if e["event"] == "phase_start" and part in e["nodeid"]
            }
            assert len(owners) == 1
        assert any("@extra_fixture" in raw for raw in manifests[0]["selected"])
    else:
        assert all(os.environ[name] == value for name, value in inherited_identity.items())
        assert result["worker_facts"]["executing"] == ["controller"]
        assert result["worker_facts"]["observed_peak_overlap"] == 1
        assert result["session_contexts"][0]["worker"] == "controller"
        assert result["session_contexts"][0]["effective_worker_count"] == 0


@pytest.mark.parametrize("workers", [0, 2])
@pytest.mark.parametrize("failure", ["collection", "setup", "teardown", "loss"])
def test_real_distributed_failure_boundaries(tmp_path, workers, failure):
    sources = {
        "collection": "raise RuntimeError('collection control')\n",
        "setup": (
            "import pytest\n@pytest.fixture\ndef broken():\n"
            "    raise RuntimeError('setup control')\ndef test_case(broken):\n    pass\n"
        ),
        "teardown": (
            "import pytest\n@pytest.fixture\ndef broken():\n    yield\n"
            "    raise RuntimeError('teardown control')\ndef test_case(broken):\n    pass\n"
        ),
        "loss": "import os\ndef test_case():\n    os._exit(19)\n",
    }
    output = isolated(tmp_path, sources[failure], workers)
    result = classify_receipt(output)
    assert result["status"] in {"failed", "incomplete"}
    if failure == "collection":
        assert result["collection_errors"]
    elif failure in {"setup", "teardown"}:
        node = next(iter(result["nodes"].values()))
        assert node["status"] == "failed"
        assert any(r["when"] == failure and r["outcome"] == "failed" for r in node["reports"])
    else:
        assert result["active_phases"]
        if workers:
            assert result["worker_loss"]


def test_project_policy_ends_native_worker_loss_without_restarting(tmp_path, monkeypatch):
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    case = tmp_path / "case"
    case.mkdir()
    (case / "conftest.py").write_text(
        "import json\nfrom pathlib import Path\n"
        "def pytest_configure(config):\n"
        "    if not hasattr(config, 'workerinput'):\n"
        "        Path('effective-policy.json').write_text(json.dumps({\n"
        "            'restart': config.getoption('maxworkerrestart'),\n"
        "            'workers': config.getoption('numprocesses'),\n"
        "            'distribution': config.getoption('dist'),\n"
        "        }))\n"
    )
    (case / "test_case.py").write_text(
        "import os\nimport pytest\n"
        "@pytest.mark.xdist_group('fatal_control')\n"
        "def test_crash():\n    os._exit(73)\n"
        "@pytest.mark.xdist_group('fatal_control')\n"
        "@pytest.mark.parametrize('index', range(6))\n"
        "def test_unexecuted(index):\n    raise AssertionError('queued body must not run')\n"
        "def test_independent():\n    pass\n"
    )
    output = tmp_path / "receipt"
    output.mkdir()
    process = run_python(
        output,
        ["-c", str(ROOT / "pyproject.toml"), "-n", "2", str(case)],
        cwd=case,
        timeout=60,
        test_timeout=30,
    )
    shutil.copyfile(case / "effective-policy.json", output / "effective-policy.json")
    retained = os.environ.get("QUALIFICATION_CONTROL_RECEIPTS")
    if retained:
        shutil.copytree(output, Path(retained) / f"{tmp_path.name}-policy-{uuid4().hex}")
    result = classify_receipt(output)
    assert process["returncode"] != 0
    assert "interruption" not in process
    assert not process["owned_group_cleanup"]["group_present_after_cleanup"]
    assert result["status"] in {"failed", "incomplete"}
    assert len(result["selected"]) == 8
    assert len(result["worker_loss"]) == 1
    assert result["worker_facts"]["created"][0]["count"] == 2
    tail = [node for name, node in result["nodes"].items() if "::test_unexecuted[" in name]
    assert len(tail) == 6
    assert {node["status"] for node in tail} == {"not_run"}
    policy = json.loads((case / "effective-policy.json").read_text())
    assert int(policy["restart"]) == 0
    assert policy["workers"] == 2 and policy["distribution"] == "loadgroup"
    ready_workers = {
        event["ready_worker"] for event in events(output) if event["event"] == "worker_ready"
    }
    assert ready_workers == {"gw0", "gw1"}


@pytest.mark.parametrize("workers,mixed", [(2, False), (0, True)])
def test_fault_lane_collection_refuses_without_running_bodies(tmp_path, workers, mixed):
    root_hooks = (ROOT / "conftest.py").read_text()
    source = (
        "import pytest\n@pytest.mark.shared_cluster_fault\ndef test_fault():\n"
        "    raise AssertionError('body forbidden')\n"
    )
    if mixed:
        source += "def test_ordinary():\n    raise AssertionError('body forbidden')\n"
    output = isolated(tmp_path, source, workers, conftest=root_hooks, args=("--collect-only",))
    result = classify_receipt(output)
    assert result["process"]["returncode"] != 0
    assert not any(e["event"] == "phase_start" for e in events(output))
    assert "shared_cluster_fault controls" in (output / "pytest.stderr").read_text()


@pytest.mark.parametrize("coarse", [False, True])
def test_dependency_affinity_frees_content_and_cold_controls(tmp_path, coarse):
    root_hooks = (ROOT / "conftest.py").read_text()
    if coarse:
        root_hooks = (
            "import pytest\n@pytest.hookimpl(wrapper=True, tryfirst=True)\n"
            "def pytest_collection_modifyitems(items):\n"
            "    for item in items: item.add_marker(pytest.mark.xdist_group('math_preparation'))\n"
            "    yield\n"
        )
    source = """import pytest
from pathlib import Path
@pytest.fixture(scope="session")
def spike_content(): return object()
@pytest.fixture(scope="session")
def spike_readings(spike_content):
    with Path("read-count").open("a") as handle: handle.write("read\\n")
    return object()
@pytest.fixture(scope="session")
def spike_extraction(spike_readings): return spike_readings
@pytest.fixture(scope="session")
def spike_scoped(spike_extraction): return spike_extraction
def test_read(spike_readings): pass
def test_extract(spike_extraction): pass
def test_scope(spike_scoped, spike_readings): assert spike_scoped is spike_readings
def test_content(spike_content): pass
def test_cold(): pass
"""
    output = isolated(tmp_path, source, 2, conftest=root_hooks)
    result = classify_receipt(output)
    assert result["status"] == "passed"
    manifest = next(e for e in events(output) if e["event"] == "collection_finish")
    grouped = {
        logical
        for raw, logical in manifest["nodeid_aliases"].items()
        if raw.endswith("@math_preparation")
    }
    expected = {"test_case.py::test_read", "test_case.py::test_extract", "test_case.py::test_scope"}
    if coarse:
        expected |= {"test_case.py::test_content", "test_case.py::test_cold"}
    assert grouped == expected
    assert (tmp_path / "case" / "read-count").read_text().splitlines() == ["read"]
    owners = {
        e["worker"]
        for e in events(output)
        if e["event"] == "phase_start" and "@math_preparation" in e["nodeid"]
    }
    assert len(owners) == 1
    content_only = tmp_path / "content-only"
    content_only.mkdir()
    output = isolated(content_only, source, 2, conftest=root_hooks, args=("-k", "test_content"))
    assert classify_receipt(output)["status"] == "passed"
    assert not (content_only / "case" / "read-count").exists()


def test_actual_math_collection_preparation_inventory(tmp_path):
    output = tmp_path / "collection"
    output.mkdir()
    run_python(
        output,
        ["-o", "addopts=", "-n", "0", "--collect-only", "python/corpus-structure/tests/math"],
        timeout=60,
    )
    result = classify_receipt(output)
    assert result["process"]["returncode"] == 0
    manifest = next(e for e in events(output) if e["event"] == "collection_finish")
    aliases = manifest["nodeid_aliases"]
    selected = set(aliases.values())
    grouped = {
        aliases[node]
        for node, groups in manifest["affinity_groups"].items()
        if "math_preparation" in groups
    }
    assert grouped
    assert len(grouped) < len(manifest["selected"])
    # Session reading, extraction and transitive scope consumers still share preparation.
    shared = {
        "python/corpus-structure/tests/math/test_property.py::test_corpus_layer_on_the_spike_pages",
        "python/corpus-structure/tests/math/test_spans.py::test_m09_on_the_spike_pages",
        "python/corpus-structure/tests/math/test_scope.py::test_core_standing_contexts",
    }
    assert shared <= grouped
    # The controlled transport oracle takes retained content only and prepares its own Normal
    # page with an explicit budget; it does not consume the shared session reading/extraction.
    parity = (
        "python/corpus-structure/tests/math/test_workers.py::"
        "test_staged_corpus_relations_preserve_direct_page_semantics"
    )
    assert parity in selected
    assert parity not in grouped
    assert not any(
        "test_real_spawn_transports" in node or "test_m13_rebuilds" in node for node in grouped
    )
    assert not result["native_contexts"]
    assert not any(e["event"] == "phase_start" for e in events(output))


def test_public_report_section_survives_two_worker_serialization(tmp_path):
    output = isolated(
        tmp_path,
        """def test_case(request):
    request.node.add_report_section(
        "call", "public scenario", "guard=fixture; diagnostic=public-control"
    )
    assert False, "deliberate conformance failure"
""",
        2,
    )
    result = classify_receipt(output)
    assert result["status"] == "failed"
    node = next(iter(result["nodes"].values()))
    call = next(r for r in node["reports"] if r["when"] == "call")
    assert ["Captured public scenario call", "guard=fixture; diagnostic=public-control"] in call[
        "sections"
    ]


def test_preparation_affinity_follows_imported_shared_and_qualified_local_fixtures(tmp_path):
    hooks = (
        (ROOT / "conftest.py").read_text()
        + """
from shared_support import statistics_pack_prepared, statistics_rules_policy
PREPARATION_AFFINITY += (("profile", "test_case.py", "local_profile"),)
@pytest.fixture
def profile(): return "local"
"""
    )
    support = """import pytest
from pathlib import Path
@pytest.fixture(scope="session")
def statistics_pack_prepared():
    with Path("prepare-count").open("a") as stream: stream.write("prepared\\n")
    return object()
@pytest.fixture(scope="session")
def statistics_rules_policy(statistics_pack_prepared): return statistics_pack_prepared
"""
    source = """import pytest
@pytest.mark.xdist_group("statistics_pack")
@pytest.mark.xdist_group("statistics_pack")
def test_shared(statistics_pack_prepared, statistics_rules_policy):
    assert statistics_pack_prepared is statistics_rules_policy
def test_local(profile): assert profile == "local"
"""
    other = """def test_shared_elsewhere(statistics_pack_prepared): pass
def test_unrelated(profile): assert profile == "local"
"""
    output = isolated(
        tmp_path,
        source,
        2,
        conftest=hooks,
        extra_files=(("shared_support.py", support), ("test_other.py", other)),
    )
    result = classify_receipt(output)
    assert result["status"] == "passed"
    manifest = next(event for event in events(output) if event["event"] == "collection_finish")
    groups = {
        logical: manifest["affinity_groups"][raw]
        for raw, logical in manifest["nodeid_aliases"].items()
    }
    assert set(groups["test_case.py::test_shared"]) == {"statistics_pack"}
    assert groups["test_other.py::test_shared_elsewhere"] == ["statistics_pack"]
    assert groups["test_case.py::test_local"] == ["local_profile"]
    assert groups["test_other.py::test_unrelated"] == []
    assert (tmp_path / "case" / "prepare-count").read_text().splitlines() == ["prepared"]
    owners = {
        event["worker"]
        for event in events(output)
        if event["event"] == "phase_start" and event["nodeid"].endswith("@statistics_pack")
    }
    assert len(owners) == 1


def test_distinct_preparation_affinity_refuses_before_execution(tmp_path):
    hooks = (ROOT / "conftest.py").read_text()
    source = """import pytest
@pytest.fixture
def statistics_pack_prepared(): return object()
@pytest.mark.xdist_group("another_preparation")
def test_conflict(statistics_pack_prepared): raise AssertionError("body must not run")
"""
    output = isolated(tmp_path, source, 2, conftest=hooks)
    result = classify_receipt(output)
    assert result["process"]["returncode"] != 0
    assert not any(event["event"] == "phase_start" for event in events(output))
    diagnostic = (output / "pytest.stdout").read_text() + (output / "pytest.stderr").read_text()
    assert "conflicting preparation affinity groups" in diagnostic
