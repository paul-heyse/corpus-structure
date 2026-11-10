"""Retained safe recipe output is bounded, authenticated, and read without execution."""

from __future__ import annotations

import hashlib
import json
import signal
import subprocess
from dataclasses import asdict, replace

import pytest

from corpus_structure._diagnostic_capture import (
    STEP_STREAM_BYTES,
    StepExit,
    bounded_safe_output,
    safe_prefix_output,
    valid_step_output,
)
from corpus_structure.cli import operations, recipes
from corpus_structure.cli.managed import Invocation, ResultError, ResultStore
from corpus_structure.cli.recipe_output import ROLE, read_output, retain_output


def test_native_prefix_drops_partial_credentials_and_multiline_control_tokens():
    prefix = b"retained\npostgresql://operator:secret-before-at"
    row = safe_prefix_output("stdout", prefix, len(prefix) + 50)
    assert row.text == "retained\n" and row.truncated
    assert row.observed_source_bytes == len(prefix) + 50
    assert row.examined_source_bytes == 9
    assert row.unexamined_source_bytes == len(prefix) + 41
    control = b"retained\n\x1b]0;not-displayable\n"
    output = safe_prefix_output("stderr", control, len(control) + 10)
    assert output.text == "retained\n" and output.examined_source_bytes == 9
    expanded = safe_prefix_output("stdout", b"\xff" * STEP_STREAM_BYTES, STEP_STREAM_BYTES)
    assert expanded.derived_safe_bytes == 3 * STEP_STREAM_BYTES
    assert expanded.retained_safe_bytes == len(expanded.text.encode()) <= STEP_STREAM_BYTES
    assert expanded.omitted_safe_bytes == expanded.derived_safe_bytes - expanded.retained_safe_bytes
    assert expanded.unexamined_source_bytes == 0 and expanded.truncated
    assert not valid_step_output(replace(expanded, omitted_safe_bytes=1))


def test_direct_output_complete_beyond_compact_tail_and_paged_without_reexecution(
    cli, tmp_path, monkeypatch
):
    original = "EARLY-ERROR\n" + "λ\tline\n" * 5000 + "LAST-LINE\n"
    monkeypatch.setattr(
        operations,
        "run_recipe",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            [], 17, original, "password=must-hide\n"
        ),
    )
    report = cli("check", "--only", "types", "--json", env={"CORPUS_CI_RESULTS": str(tmp_path)})
    assert report.exit_code == 17, report.output
    body = json.loads(report.stdout)
    assert body["exit_code"] == 17 and "EARLY-ERROR" not in body["output"]
    assert body["retained_output"]["availability"] == "available"
    identity = body["invocation_id"]
    monkeypatch.setattr(
        operations, "run_recipe", lambda *args, **kwargs: pytest.fail("retained read reran recipe")
    )
    chunks = []
    offset = 0
    while True:
        response = cli(
            "results",
            "output",
            identity,
            "--stream",
            "stdout",
            "--after",
            str(offset),
            "--max-bytes",
            "4096",
            "--json",
            env={"CORPUS_CI_RESULTS": str(tmp_path)},
        )
        assert response.exit_code == 0, response.output
        assert len(response.stdout.rstrip("\n").encode()) <= 4096
        page = json.loads(response.stdout)
        assert page["coordinate"] == "retained_safe_unicode_codepoints"
        assert page["after"] == offset and page["end"] - offset == len(page["text"])
        chunks.append(page["text"])
        if page["next_after"] is None:
            break
        assert page["next_after"] > offset
        offset = page["next_after"]
    assert "".join(chunks) == original
    stderr = read_output(ResultStore(tmp_path), identity, stream="stderr")
    assert stderr.text == "password=**********\n" and not stderr.collection_truncated


def test_native_output_collection_truncation_has_exact_source_counts(tmp_path):
    store = ResultStore(tmp_path)
    raw = b"complete line\n" + b"a" * STEP_STREAM_BYTES
    output = safe_prefix_output("stdout", raw[:STEP_STREAM_BYTES], len(raw))
    assert output.text == "complete line\n"
    empty = safe_prefix_output("stderr", b"", 0)
    captured = recipes.RecipeCapture(
        "available", records=(StepExit("types", 1, False, False, (), (output, empty)),)
    )
    with store.operation("recipe.check") as invocation:
        reference = retain_output(
            invocation,
            "check",
            1,
            stdout="wrapper",
            stderr="",
            stdout_source_bytes=7,
            stderr_source_bytes=0,
            captured=captured,
        )
        assert reference.availability == "available"
        invocation.settle("failed")
    page = read_output(store, invocation.id, stream="stdout")
    assert page.step == "types" and page.text == "complete line\n"
    assert page.collection_truncated and page.next_after is None
    assert page.observed_source_bytes == len(raw)
    assert page.unexamined_source_bytes == STEP_STREAM_BYTES
    assert page.examined_source_bytes == len(b"complete line\n")


def _retained(store):
    with store.operation("recipe.control") as invocation:
        retain_output(
            invocation,
            "control",
            0,
            stdout="retained",
            stderr="",
            stdout_source_bytes=8,
            stderr_source_bytes=0,
        )
    return invocation


def test_absent_corrupt_and_unsupported_recipe_output_refuse(tmp_path):
    store = ResultStore(tmp_path)
    with store.operation("older") as old:
        pass
    with pytest.raises(ResultError, match="unavailable"):
        read_output(store, old.id, stream="stdout")
    invocation = _retained(store)
    artifact = invocation.directory / "recipe-output.json"
    artifact.write_bytes(b"X" + artifact.read_bytes()[1:])
    with pytest.raises(ResultError, match="corrupt"):
        read_output(store, invocation.id, stream="stdout")
    unsupported = _retained(store)
    artifact = unsupported.directory / "recipe-output.json"
    document = json.loads(artifact.read_bytes())
    document["version"] = 99
    encoded = json.dumps(document).encode()
    artifact.write_bytes(encoded)
    manifest_path = unsupported.directory / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["details"]["recipe_output"] = {
        "version": 1,
        "length": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ResultError, match="unsupported"):
        read_output(store, unsupported.id, stream="stdout")


def test_invalid_or_overflow_step_channel_is_explicitly_unavailable(monkeypatch):
    for payload in (b"malformed\n", b"plan types\nstart types\n{invalid}\n", b"plan types\nstart"):
        steps, excerpts, captured = recipes._recipe_steps(payload, interrupted=False)
        assert steps == excerpts == () and captured.availability == "unavailable"
    monkeypatch.setattr(recipes, "_STEP_BYTES", 8)
    _, _, captured = recipes._recipe_steps(b"plan types\n", interrupted=False)
    assert captured.reason is not None
    assert captured.availability == "unavailable" and "byte limit" in captured.reason


def test_bundle_requires_exact_step_and_rejects_invalid_accounting(tmp_path):
    output = bounded_safe_output(
        "stdout",
        "native",
        source_coordinate="native_bytes",
        observed_source_bytes=6,
        examined_source_bytes=6,
    )
    error = bounded_safe_output(
        "stderr",
        "",
        source_coordinate="native_bytes",
        observed_source_bytes=0,
        examined_source_bytes=0,
    )
    first = StepExit("types", 1, False, False, (), (output, error))
    second = StepExit("lint", 0, False, False, (), (output, error))
    store = ResultStore(tmp_path)
    with store.operation("recipe.bundle") as invocation:
        retain_output(
            invocation,
            "bundle",
            1,
            stdout="",
            stderr="",
            stdout_source_bytes=0,
            stderr_source_bytes=0,
            captured=recipes.RecipeCapture("available", records=(first, second)),
        )
    with pytest.raises(ResultError, match="--step"):
        read_output(store, invocation.id, stream="stdout")
    selected = read_output(store, invocation.id, stream="stdout", step="types")
    assert selected.step == "types" and selected.text == "native"
    invalid = replace(first, outputs=(replace(output, observed_source_bytes=-1), error))
    payload = b"plan types\nstart types\n" + json.dumps(asdict(invalid)).encode() + b"\n"
    _, _, captured = recipes._recipe_steps(payload, interrupted=False)
    assert captured.availability == "unavailable"


def test_optional_output_publication_failure_preserves_recipe_exit(cli, tmp_path, monkeypatch):
    publish = Invocation.publish

    def refuse(invocation, role, path):
        if role == ROLE:
            raise OSError("output unavailable")
        return publish(invocation, role, path)

    monkeypatch.setattr(Invocation, "publish", refuse)
    monkeypatch.setattr(
        operations,
        "run_recipe",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 17, "failure", ""),
    )
    result = cli("check", "--only", "types", "--json", env={"CORPUS_CI_RESULTS": str(tmp_path)})
    assert result.exit_code == 17
    report = json.loads(result.stdout)
    assert report["exit_code"] == 17 and report["retained_output"]["availability"] == "unavailable"
    assert ResultStore(tmp_path).show(report["invocation_id"]).outcome == "failed"


def test_cancelled_recipe_keeps_interruption_identity(cli, tmp_path, monkeypatch):
    def interrupted(*args):
        raise recipes.RecipeCancellation(signal.SIGTERM)

    monkeypatch.setattr(operations, "run_recipe_steps", interrupted)
    result = cli("check", "--view", "steps", "--json", env={"CORPUS_CI_RESULTS": str(tmp_path)})
    assert result.exit_code == 143
    (manifest,) = ResultStore(tmp_path).list(None, 10, "recipe.ci-check").results
    assert manifest.outcome == "interrupted"


@pytest.mark.parametrize("quote", ["'", '"'])
def test_native_prefix_discards_unfinished_multiline_quoted_credentials(quote):
    prefix = ("kept\npassword=" + quote + "first-secret\nsecond-secret\n").encode()
    row = safe_prefix_output("stdout", prefix, len(prefix) + 40)
    assert row.text == "kept\n"
    assert row.examined_source_bytes == len(b"kept\n")
    assert row.unexamined_source_bytes == len(prefix) + 40 - len(b"kept\n")
    assert "first-secret" not in row.text and "second-secret" not in row.text


def test_native_prefix_omits_cut_known_multiline_secret(monkeypatch):
    monkeypatch.setenv("CORPUS_PROVIDER_TOKEN", "first-secret\nsecond-secret")
    prefix = b"kept\nfirst-secret\n"
    row = safe_prefix_output("stderr", prefix, len(prefix) + 40)
    assert row.text == "" and row.examined_source_bytes == 0
    assert row.unexamined_source_bytes == len(prefix) + 40
    complete = b"kept\nfirst-secret\nsecond-secret\nafter\n"
    full = safe_prefix_output("stderr", complete, len(complete))
    assert full.text == "kept\n**********\nafter\n"


@pytest.mark.parametrize("view", [[], ["--view", "steps"]])
def test_recipe_unsettled_cancellation_preserves_custody_and_output_unavailable(
    cli, tmp_path, monkeypatch, view
):
    def interrupted(*args, **kwargs):
        raise recipes.RecipeCancellation(signal.SIGTERM)

    monkeypatch.setattr(operations, "run_recipe", interrupted)
    monkeypatch.setattr(operations, "run_recipe_steps", interrupted)
    result = cli(
        "check", "--only", "types", *view, "--json", env={"CORPUS_CI_RESULTS": str(tmp_path)}
    )
    assert result.exit_code == 143
    store = ResultStore(tmp_path)
    (manifest,) = store.list(None, 10, "recipe.types").results
    assert manifest.outcome == "interrupted" and not manifest.custody_settled()
    assert manifest.details["custody_unsettled"] is True
    assert store.collect(apply=True, now=10**12).removed == []
    with pytest.raises(ResultError, match="unavailable"):
        read_output(store, manifest.id, stream="stdout")


def test_prefix_cut_preserves_complete_enclosing_multiline_redaction():
    prefix = b"kept\npassword='first-secret\nsecond-secret' token=\"unfinished\n"
    row = safe_prefix_output("stdout", prefix, len(prefix) + 40)
    assert row.text == "kept\n" and row.examined_source_bytes == len(b"kept\n")
