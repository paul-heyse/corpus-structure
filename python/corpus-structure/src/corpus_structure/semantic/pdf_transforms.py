"""Acquired PDF transformations over exact native publication support.

The existing PDF workers, finite kernels, private staging and sealed publication
remain their owners. This adapter supplies actual native-request custody only.
"""

from __future__ import annotations

import inspect
import json
import os
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass
from hashlib import file_digest, sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select

from .data_operation_json import json_bytes
from .identity import canonical_bytes
from .product_reference import ProductReference
from .types import SourceArtifact


class PdfEnrichmentOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    cell_math_pattern: str = "(?:[=+×÷∑∏∫√∞≤≥∈⊂∪∩^_\\\\]|(?<!\\w)[A-Za-z](?!\\w)|\\d)"  # noqa: RUF001 — literal mathematical symbols
    cell_prose_pattern: str = "[A-Za-z]{2,}(?:[\\s,;:'’().-]+[A-Za-z]{2,})*[.!?]?"  # noqa: RUF001 — literal typographic apostrophe
    crop_padding_points: float = Field(default=0.75, ge=0)


class PdfIntegrationOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    integration_policy: dict[str, Any]

    @field_validator("integration_policy")
    @classmethod
    def policy(cls, value):
        from .pdf_integrated import normalize_pdf_integration_policy

        return normalize_pdf_integration_policy(value)


class PdfRecognitionOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    # The exact existing released recovery contract; no generic retry is added.
    recovery_policy: dict[str, Any] | None
    source_recovery: Literal["grinstead-snell-witnessed-v1"] | None = None

    @field_validator("recovery_policy")
    @classmethod
    def recovery(cls, value):
        from corpus_structure.ingest.pdf_recognition import PdfRecognitionRecoveryPolicy

        return (
            None
            if value is None
            else PdfRecognitionRecoveryPolicy.model_validate(value).model_dump(mode="json")
        )


class PdfIntegrationProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    recognition: PdfRecognitionOptions
    integration: PdfIntegrationOptions


class PdfRecognitionResources(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    python: str = Field(min_length=1)
    script: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    receipts: str = Field(min_length=1)
    timeout_seconds: float = Field(gt=0)


def _root():
    return Path(__file__).parents[1]


def _implementation_files(mode):
    common = (
        "semantic/pdf_transforms.py",
        "semantic/pdf_capture.py",
        "semantic/pdf_contracts.py",
        "semantic/data_operation_pdf_effect.py",
        "semantic/pdf_effect_contract.py",
        "semantic/pdf_record_reader.py",
        "semantic/pdf_publication.py",
        "semantic/pdf_integrated.py",
        "semantic/pdf_observations.py",
        "orchestrate/pdf_streaming.py",
        "ingest/pdf_methods.py",
        "ingest/pdf_record_product.py",
        "ingest/pdf_hierarchy.py",
        "ingest/pdf_health.py",
        "ingest/pdf_section_views.py",
        "ingest/pdf_candidate_source.py",
        "ingest/pdf_worker.py",
        "ingest/pdf_capacity.py",
    )
    if mode == "organized":
        return common
    if mode == "recognized":
        return (*common, "ingest/pdf_recognition.py", "ingest/pdf_incumbent_recovery.py")
    extra = (
        (
            "ingest/pdf_selected_enrichment.py",
            "ingest/pdf_enrichment.py",
            "ingest/pdf_candidate_geometry.py",
        )
        if mode == "enriched"
        else (
            "ingest/pdf_stream_reconciliation.py",
            "ingest/pdf_reconciliation.py",
        )
    )
    return common + extra


def _file_hash(path):
    with Path(path).open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def pdf_transform_custody(
    mode,
    *,
    directory,
    recipe=None,
    assets=None,
    options,
    recognition_recipe=None,
    resources=None,
    nemotron_endpoint=None,
    input_operation="source.pdf/capture",
):
    if mode not in {"organized", "enriched", "integrated", "recognized"}:
        raise ValueError("unknown PDF transformation capability")
    if mode == "organized":
        from pydantic import TypeAdapter

        from corpus_structure.ingest.pdf_hierarchy import SectionPolicy

        policy = TypeAdapter(SectionPolicy).validate_python(options)
        option_value = TypeAdapter(SectionPolicy).dump_python(policy, mode="json")
        option_value["organizational_refs"] = sorted(policy.organizational_refs)
    else:
        options = {
            "enriched": PdfEnrichmentOptions,
            "integrated": PdfIntegrationOptions,
            "recognized": PdfRecognitionOptions,
        }[mode].model_validate(options)
        option_value = options.model_dump(mode="json")
    record = dict(
        mode=mode,
        directory=str(Path(directory).resolve()),
        options=option_value,
        input_operation=input_operation,
        files=[(name, (_root() / name).read_bytes().hex()) for name in _implementation_files(mode)],
    )
    if mode == "enriched":
        from .pdf_capture import pdf_capture_custody

        record["native"] = json.loads(
            pdf_capture_custody(
                recipe,
                assets,
                directory=directory,
                nemotron_endpoint=nemotron_endpoint,
                require_nemotron_handoff=nemotron_endpoint is not None,
            ).content
        )
    elif mode == "recognized":
        from corpus_structure.ingest.pdf_recognition import NemotronRecipe

        if not isinstance(recognition_recipe, NemotronRecipe):
            raise ValueError("recognition requires an explicit immutable NemotronRecipe")
        resources = PdfRecognitionResources.model_validate(resources)
        worker = Path(resources.script).resolve()
        # Preserve the venv entrypoint; _file_hash still follows its executable bytes.
        interpreter = Path(os.path.abspath(resources.python))
        record.update(
            recognition_recipe=asdict(recognition_recipe),
            recognition_bytes=recognition_recipe.to_bytes().hex(),
            resources=resources.model_copy(
                update={
                    "script": str(worker),
                    "python": str(interpreter),
                    "receipts": str(Path(resources.receipts).resolve()),
                }
            ).model_dump(mode="json"),
            worker_digest=_file_hash(worker),
            worker_source=worker.read_bytes().hex(),
            interpreter_digest=_file_hash(interpreter),
        )
    return SourceArtifact("pdf-" + mode + "/execution-custody", canonical_bytes(record))


def recognition_policy_asset(record):
    """The small native eligibility asset, separate from paths and executor bytes."""
    from corpus_structure.ingest.pdf_recognition import NemotronRecipe, repetition_recovery_recipe

    from .pdf_observations import PROFILE_CONTRACT

    recipe = NemotronRecipe(**record["recognition_recipe"])
    options = PdfRecognitionOptions.model_validate(record["options"])
    recipes = [recipe]
    if options.recovery_policy is not None:
        alternate = repetition_recovery_recipe(recipe)
        if alternate.recipe_id != options.recovery_policy["permitted_recipe_id"]:
            raise ValueError("recovery recipe differs from admitted policy")
        recipes.append(alternate)
    return SourceArtifact(
        PROFILE_CONTRACT,
        canonical_bytes(
            {
                "version": "pdf-recognition-profile-1",
                "base_recipe_digest": recipe.digest,
                "recipes": [
                    {
                        "digest": item.digest,
                        "weights_digest": item.weights_digest,
                        "tokenizer_digest": item.tokenizer_digest,
                        "content": item.to_bytes().decode(),
                    }
                    for item in recipes
                ],
                "recovery_policy": options.recovery_policy,
                "source_recovery": options.source_recovery,
            }
        ),
    )


def pdf_transform_operation_sources(mode, **profile):
    from .pdf_domain import pdf_helper_asset
    from .python_operation_sources import PythonSource, PythonSourceCollection

    recognition = None
    if mode == "integrated":
        recognition = pdf_transform_operation_sources(
            "recognized",
            options=profile.pop("recognition_options"),
            recognition_recipe=profile.pop("recognition_recipe"),
            resources=profile.pop("resources"),
            directory=profile["directory"],
            input_operation="source.pdf/capture",
        )
    custody = pdf_transform_custody(mode, **profile)
    module = {
        "organized": "pdf_organization_operation",
        "enriched": "pdf_enrichment_operation",
        "integrated": "pdf_integration_operation",
        "recognized": "pdf_observation_operation",
    }[mode]
    path = _root() / "ingest" / (module + ".py")
    own = PythonSourceCollection(
        tuple(
            PythonSource(name, source.read_bytes(), str(source))
            for name, source in (
                ("corpus_structure.ingest." + module, path),
                ("corpus_structure.semantic.pdf_transforms", Path(__file__)),
                (
                    "corpus_structure.semantic.data_operation_pdf_effect",
                    Path(__file__).with_name("data_operation_pdf_effect.py"),
                ),
                (
                    "corpus_structure.semantic.pdf_effect_contract",
                    Path(__file__).with_name("pdf_effect_contract.py"),
                ),
                (
                    "corpus_structure.semantic.data_operation_effects",
                    Path(__file__).with_name("data_operation_effects.py"),
                ),
            )
        ),
        boundary_contracts=(
            custody,
            pdf_helper_asset(),
            *(
                (recognition_policy_asset(json.loads(custody.content)),)
                if mode == "recognized"
                else ()
            ),
        ),
    )

    if mode in {"organized", "recognized"}:
        return own
    from .primary_operations import combine_primary_sources

    variant = (
        "organized" if profile.get("input_operation") == "source.pdf_sections/organize" else "raw"
    )
    path = _root() / "ingest" / ("pdf_" + variant + "_" + mode + "_operation.py")
    concrete = PythonSourceCollection(
        (
            PythonSource(
                "corpus_structure.ingest.pdf_" + variant + "_" + mode + "_operation",
                path.read_bytes(),
                str(path),
            ),
        )
    )
    return combine_primary_sources(
        *(item for item in (own, concrete, recognition) if item is not None)
    )


def _endpoint(mode):
    # The actual run/factory are inherited from these captured finite family owners.
    if mode == "organized":
        from corpus_structure.ingest.pdf_organization_operation import PdfOrganizationOperation

        return PdfOrganizationOperation
    if mode == "enriched":
        from corpus_structure.ingest.pdf_enrichment_operation import PdfEnrichmentOperation

        return PdfEnrichmentOperation
    if mode == "recognized":
        from corpus_structure.ingest.pdf_observation_operation import PdfObservationOperation

        return PdfObservationOperation
    from corpus_structure.ingest.pdf_integration_operation import PdfIntegrationOperation

    return PdfIntegrationOperation


@dataclass(frozen=True)
class SelectedPdfInput:
    product: Any
    parent: Any
    candidates: Any
    sections: tuple[tuple[str, str], ...]
    context: Any
    read_budget: Any


def _read_selected_pdf(
    prepared,
    capture,
    binding,
    execution_owner,
    directory,
    *,
    sections=(),
    membership: Literal["direct", "descendants"] = "direct",
    project_sections=True,
    read_candidates=True,
    check_active,
):
    """Authenticate the exact semantic support before detaching any native body."""
    from dataclasses import replace

    from pydantic import TypeAdapter

    from corpus_structure.ingest.pdf_candidate_source import ReplayCandidatePageSource
    from corpus_structure.ingest.pdf_section_views import published_section_projections
    from corpus_structure.ingest.pdf_streaming import _atomic_bytes

    from .metadata import table
    from .pdf_capture import pdf_publication_value
    from .pdf_contracts import PreparedPdfProduct, pdf_context_for_release
    from .pdf_payloads import prepare_payload_family
    from .pdf_publication import PdfExecutionReceipt
    from .pdf_record_reader import PublishedPdfReader, PublishedReadBudget
    from .product_reference import ProductReference

    claim = execution_owner.claim
    if claim is None or binding.subject_context is None:
        raise ValueError("PDF transformation requires an actual native request claim")
    if capture["document"] != binding.subject_context.original_source:
        raise ValueError("selected PDF publication changes the qualified original")
    members = [
        member for role in binding.roles if role.role == "capture" for member in role.members
    ]
    if len(members) != 1 or members[0].member is not None or len(members[0].support_episodes) != 1:
        raise ValueError("PDF transformation requires one whole exact computational publication")
    check_active()
    with execution_owner.engine.connect() as connection:
        receipt = TypeAdapter(PdfExecutionReceipt).validate_json(
            canonical_bytes(
                connection.scalar(
                    select(
                        func.ops.ddo_pdf_capture_source(
                            claim.request_id,
                            binding.subject_context.project_id,
                            members[0].product,
                            members[0].support_episodes[0],
                        )
                    )
                )
            ),
            strict=True,
        )
        publication = receipt.publication
        parent = ProductReference(
            publication.task_id, publication.product_key, publication.logical_digest
        )
        read_budget = PublishedReadBudget(
            100_000, execution_owner.invocation.executor.policy.max_packet_bytes
        )
        reader = PublishedPdfReader(
            connection,
            parent,
            projection_context=prepared,
            read_budget=read_budget,
            check_active=check_active,
        )
        # The native owner authenticates the immutable pin and returns only a scalar
        # aggregate. The invocation already owns its input credit through publication.
        reader.require_materialization_capacity()
        health = [row for row in reader.iter_companions("health") if "conversion" in row]
        if (
            len(health) != 1
            or pdf_publication_value(
                binding.subject_context.original_source, publication, health[0]
            )
            != capture
        ):
            raise ValueError("selected PDF value differs from its authentic publication")
        check_active()
        context = pdf_context_for_release(connection, prepared)
        artifacts = table("kb.source_artifact")
        digests = (publication.source_digest, publication.schema_digest, publication.recipe_digest)
        size = connection.scalar(
            select(func.sum(func.octet_length(artifacts.c.content))).where(
                artifacts.c.artifact_digest.in_(digests)
            )
        )
        if size is None or size > execution_owner.invocation.executor.policy.max_packet_bytes:
            raise ValueError("selected PDF custody exceeds reserved input capacity")
        read_budget.reserve(int(size))
        bodies = {
            digest: bytes(content)
            for digest, content in connection.execute(
                select(artifacts.c.artifact_digest, artifacts.c.content).where(
                    artifacts.c.artifact_digest.in_(digests)
                )
            )
        }
        if set(bodies) != set(digests) or any(
            sha256(bodies[digest]).hexdigest() != digest for digest in digests
        ):
            raise ValueError("selected publication original/schema/recipe custody differs")
        values = reader.native_product_values(include_candidate_pages=False)
        product = PreparedPdfProduct(
            canonical_bytes(values),
            bodies[publication.source_digest],
            bodies[publication.schema_digest],
            bodies[publication.recipe_digest],
            context.contract_digest,
        )
        if membership not in {"direct", "descendants"}:
            raise ValueError("PDF source membership is outside the admitted finite choices")
        projections = (
            published_section_projections(
                reader,
                selections=tuple(sections),
                membership=membership,
                scope=None,
                check_active=check_active,
            )
            if project_sections
            else ()
        )
        specs = tuple((row.section_pointer, row.membership) for row in projections)
        directory.mkdir(parents=True, exist_ok=False)
        replays = {}
        for payload in reader.iter_candidate_payloads(context=context) if read_candidates else ():
            check_active()
            if payload.page_no in replays:
                raise ValueError("duplicate selected PDF candidate page")
            replay = _atomic_bytes(
                directory / f"candidate-{payload.page_no:06}.arrow",
                payload.content,
                "candidate_payload",
            )
            replays[payload.page_no] = replace(
                replay,
                rows=1,
                page_no=payload.page_no,
                schema_digest=payload.schema_digest,
                logical_digest=payload.logical_digest,
            )
        candidates = (
            ReplayCandidatePageSource(replays, prepare_payload_family(context))
            if read_candidates
            else None
        )
    check_active()
    return SelectedPdfInput(product, parent, candidates, specs, context, read_budget)


def _read_selected_observations(value, binding, execution_owner, selected, check_active):
    """Detach only the exact selected set after native support/meaning correspondence."""
    from .pdf_observations import PdfObservationExecutionReceipt

    claim = execution_owner.claim
    members = [
        member for role in binding.roles if role.role == "observations" for member in role.members
    ]
    if (
        claim is None
        or binding.subject_context is None
        or len(members) != 1
        or members[0].member is not None
        or len(members[0].support_episodes) != 1
    ):
        raise ValueError("integration requires one exact computational observation-set support")
    from .metadata import table
    from .product_reference import ProductReference

    detached = []
    check_active()
    with execution_owner.engine.connect() as connection:
        authenticated = connection.scalar(
            select(
                func.ops.ddo_pdf_observation_source(
                    claim.request_id,
                    binding.subject_context.project_id,
                    members[0].product,
                    members[0].support_episodes[0],
                )
            )
        )
        receipt = PdfObservationExecutionReceipt.model_validate_json(
            canonical_bytes(authenticated["receipt"])
        )
        if authenticated["value"] != value:
            raise ValueError("selected observation value differs from actual native adoption")
        final = {page["page_no"]: page["outcome"] for page in value["pages"]}
        failures = [number for number, outcome in final.items() if outcome != "succeeded"]
        if failures:
            raise RuntimeError(f"unresolved triple-pass physical pages: {failures}")
        products, bodies, artifacts = map(
            table, ("ops.pdf_product", "ops.pdf_product_body", "kb.source_artifact")
        )
        for page in receipt.pages:
            for observation in page.observations:
                check_active()
                query = (
                    select(bodies.c.payload)
                    .join(
                        products,
                        (products.c.task_id == bodies.c.task_id)
                        & (products.c.product_key == bodies.c.product_key),
                    )
                    .where(
                        products.c.task_id == observation.task_id,
                        products.c.product_key == observation.product_key,
                        products.c.content_digest == observation.content_digest,
                    )
                )
                selected.read_budget.preflight(connection, query)
                payload = bytes(connection.scalar(query))
                selected.read_budget.reserve(len(payload))
                body = json.loads(payload)
                raw = b""
                digest = body["observation"].get("raw_response_digest")
                if digest is not None:
                    query = select(artifacts.c.content).where(artifacts.c.artifact_digest == digest)
                    selected.read_budget.preflight(connection, query)
                    raw = bytes(connection.scalar(query))
                    selected.read_budget.reserve(len(raw))
                    if sha256(raw).hexdigest() != digest:
                        raise ValueError("retained observation raw byte digest differs")
                detached.append(
                    (
                        ProductReference(
                            observation.task_id, observation.product_key, observation.content_digest
                        ).values(),
                        body,
                        raw,
                    )
                )
    check_active()
    return tuple(detached)


def recognition_page_selection(values, pages, options):
    """Validate the explicit page scope before opening the provider boundary."""
    if values["source_scope"] != "whole_document" or values["health"]["conversion"] != "success":
        raise ValueError("recognition requires a complete successful retained Standard source")
    available = tuple(sorted(int(number) for number in values["document"]["pages"]))
    requested = tuple(pages) or available
    if (
        len(set(requested)) != len(requested)
        or any(type(number) is not int for number in requested)
        or not set(requested) <= set(available)
    ):
        raise ValueError("recognition pages differ from exact physical page inventory")
    if options.source_recovery is not None and pages:
        raise ValueError("witnessed source recovery requires the whole original")
    return requested


def integration_draft(selected, recipe_bytes, observations, directory, options):
    """Pure deterministic selection; native input/publication authority stays outside."""
    from corpus_structure.core.method import PdfRecordPublicationDraft
    from corpus_structure.ingest.pdf import native_conversion_health
    from corpus_structure.ingest.pdf_hierarchy import load_snapshot, native_nodes
    from corpus_structure.ingest.pdf_methods import _snapshot_from_values
    from corpus_structure.ingest.pdf_stream_reconciliation import reconcile_pdf_stream

    document = load_snapshot(_snapshot_from_values(selected.product.values()))
    with reconcile_pdf_stream(
        document,
        selected.parent.values(),
        iter(observations),
        sha256(selected.product.original).hexdigest(),
        directory=directory,
        policy=options.integration_policy,
        context=selected.context,
    ) as reconciled:
        health = native_conversion_health(native_nodes(reconciled.document), "success", ())
        yield PdfRecordPublicationDraft(
            document=reconciled.document,
            product_key="integrated",
            kind="integrated",
            original=selected.product.original,
            schema_bytes=selected.product.schema_bytes,
            recipe_bytes=recipe_bytes,
            health=health,
            companions={
                **{
                    family: reconciled.journal.collection(family)
                    for family in ("input", "occurrence", "relation", "mapping_report", "coverage")
                },
                "health": ({"health": health, "source_scope": "whole_document"}, reconciled.health),
            },
            metadata={
                "inline_candidate_pages": (
                    selected.candidates.encoded(number) for number in selected.candidates.page_nos
                )
            },
        )


def _selected_pdf_execution(
    profile,
    capture,
    binding,
    execution_owner,
    check_active,
    *,
    sections=(),
    membership: Literal["direct", "descendants"] = "direct",
    pages=(),
):
    """The two finite PDF effects borrow one authenticated detached source lifetime."""
    import shutil
    from tempfile import mkdtemp

    from .pdf_contracts import store_pdf_original

    claim = execution_owner.claim
    if claim is None:
        raise ValueError("PDF effect requires an actual request claim")
    owner = (
        Path(profile.record["directory"])
        / sha256(claim.request_id.encode()).hexdigest()
        / str(claim.generation)
    )
    owner.mkdir(parents=True, exist_ok=True)
    directory = Path(mkdtemp(prefix="selected-", dir=owner))
    try:
        selected = _read_selected_pdf(
            profile.prepared,
            capture,
            binding,
            execution_owner,
            directory / "candidates",
            sections=sections,
            membership=membership,
            project_sections=profile.mode == "enriched",
            read_candidates=profile.mode != "recognized",
            check_active=check_active,
        )
        recipe_bytes = profile.recipe_bytes(pages)
        with execution_owner.engine.begin() as connection:
            store_pdf_original(
                connection,
                task_id=claim.task_id,
                attempt=claim.attempt,
                holder=claim.holder,
                original=selected.product.original,
                recipe_bytes=recipe_bytes,
            )
        yield selected, recipe_bytes, owner, directory
    finally:
        shutil.rmtree(directory)


@dataclass(frozen=True)
class PreparedPdfTransform:
    prepared: Any
    model: Any
    record: dict[str, Any]

    @property
    def mode(self):
        return self.record["mode"]

    def recipe_bytes(self, pages=()):
        record = self.record
        if self.mode == "organized":
            return canonical_bytes(
                dict(
                    recipe_id="native-organizational-headings-v2", section_policy=record["options"]
                )
            )
        if self.mode == "enriched":
            return canonical_bytes(
                dict(
                    recipe_id="native-scoped-math-v2",
                    inline_alignment_policy="native-prose-context-order-v1",
                    native_recipe=json.loads(bytes.fromhex(record["native"]["recipe"])),
                    candidate_policy="native-font-token-vector-ocr-word-v3",
                    cells_policy="all-nonempty-selected-cells-v1",
                    **record["options"],
                    crop_scale=2.0,
                )
            )
        if self.mode == "integrated":
            return canonical_bytes({"recipe_id": "pdf-integrated-source-v2", **record["options"]})
        options = dict(record["options"])
        if options.get("source_recovery") is not None:
            from corpus_structure.ingest.pdf_incumbent_recovery import ORIGINAL, PREDECESSOR

            options["source_recovery"] = {
                "recipe_id": options["source_recovery"],
                "original_digest": ORIGINAL,
                "reviewed_predecessor": PREDECESSOR,
            }
        return canonical_bytes(
            dict(
                recipe_id="pdf-recognition-observations-v1",
                recognition=sha256(bytes.fromhex(record["recognition_bytes"])).hexdigest(),
                recognition_pages=pages,
                **options,
            )
        )

    def transform(
        self,
        capture,
        *,
        binding,
        execution_owner,
        check_active,
        observations=None,
        sections=(),
        membership: Literal["direct", "descendants"] = "direct",
    ):
        from corpus_structure.orchestrate.pdf_streaming import publish_pdf_record_draft

        from .pdf_capture import PdfCaptureProduct, pdf_publication_value
        from .pdf_publication import inspect_pdf_execution_receipt
        from .pdf_record_reader import PublishedPdfReader, PublishedReadBudget

        claim = execution_owner.claim
        if claim is None:
            raise ValueError("PDF transformation requires an actual request claim")
        with contextmanager(_selected_pdf_execution)(
            self,
            capture,
            binding,
            execution_owner,
            check_active,
            sections=sections,
            membership=membership,
        ) as (selected, recipe_bytes, owner, directory):
            if self.mode == "organized":
                publication_scope = nullcontext(
                    self._organize(selected, recipe_bytes, check_active)
                )
            elif self.mode == "enriched":
                publication_scope = nullcontext(self._enrich(selected, recipe_bytes, check_active))
            elif self.mode == "integrated" and observations is not None:
                publication_scope = contextmanager(self._integrate)(
                    selected,
                    recipe_bytes,
                    observations,
                    binding,
                    execution_owner,
                    directory,
                    check_active,
                )
            else:
                raise ValueError("PDF integration requires its selected retained observation set")
            with publication_scope as draft:
                publication = publish_pdf_record_draft(
                    execution_owner.engine,
                    claim,
                    claim.holder,
                    draft,
                    directory=owner,
                    check_active=check_active,
                )
            with execution_owner.engine.connect() as connection:
                receipt = inspect_pdf_execution_receipt(
                    connection,
                    publication,
                    attempt=claim.attempt,
                    holder=claim.holder,
                    replay_key="product:" + publication.product_key,
                )
                reader = PublishedPdfReader(
                    connection,
                    ProductReference(
                        publication.task_id, publication.product_key, publication.logical_digest
                    ),
                    projection_context=self.prepared,
                    read_budget=PublishedReadBudget(
                        100, execution_owner.invocation.executor.policy.max_reply_bytes
                    ),
                    check_active=check_active,
                )
                health = [row for row in reader.iter_companions("health") if "conversion" in row]
                if len(health) != 1:
                    raise ValueError(
                        "transformed publication requires one exact whole-document health projection"
                    )
                value = pdf_publication_value(capture["document"], publication, health[0])
            schema = {
                "organized": "DdoPdfOrganizedPublication",
                "enriched": "DdoPdfEnrichedPublication",
                "integrated": "DdoPdfIntegratedPublication",
            }[self.mode]
            checked = self.prepared.validate_json(schema, json_bytes(value))
            return PdfCaptureProduct(
                canonical_bytes(checked.model_dump(mode="json", exclude_unset=True)),
                canonical_bytes(asdict(receipt)),
            )

    def recognize(self, capture, *, pages, binding, execution_owner, check_active):
        from corpus_structure.ingest.pdf_recognition import (
            NemotronRecipe,
            PreparedRecognitionSource,
            RecognitionWorker,
            repetition_recovery_recipe,
            repetitive_capped_page,
        )

        from .metadata import table
        from .pdf_integrated import PreparedPdfOriginal, store_pdf_observation
        from .pdf_observations import (
            MEANING_SPEC,
            PdfObservationExecutionReceipt,
            PdfObservationPublicationContext,
            PdfObservationSetProduct,
            PdfObservedPage,
            PdfObservedRequest,
            observation_meaning_digest,
        )

        claim = execution_owner.claim
        if claim is None:
            raise ValueError("recognition retention requires its actual native claim")
        options = PdfRecognitionOptions.model_validate(self.record["options"])
        with contextmanager(_selected_pdf_execution)(
            self, capture, binding, execution_owner, check_active, pages=pages
        ) as (selected, _, _, _):
            values = selected.product.values()
            requested = recognition_page_selection(values, pages, options)
            if options.source_recovery is not None:
                from corpus_structure.ingest.pdf_incumbent_recovery import read_source_witness

                read_source_witness(selected.product.original)
            original = PreparedPdfOriginal(selected.product.original)
            source = PreparedRecognitionSource(original.content, original.digest)
            recipe = NemotronRecipe(**self.record["recognition_recipe"])
            resources = PdfRecognitionResources.model_validate(self.record["resources"])
            selected.context.require_operation("recognize_pdf_observation")
            specification = next(
                source.content
                for source in selected.context.domain.sources
                if source.name == MEANING_SPEC
            )
            receipts, page_values = [], []

            def retain(page, actual_recipe):
                report = prepare_recognition_report(page, actual_recipe)
                origins = {}

                def publish(product):
                    with execution_owner.engine.begin() as connection:
                        digest = store_pdf_observation(
                            connection,
                            task_id=claim.task_id,
                            attempt=claim.attempt,
                            holder=claim.holder,
                            runtime_id=execution_owner.invocation.executor.runtime.runtime_id,
                            product=product,
                            context=selected.context,
                        )
                        reference = ProductReference(
                            claim.task_id, product.values()["product_key"], digest
                        )
                        products = table("ops.pdf_product")
                        origin = connection.scalar(
                            select(products.c.publication_context).where(
                                products.c.task_id == reference.task_id,
                                products.c.product_key == reference.product_key,
                                products.c.content_digest == reference.content_digest,
                            )
                        )
                    origins[reference] = PdfObservationPublicationContext.model_validate(origin)
                    return reference

                references, readings = [], []
                for ordinal, (pin, body, _) in enumerate(
                    retain_recognition_page(
                        page,
                        source,
                        actual_recipe,
                        original,
                        selected.context,
                        publish=publish,
                        structural_pin=selected.parent,
                        report=report,
                        verify_retained=options.source_recovery is not None,
                        check_active=check_active,
                    )
                ):
                    reference = ProductReference(**pin)
                    references.append(
                        PdfObservedRequest(
                            ordinal=ordinal,
                            **reference.values(),
                            publication_context=origins[reference],
                        )
                    )
                    readings.append(
                        {
                            "ordinal": ordinal,
                            "meaning_digest": observation_meaning_digest(
                                body, specification=specification
                            ),
                            "pass_role": body["observation"]["pass_role"],
                            "outcome": body["observation"]["outcome"],
                        }
                    )
                receipts.append(
                    PdfObservedPage(
                        page_no=page.page_no,
                        recipe_digest=actual_recipe.digest,
                        report_digest=sha256(report.content).hexdigest(),
                        adapter_reused=page.reused,
                        observations=tuple(references),
                    )
                )
                page_values.append(
                    {
                        "page_no": page.page_no,
                        "recipe_digest": actual_recipe.digest,
                        "outcome": json.loads(report.result)["outcome"],
                        "observations": readings,
                    }
                )

            worker = RecognitionWorker(
                python=Path(resources.python),
                script=Path(resources.script),
                endpoint=resources.endpoint,
                receipts=Path(resources.receipts),
                timeout_seconds=resources.timeout_seconds,
            )
            stream = (
                worker.replay_completed_pages(source, recipe, requested, check_active=check_active)
                if options.source_recovery is not None
                else worker.recognize_pages(
                    source,
                    recipe,
                    requested,
                    check_active=check_active,
                    concurrency=4,
                    reuse_failures=True,
                )
            )
            try:
                for page in stream:
                    retain(page, recipe)
                    if (
                        not page.succeeded
                        and options.recovery_policy is not None
                        and repetitive_capped_page(
                            page, minimum_run=options.recovery_policy["min_identical_character_run"]
                        )
                    ):
                        alternate = repetition_recovery_recipe(recipe)
                        if alternate.recipe_id != options.recovery_policy["permitted_recipe_id"]:
                            raise ValueError("recovery recipe differs from admitted policy")
                        recovery = worker.recognize_pages(
                            source,
                            alternate,
                            [page.page_no],
                            check_active=check_active,
                            reuse_failures=True,
                        )
                        try:
                            retain(next(recovery), alternate)
                            if next(recovery, None) is not None:
                                raise ValueError("recovery emitted an unrequested physical page")
                        finally:
                            recovery.close()
            finally:
                # The existing generator owns worker/process and PDF retirement,
                # including settling its bounded parallel children on close.
                stream.close()
            # Completion order is physical scheduling, not semantic page order.
            order = sorted(
                range(len(receipts)), key=lambda index: requested.index(receipts[index].page_no)
            )
            receipts = [receipts[index] for index in order]
            page_values = [page_values[index] for index in order]
            value = {
                "document": capture["document"],
                "source_digest": original.digest,
                "recipe_digest": recipe.digest,
                "pages": page_values,
            }
            checked = self.prepared.validate_json("DdoPdfObservationSet", json_bytes(value))
            receipt = PdfObservationExecutionReceipt(
                version="pdf-observation-execution-1",
                **claim.fence,
                runtime_id=execution_owner.invocation.executor.runtime.runtime_id,
                source_digest=original.digest,
                recipe_digest=recipe.digest,
                pages=tuple(receipts),
            )
            check_active()
            return PdfObservationSetProduct(
                canonical_bytes(checked.model_dump(mode="json", exclude_unset=True)),
                canonical_bytes(receipt.model_dump(mode="json")),
            )

    def _organize(self, selected, recipe_bytes, check_active):
        from dataclasses import replace

        from pydantic import TypeAdapter

        from corpus_structure.ingest.pdf_hierarchy import SectionPolicy, organize
        from corpus_structure.ingest.pdf_methods import _conversion_from_product
        from corpus_structure.ingest.pdf_record_product import native_publication_draft

        check_active()
        conversion = _conversion_from_product(selected.product, recipe_bytes, selected.candidates)
        organized = organize(
            conversion.native, TypeAdapter(SectionPolicy).validate_python(self.record["options"])
        )
        check_active()
        draft = native_publication_draft(
            conversion,
            product_key="organized",
            original=selected.product.original,
            schema_bytes=selected.product.schema_bytes,
            native=organized.document,
            recipe_bytes=recipe_bytes,
        )
        return replace(
            draft, companions={"input": ({**selected.parent.values(), "role": "structural"},)}
        )

    def _enrich(self, selected, recipe_bytes, check_active):
        from contextlib import nullcontext

        from corpus_structure.ingest.pdf import PdfRecipe
        from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
        from corpus_structure.ingest.pdf_capacity import native_before_nemotron
        from corpus_structure.ingest.pdf_selected_enrichment import enrich_selected_pdf
        from corpus_structure.ingest.pdf_worker import PdfWorker

        native = self.record["native"]
        recipe = PdfRecipe.from_bytes(bytes.fromhex(native["recipe"]))
        actual = native["assets"]
        assets = PreparedPdfAssets(
            Path(actual["root"]),
            bytes.fromhex(actual["manifest"]),
            tuple(tuple(item) for item in actual["files"]),
            tuple(tuple(item) for item in actual["repositories"]),
        )
        assets.verify()
        endpoint = native["nemotron_endpoint"]
        handoff = (
            native_before_nemotron(endpoint, check_active=check_active)
            if endpoint is not None
            else nullcontext()
        )
        with handoff:
            worker = PdfWorker(recipe, assets=assets)
            try:
                return enrich_selected_pdf(
                    selected.product,
                    selected.parent,
                    selected.sections,
                    PdfEnrichmentOptions.model_validate(self.record["options"]),
                    recipe_bytes,
                    selected.candidates,
                    worker,
                    check_active=check_active,
                )
            finally:
                worker.close()

    def _integrate(
        self, selected, recipe_bytes, value, binding, execution_owner, directory, check_active
    ):
        options = PdfIntegrationOptions.model_validate(self.record["options"])
        values = selected.product.values()
        if (
            values["source_scope"] != "whole_document"
            or values["health"]["conversion"] != "success"
        ):
            raise ValueError("integration requires a complete successful retained Standard source")
        observations = _read_selected_observations(
            value, binding, execution_owner, selected, check_active
        )
        yield from integration_draft(selected, recipe_bytes, observations, directory, options)


@dataclass(frozen=True)
class PreparedRecognitionReport:
    report: Any
    content: bytes
    result: bytes
    requests: tuple[bytes, ...]


def prepare_recognition_report(page, recipe):
    """Retain actual immutable report/request bytes, not a synthesized completion."""
    from .pdf_observations import PdfObservationPageReport, PdfObservationRequestReport

    result = (page.directory / "result.json").read_bytes()
    if json.loads(result) != dict(page.result):
        raise ValueError("recognition result bytes differ from actual adapter report")
    paths = sorted(
        path
        for path in page.directory.glob("request-*.json")
        if not path.name.endswith(".http.json")
    )
    requests = tuple(path.read_bytes() for path in paths)
    for ordinal, (path, content) in enumerate(zip(paths, requests, strict=True)):
        if (
            path.name != f"request-{ordinal:03d}.json"
            or json.loads(content).get("ordinal") != ordinal
        ):
            raise ValueError("recognition request inventory is unordered or incomplete")
    reported = page.result.get("requests")
    if not requests:
        if reported:
            raise ValueError("recognition reported requests have no retained request inventory")
        diagnostic = page.result.get("diagnostic")
        detail = f": {diagnostic}" if isinstance(diagnostic, str) and diagnostic else ""
        raise RuntimeError(
            f"recognition page {page.page_no} has no admitted request inventory{detail}"
        )
    if reported is not None and reported != [json.loads(content) for content in requests]:
        raise ValueError("recognition request bytes differ from actual adapter result")
    report = PdfObservationPageReport(
        version="pdf-recognition-page-report-1",
        page_no=page.page_no,
        recipe_digest=recipe.digest,
        result_digest=sha256(result).hexdigest(),
        requests=tuple(
            PdfObservationRequestReport(ordinal=ordinal, request_digest=sha256(content).hexdigest())
            for ordinal, content in enumerate(requests)
        ),
    )
    return PreparedRecognitionReport(
        report, canonical_bytes(report.model_dump(mode="json")), result, requests
    )


def retain_recognition_page(
    page,
    source,
    recipe,
    original,
    context,
    *,
    publish,
    structural_pin: ProductReference | None = None,
    verify_retained=False,
    report: PreparedRecognitionReport | None = None,
    check_active,
):
    """Prepare each actual retained request, then let its fenced native owner publish."""
    from corpus_structure.ingest.pdf_recognition import recognition_observation_values

    from .pdf_integrated import prepare_integrated_pdf_product

    report = prepare_recognition_report(page, recipe) if report is None else report
    if report.report.page_no != page.page_no or report.report.recipe_digest != recipe.digest:
        raise ValueError("recognition report belongs to a different page/recipe")
    retained = 0
    for ordinal, (row, raw, artifacts) in enumerate(
        page.requests(verify_retained=verify_retained, expected_requests=report.requests)
    ):
        check_active()
        observation = recognition_observation_values(page, row, raw, source=source, recipe=recipe)
        if structural_pin is not None:
            if not isinstance(structural_pin, ProductReference):
                raise ValueError(
                    "recognition structural support requires an exact nominal publication pin"
                )
            observation["inputs"] = [{**structural_pin.values(), "role": "structural"}]
        product = prepare_integrated_pdf_product(
            observation,
            original,
            recipe.to_bytes(),
            artifacts=(*artifacts, report.content, report.result, report.requests[ordinal]),
            context=context,
        )
        pin = publish(product)
        check_active()
        retained += 1
        yield pin.values(), product.values(), raw
    if retained != len(report.requests):
        raise ValueError("recognition request inventory changed during native retention")


def execute_pdf_organization(receiver, capture):
    return receiver.profile.transform(
        capture,
        binding=receiver.binding,
        execution_owner=receiver.execution_owner,
        check_active=receiver.check_active,
    )


def execute_pdf_enrichment(receiver, capture, sections, membership):
    return receiver.profile.transform(
        capture,
        sections=sections,
        membership=membership,
        binding=receiver.binding,
        execution_owner=receiver.execution_owner,
        check_active=receiver.check_active,
    )


def execute_pdf_integration(receiver, capture, observations):
    return receiver.profile.transform(
        capture,
        observations=observations,
        binding=receiver.binding,
        execution_owner=receiver.execution_owner,
        check_active=receiver.check_active,
    )


def execute_pdf_observation(receiver, capture, pages):
    return receiver.profile.recognize(
        capture,
        pages=pages,
        binding=receiver.binding,
        execution_owner=receiver.execution_owner,
        check_active=receiver.check_active,
    )


@dataclass(frozen=True)
class PreparedPdfTransformPort:
    identity: Any
    operation: Any
    profile: PreparedPdfTransform
    authorize: Any
    custody: tuple
    sources: Any
    native_selections = ()

    @property
    def logical_signature(self):
        signature = inspect.signature(_endpoint(self.profile.mode).run, eval_str=True)
        return signature.replace(parameters=tuple(signature.parameters.values())[1:])

    def _verify(self):
        from .data_operation_prepared_products import verify_prepared_product

        record = self.profile.record
        if any(
            (_root() / name).read_bytes() != bytes.fromhex(content)
            for name, content in record["files"]
        ):
            raise ValueError("PDF transformation implementation changed after acquisition")
        if self.profile.mode == "recognized" and (
            _file_hash(record["resources"]["script"]) != record["worker_digest"]
            or _file_hash(record["resources"]["python"]) != record["interpreter_digest"]
        ):
            raise ValueError("recognition worker/interpreter changed after acquisition")
        endpoint = _endpoint(self.profile.mode)
        capture_role = next(role for role in self.operation.roles if role.direction == "input")
        if self.profile.mode != "organized" and capture_role.selected != record["input_operation"]:
            raise ValueError("PDF transformation input differs from its frozen exact producer")
        implementation = {
            "organized": execute_pdf_organization,
            "enriched": execute_pdf_enrichment,
            "integrated": execute_pdf_integration,
            "recognized": execute_pdf_observation,
        }[self.profile.mode]
        asset = next(
            item
            for item in self.custody
            if item.name == "pdf-" + self.profile.mode + "/execution-custody"
        )
        if canonical_bytes(record) != asset.content:
            raise ValueError(
                "PDF transformation resource profile differs from immutable acquired custody"
            )
        verify_prepared_product(
            self.identity,
            self.profile.model,
            self.operation,
            self.sources,
            self.custody,
            assets=(
                asset,
                *((recognition_policy_asset(record),) if self.profile.mode == "recognized" else ()),
            ),
            functions=(
                (self.operation.callable_surfaces[0].declaration, endpoint.run),
                (
                    "corpus_structure.semantic.pdf_transforms." + implementation.__name__,
                    implementation,
                ),
                *(
                    (
                        "corpus_structure.semantic.pdf_transforms.PreparedPdfTransform." + name,
                        getattr(PreparedPdfTransform, name),
                    )
                    for name in (
                        "transform",
                        "recognize",
                        "_organize",
                        "_enrich",
                        "_integrate",
                        "recipe_bytes",
                    )
                ),
                ("corpus_structure.semantic.pdf_transforms._read_selected_pdf", _read_selected_pdf),
                (
                    "corpus_structure.semantic.pdf_transforms._read_selected_observations",
                    _read_selected_observations,
                ),
                (
                    "corpus_structure.semantic.pdf_transforms._selected_pdf_execution",
                    _selected_pdf_execution,
                ),
                ("corpus_structure.semantic.pdf_transforms.integration_draft", integration_draft),
                (
                    "corpus_structure.semantic.pdf_transforms.recognition_page_selection",
                    recognition_page_selection,
                ),
                (
                    "corpus_structure.semantic.pdf_transforms.retain_recognition_page",
                    retain_recognition_page,
                ),
                (
                    "corpus_structure.semantic.pdf_transforms.prepare_recognition_report",
                    prepare_recognition_report,
                ),
            ),
            authorize=self.authorize,
            required_sources=self.sources,
        )

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from corpus_structure.core.work import PreparedWork

        from .data_operation_identity import semantic_value
        from .data_operation_outcomes import successful_return_outcome
        from .data_operation_ports import PortCompletion, PortRefusal, RoleValue, _untrusted_value

        self._verify()
        if binding is None or not binding.sufficient or binding.subject_context is None:
            raise PortRefusal(
                "PDF transformation requires an authenticated sufficient subject context"
            )
        inputs = [role for role in self.operation.roles if role.direction == "input"]
        ids = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        definitions = {role.name: role for role in inputs}
        if (
            len(values) != len(inputs)
            or {value.role for value in values} != set(definitions)
            or any(
                value.kind_contract != ids[definitions[value.role].kind, "kind"] for value in values
            )
        ):
            raise PortRefusal("PDF effect requires its exact nominal selected input roles")
        schemas = {"capture": "DdoPdfPublication", "observations": "DdoPdfObservationSet"}
        typed_inputs = {
            value.role: self.profile.prepared.validate_json(
                schemas[value.role], json_bytes(_untrusted_value(value.value))
            ).model_dump(mode="json")
            for value in values
        }
        from .data_operation_identity import decode_semantic_value

        parameters = decode_semantic_value(json.loads(binding.parameters))

        def compute():
            self._verify()
            receiver = _endpoint(self.profile.mode)(
                self.profile,
                binding=binding,
                execution_owner=execution_owner,
                check_active=check_active,
            )
            result = receiver.run(**typed_inputs, **parameters)
            self._verify()
            output = next(role for role in self.operation.roles if role.direction == "output")
            schema = {
                "organized": "DdoPdfOrganizedPublication",
                "enriched": "DdoPdfEnrichedPublication",
                "integrated": "DdoPdfIntegratedPublication",
                "recognized": "DdoPdfObservationSet",
            }[self.profile.mode]
            body = self.profile.prepared.validate_json(schema, result.content).model_dump(
                mode="python", exclude_unset=True
            )
            return PortCompletion(
                self.operation.semantic_id,
                (
                    RoleValue(
                        output.name,
                        ids[output.kind, "kind"],
                        result.content,
                        canonical_bytes(semantic_value(body)),
                    ),
                ),
                outcome=successful_return_outcome(self.operation),
                pdf_execution_evidence=result.receipt
                if self.profile.mode != "recognized"
                else None,
                pdf_observation_evidence=result.receipt
                if self.profile.mode == "recognized"
                else None,
            )

        (result,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        check_active()
        return result


def resolve_pdf_transform_port(
    prepared, model, operation, *, identity, authorize, custody, sources, mode
):
    records = [item for item in custody if item.name == "pdf-" + mode + "/execution-custody"]
    if len(records) != 1:
        raise ValueError("PDF transformation lacks its exact captured resource profile")
    profile = PreparedPdfTransform(prepared, model, json.loads(records[0].content))
    if profile.mode != mode:
        raise ValueError("PDF transformation profile changes its acquired capability")
    port = PreparedPdfTransformPort(
        identity, model.operation(operation), profile, authorize, custody, sources
    )
    port._verify()
    return port
