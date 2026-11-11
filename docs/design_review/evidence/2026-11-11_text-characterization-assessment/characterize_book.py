"""Execute the existing enrichment boundary over the finalized authentic capture.

This is the dated qualification invocation, not a replacement workflow or reference author.
The installed ingest CLI uses this same boundary immediately after a new capture; here the
source-first panel has already frozen against the existing completed capture.
"""

from dataclasses import asdict
import json
from pathlib import Path
from types import SimpleNamespace

from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate.characterization import characterize_captured_run
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main():
    settings = Settings()
    with open_runtime_engine(settings, purpose="write") as engine:
        results = characterize_captured_run(
            engine,
            SimpleNamespace(run_id=496),
            project_id="nce-grinstead-snell-full-book",
            release_id="release:c9939039081ddcfbc382e9dc323e12e31f9b3683fb479c773ea3fd72ac6a6189",
            realization_id="source:nce-grinstead-snell-full-book:release:c9939039081ddcfbc382e9dc323e12e31f9b3683fb479c773ea3fd72ac6a6189",
            domain="statistics",
            method_settings=MethodSettings(
                data_dir=settings.paths.data_dir,
                model_cache=settings.paths.model_cache,
            ),
            method_options={},
            on_created=lambda event: print(
                json.dumps({"created": asdict(event)}), flush=True
            ),
        )
    encoded = json.dumps([asdict(result) for result in results], indent=2) + "\n"
    Path(__file__).with_name("book-result.json").write_text(encoded)
    print(encoded, flush=True)


if __name__ == "__main__":
    main()
