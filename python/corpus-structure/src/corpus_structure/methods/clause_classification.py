"""Private GLiNER observations over authenticated exact predicate focuses."""

from dataclasses import asdict, replace
from hashlib import sha256
from typing import Literal, Self

from pydantic import model_validator

from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile, GlinerRefused
from corpus_structure.methods.gliner_worker import GlinerWorker, GlinerWorkerError
from corpus_structure.semantic.identity import canonical_bytes
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
THRESHOLD = 0.5
FUNCTION = {
    "definition": "States the meaning of a term, expression, or object.",
    "explanation": "Explains why or how a fact or concept holds.",
    "assumption_restriction": "Introduces a premise, restriction, or conditional scope.",
    "prescribed_action": "Instructs a reader or actor to perform an action.",
    "described_process": "Describes how an action or process occurs.",
    "reference": "Refers to another definition, statement, source, or artifact.",
    "unresolved": "The clause function cannot be determined from the selected input.",
}
PRESENTATION = {
    "example": "Presented as a worked example or illustration.",
    "attribution": "Reports or attributes a statement, assumption, or activity to another party.",
    "historical": "Discusses prior events or historical work.",
    "unresolved": "The presentation context cannot be determined from the selected input.",
}


class ClauseClassificationConfig(StructuralValue):
    inputs: StructuralInput | None = None
    structural_input_digest: str | None = None
    focuses: tuple[ClauseFocusSelection, ...] = ()
    profile: GlinerProfile | None = None
    context_policy: ContextPolicy = "exact_focus"

    @model_validator(mode="after")
    def bound_inputs(self) -> Self:
        if self.inputs is None:
            if self.structural_input_digest is not None or self.focuses or self.profile is not None:
                raise ValueError("partial clause model configuration")
            return self
        passages = {p.passage_id for p in self.inputs.passages}
        if (
            self.structural_input_digest != self.inputs.identity
            or self.profile is None
            or not self.focuses
            or len(set(self.focuses)) != len(self.focuses)
            or any(
                s.passage_id not in passages
                or s.frame.contribution_id not in self.inputs.dependencies
                for s in self.focuses
            )
        ):
            raise ValueError("clause model requires exact selected focuses and a pinned profile")
        return self


def clause_pack(release):
    return GlinerPack.from_declaration(
        release,
        {
            "classifications": [
                {"task": "clause_function", "labels": FUNCTION, "multi_label": False},
                {
                    "task": "presentation_context",
                    "labels": PRESENTATION,
                    "multi_label": True,
                    "cls_threshold": THRESHOLD,
                },
            ]
        },
        version="native-combined-v2",
    )


def clause_labels(raw):
    """Retain all returned labels and scores, including low-score fallbacks."""
    if not isinstance(raw, dict):
        raise ValueError("native classification output must be an object")

    def axis(values, vocabulary):
        if not isinstance(values, list):
            values = [values] if values is not None else []
        result = []
        for value in values:
            label, score = (
                (value.get("label"), value.get("confidence"))
                if isinstance(value, dict)
                else (value, None)
            )
            if (
                not isinstance(label, str)
                or label not in vocabulary
                or (score is not None and type(score) not in (float, int))
            ):
                raise ValueError("native classification returned an invalid label or score")
            result.append(
                ClauseModelLabel(
                    label=label,
                    score=score,
                    accepted=label != "unresolved" and score is not None and score >= THRESHOLD,
                )
            )
        if any(item.label not in vocabulary for item in result) or len(
            {item.label for item in result}
        ) != len(result):
            raise ValueError("native classification returned unknown or repeated labels")
        return tuple(result)

    function = axis(raw.get("clause_function"), FUNCTION)
    presentation = axis(raw.get("presentation_context"), PRESENTATION)
    if len(function) > 1:
        raise ValueError("native classification returned multiple single-label values")
    supported = any(item.accepted for item in (*function, *presentation))
    return function, presentation, "observed" if supported else "withheld"


def clause_context(selection, policy, focus, preceding=None, following=None):
    if policy == "exact_focus":
        text = focus.text
    else:
        text = (
            (preceding.text + "\n" if preceding else "")
            + "<focus>"
            + focus.text
            + "</focus>"
            + ("\n" + following.text if following else "")
        )
    identity = sha256(
        canonical_bytes([policy, selection.model_dump(mode="json"), text])
    ).hexdigest()
    return GlinerInput("clause-focus:" + identity, identity, text)


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
        (predicted,) = row.function or (None,)
        if predicted is None or not predicted.accepted:
            comparison = "withheld"
        else:
            comparison = "agrees" if predicted.label == current["reading"] else "disagrees"
        output.append(
            dict(
                reference=reference.model_dump(mode="json"),
                observation=row.model_dump(mode="json", exclude_none=True),
                deterministic_reading=current["reading"],
                comparison=comparison,
            )
        )
    return output


class ClauseClassificationMethod:
    name = "structure.clause_classification"
    version = "2"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.ENCODER
    confidence_source = None
    Config = ClauseClassificationConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def __init__(self):
        self._worker: GlinerWorker | None = None

    def close(self):
        if self._worker is not None:
            self._worker.close()
        self._worker = None

    def select(self, run, cfg):
        return (
            (UnitRef(TaskUnitType.RUN, unit_key="clause-classification:" + cfg.inputs.identity),)
            if cfg.inputs is not None
            else ()
        )

    def input_digest(self, unit, cfg):
        return Digest(canonical_bytes(cfg.model_dump(mode="json", exclude_none=True)))

    def run(self, units, cfg, ctx):
        from .model_observation import (
            observation_digest,
            released_pack,
            released_policy,
            request_digest,
        )

        if cfg.inputs is None or cfg.profile is None:
            raise ValueError("clause model inputs and profile absent")
        ctx.check_active()
        ctx.reader.validate_structural_inputs(cfg.inputs)
        policy = released_policy(ctx.reader.prepared)
        pack = released_pack(ctx.reader.prepared.release_id, policy)
        if self._worker is None:
            self._worker = GlinerWorker(cfg.profile)
        elif self._worker.profile.fingerprint != cfg.profile.fingerprint:
            raise GlinerRefused("clause worker cannot switch model profile")

        passages = {p.passage_id: p for p in cfg.inputs.passages}
        sources = {source.identity: source for source in cfg.inputs.sources}
        annotations = {}
        if cfg.context_policy == "adjacent_sentences":
            profile = AnnotationProfile(SentenceConfig(exclude=("ner",)))
            for ref in dict.fromkeys(passages[s.passage_id].source_ref for s in cfg.focuses):
                prepared = ctx.reader.structural_source_annotations(cfg.inputs, ref, profile)
                if not prepared.annotations:
                    raise GlinerRefused("context comparison requires retained sentence annotations")
                annotations[ref] = prepared.annotations

        prepared_focuses = []
        for selection in cfg.focuses:
            ctx.check_active()
            passage = passages[selection.passage_id]
            retained = ctx.reader.retained_source_contribution(selection.frame)
            focus, preceding, following = clause_focus(
                selection,
                passage,
                sources[passage.source_ref],
                retained,
                annotations.get(passage.source_ref, ()),
            )
            request = replace(
                clause_context(selection, cfg.context_policy, focus, preceding, following),
                operation=f"{self.name}/{self.version}",
            )
            prepared_focuses.append((selection, focus, preceding, following, request))

        readings, raw_reports, request_outcomes = [], [], []
        for selection, focus, preceding, following, request in prepared_focuses:
            ctx.check_active()
            reply = None
            function, presentation = (), ()
            expected = request_digest(
                pack, asdict(cfg.profile), (request,), THRESHOLD, "flat", False, policy["inference"]
            )
            outcome = dict(request_digest=expected, status="failed")
            request_outcomes.append(outcome)
            try:
                (returned,) = self._worker.extract(
                    pack, (request,), threshold=THRESHOLD, check_active=ctx.check_active
                )
                if (
                    returned.computation != expected
                    or returned.request_digest != expected
                    or returned.observation_digest
                    != observation_digest(
                        expected, returned.raw_json, returned.effective_profile_json
                    )
                ):
                    raise GlinerWorkerError("provider reply differs from the selected request")
                reply = returned
                outcome["status"] = "returned"
                raw_reports.append(asdict(reply))
                function, presentation, disposition = clause_labels(reply.raw)
                reason = (
                    "Located model observation."
                    if disposition == "observed"
                    else "No resolved label met the application threshold."
                )
            except (GlinerRefused, GlinerWorkerError, ValueError, TimeoutError, OSError) as error:
                disposition, reason = "failed", f"{type(error).__name__}: {error}"
                if isinstance(error, GlinerRefused) and reply is None:
                    outcome["status"] = "refused"
            readings.append(
                ClauseModelReading(
                    selection=selection,
                    focus=focus,
                    preceding=preceding,
                    following=following,
                    context_digest=request.context_digest,
                    envelope=reply.computation if reply else None,
                    function=function,
                    presentation=presentation,
                    disposition=disposition,
                    reason=reason,
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
                parse_detail={
                    "version": "clause-model-observation-2",
                    "schema_declaration": pack.declaration_json,
                    "pack_fingerprint": pack.fingerprint,
                    "profile_fingerprint": cfg.profile.fingerprint,
                    "profile": cfg.model_dump(mode="json")["profile"],
                    "raw_reports": raw_reports,
                    "request_outcomes": request_outcomes,
                },
            )
            for unit in units
        )
