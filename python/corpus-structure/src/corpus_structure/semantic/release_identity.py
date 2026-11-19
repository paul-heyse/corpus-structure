"""Material release identity shared by preparation and immutable archive custody."""

from dataclasses import asdict, replace
from hashlib import sha256

from .identity import canonical_bytes

MANIFEST_VERSION = "semantic-release-manifest-2"


def material_dependencies(dependencies):
    return replace(
        dependencies,
        artifacts=tuple(
            item
            for item in dependencies.artifacts
            if not (item.authoring_provenance or item.runtime_transport)
        ),
    )


def release_manifest(bundle, dependencies, profile, prepared, libraries):
    from .archive_wire import encode_products
    from .determinants import BOUNDARY_LIBRARIES, SCIENTIFIC_LIBRARIES

    products = encode_products(prepared)
    products.pop("release_id")
    artifacts = {item.kind: item for item in prepared.artifacts}
    model = artifacts.get("data_operations.json")
    interfaces = artifacts.get("data_operation_source_interfaces.json")
    runtime_libraries = BOUNDARY_LIBRARIES
    if "operation/scientific-policy.json" in artifacts:
        runtime_libraries += SCIENTIFIC_LIBRARIES
    return canonical_bytes(
        {
            "version": MANIFEST_VERSION,
            "root": bundle.root,
            "profile": asdict(profile),
            "libraries": {name: libraries[name] for name in runtime_libraries},
            "sources": sorted((item.name, item.digest) for item in bundle.sources),
            "dependencies": sorted(
                (item.name, item.digest) for item in material_dependencies(dependencies).artifacts
            ),
            "ontology_sources": sorted(dependencies.ontology_sources),
            "vocabularies": [asdict(item) for item in prepared.vocabularies],
            "artifacts": sorted((item.kind, item.digest) for item in prepared.artifacts),
            "products_digest": sha256(canonical_bytes(products)).hexdigest(),
            **({"data_operation_model": model.digest} if model else {}),
            **({"data_operation_source_interfaces": interfaces.digest} if interfaces else {}),
        }
    )
