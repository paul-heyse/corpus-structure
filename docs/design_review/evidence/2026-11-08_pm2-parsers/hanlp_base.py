"""Compare pinned HanLP Large and Base on the same authenticated sentence scopes."""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import subprocess
import sys
from contextlib import redirect_stdout
from hashlib import file_digest
from importlib.metadata import version
from pathlib import Path
from runpy import run_path
from tempfile import TemporaryDirectory
from time import perf_counter
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[4]
METHODS = ROOT / "python/corpus-structure/src/corpus_structure/methods"
BASE = "en_tok_lem_pos_ner_srl_udep_sdp_con_modernbert_base_prepend_false_20241229_053838"
BASE_URL = f"https://ftp.hankcs.com/hanlp/mtl/{BASE}.zip"
BASE_BACKBONE = "answerdotai/ModernBERT-base"
BASE_REVISION = "8949b909ec900327062f0ebf497f51aef5e6f0c8"
BASE_FILES = {
    "config.json": "1609d59e627c33eaed524b4f01e546d42e84190a079a5a5ded84b212c41c324f",
    "special_tokens_map.json": "ea97ecdbcc73713039d8d64dbb05e3689495c96657fbd9a18f5bed381be81049",
    "tokenizer.json": "9fd55248d51d33976b324fc11592e28071da7d41e0e9401dfb7082e30574b7b1",
    "tokenizer_config.json": "3cd2017ff46d0a527e5d39cae39272eccfa1f19bb9f89b05d166aab2e38354e2",
}
DEPENDENCIES = {"hanlp": "2.1.7", "torch": "2.15.0", "transformers": "5.22.1"}


def sha256(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def stage_base(assets: Path, expected: str) -> None:
    staging = run_path(str(ROOT / "services/pm2-models/stage.py"))
    staging["SNAPSHOTS"]["modernbert-base"] = (BASE_BACKBONE, BASE_REVISION, tuple(BASE_FILES))
    staging["stage_hub_snapshot"](assets, "modernbert-base")
    archive = assets / "hanlp-base" / f"{BASE}.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        pending = archive.with_suffix(".pending")
        subprocess.run(
            [
                "curl", "--fail", "--location", "--continue-at", "-", "--max-time", "1800",
                "--output", str(pending), BASE_URL,
            ],
            check=True,
        )
        if sha256(pending) != expected:
            raise ValueError("HanLP Base download differs from the recorded archive digest")
        pending.rename(archive)
    if sha256(archive) != expected:
        raise ValueError("HanLP Base archive differs from the recorded digest")


def checked_base(assets: Path, expected: str, workspace: Path) -> tuple[Path, dict]:
    archive = assets / "hanlp-base" / f"{BASE}.zip"
    if sha256(archive) != expected:
        raise ValueError("HanLP Base archive differs from the recorded digest")
    cache = assets / "hub" / f"models--{BASE_BACKBONE.replace('/', '--')}"
    if (cache / "refs/main").read_text().strip() != BASE_REVISION:
        raise ValueError("HanLP Base backbone resolves outside the recorded revision")
    snapshot = cache / "snapshots" / BASE_REVISION
    for filename, digest in BASE_FILES.items():
        if sha256(snapshot / filename) != digest:
            raise ValueError(f"HanLP Base backbone file differs from its recorded digest: {filename}")
    staging = run_path(str(ROOT / "services/pm2-models/stage.py"))
    with ZipFile(archive) as bundle:
        for member in staging["HANLP_MEMBERS"]:
            bundle.extract(f"{BASE}/{member}", workspace)
    return workspace / BASE, {
        "archive": BASE_URL, "sha256": expected, "backbone": BASE_BACKBONE,
        "backbone_revision": BASE_REVISION, "backbone_files": BASE_FILES,
    }


def measure_child(assets: Path, expected: str, variant: str) -> None:
    os.environ.update(
        HF_HUB_CACHE=str(assets / "hub"), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
        CUDA_VISIBLE_DEVICES="",
    )
    import torch

    packages = {name: version(name) for name in DEPENDENCIES}
    if platform.python_version() != "3.14.10" or packages != DEPENDENCIES:
        raise ValueError("HanLP comparison requires the locked isolated runtime")
    torch.set_num_threads(4)
    loader = run_path(str(METHODS / "pm2_hanlp.py"))
    requests = json.load(sys.stdin)
    with TemporaryDirectory() as temp, redirect_stdout(sys.stderr):
        if variant == "base":
            directory, manifest = checked_base(assets, expected, Path(temp))
            start = perf_counter()
            profile, infer = loader["_load_hanlp"](assets, "cpu", directory, BASE_BACKBONE)
        else:
            verify = run_path(str(METHODS / "pm2_native.py"))["_verify_assets"]
            manifest = verify(assets, "hanlp")
            start = perf_counter()
            profile, infer = loader["load_hanlp"](assets, "cpu")
        cold_seconds = perf_counter() - start
        replies = []
        for request in requests:
            start = perf_counter()
            reply = infer(request)
            cold_scope_seconds = perf_counter() - start
            start = perf_counter()
            warm = infer(request)
            warm_scope_seconds = perf_counter() - start
            if reply != warm:
                raise ValueError(f"{variant} repeated native output changed on matched input")
            replies.append(
                {"reply": reply, "first_scope_seconds": cold_scope_seconds,
                 "repeat_scope_seconds": warm_scope_seconds}
            )
    json.dump(
        {
            "variant": variant, "assets": manifest, "profile": profile, "packages": packages,
            "python": platform.python_version(), "torch_threads": torch.get_num_threads(),
            "cold_load_seconds": cold_seconds,
            "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "scopes": replies,
        },
        sys.stdout,
        ensure_ascii=False,
    )


def measure(assets: Path, expected: str) -> None:
    from corpus_structure.methods.pm2_hanlp_products import hanlp_products
    from corpus_structure.methods.pm2_source import MappedSource
    from corpus_structure.semantic.operations import BoundReader
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.settings import Settings

    foundation = ROOT / "docs/design_review/evidence/2026-11-08_pm2-foundation/native_probe.py"
    baseline = run_path(str(foundation))
    with open_runtime_engine(Settings(), "pm2-hanlp-base", purpose="read") as engine:
        with engine.connect() as conn:
            prepared = open_release(conn, baseline["RELEASE"])
            view = BoundReader(conn, baseline["RUN"], prepared, baseline["CUT"]).source_view(
                baseline["VIEW"]
            )
    if view.ref.projection_digest != baseline["PROJECTION"]:
        raise ValueError("HanLP comparison requires the exact frozen source view")
    scopes = baseline["SCOPES"]
    maps = [baseline["inputs"](view, scope)[1] for scope in scopes]
    requests = [
        {"sentences": [
            [token.text for token in mapping.sentence_tokens(index)]
            for index in sorted({token.sentence for token in mapping.tokens})
        ]}
        for mapping in maps
    ]
    python = ROOT / "services/pm2-hanlp/.venv/bin/python"
    for variant in ("large", "base"):
        completed = subprocess.run(
            [
                str(python), "-I", "-B", str(Path(__file__).resolve()),
                "--assets", str(assets), "--base-sha256", expected, "--child", variant,
            ],
            input=json.dumps(requests), text=True, stdout=subprocess.PIPE, check=True, timeout=300,
        )
        result = json.loads(completed.stdout)
        for scope, mapping, request, row in zip(scopes, maps, requests, result["scopes"], strict=True):
            if row["reply"]["outcome"] != "succeeded":
                raise ValueError(f"{variant} did not cover the frozen comparison scope")
            products = hanlp_products(mapping, request, row["reply"])
            row.update(
                range=scope, request=request, source_view_id=view.ref.id,
                projection_digest=view.ref.projection_digest,
                products=[{"type": p.semantic_type, "key": p.key, "value": p.value}
                          for p in products.products],
                exact_locations=sum(isinstance(location, MappedSource) for location in products.locations.values()),
            )
        print(json.dumps(result, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", default=ROOT / "build/models/pm2", type=Path)
    parser.add_argument("--base-sha256", required=True, help="Exact recorded SHA-256 of the Base ZIP.")
    parser.add_argument("--stage-base", action="store_true")
    parser.add_argument("--child", choices=("large", "base"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if len(args.base_sha256) != 64 or any(c not in "0123456789abcdef" for c in args.base_sha256):
        parser.error("the Base archive requires an exact SHA-256")
    assets = args.assets.resolve()
    if args.child is not None:
        measure_child(assets, args.base_sha256, args.child)
    elif args.stage_base:
        stage_base(assets, args.base_sha256)
    else:
        measure(assets, args.base_sha256)


if __name__ == "__main__":
    main()
