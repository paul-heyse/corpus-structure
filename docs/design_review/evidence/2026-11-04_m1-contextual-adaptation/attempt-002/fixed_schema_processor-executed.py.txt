"""Evidence-only native fixed-schema adapter for ADR-0061 frontend-v2 targets.

Import is stdlib-only. Native APIs execute only when a caller explicitly collates.
Source authority belongs to the independently validated reconstruction/origin receipts;
this adapter verifies exact character/token transport and native target structure.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from hashlib import sha256
import json


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def conditioning(batch):
    return dict(input_ids=batch.input_ids.tolist(), attention_mask=batch.attention_mask.tolist(),
        mapped_indices=batch.mapped_indices, text_tokens=batch.text_tokens,
        schema_tokens_list=batch.schema_tokens_list, task_types=batch.task_types,
        schema_counts=batch.schema_counts, original_lengths=batch.original_lengths,
        text_word_indices=batch.text_word_indices.tolist(), text_word_mask=batch.text_word_mask.tolist(),
        text_word_counts=batch.text_word_counts, query_marker_indices=batch.query_marker_indices.tolist(),
        query_marker_mask=batch.query_marker_mask.tolist(), query_group_index=batch.query_group_index.tolist(),
        start_mappings=batch.start_mappings, end_mappings=batch.end_mappings,
        original_texts=batch.original_texts)


def execution_conditioning(batch):
    """Include native formation/format specifications, independent of gold labels."""
    return dict(encoding=conditioning(batch),
        record_specs=[{key: asdict(value) for key, value in specs.items()} for specs in batch.record_specs],
        original_schemas=batch.original_schemas)


def require_fragment_order(value, text):
    """Validate an already source-ordered fragment sequence; never reorder targets."""
    if not isinstance(value, list) or not value:
        raise ValueError("present logical TextSequence requires nonempty exact fragments")
    previous_end = -1
    for fragment in value:
        if not isinstance(fragment, dict) or set(fragment) != {"start", "end", "text"}:
            raise ValueError("fragment requires exactly start/end/text")
        start, end, literal = fragment["start"], fragment["end"], fragment["text"]
        if (type(start) is not int or type(end) is not int or not isinstance(literal, str)
            or not 0 <= start < end <= len(text) or start < previous_end):
            raise ValueError("fragments must be exact, source-ordered, nonoverlapping model spans")
        if text[start:end] != literal:
            raise ValueError("fragment differs from unchanged source context")
        previous_end = end


class FixedSchemaProcessor:
    """Compose native fixed preparation/target building through processor= only."""

    FORMAT = "m1-fixed-schema-native-targets-experiment-2"
    PACK_VERSION = "native-combined-v2"
    LOGICAL_FRAGMENT_POLICY = "definition-defining-text-source-fragments-1"

    def __init__(self, native_processor, *, max_gold_per_query=64):
        if max_gold_per_query != 64:
            raise ValueError("v2 experiment retains checkpoint gold capacity64")
        self.native = native_processor
        self.max_gold_per_query = max_gold_per_query
        self.requested_is_training = False
        self.calls = []
        self.last_receipt = None

    def __getattr__(self, name):
        return getattr(self.native, name)

    def change_mode(self, is_training):
        self.requested_is_training = bool(is_training)
        self.native.change_mode(is_training=False)

    def collate_fn_train(self, batch, max_len=None, **kwargs):
        return self._collate(batch, max_len=max_len, build_targets=True,
            entrypoint="collate_fn_train", **kwargs)

    def collate_fn_inference(self, batch, max_len=None, *, build_targets=False, **kwargs):
        return self._collate(batch, max_len=max_len, build_targets=bool(build_targets),
            entrypoint="collate_fn_inference", **kwargs)

    def _collate(self, rows, *, max_len, build_targets, entrypoint, architecture="boundary",
                 max_gold_per_query=64, on_capacity_exceeded="raise", error_policy="raise",
                 ignore_missing_entities=False, dedupe_contained_entity_spans=False):
        if architecture != "boundary" or error_policy != "raise" or on_capacity_exceeded != "raise":
            raise ValueError("v2 experiment requires boundary architecture and strict native raises")
        if ignore_missing_entities or dedupe_contained_entity_spans:
            raise ValueError("v2 targets forbid dropped/missing/contained-span sanitation")
        if max_gold_per_query != self.max_gold_per_query:
            raise ValueError("v2 experiment retains exact checkpoint gold capacity")
        if max_len is not None and (type(max_len) is not int or max_len < 1):
            raise ValueError("effective native source-word cap must be positive")
        if not rows:
            raise ValueError("nonempty fixed-schema batch required")
        for _, payload in rows:
            if payload["format"] != self.FORMAT or payload["native_pack_version"] != self.PACK_VERSION:
                raise ValueError("payload/pack frontend version differs from explicit v2 contract")
            if (digest(payload["released_schema"]) != payload["released_schema_digest"]
                or digest(payload["target_records"]) != payload["target_records_digest"]):
                raise ValueError("fixed schema or independent targets changed")
        from gliner2.inference.schema import Schema
        from gliner2.processing.boundary_preprocessing import build_boundary_batch_metadata
        from gliner2.processing.targets import char_span_to_word_boundaries, word_boundaries_to_char_span

        prepared = self.native.collate_fn_inference(
            [(text, Schema.from_dict(payload["released_schema"])) for text, payload in rows],
            architecture="boundary", build_targets=False, max_len=None, error_policy="raise",
            max_gold_per_query=max_gold_per_query, on_capacity_exceeded="raise",
            ignore_missing_entities=False, dedupe_contained_entity_spans=False)
        source_word_counts = [len(mapping) for mapping in prepared.start_mappings]
        if max_len is not None and any(count > max_len for count in source_word_counts):
            raise ValueError("effective native max_len would truncate a fixed source sample")
        base = execution_conditioning(prepared)
        labels, checks = [], []
        for index, ((text, payload), specs) in enumerate(zip(rows, prepared.record_specs, strict=True)):
            assert len(specs) == 1 and prepared.task_types[index] == ["json_structures"]
            spec = specs[0]
            declaration = payload["released_schema"]["structures"][payload["family"]]
            fields = declaration["fields"]
            assert spec.task_name == payload["family"] and spec.mode == declaration["mode"]
            assert [field.name for field in spec.fields] == [field["name"] for field in fields]
            if spec.mode == "latent":
                assert payload["family"] == "assertion" and "anchor" not in declaration
                assert spec.anchor_query_id is None
            else:
                assert spec.mode == "natural" and declaration.get("anchor") is not None
                assert spec.anchor_query_id is not None
            prefix_length = len(prepared.text_tokens[index]) - len(prepared.start_mappings[index])
            prefix = prepared.text_tokens[index][:prefix_length]
            instances, expected = [], []
            for target in payload["target_records"]:
                assert list(target) == [field.name for field in spec.fields]
                instance, record_checks = [], []
                for field, declared in zip(spec.fields, fields, strict=True):
                    assert field.cardinality.value == declared["cardinality"]
                    assert field.exclusive == declared.get("exclusive", False)
                    value = target[field.name]
                    qualified_fragments = payload["family"] == "definition" and field.name == "defining_text"
                    if qualified_fragments:
                        assert declared["dtype"] == "list" and field.cardinality.value == "zero_or_more"
                    else:
                        assert field.cardinality.is_scalar and declared["dtype"] == "str"
                    inclusive, spans, value_groups = [], [], ()
                    if value is None:
                        assert field.allows_absent, field.name
                        if qualified_fragments:
                            assert target[field.name + "__state"]["value"] != "present"
                    elif isinstance(value, list):
                        assert qualified_fragments
                        assert target[field.name + "__state"]["value"] == "present"
                        require_fragment_order(value, text)
                        for fragment in value:
                            start, end = char_span_to_word_boundaries(fragment["start"], fragment["end"],
                                prepared.start_mappings[index], prepared.end_mappings[index])
                            assert word_boundaries_to_char_span(start, end, prepared.start_mappings[index],
                                prepared.end_mappings[index]) == (fragment["start"], fragment["end"])
                            inclusive.append((start + prefix_length, end + prefix_length - 1))
                            spans.append((start + prefix_length, end + prefix_length))
                        value_groups = tuple((span,) for span in spans)
                    elif "choices" in value:
                        assert not qualified_fragments and value["choices"] == declared["choices"]
                        assert value["value"] in value["choices"]
                        inclusive = [(i, i) for i, token in enumerate(prefix) if token.lower() == value["value"].lower()]
                        assert inclusive
                        spans = [(start, end + 1) for start, end in inclusive]
                        value_groups = (tuple(spans),)
                    else:
                        assert not qualified_fragments
                        require_fragment_order([value], text)
                        start, end = char_span_to_word_boundaries(value["start"], value["end"],
                            prepared.start_mappings[index], prepared.end_mappings[index])
                        assert word_boundaries_to_char_span(start, end, prepared.start_mappings[index],
                            prepared.end_mappings[index]) == (value["start"], value["end"])
                        inclusive = [(start + prefix_length, end + prefix_length - 1)]
                        spans = [(start + prefix_length, end + prefix_length)]
                        value_groups = (tuple(spans),)
                    if spec.mode == "natural" and field.query_id == spec.anchor_query_id:
                        assert len(value_groups) == 1 and value_groups[0], "natural instance needs genuine anchor"
                    instance.append(inclusive)
                    record_checks.append(dict(role=field.name, spans=spans, distinct_values=value_groups,
                        absent=value is None, cardinality=field.cardinality.value, exclusive=field.exclusive,
                        logical_fragment_policy=self.LOGICAL_FRAGMENT_POLICY if qualified_fragments else None))
                instances.append(instance)
                expected.append(record_checks)
            labels.append([[len(instances), instances]])
            checks.append(dict(sample_id=payload["sample_id"], family=payload["family"], source=payload["source"],
                expected_records=len(instances), expected=expected, prefix=prefix, prefix_length=prefix_length,
                field_order=[field.name for field in spec.fields], mode=spec.mode, anchor_query_id=spec.anchor_query_id))
        if build_targets:
            layouts, targets, specs = build_boundary_batch_metadata(
                schema_tokens_list=prepared.schema_tokens_list, task_types=prepared.task_types,
                structure_labels=labels, text_lengths=prepared.text_word_counts,
                record_metadata_list=[schema["record_metadata"] for schema in prepared.original_schemas],
                is_training=False, build_targets=True, max_gold_per_query=max_gold_per_query,
                on_capacity_exceeded="raise", ignore_missing_entities=False, dedupe_contained_entity_spans=False,
                original_texts=prepared.original_texts, original_schemas=prepared.original_schemas)
            assert layouts == prepared.query_layouts and specs == prepared.record_specs
            result = replace(prepared, query_layouts=layouts, targets=targets, record_specs=specs, structure_labels=labels)
            for index, (check, sample_specs) in enumerate(zip(checks, specs, strict=True)):
                records = targets.records[index] if targets.records is not None else []
                assert len(records) == check["expected_records"]
                assert int(targets.record_targets[2][index].sum()) == len(records)
                assert int(targets.record_targets[4][index].sum()) == len(sample_specs[0].fields)
                for record, expected_fields in zip(records, check["expected"], strict=True):
                    for field, wanted in zip(sample_specs[0].fields, expected_fields, strict=True):
                        actual = record.field_for_query(field.query_id).values
                        assert actual == wanted["distinct_values"], (field.name, actual, wanted["distinct_values"])
                if not records:
                    assert not bool(targets.mention_mask[index].any())
                check["native_records"] = [asdict(record) for record in records]
        else:
            result = prepared
        assert execution_conditioning(result) == base
        self.last_receipt = dict(payload_format=self.FORMAT, native_pack_version=self.PACK_VERSION,
            logical_fragment_policy=self.LOGICAL_FRAGMENT_POLICY, entrypoint=entrypoint,
            requested_is_training=self.requested_is_training, native_processor_is_training=self.native.is_training,
            requested_max_len=max_len, source_word_counts=source_word_counts,
            native_cap_inactive=max_len is None or all(count <= max_len for count in source_word_counts),
            actual_truncation=False, build_targets=build_targets, exact_conditioning=True,
            conditioning=base["encoding"], conditioning_digest=digest(base["encoding"]),
            full_conditioning_digest=digest(base), record_specs=base["record_specs"], original_schemas=base["original_schemas"],
            samples=checks, strict_capacity=max_gold_per_query, on_capacity_exceeded="raise",
            dedupe_contained_entity_spans=False,
            record_mask=result.targets.record_targets[2].tolist() if result.targets is not None else None,
            field_mask=result.targets.record_targets[4].tolist() if result.targets is not None else None,
            mention_mask_count=int(result.targets.mention_mask.sum()) if result.targets is not None else None)
        self.calls.append(dict(entrypoint=entrypoint, samples=[check["sample_id"] for check in checks],
            full_conditioning_digest=digest(base)))
        return result
