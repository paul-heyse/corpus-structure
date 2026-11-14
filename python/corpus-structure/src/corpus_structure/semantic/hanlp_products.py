"""Independent retained HanLP heads over authentic canonical sentence members."""

from __future__ import annotations

import ast
import json
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .canonical_sentences import CanonicalProduct
from .characterization_manifests import analytical_packets, append_manifest, manifest_contract
from .data_operation_outcomes import successful_return_outcome
from .data_product_reference import DataProductMemberReference, reference_inputs
from .identity import canonical_bytes
from .source_products import FrozenNativeSource, source_subject
from .types import SourceArtifact, SourceBundle

_MODEL = Path(__file__).parents[1] / "model/semantic/data-operation-hanlp.yaml"


def hanlp_product_inputs(bundle):
    from .sentence_products import sentence_product_inputs

    if "data_operation_sentences" not in {source.name for source in bundle.sources}:
        bundle = sentence_product_inputs(bundle)
    bundle = reference_inputs(bundle)
    import yaml

    name, root = "data_operation_hanlp", "data_operation_hanlp_root"
    if {name, root} & {source.name for source in bundle.sources}:
        raise ValueError("HanLP source model uses reserved schema names")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, _MODEL.read_bytes()),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    dict(id="urn:corpus:hanlp-root", name=root, imports=[bundle.root, name])
                ).encode(),
            ),
        ),
    )


def canonical_hanlp_rows(source, canonical):
    """Use explicit sentence/token membership and original offsets, never tokenize."""
    selected, value = source.value, canonical.value.model_dump(mode="json", exclude_unset=True)
    if any(value[key] != selected[key] for key in ("source", "selectors")):
        raise ValueError("HanLP canonical source/selector scope differs from original source")
    rows = analytical_packets(
        value, manifest_contract(canonical.prepared, canonical.model, "DdoCanonicalManifest")
    )
    members = {row["member_id"]: row["body"] for row in rows}
    if len(rows) != len(members) or any(
        row["member_id"] != row["body"]["local_id"] for row in rows
    ):
        raise ValueError("HanLP canonical member addresses are not unique exact local IDs")
    result = []
    used = set()
    for packet in rows:
        sentence = packet["body"]
        if sentence["record_type"] != "sentence":
            continue
        tokens = []
        for identifier in sentence["token_ids"]:
            token = members.get(identifier)
            if (
                token is None
                or token["record_type"] != "token"
                or token.get("sentence_ref") != sentence["local_id"]
                or identifier in used
            ):
                raise ValueError(
                    "HanLP requires closed distinct canonical sentence/token membership"
                )
            if not sentence["start"] <= token["start"] < token["end"] <= sentence["end"]:
                raise ValueError("HanLP token bounds exceed the retained canonical sentence")
            used.add(identifier)
            word = selected["text"][token["start"] : token["end"]]
            if word.strip():
                tokens.append((identifier, word))
        if tokens:
            result.append((sentence, tokens))
    return result


def _local(sentence, kind, address):
    return sha256(canonical_bytes(dict(sentence=sentence, kind=kind, address=address))).hexdigest()


def detach_hanlp_sentence(sentence, tokens, canonical, heads, preparation, vocabulary=None):
    """Preserve native conventions independently; malformed heads retain failed coverage."""
    from corpus_structure.methods.native_evidence_layers import HANLP_FAMILIES
    from corpus_structure.methods.pm2_hanlp_products import (
        _NATIVE_SRL,
        _constituency,
        _dependency_graph,
    )

    sentence_ref = DataProductMemberReference(canonical.reference, sentence["local_id"]).values()
    selector = dict(
        projection=canonical.value.source.projection, start=sentence["start"], end=sentence["end"]
    )
    references = [
        DataProductMemberReference(canonical.reference, identifier).values()
        for identifier, _ in tokens
    ]
    words = [word for _, word in tokens]
    prepared_words, spans = preparation["prepared_words"], preparation["word_subwords"]
    if (
        len(prepared_words) != len(words)
        or any(type(word) is not str for word in prepared_words)
        or len(spans) != len(words)
        or any(
            not row or any(type(index) is not int or index < 0 for index in row) for row in spans
        )
    ):
        raise ValueError("HanLP preparation differs from canonical words/subword alignment")
    flattened = [index for row in spans for index in row]
    if flattened != list(range(1, len(preparation["input_ids"]) - 1)):
        raise ValueError("HanLP subword alignment does not partition actual native input")
    alignment = dict(
        sentence=sentence_ref,
        prepared_words=prepared_words,
        word_subwords=[dict(positions=row) for row in spans],
        token_id_standing="execution-only-no-authenticated-vocabulary-namespace",
    )
    if vocabulary is not None:
        alignment.update(
            token_id_standing="authenticated-vocabulary",
            vocabulary_namespace=vocabulary,
            input_ids=preparation["input_ids"],
        )
    units: list[dict[str, Any]] = [
        dict(
            record_type="token",
            local_id=_local(sentence_ref, "token", index),
            sentence=sentence_ref,
            token=ref,
            ordinal=index,
        )
        for index, ref in enumerate(references)
    ]
    coverage = []

    def standing(family, outcome, reason=None):
        row = dict(
            family="hanlp." + family,
            eligible=[selector],
            examined=[selector],
            availability="available",
            outcome=outcome,
        )
        if reason:
            row["reason"] = reason
        coverage.append(row)

    standing("tokens", "complete")
    for family in ("lemma", "pos"):
        column = heads.get(family)
        if (
            isinstance(column, list)
            and len(column) == len(words)
            and all(type(label) is str for label in column)
        ):
            for unit, label in zip(units, column, strict=True):
                unit[family] = label
            standing(family, "complete")
        else:
            standing(family, "failed", "missing or malformed actual native head")
    try:
        _dependency_graph(heads.get("dependency"), len(words))
        for unit, (head, label) in zip(units, heads["dependency"], strict=True):
            unit.update(dependency_head=head, dependency_label=label)
        standing("dependency", "complete")
    except ValueError as error:
        standing("dependency", "failed", str(error))
    try:
        tree = heads.get("constituency")
        _constituency(tree, prepared_words)
        position = 0

        def visit(node, path):
            nonlocal position
            if isinstance(node, str):
                index = position
                position += 1
                return dict(kind="token", token=references[index])
            label, children = node
            start = position
            child_refs = [visit(child, [*path, index]) for index, child in enumerate(children)]
            identifier = _local(sentence_ref, "constituent", path)
            units.append(
                dict(
                    record_type="constituent",
                    local_id=identifier,
                    sentence=sentence_ref,
                    path=path,
                    label=label,
                    start=start,
                    end=position,
                    children=child_refs,
                    tokens=references[start:position],
                )
            )
            return dict(kind="constituent", constituent=identifier)

        visit(tree, [])
        standing("constituency", "complete")
    except (ValueError, TypeError) as error:
        standing("constituency", "failed", str(error))
    try:
        groups = _NATIVE_SRL.validate_python(heads.get("srl"))
        detached = []
        for ordinal, group in enumerate(groups):
            roles = []
            for text, label, start, end in group:
                if not label or not 0 <= start < end <= len(words):
                    raise ValueError("native SRL role exceeds exact canonical word population")
                roles.append(
                    dict(
                        native_text=text,
                        label=label,
                        start=start,
                        end=end,
                        tokens=references[start:end],
                    )
                )
            detached.append(
                dict(
                    record_type="srl_group",
                    local_id=_local(sentence_ref, "srl_group", ordinal),
                    sentence=sentence_ref,
                    ordinal=ordinal,
                    roles=roles,
                )
            )
        units.extend(detached)
        standing("srl", "complete" if groups else "empty")
    except ValueError as error:
        standing("srl", "failed", str(error))
    if {row["family"] for row in coverage} != set(HANLP_FAMILIES):
        raise ValueError("HanLP family inventory differs from owned native families")
    return units, alignment, coverage


@dataclass(frozen=True)
class HanlpProduct:
    content: bytes
    prepared: Any
    model: Any
    execution_receipts: tuple[bytes, ...] = ()

    @property
    def value(self):
        checked = self.prepared.validate_json("DdoHanlpInventory", self.content)
        analytical_packets(
            checked.model_dump(mode="json", exclude_unset=True),
            manifest_contract(self.prepared, self.model, "DdoHanlpManifest"),
        )
        return checked


@dataclass(frozen=True)
class PreparedHanlpProfile:
    prepared: Any
    model: Any
    selection: Any

    def run(self, source, canonical, *, host=None, check_active=lambda: None):
        from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
        from corpus_structure.methods.native_evidence import _native_heads
        from corpus_structure.methods.native_evidence_layers import HANLP_FAMILIES
        from corpus_structure.methods.native_host import NativeHostGroup
        from corpus_structure.settings import NemotronSettings

        rows = canonical_hanlp_rows(source, canonical)
        units, alignments, coverage, receipts = [], [], [], []
        context = dict(
            subject=source_subject(source.value["source"]),
            original_source=source.value["source"]["document"],
            analyzed_scope=dict(source=source.value["source"], selectors=source.value["selectors"]),
        )
        lifetime = (
            nullcontext(host)
            if host is not None
            else NativeHostGroup(CharacterizationExecutionPolicy(), NemotronSettings().endpoint)
        )
        if rows:
            with lifetime as active:
                active.declare((self.selection,))

                def infer(payload):
                    check_active()
                    result = active.infer_result(self.selection, payload, check_active)
                    receipts.append(canonical_bytes(asdict(result.receipt)))
                    return result.payload

                startup = active.startup(self.selection, check_active)
                ready = []
                limit = int(startup.get("max_sentences", 8))
                for offset in range(0, len(rows), limit):
                    population = rows[offset : offset + limit]
                    reply = infer(
                        dict(
                            sentences=[[word for _, word in tokens] for _, tokens in population],
                            prepare_bulk=True,
                        )
                    )
                    members = reply.get("members")
                    if (
                        reply.get("outcome") != "prepared_batch"
                        or not isinstance(members, list)
                        or len(members) != len(population)
                    ):
                        raise ValueError("HanLP admission changed canonical sentence population")
                    for ordinal, (row, member) in enumerate(zip(population, members, strict=True)):
                        if member.get("ordinal") != ordinal:
                            raise ValueError("HanLP admission changed canonical sentence order")
                        if member.get("outcome") == "prepared":
                            ready.append((row, member["row_tokens"]))
                        else:
                            ref = dict(
                                projection=source.value["source"]["projection"],
                                start=row[0]["start"],
                                end=row[0]["end"],
                            )
                            coverage.extend(
                                dict(
                                    family=family,
                                    eligible=[ref],
                                    examined=[],
                                    unexamined=[ref],
                                    availability="unsupported",
                                    outcome="unsupported",
                                    reason="native admission: " + str(member.get("reason")),
                                )
                                for family in HANLP_FAMILIES
                            )
                batches = []
                batch = []
                lengths = []
                chars = 0
                for row, length in ready:
                    size = sum(len(word) for _, word in row[1])
                    if batch and (
                        len(batch) == limit
                        or (len(batch) + 1) * max(*lengths, length)
                        > int(startup.get("max_padded_subwords", 2048))
                        or chars + size > int(startup.get("max_batch_chars", 32768))
                    ):
                        batches.append(batch)
                        batch, lengths, chars = [], [], 0
                    batch.append(row)
                    lengths.append(length)
                    chars += size
                if batch:
                    batches.append(batch)
                for batch in batches:
                    words = [[word for _, word in tokens] for _, tokens in batch]
                    reply = infer(dict(sentences=words))
                    if reply.get("outcome") != "succeeded":
                        raise ValueError(
                            "admitted HanLP invocation did not produce its native heads"
                        )
                    native, preparation = reply["native"], reply["preparation"]
                    if native.get("tok") != words or len(preparation) != len(batch):
                        raise ValueError("HanLP changed native word/preparation population")
                    for index, ((sentence, tokens), sample) in enumerate(
                        zip(batch, preparation, strict=True)
                    ):
                        detached, alignment, standing = detach_hanlp_sentence(
                            sentence,
                            tokens,
                            canonical,
                            _native_heads(native, index, len(batch)),
                            sample,
                            hanlp_vocabulary_namespace(self.selection),
                        )
                        units.extend(detached)
                        alignments.append(alignment)
                        coverage.extend(standing)
        for block in canonical.value.model_dump(mode="json", exclude_unset=True)["block_coverage"]:
            if block["outcome"] in {"complete", "empty"}:
                continue
            selector = dict(
                projection=source.value["source"]["projection"],
                start=block["start"],
                end=block["end"],
            )
            if block.get("native_pointer"):
                selector["native_pointer"] = block["native_pointer"]
            coverage.extend(
                dict(
                    family=family,
                    eligible=[selector],
                    examined=[],
                    unexamined=[selector],
                    availability="unsupported",
                    outcome="unsupported",
                    reason="canonical sentence scope unexamined: "
                    + block.get("reason", "unsupported original block"),
                )
                for family in HANLP_FAMILIES
            )
        if not rows and not coverage:
            coverage = [
                dict(
                    family=family,
                    eligible=[],
                    examined=[],
                    availability="available",
                    outcome="empty",
                )
                for family in HANLP_FAMILIES
            ]
        nominal = {
            "token": "DdoHanlpToken",
            "constituent": "DdoHanlpConstituent",
            "srl_group": "DdoHanlpSrlGroup",
        }
        ids = {(item.owner, item.domain): item.key for item in self.model.identities}
        packets = [
            dict(
                member_id=unit["local_id"],
                kind_contract=ids[
                    self.prepared.index.definitions[nominal[unit["record_type"]]].iri, "kind"
                ],
                context=context,
                body=unit,
            )
            for unit in units
        ]
        value = dict(
            source=source.value["source"],
            selectors=source.value["selectors"],
            canonical=canonical.reference.values(),
            outcome="complete"
            if all(row["outcome"] in {"complete", "empty"} for row in coverage)
            else "partial",
            coverage=coverage,
            alignments=alignments,
            members=packets,
        )
        value = append_manifest(
            value, manifest_contract(self.prepared, self.model, "DdoHanlpManifest")
        )
        product = HanlpProduct(canonical_bytes(value), self.prepared, self.model, tuple(receipts))
        _ = product.value
        return product


def hanlp_vocabulary_namespace(selection):
    """Namespace native IDs by actual authenticated tokenizer/config bytes only."""
    manifest = selection.native.artifacts.get("modernbert", {}).get("files", {})
    names = {
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "added_tokens.json",
        "vocab.json",
        "vocab.txt",
        "merges.txt",
    }
    files = {name: pin["sha256"] for name, pin in manifest.items() if name in names}
    if not {"tokenizer.json", "tokenizer_config.json"} <= files.keys():
        return None
    return "hanlp-tokenizer:" + sha256(canonical_bytes(files)).hexdigest()


def prepare_hanlp_selection(assets=None):
    from corpus_structure.methods.native_profiles import pm2_selection, preflight_native_runtime
    from corpus_structure.settings import PathSettings

    assets = Path(assets) if assets is not None else PathSettings().model_cache / "pm2"
    actual = preflight_native_runtime("hanlp", assets)
    return pm2_selection("hanlp", assets, actual["runtime_identity"], actual["assets"])


def hanlp_profile_assets(selection):
    from corpus_structure.methods import pm2_hanlp, pm2_hanlp_products
    from corpus_structure.methods.native_evidence_layers import HANLP_FAMILIES, HANLP_SCHEMES
    from corpus_structure.methods.native_profiles import hanlp_observation_policy

    names = {
        "canonical_hanlp_rows",
        "_local",
        "detach_hanlp_sentence",
        "PreparedHanlpProfile",
        "hanlp_vocabulary_namespace",
    }
    module = ast.parse(Path(__file__).read_bytes())
    definitions = [
        (node.name, ast.dump(node, include_attributes=False))
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names
    ]
    return SourceArtifact(
        "hanlp/profile-assets",
        canonical_bytes(
            dict(
                definitions=definitions,
                model=_MODEL.read_bytes().hex(),
                manifests=Path(__file__)
                .with_name("characterization_manifests.py")
                .read_bytes()
                .hex(),
                provider=Path(pm2_hanlp.__file__).read_bytes().hex(),
                native_validation=Path(pm2_hanlp_products.__file__).read_bytes().hex(),
                families=HANLP_FAMILIES,
                schemes=HANLP_SCHEMES,
                profile=json.loads(
                    selection.native.identity_projections(
                        inference_policy=hanlp_observation_policy()
                    ).inference.canonical_input
                ),
            )
        ),
    )


def hanlp_provider_asset(selection):
    from corpus_structure.methods.native_profiles import hanlp_observation_policy
    from .data_operation_provider_profiles import profile_asset
    if selection is None:
        selection = prepare_hanlp_selection()
    return profile_asset("hanlp/provider-inference-profile", selection, hanlp_observation_policy())


def hanlp_provider_attestation(selection):
    from corpus_structure.methods.native_profiles import hanlp_observation_policy
    from .data_operation_provider_profiles import profile_attestation
    if selection is None:
        selection = prepare_hanlp_selection()
    return profile_attestation(selection, hanlp_observation_policy())


def hanlp_execution_custody(selection=None):
    root = Path(__file__).parent
    paths = (
        Path(__file__),
        root / "data_operation_prepared_products.py",
        root / "data_operation_ports.py",
        root.parent / "methods/native_profiles.py",
    )
    return SourceArtifact(
        "hanlp/execution-custody",
        canonical_bytes(
            dict(
                files=[(path.name, path.read_bytes().hex()) for path in paths],
                selection=selection.declaration() if selection is not None else None,
                provider_profile=hanlp_provider_attestation(selection),
            )
        ),
    )


def hanlp_operation_sources(selection, *, sentence_configuration=None, include_dependencies=True):
    from .python_operation_sources import PythonSource, PythonSourceCollection

    path = Path(__file__).parents[1] / "methods/hanlp_evidence.py"
    own = PythonSourceCollection(
        (
            PythonSource(
                "corpus_structure.semantic.hanlp_products",
                Path(__file__).read_bytes(),
                str(Path(__file__)),
            ),
            PythonSource("corpus_structure.methods.hanlp_evidence", path.read_bytes(), str(path)),
        ),
        boundary_contracts=(hanlp_profile_assets(selection), hanlp_execution_custody(selection), hanlp_provider_asset(selection)),
    )
    if not include_dependencies:
        return own
    from .canonical_sentences import canonical_sentence_operation_sources
    from .primary_operations import combine_primary_sources

    return combine_primary_sources(
        canonical_sentence_operation_sources(sentence_configuration=sentence_configuration), own
    )


def execute_hanlp_profile(receiver, source, canonical):
    return receiver.profile.run(
        source, canonical, host=receiver.host, check_active=receiver.check_active
    )


@dataclass(frozen=True)
class PreparedHanlpPort:
    identity: Any
    operation: Any
    profile: PreparedHanlpProfile
    authorize: Any
    custody: tuple
    sources: Any
    host: Any = None

    @property
    def native_selections(self):
        return (self.profile.selection,)

    def _verify(self):
        from corpus_structure.methods.hanlp_evidence import HanlpEvidenceOperation
        from corpus_structure.methods.native_evidence import _native_heads
        from corpus_structure.methods.pm2_hanlp_products import _constituency, _dependency_graph

        from .data_operation_prepared_products import verify_prepared_product

        from .data_operation_provider_profiles import operation_profile
        profile = operation_profile(self.operation, self.sources.boundary_contracts)
        if profile is None or profile["identity"] != hanlp_provider_attestation(self.profile.selection)["identity"]:
            raise ValueError("acquired HanLP provider differs from captured semantic profile")
        verify_prepared_product(
            self.identity,
            self.profile.model,
            self.operation,
            self.sources,
            self.custody,
            assets=(
                hanlp_profile_assets(self.profile.selection),
                hanlp_execution_custody(self.profile.selection),
            ),
            functions=(
                (self.operation.callable_surfaces[0].declaration, HanlpEvidenceOperation.run),
                (
                    "corpus_structure.semantic.hanlp_products.execute_hanlp_profile",
                    execute_hanlp_profile,
                ),
                (
                    "corpus_structure.semantic.hanlp_products.PreparedHanlpProfile.run",
                    PreparedHanlpProfile.run,
                ),
                (
                    "corpus_structure.semantic.hanlp_products.detach_hanlp_sentence",
                    detach_hanlp_sentence,
                ),
                (
                    "corpus_structure.semantic.hanlp_products.canonical_hanlp_rows",
                    canonical_hanlp_rows,
                ),
                ("corpus_structure.methods.native_evidence._native_heads", _native_heads),
                (
                    "corpus_structure.methods.pm2_hanlp_products._dependency_graph",
                    _dependency_graph,
                ),
                ("corpus_structure.methods.pm2_hanlp_products._constituency", _constituency),
            ),
            authorize=self.authorize,
            required_sources=hanlp_operation_sources(
                self.profile.selection, include_dependencies=False
            ),
        )

    def _inputs(self, values, binding):
        from .data_operation_identity import decode_semantic_value
        from .data_operation_ports import PortRefusal, PythonRoleValue, _untrusted_value

        roles = [role for role in self.operation.roles if role.direction == "input"]
        ids = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        if (
            len(values) != 2
            or any(not isinstance(value, PythonRoleValue) for value in values)
            or {value.role for value in values} != {role.name for role in roles}
        ):
            raise PortRefusal("HanLP requires exactly its typed source and canonical roles")
        selected = {value.role: value for value in values}
        if any(selected[role.name].kind_contract != ids[role.kind, "kind"] for role in roles):
            raise PortRefusal("HanLP input nominal contract differs")
        source = FrozenNativeSource.acquire(
            self.profile.prepared, _untrusted_value(selected["source"].value)
        )
        supplied = selected["canonical"].value
        content = (
            supplied.content
            if isinstance(supplied, CanonicalProduct)
            else canonical_bytes(_untrusted_value(supplied))
        )
        context = supplied.subject_context if isinstance(supplied, CanonicalProduct) else None
        member = None
        if binding is not None:
            from .data_operation_model import SubjectContext

            if binding.subject_context is None:
                raise PortRefusal("HanLP canonical input requires acquired context")
            role = next(role for role in binding.roles if role.role == "canonical")
            if len(role.members) != 1 or role.members[0].member is not None:
                raise PortRefusal("HanLP requires one whole canonical product")
            member = role.members[0]
            context = SubjectContext(
                binding.subject_context.project_id,
                member.subject,
                member.original_source,
                member.analyzed_scope,
            )
        canonical = CanonicalProduct(
            content,
            self.profile.prepared,
            self.profile.model,
            self.profile.prepared.index.definitions["DdoCanonicalSentences"].iri,
            context,
        )
        if member is not None and canonical.reference.product_id != member.product:
            raise PortRefusal("HanLP canonical body differs from selected native product")
        canonical_hanlp_rows(source, canonical)
        if binding is not None and (
            not binding.sufficient
            or binding.operation != self.operation.semantic_id
            or binding.definition != self.identity.definition
            or binding.eligibility != self.identity.eligibility
            or binding.subject != source_subject(source.value["source"])
            or decode_semantic_value(json.loads(binding.parameters)) != {}
        ):
            raise PortRefusal("HanLP inputs differ from exact frozen binding")
        return source, canonical

    def _complete(self, product):
        from .data_operation_identity import semantic_value
        from .data_operation_ports import PortCompletion, RoleValue, project_product_members

        output = next(role for role in self.operation.roles if role.direction == "output")
        kind = next(
            item.key
            for item in self.profile.model.identities
            if item.owner == output.kind and item.domain == "kind"
        )
        typed = product.value.model_dump(mode="python", exclude_unset=True)
        return PortCompletion(
            self.operation.semantic_id,
            (
                RoleValue(
                    output.name,
                    kind,
                    product.content,
                    canonical_bytes(semantic_value(typed)),
                    project_product_members(self.profile.model, output.kind, typed),
                ),
            ),
            execution_evidence=canonical_bytes(
                [json.loads(receipt) for receipt in product.execution_receipts]
            ),
            outcome=successful_return_outcome(self.operation),
        )

    def invoke_python(self, values, *, binding=None, check_active=lambda: None):
        from corpus_structure.methods.hanlp_evidence import HanlpEvidenceOperation

        self._verify()
        source, canonical = self._inputs(values, binding)
        product = HanlpEvidenceOperation(self.profile, check_active, self.host).run(
            source, canonical
        )
        self._verify()
        return self._complete(product)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from corpus_structure.core.method import PreparedWork
        from corpus_structure.methods.hanlp_evidence import HanlpEvidenceOperation

        self._verify()
        source, canonical = self._inputs(values, binding)

        def compute():
            self._verify()
            result = HanlpEvidenceOperation(
                self.profile, check_active, execution_owner.native_hosts
            ).run(source, canonical)
            self._verify()
            return self._complete(result)

        (completion,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        check_active()
        self._verify()
        return completion


def resolve_hanlp_port(
    prepared,
    model,
    operation,
    *,
    identity,
    authorize,
    custody=(),
    sources=None,
    host=None,
    selection=None,
    assets=None,
):
    from .data_operation_ports import PortRefusal

    selected = model.operation(operation)
    inputs = [role for role in selected.roles if role.direction == "input"]
    outputs = [role for role in selected.roles if role.direction == "output"]
    expected = prepared.index.definitions
    if (
        selected.capabilities.forms != ("scalar",)
        or selected.capabilities.preparation != "resource"
        or selected.capabilities.cancellation != "cooperative"
        or selected.effects
        or [(role.name, role.kind, role.parameter) for role in inputs]
        != [
            ("source", expected["DdoSelectedNativeSource"].iri, "source"),
            ("canonical", expected["DdoCanonicalSentences"].iri, "canonical"),
        ]
        or len(outputs) != 1
        or outputs[0].kind != expected["DdoHanlpInventory"].iri
    ):
        raise PortRefusal("operation lacks the exact prepared HanLP native profile")
    if selection is None:
        from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection

        captured = [artifact for artifact in custody if artifact.name == "hanlp/execution-custody"]
        if len(captured) != 1:
            raise PortRefusal("HanLP acquisition requires its frozen native selection")
        declaration = json.loads(captured[0].content)["selection"]
        if not isinstance(declaration, dict):
            raise PortRefusal("HanLP custody lacks its actual selected provider")
        native = NativeProfile.from_content(canonical_bytes(declaration["profile"]))
        if native.fingerprint != declaration["fingerprint"]:
            raise PortRefusal("HanLP captured selection fingerprint differs")
        selection = NativeSelection(native, Path(declaration["assets"]))
        if assets is not None and Path(assets).absolute() != selection.assets.absolute():
            raise PortRefusal("HanLP acquisition path differs from captured custody")
    profile = PreparedHanlpProfile(prepared, model, selection)
    port = PreparedHanlpPort(
        identity,
        selected,
        profile,
        authorize,
        custody,
        sources if sources is not None else hanlp_operation_sources(selection),
        host,
    )
    port._verify()
    return port
