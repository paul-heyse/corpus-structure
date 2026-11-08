"""Replay a retained assertion request and observe GLiNER's coordinate spaces."""

import importlib.metadata
import json
import sys
from dataclasses import replace
from hashlib import sha256

from corpus_structure.methods.gliner import (
    GlinerInput,
    GlinerPack,
    load_model,
    prepare_input,
)
from corpus_structure.methods.m1_source import M1Config
from corpus_structure.methods.model_observation import installed_policy
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def retained_request():
    with (
        open_runtime_engine(Settings(), "gliner-assertion-anchor", purpose="read") as engine,
        engine.connect() as conn,
    ):
        body, params = conn.exec_driver_sql(
            """select r.body,c.params from ops.task_result r
            join ops.task t on t.id=r.task_id join ops.method_config c on c.id=t.method_config_id
            where r.task_id=1866 and t.run_id=401"""
        ).one()
        detail = source_python(body["parse_detail"])
        (failure,) = (row for row in detail["execution"] if row["outcome"] == "failed")
        index = failure["context"]
        source = detail["source_pin"]
        projection, digest = conn.exec_driver_sql(
            "select projection, projection_digest from kb.source_view where id=%s",
            (source["source_view_id"],),
        ).one()
        earlier_id, earlier_projection, earlier_digest = conn.exec_driver_sql(
            """select v.id, v.projection, v.projection_digest from ops.run_source_view s
            join kb.source_view v on v.id=s.source_view_id
            where s.run_id=378 and v.section_pointer=%s and v.membership=%s
              and v.native_task_id=%s and v.native_content_digest=%s""",
            (
                source["section_pointer"],
                source["membership"],
                source["native_product"]["task_id"],
                source["native_product"]["content_digest"],
            ),
        ).one()
    assert (
        digest == source["projection_digest"] == sha256(canonical_bytes(projection)).hexdigest()
    )
    pieces = detail["contexts"][index]["pieces"]
    assert all(
        piece["source_view_id"] == source["source_view_id"]
        and piece["coordinate_space"] == "native_projection"
        for piece in pieces
        if "source_view_id" in piece
    )

    def assemble(projection):
        return "".join(
            projection["text"][piece["start"] : piece["end"]]
            if "source_view_id" in piece
            else piece["text"]
            for piece in pieces
        )

    text = assemble(projection)
    assert earlier_digest == sha256(canonical_bytes(earlier_projection)).hexdigest()
    assert text == assemble(earlier_projection)
    (control,) = (
        entry["report"]
        for entry in detail["reports"]
        if entry["context"] == index and entry["family"] == "definition"
    )
    preparation = control["preparation"]
    assert (
        sha256((text + preparation["synthetic_suffix"]).encode()).hexdigest()
        == preparation["consumed_text_sha256"]
    )
    packs = {
        family: pack
        for payload in detail["schema_packs"].values()
        for pack in (GlinerPack(**payload),)
        for family in json.loads(pack.declaration_json)["structures"]
    }
    assert control["pack"] == packs["definition"].fingerprint
    return M1Config.model_validate(params), packs, failure, control, text, earlier_id


def main():
    cfg, packs, failure, control, text, earlier_id = retained_request()
    model, effective = load_model(cfg.profile())
    assert sha256(effective.encode()).hexdigest() == control["effective_profile_ref"]
    item = GlinerInput(control["context_id"], control["context_digest"], text)
    inference, _ = installed_policy()
    settings = {
        key: value for key, value in inference["inference"].items() if key != "operation"
    }
    diagnostic = []
    results = {}

    def trace(frame, event, arg):
        if event == "call":
            if frame.f_code.co_name == "_format_field" and frame.f_globals.get("__name__") == (
                "gliner2.models.boundary.engine"
            ):
                return trace
            return None
        if event != "exception" or "out of range" not in str(arg[1]):
            return trace
        local = frame.f_locals
        outer = frame.f_back.f_locals
        offset = local["offset"]
        sample = local["sample_index"]
        tokens = local["batch"].text_tokens[sample]
        anchor = local["anchor_span"]
        choice = (local["ts_raw"], local["te_raw"])
        spec = outer["spec"]
        anchor_field = next(
            field for field in spec.fields if field.query_id == spec.anchor_query_id
        )
        index = local["record_index"]
        diagnostic.append(
            {
                "record_mode": spec.mode,
                "anchor_field": anchor_field.name,
                "anchor_query": anchor_field.query_id,
                "anchor_field_choices": outer["metadata"]["field_metadata"]
                .get(f"{spec.task_name}.{anchor_field.name}", {})
                .get("choices"),
                "packed_shared_path": outer["packed_record_output"] is not None,
                "record_index": index,
                "decoded_anchors": local["record_anchors"],
                "offset": offset,
                "source_word_count": len(local["end_map"]),
                "prefix_tokens": tokens[:offset],
                "source_tokens": tokens[offset:],
                "anchor": anchor,
                "anchor_tokens": tokens[anchor[0] : anchor[1]],
                "anchor_in_source_coordinates": [bound - offset for bound in anchor],
                "anchor_score": local["self"]._candidate_span_probability(
                    outer["candidates"], sample, anchor_field.query_id, *anchor
                ),
                "choice_field": local["fspec"].name,
                "choice_surface": local["surface"],
                "choice": choice,
                "choice_tokens": tokens[choice[0] : choice[1]],
            }
        )
        return trace

    for family, spans in (
        ("definition", True),
        ("assertion", True),
        ("assertion", False),
    ):
        schema = packs[family].compile()
        prepared = prepare_input(model, schema, item, cfg.profile())
        invocation = f"{family}/spans={spans}"
        sys.settrace(trace if family == "assertion" else None)
        try:
            raw = model.batch_extract(
                [text],
                schema,
                batch_size=1,
                threshold=cfg.threshold,
                overlap_policy="flat",
                **{**settings, "include_spans": spans},
            )
        except ValueError as error:
            results[invocation] = {"error": f"{type(error).__name__}: {error}"}
        else:
            results[invocation] = {
                "returned": True,
                "matches_retained": family == "definition"
                and raw[0] == json.loads(control["raw_json"]),
            }
        finally:
            sys.settrace(None)
        results[invocation]["preparation"] = {
            "words": prepared.words,
            "subwords": prepared.subwords,
            "synthetic_suffix": prepared.synthetic_suffix,
        }
    assert results["definition/spans=True"]["matches_retained"], results
    assert results["assertion/spans=True"]["error"] == failure["reason"]
    assert results["assertion/spans=False"]["error"] == failure["reason"]
    assert len(diagnostic) == 2 and diagnostic[0] == diagnostic[1]
    observed = diagnostic[0]
    dense = model.record_decoder.forward_groups_dense
    masked = []

    def document_anchor_only(query_states, candidates, routing):
        # Diagnostic for this one natural schema, whose literal anchor is query 1.
        field_ids, _, _, modes, anchor_fields, _ = routing
        assert field_ids.shape[:2] == (1, 1) and int(modes[0, 0]) == 0
        query = int(field_ids[0, 0, anchor_fields[0, 0]])
        assert query == observed["anchor_query"] == 1
        starts, ends = candidates.indices[0, query].unbind(-1)
        offset = observed["offset"]
        in_document = (
            (starts >= offset)
            & (ends > starts)
            & (ends <= offset + observed["source_word_count"])
        )
        valid = candidates.valid_mask.clone()
        masked.extend(candidates.indices[0, query, valid[0, query] & ~in_document].tolist())
        valid[0, query] &= in_document
        return dense(query_states, replace(candidates, valid_mask=valid), routing)

    model.record_decoder.forward_groups_dense = document_anchor_only
    try:
        (filtered,) = model.batch_extract(
            [text],
            packs["assertion"].compile(),
            batch_size=1,
            threshold=cfg.threshold,
            overlap_policy="flat",
            **settings,
        )
    finally:
        model.record_decoder.forward_groups_dense = dense
    assert list(observed["anchor"]) in masked
    results["assertion/diagnostic_document_anchor_mask"] = {
        "masked_candidates": len(masked),
        "returned_assertion_records": len(filtered.get("assertion", [])),
    }
    print(
        json.dumps(
            {
                "task": 1866,
                "context": failure["context"],
                "text_sha256": sha256(text.encode()).hexdigest(),
                "text_bytes": len(text.encode()),
                "earlier_equal_source_slice": {"run": 378, "view": earlier_id},
                "profile": cfg.profile().fingerprint,
                "assertion_pack": packs["assertion"].fingerprint,
                "versions": {
                    name: importlib.metadata.version(name)
                    for name in (
                        "gliner2",
                        "torch",
                        "transformers",
                        "tokenizers",
                        "safetensors",
                    )
                },
                "decoder": observed,
                "controls": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
