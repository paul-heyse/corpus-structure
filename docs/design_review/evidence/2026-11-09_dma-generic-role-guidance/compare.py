"""Read-only same-source comparison of baseline and generic M1 role guidance."""

from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / "docs/design_review/evidence/2026-11-09_dma-producer-gap"
sys.path.insert(0, str(EVIDENCE))
import replay_candidate  # noqa: E402

RUN_ID, CUT_ID, SOURCE_VIEW_ID = 437, 537, 409
PROJECT = "nce-grinstead-snell-full-book"


class ArmRegistry:
    def __init__(self, delegate, *, guided: bool):
        self.delegate = delegate
        self.guided = guided
        self.binding: dict | None = None

    def bind_release(self, prepared):
        from corpus_structure.methods.m1_source import configured_pack_variants

        source = self

        class Bound:
            def __init__(self):
                self.delegate = source.delegate.bind_release(prepared)

            def resolve(self, method_name, configuration_name):
                resolved = self.delegate.resolve(method_name, configuration_name)
                if method_name != "extract.m1_candidates":
                    return resolved
                variants = configured_pack_variants(
                    prepared,
                    resolved.config,
                    generic_role_guidance=source.guided,
                )
                pack_fingerprints = {
                    family: [pack.fingerprint for _variant, _anchor, pack in family_variants]
                    for family, family_variants in variants.items()
                }
                diagnostic_arm = (
                    "generic-source-role-guidance-1" if source.guided else "baseline"
                )
                source.binding = {
                    "method": method_name,
                    "method_version": self.delegate.method(method_name).version,
                    "configuration": configuration_name,
                    "registered_config_key": resolved.config_hash,
                    "diagnostic_arm": diagnostic_arm,
                    "config_params": dict(resolved.params),
                    "pack_fingerprints": pack_fingerprints,
                    "diagnostic_request_id": sha256(
                        canonical_bytes(
                            {
                                "method": method_name,
                                "method_version": self.delegate.method(method_name).version,
                                "registered_config_key": resolved.config_hash,
                                "diagnostic_arm": diagnostic_arm,
                                "pack_fingerprints": pack_fingerprints,
                            }
                        )
                    ).hexdigest(),
                }
                return resolved

            def method(self, method_name):
                method = self.delegate.method(method_name)
                if source.guided and method_name == "extract.m1_candidates":
                    method.run = lambda units, config, ctx: method.run_generic_role_guidance_comparison(
                        units, config, ctx
                    )
                return method

        return Bound()


def run_arm(conn, *, guided: bool) -> dict:
    delegate = replay_candidate.registry(ROOT / "domains/statistics")
    arm = ArmRegistry(delegate, guided=guided)
    replay_candidate.registry = lambda _path: arm
    result = replay_candidate.compare(
        conn, RUN_ID, CUT_ID, SOURCE_VIEW_ID, "default"
    )
    if arm.binding is None:
        raise RuntimeError("M1 request binding was not captured")
    raw = result
    group_counts: dict[str, int] = {}
    for report in raw["reports"]:
        family = report["family"]
        group_counts[family] = group_counts.get(family, 0) + len(report["groups"])
    record_families = [row["family"] for row in raw["records"]]
    return {
        "binding": {
            key: arm.binding[key]
            for key in (
                "method",
                "method_version",
                "configuration",
                "registered_config_key",
                "diagnostic_arm",
                "pack_fingerprints",
                "diagnostic_request_id",
            )
        },
        "run": raw["run"],
        "cut": raw["cut"],
        "view": raw["view"],
        "release": raw["release"],
        "policy": raw["policy"],
        "source_binding": {
            "native_product": raw["source"]["native_product"],
            "projection_digest": raw["source"]["projection_digest"],
            "recipe_digest": raw["source"]["recipe_digest"],
            "version": raw["source"]["version"],
        },
        "outcome": raw["outcome"],
        "decoder_group_counts_by_family": dict(sorted(group_counts.items())),
        "assembled_private_record_count": len(record_families),
        "assembled_private_record_families": record_families,
        "assembled_private_record_role_names": [
            sorted(field["role"] for field in row["fields"])
            for row in raw["records"]
        ],
        "protected_reference_grade": "not_run",
    }


def main() -> None:
    with (
        open_runtime_engine(Settings(), "dma-generic-guidance-readonly", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        baseline = run_arm(conn, guided=False)
        guided = run_arm(conn, guided=True)
    print(json.dumps({"baseline": baseline, "guided": guided}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
