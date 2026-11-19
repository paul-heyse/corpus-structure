"""Verified immutable disk entries for expendable program and page retention."""

from __future__ import annotations

import fcntl
import logging
import os
import re
import stat
from collections.abc import Generator, Mapping
from contextlib import contextmanager, suppress
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

Tier = Literal["programs", "pages"]
_TIERS: tuple[Tier, ...] = ("programs", "pages")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_LOG = logging.getLogger(__name__)


class CacheStoreError(ValueError):
    """Disk retention cannot establish its local storage contract."""


class _File(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    size: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class _Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: str
    key: str = Field(pattern=r"^[0-9a-f]{64}$")
    files: dict[str, _File]


class DiskTierStats(BaseModel):
    tier: Tier
    entries: int
    bytes: int
    max_bytes: int
    hits: int = 0
    misses: int = 0
    writes: int = 0
    unusable: int = 0


class DiskSnapshot(BaseModel):
    root: str
    tiers: tuple[DiskTierStats, ...]


class PrunedTier(BaseModel):
    tier: Tier
    entries_removed: int
    bytes_removed: int
    abandoned_writers_removed: int
    bytes_retained: int
    max_bytes: int


class PruneReport(BaseModel):
    root: str
    tiers: tuple[PrunedTier, ...]


def _name(name: str) -> str:
    if not _NAME.fullmatch(name) or name == "manifest.json":
        raise CacheStoreError("cache file or version name is invalid")
    return name


def _private(fd: int) -> None:
    info = os.fstat(fd)
    if info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise CacheStoreError("cache directory must be writable only by its operator")


@contextmanager
def _directory(path: Path) -> Generator[int]:
    fd = os.open(path.anchor, _FLAGS)
    try:
        for part in path.parts[1:]:
            try:
                opened = os.open(part, _FLAGS, dir_fd=fd)
            except FileNotFoundError:
                with suppress(FileExistsError):
                    os.mkdir(part, 0o700, dir_fd=fd)
                opened = os.open(part, _FLAGS, dir_fd=fd)
            os.close(fd)
            fd = opened
        _private(fd)
        yield fd
    finally:
        os.close(fd)


@contextmanager
def _child(parent: int, name: str, *, create: bool = False) -> Generator[int]:
    if create:
        with suppress(FileExistsError):
            os.mkdir(name, 0o700, dir_fd=parent)
    fd = os.open(name, _FLAGS, dir_fd=parent)
    try:
        _private(fd)
        yield fd
    finally:
        os.close(fd)


def _read(parent: int, name: str, limit: int) -> bytes:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise CacheStoreError("cache content is not a bounded regular file")
        result = stream.read(limit + 1)
        if len(result) > limit:
            raise CacheStoreError("cache content exceeds its declared size")
        return result


def _write(parent: int, name: str, content: bytes) -> None:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _remove(parent: int, name: str) -> None:
    """Remove only a cache-owned directory, with no traversal through links."""
    with _child(parent, name) as fd:
        for child in os.listdir(fd):
            info = os.stat(child, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                raise CacheStoreError("cache entry contains an unexpected directory")
            os.unlink(child, dir_fd=fd)
    os.rmdir(name, dir_fd=parent)


@contextmanager
def _locked(parent: int, name: str, operation: int) -> Generator[int]:
    fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=parent)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise CacheStoreError("cache lock must be an operator-owned regular file")
        fcntl.flock(fd, operation)
        yield fd
    finally:
        os.close(fd)


def _writer(parent: int, name: str) -> tuple[int, int]:
    os.mkdir(name, 0o700, dir_fd=parent)
    writer_fd = os.open(name, _FLAGS, dir_fd=parent)
    lease_fd = None
    try:
        lease_fd = os.open(".lease", os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=writer_fd)
        fcntl.flock(lease_fd, fcntl.LOCK_EX)
        return writer_fd, lease_fd
    except BaseException:
        if lease_fd is not None:
            os.close(lease_fd)
        os.close(writer_fd)
        with suppress(OSError, ValueError):
            _remove(parent, name)
        raise


class CacheStore:
    def __init__(self, root: Path, *, program_store_bytes: int, page_store_bytes: int):
        if min(program_store_bytes, page_store_bytes) < 0:
            raise ValueError("cache budgets must be nonnegative")
        self.root = Path(os.path.abspath(root))
        self.budgets = dict(programs=program_store_bytes, pages=page_store_bytes)
        self._counts = {tier: dict(hits=0, misses=0, writes=0, unusable=0) for tier in _TIERS}

    @contextmanager
    def _tier(self, tier: Tier, *, exclusive: bool) -> Generator[int]:
        if tier not in _TIERS:
            raise CacheStoreError("unknown cache tier")
        with (
            _directory(self.root) as root,
            _child(root, tier, create=True) as fd,
            _locked(fd, ".lock", fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH),
        ):
            yield fd

    def _entry(self, version_fd: int, digest: str, version: str, limit: int) -> dict[str, bytes]:
        with _child(version_fd, digest) as fd:
            manifest_bytes = _read(fd, "manifest.json", min(limit, 4 * 1024**2))
            manifest = _Manifest.model_validate_json(manifest_bytes)
            if manifest.key != digest or manifest.version != version or not manifest.files:
                raise CacheStoreError("cache manifest identity differs")
            if set(os.listdir(fd)) != {"manifest.json", *manifest.files}:
                raise CacheStoreError("cache entry file inventory differs")
            if len(manifest_bytes) + sum(item.size for item in manifest.files.values()) > limit:
                raise CacheStoreError("cache entry exceeds its tier budget")
            result = {}
            for name, expected in manifest.files.items():
                content = _read(fd, _name(name), expected.size)
                if len(content) != expected.size or sha256(content).hexdigest() != expected.sha256:
                    raise CacheStoreError("cache content digest differs")
                result[name] = content
            return result

    def get(self, tier: Tier, version: str, key: bytes) -> dict[str, bytes] | None:
        if not self.budgets[tier]:
            return None
        digest = sha256(key).hexdigest()
        try:
            with self._tier(tier, exclusive=False) as fd, _child(fd, _name(version)) as version_fd:
                result = self._entry(version_fd, digest, version, self.budgets[tier])
            self._counts[tier]["hits"] += 1
            _LOG.debug("%s disk cache hit", tier)
            return result
        except FileNotFoundError:
            self._counts[tier]["misses"] += 1
            _LOG.debug("%s disk cache miss", tier)
            return None
        except (OSError, ValueError) as error:
            self._counts[tier]["unusable"] += 1
            _LOG.warning("%s disk cache unavailable: %s", tier, error)
            # Recheck under exclusive custody before removing a corrupt entry.
            with (
                suppress(OSError, ValueError),
                self._tier(tier, exclusive=True) as fd,
                _child(fd, _name(version)) as vfd,
            ):
                try:
                    self._entry(vfd, digest, version, self.budgets[tier])
                except OSError, ValueError:
                    _remove(vfd, digest)
            return None

    def put(self, tier: Tier, version: str, key: bytes, files: Mapping[str, bytes]) -> bool:
        budget = self.budgets[tier]
        if not budget:
            return False
        temporary = ".writer-" + uuid4().hex
        digest = sha256(key).hexdigest()
        try:
            checked = {_name(name): content for name, content in files.items()}
            if not checked:
                raise CacheStoreError("cache entry requires content files")
            manifest = (
                _Manifest(
                    version=_name(version),
                    key=digest,
                    files={
                        name: _File(size=len(content), sha256=sha256(content).hexdigest())
                        for name, content in checked.items()
                    },
                )
                .model_dump_json()
                .encode()
            )
            size = len(manifest) + sum(map(len, checked.values()))
            if size > budget:
                return False
            # A writer holds its own lease while preparing outside the tier lock.
            with self._tier(tier, exclusive=True) as fd, _child(fd, version, create=True) as vfd:
                writer_fd, lease_fd = _writer(vfd, temporary)
            try:
                for name, content in checked.items():
                    _write(writer_fd, name, content)
                _write(writer_fd, "manifest.json", manifest)
                with self._tier(tier, exclusive=True) as fd, _child(fd, version) as vfd:
                    if digest in os.listdir(vfd):
                        try:
                            winner = self._entry(vfd, digest, version, budget)
                        except OSError, ValueError:
                            _remove(vfd, digest)
                            raise
                        if winner != checked:
                            _remove(vfd, digest)
                            raise CacheStoreError(
                                "cache winner has different content for the same key"
                            )
                        return True
                    os.unlink(".lease", dir_fd=writer_fd)
                    os.rename(temporary, digest, src_dir_fd=vfd, dst_dir_fd=vfd)
                    os.fsync(vfd)
                    self._counts[tier]["writes"] += 1
                    self._prune_tier(tier, fd)
                    return True
            finally:
                os.close(lease_fd)
                os.close(writer_fd)
                with (
                    suppress(OSError, ValueError),
                    self._tier(tier, exclusive=True) as fd,
                    _child(fd, version) as vfd,
                ):
                    _remove(vfd, temporary)
        except (OSError, ValueError) as error:
            self._counts[tier]["unusable"] += 1
            _LOG.warning("%s disk cache write skipped: %s", tier, error)
            return False

    def _inventory(self, fd: int):
        entries = []
        for version in sorted(os.listdir(fd)):
            if not _NAME.fullmatch(version):
                continue
            with _child(fd, version) as vfd:
                for name in os.listdir(vfd):
                    if _DIGEST.fullmatch(name):
                        with _child(vfd, name) as entry:
                            info = os.fstat(entry)
                            size = sum(
                                os.stat(child, dir_fd=entry, follow_symlinks=False).st_size
                                for child in os.listdir(entry)
                            )
                        entries.append((info.st_mtime_ns, version, name, size))
        return sorted(entries)

    def _prune_tier(self, tier: Tier, fd: int) -> PrunedTier:
        entries = self._inventory(fd)
        retained = sum(row[3] for row in entries)
        removed = removed_bytes = abandoned = 0
        for _, version, name, size in entries:
            if retained <= self.budgets[tier]:
                break
            with _child(fd, version) as vfd:
                _remove(vfd, name)
            retained -= size
            removed += 1
            removed_bytes += size
        for version in os.listdir(fd):
            if not _NAME.fullmatch(version):
                continue
            with _child(fd, version) as vfd:
                for name in os.listdir(vfd):
                    if not name.startswith(".writer-"):
                        continue
                    with _child(vfd, name) as writer:
                        try:
                            with _locked(writer, ".lease", fcntl.LOCK_EX | fcntl.LOCK_NB):
                                _remove(vfd, name)
                                abandoned += 1
                        except BlockingIOError:
                            pass
        return PrunedTier(
            tier=tier,
            entries_removed=removed,
            bytes_removed=removed_bytes,
            abandoned_writers_removed=abandoned,
            bytes_retained=retained,
            max_bytes=self.budgets[tier],
        )

    def snapshot(self) -> DiskSnapshot:
        if not self.root.exists() and not self.root.is_symlink():
            return DiskSnapshot(
                root=str(self.root),
                tiers=tuple(
                    DiskTierStats(
                        tier=tier,
                        entries=0,
                        bytes=0,
                        max_bytes=self.budgets[tier],
                        **self._counts[tier],
                    )
                    for tier in _TIERS
                ),
            )
        tiers = []
        for tier in _TIERS:
            with self._tier(tier, exclusive=False) as fd:
                inventory = self._inventory(fd)
            tiers.append(
                DiskTierStats(
                    tier=tier,
                    entries=len(inventory),
                    bytes=sum(row[3] for row in inventory),
                    max_bytes=self.budgets[tier],
                    **self._counts[tier],
                )
            )
        return DiskSnapshot(root=str(self.root), tiers=tuple(tiers))

    def prune(self, tier: Tier | None = None) -> PruneReport:
        reports = []
        for selected in _TIERS if tier is None else (tier,):
            with self._tier(selected, exclusive=True) as fd:
                reports.append(self._prune_tier(selected, fd))
        return PruneReport(root=str(self.root), tiers=tuple(reports))


@lru_cache(maxsize=4)
def _store(root: Path, programs: int, pages: int) -> CacheStore:
    return CacheStore(root, program_store_bytes=programs, page_store_bytes=pages)


def configured_store() -> CacheStore:
    from corpus_structure.caches import configured

    settings = configured()
    return _store(settings.root, settings.program_store_bytes, settings.page_store_bytes)
