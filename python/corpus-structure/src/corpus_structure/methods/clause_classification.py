"""Project exact retained linguistic function answers onto domain predicate focuses."""

import json
from hashlib import sha256
from typing import Literal, Self

from pydantic import model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.semantic.characterization import annotation_reference
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import declared_families
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.source_contexts import record_source_pin
from corpus_structure.semantic.structural_products import (
    ClauseClassificationProduct,
    ClauseFocusSelection,
    ClauseModelLabel,
    ClauseModelReading,
    LocatedDefinitionSpan,
    StructuralInput,
    StructuralProductReport,
    StructuralValue,
)

ContextPolicy = Literal["exact_focus", "adjacent_sentences"]


class ClauseClassificationConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    focuses: tuple[ClauseFocusSelection, ...] = ()
    characterization_layers: tuple[dict, ...] = ()
    context_policy: ContextPolicy = "exact_focus"

    @model_validator(mode="after")
    def bound_inputs(self) -> Self:
        if self.inputs is None:
            if (
                self.structural_input_digest is not None
                or self.focuses
                or self.characterization_layers
            ):
                raise ValueError("partial clause model configuration")
            return self
        passages = {p.passage_id for p in self.inputs.passages}
        if (
            self.structural_input_digest != self.inputs.identity
            or not self.characterization_layers
            or not self.focuses
            or len(set(self.focuses)) != len(self.focuses)
            or any(
                s.passage_id not in passages
                or s.frame.contribution_id not in self.inputs.dependencies
                for s in self.focuses
            )
        ):
            raise ValueError("clause model projection requires exact selected focuses")
        return self


def clause_focus(selection, passage, source_ref, retained, annotations=()):
    """Project the exact retained frame focus and nearest source-contained sentences."""
    (frame,) = [
        row
        for row in retained["contributions"]
        if row["contribution_id"] == selection.frame.contribution_id
    ]
    component = frame["component"]
    if (
        component["kind"] != "predicate_frame"
        or component.get("focus_state") != "exact"
        or component.get("scope") != passage.passage_id
        or component.get("effective_version") != passage.effective_version
        or frame["pin"]["source_view_id"] != source_ref.source_view_id
        or frame["pin"]["projection_digest"] != source_ref.projection_digest
    ):
        raise ValueError("classifier requires the exact retained focus under the selected passage")
    (focus_member,) = [m for m in component["frame_members"] if m["role"] == "focus"]
    (extent,) = focus_member["extents"]

    def span(start, end):
        if not passage.start <= start < end <= passage.end:
            raise ValueError("clause context is outside selected passage")
        return LocatedDefinitionSpan(
            passage_id=passage.passage_id,
            start=start,
            end=end,
            text=passage.text[start - passage.start : end - passage.start],
        )

    focus = span(extent["start"], extent["end"])
    if not annotations:
        return focus, None, None
    (block,) = [
        a
        for a in annotations
        if "annotation:" + a.dependency_digest == component["annotation"]
        and a.block_id == component["block"]
    ]
    (position,) = [
        i
        for i, sentence in enumerate(block.sentences)
        if sentence.start <= focus.start < focus.end <= sentence.end
    ]

    def neighbor(index):
        if not 0 <= index < len(block.sentences):
            return None
        sentence = block.sentences[index]
        if passage.start <= sentence.start < sentence.end <= passage.end:
            return span(sentence.start, sentence.end)
        return None

    return focus, neighbor(position - 1), neighbor(position + 1)


def model_concordance(reference, report, source_view_id, contributions, resolve_frame):
    """Cite an exact later observation while preserving the deterministic reading."""
    if report.product_id != reference.product_id or report.clause_classification is None:
        raise ValueError("retained model reference is not its exact classification product")
    passages = {p.passage_id: p for p in report.inputs.passages}
    sources = {s.identity: s for s in report.inputs.sources}
    output = []
    current_frames = {
        c["contribution_id"]: c
        for c in contributions
        if c.get("component", {}).get("kind") == "predicate_frame"
    }
    frame_keys = (
        "annotation",
        "block",
        "predicate_token",
        "variant",
        "scope",
        "effective_version",
    )

    def frame_key(frame):
        component = frame["component"]
        (focus,) = [m["extents"] for m in component["frame_members"] if m["role"] == "focus"]
        # The retained JSON array is a list, while the current producer emits a tuple.
        extents = tuple((extent["start"], extent["end"]) for extent in focus)
        return frame["pin"], tuple(component.get(k) for k in frame_keys), extents

    for row in report.clause_classification.readings:
        passage = passages[row.selection.passage_id]
        if sources[passage.source_ref].source_view_id != source_view_id:
            continue
        original = resolve_frame(row.selection.frame)
        original_key = frame_key(original)
        (current,) = [
            c["component"]
            for c in contributions
            if c.get("component", {}).get("kind") == "predicate_reading"
            and (frame := current_frames.get(c["component"]["frame"])) is not None
            and frame["component"].get("focus_state") == "exact"
            and frame_key(frame) == original_key
        ]
        predicted = {item.label for item in row.function if item.accepted}
        comparable = predicted & {"definition", "explanation"}
        if not predicted:
            comparison = "withheld"
        elif current["reading"] not in {"definition", "explanation"} or not comparable:
            comparison = "incomparable"
        else:
            comparison = "agrees" if current["reading"] in comparable else "disagrees"
        output.append(
            dict(
                reference=reference.model_dump(mode="json"),
                observation=row.model_dump(mode="json", exclude_none=True),
                deterministic_reading=current["reading"],
                comparison=comparison,
            )
        )
    return output


def primary_clause_functions(layers, prepared, source, focus, examined):
    """Read an exact released function question, preserving its actual vocabulary.

    A classification of a containing passage cannot stand for this focal clause.
    Independent retained observations are rivals; none is selected by iteration order.
    """
    families = declared_families(prepared.registry_rows)
    pin = record_source_pin(source)
    found = []
    for layer_pin, report in layers.items():
        if report.reference(layer_pin.task_id) != layer_pin:
            raise ValueError("clause functions require exact retained layer pins")
        body = report.payload
        occurrences = {row["local_id"]: row for row in body["occurrences"]}
        for annotation in body["annotations"]:
            answer = annotation.get("model_answer")
            if (
                annotation["kind"] != "model.question"
                or answer is None
                or answer["family"] not in {"character_gliner_function_v1", "character_function_v1"}
                or answer["question_key"] != "functions"
            ):
                continue
            family = families.get(answer["family"])
            if family is None or answer["declaration_digest"] != family.digest:
                continue
            extents = [
                part for key in annotation["occurrences"] for part in occurrences[key]["extents"]
            ]
            if len(extents) != 1 or any(
                extents[0].get(key) != expected
                for key, expected in dict(
                    source_view_id=source.source_view_id,
                    projection=source.projection_digest,
                    start=focus.start,
                    end=focus.end,
                    text=focus.text,
                    synthetic=False,
                ).items()
            ):
                continue
            native = source_python(answer["native_answer"])
            if not isinstance(native, dict) or not isinstance(native.get("request"), dict):
                continue
            request = native["request"]
            if answer["answer_kind"] == "gliner_classification":
                scope = request.get("assessed_scope", {})
                request_digest_ = sha256(canonical_bytes(request)).hexdigest()
                focal = scope.get("projection_extent")
                if (
                    examined != (focus.start, focus.end)
                    or request.get("declaration_digest") != family.digest
                    or request.get("item", {}).get("text") != focus.text
                ):
                    continue
            elif answer["answer_kind"] == "choice":
                scope = request.get("interpretation", {}).get("assessed_scope", {})
                request_digest_ = sha256(
                    json.dumps(
                        request, ensure_ascii=False, separators=(",", ":"), allow_nan=False
                    ).encode()
                ).hexdigest()
                focal = scope.get("focal_extent")
                state = request.get("state", {})
                if (
                    request.get("interpretation", {}).get("declaration_digest") != family.digest
                    or state.get("source") != source.text[examined[0] : examined[1]]
                    or state.get("focal")
                    != dict(start=focus.start - examined[0], end=focus.end - examined[0])
                ):
                    continue
            else:
                continue
            if (
                scope.get("pin") != pin
                or scope.get("projection_extent") != list(examined)
                or focal != [focus.start, focus.end]
                or answer["request_digest"] != request_digest_
            ):
                continue
            alternatives = {row["key"]: row for row in answer["alternatives"]}
            labels = []
            for key in answer["observed_keys"]:
                alternative = alternatives[key]
                score = alternative.get("score")
                numeric = None if score is None else float(source_python(score["value"]))
                labels.append(
                    ClauseModelLabel(
                        label=key, score=numeric, accepted=key in answer["selected_keys"]
                    )
                )
            found.append(
                (
                    tuple(labels),
                    annotation_reference(layer_pin, annotation["local_id"]).values(),
                    answer["request_digest"],
                    answer["state"],
                )
            )
    if len(found) != 1:
        return (
            (),
            (),
            None,
            "failed",
            "Exact primary clause function question is missing or ambiguous.",
        )
    labels, reference, digest_, state = found[0]
    disposition = (
        "observed"
        if any(label.accepted for label in labels)
        else "withheld"
        if state in {"policy_withheld", "unresolved", "proposed"}
        else "failed"
    )
    return (
        labels,
        (reference,),
        digest_,
        disposition,
        (
            "Retained released linguistic function proposals; "
            "independent domain support remains unassessed."
        ),
    )


class ClauseClassificationMethod:
    name = "structure.clause_classification"
    version = "3"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = ClauseClassificationConfig
    resources = Resources(worker="cpu", batch_size=1)

    def select(self, run, cfg):
        return (
            (UnitRef(TaskUnitType.RUN, unit_key="clause-classification:" + cfg.inputs.identity),)
            if cfg.inputs is not None
            else ()
        )

    def input_digest(self, unit, cfg):
        return Digest(canonical_bytes(cfg.model_dump(mode="json", exclude_none=True)))

    def run(self, units, cfg, ctx):
        if cfg.inputs is None:
            raise ValueError("clause projection requires selected exact inputs")
        ctx.check_active()
        ctx.reader.validate_structural_inputs(cfg.inputs)
        passages = {p.passage_id: p for p in cfg.inputs.passages}
        sources = {source.identity: source for source in cfg.inputs.sources}
        primary, native, annotations = {}, {}, {}
        for source_ref in dict.fromkeys(
            passages[selection.passage_id].source_ref for selection in cfg.focuses
        ):
            source = sources[source_ref]
            primary[source_ref] = ctx.reader.primary_characterization(
                source.source_view_id, families=()
            )
            native[source_ref] = ctx.reader.structural_source_frame(cfg.inputs, source_ref)
            if cfg.context_policy == "adjacent_sentences":
                annotations[source_ref] = ctx.reader.structural_source_annotations(
                    cfg.inputs, source_ref, AnnotationProfile(SentenceConfig(exclude=("ner",)))
                ).annotations
        readings = []
        for selection in cfg.focuses:
            ctx.check_active()
            passage = passages[selection.passage_id]
            focus, preceding, following = clause_focus(
                selection,
                passage,
                sources[passage.source_ref],
                ctx.reader.retained_source_contribution(selection.frame),
                annotations.get(passage.source_ref, ()),
            )
            examined = (
                preceding.start if preceding is not None else focus.start,
                following.end if following is not None else focus.end,
            )
            labels, references, digest_, disposition, reason = primary_clause_functions(
                primary[passage.source_ref],
                ctx.reader.prepared,
                native[passage.source_ref],
                focus,
                examined,
            )
            context_digest = (
                digest_
                or sha256(
                    canonical_bytes(
                        [cfg.context_policy, selection.model_dump(mode="json"), examined]
                    )
                ).hexdigest()
            )
            readings.append(
                ClauseModelReading(
                    selection=selection,
                    focus=focus,
                    preceding=preceding,
                    following=following,
                    context_digest=context_digest,
                    envelope=digest_,
                    function=labels,
                    presentation=(),
                    disposition=disposition,
                    reason=reason,
                    primary_functions=references,
                    primary_context=(),
                )
            )
        report = StructuralProductReport(
            kind="clause_classification",
            inputs=cfg.inputs,
            clause_classification=ClauseClassificationProduct(
                context_policy=cfg.context_policy, readings=tuple(readings)
            ),
        )
        return tuple(
            UnitResult(
                ref=unit.ref,
                outcome=ObservationOutcome.PRODUCED,
                structural_product=report.model_dump(mode="json"),
                parse_detail=dict(
                    version="primary-clause-functions-1",
                    characterization_layers=[
                        pin.values() for layers in primary.values() for pin in layers
                    ],
                ),
            )
            for unit in units
        )
