"""Independent retained HanLP heads over authentic canonical sentence members."""

from __future__ import annotations

import ast
import json
from collections.abc import Mapping
from contextlib import nullcontext
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, ClassVar

from .canonical_sentences import CanonicalProduct
from .characterization_manifests import append_manifest, manifest_contract
from .data_operation_outcomes import successful_return_outcome
from .data_product_reference import reference_inputs
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
    existing = {source.name: source.content for source in bundle.sources}
    if name in existing:
        if existing[name] != _MODEL.read_bytes():
            raise ValueError("HanLP source model differs from its acquired owner")
        return bundle
    if root in existing:
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
    """Acquire closed block-local membership and recover original pretokenized words."""
    return canonical_hanlp_rows_from_blocks(source, canonical.value, canonical.partition_blocks)


def canonical_hanlp_rows_from_blocks(source, header, blocks):
    """Interpret acquired block rows against their exact source."""
    from .data_product_reference import SemanticReference
    from .sentence_partitions import COLLECTION

    selected = source.value
    if header["source"] != selected["source"] or tuple(header["selectors"]) != tuple(
        selected["selectors"]
    ):
        raise ValueError("HanLP canonical source/selector scope differs from original source")
    result = []
    for block in blocks:
        if not 0 <= block.start <= block.end <= len(selected["text"]):
            raise ValueError("HanLP canonical block exceeds its selected original source")
        addresses = set()
        tokens = {}
        sentences = {}
        for item in block.rows:
            address = item["record_type"], item["ordinal"]
            if (
                address in addresses
                or not 0 <= item["start"] < item["end"] <= block.end - block.start
            ):
                raise ValueError("HanLP canonical address or span is invalid")
            addresses.add(address)
            if item["record_type"] == "sentence":
                sentences[item["ordinal"]] = item
            elif (owner := item.get("sentence")) is not None:
                tokens.setdefault(owner, []).append(item)
        if tokens.keys() - sentences.keys():
            raise ValueError("HanLP requires exact local canonical sentence membership")
        for ordinal, sentence in sentences.items():
            start, end = block.start + sentence["start"], block.start + sentence["end"]
            words, extents = [], []
            for token in tokens.get(ordinal, ()):
                lo, hi = block.start + token["start"], block.start + token["end"]
                if not start <= lo < hi <= end:
                    raise ValueError("HanLP token bounds exceed the canonical sentence")
                if (word := selected["text"][lo:hi]).strip():
                    extents.append((lo, hi))
                    words.append(
                        (
                            SemanticReference.item(
                                "canonical", COLLECTION, block.key, ("token", token["ordinal"])
                            ).values(),
                            word,
                        )
                    )
            if words:
                result.append(
                    (
                        dict(
                            sentence,
                            start=start,
                            end=end,
                            block_id=block.key,
                            placement=(block.start, block.end),
                            block_order=block.ordinal,
                            token_extents=tuple(extents),
                            reference=SemanticReference.item(
                                "canonical", COLLECTION, block.key, ("sentence", ordinal)
                            ).values(),
                        ),
                        words,
                    )
                )
    return result


def verify_hanlp_sentence_alignment(sentence, tokens, units, alignment):
    """Verify exact canonical token order and the published span references."""
    if alignment["sentence"] != sentence or len(alignment["prepared_words"]) != len(tokens):
        raise ValueError("HanLP subword alignment differs from its canonical sentence")
    if [unit["token"] for unit in units if unit["record_type"] == "token"] != tokens:
        raise ValueError("HanLP tokens differ from exact canonical non-whitespace tokens")
    for unit in units:
        if unit["sentence"] != sentence:
            raise ValueError("HanLP unit refers to another canonical sentence")
        if unit["record_type"] == "constituent":
            spans = [unit]
        elif unit["record_type"] == "srl_group":
            spans = unit["roles"]
        else:
            continue
        for span in spans:
            start, end = span["start"], span["end"]
            if not 0 <= start < end <= len(tokens) or span["tokens"] != tokens[start:end]:
                raise ValueError("HanLP unit span differs from its canonical token references")


def hanlp_coverage_outcome(coverage):
    """Every processed or unavailable scope has one standing per native family."""
    from corpus_structure.methods.native_evidence_layers import HANLP_FAMILIES

    width = len(HANLP_FAMILIES)
    if not coverage or len(coverage) % width:
        raise ValueError("HanLP coverage differs from its native family roster")
    for start in range(0, len(coverage), width):
        scope = coverage[start : start + width]
        if {row["family"] for row in scope} != set(HANLP_FAMILIES) or any(
            row["eligible"] != scope[0]["eligible"] for row in scope
        ):
            raise ValueError("HanLP coverage differs from its native family roster or scope")
    return (
        "complete"
        if all(row["outcome"] in {"complete", "empty"} for row in coverage)
        else "partial"
    )


def detach_hanlp_sentence(sentence, tokens, canonical, heads, preparation, vocabulary=None):
    """Preserve native conventions independently; malformed heads retain failed coverage."""
    from corpus_structure.methods.pm2_hanlp_products import (
        _NATIVE_SRL,
        _constituency,
        _dependency_graph,
    )

    sentence_ref = sentence["reference"]
    references = [reference for reference, _ in tokens]
    selector = dict(
        projection=canonical.value["source"]["projection"],
        start=sentence["start"],
        end=sentence["end"],
    )
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
            units.append(
                dict(
                    record_type="constituent",
                    sentence=sentence_ref,
                    path=path,
                    label=label,
                    start=start,
                    end=position,
                    children=child_refs,
                    tokens=references[start:position],
                )
            )
            return dict(kind="constituent", constituent_path=path)

        visit(tree, [])
        standing("constituency", "complete")
    except (ValueError, TypeError) as error:
        standing("constituency", "failed", str(error))
    try:
        groups = _NATIVE_SRL.validate_python(heads.get("srl"))
        detached = []
        ambiguous_predicate = False
        for ordinal, group in enumerate(groups):
            if not group:
                raise ValueError("native SRL returned an empty role group")
            ambiguous_predicate |= sum(role[1] == "PRED" for role in group) != 1
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
                    sentence=sentence_ref,
                    ordinal=ordinal,
                    roles=roles,
                )
            )
        units.extend(detached)
        standing(
            "srl",
            "partial" if ambiguous_predicate else "complete" if groups else "empty",
            "native SRL group has no unique predicate" if ambiguous_predicate else None,
        )
    except ValueError as error:
        standing("srl", "failed", str(error))
    verify_hanlp_sentence_alignment(sentence_ref, references, units, alignment)
    return units, alignment, coverage


def admitted_hanlp_rows(population, reply):
    """Authenticate native admission ordinals/lengths; never cut a canonical sentence."""
    members = reply.get("members")
    if (
        reply.get("outcome") != "prepared_batch"
        or not isinstance(members, list)
        or len(members) != len(population)
    ):
        raise ValueError("HanLP admission changed canonical sentence population")
    ready, refused = [], []
    for ordinal, (row, member) in enumerate(zip(population, members, strict=True)):
        if (
            not isinstance(member, dict)
            or type(member.get("ordinal")) is not int
            or member["ordinal"] != ordinal
        ):
            raise ValueError("HanLP admission changed canonical sentence order")
        if member.get("outcome") == "prepared":
            length = member.get("row_tokens")
            if type(length) is not int or length < 1:
                raise ValueError("HanLP admission omitted actual positive native subword length")
            ready.append((row, length))
        else:
            refused.append((row, member))
    return ready, refused


def hanlp_admission_batches(rows, selection, frame_bytes):
    """Pack CPU-only admission by exact multiplexed request bytes, not inference size."""
    from corpus_structure.methods.native_host import host_request_frame_size
    from corpus_structure.methods.pm2_worker import Pm2WorkerRefused

    base = host_request_frame_size(selection, dict(sentences=[], prepare_bulk=True), frame_bytes)
    batch, size = [], base
    for row in rows:
        words = [word for _, word in row[1]]
        width = len(
            json.dumps(words, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
        )
        if base + width > frame_bytes:
            raise Pm2WorkerRefused(
                "one HanLP admission sentence exceeds its request frame byte bound"
            )
        additional = width + bool(batch)
        if batch and size + additional > frame_bytes:
            yield batch
            batch, size = [], base
            additional = width
        batch.append(row)
        size += additional
    if batch:
        yield batch


def hanlp_sentence_batches(ready, startup):
    """Bound padded native subwords and characters without changing sentence membership."""
    batches, batch, lengths, chars = [], [], [], 0
    for row, length in ready:
        size = sum(len(word) for _, word in row[1])
        if batch and (
            len(batch) == int(startup.get("max_sentences", 8))
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
    return batches


@dataclass(frozen=True)
class HanlpProduct:
    content: bytes
    partitions: tuple[bytes, ...]
    execution_receipts: tuple[bytes, ...] = ()
    prepared: Any = field(kw_only=True)
    _payload: ClassVar[Any]

    def __post_init__(self):
        from .sentence_partitions import sentence_product_payload

        if type(self.execution_receipts) is not tuple or any(
            type(receipt) is not bytes for receipt in self.execution_receipts
        ):
            raise TypeError("HanLP execution custody requires immutable receipt bytes")
        payload = sentence_product_payload(
            self.content, self.partitions, self.prepared, "DdoHanlpInventory"
        )
        object.__setattr__(self, "content", payload.content)
        object.__setattr__(self, "partitions", payload.partitions)
        object.__setattr__(self, "_payload", payload)

    @property
    def value(self) -> Mapping[str, Any]:
        if (
            "_payload" not in vars(self)
            or self.content is not self._payload.content
            or self.partitions is not self._payload.partitions
        ):
            raise TypeError("HanLP product lacks its validating acquisition")
        return self._payload.value


@dataclass(frozen=True)
class PreparedHanlpProfile:
    prepared: Any
    model: Any
    selection: Any

    def run(self, source, canonical, *, host=None, check_active=lambda: None):
        from corpus_structure.methods.native_evidence import _native_heads
        from corpus_structure.methods.native_evidence_layers import HANLP_FAMILIES
        from corpus_structure.methods.native_host import NativeHostGroup
        from corpus_structure.settings import Settings

        rows = canonical_hanlp_rows(source, canonical)
        units: list[dict[str, Any]] = []
        alignments: list[dict[str, Any]] = []
        coverage, receipts = [], []
        if rows:
            if host is None:
                settings = Settings()
                lifetime = NativeHostGroup(
                    settings.characterization_execution, settings.nemotron.endpoint
                )
            else:
                lifetime = nullcontext(host)
            with lifetime as active:
                active.declare((self.selection,))

                def infer(payload):
                    check_active()
                    result = active.infer_result(self.selection, payload, check_active)
                    receipts.append(canonical_bytes(asdict(result.receipt)))
                    return result.payload

                startup = active.startup(self.selection, check_active)
                ready = []
                for population in hanlp_admission_batches(
                    rows, self.selection, active.policy.max_native_request_bytes
                ):
                    reply = infer(
                        dict(
                            sentences=[[word for _, word in tokens] for _, tokens in population],
                            prepare_bulk=True,
                        )
                    )
                    accepted, refused = admitted_hanlp_rows(population, reply)
                    ready.extend(accepted)
                    for row, member in refused:
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
                batches = hanlp_sentence_batches(ready, startup)
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
        for block in canonical.value["block_coverage"]:
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
        return partition_hanlp_product(
            source,
            rows,
            units,
            alignments,
            coverage,
            kind_contract=manifest_contract(self.prepared, self.model, "DdoHanlpManifest"),
            receipts=tuple(receipts),
            prepared=self.prepared,
        )


def partition_hanlp_product(
    source, rows, units, alignments, coverage, *, kind_contract, prepared, receipts=()
):
    """Publish one flat population of the native heads under its canonical block placements."""
    from .data_operation_partitions import partition_header
    from .data_product_reference import SemanticReference, read_semantic_reference
    from .sentence_partitions import COLLECTION, SentenceBlock

    placements = {
        sentence["block_id"]: (sentence["block_order"], sentence["placement"])
        for sentence, _ in rows
    }
    grouped = {}
    counters = {}
    partition_rows = [
        *units,
        *({**alignment, "record_type": "alignment"} for alignment in alignments),
    ]
    for unit in partition_rows:
        reference = read_semantic_reference(unit["sentence"])
        key = reference.item_key
        if (
            reference.partition_key is None
            or key is None
            or len(key) != 2
            or key[0] != "sentence"
            or type(key[1]) is not int
        ):
            raise ValueError("HanLP output lost its canonical sentence address")
        block_key, sentence_ordinal = reference.partition_key, key[1]
        counter_key = block_key, sentence_ordinal, unit["record_type"]
        ordinal = counters.get(counter_key, 0)
        counters[counter_key] = ordinal + 1
        grouped.setdefault(block_key, []).append(
            dict(unit, ordinal=ordinal, sentence_ordinal=sentence_ordinal)
        )
    packets = []
    for index, key in enumerate(sorted(grouped, key=lambda key: placements[key][0])):
        start, end = placements[key][1]
        rows = sorted(
            grouped[key],
            key=lambda item: (
                item["sentence_ordinal"],
                item["record_type"],
                item["ordinal"],
            ),
        )
        packets.append(SentenceBlock(key, index, start, end, tuple(rows)).packet())
    header = append_manifest(
        dict(
            source=source.value["source"],
            selectors=source.value["selectors"],
            canonical_input=SemanticReference.whole("canonical").values(),
            outcome=hanlp_coverage_outcome(coverage),
            coverage=coverage,
        ),
        kind_contract,
    )
    header[COLLECTION] = partition_header(packets)
    return HanlpProduct(
        canonical_bytes(header),
        tuple(canonical_bytes(packet) for packet in packets),
        receipts,
        prepared=prepared,
    )


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


def _hanlp_asset_paths():
    from corpus_structure.methods import pm2_hanlp, pm2_hanlp_products

    return {
        "model": _MODEL,
        "manifests": Path(__file__).with_name("characterization_manifests.py"),
        "provider": Path(pm2_hanlp.__file__),
        "native_validation": Path(pm2_hanlp_products.__file__),
    }


def _hanlp_execution_paths():
    root = Path(__file__).parent
    return (
        Path(__file__),
        root / "data_operation_prepared_products.py",
        root / "data_operation_ports.py",
        root / "sentence_partitions.py",
        root / "data_operation_population.py",
        root / "population_canonical.py",
        root / "population_transfer.py",
        root.parent / "methods/native_profiles.py",
        root.parent / "methods/native_host.py",
        root.parent / "core/process_lifetime.py",
    )


def hanlp_profile_assets(selection):
    from corpus_structure.methods.native_evidence_layers import HANLP_FAMILIES, HANLP_SCHEMES
    from corpus_structure.methods.native_profiles import hanlp_observation_policy

    names = {
        "canonical_hanlp_rows",
        "hanlp_admission_batches",
        "partition_hanlp_product",
        "detach_hanlp_sentence",
        "PreparedHanlpProfile",
        "hanlp_vocabulary_namespace",
    }
    paths = _hanlp_asset_paths()
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
                **{name: path.read_bytes().hex() for name, path in paths.items()},
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
    paths = _hanlp_execution_paths()
    return SourceArtifact(
        "hanlp/execution-custody",
        canonical_bytes(
            dict(
                files=[(path.name, path.read_bytes().hex()) for path in paths],
                selection=selection.execution_custody() if selection is not None else None,
                provider_profile=hanlp_provider_attestation(selection),
            )
        ),
        runtime_transport=True,
    )


def hanlp_operation_sources(selection, *, sentence_configuration=None, include_dependencies=True):
    from .python_operation_sources import PythonSource, PythonSourceCollection

    methods = Path(__file__).parents[1] / "methods"
    path = methods / "hanlp_evidence.py"
    heads = methods / "native_evidence.py"
    products = methods / "pm2_hanlp_products.py"
    families = methods / "native_evidence_layers.py"
    own = PythonSourceCollection(
        (
            PythonSource(
                "corpus_structure.semantic.input_values",
                Path(__file__).with_name("input_values.py").read_bytes(),
                str(Path(__file__).with_name("input_values.py")),
            ),
            PythonSource(
                "corpus_structure.semantic.hanlp_products",
                Path(__file__).read_bytes(),
                str(Path(__file__)),
            ),
            PythonSource("corpus_structure.methods.hanlp_evidence", path.read_bytes(), str(path)),
            PythonSource(
                "corpus_structure.methods.native_evidence", heads.read_bytes(), str(heads)
            ),
            PythonSource(
                "corpus_structure.methods.pm2_hanlp_products", products.read_bytes(), str(products)
            ),
            PythonSource(
                "corpus_structure.methods.native_evidence_layers",
                families.read_bytes(),
                str(families),
            ),
        ),
        boundary_contracts=(
            hanlp_profile_assets(selection),
            hanlp_execution_custody(selection),
            hanlp_provider_asset(selection),
        ),
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
    _verification: Any = field(init=False, repr=False, compare=False)
    _basis: tuple = field(init=False, repr=False, compare=False)
    _asset_paths: tuple = field(init=False, repr=False, compare=False)

    @property
    def native_selections(self):
        return (self.profile.selection,)

    def __post_init__(self):
        from corpus_structure.methods.hanlp_evidence import HanlpEvidenceOperation
        from corpus_structure.methods.native_evidence import _native_heads
        from corpus_structure.methods.pm2_hanlp_products import _constituency, _dependency_graph

        from .data_operation_ports import PortRefusal
        from .data_operation_prepared_products import (
            authenticated_prepared_product,
            verify_prepared_product,
        )
        from .data_operation_provider_profiles import operation_profile
        from .file_custody import verified_file

        profile = operation_profile(self.operation, self.sources.boundary_contracts)
        if (
            profile is None
            or profile["identity"] != hanlp_provider_attestation(self.profile.selection)["identity"]
        ):
            raise PortRefusal("acquired HanLP provider differs from captured semantic profile")
        required = hanlp_operation_sources(self.profile.selection, include_dependencies=False)
        assets = tuple(
            asset
            for asset in required.boundary_contracts
            if asset.name
            in {
                "hanlp/profile-assets",
                "hanlp/execution-custody",
            }
        )
        functions = (
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
            (
                "corpus_structure.semantic.hanlp_products.verify_hanlp_sentence_alignment",
                verify_hanlp_sentence_alignment,
            ),
            (
                "corpus_structure.semantic.hanlp_products.hanlp_coverage_outcome",
                hanlp_coverage_outcome,
            ),
            (
                "corpus_structure.semantic.hanlp_products.partition_hanlp_product",
                partition_hanlp_product,
            ),
            (
                "corpus_structure.semantic.hanlp_products.admitted_hanlp_rows",
                admitted_hanlp_rows,
            ),
            (
                "corpus_structure.semantic.hanlp_products.hanlp_admission_batches",
                hanlp_admission_batches,
            ),
            (
                "corpus_structure.semantic.hanlp_products.hanlp_sentence_batches",
                hanlp_sentence_batches,
            ),
            ("corpus_structure.methods.native_evidence._native_heads", _native_heads),
            (
                "corpus_structure.methods.pm2_hanlp_products._dependency_graph",
                _dependency_graph,
            ),
            ("corpus_structure.methods.pm2_hanlp_products._constituency", _constituency),
            *(
                (
                    "corpus_structure.semantic.hanlp_products.PreparedHanlpPort." + name,
                    getattr(type(self), name),
                )
                for name in ("__post_init__", "invoke_python", "plan_python")
            ),
        )
        verify_prepared_product(
            self.identity,
            self.profile.model,
            self.operation,
            self.sources,
            self.custody,
            assets=assets,
            functions=functions,
            authorize=self.authorize,
            required_sources=required,
        )
        verification = authenticated_prepared_product(
            self.sources, functions, required_sources=required
        )
        files = {record.path.resolve(): record for record in verification.files}
        captured = {asset.name: json.loads(asset.content) for asset in assets}
        paths = _hanlp_asset_paths()
        for name, path in paths.items():
            record = verified_file(
                path, sha256(bytes.fromhex(captured["hanlp/profile-assets"][name])).hexdigest()
            )
            if (
                record.path.resolve() in files
                and files[record.path.resolve()].digest != record.digest
            ):
                raise PortRefusal("HanLP asset disagrees with captured source")
            files[record.path.resolve()] = record
        runtime = {path.name: path for path in _hanlp_execution_paths()}
        for name, encoded in captured["hanlp/execution-custody"]["files"]:
            record = verified_file(runtime[name], sha256(bytes.fromhex(encoded)).hexdigest())
            if (
                record.path.resolve() in files
                and files[record.path.resolve()].digest != record.digest
            ):
                raise PortRefusal("HanLP runtime custody disagrees with captured source")
            files[record.path.resolve()] = record
        verification.files = tuple(files.values())
        object.__setattr__(self, "_verification", verification)
        object.__setattr__(self, "_asset_paths", tuple(paths.items()))
        object.__setattr__(
            self,
            "_basis",
            tuple(
                (name, getattr(self, name))
                for name in (
                    "identity",
                    "operation",
                    "profile",
                    "authorize",
                    "custody",
                    "sources",
                    "host",
                    "_verification",
                    "_asset_paths",
                )
            ),
        )

    def _verify(self):
        from .data_operation_ports import PortRefusal

        if any(getattr(self, name) is not value for name, value in self._basis):
            raise PortRefusal("HanLP correspondence changed after acquisition")
        if tuple(_hanlp_asset_paths().items()) != self._asset_paths:
            raise PortRefusal("HanLP resource locations changed after acquisition")
        try:
            self._verification.check()
        except ValueError as error:
            raise PortRefusal("HanLP acquired custody changed: " + str(error)) from error
        self.authorize(self.identity)

    def _inputs(self, values, binding):
        from corpus_structure.semantic.input_values import _untrusted_value

        from .data_operation_ports import HydratedRoleValue, PortRefusal, PythonRoleValue
        from .data_operation_values import decode_semantic_value

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
        actual_source = selected["source"].value
        source_role = selected["source"]
        if type(source_role) is HydratedRoleValue and source_role.selected is not None:
            source = FrozenNativeSource.acquire_selected(
                self.profile.prepared, HydratedRoleValue._require_selected(source_role, binding)
            )
        else:
            source = FrozenNativeSource.acquire(
                self.profile.prepared,
                actual_source
                if isinstance(actual_source, (FrozenNativeSource, Mapping))
                else _untrusted_value(actual_source),
            )
        supplied = selected["canonical"]
        if supplied.partitioned is None:
            raise PortRefusal("HanLP requires selected canonical partitions")
        content, packets = supplied.partitioned.header, supplied.partitioned.packets
        context = None
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
                subject_definition=member.subject_definition,
            )
        canonical = CanonicalProduct(
            content,
            self.profile.prepared,
            self.profile.model,
            self.profile.prepared.index.definitions["DdoCanonicalSentences"].iri,
            context,
            partitions=packets,
            populations=supplied.partitioned.populations,
        )
        if member is not None and canonical.reference.product_id != member.product:
            raise PortRefusal("HanLP canonical body differs from selected native product")
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

    def _complete(self, product, source, canonical, binding):
        from ._data_operation_wire import WireKindContract, WireOutputMember
        from .data_operation_ports import PortCompletion
        from .established_validity import RuleObservedInput, successful_rule_attestation
        from .sentence_partitions import typed_sentence_role

        output = next(role for role in self.operation.roles if role.direction == "output")
        model = self.profile.model
        kind_contract = next(
            item.key
            for item in model.identities
            if item.owner == output.kind and item.domain == "kind"
        )
        kind = next(kind for kind in model.kinds if kind.semantic_id == output.kind)
        result = typed_sentence_role(
            output.name,
            kind_contract,
            product._payload,
            self.profile.prepared,
            kind,
        )
        attestations = ()
        if binding is not None and binding.subject_context is not None:
            from .native_source_view import thaw_native

            assert result.meaning is not None
            packet: WireOutputMember = {
                "role": output.name,
                "position": 0,
                "multiplicity": 1,
                "product": {
                    "kind_contract": WireKindContract(kind_contract),
                    "body": thaw_native(product._payload.tagged),
                    "members": thaw_native(product._payload.member_packets),
                },
            }
            observed = {
                "source": (RuleObservedInput(source.value),),
                "canonical": (RuleObservedInput(canonical.value),),
            }
            attestations = tuple(
                successful_rule_attestation(
                    rule,
                    kind,
                    self.operation.semantic_id,
                    packet,
                    binding.subject_context,
                    selected_inputs=observed,
                )
                for rule in model.rules
                if rule.id
                in {
                    "text.hanlp_native/canonical-token-and-span-alignment",
                    "text.hanlp_native/coverage",
                }
            )
        return PortCompletion(
            self.operation.semantic_id,
            (result,),
            execution_evidence=canonical_bytes(
                [json.loads(receipt) for receipt in product.execution_receipts]
            ),
            outcome=successful_return_outcome(self.operation),
            rule_attestations=attestations,
        )

    def invoke_python(self, values, *, binding=None, check_active=lambda: None):
        from corpus_structure.methods.hanlp_evidence import HanlpEvidenceOperation

        self._verify()
        source, canonical = self._inputs(values, binding)
        product = HanlpEvidenceOperation(self.profile, check_active, self.host).run(
            source, canonical
        )
        self._verify()
        return self._complete(product, source, canonical, binding)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from corpus_structure.core.method import PreparedWork
        from corpus_structure.methods.hanlp_evidence import HanlpEvidenceOperation

        source, canonical = self._inputs(values, binding)

        def compute():
            self._verify()
            result = HanlpEvidenceOperation(
                self.profile, check_active, execution_owner.native_hosts
            ).run(source, canonical)
            self._verify()
            return self._complete(result, source, canonical, binding)

        (completion,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        check_active()
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
    return port
