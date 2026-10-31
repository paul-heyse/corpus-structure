"""Content-addressed, offline native model bundles; preparation never runs inference."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pdf import PdfRecipe


@dataclass(frozen=True, slots=True)
class PreparedPdfAssets:
    root: Path
    manifest: bytes
    files: tuple[tuple[str, str], ...]
    repositories: tuple[tuple[str, str], ...] = ()

    @property
    def digest(self) -> str:
        return sha256(self.manifest).hexdigest()

    def verify(self) -> None:
        for name, expected in self.files:
            path = self.root / name
            if not path.is_file() or _hash(path) != expected:
                raise ValueError(f"native model artifact integrity mismatch: {name}")


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_pdf_assets(
    recipe: PdfRecipe, *, cache: Path, offline: bool = True
) -> PreparedPdfAssets:
    """Pin actual selected repositories and OCR files into an owned immutable bundle.

    Local HF refs resolve the table tag to an immutable snapshot. A missing offline dependency
    refuses; no weaker model or engine is substituted. Every file used by native initialization
    is copied to the qualified bundle, whose identity is independent of cache location.
    """
    from huggingface_hub import snapshot_download

    repositories = (
        ("docling-project/docling-layout-heron", recipe.layout_revision),
        ("docling-project/CodeFormulaV2", recipe.formula_revision),
        ("docling-project/docling-models", "v2.3.0"),
    )
    roots: list[tuple[str, Path]] = []
    revisions: list[tuple[str, str]] = []
    for repository, revision in repositories:
        source = Path(
            snapshot_download(repo_id=repository, revision=revision, local_files_only=offline)
        )
        if re.fullmatch(r"[0-9a-f]{40}", source.name) is None:
            raise ValueError("HF model did not resolve to an immutable snapshot")
        roots.append((repository.replace("/", "--"), source))
        revisions.append((repository, source.name))
    ocr_root = cache / "RapidOcr"
    ocr_files = (
        "PP-OCRv6_det_small.onnx",
        "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
        "PP-OCRv6_rec_small.onnx",
    )
    selected: list[tuple[str, Path]] = []
    for folder, source in roots:
        selected.extend(
            (f"{folder}/{file.relative_to(source).as_posix()}", file)
            for file in sorted(source.rglob("*"))
            if file.is_file()
        )
    for name in ocr_files:
        path = ocr_root / name
        if not path.is_file():
            raise FileNotFoundError(f"prefetched RapidOCR artifact is missing: {path}")
        selected.append((f"RapidOcr/{name}", path))
    files = tuple((name, _hash(path)) for name, path in selected)
    manifest = json.dumps(
        {"recipe": "pdf-model-assets-v1", "repositories": revisions, "files": files},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    destination = cache / "qualified" / sha256(manifest).hexdigest()
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".pdf-models-", dir=destination.parent))
        try:
            for name, source in selected:
                target = temporary / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                target.chmod(0o444)
            (temporary / "manifest.json").write_bytes(manifest)
            try:
                temporary.rename(destination)
            except FileExistsError:
                shutil.rmtree(temporary)
        except BaseException:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
    prepared = PreparedPdfAssets(destination, manifest, files, tuple(revisions))
    prepared.verify()
    return prepared
