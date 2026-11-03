"""Read-only integrity/sample check of the detached inventory, without database access."""

from __future__ import annotations

import gzip
import json
import random
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def main():
    manifest = json.loads((HERE / "manifest.json").read_bytes())
    for name, expected in manifest["artifacts"].items():
        raw = (HERE / name).read_bytes()
        assert len(raw) == expected["bytes"]
        assert sha256(raw).hexdigest() == expected["sha256"]
    sources = json.loads(gzip.decompress((HERE / "sources.json.gz").read_bytes()))
    by_id = {source["pin"]["id"]: source for source in sources}
    regions = [json.loads(line) for line in (HERE / "regions.jsonl").read_bytes().splitlines()]
    for region in regions:
        source = by_id[region["source_view_id"]]
        piece = region["piece"]
        assert source["text"][piece["start"] : piece["end"]] == region["text"]
        assert sha256(region["text"].encode()).hexdigest() == region["text_sha256"]
    for view in manifest["views"]:
        assert sha256(encoded(by_id[view["pin"]["id"]])).hexdigest() == view["source_sha256"]
    sample = json.loads((HERE / "sample.json").read_bytes())
    assert len(regions) == sample["population_size"] == manifest["total_regions"]
    assert [row["id"] for row in random.Random(sample["seed"]).sample(regions, sample["sample_size"])] == sample["random_region_ids"]
    paragraph = json.loads((HERE / "cpu-source-paragraph.json").read_bytes())
    source = by_id[paragraph["pin"]["id"]]
    assert paragraph["pin"] == source["pin"]
    assert paragraph["source_snapshot_sha256"] == sha256(encoded(source)).hexdigest()
    assert paragraph["text"] == source["text"][paragraph["start"] : paragraph["end"]]
    print(json.dumps(dict(outcome="passed", scope="detached digests, exact projection reconstruction and deterministic sample only", views=len(sources), regions=len(regions), sample=len(sample["random_region_ids"])), sort_keys=True))


if __name__ == "__main__":
    main()
