"""`python -m corpus_structure.schema generate|check` (`just model generate|check`).

`generate` checks the model's declarations, writes Stage A's files and records the root revision
in `model/revisions.yaml` while it is the only one. `check` changes nothing: it fails on a
declaration problem, a revision log that does not end at the current revision, or a generated file
that differs from what the model generates (a hand edit, or a model change not regenerated).
"""

from __future__ import annotations

import sys

from corpus_structure.schema import generate, model


def main(argv: list[str]) -> int:
    if argv not in (["generate"], ["check"]):
        print("usage: python -m corpus_structure.schema generate|check", file=sys.stderr)
        return 2
    loaded = model.load()
    current = model.revision(loaded)
    if argv == ["generate"]:
        problems = model.check(loaded)
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        changed = generate.write(generate.render(loaded))
        log = model.record_root(current, model.read_log())
        text = model.render_log(log)
        if not model.REVISIONS.exists() or model.REVISIONS.read_text(encoding="utf-8") != text:
            model.REVISIONS.write_text(text, encoding="utf-8")
            changed.append("model/revisions.yaml")
        print("\n".join(f"wrote {path}" for path in changed) or "model: generated files current")
        return 0
    from corpus_structure.core import vocab

    problems = model.check(loaded, vocab.MEMBER_PROPERTIES)
    problems += model.check_log(current, model.read_log())
    problems += [f"{path} differs from the model (run just model generate)"
                 for path in generate.drift(generate.render(loaded))]  # fmt: skip
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"model: revision {current.label} {current.content_hash[:12]} current")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
