"""Replay located model observations against captured envelopes and selected source."""

import base64
import contextlib
import json
from dataclasses import asdict, replace
from hashlib import sha256
from types import SimpleNamespace

from pydantic import TypeAdapter

from corpus_structure.methods.clause_classification import (
    clause_focus,
    model_concordance,
)
from corpus_structure.methods.definition_applicability import (
    DefinitionComponentsConfig,
    decode_definition_components,
    definition_pack,
    definition_windows,
    located_definition_roles,
)
from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile, GlinerRefused
from corpus_structure.methods.model_observation import (
    MODEL_OBSERVATION_INPUT,
    observation_digest,
    released_pack,
    request_digest,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import (
    ClauseModelLabel,
    RetainedStructuralRef,
    StructuralProductReport,
)

# Exact historical native classification recipe, retained only for archived replay.
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


def _reports(detail):
    reports = {entry["computation"]: entry for entry in detail["raw_reports"]}
    if len(reports) != len(detail["raw_reports"]):
        raise ValueError("duplicate retained provider envelope")
    return reports


def _verify_envelope(entry, detail, text, identity, prefix):
    prep = entry["preparation"]
    if (
        entry["context_id"] != prefix + identity
        or entry["context_digest"] != identity
        or entry["pack"] != detail["pack_fingerprint"]
        or entry["profile"] != detail["profile_fingerprint"]
        or prep["synthetic_suffix"] not in ("", ".")
        or prep["consumed_text"] != text + prep["synthetic_suffix"]
    ):
        raise ValueError("provider envelope differs from exact context, pack, or profile")


def _verify_profile(config, detail):
    profile = TypeAdapter(GlinerProfile)
    declared = profile.validate_python(config["profile"])
    fingerprints = {declared.fingerprint}
    # Configuration custody canonicalizes numeric parameters. The native profile
    # constructor also accepts whole-second integer values for its float timeout.
    if declared.timeout_seconds.is_integer():
        fingerprints.add(
            replace(declared, timeout_seconds=int(declared.timeout_seconds)).fingerprint
        )
    if (
        profile.validate_python(detail["profile"]) != declared
        or detail["profile_fingerprint"] not in fingerprints
    ):
        raise ValueError("provider profile differs from registered execution profile")


def _policy(contract):
    retained = contract["model_observation_policy"]
    manifest = base64.b64decode(retained["manifest_base64"], validate=True)
    content = base64.b64decode(retained["input_base64"], validate=True)
    if "release:" + sha256(manifest).hexdigest() != contract["release_id"] or sha256(
        content
    ).hexdigest() != dict(json.loads(manifest)["dependencies"]).get(MODEL_OBSERVATION_INPUT):
        raise ValueError("model observation policy differs from released dependency")
    return json.loads(content)


def _verify_request(entry, expected):
    if (
        entry["request_digest"] != expected
        or entry["computation"] != expected
        or entry["observation_digest"]
        != observation_digest(expected, entry["raw_json"], entry["effective_profile_json"])
    ):
        raise ValueError("provider observation differs from exact model request")


def _verify_definition_windows(config, detail, policy, pack, passages, *, operation_version="9"):
    profile = TypeAdapter(GlinerProfile).validate_python(config["profile"]) if pack else None
    cfg = DefinitionComponentsConfig(profile=None)
    if profile:
        cfg = cfg.model_copy(update={"profile": profile})
    profile_values = asdict(profile) if profile is not None else {}
    ledger = iter(detail["window_outcomes"])
    reports = iter(detail["raw_reports"])
    overlap = config.get("evaluation_overlap")
    for passage_id in config["target_ids"] if pack else ():
        passage = passages[passage_id]
        windows = definition_windows(passage, cfg, policy["definition_windows"])
        for window in windows:
            request = GlinerInput(
                "definition-target:" + window.identity,
                window.identity,
                window.text,
                "structure.definition_components/" + operation_version,
            )
            expected = request_digest(
                pack,
                profile_values,
                (request,),
                config["threshold"],
                overlap or "flat",
                overlap is not None,
                policy["inference"],
            )
            row = next(ledger, {})
            status = row.get("status")
            if status not in {"returned", "failed", "refused"} or row != dict(
                passage_id=passage_id,
                start=window.start,
                end=window.end,
                request_digest=expected,
                status=status,
            ):
                raise ValueError("definition window differs from exact configured population")
            if status == "returned":
                entry = next(reports, {})
                _verify_request(entry, expected)
                if (entry["passage_id"], entry["window_start"], entry["window_end"]) != (
                    passage_id,
                    window.start,
                    window.end,
                ):
                    raise ValueError("definition report differs from the returned window")
        if windows[-1].end < passage.end and next(ledger, {}) != dict(
            passage_id=passage_id,
            start=windows[-1].end,
            end=passage.end,
            status="uninspected",
        ):
            raise ValueError("definition report misses bounded uninspected tail")
    if next(ledger, None) is not None or next(reports, None) is not None:
        raise ValueError("definition report contains unbound window outcomes")


def _verify_definition_roles(report, config, detail, release, policy=None, *, primary=False):
    if (
        detail["version"]
        != (
            "located-definition-extraction-5"
            if primary
            else "located-definition-extraction-4"
            if policy
            else "located-definition-extraction-3"
        )
        or detail["description_arm"] != config["description_arm"]
        or detail["overlap_policy"] != (config.get("evaluation_overlap") or "flat")
    ):
        raise ValueError("definition model differs from released extraction arm")
    cfg = DefinitionComponentsConfig(
        term_entity=config["term_entity"],
        content_entity=config["content_entity"],
        attachment_relation=config["attachment_relation"],
        description_arm=config["description_arm"],
    )
    pack = None
    if config["use_model"]:
        _verify_profile(config, detail)
        pack = (
            released_pack(release, policy, config=config)
            if policy
            else definition_pack(release, cfg)
        )
        if (
            detail["schema_declaration"] != pack.declaration_json
            or detail["pack_fingerprint"] != pack.fingerprint
        ):
            raise ValueError("definition model pack differs from released declaration")
    elif detail["raw_reports"]:
        raise ValueError("linguistic-only definition contains provider envelopes")
    passages = {p.passage_id: p for p in report.inputs.passages}
    if policy:
        _verify_definition_windows(
            config, detail, policy, pack, passages, operation_version="10" if primary else "9"
        )
    roles = []
    model_components = {}
    for envelope, entry in _reports(detail).items():
        passage = passages[entry["passage_id"]]
        lo, hi = entry["window_start"], entry["window_end"]
        if (
            entry["passage_id"] not in config["target_ids"]
            or not passage.start <= lo < hi <= passage.end
        ):
            raise ValueError("definition model window differs from selected source")
        window = passage.model_copy(
            update={
                "start": lo,
                "end": hi,
                "text": passage.text[lo - passage.start : hi - passage.start],
            }
        )
        _verify_envelope(entry, detail, window.text, window.identity, "definition-target:")
        raw = json.loads(entry["raw_json"])
        try:
            roles.extend(
                located_definition_roles(
                    raw,
                    window,
                    cfg,
                    envelope=envelope,
                    errors=[],
                )
            )
        except GlinerRefused:
            # A malformed entity population yields an explicit stage failure and no located roles.
            continue
        try:
            decoded = decode_definition_components(raw, window, cfg, candidate_errors=[])
        except GlinerRefused:
            # Failed attachment decoding keeps the independent entity-role candidates.
            continue
        model_components.update((component.component_id, component) for component in decoded)
    if tuple(roles) != (report.definition_components.role_candidates or ()):
        raise ValueError("retained definition role candidates differ from indexed provider output")
    if model_components != {
        component.component_id: component
        for component in report.definition_components.components
        if component.basis == "model_reading"
    }:
        raise ValueError("model definition components differ from retained directed attachments")


def _annotations(frame_ref, origins):
    producer = origins[frame_ref.origin_task_id]
    task_ids = {
        op["annotation_origin_task_id"]
        for op in producer["body"]["contribution_operations"]
        if op["question"] == "source_predicate_frames"
    }
    (annotation,) = task_ids
    details = source_python(origins[annotation]["body"]["parse_detail"])
    return tuple(
        SimpleNamespace(
            block_id=block["block_id"],
            dependency_digest=block["dependency_digest"],
            sentences=tuple(SimpleNamespace(**s) for s in block["sentences"]),
        )
        for block in details["annotations"]
    )


def _verify_clause_model(report, config, detail, release, payloads, origins, policy=None):
    if detail["version"] != (
        "clause-model-observation-2" if policy else "clause-model-observation-1"
    ):
        raise ValueError("clause model report version differs")
    pack = released_pack(release, policy) if policy else clause_pack(release)
    _verify_profile(config, detail)
    if (
        detail["schema_declaration"] != pack.declaration_json
        or detail["pack_fingerprint"] != pack.fingerprint
    ):
        raise ValueError("clause model pack differs from released declaration")
    product = report.clause_classification
    if (
        product.context_policy != config["context_policy"]
        or [row.selection.model_dump(mode="json") for row in product.readings] != config["focuses"]
    ):
        raise ValueError("clause model differs from registered focus selection")
    passages = {p.passage_id: p for p in report.inputs.passages}
    sources = {s.identity: s for s in report.inputs.sources}
    raw = _reports(detail)
    outcomes = iter(detail["request_outcomes"] if policy else ())
    for row in product.readings:
        passage = passages[row.selection.passage_id]
        retained = next(payloads)
        annotations = (
            _annotations(row.selection.frame, origins)
            if product.context_policy == "adjacent_sentences"
            else ()
        )
        spans = clause_focus(
            row.selection, passage, sources[passage.source_ref], retained, annotations
        )
        if spans != (row.focus, row.preceding, row.following):
            raise ValueError("clause model context differs from retained source selection")
        request = clause_context(row.selection, product.context_policy, *spans)
        if row.context_digest != request.context_digest:
            raise ValueError("clause model input digest differs from retained context")
        expected = None
        if policy:
            request = replace(request, operation="structure.clause_classification/2")
            expected = request_digest(
                pack,
                config["profile"],
                (request,),
                0.5,
                "flat",
                False,
                policy["inference"],
            )
            outcome = next(outcomes, {})
            status = outcome.get("status")
            if (
                status not in {"returned", "failed", "refused"}
                or (status == "returned") != (row.envelope is not None)
                or outcome != dict(request_digest=expected, status=status)
            ):
                raise ValueError("clause outcome differs from exact configured request")
        function, presentation, disposition = (), (), "failed"
        if row.envelope is not None:
            entry = raw.pop(row.envelope, None)
            if entry is None:
                raise ValueError("clause model result lacks retained envelope")
            if expected:
                _verify_request(entry, expected)
            _verify_envelope(entry, detail, request.text, request.context_digest, "clause-focus:")
            with contextlib.suppress(ValueError):
                function, presentation, disposition = clause_labels(json.loads(entry["raw_json"]))
        if (row.function, row.presentation, row.disposition) != (
            function,
            presentation,
            disposition,
        ):
            raise ValueError("clause model reading differs from retained output and withholding")
    if raw or next(outcomes, None) is not None:
        raise ValueError("unbound retained clause model envelopes")


def _primary_observation_reader(root, manifest, retained, report):
    from corpus_structure.methods.native_evidence_layers import retained_annotation_products
    from corpus_structure.semantic.proposals import native_source_frame

    from .primary_characterization_replay import primary_layers_for_report, retained_primary_layers
    from .review_bundle import _detached_relation, _retained_review_source_view

    frozen = retained_primary_layers(root, manifest)
    layers, releases = primary_layers_for_report(root, manifest, retained, retained=frozen)
    body = retained["body"]
    prepared = releases.get(body["release_id"])
    if prepared is None:
        raise ValueError("analytical primary replay lacks its original archived release")
    raw = {row["source_view_id"]: row for row in _detached_relation(root, manifest, "sources")}
    views = {}
    refs = {row.identity: row for row in report.inputs.sources}
    for ref in refs.values():
        if ref.source_view_id not in raw:
            raise ValueError("primary observation source closure is missing")
        view = _retained_review_source_view(raw[ref.source_view_id])
        if (
            view.ref.native_product.task_id,
            view.ref.native_product.product_key,
            view.ref.native_product.content_digest,
            view.ref.projection_digest,
            view.ref.recipe_digest,
        ) != (
            ref.native_task_id,
            ref.native_product_key,
            ref.native_content_digest,
            ref.projection_digest,
            ref.recipe_digest,
        ):
            raise ValueError("primary observation source differs from its original pin")
        views[ref.source_view_id] = view

    def selected(identity, *, families=()):
        chosen, _releases = primary_layers_for_report(
            root, manifest, retained, source_view_id=identity, retained=frozen
        )
        if not set(families) <= {
            family
            for layer in chosen.values()
            for family in layer.payload["operation"]["produced_families"]
        }:
            raise ValueError("primary observation lacks a required selected family")
        return chosen

    def annotations(inputs, source_ref, profile):
        ref = refs[source_ref]
        view = views[ref.source_view_id]
        return SimpleNamespace(
            source=native_source_frame(view, ()),
            annotations=retained_annotation_products(selected(ref.source_view_id), view, profile),
            errors=(),
        )

    reader = SimpleNamespace(
        prepared=prepared,
        source_view=views.__getitem__,
        primary_characterization=selected,
        structural_source_annotations=annotations,
        structural_source_frame=lambda inputs, key: native_source_frame(
            views[refs[key].source_view_id], ()
        ),
        validate_structural_inputs=lambda inputs: (
            None
            if inputs == report.inputs
            else (_ for _ in ()).throw(
                ValueError("primary observation substituted structural inputs")
            )
        ),
    )
    return reader, layers


def _verify_primary_observation(root, manifest, retained, report, origins, payloads, policy):
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.clause_classification import (
        ClauseClassificationConfig,
        ClauseClassificationMethod,
    )
    from corpus_structure.methods.definition_applicability import (
        DefinitionComponentsConfig,
        retained_annotation_components,
    )
    from corpus_structure.methods.definition_declaration import (
        DeclarationComponentsConfig,
        DeclarationComponentsMethod,
    )
    from corpus_structure.semantic.source_contexts import NativeSourcePin

    body, config = retained["body"], retained["configuration"]
    if report.definition_components is not None and any(
        component.basis in {"matched_cue", "native_geometry"}
        and (
            component.witness is None
            or component.witness.primary_match is None
            or not component.witness.primary_scope
        )
        for component in report.definition_components.components
    ):
        raise ValueError(
            "definition basis lacks exact retained annotation witness with primary match and scope"
        )
    reader, _layers = _primary_observation_reader(root, manifest, retained, report)
    ctx = SimpleNamespace(reader=reader, check_active=lambda: None)
    if (
        report.clause_classification is not None
        or body["method"] == "structure.definition_declaration_components"
    ):
        if report.clause_classification is not None:
            method, cfg = (
                ClauseClassificationMethod(),
                ClauseClassificationConfig.model_validate(config),
            )
            reader.retained_source_contribution = lambda _reference: next(payloads)
        else:
            method, cfg = (
                DeclarationComponentsMethod(),
                DeclarationComponentsConfig.model_validate(config),
            )
        if body["operation_version"] != method.version or cfg.inputs != report.inputs:
            raise ValueError("primary observation differs from its exact active method/input ABI")
        (result,) = method.run((SimpleNamespace(ref=None),), cfg, ctx)
        if StructuralProductReport.model_validate(
            result.structural_product
        ) != report or result.parse_detail != source_python(body["parse_detail"]):
            raise ValueError("primary observation differs from exact retained projection")
        return
    cfg = DefinitionComponentsConfig.model_validate(config)
    if body["operation_version"] != "10" or cfg.inputs != report.inputs:
        raise ValueError("primary named definitions differ from their exact active ABI")
    detail = source_python(body["parse_detail"])
    _verify_definition_roles(report, config, detail, body["release_id"], policy, primary=True)
    passages = {row.passage_id: row for row in report.inputs.passages}
    evidence = {row["source_ref"]: row for row in detail["annotation_inputs"]}
    replayed = {}
    for passage_id in cfg.target_ids:
        passage = passages[passage_id]
        if not cfg.use_named_candidates or not cfg.annotation_rules:
            continue
        original = evidence.get(passage.source_ref)
        if original is None:
            raise ValueError("primary named definition has no original annotation operation")
        task = original["task_id"]
        origin = origins.get(task, {})
        annotation_body = origin.get("body", {})
        annotation_detail = (
            source_python(annotation_body["parse_detail"])
            if "parse_detail" in annotation_body
            else {}
        )
        retained_annotations = reader.structural_source_annotations(
            cfg.inputs, passage.source_ref, AnnotationProfile(SentenceConfig(exclude=("ner",)))
        )
        frame = retained_annotations.source
        if task is not None and (
            origin.get("method") != "extract.m1_annotations"
            or annotation_body.get("operation_version") != "3"
            or origin.get("origin_unit_id") != frame.source_view_id
            or annotation_body.get("source") != frame.unit_ref
            or annotation_detail.get("source_pin") != asdict(NativeSourcePin.from_source(frame))
            or annotation_body.get("input_hash") != original["input_hash"]
        ):
            raise ValueError("primary named definition lacks original annotation custody")
        retained_annotations.annotation_task_id = task
        retained_annotations.annotation_input_hash = original["input_hash"]
        result = retained_annotation_components(
            reader,
            cfg.inputs,
            passage,
            cfg,
            retained=retained_annotations,
            witness_policy=(policy or {}).get("definition_witness", {}),
        )
        replayed.update((component.component_id, component) for component in result.components)
    actual = {
        component.component_id: component
        for component in report.definition_components.components
        if component.basis != "model_reading"
    }
    if replayed != actual:
        raise ValueError(
            "primary named definition differs from exact retained match/scope projection"
        )


def verify_model_observation_closure(root, manifest, products, scopes, inventory):
    from corpus_structure.methods.definition_declaration import CHAIN_METHOD

    from .review_bundle import _detached_relation, _retained_contribution_payloads

    selected = [
        (entry[2], report)
        for entry in products
        if (report := entry[-1]).clause_classification is not None
        or report.definition_components is not None
    ]
    if not selected:
        return
    origins = {row["origin_task_id"]: row for row in _detached_relation(root, manifest, "reports")}
    contracts = {row["release_id"]: row for row in _detached_relation(root, manifest, "contracts")}
    requests = [
        (report, row.selection.frame)
        for _, report in selected
        if report.clause_classification is not None
        for row in report.clause_classification.readings
    ]
    payloads = _retained_contribution_payloads(root, manifest, requests, scopes, inventory)
    for origin, report in selected:
        retained = origins.get(origin) or {}
        body = retained.get("body") or {}
        primary_version = body.get("operation_version")
        if (body.get("method"), primary_version) in {
            ("structure.definition_components", "10"),
            ("structure.clause_classification", "3"),
            (CHAIN_METHOD, "2"),
        }:
            config = retained.get("configuration")
            if (
                not isinstance(config, dict)
                or StructuralProductReport.model_validate(body["structural_product"]) != report
            ):
                raise ValueError("primary observation differs from its immutable original report")
            contract = contracts.get(body["release_id"], {})
            policy = _policy(contract) if "model_observation_policy" in contract else None
            _verify_primary_observation(root, manifest, retained, report, origins, payloads, policy)
            continue
        if body.get("method") == CHAIN_METHOD or (
            report.definition_components is not None and body.get("operation_version") in {"8", "9"}
        ):
            raise ValueError(
                "obsolete definition semantic closure requires regeneration "
                "from primary characterization; original raw bytes "
                "and source proofs remain retained"
            )
        if (
            report.definition_components is not None
            and report.definition_components.role_candidates is None
            and body.get("operation_version") not in {"8", "9"}
        ):
            # Older definition results do not declare this envelope ABI. The enclosing
            # bundle verifier still checks their original reports and closure membership.
            continue
        config = retained.get("configuration")
        if not isinstance(config, dict):
            raise ValueError("required model observation report or configuration is missing")
        method = "structure." + report.kind
        versions = {"1", "2"} if report.clause_classification is not None else {"8", "9"}
        version = body.get("operation_version")
        if (
            body.get("method") != method
            or version not in versions
            or StructuralProductReport.model_validate(body["structural_product"]) != report
        ):
            raise ValueError("model observation differs from registered original producer")
        detail = source_python(body["parse_detail"])
        contract = contracts.get(body["release_id"], {})
        if (version in {"2", "9"}) != ("model_observation_policy" in contract):
            raise ValueError("model observation version differs from the selected release policy")
        policy = _policy(contract) if version in {"2", "9"} else None
        if version == "9" and report.definition_components.role_candidates is None:
            raise ValueError("definition model lacks an explicit role outcome population")
        if report.clause_classification is not None:
            _verify_clause_model(
                report, config, detail, body["release_id"], payloads, origins, policy
            )
        else:
            if any(
                component.declaration_chain is not None
                for component in report.definition_components.components
            ):
                raise ValueError("incumbent definition extraction cannot carry a declaration chain")
            _verify_definition_roles(report, config, detail, body["release_id"], policy)


def verify_projected_definition_roles(root, manifest, products, structural_scopes):
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.methods.definition_terms import (
        DefinitionTermsConfig,
        DefinitionTermsMethod,
    )
    from corpus_structure.semantic.identity import canonical_bytes

    from .review_bundle import _detached_relation, _retained_review_source_view

    origins = {row["origin_task_id"]: row for row in _detached_relation(root, manifest, "reports")}
    projections = [
        row
        for row in origins.values()
        if row.get("method") == "locate.definition_terms"
        and (row.get("configuration") or {}).get("role_refs")
    ]
    if not projections:
        return
    sources = {row["source_view_id"]: row for row in _detached_relation(root, manifest, "sources")}

    def retained(reference):
        matches = [
            product
            for index, task, origin, _, project, runtime, product in products
            if task == reference.selected_task_id
            and origin == reference.origin_task_id
            and project == reference.project_id
            and runtime == reference.runtime_fingerprint
            and product.product_id == reference.product_id
            and structural_scopes[index]["run_id"] == reference.run_id
            and structural_scopes[index]["cut_id"] == reference.cut_id
            and structural_scopes[index]["release_id"] == reference.release_id
            and structural_scopes[index]["binding"]["data_revision"] == reference.result_revision
        ]
        upstream = origins.get(reference.origin_task_id, {}).get("body") or {}
        if (
            not matches
            or upstream.get("operation_version") != "9"
            or any(match != matches[0] for match in matches)
        ):
            raise ValueError("projected definition role lacks exact selected observation custody")
        return {"report": matches[0].model_dump(mode="json")}

    for producer in projections:
        body = producer["body"]
        if body["operation_version"] != "2":
            raise ValueError("projected definition role uses the wrong producer version")
        view = _retained_review_source_view(sources[producer["origin_unit_id"]])
        cfg = DefinitionTermsConfig.model_validate(producer["configuration"])
        if (
            cfg.source_product_digest != view.ref.native_product.content_digest
            or cfg.source_projection_digest != view.ref.projection_digest
        ):
            raise ValueError("projected definition role differs from configured source")
        ctx = SimpleNamespace(
            check_active=lambda: None,
            reader=SimpleNamespace(
                source_view=lambda _, view=view: view,
                retained_structural_report=retained,
            ),
        )
        (result,) = DefinitionTermsMethod().run(
            (SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, view.ref.id, view.ref.key)),),
            cfg,
            ctx,
        )
        if canonical_bytes(result.contributions) != canonical_bytes(
            body["contributions"]
        ) or canonical_bytes(result.contribution_operations) != canonical_bytes(
            body["contribution_operations"]
        ):
            raise ValueError("projected definition role differs from its indexed source evidence")


def verify_model_concordance_closure(root, manifest):
    """Check later interpretation observations without provider execution."""
    from corpus_structure.semantic.contributions import contribution_identity

    from .review_bundle import _detached_relation

    origins = {row["origin_task_id"]: row for row in _detached_relation(root, manifest, "reports")}

    def origin(reference):
        value = origins[reference.origin_task_id]
        if (
            value["project_id"] != reference.project_id
            or value["runtime_fingerprint"] != reference.runtime_fingerprint
            or value["body"]["release_id"] != reference.release_id
            or (
                reference.selected_task_id == reference.origin_task_id
                and value["origin_run_id"] != reference.run_id
            )
        ):
            raise ValueError("model concordance loses its original producer custody")
        return value["body"]

    def resolve_frame(reference):
        (frame,) = [
            c
            for c in origin(reference)["contributions"]
            if c["contribution_id"] == reference.contribution_id
        ]
        if contribution_identity(frame) != reference.contribution_id:
            raise ValueError("model concordance predecessor frame has changed")
        return frame

    for producer in origins.values():
        config = producer.get("configuration") or {}
        body = producer["body"] or {}
        if not config.get("classification_refs"):
            if (
                body.get("method") == "structure.scoped_relations"
                and body.get("parse_detail")
                and source_python(body["parse_detail"]).get("clause_model_concordance")
            ):
                raise ValueError("unbound clause model concordance")
            continue
        if body["method"] != "structure.scoped_relations" or body["operation_version"] not in {
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
        }:
            raise ValueError("model concordance uses the wrong producing method")
        expected = []
        for raw_ref in config["classification_refs"]:
            ref = RetainedStructuralRef.model_validate(raw_ref)
            if ref.product_id not in config["inputs"]["dependencies"]:
                raise ValueError("model concordance lacks declared classification dependency")
            observation = origin(ref)
            if observation["method"] != "structure.clause_classification" or observation[
                "operation_version"
            ] not in {"1", "2"}:
                raise ValueError("model concordance requires exact retained classifier origin")
            report = StructuralProductReport.model_validate(observation["structural_product"])
            expected.extend(
                model_concordance(
                    ref,
                    report,
                    producer["origin_unit_id"],
                    body["contributions"],
                    resolve_frame,
                )
            )
        detail = source_python(body["parse_detail"])
        if detail.get("clause_model_concordance", []) != expected:
            raise ValueError(
                "model concordance differs from exact retained classification and frame"
            )
