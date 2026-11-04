"""Check frozen v2 native distinct-fragment and latent target receipts only."""

from collections import Counter
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    out = HERE / sys.argv[1]
    data = rows(out / "training-targets.jsonl")
    origins = rows(out / "training-target-origins.jsonl")
    native = {row["request"]: row for row in rows(out / "native-collation.jsonl")}
    refs = json.loads((out / "feature-fit-protected.json").read_text())
    gold = {r["record_id"]: r for u in refs for r in u["authored"]["records"]}
    definitions, assertions, custody = {}, set(), {True: set(), False: set()}
    counts = Counter()
    for example, origin in zip(data, origins, strict=True):
        receipt = native[origin["request"]]
        spec = receipt["record_specs"][0]["0"]
        native_records = receipt["samples"][0]["native_records"]
        assert len(native_records) == len(example["output"]["target_records"]) == len(origin["origins"])
        for alias in origin["all_alias_origins"]:
            for row in alias["origins"]:
                custody[row["structural_custody"]["request_primary_assembly_eligible"]].add(row["record_id"])
        family = example["output"]["family"]
        if family == "assertion":
            assert spec["mode"] == "latent" and spec["anchor_query_id"] is None
            assertions.update(row["record_id"] for row in origin["origins"])
            counts["latent_assertion_examples"] += 1
        if family != "definition":
            continue
        field = next(field for field in spec["fields"] if field["name"] == "defining_text")
        assert field["cardinality"] == "zero_or_more"
        prefix = receipt["samples"][0]["prefix_length"]
        for target, original, actual in zip(example["output"]["target_records"], origin["origins"], native_records, strict=True):
            identity = original["record_id"]
            expected = original["mappings"]["defining_text"]
            anchors = {a["anchor_id"]: a for a in gold[identity]["anchors"]}
            literal_sets = [s for s in gold[identity]["evidence_sets"] if s["role"] == "defining_text" and s["usage"] == "literal"]
            expected_ids = [key for group in literal_sets for key in group["anchors"]]
            assert [f["anchor_id"] for f in expected["fragments"]] == expected_ids
            values = next(f["values"] for f in actual["fields"] if f["query_id"] == field["query_id"])
            assert len(values) == len(target["defining_text"]) == len(expected_ids)
            previous_end = -1
            for fragment, mapping, value, anchor_id in zip(target["defining_text"], expected["fragments"], values, expected_ids, strict=True):
                assert fragment["start"] >= previous_end
                assert example["input"][fragment["start"]:fragment["end"]] == fragment["text"] == anchors[anchor_id]["source_piece"]
                a, b = mapping["word_span"]
                assert value == [[a + prefix, b + prefix]]
                assert len(mapping["source_pieces"]) == 1
                source = mapping["source_pieces"][0]
                anchor = anchors[anchor_id]
                assert source[1:] == [anchor["pointer"], anchor["start"], anchor["end"], anchor["source_piece"]]
                previous_end = fragment["end"]
            definitions[identity] = dict(fragments=len(values), logical_kind=expected["kind"])
            counts["definition_fragment_instances"] += len(values)
    summary = dict(outcome="passed", distinct_definition_records=len(definitions), definitions=definitions,
        distinct_latent_assertion_records=len(assertions), counts=dict(counts),
        any_emitted_primary_custody=len(custody[True]),
        neighbor_only_records=sorted(custody[False] - custody[True]),
        original_records=len(gold),
        limits="Nested native target/source receipt integrity only; no model/decoder confidence, logical-field probability or assembled-reading qualification.")
    assert len(gold) == 270
    with (out / "frontend-audit.json").open("x") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    (out / "frontend_audit-executed.py.txt").write_bytes(Path(__file__).read_bytes())
    print(json.dumps({key: value for key, value in summary.items() if key != "definitions"}))


if __name__ == "__main__":
    main()
