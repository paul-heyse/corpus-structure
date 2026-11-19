"""Check or generate the current released model's native Python projections."""

from __future__ import annotations

import sys
from pathlib import Path

from corpus_structure.schema.code_generation import native_facades
from corpus_structure.schema.declarations import ModelError
from corpus_structure.schema.model_change import native_model_inputs
from corpus_structure.schema.preparation import writer_lock
from corpus_structure.semantic.metadata import get_metadata


def main(argv: list[str]) -> int:
    if argv not in (["generate"], ["check"]):
        print("usage: python -m corpus_structure.schema generate|check", file=sys.stderr)
        return 2
    repository = Path(__file__).resolve().parents[5]
    try:
        files = native_facades(get_metadata(), native_model_inputs(repository))
    except (ModelError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    changed = [
        path
        for path, content in files.items()
        if not (repository / path).is_file() or (repository / path).read_text() != content
    ]
    if argv == ["generate"]:
        with writer_lock(repository):
            for relative in changed:
                destination = repository / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(files[relative])
        print("\n".join(f"wrote {path}" for path in changed) or "model: generated files current")
        return 0
    if changed:
        print(
            "\n".join(
                f"{path} differs from the released model (run just model generate)"
                for path in changed
            ),
            file=sys.stderr,
        )
        return 1
    print("model: released model projections current")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
