"""Run the frozen Dipo book and operations cases through the isolated CPU worker."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from corpus_structure.methods.pm2_worker import open_pm2_worker


def main() -> None:
    evidence = Path(__file__).parent
    cases = [
        case
        for panel in ("reference-book.json", "reference-operations.json")
        for case in json.loads((evidence / "raw" / panel).read_text())["cases"]
        if "PM2-05" in case["packages"]
    ]
    with TemporaryDirectory(prefix="pm2-dipo-panel-") as directory:
        profile = Path(directory) / "profile.json"
        profile.write_text(
            json.dumps({"provider": "dipo", "device": "cpu", "assets": "build/models/pm2"})
        )
        with open_pm2_worker(
            python=Path("services/pm2-dipo/.venv/bin/python"),
            script=Path("python/corpus-structure/src/corpus_structure/methods/pm2_native.py"),
            profile=profile,
            device="cpu",
        ) as worker:
            print(json.dumps({"startup": worker.startup}), flush=True)
            for case in cases:
                source = case["text"]
                source_hash = hashlib.sha256(source.encode()).hexdigest()
                if source_hash != case["text_sha256"]:
                    raise ValueError(f"frozen source digest differs for {case['id']}")
                scope = case.get("range", [0, len(source)])
                reviewed = (
                    sorted(case["spans"].values(), key=lambda edu: edu["range"])
                    if "spans" in case
                    else case["expected"].get("reviewed_edus")
                )
                modes = ("learned", "layout_forced", "supplied_edus") if reviewed else ("learned",)
                for mode in modes:
                    request = {"text": source, "mode": mode}
                    if mode == "supplied_edus":
                        origin = scope[0]
                        request["edu_ranges"] = [
                            [start - origin, end - origin]
                            for start, end in (edu["range"] for edu in reviewed)
                        ]
                    print(
                        json.dumps(
                            {
                                "case": case["id"],
                                "source_sha256": source_hash,
                                "scope": scope,
                                "mode": mode,
                                "reply": worker.infer(request),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )


if __name__ == "__main__":
    main()
