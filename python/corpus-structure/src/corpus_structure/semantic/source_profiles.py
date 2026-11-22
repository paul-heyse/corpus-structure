"""Source metrics over exact retained text intervals, without text recognition."""

SOURCE_RATIO_DECIMAL_PLACES = 6
SOURCE_RATIO_EMPTY_FRACTION = 0.0


def _parent(atom) -> str | None:
    if "parent" not in atom:
        return ""
    parent = atom["parent"]
    return parent if isinstance(parent, str) or parent is None else parent["$ref"]


def _under(pointer: str | None, ancestor: str, atoms: dict) -> bool:
    seen = ()
    while pointer:
        if pointer == ancestor:
            return True
        if pointer in seen:
            raise ValueError("source ancestry is cyclic")
        if pointer not in atoms:
            raise ValueError("source ancestry is unavailable for the requested selector")
        seen += (pointer,)
        atom = atoms[pointer]
        pointer = _parent(atom)
    return False


def _selected(piece: dict, selectors: list, atoms: dict) -> list:
    ranges = [
        (
            max(piece["start"], selector["start"] if "start" in selector else piece["start"]),
            min(piece["end"], selector["end"] if "end" in selector else piece["end"]),
        )
        for selector in selectors
        if (
            "native_pointer" not in selector
            or (
                piece["kind"] == "native_text"
                and _under(piece["item_ref"], selector["native_pointer"], atoms)
            )
        )
        and (
            "page" not in selector
            or (
                piece["kind"] == "native_text"
                and any(
                    page["page_no"] == selector["page"] for page in atoms[piece["item_ref"]]["prov"]
                )
            )
        )
    ]
    # Partition at selector endpoints, then retain covered intervals exactly once.
    # Overlapping selectors never multiply characters or math observations.
    points = sorted({endpoint for span in ranges for endpoint in span})
    return [
        (points[index], points[index + 1])
        for index in range(len(points) - 1)
        if any(left <= points[index] and points[index + 1] <= right for left, right in ranges)
    ]


def source_profile_values(source) -> dict:
    atoms = {atom["self_ref"]: atom for atom in (*source["items"], *source["ancestors"])}
    selected = [(piece, _selected(piece, source["selectors"], atoms)) for piece in source["pieces"]]
    chars = sum(end - start for _, spans in selected for start, end in spans)
    math = [
        (piece, spans)
        for piece, spans in selected
        if spans
        and piece["kind"] == "native_text"
        and atoms[piece["item_ref"]]["label"] == "formula"
    ]
    parents = [_parent(atoms[piece["item_ref"]]) for piece, _ in math]
    labels = [atoms[parent]["label"] if parent in atoms else "unavailable" for parent in parents]
    if "unavailable" in labels:
        raise ValueError("math layout parent is unavailable")
    inside = sum(end - start for _, spans in math for start, end in spans)
    return {
        "source": source["source"],
        "selectors": source["selectors"],
        "chars": chars,
        "math_share": round(inside / chars, SOURCE_RATIO_DECIMAL_PLACES)
        if chars
        else SOURCE_RATIO_EMPTY_FRACTION,
        "inline_math": sum(label == "inline" for label in labels),
        "display_math": sum(label not in ("inline", "table") for label in labels),
    }


def source_profile_inputs(bundle):
    from pathlib import Path

    import yaml

    from .source_products import source_product_inputs
    from .types import SourceArtifact, SourceBundle

    bundle = source_product_inputs(bundle)
    model = Path(__file__).parents[1] / "model/semantic/data-operation-source-profile.yaml"
    return SourceBundle(
        "data_operation_source_profile_root",
        (
            *bundle.sources,
            SourceArtifact("data_operation_source_profile", model.read_bytes()),
            SourceArtifact(
                "data_operation_source_profile_root",
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:source-profile-root",
                        "name": "data_operation_source_profile_root",
                        "imports": [bundle.root, "data_operation_source_profile"],
                    }
                ).encode(),
            ),
        ),
    )


def source_profile_numerical_asset():
    from pathlib import Path

    from .identity import canonical_bytes
    from .source_profile_numerics import source_ratio_numerical_policy
    from .types import SourceArtifact

    return SourceArtifact(
        "source-profile/numerical-policy",
        canonical_bytes(
            {
                "numerical_policy": source_ratio_numerical_policy().model_dump(mode="json"),
                "implementation": Path(__file__)
                .with_name("source_profile_numerics.py")
                .read_bytes()
                .hex(),
            }
        ),
    )


def source_profile_declarations():
    from .data_operation_version import MODEL_VERSION
    from .identity import canonical_bytes
    from .nominal_schema_kinds import nominal_schema_kinds
    from .source_profile_numerics import SourceRatioNumericalPolicy
    from .types import SourceArtifact

    return SourceArtifact(
        "source-profile/numerical-kinds",
        canonical_bytes(
            {
                "version": MODEL_VERSION,
                "kinds": nominal_schema_kinds(
                    SourceRatioNumericalPolicy.model_json_schema(),
                    namespace="urn:corpus:kind:source-profile:",
                    root_name="NumericalPolicy",
                ),
            }
        ),
    )


def source_profile_operation_sources():
    from pathlib import Path

    from .python_operation_sources import PythonSource, PythonSourceCollection

    root = Path(__file__).parents[1]
    return PythonSourceCollection(
        tuple(
            PythonSource(module, path.read_bytes(), str(path))
            for module, path in (
                ("corpus_structure.methods.source_profile", root / "methods/source_profile.py"),
                ("corpus_structure.semantic.source_profiles", Path(__file__)),
            )
        ),
        boundary_contracts=(source_profile_numerical_asset(),),
    )
