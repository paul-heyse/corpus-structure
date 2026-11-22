"""Coordinate and source closure for declared formal and navigation evidence.

These checks establish representation fidelity, not linguistic or scientific truth.
"""

from decimal import Decimal


def _field(record, name, default):
    if name not in record:
        return default
    return record[name]


def validate_formal_positions(indexes):
    """Check formal source correspondence and the positioned symbolic inventory."""
    annotations = indexes["annotations"]
    occurrences = indexes["occurrences"]
    for key in annotations:
        annotation = annotations[key]
        formal_input = _field(annotation, "formal_input", None)
        if annotation["kind"] == "formal.input" and formal_input is None:
            raise ValueError("formal input annotation requires typed input")
        if (
            annotation["kind"] in {"formal.rule", "formal.token", "formal.symbol"}
            and "formal" not in annotation
        ):
            raise ValueError("formal node annotation requires typed positions")
        if formal_input is None:
            continue
        parent = formal_input["parent_occurrence"]
        if parent not in occurrences or parent not in _field(annotation, "occurrences", ()):
            raise ValueError("formal input requires its literal parent occurrence")
        normalized_input = formal_input["representation"] == "normalized_latex"
        if normalized_input:
            recipe = _field(formal_input, "normalization_recipe", "")
            if type(recipe) is not str:
                raise ValueError("normalized formal input requires its normalization recipe")
            if not recipe.strip():
                raise ValueError("normalized formal input requires its normalization recipe")
        parent_extents = occurrences[parent]["extents"]
        if normalized_input and (
            any(e["synthetic"] or "text" not in e for e in parent_extents)
            or _field(formal_input, "original_text", None)
            != "".join(e["text"] for e in parent_extents)
        ):
            raise ValueError("normalized formal input requires its exact original source text")
        position = 0
        for correspondence in _field(formal_input, "correspondence", ()):
            start, end = correspondence["input_start"], correspondence["input_end"]
            if not 0 <= start <= end <= len(formal_input["text"]):
                raise ValueError("formal correspondence is outside input")
            if normalized_input and (start != position or end <= start):
                raise ValueError("normalized correspondence requires an ordered complete partition")
            position = end
            refs = _field(correspondence, "source_occurrences", ())
            if any(ref not in occurrences for ref in refs):
                raise ValueError("formal correspondence has unknown source occurrence")
            relation = correspondence["relation"]
            if relation == "synthetic":
                if refs or "boundary" not in correspondence:
                    raise ValueError(
                        "synthetic correspondence requires a boundary, no literal source"
                    )
                if not any(
                    _field(e, "start", -1) <= correspondence["boundary"] <= _field(e, "end", -1)
                    for e in occurrences[parent]["extents"]
                ):
                    raise ValueError("synthetic correspondence boundary is outside parent source")
            elif not refs:
                raise ValueError("formal correspondence requires source support")
            if relation == "contained_in_atom" and refs != [parent]:
                raise ValueError("recognized interior must retain its parent atom")
            if normalized_input and (
                relation == "contained_in_atom"
                or any(
                    e["synthetic"] or "text" not in e
                    for ref in refs
                    for e in occurrences[ref]["extents"]
                )
            ):
                raise ValueError("normalized correspondence requires literal source support")
            if normalized_input and any(
                not any(
                    all(
                        _field(e, key, None) == _field(p, key, None)
                        for key in ("projection", "native_pointer")
                    )
                    and all(key in extent for extent in (p, e) for key in ("start", "end"))
                    and p["start"] <= e["start"] <= e["end"] <= p["end"]
                    for p in parent_extents
                )
                for ref in refs
                for e in occurrences[ref]["extents"]
            ):
                raise ValueError("normalized correspondence source is outside its parent")
            if relation == "exact":
                extents = [e for ref in refs for e in occurrences[ref]["extents"]]
                if any(e["synthetic"] or "text" not in e for e in extents):
                    raise ValueError("exact formal correspondence requires literal text")
                if "".join(e["text"] for e in extents) != formal_input["text"][start:end]:
                    raise ValueError("formal correspondence differs from literal source")
        if normalized_input and position != len(formal_input["text"]):
            raise ValueError("normalized correspondence requires an ordered complete partition")
    parents = {
        key: row["formal"]["symbol_parent"]
        for key in annotations
        if "symbol_parent" in _field(row := annotations[key], "formal", {})
    }
    settled = set()
    for key in parents:
        pending = set()
        while key in parents and key not in settled:
            if key in pending:
                raise ValueError("formal symbol parent cycle")
            pending |= {key}
            key = parents[key]
        settled |= pending
    for key in annotations:
        annotation = annotations[key]
        formal = _field(annotation, "formal", None)
        if formal is None:
            continue
        root = _field(_field(annotations, formal["input_id"], {}), "formal_input", None)
        if root is None:
            raise ValueError("formal node requires a typed input root")
        start, end = formal["start"], formal["end"]
        if "symbol_parent" in formal:
            parent = _field(annotations, formal["symbol_parent"], {})
            positions = _field(parent, "formal", {})
            if (
                _field(parent, "kind", None) != "formal.symbol"
                or _field(positions, "input_id", None) != formal["input_id"]
                or not _field(positions, "start", end + 1)
                <= start
                <= end
                <= _field(positions, "end", -1)
            ):
                raise ValueError("formal symbol parent differs from positioned enclosing symbol")
        if not 0 <= start <= end <= len(root["text"]):
            raise ValueError("formal node is outside represented input")
        if start == end and not _field(formal, "synthetic", False):
            raise ValueError("empty formal node requires synthetic boundary status")
        if ("container_start" in formal) != ("container_end" in formal):
            raise ValueError("formal container requires both endpoints")
        if "container_start" in formal and not (
            0
            <= formal["container_start"]
            <= start
            <= end
            <= formal["container_end"]
            <= len(root["text"])
        ):
            raise ValueError("formal container does not enclose visible extent")


def _decimal_digits(value: str) -> bool:
    return bool(value) and all("0" <= char <= "9" for char in value)


def _unsigned(value: str) -> str:
    return value[1:] if value and value[0] in "+-" else value


def _decimal_spelling(value: str) -> bool:
    mantissa, exponent_mark, exponent = value.lower().partition("e")
    if exponent_mark and not _decimal_digits(_unsigned(exponent)):
        return False
    whole, dot, fractional = str(_unsigned(mantissa)).partition(".")
    if not dot:
        return _decimal_digits(whole)
    return bool(whole or fractional) and (
        (not whole or _decimal_digits(whole)) and (not fractional or _decimal_digits(fractional))
    )


def validate_formal_normalization(annotations):
    """Check finite numeric meaning for formal normalization assertions."""
    for key in annotations:
        annotation = annotations[key]
        normalized = _field(_field(annotation, "formal", {}), "normalized", {})
        kind = _field(normalized, "kind", None)
        status = _field(normalized, "domain_status", None)
        if (kind in {"decimal", "threshold"} and status == "valid") or (
            kind == "threshold" and status == "unresolved"
        ):
            spelling = _field(normalized, "value", "")
            if type(spelling) is not str or not _decimal_spelling(spelling):
                raise ValueError("formal decimal requires exact finite decimal text")
            try:
                value = Decimal(spelling)
            except ArithmeticError as exc:
                raise ValueError("formal decimal requires exact decimal text") from exc
            if type(value) is not Decimal:
                raise ValueError("formal decimal must have exact native representation")
            if not value.is_finite():
                raise ValueError("formal decimal must be finite")


def validate_navigation_evidence(indexes):
    annotations = indexes["annotations"]
    occurrences = indexes["occurrences"]
    for annotation in annotations.values():
        navigation = annotation.get("navigation")
        if annotation["kind"] == "construction.navigation" and navigation is None:
            raise ValueError("navigation annotation requires typed source fields")
        if navigation is not None:
            if (
                annotation["kind"] != "construction.navigation"
                or annotation["family"] != "construction.navigation"
            ):
                raise ValueError("navigation fields require their declared annotation family")
            roles = navigation.get("roles", ())
            if len({role["role"] for role in roles}) != len(roles):
                raise ValueError("navigation role identity repeats")
            refs = [ref for role in roles for ref in role["occurrences"]]
            if (
                not refs
                or any(ref not in occurrences for ref in refs)
                or set(refs) != set(annotation.get("occurrences", ()))
            ):
                raise ValueError(
                    "navigation roles must conserve their annotation source occurrences"
                )
            if any(
                e["synthetic"] or "text" not in e
                for ref in refs
                for e in occurrences[ref]["extents"]
            ):
                raise ValueError("navigation fields require literal source evidence")
            for label in navigation.get("source_labels", ()):
                if (
                    not label["occurrences"]
                    or any(ref not in refs for ref in label["occurrences"])
                    or "".join(
                        e["text"]
                        for ref in label["occurrences"]
                        for e in occurrences[ref]["extents"]
                    )
                    != label["value"]
                ):
                    raise ValueError("navigation source label differs from its literal source")
            if any(
                token["native_node"] not in annotation.get("external_premises", ())
                for token in navigation.get("native_tokens", ())
            ):
                raise ValueError("navigation native token requires its external premise")
