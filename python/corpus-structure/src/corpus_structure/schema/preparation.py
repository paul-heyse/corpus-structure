"""Prepare canonical generated files and their revision log before applying any writes."""

from __future__ import annotations

import fcntl
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from corpus_structure.schema import generate, model
from corpus_structure.schema.change import ChangeRecord

MODEL_PATH = model.MODEL_DIR.relative_to(generate.REPOSITORY)
PACKAGE_PATH = generate.PACKAGE.relative_to(generate.REPOSITORY)


@contextmanager
def writer_lock(root: Path) -> Generator[None]:
    """Serialize the supported model writers in this checkout."""
    lock_path = root / "build/ci/.model-writer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def prepare(
    loaded: model.Model,
    log: list[dict],
    *,
    before: model.Model | None = None,
    record: ChangeRecord | None = None,
) -> dict[str, str]:
    """Validate declarations and log, then render the exact owner-defined output paths."""
    from corpus_structure.schema import change

    problems = model.check(loaded)
    if problems:
        raise model.ModelError(problems)
    current = model.revision(loaded)
    if before is None:
        if record is not None:
            raise model.ModelError(["a change record requires a baseline"])
        log = model.record_root(current, log)
    else:
        previous = model.revision(before)
        problems = model.check_log(previous, log)
        if previous.content_hash != current.content_hash:
            if record is None:
                problems.append("a canonical declaration change requires an explicit change record")
            else:
                if record.from_revision != previous.content_hash:
                    problems.append("change record does not name the baseline revision")
                if record.to_revision != current.content_hash:
                    problems.append("change record does not name the requested revision")
                if any(entry.get("content_hash") == current.content_hash for entry in log):
                    problems.append("the requested revision already appears in the revision log")
                if any(entry.get("label") == current.label for entry in log):
                    problems.append("the requested revision label already appears in the revision log")
                problems.extend(change.check(record, before, loaded))
                log = [
                    *log,
                    {
                        **current.entry(),
                        "parent": previous.content_hash,
                        "change_record": record.model_dump(mode="json", exclude_defaults=True),
                    },
                ]
        elif record is not None:
            problems.append("the change record has no canonical declaration change")
        if problems:
            raise model.ModelError(problems)
    problems = model.check_log(current, log)
    if problems:
        raise model.ModelError(problems)
    return {
        **{(PACKAGE_PATH / path).as_posix(): content for path, content in generate.render(loaded).items()},
        (MODEL_PATH / "revisions.yaml").as_posix(): model.render_log(log),
    }
