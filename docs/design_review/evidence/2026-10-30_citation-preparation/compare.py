"""Bounded, complete frame-construction/citation comparison, not corpus throughput."""
from __future__ import annotations

import dataclasses
import json
import statistics
import subprocess
import sys
import time
import types

from corpus_structure.methods.llm import cascade as current

BASELINE = "ea2d306"
PATH = "python/corpus-structure/src/corpus_structure/methods/llm/cascade.py"


def main() -> None:
    baseline = types.ModuleType("baseline_cascade")
    sys.modules[baseline.__name__] = baseline
    source = subprocess.check_output(["git", "show", f"{BASELINE}:{PATH}"], text=True)
    exec(compile(source, "<baseline-cascade>", "exec"), baseline.__dict__)
    sentence = "The distribution has location mu and positive scale sigma. "
    workloads = []
    for size, count, anchors in ((1, 1, 1), (80, 400, 8)):
        text = sentence * size
        rows = [(f"a{i}", i * len(sentence), (i + 1) * len(sentence) - 1) for i in range(size)]
        queries = [
            ("distribution has mu and positive scale sigma", f"a{i % anchors}")
            for i in range(count)
        ]
        outputs = []
        timings = {}
        for label, module in (("baseline", baseline), ("prepared", current)):
            elapsed = []
            for _ in range(3):
                started = time.perf_counter()
                cascade = module.Cascade(text, [module.FrameSentence(*row) for row in rows])
                located = [cascade.locate(*query) for query in queries]
                elapsed.append(time.perf_counter() - started)
            outputs.append([
                {key: value for key, value in dataclasses.asdict(row).items() if key != "ms"}
                for row in located
            ])
            timings[label] = {"median_seconds": statistics.median(elapsed), "runs": elapsed}
        assert outputs[0] == outputs[1], "source coordinates/outcomes differ"
        workloads.append({
            "sentences": size,
            "citations": count,
            "distinct_cited_anchors": anchors,
            "parity_excluding_ms": True,
            "timings": timings,
        })
    print(json.dumps({
        "baseline": BASELINE,
        "python": sys.version,
        "boundary": "frame construction and all locate calls; imports excluded; fresh frame each run",
        "repetitions": 3,
        "workloads": workloads,
    }, indent=2))


if __name__ == "__main__":
    main()
