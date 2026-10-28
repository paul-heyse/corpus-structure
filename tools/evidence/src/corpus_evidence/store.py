"""Evidence folders, their records, content hashes and consistency checks."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from .model import FileRef, Record, item_kind

RECORDS_DIR = "records"
FOLDER_GLOB = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_*"
SKIP_NAMES = {"__pycache__", ".DS_Store"}


@dataclass
class Folder:
    path: Path
    records: dict[str, Record] = field(default_factory=dict)
    record_paths: dict[str, Path] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.path.name

    def title(self) -> str:
        readme = self.path / "README.md"
        if readme.exists():
            for line in readme.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    return line[2:].strip()
        return self.name


@dataclass
class Store:
    root: Path
    folders: dict[str, Folder]
    load_errors: list[str]

    def resolve(self, folder: Folder, ref: str) -> tuple[Folder, Record] | None:
        fname, _, rid = ref.rpartition("/")
        target = self.folders.get(fname) if fname else folder
        if target is None or rid not in target.records:
            return None
        return target, target.records[rid]

    def all_records(self) -> list[tuple[Folder, Record]]:
        return [(f, r) for f in self.folders.values() for r in f.records.values()]


def load(root: Path) -> Store:
    folders: dict[str, Folder] = {}
    errors: list[str] = []
    for path in sorted(p for p in root.glob(FOLDER_GLOB) if p.is_dir()):
        folder = Folder(path)
        for rec_path in sorted((path / RECORDS_DIR).glob("*.json")):
            try:
                rec = Record.model_validate_json(rec_path.read_bytes())
            except ValidationError as e:
                errors.append(f"{rec_path.relative_to(root)}: invalid record: {e}")
                continue
            if rec.id != rec_path.stem:
                errors.append(
                    f"{rec_path.relative_to(root)}: id {rec.id!r} does not match the file name"
                )
            if rec.id in folder.records:
                errors.append(f"{rec_path.relative_to(root)}: duplicate id {rec.id!r}")
            folder.records[rec.id] = rec
            folder.record_paths[rec.id] = rec_path
        folders[folder.name] = folder
    return Store(root, folders, errors)


def content_hash(path: Path) -> str:
    """sha256 of a file's bytes; of a directory, of its files' relative paths and hashes, sorted."""
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    h = hashlib.sha256()
    for f in sorted(p for p in path.rglob("*") if p.is_file() and not (set(p.parts) & SKIP_NAMES)):
        h.update(f.relative_to(path).as_posix().encode())
        h.update(b"\0")
        h.update(hashlib.sha256(f.read_bytes()).hexdigest().encode())
        h.update(b"\n")
    return h.hexdigest()


def finalize(folder: Folder, rid: str, today: dt.date | None = None) -> Record:
    """Fill every file hash (and the date) of a record and write it back."""
    rec = folder.records[rid]
    missing = [f.path for _, f in rec.files if not (folder.path / f.path).exists()]
    if missing:
        raise FileNotFoundError(f"{folder.name}/{rid}: missing files: {', '.join(missing)}")

    def hashed(refs: list[FileRef]) -> list[FileRef]:
        return [r.model_copy(update={"sha256": content_hash(folder.path / r.path)}) for r in refs]

    new = rec.model_copy(
        update={
            "inputs": hashed(rec.inputs),
            "outputs": hashed(rec.outputs),
            "finalized": today or dt.date.today(),
        }
    )
    new = Record.model_validate(new.model_dump())  # re-validate the updated record
    write(folder, new)
    return new


def write(folder: Folder, rec: Record) -> Path:
    path = folder.path / RECORDS_DIR / f"{rec.id}.json"
    path.parent.mkdir(exist_ok=True)
    data = rec.model_dump(mode="json", exclude_defaults=False)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    folder.records[rec.id] = rec
    folder.record_paths[rec.id] = path
    return path


@dataclass
class Issue:
    where: str
    message: str
    severity: str = "error"  # error | warning

    def __str__(self) -> str:
        return f"{self.severity}: {self.where}: {self.message}"


def check(store: Store) -> list[Issue]:
    issues = [Issue("records", e) for e in store.load_errors]
    for folder, rec in store.all_records():
        where = f"{folder.name}/{rec.id}"
        for direction, ref in rec.files:
            p = folder.path / ref.path
            if not p.exists():
                issues.append(Issue(where, f"{direction} {ref.path} does not exist"))
            elif ref.sha256 is None:
                issues.append(
                    Issue(where, f"{direction} {ref.path} has no hash (run `evidence finalize`)")
                )
            elif content_hash(p) != ref.sha256:
                sev = "error" if direction == "output" and rec.status == "current" else "warning"
                issues.append(
                    Issue(where, f"{direction} {ref.path} changed since finalization", sev)
                )
        for ref in [*rec.depends_on, *rec.supersedes]:
            if store.resolve(folder, ref) is None:
                issues.append(Issue(where, f"reference {ref!r} does not resolve"))
        if rec.superseded_by:
            hit = store.resolve(folder, rec.superseded_by)
            if hit is None:
                issues.append(Issue(where, f"superseded_by {rec.superseded_by!r} does not resolve"))
            elif not any(store.resolve(hit[0], s) == (folder, rec) for s in hit[1].supersedes):
                issues.append(Issue(where, f"{rec.superseded_by} does not list it in supersedes"))
        for ref in rec.supersedes:
            hit = store.resolve(folder, ref)
            if hit and hit[1].status != "superseded":
                issues.append(Issue(where, f"supersedes {ref} but that record is still current"))
        for ref in rec.depends_on:
            hit = store.resolve(folder, ref)
            if hit and hit[1].status == "superseded" and rec.status == "current":
                issues.append(Issue(where, f"depends on superseded {ref}", "warning"))
        for name in ("answers", "consumed_by"):
            for item in getattr(rec, name):
                ref = item.split(" ", 1)[0]
                if item_kind(item) == "record" and store.resolve(folder, ref) is None:
                    issues.append(Issue(where, f"{name} names unknown record {ref}", "warning"))
    return issues
