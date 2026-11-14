"""Native TAP parser and pg_prove boundaries; no PostgreSQL acquisition."""

import json
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url

from pgtap_batch import (
    SelectedCase,
    SqlBatch,
    controlled_environment,
    run_sql_batch,
    selected_sql_cases,
)

ADAPTER = Path(__file__).resolve().parents[2] / "scripts" / "pgtap"
MANIFEST = {"cases": [{"name": "sample.test_one", "assertions": 1}]}
VALID = "# CORPUS_CONTEXT {}\n# Subtest: sample.test_one()\n    ok 1 - expected\n    1..1\nok 1 - sample.test_one\n1..1\n"


def parse(tap, *, manifest=MANIFEST, exit=0):
    result = subprocess.run(
        [
            "perl",
            "-I",
            str(ADAPTER),
            "-MCorpus::Report",
            "-MJSON::PP",
            "-e",
            "local $/; my $v=decode_json(<STDIN>); print encode_json(Corpus::Report::analyze($v->{tap},$v->{manifest},$v->{process}));",
        ],
        input=json.dumps(
            {"tap": tap, "manifest": manifest, "process": {"exit": exit, "wait": exit * 256}}
        ),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_native_parser_preserves_completed_observation_and_declared_count():
    report = parse(VALID)
    assert report["valid"] is True
    assert report["observed"]["sample.test_one"]["assertions"] == 1
    assert report["observed"]["sample.test_one"]["status"] == "passed"
    # A generated 1..0 plan cannot make a deleted authored assertion acceptable.
    deleted = parse(VALID.replace("    ok 1 - expected\n", "").replace("    1..1", "    1..0"))
    assert deleted["valid"] is False


@pytest.mark.parametrize(
    "tap",
    [
        VALID.replace("    ok 1 - expected", "    not ok 1 - wrong reason"),
        VALID.replace("    ok 1 - expected", "    ok 1 - expected # TODO later"),
        VALID.replace("    ok 1 - expected", "    ok 1 - expected # SKIP absent"),
        VALID.replace("    1..1", "    1..2"),
        VALID.replace("    1..1", "    ok 1 - duplicate\n    1..2"),
        VALID.replace("sample.test_one", "sample.unknown"),
        VALID.replace("    1..1", "    # Subtest: nested()\n    1..1"),
        VALID.replace("    1..1", "    gibberish\n    1..1"),
        VALID.replace("    1..1", "    Bail out! stopped\n    1..1"),
        VALID.replace("ok 1 - sample.test_one\n1..1\n", ""),
        VALID.replace("# CORPUS_CONTEXT {}\n", ""),
        VALID.replace("# CORPUS_CONTEXT {}", "# CORPUS_CONTEXT malformed"),
        VALID + "unexpected output\n",
        VALID + "# CORPUS_CONTEXT {}\n",
        VALID + "# Subtest: sample.test_one()\n    ok 1\n    1..1\nok 2 - sample.test_one\n",
    ],
)
def test_invalid_stream_never_qualifies_any_member(tap, tmp_path):
    report = parse(tap)
    assert report["valid"] is False
    with pytest.raises(AssertionError, match="invalid pgTAP batch"):
        SqlBatch(report, tmp_path).require_pass("sample.test_one")


def test_nonzero_exit_and_missing_selected_sibling_invalidate_batch():
    assert parse(VALID, exit=3)["valid"] is False
    report = parse(
        VALID,
        manifest={"cases": MANIFEST["cases"] + [{"name": "sample.test_two", "assertions": 2}]},
    )
    assert report["valid"] is False
    assert report["observed"]["sample.test_one"]["status"] == "passed"
    assert "sample.test_two" not in report["observed"]


def test_environment_removes_ambient_runner_and_libpq_controls():
    url = make_url("postgresql+psycopg://expected:secret@localhost:5434/owned")
    env = controlled_environment(
        {
            "PATH": "/usr/bin",
            "PERL5OPT": "-MUntrusted",
            "PERL5LIB": "bad",
            "HARNESS_RULESFILE": "bad",
            "PERL_TEST_HARNESS_DUMP_TAP": "bad",
            "PROVE_SWITCHES": "bad",
            "PGDATABASE": "other",
            "PGOPTIONS": "-c role=other",
            "TEST_VERBOSE": "1",
        },
        url,
    )
    assert env == {
        "PATH": "/usr/bin",
        "PGHOST": "localhost",
        "PGPORT": "5434",
        "PGDATABASE": "owned",
        "PGUSER": "expected",
        "PGPASSWORD": "secret",
        "PGCONNECT_TIMEOUT": "15",
    }


@pytest.mark.parametrize("drop_endpoint,exit_code", [(False, 0), (True, 0), (False, 3)])
def test_real_pg_prove_uses_native_source_with_conflicting_configuration(
    tmp_path, drop_endpoint, exit_code
):
    # An executable source double tests pg_prove's installed source-handler route.
    psql = tmp_path / "psql"
    psql.write_text(
        "#!/usr/bin/python3\nimport sys,json\nfrom pathlib import Path\nwith Path(__file__).with_name('invocations').open('a') as log: log.write(json.dumps(sys.argv[1:])+'\\n')\nprint("
        + repr(VALID)
        + ",end='')\nprint('retained source stderr',file=sys.stderr)\nsys.exit("
        + str(exit_code)
        + ")\n"
    )
    psql.chmod(0o755)
    (tmp_path / ".proverc").write_text("--require Missing::Ambient\n--state failed,save\n-j9\n")
    (tmp_path / "testrules.yml").write_text("invalid: [\n")
    source = tmp_path / "selected.pg"
    source.write_text("SELECT 'the source handler must pass --file';")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            MANIFEST
            | {
                "launch": {
                    "psql": str(psql),
                    "host": "localhost",
                    "port": "5434",
                    "dbname": "owned",
                    "username": "owner",
                }
            }
        )
    )
    env = controlled_environment(
        dict(os.environ)
        | {
            "PERL5OPT": "-MMissing::Ambient",
            "HARNESS_RULESFILE": str(tmp_path / "testrules.yml"),
            "PERL_TEST_HARNESS_DUMP_TAP": str(tmp_path / "unowned-spool"),
        },
        make_url("postgresql://owner@localhost:5434/owned"),
    )
    env.update(
        PERL5LIB=str(ADAPTER),
        CORPUS_PGTAP_RAW=str(tmp_path / "raw.tap"),
        CORPUS_PGTAP_REPORT=str(tmp_path / "report.json"),
        CORPUS_PGTAP_MANIFEST=str(manifest),
        HOME=str(tmp_path),
    )
    endpoint = (
        []
        if drop_endpoint
        else ["--host", "localhost", "--port", "5434", "--dbname", "owned", "--username", "owner"]
    )
    result = subprocess.run(
        [
            "pg_prove",
            "--norc",
            "--jobs",
            "1",
            "--rules",
            "seq=*",
            "--harness",
            "Corpus::Harness",
            "--formatter",
            "Corpus::Formatter",
            "--nocolor",
            "--psql-bin",
            str(psql),
            *endpoint,
            str(source),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    if drop_endpoint:
        assert result.returncode != 0
        assert "missing/changed native pgTAP source option: host" in result.stderr
        assert not (tmp_path / "raw.tap").exists()
        assert not (tmp_path / "invocations").exists()
        return
    assert result.returncode == (1 if exit_code else 0), result.stderr
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["valid"] is (not bool(exit_code))
    assert report["process"]["exit"] == exit_code
    assert report["observed"]["sample.test_one"]["status"] == "passed"
    invocations = (tmp_path / "invocations").read_text().splitlines()
    assert len(invocations) == 1
    arguments = json.loads(invocations[0])
    assert "--no-psqlrc" in arguments
    assert arguments[arguments.index("--set") + 1] == "ON_ERROR_STOP=1"
    assert arguments[arguments.index("--file") + 1] == str(source)
    assert arguments[arguments.index("--dbname") + 1] == "owned"
    assert (tmp_path / "raw.tap").read_text() == VALID
    assert "retained source stderr" in result.stderr
    assert not (tmp_path / "unowned-spool").exists()
    assert not (tmp_path / ".pg_prove").exists()


def test_selection_keeps_exact_logical_ids_and_finite_subset(monkeypatch):
    monkeypatch.setattr("qualification_plugin.logical_nodeid", lambda item: item.original)

    def item(name, original, group="family"):
        marker = SimpleNamespace(args=("sample", name), kwargs={"assertions": 2})
        affinity = SimpleNamespace(args=(group,), kwargs={})
        return SimpleNamespace(
            original=original,
            get_closest_marker=lambda _: marker,
            iter_markers=lambda _: iter([affinity]),
        )

    first = item("test_one", "module.py::test_one[param]")
    second = item("test_two", "module.py::test_two")
    assert [c.nodeid for c in selected_sql_cases(SimpleNamespace(items=[first]), "sample")] == [
        first.original
    ]
    assert len(selected_sql_cases(SimpleNamespace(items=[first, second]), "sample")) == 2
    with pytest.raises(ValueError, match="unique"):
        selected_sql_cases(SimpleNamespace(items=[first, first]), "sample")
    with pytest.raises(ValueError, match="affinity"):
        selected_sql_cases(
            SimpleNamespace(items=[first, item("test_two", "other", "different")]), "sample"
        )


@pytest.mark.parametrize(
    "changed",
    [
        {},
        {"database": "foreign"},
        {"database_oid": 99},
        {"session_user": "other"},
        {"server_started": "new incarnation"},
    ],
)
def test_batch_binds_observed_psql_context_to_each_selected_logical_item(
    monkeypatch, tmp_path, changed
):
    context = {
        "database": "owned",
        "database_oid": 42,
        "current_user": "owner",
        "session_user": "owner",
        "server_version": "18",
        "server_started": "2026-11-13",
        "host": "127.0.0.1",
        "port": 5434,
    } | changed

    @contextmanager
    def connect():
        info = SimpleNamespace(dbname="owned", user="owner", host="localhost", port=5434)
        yield SimpleNamespace(
            connection=SimpleNamespace(driver_connection=SimpleNamespace(info=info)),
            execute=lambda _: SimpleNamespace(one=lambda: (42, "2026-11-13")),
        )

    clone = SimpleNamespace(
        admin=SimpleNamespace(
            url=make_url("postgresql://owner@localhost:5434/owned"),
            connect=connect,
            dispose=lambda: None,
        ),
        stage=SimpleNamespace(family="sample", cases=("test_one", "test_two"), adapter=ADAPTER),
        origin={"recipe_id": "owned-seed"},
    )
    calls, contexts = [], []

    def execute(command, *, env, **kwargs):
        manifest = json.loads(Path(env["CORPUS_PGTAP_MANIFEST"]).read_text())
        calls.append((command, manifest, Path(command[-1]).read_text()))
        report = {
            "valid": True,
            "context": context,
            "errors": [],
            "observed": {case["name"]: {"status": "passed"} for case in manifest["cases"]},
        }
        Path(env["CORPUS_PGTAP_REPORT"]).write_text(json.dumps(report))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("pgtap_batch.subprocess.run", execute)
    monkeypatch.setattr(
        "qualification_plugin.record_native_context",
        lambda context, *, nodeid: contexts.append((nodeid, context)),
    )
    monkeypatch.setattr("qualification_plugin.record_sql_batch", lambda *args, **kwargs: None)
    selected = (
        SelectedCase("module.py::first[param]", "test_one", 1),
        SelectedCase("module.py::second", "test_two", 2),
    )
    batch = run_sql_batch(clone, selected, tmp_path)
    assert [nodeid for nodeid, _ in contexts] == [case.nodeid for case in selected]
    assert all(
        value["acquired"]["session_user"] == context["session_user"] for _, value in contexts
    )
    assert batch.report["valid"] is (not bool(changed))
    # A fresh exact retry executes only its member; there is no historical-pass cache.
    run_sql_batch(clone, selected[1:], tmp_path)
    assert len(calls) == 2
    assert [case["name"] for case in calls[1][1]["cases"]] == ["sample.test_two"]
    assert "test_one" not in calls[1][2]
