"""Current contextual source hypotheses consume actual selected native products once."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from hashlib import sha256
from typing import TYPE_CHECKING, Any, ClassVar

from .construction_products import CharacterizationSnapshot, InterpretedProduct
from .declared_record_sources import DeclaredNativeFrameSource
from .identity import canonical_bytes
from .source_products import FrozenNativeSource

if TYPE_CHECKING:
    from .data_operation_cpu import PythonCPUDescriptor
    from .runtime_slice import AuthenticatedSlice


@dataclass(frozen=True, init=False)
class ContextualNativeProduct(InterpretedProduct):
    kind_name: ClassVar[str] = "DdoContextualNativeProduct"
    manifest_name: ClassVar[str] = "DdoContextualManifest"

    @staticmethod
    def manifest_projection(value):
        # Native dependency custody belongs to the parent inventory; the contextual
        # manifest exposes only the characterized source and coverage view.
        return {key: item for key, item in value.items() if key != "dependencies"}


def contextual_native_values(
    source: FrozenNativeSource,
    frame: DeclaredNativeFrameSource,
    products: tuple[CharacterizationSnapshot, ...],
    maverick: CharacterizationSnapshot,
    dipo: CharacterizationSnapshot,
    contracts: dict[str, str],
    assets: str,
    check_active: Callable[[], None],
) -> dict[str, Any]:
    from .characterization_manifests import append_manifest
    from .contextual_characterization import (
        CONTEXT_FAMILIES,
        ContextInput,
        ContextPart,
        ContextualLayer,
    )
    from .contextual_proxy_references import contextual_proxy_roles, stage_contextual_proxy_support
    from .data_product_reference import DataProductReference
    from .model_characterization import declared_model_dependencies
    from .observations import source_python
    from .source_products import source_subject

    selected = source.value
    if frame.value != selected:
        raise ValueError("contextual kernel changes the selected original source")
    dependencies = declared_model_dependencies(products, frame)
    proxy_roles = contextual_proxy_roles(product.semantic_id for product in products)
    population = {}
    native_complete, native_unexamined = {}, []
    for provider, snapshot in (("maverick", maverick), ("dipo", dipo)):
        body = json.loads(snapshot.content)
        if body["source"] != selected["source"] or tuple(body["selectors"]) != tuple(
            selected["selectors"]
        ):
            raise ValueError("contextual native dependency changes original selected scope")
        native_complete[provider] = all(
            row["outcome"] in {"complete", "empty"}
            and row["availability"] == "available"
            and not row.get("unexamined")
            for row in body["coverage"]
        )
        native_unexamined.extend(
            selector for row in body["coverage"] for selector in row.get("unexamined", ())
        )
        for ordinal, raw in enumerate(body["observations"]):
            value = source_python(raw)
            if value.get("provider") != provider or "source_map" not in value:
                continue
            (piece,) = value["source_map"]["context_pieces"]
            if piece["source"] != frame.source_key:
                raise ValueError("native context map names another actual source carrier")
            extent = (piece["start"], piece["end"])
            group = population.setdefault(extent, {})
            if provider in group:
                raise ValueError("native contextual dependency repeats an original scope")
            group[provider] = (snapshot.semantic_id, ordinal, value)
    coordinate = dict(selected["source"])
    selectors = [dict(selector) for selector in selected["selectors"]]
    inventories = {
        name: {}
        for name in ("occurrences", "annotations", "memberships", "roles", "terms", "choices")
    }
    coverage: dict[str, list[dict[str, Any]]] = {family: [] for family in CONTEXT_FAMILIES}
    for (start, end), native in sorted(population.items()):
        check_active()
        context = ContextInput.build(
            (ContextPart(frame, start, end),),
            (dict(projection=frame.projection_digest, start=start, end=end),),
        )
        builder = ContextualLayer(
            coordinate,
            {"selectors": list(context.focal)},
            {"key": "text.contextual_native/source-native", "assets": assets},
            context,
            proxy_roles=proxy_roles,
        )
        builder.depend(dependencies)
        builder.structural()
        if "maverick" in native:
            product, ordinal, value = native["maverick"]
            tokens = []
            for token in value["source_map"]["tokens"]:
                if token["start"] is None or token["end"] is None:
                    raise ValueError(
                        "native contextual mention tokens lack original source positions"
                    )
                tokens.append(
                    {
                        "text": token["text"],
                        "sentence": token["sentence"],
                        "occurrences": context.occurrences(builder, token["start"], token["end"]),
                    }
                )
            builder.maverick(
                tokens, value["request"], value["native"], run=product + ":" + str(ordinal)
            )
        else:
            for family in ("maverick.mentions", "maverick.clusters"):
                builder.record(
                    family,
                    context.focal,
                    "failed",
                    "selected native mention scope was not inspected",
                )
        if "dipo" in native:
            product, ordinal, value = native["dipo"]
            builder.dipo(value["request"], value["native"], run=product + ":" + str(ordinal))
        else:
            for family in ("dipo.edus", "dipo.rst"):
                builder.record(
                    family,
                    context.focal,
                    "failed",
                    "selected native discourse scope was not inspected",
                )
        builder.hypotheses()
        for name, rows in builder.inventory().items():
            for row in rows:
                prior = inventories[name].setdefault(row["local_id"], row)
                if prior != row:
                    raise ValueError(
                        "contextual source populations disagree on one semantic member"
                    )
        for row in builder.coverage_values():
            coverage[row["family"]].append(row)
    combined = []
    for family in CONTEXT_FAMILIES:
        rows = coverage[family]
        if not rows:
            complete = not selected["text"].strip()
            combined.append(
                {
                    "family": family,
                    "eligible": selectors,
                    "examined": selectors if complete else [],
                    "unexamined": [] if complete else selectors,
                    "availability": "available" if complete else "unavailable",
                    "outcome": "empty" if complete else "partial",
                    "operation": "text.contextual_native/source-native",
                    "profile": "contextual-source-hypotheses-1",
                    **({} if complete else {"reason": "native source scopes were not inspected"}),
                }
            )
            continue
        full = all(row["outcome"] in {"complete", "empty"} for row in rows) and all(
            native_complete.values()
        )
        combined.append(
            {
                "family": family,
                "eligible": selectors,
                "examined": [selector for row in rows for selector in row["examined"]],
                "unexamined": [
                    *native_unexamined,
                    *(selector for row in rows for selector in row.get("unexamined", ())),
                ],
                "availability": "available" if full else "unknown",
                "outcome": "complete" if full else "partial",
                "operation": "text.contextual_native/source-native",
                "profile": "contextual-source-hypotheses-1",
                **(
                    {}
                    if full
                    else {
                        "reason": "; ".join(
                            dict.fromkeys(
                                row.get("reason", "incomplete native context")
                                for row in rows
                                if row["outcome"] not in {"complete", "empty"}
                            )
                        )
                        or "selected native population is incomplete"
                    }
                ),
            }
        )
    context = {
        "subject": source_subject(coordinate),
        "subject_definition": "original-source-view",
        "original_source": coordinate["document"],
        "analyzed_scope": {"source": coordinate, "selectors": selectors},
    }
    members = []
    for name, tag in (
        ("occurrences", "occurrence"),
        ("annotations", "annotation"),
        ("memberships", "membership"),
        ("roles", "role"),
        ("terms", "term"),
        ("choices", "choice"),
    ):
        for row in inventories[name].values():
            members.append(
                {
                    "member_id": row["local_id"],
                    "kind_contract": contracts[tag],
                    "context": context,
                    "body": {"record_type": tag, **row},
                }
            )
    value = {
        "source": coordinate,
        "selectors": selectors,
        "coverage": combined,
        "outcome": "complete"
        if all(row["outcome"] in {"complete", "empty"} for row in combined)
        else "partial",
        "dependencies": [
            DataProductReference(product.semantic_id).values()
            for product in (*products, maverick, dipo)
        ],
        **stage_contextual_proxy_support(members, proxy_roles),
    }
    summary = append_manifest(
        ContextualNativeProduct.manifest_projection(value), contracts["contextual_manifest"]
    )
    return {**value, "members": summary["members"]}


def execute_contextual_native(receiver, source, formal, constructions, maverick, dipo):
    return receiver.profile.run(source, formal, constructions, maverick, dipo)


def execute_contextual_native_kernel(
    source: FrozenNativeSource,
    frame: dict,
    products: tuple[CharacterizationSnapshot, ...],
    maverick: CharacterizationSnapshot,
    dipo: CharacterizationSnapshot,
    contracts: dict[str, str],
    assets: str,
    check_active: Callable[[], None],
) -> dict[str, Any]:
    from corpus_structure.methods.learned_primary import ContextualNativePrimaryOperation

    acquired_frame = DeclaredNativeFrameSource._from_worker_record(**frame, source=source)

    class BoundKernel:
        def run(self, source, formal, constructions, maverick_value, dipo_value):
            return contextual_native_values(
                source,
                acquired_frame,
                (formal, constructions),
                CharacterizationSnapshot(maverick.semantic_id, canonical_bytes(maverick_value)),
                CharacterizationSnapshot(dipo.semantic_id, canonical_bytes(dipo_value)),
                contracts,
                assets,
                check_active,
            )

    if len(products) != 2:
        raise ValueError(
            "contextual native kernel requires its actual formal and construction inputs"
        )
    return ContextualNativePrimaryOperation(BoundKernel()).run(
        source, products[0], products[1], json.loads(maverick.content), json.loads(dipo.content)
    )


@dataclass(frozen=True)
class PreparedContextualNativePort:
    identity: Any
    operation: Any
    prepared: Any
    model: Any
    authorize: Any
    custody: tuple
    sources: Any
    _verification: AuthenticatedSlice = field(init=False, repr=False, compare=False)
    _descriptor: PythonCPUDescriptor = field(init=False, repr=False, compare=False)
    _signature: inspect.Signature = field(init=False, repr=False, compare=False)
    _asset_digest: str = field(init=False, repr=False, compare=False)
    _member_contracts: tuple[tuple[str, str], ...] = field(init=False, repr=False, compare=False)
    native_selections = ()

    def __post_init__(self):
        from corpus_structure.methods.learned_primary import ContextualNativePrimaryOperation

        from .construction_products import interpreted_member_contracts
        from .data_operation_cpu import prepared_cpu_descriptor
        from .data_operation_prepared_products import (
            authenticated_prepared_product,
            verify_prepared_product,
        )
        from .file_custody import verified_file
        from .learned_primary import (
            _ROOT,
            learned_execution_custody,
            learned_profile_assets,
            resolve_learned_selections,
        )

        selections, threshold, max_context_chars = resolve_learned_selections(self.custody)
        profile = learned_profile_assets(
            selections, threshold=threshold, max_context_chars=max_context_chars
        )
        custody = learned_execution_custody(
            selections, threshold=threshold, max_context_chars=max_context_chars
        )
        entrypoint = (
            "corpus_structure.semantic.contextual_native_products.execute_contextual_native_kernel"
        )
        functions = (
            (
                self.operation.callable_surfaces[0].declaration,
                ContextualNativePrimaryOperation.run,
            ),
            (
                "corpus_structure.semantic.contextual_native_products.execute_contextual_native",
                execute_contextual_native,
            ),
            (
                "corpus_structure.semantic.contextual_native_products.contextual_native_values",
                contextual_native_values,
            ),
            (entrypoint, execute_contextual_native_kernel),
        )
        verify_prepared_product(
            self.identity,
            self.model,
            self.operation,
            self.sources,
            self.custody,
            assets=(profile, custody),
            functions=functions,
            authorize=self.authorize,
            required_sources=self.sources,
        )
        verification = authenticated_prepared_product(
            self.sources, functions, required_sources=self.sources
        )
        configuration = json.loads(profile.content)
        captured = {source.module: source.content for source in self.sources.sources}
        sources = []
        questions = bytes.fromhex(configuration["questions"])
        files = [
            verified_file(
                _ROOT / "model/semantic/characterization-questions.yaml",
                sha256(questions).hexdigest(),
            )
        ]
        for name, encoded in configuration["files"]:
            module = "corpus_structure." + name.removesuffix(".py").replace("/", ".")
            path = (_ROOT / name).resolve()
            # The declaration module contributes normalized meaning to the profile.
            # Its exact executable bytes come from the admitted operation sources.
            content = (
                captured[module] if name == "methods/learned_primary.py" else bytes.fromhex(encoded)
            )
            sources.append((module, str(path), content))
            files.append(verified_file(path, sha256(content).hexdigest()))
        verification.files = tuple(
            {file.path: file for file in (*verification.files, *files)}.values()
        )
        object.__setattr__(self, "_verification", verification)
        object.__setattr__(
            self, "_signature", inspect.signature(execute_contextual_native_kernel, eval_str=True)
        )
        object.__setattr__(self, "_asset_digest", profile.digest)
        object.__setattr__(
            self,
            "_member_contracts",
            tuple(interpreted_member_contracts(self.prepared, self.model).items()),
        )
        object.__setattr__(
            self,
            "_descriptor",
            prepared_cpu_descriptor(
                tuple(sources), entrypoint, None, tuple(file.receipt() for file in files)
            ),
        )

    def _verify(self):
        from .data_operation_ports import PortRefusal

        try:
            self._verification.check()
        except ValueError as error:
            raise PortRefusal(str(error)) from error
        self.authorize(self.identity)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from corpus_structure.semantic.input_values import _untrusted_value

        from .construction_products import validate_interpreted_product
        from .data_operation_cpu import plan_cpu_call
        from .data_operation_ports import (
            PortCompletion,
            PortRefusal,
        )

        if (
            binding is None
            or not binding.sufficient
            or binding.subject_context is None
            or binding.operation != self.operation.semantic_id
        ):
            raise PortRefusal("native contextual product needs its sufficient exact source binding")
        ids = {
            (identity.owner, identity.domain): identity.key for identity in self.model.identities
        }
        inputs = {}
        for value in values:
            role = next(
                role
                for role in self.operation.roles
                if role.name == value.role and role.direction == "input"
            )
            if value.kind_contract != ids[role.kind, "kind"]:
                raise PortRefusal("native contextual input kind differs from its admitted role")
            name = next(kind.name for kind in self.model.kinds if kind.semantic_id == role.kind)
            inputs[role.name] = self.prepared.validate_json(
                name, canonical_bytes(_untrusted_value(value.value))
            ).model_dump(mode="python", exclude_unset=True)
        source = FrozenNativeSource.acquire(self.prepared, inputs.pop("source"))
        selected = {role.role: role.members[0] for role in binding.roles}
        frame = DeclaredNativeFrameSource.acquire(
            self.prepared,
            source,
            selected["source"],
            project=binding.subject_context.project_id,
        )
        snapshots = {
            name: CharacterizationSnapshot(selected[name].product, canonical_bytes(value))
            for name, value in inputs.items()
        }
        args = dict(
            source=source,
            frame=frame.record,
            products=(snapshots["formal"], snapshots["constructions"]),
            maverick=snapshots["maverick"],
            dipo=snapshots["dipo"],
            contracts=dict(self._member_contracts),
            assets=self._asset_digest,
            check_active=check_active,
        )
        reply = yield from plan_cpu_call(
            self._descriptor,
            self._signature.bind(**args),
            self._signature,
            verify=self._verify,
            execution_owner=execution_owner,
            check_active=check_active,
        )
        product = validate_interpreted_product(
            self.prepared,
            self.model,
            json.loads(reply.content),
            source,
            (*args["products"], args["maverick"], args["dipo"]),
            product_type=ContextualNativeProduct,
            contextual_proxy_inputs={name: snapshots[name] for name in ("formal", "constructions")},
            subject_context=binding.subject_context,
        )
        output = next(role for role in self.operation.roles if role.direction == "output")
        return PortCompletion(
            self.operation.semantic_id,
            (product.publication(output.name, ids[output.kind, "kind"]),),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
        )


def resolve_contextual_native_port(
    prepared, model, operation, *, identity, authorize, custody, sources
):
    selected = model.operation(operation)
    if selected.semantic_id != "text.contextual_native/source-native" or selected.effects:
        raise ValueError("contextual native factory differs from its declared source owner")
    return PreparedContextualNativePort(
        identity, selected, prepared, model, authorize, custody, sources
    )
