"""Coordinate and population closure for retained native/formal evidence.

These checks establish representation fidelity, not linguistic or scientific truth.
"""

import re
from decimal import Decimal, InvalidOperation


def validate_evidence(data, indexes):
    annotations = indexes["annotations"]
    occurrences = indexes["occurrences"]
    runs = {run["local_id"]: run for run in data.get("native_runs", ())}
    if len(runs) != len(data.get("native_runs", ())):
        raise ValueError("duplicate native run identity")
    tokens = {}
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
        token = annotation.get("native_token")
        if annotation["kind"] == "native.token" and token is None:
            raise ValueError("native token requires typed columns")
        if token is not None:
            if token["native_run"] not in runs or annotations.get(token["container"], {}).get(
                "kind"
            ) not in {"native.block", "native.sentence"}:
                raise ValueError("native token requires its run and container")
            if (
                token.get("sentence") is not None
                and annotations.get(token["sentence"], {}).get("kind") != "native.sentence"
            ):
                raise ValueError("native token has unknown sentence")
            sources = annotation.get("occurrences", ())
            if not sources or any(ref not in occurrences for ref in sources):
                raise ValueError("native token requires its exact source occurrence")
            extents = [e for ref in sources for e in occurrences[ref]["extents"]]
            if (
                any(e["synthetic"] or "text" not in e for e in extents)
                or "".join(e["text"] for e in extents) != token["text"]
            ):
                raise ValueError("native token text differs from literal source")
            population = (token["native_run"], token["container"])
            indices = tokens.setdefault(population, {})
            if token["index"] in indices:
                raise ValueError("duplicate native token index within container")
            indices[token["index"]] = token
        formal_input = annotation.get("formal_input")
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
        if parent not in occurrences or parent not in annotation.get("occurrences", ()):
            raise ValueError("formal input requires its literal parent occurrence")
        normalized_input = formal_input["representation"] == "normalized_latex"
        if normalized_input and not formal_input.get("normalization_recipe", "").strip():
            raise ValueError("normalized formal input requires its normalization recipe")
        parent_extents = occurrences[parent]["extents"]
        if normalized_input and (
            any(e["synthetic"] or "text" not in e for e in parent_extents)
            or formal_input.get("original_text") != "".join(e["text"] for e in parent_extents)
        ):
            raise ValueError("normalized formal input requires its exact original source text")
        position = 0
        for correspondence in formal_input.get("correspondence", ()):
            start, end = correspondence["input_start"], correspondence["input_end"]
            if not 0 <= start <= end <= len(formal_input["text"]):
                raise ValueError("formal correspondence is outside input")
            if normalized_input and (start != position or end <= start):
                raise ValueError("normalized correspondence requires an ordered complete partition")
            position = end
            refs = correspondence.get("source_occurrences", ())
            if any(ref not in occurrences for ref in refs):
                raise ValueError("formal correspondence has unknown source occurrence")
            relation = correspondence["relation"]
            if relation == "synthetic":
                if refs or "boundary" not in correspondence:
                    raise ValueError(
                        "synthetic correspondence requires a boundary, no literal source"
                    )
                if not any(
                    e.get("start", -1) <= correspondence["boundary"] <= e.get("end", -1)
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
                        e.get(key) == p.get(key)
                        for key in ("projection", "source_view_id", "native_pointer")
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
    from corpus_structure.methods.model_observation import validate_pm2_batch_receipt

    from .observations import source_python

    for annotation in annotations.values():
        receipt_value = annotation.get("native_batch")
        native_sentence = (
            annotation["kind"] == "native.sentence" and annotation["family"] == "hanlp.tokens"
        )
        if receipt_value is None:
            if (
                native_sentence
                and data["operation"]["key"] == "text.native_evidence"
                and data["operation"]["version"] == "2"
            ):
                raise ValueError("current HanLP sentence requires its physical batch receipt")
            continue
        if not native_sentence:
            raise ValueError("native batch receipt requires a HanLP sentence")
        receipt = source_python(receipt_value)
        population = tokens.get(("hanlp", annotation["local_id"]))
        if population is None:
            raise ValueError("native batch sentence lacks its canonical token population")
        sentence = [population[index]["text"] for index in sorted(population)]
        validate_pm2_batch_receipt(receipt, sentence, "hanlp")

    for indices in tokens.values():
        for token in indices.values():
            if "native_head" in token:
                if "head_index_base" not in token:
                    raise ValueError("native head requires its index scheme")
                head = token["native_head"]
                base = token["head_index_base"]
                if not (base == 1 and head == 0) and head - base not in indices:
                    raise ValueError("native head is outside token population")
    parents = {
        key: row["formal"]["symbol_parent"]
        for key, row in annotations.items()
        if "symbol_parent" in row.get("formal", {})
    }
    settled = set()
    for key in parents:
        pending = set()
        while key in parents and key not in settled:
            if key in pending:
                raise ValueError("formal symbol parent cycle")
            pending.add(key)
            key = parents[key]
        settled.update(pending)
    for annotation in annotations.values():
        formal = annotation.get("formal")
        if formal is None:
            continue
        root = annotations.get(formal["input_id"], {}).get("formal_input")
        if root is None:
            raise ValueError("formal node requires a typed input root")
        start, end = formal["start"], formal["end"]
        if "symbol_parent" in formal:
            parent = annotations.get(formal["symbol_parent"], {})
            positions = parent.get("formal", {})
            if (
                parent.get("kind") != "formal.symbol"
                or positions.get("input_id") != formal["input_id"]
                or not positions.get("start", end + 1) <= start <= end <= positions.get("end", -1)
            ):
                raise ValueError("formal symbol parent differs from positioned enclosing symbol")
        if not 0 <= start <= end <= len(root["text"]):
            raise ValueError("formal node is outside represented input")
        if start == end and not formal.get("synthetic", False):
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
        normalized = formal.get("normalized", {})
        if (
            normalized.get("kind") in {"decimal", "threshold"}
            and normalized.get("domain_status") == "valid"
        ):
            if not re.fullmatch(
                r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?",
                normalized.get("value", ""),
            ):
                raise ValueError("formal decimal requires exact finite decimal text")
            try:
                value = Decimal(normalized["value"])
            except (InvalidOperation, KeyError) as exc:
                raise ValueError("formal decimal requires exact decimal text") from exc
            if not value.is_finite():
                raise ValueError("formal decimal must be finite")
