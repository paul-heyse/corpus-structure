"""Declared original-relative record pins and their selected schema projection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .data_operation_model import BoundRoleMember, SubjectContext, json_context_meaning
from .observations import observation_inputs
from .source_products import FrozenNativeSource
from .types import SourceArtifact, SourceBundle


@dataclass(frozen=True)
class DeclaredRecordSource:
    """Existing coordinate, complete subject context and semantic member selection.

    This introduces no new identity hash and contains no task/run/view-row alias.
    Selected execution/support references remain in the native input binding.
    """

    document: str
    projection: str
    section_pointer: str
    membership: str
    context: SubjectContext
    product: str
    member: str | None
    kind_contract: str

    @classmethod
    def from_bound(cls, source: FrozenNativeSource, member: BoundRoleMember, *, project: str):
        coordinate = source.value["source"]
        if coordinate["document"] != member.original_source:
            raise ValueError("selected native source differs from its bound original document")
        return cls(
            coordinate["document"], coordinate["projection"],
            coordinate["section_pointer"], coordinate["membership"],
            SubjectContext(project, member.subject, member.original_source, member.analyzed_scope),
            member.product, member.member, member.kind_contract,
        )

    def pin(self) -> dict[str, Any]:
        return {
            "source": self.context.subject,
            "document": self.document,
            "projection_digest": self.projection,
            "section_pointer": self.section_pointer,
            "membership": self.membership,
            "project_id": self.context.project_id,
            "original_source": self.context.original_source,
            "analyzed_scope_meaning": json_context_meaning(self.context.analyzed_scope).decode(),
            "source_product": self.product,
            **({"source_member": self.member} if self.member is not None else {}),
            "kind_contract": self.kind_contract,
        }


def declared_record_inputs(bundle: SourceBundle) -> SourceBundle:
    """Project the existing record model at the selected declared-source boundary.

    Legacy/default and frozen observation artifacts retain their exact pin contract.
    A target release receives a different pin shape and consequently a different
    kind contract. No caller edits a parallel record schema or weakens old fields.
    """
    canonical = (Path(__file__).parents[1] / "model/semantic/observations.yaml").read_bytes()
    supplied = next((item.content for item in bundle.sources if item.name == "observations"), canonical)
    module = yaml.safe_load(supplied)
    prior = module["classes"]["RecordSourcePin"]["attributes"]
    canonical_attributes = yaml.safe_load(canonical)["classes"]["RecordSourcePin"]["attributes"]
    module["classes"]["RecordSourcePin"]["description"] = (
        "Declared semantic source/member and original-relative coordinates with complete context; "
        "task, run and source-view row identities are not source meaning."
    )
    module["classes"]["RecordSourcePin"]["attributes"] = {
        name: {"range": "string", **({"required": True} if name != "source_member" else {})}
        for name in (
            "source", "document", "projection_digest", "section_pointer", "membership",
            "project_id", "original_source", "analyzed_scope_meaning", "source_product",
            "source_member", "kind_contract",
        )
    }
    module["classes"]["RecordSourcePin"]["attributes"]["projection_digest"]["pattern"] = "^[0-9a-f]{64}$"
    if prior not in (canonical_attributes, module["classes"]["RecordSourcePin"]["attributes"]):
        raise ValueError("declared record projection refuses an independently changed source pin")
    content = yaml.safe_dump(module, sort_keys=True).encode()
    names = {item.name for item in bundle.sources}
    if "observations" in names:
        sources = tuple(
            SourceArtifact(item.name, content) if item.name == "observations" else item
            for item in bundle.sources
        )
        return SourceBundle(bundle.root, sources)
    return observation_inputs(bundle, model_content=content)
