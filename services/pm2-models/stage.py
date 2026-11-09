"""Stage and verify PM2 provider files without importing the providers."""

import argparse
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from fnmatch import fnmatchcase
from hashlib import file_digest, sha1
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from huggingface_hub import HfApi, snapshot_download

SNAPSHOTS = {
    "modernbert": (
        "answerdotai/ModernBERT-large",
        "45bb4654a4d5aaff24dd11d4781fa46d39bf8c13",
        ("config.json", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"),
    ),
    "maverick": (
        "sapienzanlp/maverick-mes-ontonotes",
        "087a90f0380ec1f20ed19732b657f53fd3542c81",
        ("config.yaml", "weights.ckpt"),
    ),
    "deberta": (
        "microsoft/deberta-v3-large",
        "64a8c8eab3e352a784c658aef62be1662607476f",
        ("config.json", "pytorch_model.bin", "spm.model", "tokenizer_config.json"),
    ),
    "dipo": (
        "larc-iu/dmrst-ettin-400m-gum-12.1.0",
        "e33906a27f89b2703df8ab19e471aa82141d62cb",
        ("config.json", "best_model.pt"),
    ),
    "ettin": (
        "jhu-clsp/ettin-encoder-400m",
        "7662476d60abb071a5bd319c9f3074f3072c062d",
        (
            "config.json",
            "pytorch_model.bin",
            "special_tokens_map.json",
            "tokenizer.json",
            "tokenizer_config.json",
        ),
    ),
    "d1": (
        "LiquidAI/d1-2B",
        "652f920e544ea37f81e4b0ce89b81d4ed0da90b1",
        (
            "*.py",
            "calibration.json",
            "chat_template.jinja",
            "config.json",
            "model.safetensors",
            "processor_config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "LICENSE",
        ),
    ),
}

HANLP_ARCHIVE = (
    "en_tok_lem_pos_ner_srl_udep_sdp_con_modernbert_large_prepend_false_20250107_181612.zip"
)
HANLP_URL = "https://ftp.hankcs.com/hanlp/mtl/" + HANLP_ARCHIVE
HANLP_SIZE = 1_519_954_959
HANLP_SHA256 = "b2e686acdd1702c40ebae2d248c82a2a1cff2e9a76754295c393f2e843d3222e"
HANLP_MEMBERS = (
    "config.json",
    "model.pt",
    "con_vocabs.json",
    "dep_vocabs.json",
    "lem_vocabs.json",
    "ner_vocabs.json",
    "pos_vocabs.json",
    "sdp/dm_vocabs.json",
    "sdp/pas_vocabs.json",
    "sdp/psd_vocabs.json",
    "srl_vocabs.json",
    "tok_vocabs.json",
)


def sha256(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def record(destination, data):
    path = destination / ".verified-artifacts.json"
    pending = path.with_suffix(".tmp")
    pending.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    pending.replace(path)


def stage_hub_snapshot(root, name):
    repo_id, revision, patterns = SNAPSHOTS[name]
    destination = root / name
    info = HfApi().model_info(repo_id, revision=revision, files_metadata=True, token=False)
    if info.sha != revision:
        raise ValueError(f"Unexpected revision for {repo_id}: {info.sha}")
    if info.siblings is None:
        raise ValueError(f"Missing file metadata for {repo_id}")
    for pattern in patterns:
        if not any(fnmatchcase(entry.rfilename, pattern) for entry in info.siblings):
            raise ValueError(f"Missing {pattern} from pinned snapshot {repo_id}")
    snapshot_download(
        repo_id,
        revision=revision,
        allow_patterns=patterns,
        local_dir=destination,
        token=False,
    )
    files = {}
    for entry in info.siblings:
        if not any(fnmatchcase(entry.rfilename, pattern) for pattern in patterns):
            continue
        path = destination / entry.rfilename
        size = path.stat().st_size
        if size != entry.size:
            raise ValueError(f"Size mismatch for {path}")
        digest = sha256(path)
        if entry.lfs:
            if digest != entry.lfs.sha256:
                raise ValueError(f"SHA-256 mismatch for {path}")
        else:
            blob = sha1(f"blob {size}\0".encode(), usedforsecurity=False)
            blob.update(path.read_bytes())
            if blob.hexdigest() != entry.blob_id:
                raise ValueError(f"Git blob identity mismatch for {path}")
        files[entry.rfilename] = {"sha256": digest, "size": size}
    record(destination, {"id": repo_id, "revision": revision, "files": files})

    # These aliases allow upstream wrappers to resolve their compiled-in identifiers
    # through the isolated offline Hub cache. All paths continue to name exact bytes.
    cache = root / "hub" / ("models--" + repo_id.replace("/", "--"))
    snapshot = cache / "snapshots" / revision
    snapshot.mkdir(parents=True, exist_ok=True)
    for filename in files:
        link = snapshot / filename
        if link.resolve() != (destination / filename).resolve():
            link.symlink_to(os.path.relpath(destination / filename, link.parent))
    refs = cache / "refs"
    refs.mkdir(exist_ok=True)
    main = refs / "main"
    if main.exists():
        if main.read_text(encoding="utf-8") != revision:
            raise ValueError(f"Existing offline Hub ref for {repo_id} differs from {revision}")
    else:
        pending = main.with_suffix(".pending")
        pending.write_text(revision, encoding="utf-8")
        pending.replace(main)


def stage_hanlp(root):
    destination = root / "hanlp"
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / HANLP_ARCHIVE
    candidate = archive
    if not archive.is_file():
        candidate = archive.with_suffix(".partial")
        subprocess.run(
            [
                "curl",
                "--fail",
                "--location",
                "--continue-at",
                "-",
                "--output",
                str(candidate),
                HANLP_URL,
            ],
            check=True,
        )
    if candidate.stat().st_size != HANLP_SIZE or sha256(candidate) != HANLP_SHA256:
        raise ValueError(f"Size or SHA-256 mismatch for {candidate}")
    if candidate != archive:
        candidate.replace(archive)
    files = {HANLP_ARCHIVE: {"sha256": HANLP_SHA256, "size": HANLP_SIZE}}
    archive_root = archive.stem
    members = [f"{archive_root}/{name}" for name in HANLP_MEMBERS]
    model = destination / archive_root
    with ZipFile(archive) as bundle:
        if model.exists():
            for member in members:
                path = destination / member
                with bundle.open(member) as stream:
                    digest = file_digest(stream, "sha256").hexdigest()
                if sha256(path) != digest:
                    raise ValueError(f"Extracted file differs from pinned HanLP archive: {path}")
                files[member] = {"sha256": digest, "size": path.stat().st_size}
        else:
            with TemporaryDirectory(dir=destination) as work:
                for member in members:
                    path = Path(bundle.extract(member, work))
                    files[member] = {"sha256": sha256(path), "size": path.stat().st_size}
                (Path(work) / archive_root).rename(model)
    record(
        destination,
        {"url": HANLP_URL, "files": files},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("build/models/pm2"))
    parser.add_argument("--only", nargs="+", choices=(*SNAPSHOTS, "hanlp"))
    args = parser.parse_args()
    root = args.root.resolve()
    names = args.only or (*SNAPSHOTS, "hanlp")
    if len(set(names)) != len(names):
        parser.error("each requested asset may appear only once")
    with ThreadPoolExecutor() as pool:
        staged = {
            name: (
                pool.submit(stage_hanlp, root)
                if name == "hanlp"
                else pool.submit(stage_hub_snapshot, root, name)
            )
            for name in names
        }
        for name, result in staged.items():
            result.result()
            print(f"Staged {name}")


if __name__ == "__main__":
    main()
