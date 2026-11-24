"""Protected reference authorship and comparison across explicit native selections.

Original source selection, independently authored answers, prediction selection and
comparison recipe remain distinct. No retained frame is translated or regraded by
address inference, and this reader grants no public knowledge admission.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import ExitStack
from functools import cached_property
from itertools import islice

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic._data_operation_wire import WireCutSelection
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import json_context_meaning
from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.demand_results import CutSelection, acquired_selected_relations
from corpus_structure.semantic.native_definition_projection import read_native_definition_projection
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.refusal_types import SemanticRefusal


class SelectedReferenceRefusal(SemanticRefusal):
    """An explicit reference or prediction selection cannot support this comparison."""


_REFERENCE = "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference"
_SNAPSHOT = (
    "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReferenceSnapshot"
)


def _row(index, product, member=None):
    row = (
        index.mapping("kb.data_product", ("id",)).get(product)
        if member is None
        else index.mapping("kb.data_product_member", ("product_id", "member_id")).get(
            (product, member)
        )
    )
    if row is None:
        raise SelectedReferenceRefusal("reference address is outside the selected native closure")
    return row


def _body(index, product, member=None):
    row = _row(index, product, member)
    return row, decode_semantic_value(row["canonical_body" if member is None else "body"])


def _partition(index, product_id, collection, partition_key):
    from corpus_structure.semantic.selected_population_archive import POPULATION_HEADERS

    address = dict(product_id=product_id, collection=collection, partition_key=partition_key)
    population = index.population_archive
    rows = tuple(population.rows(POPULATION_HEADERS, **address)) if population is not None else ()
    if not rows:
        rows = tuple(index.rows_for("kb.data_product_partition", **address))
    if len(rows) != 1:
        raise SelectedReferenceRefusal(
            "reference partition is outside the exact selected native closure"
        )
    return rows[0]


def _read_exact_selected_partition(
    connection, cut, uses, *, product_id, collection, partition_key, max_bytes, item_key=None
):
    """Locate one whole-parent partition address under its actual selected cut."""
    from corpus_structure.semantic.demand_results import read_selected_answer

    pin = cut.record
    address = dict(product_id=product_id, collection=collection, partition_key=partition_key)
    lookup = address if item_key is None else {**address, "item_key": list(item_key)}
    for use_id in uses:
        result = read_selected_answer(
            connection,
            "read_selected_partitions",
            pin["demand_id"],
            project_id=pin["project_id"],
            read_id=pin["read_id"],
            scope=pin["scope"],
            use_id=use_id,
            limit=1,
            max_bytes=max_bytes,
            **lookup,
        )
        if CutSelection.from_native(result["cut"]).content != cut.content:
            raise SelectedReferenceRefusal("annotation partition changed its exact selected cut")
        rows = result["rows"]
        if result["answer_after"] is not None or len(rows) > 1:
            raise SelectedReferenceRefusal(
                "selected annotation partition repeats its exact address"
            )
        if rows:
            (row,) = rows
            if any(row.get(name) != value for name, value in address.items()):
                raise SelectedReferenceRefusal(
                    "selected annotation partition differs from its address"
                )
            return row
    return None


def _selected_partition_uses(index, demand_id, product_id):
    producers = {
        row["derivation_id"]
        for row in index.rows_for("ops.data_derivation_output", product_id=product_id)
        if row.get("member_id") is None
    }
    ranked = (
        (row["derivation_id"] not in producers, row["id"])
        for row in index.rows_for("ops.demand_use", demand_id=demand_id, fate="fulfilled")
    )
    # Prefer a direct whole producer. Another selected output can still
    # authorize the same whole parent through its retained support.
    return tuple(use_id for _, use_id in sorted(ranked))


def _restore_annotation(source, header, layout, partition, batches):
    from corpus_structure.semantic.data_operation_json import native_json_loads
    from corpus_structure.semantic.sentence_partitions import SentenceBlock
    from corpus_structure.semantic.sentence_products import (
        _annotation_block,
        _annotation_row,
        _restore_selected_annotation_rows,
        restore_selected_annotation_partition,
    )

    if "body" in partition:
        return restore_selected_annotation_partition(source, header, layout, partition)
    block = SentenceBlock(
        partition["partition_key"],
        partition["ordinal"],
        partition["placement"]["start"],
        partition["placement"]["end"],
        tuple(
            decode_semantic_value(native_json_loads(content.as_py()))
            for batch in batches
            for content in batch.column("canonical_text")
        ),
    )
    row = _annotation_row(_annotation_block(layout, block))
    (product,) = _restore_selected_annotation_rows(source, header, (row,))
    return product


def _output_address(row):
    if not isinstance(row.get("product_id"), str) or not row["product_id"]:
        raise SelectedReferenceRefusal("reference output requires a selected parent product")
    if (
        row.get("variant") == "member"
        and set(row) == {"variant", "product_id", "member_id"}
        and isinstance(row["member_id"], str)
        and row["member_id"]
    ):
        return row["product_id"], "member", row["member_id"]
    if (
        row.get("variant") == "partition"
        and set(row) == {"variant", "product_id", "collection", "partition_key"}
        and row["collection"] == "rows"
        and isinstance(row["partition_key"], str)
        and row["partition_key"]
    ):
        return row["product_id"], "partition", row["partition_key"]
    raise SelectedReferenceRefusal(
        "reference output requires one exact member or annotation partition address"
    )


def _reference_invariants(body):
    source_cut = CutSelection(json_bytes(source_python(body["source_cut"])))
    pins = source_cut.record
    if (
        source_cut.identity,
        pins["demand_id"],
        pins["read_id"],
        pins["release_id"],
        pins["runtime_id"],
    ) != (
        body["source_cut_id"],
        body["source_demand_id"],
        body["source_read_id"],
        body["source_release_id"],
        body["source_runtime_id"],
    ):
        raise SelectedReferenceRefusal(
            "reference question differs from its immutable original source cut"
        )
    if body["direction"] == "source_first" and body["output_addresses"]:
        raise SelectedReferenceRefusal(
            "source-first reference cannot freeze exposed prediction outputs"
        )
    if body["direction"] == "output_first" and not body["output_addresses"]:
        raise SelectedReferenceRefusal(
            "output-first reference requires its exact frozen output population"
        )
    addresses = [_output_address(row) for row in body["output_addresses"]]
    if len(set(addresses)) != len(addresses):
        raise SelectedReferenceRefusal("independent reference repeats an output address")
    cases = [case["case_id"] for case in body["cases"]]
    if len(set(cases)) != len(cases):
        raise SelectedReferenceRefusal("independent reference repeats a case identity")
    sources = [(row["product_id"], row.get("member_id")) for row in body["source_members"]]
    if len(set(sources)) != len(sources):
        raise SelectedReferenceRefusal("independent reference repeats a source identity")
    source_keys = {json_bytes(row) for row in body["source_members"]}
    for case in body["cases"]:
        if not {json_bytes(row) for row in case["source_members"]} <= source_keys:
            raise SelectedReferenceRefusal(
                "reference case cites outside its frozen source population"
            )
        expected = source_python(case["expected"])
        if not isinstance(expected, Mapping):
            raise SelectedReferenceRefusal(
                "reference matcher requires an explicit object expectation"
            )
        if case["matcher"] == "graph_full":
            if not {"root", "nodes"} <= expected.keys() or "graph_projection" not in case:
                raise SelectedReferenceRefusal(
                    "graph reference requires its full rooted graph and explicit comparison projection"
                )
            from .characterization_assessment import project_graph

            project_graph(expected, case["graph_projection"])
        elif case["matcher"] == "spacy_native":
            from .native_scoring import SelectedNativeScoringQuestion

            SelectedNativeScoringQuestion.model_validate(expected)
    if source_python(body["retained_correspondence"]) is not None:
        correspondence = source_python(body["retained_correspondence"])
        if (
            not isinstance(correspondence, dict)
            or not {
                "original_reference",
                "original_grade",
                "target_reference_name",
                "reviewed_by",
                "basis",
            }
            <= correspondence.keys()
            or correspondence["target_reference_name"] != body["reference_name"]
            or not correspondence["basis"]
            or not correspondence["reviewed_by"]
        ):
            raise SelectedReferenceRefusal(
                "retained reference requires explicit reviewed identity/question correspondence and its original grade"
            )


def _authenticate_reference_sources(connection, body, *, project_id, max_bytes=8388608):
    source_cut = CutSelection(json_bytes(source_python(body["source_cut"])))
    pins = source_cut.record
    if pins["project_id"] != project_id:
        raise SelectedReferenceRefusal("reference original source belongs to another project")
    with acquired_selected_relations(
        connection,
        body["source_demand_id"],
        project_id=project_id,
        scope=pins["scope"],
        read_id=pins["read_id"],
        expected_cut=source_cut.identity,
        max_bytes=max_bytes,
        retain_population_items=False,
    ) as (_, index):
        for source in body["source_members"]:
            actual = _row(index, source["product_id"], source.get("member_id"))
            if (
                any(
                    actual[key] != source[key]
                    for key in ("kind_contract", "subject", "subject_definition", "original_source")
                )
                or json_context_meaning(json_bytes(actual["analyzed_scope"])).decode()
                != source["analyzed_scope_meaning"]
            ):
                raise SelectedReferenceRefusal(
                    "reference source member differs from its native source/context"
                )
        for output in body["output_addresses"]:
            parent, variant, address = _output_address(output)
            if variant == "partition":
                if (
                    _read_exact_selected_partition(
                        connection,
                        source_cut,
                        _selected_partition_uses(index, pins["demand_id"], parent),
                        product_id=parent,
                        collection=output["collection"],
                        partition_key=address,
                        max_bytes=max_bytes,
                    )
                    is None
                ):
                    raise SelectedReferenceRefusal(
                        "reference partition is outside the exact selected native closure"
                    )
            else:
                _row(index, parent, address)


def author_selected_references(engine, prepared, *, request):
    """Admit actual protected authored facts after checking their exact source pins."""
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    if request.targets != ("reference.snapshot/declared",):
        raise SelectedReferenceRefusal("reference authoring requires its dedicated snapshot target")
    contracts = {
        kind["kind_contract"]
        for kind in read_native_definition_projection(prepared)["kinds"]
        if kind["kind"] == _REFERENCE and kind["universe"] == "evaluator"
    }
    if len(contracts) != 1:
        raise SelectedReferenceRefusal(
            "reference authoring release lacks its protected declared kind"
        )
    for selected in request.original_sources.values():
        reference = selected.reference
        if (
            reference.get("kind") != "authored-fact"
            or reference.get("kind_contract") not in contracts
        ):
            raise SelectedReferenceRefusal(
                "reference authoring accepts only the protected reference fact kind"
            )
        body = prepared.validate_json(
            "DdoSelectedReference", json_bytes(decode_semantic_value(reference["meaning_body"]))
        ).model_dump(mode="python", exclude_unset=True)
        _reference_invariants(body)
        with engine.begin() as connection:
            _authenticate_reference_sources(connection, body, project_id=request.project_id)
    return author_interpretations(engine, prepared, request=request)


class ReferenceApplicability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reference_source_release_id: str
    reference_source_cut_id: str
    prediction_release_id: str
    original_source: str
    projection: str
    selectors: tuple[dict, ...]
    basis: str = Field(min_length=1)


class SelectedReferenceEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str = Field(min_length=1)
    reference_demand_id: str = Field(min_length=1)
    reference_product_id: str = Field(min_length=1)
    prediction_demand_id: str = Field(min_length=1)
    prediction_product_id: str = Field(min_length=1)
    assignments: dict[str, str] = Field(
        description="Selected member IDs for graph and field cases, or block partition keys for native cases."
    )
    applicability: ReferenceApplicability
    reference_cut: WireCutSelection | None = None
    prediction_cut: WireCutSelection | None = None
    max_bytes: int = Field(default=8388608, ge=1024, le=67108864)

    @model_validator(mode="after")
    def validate_cut_bindings(self):
        for pin, demand in (
            (self.reference_cut, self.reference_demand_id),
            (self.prediction_cut, self.prediction_demand_id),
        ):
            if pin is not None and (pin["project_id"], pin["demand_id"]) != (
                self.project_id,
                demand,
            ):
                raise ValueError("reference comparison cut belongs to another project or demand")
        return self


class PreparedNativeReferenceScoring:
    """One evaluation's authenticated annotation/source/producer closure, without gold."""

    def __init__(self, prepared, index, cut, product_id):
        self.prepared, self.index, self.cut, self.product_id = prepared, index, cut, product_id
        self._sources = {}
        self._packets = {}
        self._batches = {}
        self._products = {}
        self.views = {}

    @cached_property
    def product(self):
        row, body = _body(self.index, self.product_id)
        projection = read_native_definition_projection(self.prepared)
        kinds = {kind["kind"]: kind["kind_contract"] for kind in projection["kinds"]}
        owner = (
            "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations"
        )
        return (body if row["kind_contract"] == kinds.get(owner) else None), projection

    @cached_property
    def blocks(self):
        checked, _ = self.product
        result = {}
        for layout in checked["block_layouts"] if checked is not None else ():
            result.setdefault(layout["annotation"]["block_id"], []).append(layout)
        return result

    @cached_property
    def authenticated_sources(self):
        prepared, index, cut, product_id = self.prepared, self.index, self.cut, self.product_id
        _, projection = self.product
        producing = {
            row["derivation_id"]
            for row in index.rows_for("ops.data_derivation_output", product_id=product_id)
        }
        selected = {
            row["derivation_id"]
            for row in index.rows_for(
                "ops.demand_use", demand_id=cut.record["demand_id"], fate="fulfilled"
            )
        }
        definition = next(
            (
                item
                for item in projection["operations"]
                if item["operation_id"] == "segment.sentences/source-native"
            ),
            None,
        )
        capability = (
            {} if definition is None else definition["support_contract"].get("capabilities", {})
        )
        factory = capability.get("prepared_factory", {})
        if (
            definition is None
            or definition["profile"] != "derivation"
            or factory.get("entrypoint")
            != "corpus_structure.methods.sentence_evidence.SentenceEvidenceOperation.acquire_port"
            or not factory.get("source_digest")
        ):
            raise SelectedReferenceRefusal("native scoring lacks its captured sentence producer")
        requests = index.mapping("ops.data_request", ("id",))
        authentic = set()
        episodes = index.mapping("ops.data_derivation", ("id",))
        for identifier in producing & selected:
            episode = episodes.get(identifier)
            if episode is None:
                continue
            request = requests.get(episode["request_id"])
            if (
                request is not None
                and request["project_id"] == cut.record["project_id"]
                and request["operation_id"] == definition["operation_id"]
                and episode["release_id"] == prepared.release_id
                and episode["recipe"] == definition["recipe"]
                and episode["outcome"] == "success"
            ):
                authentic.add(episode["id"])
        return frozenset(
            (row["product_id"], row.get("member_id"))
            for identifier in authentic
            for row in index.rows_for(
                "ops.data_derivation_input", derivation_id=identifier, role="source"
            )
        )

    def source(self, pin):
        from corpus_structure.semantic.data_operation_model import SubjectContext
        from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource
        from corpus_structure.semantic.source_products import FrozenNativeSource

        key = json_bytes(pin)
        if key in self._sources:
            return self._sources[key]
        prepared, index, cut = self.prepared, self.index, self.cut
        _, projection = self.product
        kinds = {kind["kind"]: kind["kind_contract"] for kind in projection["kinds"]}
        source_row, source_body = _body(index, pin["source_product"], pin.get("source_member"))
        source_kind = (
            "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource"
        )
        if source_row["kind_contract"] != kinds.get(source_kind):
            raise SelectedReferenceRefusal("native block source has another nominal kind")
        source = FrozenNativeSource.acquire(prepared, source_body)
        coordinate = source.value["source"]
        actual_pin = DeclaredRecordSource(
            coordinate["document"],
            coordinate["projection"],
            coordinate["section_pointer"],
            coordinate["membership"],
            SubjectContext(
                cut.record["project_id"],
                source_row["subject"],
                source_row["original_source"],
                json_bytes(source_row["analyzed_scope"]),
                subject_definition=source_row["subject_definition"],
            ),
            pin["source_product"],
            pin.get("source_member"),
            source_row["kind_contract"],
        ).pin()
        if json_bytes(pin) != json_bytes(actual_pin):
            raise SelectedReferenceRefusal(
                "native block source pin differs from selected source context"
            )
        if (pin["source_product"], pin.get("source_member")) not in self.authenticated_sources:
            raise SelectedReferenceRefusal("native block lacks its actual selected source input")
        self._sources[key] = source_row, source
        return self._sources[key]

    def acquire_partitions(self, assigned, *, max_bytes):
        import pyarrow as pa

        from corpus_structure.semantic.selected_population_archive import POPULATION_ITEMS, _schema

        checked, _ = self.product
        if checked is None:
            return
        remaining = max_bytes
        schema = _schema(POPULATION_ITEMS, self.cut.identity)
        for key, needs_items in assigned.items():
            packet = _partition(self.index, self.product_id, "rows", key)
            self._packets[key] = packet
            batches = []
            if needs_items:
                if "body" in packet:
                    remaining -= len(json_bytes(packet["body"]))
                else:
                    rows = iter(
                        self.index.population_archive.rows(
                            POPULATION_ITEMS,
                            product_id=self.product_id,
                            collection="rows",
                            partition_key=key,
                        )
                    )
                    while chunk := list(islice(rows, 64)):
                        batch = pa.RecordBatch.from_pylist(chunk, schema=schema)
                        remaining -= batch.nbytes
                        if remaining < 0:
                            raise SelectedReferenceRefusal(
                                "selected annotation items exceed max_bytes"
                            )
                        batches.append(batch)
                if remaining < 0:
                    raise SelectedReferenceRefusal("selected annotation items exceed max_bytes")
            self._batches[key] = tuple(batches)

    def score(self, partition_key, expected, source_members):
        from spacy.vocab import Vocab

        from corpus_structure.ingest.annotation_views import annotation_view
        from corpus_structure.ingest.annotations import AnnotationUnavailable

        from .native_scoring import SelectedNativeScoringQuestion, score_native

        stage = self
        question = SelectedNativeScoringQuestion.model_validate(expected)

        def unavailable(reason):
            return dict(score_native(None, question.reference), reason=reason)

        product_id = stage.product_id
        checked, _ = stage.product
        if checked is None:
            return unavailable("native_annotation_kind_unavailable")
        packet = self._packets[partition_key]
        blocks = stage.blocks.get(partition_key, ())
        if len(blocks) != 1:
            raise SelectedReferenceRefusal(
                "selected annotation block differs from its actual layout"
            )
        (layout,) = blocks
        annotation = layout["annotation"]
        if (question.projection, question.start, question.end) != (
            checked["source"]["projection"],
            annotation["block_start"],
            annotation["block_end"],
        ) or packet["placement"] != dict(start=question.start, end=question.end):
            raise SelectedReferenceRefusal("native question differs from the selected whole block")
        pin = annotation["source"]
        source_row, source = stage.source(pin)
        if not any(
            all(
                item[name] == source_row[name]
                for name in ("subject", "subject_definition", "original_source")
            )
            and item["analyzed_scope_meaning"]
            == json_context_meaning(json_bytes(source_row["analyzed_scope"])).decode()
            for item in source_members
        ):
            raise SelectedReferenceRefusal(
                "native source is outside the independent question scope"
            )
        text = source.value["text"][question.start : question.end]
        if text != question.reference.text:
            raise SelectedReferenceRefusal("native gold text differs from the exact original block")
        if not question.reference.inspected:
            return score_native(None, question.reference)
        required = (
            ("DEP",)
            if question.reference.kind == "dependencies"
            else ("SENT_START",)
            if question.reference.kind == "spans" and question.reference.span_key == "sents"
            else ()
        )
        try:
            key = json_bytes(pin), partition_key, required
            if key not in stage.views:
                if partition_key not in stage._products:
                    stage._products[partition_key] = _restore_annotation(
                        source, checked, layout, packet, stage._batches[partition_key]
                    )
                product = stage._products[partition_key]
                stage.views[key] = annotation_view(product, text, Vocab(), required=required)
            view = stage.views[key]
        except AnnotationUnavailable:
            return unavailable("native_required_columns_unavailable")
        result = score_native(view.doc, question.reference)
        result["prediction_reference"] = dict(
            variant="partition",
            product_id=product_id,
            collection="rows",
            partition_key=partition_key,
        )
        result["source_scope"] = dict(
            projection=question.projection, start=question.start, end=question.end
        )
        return result


class _PinnedEvaluationItems:
    """Acquire each newly discovered witness under the same authorized prediction cut."""

    def __init__(self, reader, cut, uses, max_bytes):
        self.reader, self.cut, self.uses, self.remaining = reader, cut, uses, max_bytes
        self._headers = {}
        self._items = {}

    def _acquire(self, product_id, collection, partition_key, *, item_key=None):
        if self.remaining <= 0:
            raise SelectedReferenceRefusal("selected annotation witnesses exceed max_bytes")
        with self.reader() as connection:
            return _read_exact_selected_partition(
                connection,
                self.cut,
                self.uses,
                product_id=product_id,
                collection=collection,
                partition_key=partition_key,
                item_key=item_key,
                max_bytes=self.remaining,
            )

    def _charge(self, value):
        self.remaining -= len(json_bytes(value))
        if self.remaining < 0:
            raise SelectedReferenceRefusal("selected annotation witnesses exceed max_bytes")

    def rows(self, relation, *, product_id, collection, partition_key):
        from corpus_structure.semantic.selected_population_archive import POPULATION_HEADERS

        if relation != POPULATION_HEADERS:
            raise ValueError("evaluation item lookup only exposes acquired population headers")
        key = product_id, collection, partition_key
        if key not in self._headers:
            row = self._acquire(*key)
            if row is None:
                return
            self._charge(row)
            self._headers[key] = row
        yield self._headers[key]

    def item(self, product_id, collection, partition_key, item_key):
        key = product_id, collection, partition_key, json_bytes(list(item_key))
        if key not in self._items:
            row = self._acquire(product_id, collection, partition_key, item_key=item_key)
            if row is None:
                raise KeyError(item_key)
            value = row["meaning_body"]
            self._charge(value)
            self._items[key] = decode_semantic_value(value)
        return self._items[key]


def evaluate_selected_references(
    reader, request: SelectedReferenceEvaluationRequest, *, on_acquire=None
):
    """Compare independently authored cases after the native acquisition commits."""
    with ExitStack() as owned:
        with reader() as connection, ExitStack() as acquiring:
            if on_acquire is not None:
                on_acquire(connection)
            facts = _acquire_comparison(connection, reader, acquiring, request)
            # Finish failed acquisition inside the transaction. Only a
            # successful acquisition transfers its owned facts to scoring.
            owned.enter_context(acquiring.pop_all())
        return _score_comparison(request, *facts)


def _acquire_comparison(connection, reader, owned, request):
    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.declared_formal_readings import (
        SelectedCharacterizationInventories,
    )
    from corpus_structure.semantic.releases import open_release

    from .characterization_assessment import (
        LayerProjection,
        SelectedAnnotationTargets,
    )

    # A pin owns its original scope. Narrowing it while retaining its read ID
    # would silently substitute a different native selection.
    reference_pin = (
        CutSelection.from_native(request.reference_cut)
        if request.reference_cut is not None
        else None
    )
    prediction_pin = (
        CutSelection.from_native(request.prediction_cut)
        if request.prediction_cut is not None
        else None
    )
    reference_scope = (
        reference_pin.record["scope"]
        if reference_pin is not None
        else {"product_ids": [request.reference_product_id]}
    )
    prediction_scope = (
        prediction_pin.record["scope"]
        if prediction_pin is not None
        else {"product_ids": [request.prediction_product_id]}
    )
    if request.reference_demand_id == request.prediction_demand_id:
        raise SelectedReferenceRefusal(
            "reference and prediction require their separate native selections"
        )
    with acquired_selected_relations(
        connection,
        request.reference_demand_id,
        project_id=request.project_id,
        scope=reference_scope,
        read_id=reference_pin.record["read_id"] if reference_pin is not None else None,
        expected_cut=reference_pin.identity if reference_pin is not None else None,
        max_bytes=request.max_bytes,
        retain_population_items=False,
    ) as (reference_cut, references):
        reference_row, reference = _body(references, request.reference_product_id)
        prepared = open_release(connection, reference_cut.record["release_id"])
        reference_projection = read_native_definition_projection(prepared)
        admitted = {
            kind["kind_contract"]
            for kind in reference_projection["kinds"]
            if kind["kind"] in {_REFERENCE, _SNAPSHOT} and kind["universe"] == "evaluator"
        }
        if reference_row["kind_contract"] not in admitted:
            raise SelectedReferenceRefusal(
                "selected reference is not a protected declared reference kind"
            )
        prepared.validate_json(
            "DdoSelectedReferenceSnapshot"
            if reference_row["kind_contract"]
            in {
                kind["kind_contract"]
                for kind in reference_projection["kinds"]
                if kind["kind"] == _SNAPSHOT
            }
            else "DdoSelectedReference",
            json_bytes(reference),
        )
        _reference_invariants(reference)
        _authenticate_reference_sources(
            connection, reference, project_id=request.project_id, max_bytes=request.max_bytes
        )
        # Native witnesses bind the complete typed authored value; this read
        # comparison independently checks its captured support and whole body.
        snapshot_contracts = {
            kind["kind_contract"]
            for kind in reference_projection["kinds"]
            if kind["kind"] == _SNAPSHOT
        }
        if reference_row["kind_contract"] in snapshot_contracts:
            episodes = {
                row["derivation_id"]
                for row in references.rows_for(
                    "ops.data_derivation_output", product_id=request.reference_product_id
                )
            }
            originals = [
                row
                for episode in episodes
                for row in references.rows_for(
                    "ops.data_derivation_input", derivation_id=episode, role="reference"
                )
            ]
            if len(originals) != 1:
                raise SelectedReferenceRefusal(
                    "reference snapshot requires its exact independently authored input"
                )
            original = originals[0]
            original_row, original_body = _body(
                references, original["product_id"], original.get("member_id")
            )
            source_contracts = {
                kind["kind_contract"]
                for kind in reference_projection["kinds"]
                if kind["kind"] == _REFERENCE
            }
            admissions = {
                row["id"]
                for row in references.rows_for(
                    "ops.original_source_admission", product_id=original["product_id"]
                )
                if row["evidence"].get("standing") == "authored"
            }
            if (
                original_row["kind_contract"] not in source_contracts
                or json_bytes(original_body) != json_bytes(reference)
                or not any(
                    row["admission_id"] in admissions
                    for row in references.rows_for(
                        "ops.data_derivation_original_support",
                        derivation_id=original["derivation_id"],
                        role="reference",
                    )
                )
            ):
                raise SelectedReferenceRefusal(
                    "reference snapshot differs from its authentic independently authored input"
                )
        prediction_cut, predictions = owned.enter_context(
            acquired_selected_relations(
                connection,
                request.prediction_demand_id,
                project_id=request.project_id,
                scope=prediction_scope,
                read_id=prediction_pin.record["read_id"] if prediction_pin is not None else None,
                expected_cut=prediction_pin.identity if prediction_pin is not None else None,
                max_bytes=request.max_bytes,
            )
        )
        _, prediction = _body(predictions, request.prediction_product_id)
        applicability = request.applicability
        if (
            reference["source_release_id"],
            reference["source_cut_id"],
            prediction_cut.record["release_id"],
        ) != (
            applicability.reference_source_release_id,
            applicability.reference_source_cut_id,
            applicability.prediction_release_id,
        ):
            raise SelectedReferenceRefusal(
                "reference source release and prediction release require exact reviewed applicability"
            )
        producer_episodes = {
            row["derivation_id"]
            for row in predictions.rows_for(
                "ops.data_derivation_output", product_id=request.prediction_product_id
            )
        }
        producer_uses = tuple(
            row["id"]
            for row in predictions.rows("ops.demand_use")
            if row["derivation_id"] in producer_episodes and row["fate"] == "fulfilled"
        )
        if not producer_uses:
            raise SelectedReferenceRefusal(
                "prediction requires its authentic selected producing episode"
            )
        source = prediction["source"]
        if (
            source["document"] != applicability.original_source
            or source["projection"] != applicability.projection
            or json_bytes(prediction["selectors"]) != json_bytes(list(applicability.selectors))
            or not any(
                row["original_source"] == source["document"] for row in reference["source_members"]
            )
        ):
            raise SelectedReferenceRefusal(
                "prediction source is outside the independent reference scope"
            )
        expected_cases = {
            case["case_id"] for case in reference["cases"] if case["judgment"] != "unassessed"
        }
        if not set(request.assignments) <= expected_cases or (
            reference["direction"] == "output_first" and set(request.assignments) != expected_cases
        ):
            raise SelectedReferenceRefusal(
                "assessment assignments differ from the frozen assessed cases"
            )
        if reference["direction"] == "output_first":
            frozen = {_output_address(row) for row in reference["output_addresses"]}
            actual = {
                (
                    request.prediction_product_id,
                    "partition" if case["matcher"] == "spacy_native" else "member",
                    request.assignments[case["case_id"]],
                )
                for case in reference["cases"]
                if case["case_id"] in request.assignments
            }
            if actual != frozen:
                raise SelectedReferenceRefusal(
                    "output-first assessment differs from its frozen prediction population"
                )
        products = predictions.mapping("kb.data_product", ("id",))
        inventories = SelectedCharacterizationInventories(
            products, index=predictions, cut=prediction_cut
        )
        payload = (
            inventories[DataProductReference(request.prediction_product_id)].payload
            if any(case["matcher"] != "spacy_native" for case in reference["cases"])
            else {}
        )
        collections = {
            row["local_id"]: collection
            for collection in (
                "terms",
                "annotations",
                "memberships",
                "occurrences",
                "roles",
                "choices",
            )
            for row in payload.get(collection, ())
        }
        native_prepared = (
            (
                prepared
                if prepared.release_id == prediction_cut.record["release_id"]
                else open_release(connection, prediction_cut.record["release_id"])
            )
            if any(case["matcher"] == "spacy_native" for case in reference["cases"])
            else None
        )
        native_scoring = (
            PreparedNativeReferenceScoring(
                native_prepared, predictions, prediction_cut, request.prediction_product_id
            )
            if native_prepared is not None
            else None
        )
        if native_scoring is not None:
            from .native_scoring import SelectedNativeScoringQuestion

            assigned = {}
            for case in reference["cases"]:
                if case["matcher"] != "spacy_native" or case["judgment"] == "unassessed":
                    continue
                partition_key = request.assignments.get(case["case_id"])
                if partition_key is not None:
                    expected = SelectedNativeScoringQuestion.model_validate(
                        source_python(case["expected"])
                    )
                    assigned[partition_key] = (
                        assigned.get(partition_key, False) or expected.reference.inspected
                    )
            native_scoring.acquire_partitions(assigned, max_bytes=request.max_bytes)
        if (live := getattr(predictions, "population_archive", None)) is not None:
            live.close()
        predictions.population_archive = _PinnedEvaluationItems(
            reader,
            prediction_cut,
            producer_uses,
            request.max_bytes,
        )
        owned.callback(setattr, predictions, "population_archive", None)
        projection = LayerProjection(
            lambda pin: inventories[DataProductReference(pin["product_id"])].payload,
            SelectedAnnotationTargets(predictions, prediction_cut),
        )
        return (
            reference,
            reference_cut,
            prediction_cut,
            source,
            collections,
            projection,
            native_scoring,
        )


def _score_comparison(
    request,
    reference,
    reference_cut,
    prediction_cut,
    source,
    collections,
    projection,
    native_scoring,
):
    from .characterization_assessment import _matches, graph_equal

    cases = []
    for case in reference["cases"]:
        member = request.assignments.get(case["case_id"])
        if case["judgment"] == "unassessed":
            cases.append(
                dict(
                    case_id=case["case_id"],
                    opportunity_id=case["opportunity_id"],
                    outcome="unassessed",
                )
            )
            continue
        if member is not None and not any(
            row["original_source"] == source["document"] for row in case["source_members"]
        ):
            raise SelectedReferenceRefusal(
                "prediction assignment cites outside the case's independent source question"
            )
        if case["matcher"] == "spacy_native":
            if member is None:
                from .native_scoring import SelectedNativeScoringQuestion, score_native

                native = score_native(
                    None,
                    SelectedNativeScoringQuestion.model_validate(
                        source_python(case["expected"])
                    ).reference,
                )
            else:
                assert native_scoring is not None
                native = native_scoring.score(
                    member, source_python(case["expected"]), case["source_members"]
                )
            cases.append(
                dict(
                    case_id=case["case_id"],
                    opportunity_id=case["opportunity_id"],
                    judgment=case["judgment"],
                    outcome=native["status"],
                    native=native,
                )
            )
            continue
        if member not in collections:
            cases.append(
                dict(
                    case_id=case["case_id"],
                    opportunity_id=case["opportunity_id"],
                    outcome="unavailable",
                    reason="selected prediction member is absent",
                )
            )
            continue
        output = dict(
            product_id=request.prediction_product_id,
            member_id=member,
            collection=collections[member],
        )
        actual = projection.project(output, include_graph=case["matcher"] == "graph_full")
        expected = source_python(case["expected"])
        matched = (
            graph_equal(actual["graph"], expected, case.get("graph_projection"))
            if case["matcher"] == "graph_full"
            else _matches(actual, expected)
        )
        cases.append(
            dict(
                case_id=case["case_id"],
                opportunity_id=case["opportunity_id"],
                prediction=output,
                judgment=case["judgment"],
                outcome="match" if matched else "mismatch",
            )
        )
    report = dict(
        format="selected-reference-comparison-v1",
        reference=dict(
            product_id=request.reference_product_id,
            cut=reference_cut.record,
            cut_id=reference_cut.identity,
            source_release_id=reference["source_release_id"],
            source_cut_id=reference["source_cut_id"],
        ),
        prediction=dict(
            product_id=request.prediction_product_id,
            cut=prediction_cut.record,
            cut_id=prediction_cut.identity,
        ),
        applicability=request.applicability.model_dump(mode="python"),
        direction=reference["direction"],
        opportunity_denominator=len({case["opportunity_id"] for case in reference["cases"]}),
        cases=cases,
        quality_claim="declared_cases_only",
        publication_authority=False,
        inference="not_run",
    )
    if source_python(reference["retained_correspondence"]) is not None:
        report["retained_correspondence"] = source_python(reference["retained_correspondence"])
    if len(json_bytes(report)) > request.max_bytes:
        raise SelectedReferenceRefusal("complete selected reference comparison exceeds max_bytes")
    return report
