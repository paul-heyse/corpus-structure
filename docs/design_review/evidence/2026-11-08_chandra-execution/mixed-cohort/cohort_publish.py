"""Register the exact mixed-cohort sources and run their incumbent-only graph."""

import argparse
import json
from hashlib import sha256
from pathlib import Path
from shutil import copy2

import yaml

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.orchestrate.commands import start_bound_run
from corpus_structure.orchestrate.project import init_bound_project
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

_PROJECT = "chandra-mixed-cohort"
_REALIZATION = "source:chandra-mixed-cohort"
_METHOD = "ingest.pdf_integrated"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release")
    parser.add_argument("domains", type=Path)
    parser.add_argument("--realization", default=_REALIZATION)
    parser.add_argument("--register-only", action="store_true")
    args = parser.parse_args()

    evidence = Path(__file__).resolve().parent
    corpus = evidence / "inputs"
    manifest = json.loads((evidence / "cohort.json").read_bytes())
    expected = {Path(row["input"]).name: row["input_sha256"] for row in manifest["inputs"]}
    actual = {source.name: sha256(source.read_bytes()).hexdigest() for source in corpus.glob("*.pdf")}
    if actual != expected:
        raise ValueError("cohort PDF bytes differ from the frozen inventory")

    pack = args.domains / "statistics"
    pack.mkdir(parents=True, exist_ok=True)
    native_pack = DOMAINS / "statistics"
    config = yaml.safe_load((native_pack / "methods.yaml").read_text())
    for method in ("ingest.pdf", _METHOD):
        config["configs"][method]["default"]["originals"] = sorted(expected)
    (pack / "methods.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    copy2(native_pack / "guideline.md", pack / "guideline.md")

    settings = Settings()
    with open_runtime_engine(settings, application_name=_PROJECT, purpose="write") as engine:
        if args.register_only:
            with engine.begin() as conn:
                result = init_bound_project(
                    conn,
                    domain="statistics",
                    corpus=corpus,
                    release_id=args.release,
                    realization_id=args.realization,
                    name=_PROJECT,
                    domains=args.domains,
                )
        else:
            result = start_bound_run(
                engine,
                release_id=args.release,
                realization_id=args.realization,
                project_id=_PROJECT,
                domain="statistics",
                method_settings=MethodSettings(
                    data_dir=settings.paths.data_dir,
                    model_cache=settings.paths.model_cache,
                    nemotron_endpoint=settings.nemotron.endpoint,
                    nemotron_python=settings.nemotron.python,
                    nemotron_worker=settings.nemotron.worker,
                    nemotron_receipts=settings.nemotron.receipts,
                    nemotron_timeout_seconds=settings.nemotron.timeout_seconds,
                ),
                domains=args.domains,
                graph=Graph(((Stage.INGEST, (Step(_METHOD + "/default"),)),), policy_propose=False),
                source_only=True,
            )
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
