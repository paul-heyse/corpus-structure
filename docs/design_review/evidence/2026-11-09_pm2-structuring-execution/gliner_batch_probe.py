"""Compare bounded batch and singleton execution on the same retained source windows."""

import json
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import yaml

from corpus_structure.methods.definition_applicability import DefinitionComponentsConfig
from corpus_structure.methods.gliner import GlinerInput, GlinerProfile, GlinerRefused
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.model_observation import installed_policy, released_pack
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralInput

HERE = Path(__file__).resolve().parent


def main():
    previous = json.loads((HERE / "raw/packed-gliner.json").read_bytes())
    inputs = StructuralInput.model_validate_json(
        (HERE.parent / "2026-11-09_pm2-adoption/raw/target-inputs.json").read_bytes()
    )
    profile_values = yaml.safe_load(
        (HERE.parents[3] / "domains/statistics/m1-methods.yaml").read_bytes()
    )["configs"]["extract.m1_candidates"]["default"]
    profile = GlinerProfile(
        snapshot=Path(profile_values["snapshot"]),
        checkpoint=profile_values["checkpoint"],
        revision=profile_values["revision"],
        artifact_hashes=tuple(map(tuple, profile_values["artifact_hashes"])),
    )
    # The same bare retained diagnostic schema, authenticated by its recorded fingerprint.
    config = DefinitionComponentsConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        target_ids=tuple(p.passage_id for p in inputs.passages),
        profile={
            key: profile_values[key]
            for key in ("snapshot", "checkpoint", "revision", "artifact_hashes")
        },
    )
    policy, _ = installed_policy()
    pack = released_pack(previous["release"], policy, config=config.model_dump())
    if pack.fingerprint != previous["pack"] or profile.fingerprint != previous["profile"]:
        raise RuntimeError("cannot reproduce the exact retained diagnostic pack and profile")
    items = tuple(GlinerInput(p.identity, p.identity, p.text) for p in inputs.passages)
    report = {"profile": profile.fingerprint, "pack": pack.fingerprint, "passes": []}
    with closing(GlinerWorker(profile)) as worker:
        worker.extract(pack, items[:1])
        for _ in range(2):
            started = perf_counter()
            single = tuple(worker.extract(pack, (item,))[0] for item in items)
            single_elapsed = perf_counter() - started
            started = perf_counter()
            batch = worker.extract(pack, items[:4]) + worker.extract(pack, items[4:])
            batch_elapsed = perf_counter() - started
            report["passes"].append(
                {
                    "singleton_seconds": single_elapsed,
                    "batch_seconds": batch_elapsed,
                    "exact_order": [r.context_digest for r in single]
                    == [r.context_digest for r in batch],
                    "exact_native_output": [
                        canonical_bytes(a.raw) == canonical_bytes(b.raw)
                        for a, b in zip(single, batch, strict=True)
                    ],
                }
            )
        try:
            worker.extract(pack, items[:4] + (replace(items[4], context_id="over-budget"),))
        except GlinerRefused as exc:
            report["oversized_refusal"] = str(exc)
        else:
            raise AssertionError("oversized batch was admitted")
        report["healthy_after_refusal"] = (
            worker.extract(pack, items[:1])[0].raw == single[0].raw
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
