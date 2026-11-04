"""Exercise actual owned source execution with one changed downstream resolver configuration."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

import yaml
from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate.m1 import registry, source_graph
from corpus_structure.orchestrate.registry import MethodRegistry
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, seal_cut
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main():
    folder = Path(__file__).parent / "downstream-subset-001"
    folder.mkdir(exist_ok=False)
    settings = Settings()
    with open_runtime_engine(settings, "m1-actual-reuse", purpose="write") as engine:
        with engine.connect() as conn:
            runs = table("ops.run")
            original = dict(conn.execute(select(runs).where(runs.c.id == 14)).mappings().one())
            prepared = open_release(conn, original["release_id"])
        dependencies = json.loads(original["dependencies"])
        base = registry(Path("domains/statistics"))
        configs = {name: {"readings" if name == "extract.m1_candidates" else "default":
                          dict(row["parameters"])} for name, row in dependencies["operations"].items()}
        before = configs["resolve.m1_readings"]["default"]["subset"]
        configs["resolve.m1_readings"]["default"]["subset"] = "statistics-m1-reuse-control-1"
        bound = MethodRegistry(base.methods(), replace(base.file, configs=configs), base.sources,
                               prepared=prepared)
        configuration_source = yaml.safe_dump(dict(version=base.file.version, configs=configs,
                                                   **base.file.sections), sort_keys=True)
        with (folder / "declared-input.json").open("xb") as output:
            output.write(canonical_bytes(dict(original_run=14, release_id=prepared.release_id,
                old_subset=before, new_subset="statistics-m1-reuse-control-1", configs=configs,
                fitted_instance="not_supplied", purpose="actual downstream-only configuration reuse")))
        report = run_source_methods(engine, project_id=original["project_id"], prepared=prepared,
            binding=OperationBinding(original["release_id"], original["input_realization_id"],
                original["input_revision"], canonical_bytes(dependencies["parent"])),
            registry=bound, graph=source_graph("readings"),
            method_settings=MethodSettings(data_dir=settings.paths.data_dir,
                                          model_cache=settings.paths.model_cache),
            guideline=dependencies["guideline"], corpus_record=dependencies["corpus"],
            scope_record=dependencies["scope"], policy_source=dependencies["policy"],
            extraction_policy="m1-candidate", extraction_policy_config=configuration_source,
            configurations={"extract.m1_candidates": "readings"})
        with (folder / "source-ready.json").open("xb") as output:
            output.write(canonical_bytes(report.model_dump(mode="json")))
        with engine.begin() as conn:
            cut = seal_cut(conn, report.run_id, "actual-reuse-final", final=True)
        result = consolidate_cut(engine, cut, "m1-reuse-result:" + str(report.run_id))
        with (folder / "completed.json").open("xb") as output:
            output.write(canonical_bytes(asdict(result)))
        print(json.dumps(dict(outcome="passed", report=report.model_dump(mode="json"),
                              publication=asdict(result))), flush=True)


if __name__ == "__main__":
    main()
