"""Process-owned file authentication and metadata-confirmed reuse.

Content identity is established before reuse. Metadata is an invalidation signal,
never an alternative source of the expected digest. Records are not persistent.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from hashlib import file_digest
from pathlib import Path
from threading import RLock
from time import time_ns

# Conservative for the local POSIX filesystems supported by this workstation.
# Files inside this window are re-read at every check, including future stamps.
_RACY_WINDOW_NS = 2_000_000_000


def stat_identity(path: Path) -> tuple[int, int, int, int, int]:
    value = path.stat()
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


class FileCustodyError(ValueError):
    """Acquired file content changed; the importing process must restart."""


@dataclass
class FileCustody:
    path: Path
    digest: str
    identity: tuple[int, int, int, int, int]
    racily_clean: bool

    @classmethod
    def acquire(cls, path: Path, expected: str) -> FileCustody:
        path = Path(path)
        before = stat_identity(path)
        with path.open("rb") as source:
            observed = file_digest(source, "sha256").hexdigest()
        after = stat_identity(path)
        if before != after or observed != expected:
            raise FileCustodyError(f"acquired file changed: {path}; restart required")
        return cls(path, expected, after, time_ns() - max(after[3:]) <= _RACY_WINDOW_NS)

    def check(self) -> None:
        try:
            observed = stat_identity(self.path)
            if observed != self.identity or self.racily_clean:
                refreshed = type(self).acquire(self.path, self.digest)
                self.identity, self.racily_clean = refreshed.identity, refreshed.racily_clean
        except OSError as error:
            raise FileCustodyError(
                f"acquired file unavailable: {self.path}; restart required"
            ) from error

    def receipt(self) -> tuple[str, str, tuple[int, int, int, int, int], bool]:
        self.check()
        return str(self.path), self.digest, self.identity, self.racily_clean

    @classmethod
    def accept(cls, receipt) -> FileCustody:
        """Child-side metadata handoff of an authenticated parent observation."""
        path, digest, identity, racily_clean = receipt
        record = cls(Path(path), digest, tuple(identity), racily_clean)
        # Metadata invalidates the observation; equal bytes can establish a fresh
        # observation, while a changed file cannot inherit parent custody.
        if stat_identity(record.path) != record.identity or record.racily_clean:
            try:
                return cls.acquire(record.path, record.digest)
            except (FileCustodyError, OSError) as error:
                raise FileCustodyError(
                    f"file changed during worker handoff: {path}; restart required"
                ) from error
        return record


_records: dict[Path, dict[str, FileCustody]] = {}
_lock = RLock()


def verified_file(path: Path, expected: str) -> FileCustody:
    """Authenticate once per process/path/digest and check its mutable premises."""
    path = Path(path)
    with _lock:
        records = _records.get(path)
        record = records.get(expected) if records is not None else None
        if record is None:
            record = FileCustody.acquire(path, expected)
            _records.setdefault(path, {})[expected] = record
        else:
            record.check()
        return record


_observed: dict[Path, FileCustody] = {}
_verified_derivations: dict[Path, tuple[str, tuple[int, int, int, int, int], Hashable]] = {}
_derivation_lock = RLock()


def verify_file_derivation(
    path: Path, expected: str, premise: Hashable, verify: Callable[[], None]
) -> None:
    """Carry a completed derivation check for an authenticated immutable file."""
    with _derivation_lock:
        record = verified_file(path, expected)
        key = record.digest, record.identity, premise
        if _verified_derivations.get(path) == key:
            return
        verify()
        record.check()
        if record.identity != key[1]:
            raise FileCustodyError(f"file changed during verification: {path}")
        _verified_derivations[path] = key


def custody_counts() -> tuple[int, int]:
    with _lock:
        return sum(map(len, _records.values())), len(_verified_derivations)


def observed_file(path: Path) -> FileCustody:
    """Establish local runtime identity once; callers compare its admitted identity."""
    path = Path(path)
    with _lock:
        record = _observed.get(path)
        if record is None:
            records = _records.get(path)
            known = next(iter(records.values()), None) if records is not None else None
            if known is not None:
                known.check()
                _observed[path] = known
                return known
            before = stat_identity(path)
            with path.open("rb") as source:
                digest = file_digest(source, "sha256").hexdigest()
            after = stat_identity(path)
            if before != after:
                raise FileCustodyError(f"file changed during runtime acquisition: {path}")
            record = FileCustody(path, digest, after, time_ns() - max(after[3:]) <= _RACY_WINDOW_NS)
            _observed[path] = record
            _records.setdefault(path, {})[record.digest] = record
        else:
            record.check()
        return record


def accept_file_receipt(receipt, *, path: Path, expected: str) -> FileCustody:
    """Receive private parent custody without accepting a different file population."""
    if Path(receipt[0]) != Path(path) or receipt[1] != expected:
        raise FileCustodyError("model file handoff differs from admitted manifest")
    with _lock:
        path = Path(path)
        prior = _observed.get(path)
        if prior is not None and prior.digest != expected:
            raise FileCustodyError("file already has another runtime observation; restart required")
        records = _records.get(path)
        record = records.get(expected) if records is not None else None
        if record is None:
            record = FileCustody.accept(receipt)
            _records.setdefault(path, {})[expected] = record
        else:
            record.check()
        if prior is not None:
            prior.check()
        # A verified private parent handoff is already an observation. Priming the
        # path index avoids scanning every admitted digest on the child's first use.
        _observed.setdefault(path, record)
        return record
