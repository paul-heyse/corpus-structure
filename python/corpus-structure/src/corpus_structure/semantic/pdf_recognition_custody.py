"""Exact installed runtime and callable selection for managed PDF recognition."""

from __future__ import annotations

import json
import os
import subprocess
from hashlib import sha256
from importlib.metadata import distribution
from pathlib import Path

from .file_custody import observed_file, verified_file

# The service worker's HTTP client/backend, image codecs and Nemotron's parser.
# Its server and local Transformers backend are separate deployed capabilities.
_CLIENT = (
    "anyio",
    "beautifulsoup4",
    "certifi",
    "h11",
    "httpcore",
    "httpx",
    "idna",
    "nemotron-parse",
    "numpy",
    "Pillow",
    "sniffio",
    "soupsieve",
    "typing-extensions",
)
_PARENT = (
    "annotated-types",
    "certifi",
    "h11",
    "httpcore",
    "httpx",
    "idna",
    "Pillow",
    "pydantic",
    "pydantic-core",
    "pypdfium2",
    "typing-extensions",
    "typing-inspection",
)

# Metadata acquisition uses the same isolated executable as the actual worker.
# Derive the explicit venv site directory without executing installed .pth files.
_INVENTORY = """
import importlib.metadata as metadata
import json
import pathlib
import sys
import sysconfig

root = pathlib.Path(sys.executable).parent.parent
if not (root / 'pyvenv.cfg').is_file():
    raise ValueError('managed recognition requires its selected virtual environment')
site = pathlib.Path(sysconfig.get_path('purelib', scheme='venv', vars={'base': str(root), 'platbase': str(root)}))
if not site.is_relative_to(root) or not site.is_dir():
    raise ValueError('managed recognition environment has no isolated package directory')
site = site.resolve()
client, pins = json.loads(sys.argv[1])
sys.path.append(str(site))
versions = {name: metadata.version(name) for name in pins}
if versions != pins:
    raise ValueError('managed recognition dependencies differ from the admitted package pins')
files = {}
for name in client:
    package = metadata.distribution(name)
    if package.files is None:
        raise ValueError('recognition dependency has no installed file inventory: ' + name)
    for member in package.files:
        path = pathlib.Path(package.locate_file(member)).resolve()
        if not path.is_relative_to(site) or path.suffix in {'.pyc', '.pyo'}:
            continue
        if not path.is_file():
            raise ValueError('recognition dependency file is missing: ' + str(path))
        files[path.relative_to(site).as_posix()] = str(path)
for name in pins:
    package = metadata.distribution(name)
    member = next(item for item in package.files if item.name == 'METADATA')
    path = pathlib.Path(package.locate_file(member)).resolve()
    if not path.is_relative_to(site):
        raise ValueError('recognition package metadata is outside the owned environment')
    files[path.relative_to(site).as_posix()] = str(path)
print(json.dumps({'versions': versions, 'site': str(site), 'files': files,
                  'stdlib': sysconfig.get_path('stdlib'),
                  'environment': str(root / 'pyvenv.cfg'), 'python': sys.version}))
"""

# No ambient site initializers or bytecode caches participate. Installed client
# imports must correspond to exact retained files. The package metadata probes
# in the worker still see the same checked site directory.
_BOOTSTRAP = """
import hashlib
import importlib.abc
import importlib.machinery
import json
import pathlib
import sys

script, site, inventory, expected = sys.argv[1:]
site = pathlib.Path(site)
contents = pathlib.Path(inventory).read_bytes()
if hashlib.sha256(contents).hexdigest() != expected:
    raise ValueError('recognition package inventory differs from parent custody')
files = json.loads(contents)

class SourceLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        content = pathlib.Path(self.path).read_bytes()
        if hashlib.sha256(content).hexdigest() != files[pathlib.Path(self.path).relative_to(site).as_posix()]:
            raise ImportError('recognition dependency changed: ' + fullname)
        return compile(content, self.path, 'exec', dont_inherit=True)

class AcquiredPackages(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None:
            return None
        if spec.origin is None:
            raise ImportError('unowned recognition package namespace: ' + fullname)
        origin = pathlib.Path(spec.origin).resolve()
        if origin.is_relative_to(site):
            relative = origin.relative_to(site).as_posix()
            if relative not in files:
                raise ImportError('unowned recognition dependency: ' + fullname)
            if origin.suffix == '.py':
                spec.loader = SourceLoader(fullname, str(origin))
            elif hashlib.sha256(origin.read_bytes()).hexdigest() != files[relative]:
                raise ImportError('recognition native dependency changed: ' + fullname)
        return spec

sys.meta_path.insert(sys.meta_path.index(importlib.machinery.PathFinder), AcquiredPackages())
sys.path.append(str(site))
sys.argv[:] = [script, '--serve']
content = pathlib.Path(script).read_bytes()
if hashlib.sha256(content).hexdigest() != files['<worker>']:
    raise ValueError('recognition worker differs from parent custody')
__file__ = script
exec(compile(content, script, 'exec', dont_inherit=True))
"""


def recognition_runtime(python: Path, worker: Path) -> dict:
    """Acquire the actual selected client interpreter and renderer files."""
    from corpus_structure.ingest.pdf_recognition import NEMOTRON_PACKAGES

    result = subprocess.run(
        [str(python), "-I", "-B", "-S", "-c", _INVENTORY, json.dumps((_CLIENT, NEMOTRON_PACKAGES))],
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise ValueError(
            "cannot acquire the managed recognition environment: "
            + result.stderr.decode(errors="replace")[-800:]
        )
    record = json.loads(result.stdout)
    stdlib = Path(record.pop("stdlib"))
    record["stdlib"] = str(stdlib)
    record["standard_library"] = [
        (path.relative_to(stdlib).as_posix(), observed_file(path).digest)
        for path in sorted(stdlib.rglob("*"))
        if path.suffix in {".py", ".so", ".pyd"}
        and path.is_file()
        and "site-packages" not in path.parts
        and "dist-packages" not in path.parts
    ]
    record["client"] = [
        (name, observed_file(Path(path)).digest)
        for name, path in sorted(record.pop("files").items())
    ]
    record["configuration"] = observed_file(Path(record["environment"])).digest
    record["worker"] = observed_file(worker).digest
    record["launcher"] = sha256(_BOOTSTRAP.encode()).hexdigest()
    renderer = []
    for name in _PARENT:
        package = distribution(name)
        if package.files is None:
            raise ValueError(
                "recognition renderer dependency has no installed file inventory: " + name
            )
        for member in package.files:
            path = Path(package.locate_file(member)).absolute()
            if ".." in member.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            renderer.append((name, str(member), str(path), observed_file(path).digest))
    record["renderer"] = sorted(renderer)
    return record


def recognition_runtime_identity(record: dict) -> dict:
    """Exclude installation locations while retaining exact executable meaning."""
    return {
        **{
            key: record[key]
            for key in ("python", "versions", "standard_library", "client", "worker", "launcher")
        },
        "renderer": [(package, name, digest) for package, name, _, digest in record["renderer"]],
    }


def verify_recognition_runtime(record: dict):
    if record["launcher"] != sha256(_BOOTSTRAP.encode()).hexdigest():
        raise ValueError("recognition worker launch differs from its acquired environment")
    return (
        verified_file(Path(record["environment"]), record["configuration"]),
        *(verified_file(Path(record["site"]) / name, digest) for name, digest in record["client"]),
        *(
            verified_file(Path(record["stdlib"]) / name, digest)
            for name, digest in record["standard_library"]
        ),
        *(verified_file(Path(path), digest) for _, _, path, digest in record["renderer"]),
    )


def recognition_worker_command(
    python: Path, worker: Path, directory: Path, record: dict
) -> list[str]:
    from .identity import canonical_bytes

    inventory = canonical_bytes(dict((*record["client"], ("<worker>", record["worker"]))))
    path = directory / "recognition-environment.json"
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(inventory)
    return [
        str(python),
        "-I",
        "-B",
        "-S",
        "-c",
        _BOOTSTRAP,
        str(worker),
        record["site"],
        str(path),
        sha256(inventory).hexdigest(),
    ]


def managed_page_generation(page, recipe, source_digest, execution_digest) -> str:
    """Recover the generation of the exact fresh or adopted managed invocation."""
    root = page.directory.resolve()
    path = root / "input.json"
    if path.resolve().parent != root:
        raise ValueError("managed recognition invocation escaped its attempt directory")
    invocation = json.loads(path.read_bytes())
    provider = invocation.get("service_binding")
    if (
        invocation.get("source_digest") != source_digest
        or invocation.get("recipe_digest") != recipe.digest
        or invocation.get("execution_digest") != execution_digest
        or not isinstance(provider, dict)
        or provider.get("protocol") != "corpus-managed-recognition-1"
        or provider.get("assurance") != "trusted_managed_service"
        or not isinstance(provider.get("generation"), str)
        or not provider["generation"]
        or provider.get("artifacts", {}).get("model.safetensors") != recipe.weights_digest
        or provider.get("artifacts", {}).get("tokenizer.json") != recipe.tokenizer_digest
    ):
        raise ValueError("managed recognition page differs from its acquired invocation")
    return provider["generation"]


def verify_managed_observation(row, raw, artifacts, generation) -> bool:
    """Check the actual already-carried bytes before admitting one raw reading."""
    if sha256(artifacts[0]).hexdigest() != row["submitted_digest"]:
        raise ValueError("managed recognition submitted image differs from its receipt")
    if row.get("outcome_class") == "execution" and "raw_response" not in row:
        return False
    if (
        row.get("identity_assurance") != "trusted_managed_service"
        or row.get("service_generation") != generation
        or row.get("response_generation") != generation
        or "http_response" not in row
    ):
        raise ValueError("managed recognition response crossed its acquired service generation")
    if "raw_response" in row:
        choice = json.loads(artifacts[2])["choices"][0]
        if (
            sha256(raw).hexdigest() != row["raw_digest"]
            or (choice["message"].get("content") or "").encode() != raw
            or choice.get("finish_reason") != row.get("finish_reason")
        ):
            raise ValueError("managed recognition raw response differs from its HTTP receipt")
    return True


def recognition_functions():
    from corpus_structure.ingest import pdf_recognition as worker

    from .pdf_integrated import PreparedPdfObservationPublisher, prepare_pdf_observation_publisher
    from .pdf_record_reader import PublishedPdfReader

    return (
        worker.admit_service_generation,
        worker.render_recognition_page,
        worker.render_affine,
        worker.recognition_observation_values,
        worker.repetition_recovery_recipe,
        worker.repetitive_capped_page,
        worker.terminal_recognition_result,
        worker.RecognitionPage.requests,
        worker.RecognitionWorker.__init__,
        worker.RecognitionWorker.recognize_pages,
        worker.RecognitionWorker._recognize_pages,
        worker.RecognitionWorker._execute_page,
        worker.RecognitionWorker._readmit_generation,
        worker._RecognitionSlot.execute,
        recognition_worker_command,
        managed_page_generation,
        verify_managed_observation,
        PublishedPdfReader.recognition_inventory,
        PreparedPdfObservationPublisher.publish,
        prepare_pdf_observation_publisher,
    )
