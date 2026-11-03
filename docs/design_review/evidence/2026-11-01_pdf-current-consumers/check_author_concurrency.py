"""Controlled subprocess checks; never real provider/reference qualification."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import threading
from dataclasses import asdict, replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import author_source_references as author

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAQAAAAGCAIAAABrW6giAAAAFElEQVR4nGP8//8/"
    "AwwwMSABcjgA5T4DCWUMPAMAAAAASUVORK5CYII="
)
CHILD = r"""
import base64, json, os, signal, sys, time
from pathlib import Path

root = Path(os.environ["AUTHOR_CONTROL_ROOT"])
mode = os.environ["AUTHOR_CONTROL_MODE"]
message = json.loads(sys.stdin.buffer.read())
text = message["message"]["content"][0]["text"]
kind = "C" if "You are fresh adjudicator C." in text else (
    "A" if "You are independent author A;" in text else "B"
)
payload = json.loads(text.split("\n", 1)[1])
session = sys.argv[sys.argv.index("--session-id") + 1]
assert sys.argv[sys.argv.index("--tools") + 1] == ""
assert sys.argv[sys.argv.index("--input-format") + 1] == "stream-json"
assert sys.argv[sys.argv.index("--output-format") + 1] == "stream-json"
assert "--verbose" in sys.argv and "--json-schema" in sys.argv
assert "--strict-mcp-config" in sys.argv and "--restricted" in sys.argv
images = [v["source"] for v in message["message"]["content"] if v["type"] == "image"]
assert len(images) == 2
for key, image in zip(("sampling", "normal"), images, strict=True):
    assert image["type"] == "base64" and image["media_type"] == "image/png"
    assert base64.b64decode(image["data"]) == (root / f"source-{key}.png").read_bytes()
assert not any(key.startswith(("CORPUS_", "PG", "DATABASE")) for key in os.environ)
assert payload["source_prompt_profile"] == "source-only-native-sections-1"
assert payload["annotation_guideline"] == "complete controlled annotation guideline"
assert set(payload["sources"]) == {"sampling", "normal"}
for item in payload["sources"].values():
    source = item["source"]
    assert source["text"] == "Alpha body\ncell"
    assert "integrated_context_json" not in source["context"]
    assert "frame" not in item and "parts" not in item
    assert source["native_evidence"][0]["handle"] == "native_evidence:0"
    assert source["text"][source["native_evidence"][0]["start"]:source["native_evidence"][0]["end"]] == "Alpha body"
    assert source["native_evidence"][0]["text"] == "Alpha body"
    assert source["native_evidence"][0]["precision"] == "character"
    assert item["context_sources"][0]["text"] == "Parent context"
assert "OMIT-RECONCILIATION-GRAPH" not in json.dumps(payload["sources"])
if kind == "C":
    assert (root / "A.validated").exists() and (root / "B.validated").exists()
    assert set(payload["independent_authors"]) == {"A", "B"}
    assert all(v["complete_batches"] == ["sampling-full", "normal-full"]
               for v in payload["independent_authors"].values())
else:
    assert "independent_authors" not in payload
    if kind == "B" and mode != "success":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
(root / (kind + ".started")).write_text(json.dumps({
    "pid": os.getpid(), "session": session, "cwd": os.getcwd()
}))
if kind in {"A", "B"}:
    deadline = time.monotonic() + 5
    while not all((root / (other + ".started")).exists() for other in ("A", "B")):
        assert time.monotonic() < deadline, "both independent children must start"
        time.sleep(.01)
print(json.dumps({"type": "system", "subtype": "init", "session_id": session}), flush=True)
if mode == "both_refusals" or (mode == "failure" and kind == "A"):
    print(json.dumps({"type": "result", "subtype": "error_during_execution",
                      "session_id": session, "is_error": True,
                      "errors": ["controlled-provider-refusal"]}), flush=True)
elif kind == "B" and mode != "success":
    print("controlled partial B", flush=True)
    while True:
        time.sleep(1)
else:
    print(json.dumps({"type": "assistant", "session_id": session,
                      "message": {"content": [{"type": "text", "text": "control"}]}}))
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                      "stop_reason": "end_turn", "session_id": session, "structured_output": {
        "author": kind, "complete_batches": ["sampling-full", "normal-full"]
    }}), flush=True)
"""


def controlled_sources() -> dict:
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.proposals import native_frame_source, native_source_frame

    product = ProductReference(7, "integrated", "a" * 64)
    result = {}
    for ordinal, key in enumerate(("sampling", "normal")):
        parent_id = 20 + ordinal
        parent_view = SimpleNamespace(
            ref=SimpleNamespace(
                id=parent_id,
                key=f"{key}-parent",
                native_product=product,
                section_pointer="#/groups/0",
                membership="direct",
                projection_digest="b" * 64,
                recipe_digest="c" * 64,
            ),
            text="Parent context",
            items=({"self_ref": "#/texts/parent", "text": "Parent context"},),
            pieces=({"kind": "native_text", "item_ref": "#/texts/parent", "start": 0, "end": 14},),
            ancestors=(),
            health={"outcome": "qualified control"},
        )
        context = {
            "items": [
                {"self_ref": "#/texts/0", "label": "text", "text": "Alpha body"},
                {
                    "self_ref": "#/tables/0",
                    "label": "table",
                    "data": {"table_cells": [{"text": "cell", "row_span": 1, "col_span": 1}]},
                },
            ],
            "pieces": [
                {"kind": "native_text", "item_ref": "#/texts/0", "start": 0, "end": 10},
                {"kind": "separator", "start": 10, "end": 11},
                {
                    "kind": "native_text",
                    "item_ref": "#/tables/0",
                    "start": 11,
                    "end": 15,
                    "cell_index": 0,
                    "source_field": "cell_text",
                },
            ],
            "ancestors": [{"self_ref": "#/groups/0", "name": "Full parent title"}],
            "health": {"outcome": "partial", "scope": "entire controlled section"},
            "integrated_context_json": canonical_bytes(
                {
                    "selection": asdict(product),
                    "relations": [{"retained_only": "OMIT-RECONCILIATION-GRAPH"}],
                    "occurrences": [
                        {
                            "occurrence_id": f"{key}-text",
                            "pointer": "#/texts/0",
                            "precision": "character",
                            "address_space": "native_item",
                        }
                    ],
                }
            ).decode(),
        }
        view = SimpleNamespace(
            ref=SimpleNamespace(
                id=10 + ordinal,
                key=f"{key}-full",
                native_product=product,
                section_pointer="#/groups/1",
                membership="descendants",
                projection_digest="d" * 64,
                recipe_digest="e" * 64,
            ),
            text="Alpha body\ncell",
            context=lambda context=context: context,
        )
        frame = replace(
            native_source_frame(view, ()),
            context_sources=(native_frame_source(native_source_frame(parent_view, ())),),
        )
        result[key] = {
            "frame": asdict(frame),
            "packet_hash": "control-packet",
            "source_case": key,
            "topic": author.TOPICS[key],
        }
    return result


def projection_controls(root: Path) -> dict:
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.proposals import native_evidence_entries, native_frame_from_dict

    root.mkdir()
    sources = controlled_sources()
    projected = author.source_prompt_sources(sources)
    for key, item in projected.items():
        frame = native_frame_from_dict(sources[key]["frame"])
        source = item["source"]
        context = json.loads(frame.native_context)
        assert source["text"] == "Alpha body\ncell" == frame.text
        assert source["context"] == {
            name: context[name] for name in ("items", "pieces", "ancestors", "health")
        }
        expected = native_evidence_entries(frame)
        assert len(source["native_evidence"]) == 2
        for actual, entry in zip(source["native_evidence"], expected, strict=True):
            assert actual == entry
            assert actual["text"] == ("Alpha body", "cell")[expected.index(entry)]
            assert source["text"][actual["start"] : actual["end"]] == entry["text"]
        assert source["native_evidence"][1]["cell_index"] == 0
        assert source["native_evidence"][1]["source_field"] == "cell_text"
        assert source["native_evidence"][0]["occurrences"] == [
            {
                "occurrence_id": f"{key}-text",
                "precision": "character",
                "address_space": "native_item",
            }
        ]
        parent = item["context_sources"][0]
        assert parent["text"] == "Parent context"
        assert parent["native_evidence"][0]["text"] == "Parent context"
        assert (
            parent["native_evidence"][0]["handle"]
            == f"native_context:{20 + list(projected).index(key)}:native_evidence:0"
        )
        assert (
            parent["native_evidence"][0]["locator"]
            == native_evidence_entries(frame.context_sources[0])[0]["locator"]
        )
        assert "integrated_context_json" in json.loads(sources[key]["frame"]["native_context"])
        assert "OMIT-RECONCILIATION-GRAPH" not in canonical_bytes(item).decode()
    # The provider projection never replaces the local admission frame. This is a
    # wiring control; rich semantic acceptance remains the real validator's owner.
    observed = []

    def located(release, batch, frame, *, known_classes):
        assert "OMIT-RECONCILIATION-GRAPH" in frame.native_context
        assert asdict(frame) == sources[batch["source_case"]]["frame"]
        observed.append(frame.unit_ref)
        return SimpleNamespace(clean=True)

    value = {
        "units": [
            {
                "source_case": key,
                "authored_batch": {
                    "source_case": key,
                    "claims": [{"id": "claim", "object": {"expression": "controlled"}}],
                },
            }
            for key in sources
        ],
        "assertions": [
            {"id": identity, "latex": "controlled", "claim_ids": ["claim"]}
            for topic in author.TOPICS.values()
            for identity in topic["cases"]
        ],
    }
    with patch.object(author, "locate_proposal", located):
        author.validate_pass(None, sources, value, root, "CONTROL")
    assert set(observed) == {"sampling-full", "normal-full"}
    changed = json.loads(canonical_bytes(projected))
    changed["sampling"]["source"]["text"] = "omitted body"
    (root / "provider-sources.json").write_bytes(canonical_bytes(changed))

    def must_not_start(*args, **kwargs):
        raise AssertionError("tampered source projection started a provider")

    with patch.object(author, "provider_pass", must_not_start):
        try:
            author.authored_passes(
                None,
                sources,
                {},
                root,
                model="CONTROL-NOT-A-PROVIDER",
                timeout=1,
                max_output_tokens=100,
            )
        except ValueError as error:
            assert "differs from its canonical native frames" in str(error)
        else:
            raise AssertionError("tampered prepared source projection was accepted")
    return {
        "outcome": "passed",
        "scope": "complete projected content/evidence, canonical admission-frame wiring and pre-provider tamper refusal; not rich semantic validity",
    }


def control(root: Path, executable: Path, mode: str) -> dict:
    root.mkdir()
    (root / "domain-definitions.json").write_text("[]")
    (root / "annotation-guideline.txt").write_text("complete controlled annotation guideline")
    sources = controlled_sources()
    (root / "provider-sources.json").write_bytes(
        author.canonical_bytes(author.source_prompt_sources(sources))
    )
    for key in ("sampling", "normal"):
        (root / f"source-{key}.png").write_bytes(PNG)
    schema = {
        "type": "object",
        "required": ["author", "complete_batches"],
        "properties": {
            "author": {"type": "string"},
            "complete_batches": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    }

    def admitted(release, sources, value, directory, kind):
        assert threading.current_thread() is threading.main_thread()
        assert value == {"author": kind, "complete_batches": ["sampling-full", "normal-full"]}
        if mode == "interruption" and kind == "A":
            raise KeyboardInterrupt("controlled main-thread interruption")
        (directory / f"{kind}.validated").write_text("control admission only")

    failure = None
    result = {}
    barrier = threading.Barrier(2)
    provider_pass = author.provider_pass

    def controlled_pass(*args, **kwargs):
        try:
            return provider_pass(*args, **kwargs)
        except RuntimeError:
            if mode == "both_refusals":
                # Both refusals have been read before either future is released.
                barrier.wait(timeout=5)
            raise

    with (
        patch.object(author.shutil, "which", return_value=str(executable)),
        patch.object(author, "validate_pass", admitted),
        patch.object(author, "provider_pass", controlled_pass),
        patch.object(author, "PROVIDER_POLL_SECONDS", 0.02),
        patch.object(author, "PROVIDER_CLEANUP_SECONDS", 0.2),
        patch.dict(
            os.environ,
            {
                "AUTHOR_CONTROL_ROOT": str(root),
                "AUTHOR_CONTROL_MODE": mode,
                "CORPUS_DATABASE__URL": "must-not-forward",
            },
        ),
    ):
        try:
            result = author.authored_passes(
                None,
                sources,
                schema,
                root,
                model="CONTROL-NOT-A-PROVIDER",
                timeout=1 if mode == "timeout" else 1800,
                max_output_tokens=100,
            )
        except BaseException as error:
            failure = error
    children = {path.stem: json.loads(path.read_bytes()) for path in root.glob("*.started")}
    assert {"A", "B"} <= children.keys()
    assert children["A"]["cwd"] != children["B"]["cwd"]
    assert len({value["session"] for value in children.values()}) == len(children)
    for value in children.values():
        try:
            os.kill(value["pid"], 0)
        except ProcessLookupError:
            pass
        else:
            raise AssertionError("controlled provider child survived cleanup")
    if mode == "success":
        assert failure is None, repr(failure)
        assert set(result) == {"A", "B", "C"}
        assert set(children) == {"A", "B", "C"}
        for kind in children:
            assert (root / f"{kind}.input.jsonl").exists()
            assert (root / f"{kind}.stdout.jsonl").exists()
            assert (root / f"{kind}.structured.json").exists()
            invocation = json.loads((root / f"{kind}.invocation.json").read_bytes())
            assert invocation["independent_prior_passes"] == (["A", "B"] if kind == "C" else [])
            assert invocation["input_format"] == invocation["output_format"] == "stream-json"
            assert invocation["verbose"] is True
            assert (
                invocation["prompt_digest"]
                == sha256((root / f"{kind}.input.jsonl").read_bytes()).hexdigest()
            )
    else:
        assert failure is not None
        expected = {
            "failure": RuntimeError,
            "both_refusals": RuntimeError,
            "interruption": KeyboardInterrupt,
            "timeout": author.subprocess.TimeoutExpired,
        }[mode]
        assert isinstance(failure, expected), repr(failure)
        assert "C" not in children and not (root / "C.invocation.json").exists()
        custody = json.loads((root / "independent-authors-interrupted.json").read_bytes())
        assert not custody["pending_cleanup"] and not custody["cleanup_failures"]
        if mode == "both_refusals":
            assert set(custody["pass_settlements"]) == {"A", "B"}
            assert all(
                row["state"] == "failed" and row["error_type"] == "RuntimeError"
                for row in custody["pass_settlements"].values()
            )
            for kind in ("A", "B"):
                raw = (root / f"{kind}.stdout.jsonl").read_bytes()
                assert b"controlled-provider-refusal" in raw
        else:
            assert b"controlled partial B" in (root / "B.interrupted.stdout.jsonl").read_bytes()
        if mode == "failure":
            assert b"controlled-provider-refusal" in (root / "A.stdout.jsonl").read_bytes()
    return {
        "mode": mode,
        "outcome": "passed",
        "children": children,
        "expected_error": type(failure).__name__ if failure else None,
    }


def protocol_controls(root: Path) -> list[dict]:
    root.mkdir()
    expected = {"complete_batches": ["sampling-full", "normal-full"]}
    result = {
        "type": "result",
        "subtype": "success",
        "session_id": "control-session",
        "is_error": False,
        "stop_reason": "end_turn",
        "structured_output": expected,
    }
    init = {"type": "system", "subtype": "init", "session_id": "control-session"}
    bait = {"type": "assistant", "structured_output": {"must_not_be_admitted": True}}
    cases = {
        "success": ([init, bait, result], 0, True),
        "null_stop_reason": ([{**result, "stop_reason": None}], 0, True),
        "structured_tool_use": ([{**result, "stop_reason": "tool_use"}], 0, True),
        "stop_sequence": ([{**result, "stop_reason": "stop_sequence"}], 0, True),
        "unknown_stop_reason": ([{**result, "stop_reason": "unrecognized"}], 0, False),
        "missing_result": ([init, bait], 0, False),
        "duplicate_result": ([init, result, result], 0, False),
        "nonterminal_result": ([result, init], 0, False),
        "wrong_session": ([{**result, "session_id": "another-session"}], 0, False),
        "refusal": ([{**result, "stop_reason": "refusal"}], 0, False),
        "max_tokens": ([{**result, "stop_reason": "max_tokens"}], 0, False),
        "context_exceeded": (
            [{**result, "stop_reason": "model_context_window_exceeded"}],
            0,
            False,
        ),
        "pause_turn": ([{**result, "stop_reason": "pause_turn"}], 0, False),
        "error_flag": ([{**result, "is_error": True}], 0, False),
        "unknown_error_flag": ([{k: v for k, v in result.items() if k != "is_error"}], 0, False),
        "error_subtype": ([{**result, "subtype": "error_max_turns"}], 0, False),
        "missing_structured": (
            [{k: v for k, v in result.items() if k != "structured_output"}],
            0,
            False,
        ),
        "nonzero_exit": ([result], 1, False),
        "nonobject_event": ([[], result], 0, False),
    }
    raw_cases = {
        name: (b"".join(json.dumps(event).encode() + b"\n" for event in events), code, admitted)
        for name, (events, code, admitted) in cases.items()
    }
    raw_cases["malformed_json"] = (b'{"type":"result"\n', 0, False)
    checks = []
    for name, (raw, returncode, admitted) in raw_cases.items():
        (root / f"{name}.stdout.jsonl").write_bytes(raw)
        try:
            actual = author.provider_result(
                raw, session="control-session", returncode=returncode, kind="CONTROL"
            )
        except RuntimeError as error:
            assert not admitted, repr(error)
            checks.append({"case": name, "outcome": "passed", "refusal": str(error)})
        else:
            assert admitted, f"invalid protocol admitted: {name}"
            assert actual == expected
            checks.append({"case": name, "outcome": "passed", "admitted": True})
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    executable = root / "controlled-provider.py"
    executable.write_text(f"#!{sys.executable}\n" + CHILD)
    executable.chmod(0o700)
    controls = [
        control(root / mode, executable, mode)
        for mode in ("success", "failure", "both_refusals", "interruption", "timeout")
    ]
    receipt = {
        "verified_at": datetime.now(UTC).isoformat(),
        "outcome": "passed",
        "scope": (
            "controlled subprocess concurrency/custody/cleanup only; "
            "no actual provider, database, source reference or performance qualification"
        ),
        "controls": controls,
        "projection_controls": projection_controls(root / "projection"),
        "protocol_controls": protocol_controls(root / "protocol"),
    }
    (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
