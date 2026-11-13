"""Frozen numerical/provider meaning and separate shared-host acquisition paths."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, fields
from hashlib import sha256
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from corpus_structure.semantic.identity import canonical_bytes

if TYPE_CHECKING:
    from corpus_structure.semantic.data_operation_identity import ProfileIdentities

Provider = Literal["d1", "gliner", "hanlp", "spacy", "maverick", "dipo"]
_PROVIDERS = frozenset({"d1", "gliner", "hanlp", "spacy", "maverick", "dipo"})


def _identity_roles(
    owner: Any, names: set[str]
) -> dict[str, Literal["semantic", "execution", "acquisition"]]:
    """Read non-derivable roles from the authoritative field/port declarations."""
    annotations = get_type_hints(owner, include_extras=True)
    roles = {}
    for name in names:
        annotation = annotations.get(name)
        metadata = get_args(annotation)[1:] if get_origin(annotation) is Annotated else ()
        selected = [
            role.removeprefix("ddo:")
            for role in metadata
            if isinstance(role, str) and role.startswith("ddo:")
        ]
        if len(selected) != 1 or selected[0] not in {"semantic", "execution", "acquisition"}:
            raise ValueError("native profile field requires one declared identity role: " + name)
        roles[name] = cast(Literal["semantic", "execution", "acquisition"], selected[0])
    return roles


def _observation_policy(profile: NativeProfile, policy: Mapping[str, Any]) -> dict[str, Any]:
    """Select the supported released numerical meaning, never installed defaults.

    The current model-observation owner qualifies D1 and GLiNER observations. Other
    providers need an admitted numerical declaration before thread neutrality can
    be claimed. This projection authenticates no policy/release or execution by itself.
    """
    expected = {
        "version": 4,
        "native_input_order": "preserve-declared-question-option-state-field-order",
        "pm2_receipt_version": 2,
        "member_identity": "exact-request-context-source-and-inference-policy",
        "grouping": "compatible-admitted-members-in-declared-order",
        "native_numerical_variation": (
            "permitted-including-threshold-and-decoder-tie-selection-changes"
        ),
        "score_reduction": "unrounded-actual-native-confidence-with-unchanged-released-thresholds",
        "reuse": "authentic-retained-observation-not-bitwise-fresh-execution-equivalence",
    }
    if set(policy) != {*expected, "providers"} or canonical_bytes(
        {key: policy[key] for key in expected}
    ) != canonical_bytes(expected):
        raise ValueError(
            "native profile requires its supported explicit authentic-observation inference policy"
        )
    providers = policy["providers"]
    if profile.provider not in {"d1", "gliner"} or not isinstance(providers, Mapping):
        raise ValueError("provider has no supported qualified numerical contract")
    provider = providers.get(profile.provider)
    declared: dict[str, Any] = {
        "device": profile.device,
        "dtype": profile.dtype,
        "numerical_contract": "native-cuda-" + profile.dtype + "-batch-observation-v1",
    }
    if profile.provider == "d1":
        declared["cpu_allowed"] = False
    if not isinstance(provider, Mapping) or canonical_bytes(dict(provider)) != canonical_bytes(
        declared
    ):
        raise ValueError(
            "native profile differs from its qualified provider/device/dtype numerical contract"
        )
    # Other providers' declarations are outside this selected recipe closure.
    return {**expected, "provider": dict(provider)}


def admitted_startup_matches(observed: Mapping[str, Any], admitted: Mapping[str, Any]) -> bool:
    """Compare declared execution meaning while retaining runtime observations.

    Stream handles and the supported-pool roster (paths, order and loaded-library
    population) are process observations. Every reported pool must still satisfy
    the admitted native thread count. All other fields, including future fields,
    remain exact. Original config/receipt dictionaries and hashes are untouched.
    """
    threads = admitted.get("native_threads", {})
    limit = threads.get("intra_op") if isinstance(threads, Mapping) else None

    def semantic(startup):
        value = {key: item for key, item in startup.items() if key != "host_stream"}
        native = value.get("native_threads")
        if isinstance(native, Mapping):
            if "supported_pools" in native:
                pools = native["supported_pools"]
                if (
                    type(limit) is not int
                    or limit < 1
                    or not isinstance(pools, list)
                    or any(
                        not isinstance(pool, Mapping)
                        or type(pool.get("num_threads")) is not int
                        or pool["num_threads"] != limit
                        for pool in pools
                    )
                ):
                    return None
            value["native_threads"] = {
                key: item for key, item in native.items() if key != "supported_pools"
            }
        return value

    actual, expected = semantic(observed), semantic(admitted)
    return actual is not None and expected is not None and actual == expected


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
        provider: Annotated[Provider, "ddo:semantic"],
        runtime_identity: Annotated[dict[str, Any], "ddo:execution"],
        artifacts: Annotated[dict[str, Any], "ddo:semantic"],
        parameters: Annotated[dict[str, Any], "ddo:semantic"],
        dtype: Annotated[Literal["float32", "bfloat16"], "ddo:semantic"],
        backend: Annotated[str, "ddo:semantic"],
        threads: Annotated[int, "ddo:execution"] = 4,
        interop_threads: Annotated[int, "ddo:execution"] = 1,
        device: Annotated[Literal["cuda"], "ddo:semantic"] = "cuda",
        matmul_precision: Annotated[Literal["highest"], "ddo:semantic"] = "highest",
        cudnn_allow_tf32: Annotated[bool, "ddo:semantic"] = False,
        version: Annotated[Literal["nlp-gpu-profile-1"], "ddo:semantic"] = "nlp-gpu-profile-1",
    ):
        if provider not in _PROVIDERS or device != "cuda":
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
        return "primary"

    @property
    def content(self):
        return self._content

    @property
    def fingerprint(self):
        return sha256(self._content).hexdigest()

    def identity_projections(self, *, inference_policy: Mapping[str, Any]) -> ProfileIdentities:
        """DDO semantic/execution identities under a supplied qualified policy.

        The selected legacy wire/fingerprint remains exact. Runtime/thread fields
        remain execution determinants; result-neutrality is available only under
        the explicitly supported authentic-observation numerical contract. Adoption
        by native requests/reuse is a separate DDO-07/09 responsibility.
        """
        from inspect import signature

        from corpus_structure.semantic.data_operation_identity import (
            ProfileField,
            profile_identities,
        )

        values = self.wire
        names = set(signature(type(self).__init__).parameters) - {"self"}
        roles = _identity_roles(type(self).__init__, names)
        if values.keys() != names or any(role == "acquisition" for role in roles.values()):
            raise ValueError(
                "native profile fields differ from their complete identity declarations"
            )
        projected = [
            ProfileField(
                "inference_policy", _observation_policy(self, inference_policy), "semantic"
            )
        ]
        for name, role in roles.items():
            if name == "parameters" and self.provider == "gliner":
                from .gliner import GlinerProfile, gliner_profile_device, normalize_gliner_profile

                if not isinstance(values[name], dict) or values[name].keys() != {"gliner_profile"}:
                    raise ValueError("GLiNER identity requires its declared nested profile")
                nested = values[name]["gliner_profile"]
                nested_roles = _identity_roles(
                    GlinerProfile, {item.name for item in fields(GlinerProfile)}
                )
                included = {
                    key for key, meaning in nested_roles.items() if meaning != "acquisition"
                }
                if not isinstance(nested, dict) or nested.keys() != included:
                    raise ValueError(
                        "GLiNER nested profile fields differ from their complete "
                        "identity declarations"
                    )
                nested = normalize_gliner_profile(nested, json_input=True)
                if gliner_profile_device(nested["version"]) != self.device:
                    raise ValueError(
                        "nested GLiNER profile device differs from its qualified native profile"
                    )
                projected.append(
                    ProfileField("parameters", "declared-gliner-profile-fields-v1", "semantic")
                )
                projected.extend(
                    ProfileField(
                        "parameters.gliner_profile." + key,
                        nested[key],
                        cast(Literal["semantic", "execution"], nested_roles[key]),
                    )
                    for key in included
                )
            else:
                projected.append(
                    ProfileField(name, values[name], cast(Literal["semantic", "execution"], role))
                )
        return profile_identities(projected)

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
        return root

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


def pm2_selection(provider, assets, runtime, artifacts, *, threads=4, interop_threads=1):
    """Select the reviewed native recipe in the shared interpreter, before task reuse."""
    backends = {"d1": "d1", "hanlp": "sdpa", "maverick": "eager", "dipo": "sdpa"}
    if provider not in backends:
        raise ValueError("unsupported PM2 shared-host provider")
    return NativeSelection(
        NativeProfile(
            provider,
            runtime,
            artifacts,
            {"adapter": "pm2-native-1"},
            "bfloat16" if provider == "d1" else "float32",
            backends[provider],
            threads,
            interop_threads,
        ),
        assets,
    )


def gliner_selection(profile, runtime):
    from dataclasses import asdict

    if profile.device != "cuda":
        raise ValueError("shared GLiNER selection requires an explicit CUDA profile")
    values = asdict(profile)
    values.pop("snapshot")
    return NativeSelection(
        NativeProfile(
            "gliner",
            runtime,
            dict(profile.artifact_hashes),
            {"gliner_profile": values},
            "float32",
            "standard",
            profile.threads,
            1,
        ),
        profile.snapshot,
    )


def preflight_native_runtime(provider, assets):
    """Inspect an already prepared shared environment and assets without loading models."""
    from .pm2_worker import preflight_pm2_runtime

    root = Path(__file__).resolve().parents[5]
    project = root
    return preflight_pm2_runtime(
        python=project / ".venv/bin/python",
        script=Path(__file__).with_name("native_host_worker.py"),
        project=project,
        provider=provider,
        assets=assets,
    )


def spacy_selection(config, *, threads=4, interop_threads=1):
    """Freeze the installed model files and shared runtime without loading weights."""
    import spacy

    assets = spacy.util.get_package_path(config.model)
    artifacts = spacy_artifacts(assets)
    runtime = preflight_native_runtime("spacy", assets)["runtime_identity"]
    return NativeSelection(
        NativeProfile(
            "spacy",
            runtime,
            artifacts,
            config.model_dump(mode="json"),
            "float32",
            "cupy",
            threads,
            interop_threads,
        ),
        assets,
    )


def spacy_artifacts(assets):
    from hashlib import file_digest

    files = {}
    for path in sorted(assets.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            with path.open("rb") as stream:
                files[path.relative_to(assets).as_posix()] = file_digest(
                    stream, "sha256"
                ).hexdigest()
    return {"files": files}
