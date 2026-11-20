"""Report the required facts at the current UDM generator and serving roots."""

import json
from dataclasses import asdict
from pathlib import Path

from corpus_structure.semantic.code_identity import capture_code_identity
from corpus_structure.semantic.external_runtime import acquire_codec_runtime
from corpus_structure.semantic.native_program_store import _analyze_generator_code


def main():
    workspace = Path(__file__).resolve().parents[4]
    package = workspace / "python/corpus-structure/src/corpus_structure"
    previous = Path(__file__).resolve().parent.parent / "2026-11-20_udm10-workload-custody" / "raw"
    capabilities = acquire_codec_runtime()
    identities = {"generator": _analyze_generator_code()}
    for name in ("native-demand", "rich", "contribution"):
        declaration = json.loads((previous / f"{name}.json").read_text())
        identities[name] = capture_code_identity(
            package,
            (declaration["entry"],),
            callables=tuple(declaration["roots"]),
            external_runtime=capabilities,
        )
    print(
        json.dumps(
            {
                name: {
                    "complete": value.complete,
                    "discovered_modules": len(value.modules),
                    "determining_modules": [source.module for source in value.determining_modules],
                    "required": [asdict(fact) for fact in value.unknowns],
                }
                for name, value in identities.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
