"""Replay located model observations against captured envelopes and selected source."""

import base64
import contextlib
import json
from dataclasses import asdict, replace
from hashlib import sha256
from types import SimpleNamespace

from pydantic import TypeAdapter

from corpus_structure.methods.clause_classification import (
    clause_context,
    clause_focus,
    clause_labels,
    clause_pack,
    model_concordance,
)
from corpus_structure.methods.definition_applicability import (
    DefinitionComponentsConfig,
    decode_definition_components,
    definition_pack,
    definition_windows,
    located_definition_roles,
)
from corpus_structure.methods.gliner import GlinerInput, GlinerProfile, GlinerRefused
from corpus_structure.methods.model_observation import (
    MODEL_OBSERVATION_INPUT,
    observation_digest,
    released_pack,
    request_digest,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import (
    RetainedStructuralRef,
    StructuralProductReport,
)


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


def _verify_definition_windows(config, detail, policy, pack, passages):
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
                "structure.definition_components/9",
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


def _verify_definition_roles(report, config, detail, release, policy=None):
    if (
        detail["version"]
        != ("located-definition-extraction-4" if policy else "located-definition-extraction-3")
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
        _verify_definition_windows(config, detail, policy, pack, passages)
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


def verify_model_observation_closure(root, manifest, products, scopes, inventory):
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
