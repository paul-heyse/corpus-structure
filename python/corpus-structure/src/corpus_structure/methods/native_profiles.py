"""Frozen numerical/provider meaning and separate shared-host acquisition paths."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from corpus_structure.semantic.identity import canonical_bytes

Provider = Literal["d1", "gliner", "hanlp", "spacy", "maverick", "dipo"]
_HOSTS = {
    "d1": "314",
    "gliner": "314",
    "hanlp": "314",
    "spacy": "314",
    "maverick": "312",
    "dipo": "312",
}


@dataclass(frozen=True, init=False)
class NativeProfile:
    """One canonical immutable snapshot owns all requested execution meaning.

    Mapping properties and declarations return owned decoded copies. Neither the
    constructor's input aliases nor returned dictionaries can edit this profile.
    Resolved CUDA placement remains an observation outside this requested identity.
    """

    _content: bytes

    def __init__(
        self,
        provider: Provider,
        runtime_identity: dict[str, Any],
        artifacts: dict[str, Any],
        parameters: dict[str, Any],
        dtype: Literal["float32", "bfloat16"],
        backend: str,
        threads: int = 4,
        interop_threads: int = 1,
        device: Literal["cuda"] = "cuda",
        matmul_precision: Literal["highest"] = "highest",
        cudnn_allow_tf32: bool = False,
        version: Literal["nlp-gpu-profile-1"] = "nlp-gpu-profile-1",
    ):
        if provider not in _HOSTS or device != "cuda":
            raise ValueError("selected native profile requires a supported CUDA provider")
        if dtype != ("bfloat16" if provider == "d1" else "float32"):
            raise ValueError("selected native provider dtype differs from its numerical recipe")
        if not backend or version != "nlp-gpu-profile-1":
            raise ValueError("native profile requires its explicit supported backend/version")
        if any(type(n) is not int or n < 1 for n in (threads, interop_threads)):
            raise ValueError("native profile threads must be positive integers")
        if matmul_precision != "highest" or cudnn_allow_tf32 is not False:
            raise ValueError("native profile requires the selected explicit FP32 math recipe")
        object.__setattr__(
            self,
            "_content",
            canonical_bytes(
                dict(
                    provider=provider,
                    runtime_identity=runtime_identity,
                    artifacts=artifacts,
                    parameters=parameters,
                    dtype=dtype,
                    backend=backend,
                    threads=threads,
                    interop_threads=interop_threads,
                    device=device,
                    matmul_precision=matmul_precision,
                    cudnn_allow_tf32=cudnn_allow_tf32,
                    version=version,
                )
            ),
        )

    @property
    def wire(self):
        return json.loads(self._content)

    @property
    def provider(self):
        return self.wire["provider"]

    @property
    def runtime_identity(self):
        return self.wire["runtime_identity"]

    @property
    def artifacts(self):
        return self.wire["artifacts"]

    @property
    def parameters(self):
        return self.wire["parameters"]

    @property
    def dtype(self):
        return self.wire["dtype"]

    @property
    def backend(self):
        return self.wire["backend"]

    @property
    def threads(self):
        return self.wire["threads"]

    @property
    def interop_threads(self):
        return self.wire["interop_threads"]

    @property
    def device(self):
        return self.wire["device"]

    @property
    def matmul_precision(self):
        return self.wire["matmul_precision"]

    @property
    def cudnn_allow_tf32(self):
        return self.wire["cudnn_allow_tf32"]

    @property
    def version(self):
        return self.wire["version"]

    @property
    def host(self):
        return _HOSTS[self.provider]

    @property
    def content(self):
        return self._content

    @property
    def fingerprint(self):
        return sha256(self._content).hexdigest()

    @classmethod
    def from_content(cls, content):
        return cls(**json.loads(content))


@dataclass(frozen=True)
class NativeSelection:
    """One immutable profile, with nonsemantic local acquisition locations."""

    native: NativeProfile
    assets: Path

    @property
    def provider(self):
        return self.native.provider

    @property
    def profile(self):
        return self.native.content

    @property
    def runtime(self):
        return canonical_bytes(self.native.runtime_identity)

    @property
    def artifacts(self):
        return canonical_bytes(self.native.artifacts)

    @property
    def device(self):
        return self.native.device

    @property
    def project(self):
        root = Path(__file__).resolve().parents[5]
        return root if self.native.host == "314" else root / "services/nlp-host-312"

    @property
    def python(self):
        return self.project / ".venv/bin/python"

    @property
    def script(self):
        return Path(__file__).with_name("native_host_worker.py")

    @property
    def identity(self):
        return self.native.fingerprint, str(self.assets.absolute())

    def declaration(self):
        return dict(
            profile=self.native.wire,
            fingerprint=self.native.fingerprint,
            assets=str(self.assets.absolute()),
        )
