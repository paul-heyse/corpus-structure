"""Publish and adopt a bounded real Standard PDF under a qualified development release."""

import argparse
import json
from pathlib import Path

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.orchestrate.commands import start_bound_run
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release")
    parser.add_argument("domains", type=Path)
    parser.add_argument("--native-pin", type=Path)
    args = parser.parse_args()
    settings = Settings()
    native = (
        ProductReference(**json.loads(args.native_pin.read_bytes())) if args.native_pin else None
    )
    with open_runtime_engine(
        settings, application_name="chandra-standard-control", purpose="write"
    ) as engine:
        result = start_bound_run(
            engine,
            release_id=args.release,
            realization_id="source:chandra-standard-control",
            project_id="chandra-standard-control",
            domain="statistics",
            method_settings=MethodSettings(
                data_dir=settings.paths.data_dir, model_cache=settings.paths.model_cache
            ),
            domains=args.domains,
            graph=Graph(((Stage.INGEST, (Step("ingest.pdf/default"),)),), policy_propose=False),
            native_product=native,
            source_only=True,
        )
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
