"""Prove the production constructor correction changes only configuration binding."""

from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def without_tracebacks(value):
    if isinstance(value, dict):
        return {key: without_tracebacks(item) for key, item in value.items() if key != "traceback"}
    if isinstance(value, list):
        return [without_tracebacks(item) for item in value]
    return value


def main():
    old, new = HERE / "attempt-003", HERE / "attempt-004"
    names = ("feature-fit-protected.json", "source-contexts.jsonl", "source-reconstruction.jsonl",
        "native-preparation.jsonl", "source-only-request-inventory.jsonl", "native-collation.jsonl",
        "mapping-attempts.jsonl", "training-targets.jsonl",
        "training-target-origins.jsonl", "reload-collation.jsonl", "summary.json")
    equal = []
    for name in names:
        before, after = (old / name).read_bytes(), (new / name).read_bytes()
        assert before == after, name
        equal.append(dict(file=name, bytes=len(after), sha256=sha256(after).hexdigest(), byte_identical=True))
    diagnostics = []
    for name in ("request-audit.jsonl", "record-disposition.jsonl"):
        before, after = ((folder / name).read_bytes() for folder in (old, new))
        a_rows, b_rows = ([json.loads(line) for line in blob.splitlines()] for blob in (before, after))
        assert without_tracebacks(a_rows) == without_tracebacks(b_rows), name
        diagnostics.append(dict(file=name, equal_excluding_tracebacks=True,
            before_sha256=sha256(before).hexdigest(), after_sha256=sha256(after).hexdigest(),
            difference="executed constructor edit shifts traceback source-line locations; original diagnostics remain untouched"))
    a, b = (json.loads((folder / "contextual-configuration.json").read_text()) for folder in (old, new))
    assert json.dumps(a["params"]) == json.dumps(b["params"])
    changed = [key for key in a["profile"] if json.dumps(a["profile"][key]) != json.dumps(b["profile"][key])]
    assert changed == ["timeout_seconds"]
    assert type(a["profile"]["timeout_seconds"]) is int and type(b["profile"]["timeout_seconds"]) is float
    assert a["params"] == b["params"]
    assert b["constructor"] == "MethodRegistry.config('extract.m1_candidates','contextual').config"
    summary = dict(outcome="passed", previous="attempt-003", corrected="attempt-004", identical_payloads=equal,
        diagnostic_provenance=diagnostics,
        serialized_params_identical=True, changed_profile_spellings=changed,
        before_timeout=dict(value=a["profile"]["timeout_seconds"], type="int"),
        after_timeout=dict(value=b["profile"]["timeout_seconds"], type="float"),
        previous_profile=a["profile_fingerprint"], corrected_profile=b["profile_fingerprint"],
        corrected_constructor=b["constructor"],
        note="Source text, schemas, native specs/conditioning and all targets are byte-identical. Config/profile/launch binding reflects the actual production constructor; no model executed or profile check weakened.")
    with (HERE / "constructor-difference-proof-004.json").open("x") as stream:
        json.dump(summary, stream, indent=2)
        stream.write("\n")
    (HERE / "compare_constructor-executed-004.py.txt").write_bytes(Path(__file__).read_bytes())
    print(json.dumps({key: value for key, value in summary.items() if key != "identical_payloads"}))


if __name__ == "__main__":
    main()
