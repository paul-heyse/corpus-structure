"""Conservative compatibility for rederiving a page in the managed installation."""

import sys
from dataclasses import dataclass
from functools import cache
from hashlib import sha256
from importlib.metadata import distributions
from pathlib import Path

from corpus_structure._query_custody import SourceCustodyError, capture_sources

from .data_operation_json import json_bytes
from .file_custody import FileCustody, observed_file, stat_identity

_ROOT = Path(__file__).resolve().parents[1]


def _inventory(root: Path) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    directories, files = [], []
    for directory, subdirectories, names in root.walk(on_error=_raise):
        subdirectories[:] = [name for name in subdirectories if name != "__pycache__"]
        directories.append(directory)
        files.extend(
            directory / name
            for name in names
            if not name.startswith(".") and Path(name).suffix not in {".md", ".pyc"}
        )
    return tuple(sorted(directories)), tuple(sorted(files))


def _raise(error: OSError):
    raise error


def _dependency_inventory() -> tuple[tuple[str, str, str], ...]:
    """Fingerprint managed environment metadata once, independent of discovery order."""
    records = []
    for distribution in distributions():
        name = distribution.metadata["Name"]
        if not name or not distribution.version:
            raise SourceCustodyError("installed dependency lacks version metadata")
        witness = sha256()
        for member in ("RECORD", "direct_url.json"):
            content = distribution.read_text(member)
            if content is not None:
                witness.update(json_bytes([member, content]))
        records.append((name.lower(), distribution.version, witness.hexdigest()))
    return tuple(sorted(records))


@dataclass(frozen=True)
class ServingInstallation:
    root: Path
    digest: str
    sources: dict[str, str]
    files: tuple[Path, ...]
    directories: tuple[tuple[Path, tuple[int, int, int, int, int]], ...]
    resources: tuple[FileCustody, ...]

    def check(self) -> None:
        try:
            # A changed directory can add a lazy import that was absent at capture.
            if any(stat_identity(path) != stamp for path, stamp in self.directories):
                directories, files = _inventory(self.root)
                if files != self.files or directories != tuple(p for p, _ in self.directories):
                    raise SourceCustodyError(
                        "serving installation inventory changed; restart required"
                    )
            for record in self.resources:
                record.check()
        except (OSError, ValueError) as error:
            raise SourceCustodyError("serving installation changed; restart required") from error


def _capture_installation(root: Path) -> ServingInstallation:
    directories, files = _inventory(root)
    stamps = tuple((path, stat_identity(path)) for path in directories)
    if any(not path.is_file() or path.is_symlink() for path in files):
        raise SourceCustodyError("serving installation requires regular owned package files")
    sources = capture_sources(path for path in files if path.suffix == ".py")
    resources = tuple(observed_file(path) for path in files if path.suffix != ".py")
    interpreter = observed_file(Path(sys.executable).resolve())
    digests = sources | {str(record.path): record.digest for record in resources}
    digest = sha256(
        json_bytes(
            [
                "managed-serving-installation-v1",
                [(path.relative_to(root).as_posix(), digests[str(path)]) for path in files],
                [interpreter.digest, sys.version, sys.implementation.cache_tag],
                _dependency_inventory(),
            ]
        )
    ).hexdigest()
    installation = ServingInstallation(
        root, digest, sources, files, stamps, (*resources, interpreter)
    )
    installation.check()
    return installation


@cache
def serving_installation() -> ServingInstallation:
    return _capture_installation(_ROOT)
