"""Freeze independent C inputs from protected A/B/source operations, without predictions."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from corpus_structure.evaluate.record_references import adjudication_packet
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--freeze", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
frozen = json.loads((args.freeze / "manifest.json").read_bytes())
args.out.mkdir(parents=True, exist_ok=False)
completed = []
with open_runtime_engine(Settings(), "m1-source-only-C-packets", purpose="evaluate") as engine:
    with engine.connect() as conn:
        for origin in frozen["sets"]:
            for unit in origin["units"]:
                packet = adjudication_packet(conn, unit["unit_id"])
                authors = []
                for author in packet["authors"]:
                    raw = author["authored"]
                    assert isinstance(raw, bytes)
                    literal = raw.decode("utf-8")
                    assert literal.encode("utf-8") == raw
                    assert sha256(raw).hexdigest() == author["content_digest"]
                    authors.append({key: value for key, value in author.items() if key != "authored"} |
                                   dict(authored_utf8=literal, authored_encoding="exact UTF-8 roundtrip"))
                packet["authors"] = authors
                name = f"unit-{unit['unit_id']}.json"
                with (args.out / name).open("xb") as output:
                    output.write(canonical_bytes(packet))
                completed.append(dict(unit_id=unit["unit_id"], path=name,
                                      adjudication_passes=packet["adjudication_passes"]))
with (args.out / "manifest.json").open("xb") as output:
    output.write(canonical_bytes(dict(outcome="passed", release_id=frozen["release_id"],
                                      units=completed, prediction_access="not_run")))
print("passed: source-only protected A/B disagreement packets for", len(completed), "units")
