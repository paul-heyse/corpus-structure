"""Protected reference authorship and comparison across explicit native selections.

Original source selection, independently authored answers, prediction selection and
comparison recipe remain distinct. No retained frame is translated or regraded by
address inference, and this reader grants no public knowledge admission.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import cached_property

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic._data_operation_wire import WireCutSelection
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import json_context_meaning
from corpus_structure.semantic.demand_results import CutSelection, selected_record_index
from corpus_structure.semantic.native_definition_projection import read_native_definition_projection
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.refusals import SemanticRefusal


class SelectedReferenceRefusal(SemanticRefusal):
    """An explicit reference or prediction selection cannot support this comparison."""


_REFERENCE = "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference"
_SNAPSHOT = (
    "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReferenceSnapshot"
)


def _body(index, product, member=None):
    row = (
        index.mapping("kb.data_product", ("id",)).get(product)
        if member is None
        else index.mapping("kb.data_product_member", ("product_id", "member_id")).get(
            (product, member)
        )
    )
    if row is None:
        raise SelectedReferenceRefusal("reference address is outside the selected native closure")
    return row, decode_semantic_value(row["canonical_body" if member is None else "body"])


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
    if body["direction"] == "source_first" and body["output_members"]:
        raise SelectedReferenceRefusal(
            "source-first reference cannot freeze exposed prediction outputs"
        )
    if body["direction"] == "output_first" and not body["output_members"]:
        raise SelectedReferenceRefusal(
            "output-first reference requires its exact frozen output population"
        )
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
    with selected_record_index(
        connection,
        body["source_demand_id"],
        project_id=project_id,
        scope=pins["scope"],
        read_id=pins["read_id"],
        expected_cut=source_cut.identity,
        max_bytes=max_bytes,
    ) as (_, index):
        for source in body["source_members"]:
            actual, _ = _body(index, source["product_id"], source.get("member_id"))
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
        for output in body["output_members"]:
            _body(index, output["product_id"], output["member_id"])


def author_selected_references(engine, prepared, *, request):
    """Admit actual protected authored facts after checking their exact source pins."""
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value
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
    assignments: dict[str, str]
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
        self.views = {}

    @cached_property
    def product(self):
        row, body = _body(self.index, self.product_id)
        projection = read_native_definition_projection(self.prepared)
        kinds = {kind["kind"]: kind["kind_contract"] for kind in projection["kinds"]}
        owner = (
            "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations"
        )
        checked = (
            None
            if row["kind_contract"] != kinds.get(owner)
            else self.prepared.validate_json("DdoSourceAnnotations", json_bytes(body)).model_dump(
                mode="json", exclude_unset=True
            )
        )
        return checked, projection, kinds

    @cached_property
    def blocks(self):
        checked, _, _ = self.product
        result = {}
        for block in checked["blocks"] if checked is not None else ():
            result.setdefault(block["annotation"]["block_id"], []).append(block)
        return result

    @cached_property
    def authenticated_sources(self):
        prepared, index, cut, product_id = self.prepared, self.index, self.cut, self.product_id
        _, projection, _ = self.product
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
        from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
        from corpus_structure.semantic.data_operation_json import json_loads
        from corpus_structure.semantic.data_operation_model import SubjectContext
        from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource
        from corpus_structure.semantic.sentence_products import (
            retained_source_annotation_products,
            validate_source_annotations,
        )
        from corpus_structure.semantic.source_products import FrozenNativeSource

        key = json_bytes(pin)
        if key in self._sources:
            return self._sources[key]
        prepared, index, cut = self.prepared, self.index, self.cut
        checked, _, kinds = self.product
        if checked is None:
            raise SelectedReferenceRefusal("native scoring requires its nominal annotation product")
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
        model = bound_data_operation_model(prepared)
        native = validate_source_annotations(prepared, model, checked, source)
        packets, products = {}, {}
        for packet in json_loads(native.content)["members"]:
            packets.setdefault(packet["member_id"], []).append(packet)
        for product in retained_source_annotation_products(source, native):
            products.setdefault(product.block_id, []).append(product)
        self._sources[key] = source_row, source, native, packets, products
        return self._sources[key]

    def score(self, member_id, expected, source_members):
        from spacy.vocab import Vocab

        from corpus_structure.ingest.annotation_views import annotation_view
        from corpus_structure.ingest.annotations import AnnotationUnavailable

        from .native_scoring import SelectedNativeScoringQuestion, score_native

        stage = self
        question = SelectedNativeScoringQuestion.model_validate(expected)

        def unavailable(reason):
            return dict(score_native(None, question.reference), reason=reason)

        index, product_id = stage.index, stage.product_id
        checked, _projection, kinds = stage.product
        namespace = "https://corpus-structure.dev/semantic/data-operation-sentences/"
        if checked is None:
            return unavailable("native_annotation_kind_unavailable")
        member_row, member = _body(index, product_id, member_id)
        if (
            member_row["kind_contract"] != kinds.get(namespace + "DdoNativeBlock")
            or member.get("record_type") != "native_block"
        ):
            raise SelectedReferenceRefusal("native scoring requires an explicit whole-block member")
        blocks = stage.blocks.get(member["block_id"], ())
        if len(blocks) != 1:
            raise SelectedReferenceRefusal(
                "selected native block differs from its actual population"
            )
        annotation = blocks[0]["annotation"]
        if (question.projection, question.start, question.end) != (
            checked["source"]["projection"],
            annotation["block_start"],
            annotation["block_end"],
        ) or (member["start"], member["end"]) != (question.start, question.end):
            raise SelectedReferenceRefusal("native question differs from the selected whole block")
        pin = annotation["source"]
        source_row, source, _native, packets, products = stage.source(pin)
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
        packets = packets.get(member_id, ())
        if (
            len(packets) != 1
            or json_bytes(packets[0]["body"]) != json_bytes(member)
            or packets[0]["kind_contract"] != member_row["kind_contract"]
            or any(
                packets[0]["context"][name] != member_row[name]
                for name in ("subject", "subject_definition", "original_source")
            )
            or json_context_meaning(json_bytes(packets[0]["context"]["analyzed_scope"]))
            != json_context_meaning(json_bytes(member_row["analyzed_scope"]))
        ):
            raise SelectedReferenceRefusal("native block member differs from its actual parent")
        text = source.value["text"][question.start : question.end]
        if text != question.reference.text:
            raise SelectedReferenceRefusal("native gold text differs from the exact original block")
        if not question.reference.inspected:
            return score_native(None, question.reference)
        (product,) = products[member["block_id"]]
        required = (
            ("DEP",)
            if question.reference.kind == "dependencies"
            else ("SENT_START",)
            if question.reference.kind == "spans" and question.reference.span_key == "sents"
            else ()
        )
        try:
            key = json_bytes(pin), member["block_id"], required
            if key not in stage.views:
                stage.views[key] = annotation_view(product, text, Vocab(), required=required)
            view = stage.views[key]
        except AnnotationUnavailable:
            return unavailable("native_required_columns_unavailable")
        result = score_native(view.doc, question.reference)
        result["prediction_reference"] = dict(product_id=product_id, member_id=member_id)
        result["source_scope"] = dict(
            projection=question.projection, start=question.start, end=question.end
        )
        return result


def evaluate_selected_references(connection, request: SelectedReferenceEvaluationRequest):
    """Compare actual selected primary members against independent protected cases.

    The result is a pinned comparison report, with no linguistic truth claim,
    publication authority or hidden inference. Native reference custody remains
    distinct from this report's operator-managed retention.
    """
    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.declared_formal_readings import (
        SelectedCharacterizationInventories,
    )
    from corpus_structure.semantic.releases import open_release

    from .characterization_assessment import LayerProjection, _matches, graph_equal

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
    with selected_record_index(
        connection,
        request.reference_demand_id,
        project_id=request.project_id,
        scope=reference_scope,
        read_id=reference_pin.record["read_id"] if reference_pin is not None else None,
        expected_cut=reference_pin.identity if reference_pin is not None else None,
        max_bytes=request.max_bytes,
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
                for row in references.rows("ops.data_derivation_output")
                if row["product_id"] == request.reference_product_id
            }
            originals = [
                row
                for row in references.rows("ops.data_derivation_input")
                if row["derivation_id"] in episodes and row["role"] == "reference"
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
                for row in references.rows("ops.original_source_admission")
                if row["product_id"] == original["product_id"]
                and row["evidence"].get("standing") == "authored"
            }
            if (
                original_row["kind_contract"] not in source_contracts
                or json_bytes(original_body) != json_bytes(reference)
                or not any(
                    row["derivation_id"] == original["derivation_id"]
                    and row["role"] == "reference"
                    and row["admission_id"] in admissions
                    for row in references.rows("ops.data_derivation_original_support")
                )
            ):
                raise SelectedReferenceRefusal(
                    "reference snapshot differs from its authentic independently authored input"
                )
        with selected_record_index(
            connection,
            request.prediction_demand_id,
            project_id=request.project_id,
            scope=prediction_scope,
            read_id=prediction_pin.record["read_id"] if prediction_pin is not None else None,
            expected_cut=prediction_pin.identity if prediction_pin is not None else None,
            max_bytes=request.max_bytes,
        ) as (prediction_cut, predictions):
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
                for row in predictions.rows("ops.data_derivation_output")
                if row["product_id"] == request.prediction_product_id
            }
            if not producer_episodes or not any(
                row["derivation_id"] in producer_episodes and row["fate"] == "fulfilled"
                for row in predictions.rows("ops.demand_use")
            ):
                raise SelectedReferenceRefusal(
                    "prediction requires its authentic selected producing episode"
                )
            source = prediction["source"]
            if (
                source["document"] != applicability.original_source
                or source["projection"] != applicability.projection
                or json_bytes(prediction["selectors"]) != json_bytes(list(applicability.selectors))
                or not any(
                    row["original_source"] == source["document"]
                    for row in reference["source_members"]
                )
            ):
                raise SelectedReferenceRefusal(
                    "prediction source is outside the independent reference scope"
                )
            expected_cases = {
                case["case_id"] for case in reference["cases"] if case["judgment"] != "unassessed"
            }
            if not set(request.assignments) <= expected_cases or (
                reference["direction"] == "output_first"
                and set(request.assignments) != expected_cases
            ):
                raise SelectedReferenceRefusal(
                    "assessment assignments differ from the frozen assessed cases"
                )
            if reference["direction"] == "output_first":
                frozen = {
                    (row["product_id"], row["member_id"]) for row in reference["output_members"]
                }
                actual = {
                    (request.prediction_product_id, member)
                    for member in request.assignments.values()
                }
                if actual != frozen:
                    raise SelectedReferenceRefusal(
                        "output-first assessment differs from its frozen prediction population"
                    )
            products = predictions.mapping("kb.data_product", ("id",))
            inventories = SelectedCharacterizationInventories(products)
            projection = LayerProjection(
                lambda pin: inventories[DataProductReference(pin["product_id"])].payload
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
                applicability=applicability.model_dump(mode="python"),
                direction=reference["direction"],
                opportunity_denominator=len(
                    {case["opportunity_id"] for case in reference["cases"]}
                ),
                cases=cases,
                quality_claim="declared_cases_only",
                publication_authority=False,
                inference="not_run",
            )
            if source_python(reference["retained_correspondence"]) is not None:
                report["retained_correspondence"] = source_python(
                    reference["retained_correspondence"]
                )
            if len(json_bytes(report)) > request.max_bytes:
                raise SelectedReferenceRefusal(
                    "complete selected reference comparison exceeds max_bytes"
                )
            return report
