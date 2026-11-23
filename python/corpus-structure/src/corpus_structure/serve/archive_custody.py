"""Own detached archive bytes from authentication through final consumption."""

from contextlib import contextmanager
from hashlib import sha256
from os import O_DIRECTORY, O_NOFOLLOW, O_NONBLOCK, O_RDONLY, close, fdopen, fstat
from os import open as open_fd
from pathlib import Path, PurePosixPath
from stat import S_ISREG
from tempfile import TemporaryDirectory


@contextmanager
def _source_file(root_fd, name):
    path = PurePosixPath(name)
    if not path.parts or path.is_absolute() or ".." in path.parts or path.as_posix() != name:
        raise ValueError("detached archive requires canonical relative file names")
    directories = []
    parent = root_fd
    try:
        for part in path.parts[:-1]:
            parent = open_fd(part, O_RDONLY | O_DIRECTORY | O_NOFOLLOW, dir_fd=parent)
            directories.append(parent)
        fd = open_fd(path.name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK, dir_fd=parent)
        with fdopen(fd, "rb") as stream:
            if not S_ISREG(fstat(fd).st_mode):
                raise ValueError("detached archive files must be regular files")
            yield stream
    finally:
        for directory in reversed(directories):
            close(directory)


@contextmanager
def _source_root(root):
    owner = open_fd(root, O_RDONLY | O_DIRECTORY)
    try:
        yield owner
    finally:
        close(owner)


def verified_archive_members(root, expected):
    """Read small manifest members once and return the bytes just authenticated."""
    members = {}
    with _source_root(root) as source:
        for name, digest in expected.items():
            with _source_file(source, name) as stream:
                content = stream.read()
            if sha256(content).hexdigest() != digest:
                raise ValueError("detached file differs from its pinned manifest: " + name)
            members[name] = content
    return members


@contextmanager
def acquire_demand_archive(root, manifest_digest, decode_manifest):
    """Verify a copy owned exclusively by this invocation before exposing any scan path."""
    with _source_root(root) as source, TemporaryDirectory(prefix="selected-archive-") as temporary:
        with _source_file(source, "manifest.json") as stream:
            content = stream.read()
        if sha256(content).hexdigest() != manifest_digest:
            raise ValueError("export manifest differs from the explicit trusted digest")
        manifest = decode_manifest(content)
        owned = Path(temporary)
        for name, descriptor in manifest.files.items():
            path = owned / name
            path.parent.mkdir(parents=True, exist_ok=True)
            digest = sha256()
            remaining = descriptor.bytes
            with _source_file(source, name) as stream, path.open("xb") as output:
                if fstat(stream.fileno()).st_size != remaining:
                    raise ValueError("detached file differs from its pinned manifest: " + name)
                while remaining:
                    chunk = stream.read(min(remaining, 1024 * 1024))
                    if not chunk:
                        raise ValueError("detached file differs from its pinned manifest: " + name)
                    output.write(chunk)
                    digest.update(chunk)
                    remaining -= len(chunk)
                if stream.read(1) or digest.hexdigest() != descriptor.sha256:
                    raise ValueError("detached file differs from its pinned manifest: " + name)
        yield owned, manifest
