"""Actual registered command dispatch preserves semantic, database and defect outcomes."""

from __future__ import annotations

import json
from contextlib import contextmanager
from types import SimpleNamespace

import psycopg
import pytest
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.semantic import ReferenceError
from corpus_structure.semantic.refusals import SemanticRefusal


@pytest.mark.parametrize("command", ["golden", "eval", "regenerate"])
@pytest.mark.parametrize("kind", ["refusal", "retry", "fencing", "defect", "bug", "cancel"])
def test_actual_command_failure_classification(cli, monkeypatch, tmp_path, command, kind):
    from corpus_structure.core.db.store import FENCING_CONSTRAINT
    from corpus_structure.semantic import regeneration, runtime

    if kind == "refusal":
        failure = (
            ReferenceError("reference selection refused")
            if command != "regenerate"
            else SemanticRefusal("pack refused")
        )
    elif kind == "retry":
        failure = DBAPIError(None, None, psycopg.errors.SerializationFailure("retry"))
    elif kind == "fencing":

        class Fenced(Exception):
            sqlstate = "23505"
            diag = SimpleNamespace(constraint_name=FENCING_CONSTRAINT)

        failure = DBAPIError(None, None, Fenced("fenced"))
    elif kind == "defect":
        failure = DBAPIError(None, None, psycopg.errors.UndefinedColumn("broken SQL"))
    elif kind == "bug":
        failure = ValueError("implementation defect")
    else:
        failure = KeyboardInterrupt()

    @contextmanager
    def unavailable(*args, **kwargs):
        raise failure
        yield

    def bad_pack(*args, **kwargs):
        raise failure

    monkeypatch.setattr(runtime, "open_runtime_engine", unavailable)
    monkeypatch.setattr(regeneration, "prepare_pack", bad_pack)
    args = {
        "golden": ("golden", "status", "--json"),
        "eval": ("eval", "run", "--run", "1", "--set-id", "1", "--json"),
        "regenerate": ("regenerate", "--domain", "toy", "--corpus", str(tmp_path), "--json"),
    }[command]
    result = cli(*args)
    assert result.exit_code != 0
    if kind in {"bug", "cancel"}:
        assert "refused:" not in result.output
        assert '"error"' not in result.output
        if kind == "bug":
            assert result.exception is failure
        return
    error = json.loads(result.stdout)["error"]
    expected = type(failure).__name__ if kind == "refusal" else "database_" + kind
    assert error["code"] == expected


def test_invalid_pack_is_a_typed_actual_regenerate_refusal(cli, tmp_path):
    result = cli(
        "regenerate", "--domain", "absent-fixture-pack", "--corpus", str(tmp_path), "--json"
    )
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "PackInputError"
