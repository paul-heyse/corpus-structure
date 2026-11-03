"""Explicit synthetic producer declarations for owned native test releases."""

from dataclasses import replace

import yaml

from corpus_structure.semantic.contracts import trusted_execution_inputs
from corpus_structure.semantic.types import SourceArtifact

# Test producers are named fixtures, never a production wildcard or inferred output list.
FIXTURE_METHODS = {
    "read": ("ingest", "deterministic", ("reading", "record", "author_markup")),
    "owned": ("profile", "deterministic", ()),
    "agent": ("agent", "agent", ()),
    "agent-disposition": ("agent", "agent", ()),
    "contract-unit": ("profile", "cpu", ()),
    "custom.agent": ("agent", "agent", ()),
    "native-binding": ("ingest", "deterministic", ()),
    "native.packet-fixture": ("agent", "agent", ()),
    "native.region-frame": ("agent", "agent", ()),
    "coverage.witness": ("extract", "deterministic", ()),
    "private.records": ("record", "deterministic", ("record",)),
    "private.source": ("ingest", "deterministic", ()),
    **{name: ("ingest", "deterministic", ()) for name in (
        "pdf.adoption-fixture", "pdf.consumer-fixture", "pdf.controlled-retained-fixture",
        "pdf.controlled-source", "pdf.fixture", "pdf.inline-fixture", "pdf.ocr-fixture",
        "pdf.stage.fixture", "pdf.view-fixture", "pdf13.fixture",
    )},
}


def fixture_execution_inputs(*methods: str, inputs=None):
    """Callers select literal fixtures; one archived execution product owns their dimensions."""
    inputs = trusted_execution_inputs() if inputs is None else inputs
    catalog = yaml.safe_load(inputs.catalog.content)
    operation = next(o for o in catalog["operations"] if o["id"] == "configure_method")
    for method in methods:
        family, tier, reports = FIXTURE_METHODS[method]
        declarations = {"family": ("family", (family,)), "tier": ("tier", (tier,)),
                        "result.outcome": ("outcome", ("produced", "empty", "failed"))}
        if reports:
            declarations |= {"observation.family": ("observations.family", reports),
                             "observation.outcome": ("observations.outcome", ("produced", "empty", "failed"))}
        for dimension, (field, values) in declarations.items():
            key = f"fixture.{method}/{dimension}"
            catalog["outcome_domains"].append({"id": key, "authority": "code", "values": list(values)})
            operation["result_dimensions"].append({"id": f"{method}/{dimension}", "field": field,
                                                    "outcome_domain": key})
    return replace(inputs, catalog=SourceArtifact(inputs.catalog.name, yaml.safe_dump(catalog,sort_keys=False).encode()))


def prepare_fixture_pack(pack, *methods):
    """Explicit acquired pack inputs keep their source bytes and declared test producers together."""
    from corpus_structure.semantic import prepare_release
    from corpus_structure.semantic.regeneration import acquire_pack, compose_pack_inputs

    acquired = acquire_pack(pack)
    acquired = replace(acquired, execution=fixture_execution_inputs(*methods, inputs=acquired.execution))
    bundle, deps, profile = compose_pack_inputs((acquired,))
    return bundle, deps, profile, prepare_release(bundle, deps, profile)
