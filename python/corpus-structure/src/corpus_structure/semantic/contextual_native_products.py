"""Current contextual source hypotheses consume actual selected native products once."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from .construction_products import CharacterizationSnapshot, InterpretedProduct
from .declared_record_sources import DeclaredNativeFrameSource
from .identity import canonical_bytes
from .source_products import FrozenNativeSource


@dataclass(frozen=True)
class ContextualNativeProduct(InterpretedProduct):
    kind_name: ClassVar[str] = "DdoContextualNativeProduct"
    manifest_name: ClassVar[str] = "DdoContextualManifest"


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
    from .data_product_reference import DataProductReference
    from .model_characterization import declared_model_dependencies
    from .observations import source_python
    from .source_products import source_subject

    selected = source.value
    if frame.value != selected:
        raise ValueError("contextual kernel changes the selected original source")
    dependencies = declared_model_dependencies(products, frame)
    population = {}
    native_complete, native_unexamined = {}, []
    for provider, snapshot in (("maverick", maverick), ("dipo", dipo)):
        body = json.loads(snapshot.content)
        if body["source"] != selected["source"] or body["selectors"] != selected["selectors"]:
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
            selected["source"],
            {"selectors": list(context.focal)},
            {"key": "text.contextual_native/source-native", "assets": assets},
            context,
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
        for name, rows in (
            ("occurrences", builder.occurrences.values()),
            ("annotations", builder.annotations),
            ("memberships", builder.memberships),
            ("roles", builder.roles),
            ("terms", builder.terms),
            ("choices", builder.choices),
        ):
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
        eligible = selected["selectors"]
        if not rows:
            complete = not selected["text"].strip()
            combined.append(
                {
                    "family": family,
                    "eligible": eligible,
                    "examined": eligible if complete else [],
                    "unexamined": [] if complete else eligible,
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
                "eligible": eligible,
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
        "subject": source_subject(selected["source"]),
        "original_source": selected["source"]["document"],
        "analyzed_scope": {"source": selected["source"], "selectors": selected["selectors"]},
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
        "source": selected["source"],
        "selectors": selected["selectors"],
        "coverage": combined,
        "outcome": "complete"
        if all(row["outcome"] in {"complete", "empty"} for row in combined)
        else "partial",
        "dependencies": [
            DataProductReference(product.semantic_id).values()
            for product in (*products, maverick, dipo)
        ],
        "members": members,
    }
    return append_manifest(value, contracts["contextual_manifest"])


def execute_contextual_native(receiver, source, formal, constructions, maverick, dipo):
    return receiver.profile.run(source, formal, constructions, maverick, dipo)


def execute_contextual_native_kernel(
    source: FrozenNativeSource,
    frame: DeclaredNativeFrameSource,
    products: tuple[CharacterizationSnapshot, ...],
    maverick: CharacterizationSnapshot,
    dipo: CharacterizationSnapshot,
    contracts: dict[str, str],
    assets: str,
    check_active: Callable[[], None],
) -> dict[str, Any]:
    from corpus_structure.methods.learned_primary import ContextualNativePrimaryOperation

    class BoundKernel:
        def run(self, source, formal, constructions, maverick_value, dipo_value):
            return contextual_native_values(
                source,
                frame,
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
    selections: Any
    threshold: float
    max_context_chars: int
    native_selections = ()

    def _verify(self):
        from corpus_structure.methods.learned_primary import ContextualNativePrimaryOperation

        from .data_operation_prepared_products import verify_prepared_product
        from .learned_primary import learned_execution_custody, learned_profile_assets

        verify_prepared_product(
            self.identity,
            self.model,
            self.operation,
            self.sources,
            self.custody,
            assets=(
                learned_profile_assets(
                    self.selections,
                    threshold=self.threshold,
                    max_context_chars=self.max_context_chars,
                ),
                learned_execution_custody(
                    self.selections,
                    threshold=self.threshold,
                    max_context_chars=self.max_context_chars,
                ),
            ),
            functions=(
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
                (
                    "corpus_structure.semantic.contextual_native_products.execute_contextual_native_kernel",
                    execute_contextual_native_kernel,
                ),
            ),
            authorize=self.authorize,
            required_sources=self.sources,
        )

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from .construction_products import (
            interpreted_member_contracts,
            validate_interpreted_product,
        )
        from .data_operation_cpu import PythonCPUDescriptor, plan_cpu_call
        from .data_operation_identity import semantic_value
        from .data_operation_ports import (
            PortCompletion,
            PortRefusal,
            RoleValue,
            _untrusted_value,
            project_product_members,
        )
        from .learned_primary import _FILES, _ROOT, learned_profile_assets

        self._verify()
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
            source.value,
            selected["source"],
            project=binding.subject_context.project_id,
        )
        snapshots = {
            name: CharacterizationSnapshot(selected[name].product, canonical_bytes(value))
            for name, value in inputs.items()
        }
        args = dict(
            source=source,
            frame=frame,
            products=(snapshots["formal"], snapshots["constructions"]),
            maverick=snapshots["maverick"],
            dipo=snapshots["dipo"],
            contracts=interpreted_member_contracts(self.prepared, self.model),
            assets=learned_profile_assets(
                self.selections, threshold=self.threshold, max_context_chars=self.max_context_chars
            ).digest,
            check_active=check_active,
        )
        signature = inspect.signature(execute_contextual_native_kernel, eval_str=True)
        files = tuple(
            (
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                str((_ROOT / name).resolve()),
                (_ROOT / name).read_bytes(),
            )
            for name in _FILES
        )
        descriptor = PythonCPUDescriptor(
            files,
            "corpus_structure.semantic.contextual_native_products.execute_contextual_native_kernel",
            (),
            verification="prepared-kernel",
            control_parameter="check_active",
        )
        reply = yield from plan_cpu_call(
            descriptor,
            signature.bind(**args),
            signature,
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
            subject_context=binding.subject_context,
        )
        output = next(role for role in self.operation.roles if role.direction == "output")
        body = product.value.model_dump(mode="python", exclude_unset=True)
        return PortCompletion(
            self.operation.semantic_id,
            (
                RoleValue(
                    output.name,
                    ids[output.kind, "kind"],
                    product.content,
                    canonical_bytes(semantic_value(body)),
                    project_product_members(self.model, output.kind, body),
                ),
            ),
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
        )


def resolve_contextual_native_port(
    prepared, model, operation, *, identity, authorize, custody, sources
):
    from .learned_primary import resolve_learned_selections

    selected = model.operation(operation)
    if selected.semantic_id != "text.contextual_native/source-native" or selected.effects:
        raise ValueError("contextual native factory differs from its declared source owner")
    selections, threshold, max_context_chars = resolve_learned_selections(custody)
    port = PreparedContextualNativePort(
        identity,
        selected,
        prepared,
        model,
        authorize,
        custody,
        sources,
        selections,
        threshold,
        max_context_chars,
    )
    port._verify()
    return port
