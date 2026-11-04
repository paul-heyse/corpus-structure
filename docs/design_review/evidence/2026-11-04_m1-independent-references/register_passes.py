"""Register exact independent author bytes through existing protected reference operations."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from corpus_structure.evaluate.record_references import decode_frame, record_pass
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--author", type=Path, required=True)
    parser.add_argument("--kind", choices=("A", "B", "C"), required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--filename-prefix", default="unit-")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    frozen = json.loads((args.freeze / "manifest.json").read_bytes())
    units = [(entry, unit) for entry in frozen["sets"] for unit in entry["units"]]
    expected = {f"{args.filename_prefix}{unit['unit_id']}.json" for _, unit in units}
    actual = {path.name for path in args.author.glob(args.filename_prefix + "*.json")}
    if actual != expected:
        raise ValueError(f"authored unit census differs: missing={expected-actual}, extra={actual-expected}")
    args.out.mkdir(parents=True, exist_ok=False)
    completed = []
    try:
        with open_runtime_engine(Settings(), "m1-independent-reference-register", purpose="evaluate") as engine:
            for entry, unit in units:
                packet = json.loads((args.freeze / entry["directory"] / unit["path"]).read_bytes())
                frame = decode_frame(packet["source_frame"])
                content = (args.author / f"{args.filename_prefix}{unit['unit_id']}.json").read_bytes()
                # No mutation, normalization, relabeling or reference relocation.
                with engine.begin() as conn:
                    identity = record_pass(conn, unit_id=unit["unit_id"], pass_kind=args.kind,
                                           actor=args.actor, authored=content, frame=frame)
                receipt = dict(unit_id=unit["unit_id"], pass_id=identity, kind=args.kind,
                               actor=args.actor, authored_sha256=sha256(content).hexdigest(),
                               frozen_packet_sha256=unit["sha256"], bytes=len(content))
                with (args.out / f"unit-{unit['unit_id']}.json").open("xb") as output:
                    output.write(canonical_bytes(receipt))
                completed.append(receipt)
                print(json.dumps(receipt), flush=True)
        with (args.out / "manifest.json").open("xb") as output:
            output.write(canonical_bytes(dict(outcome="passed", kind=args.kind, actor=args.actor,
                                              release_id=frozen["release_id"], units=completed,
                                              quality_claim="not_established")))
    except BaseException as error:
        with (args.out / "failure.json").open("xb") as output:
            output.write(canonical_bytes(dict(outcome="failed", error_type=type(error).__name__,
                                              error=str(error), completed_committed_units=completed)))
        raise


if __name__ == "__main__":
    main()
