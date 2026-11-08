"""Run the standalone Standard method while the dedicated Nemotron service is resident."""

from __future__ import annotations

import argparse
from pathlib import Path

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.orchestrate.commands import start_bound_run
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release")
    parser.add_argument("domains", type=Path)
    args = parser.parse_args()
    settings = Settings()
    with open_runtime_engine(settings, application_name="chandra-standard-handoff", purpose="write") as engine:
        result = start_bound_run(
            engine,
            release_id=args.release,
            realization_id="source:chandra-standard-handoff",
            project_id="chandra-standard-handoff",
            domain="statistics",
            method_settings=MethodSettings(
                data_dir=settings.paths.data_dir,
                model_cache=settings.paths.model_cache,
                nemotron_endpoint=settings.nemotron.endpoint,
            ),
            domains=args.domains,
            graph=Graph(((Stage.INGEST, (Step("ingest.pdf/default"),)),), policy_propose=False),
            source_only=True,
        )
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
