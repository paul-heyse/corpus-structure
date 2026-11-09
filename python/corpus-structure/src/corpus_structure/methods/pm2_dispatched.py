"""Maverick and Dipo native profiles loaded by their isolated worker processes."""

from __future__ import annotations

import os
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

Payload = dict[str, Any]
Inference = Callable[[Payload], Payload]

_MAVERICK_TOKENS = 512
_MAVERICK_MENTIONS = 128
_MAVERICK_ENCODER = "microsoft/deberta-v3-large"
_DIPO_TOKENS = 2048
_DIPO_EDUS = 128
_TEXT_BYTES = 64 * 1024


class _RequestLimit(Exception):
    def __init__(self, reason: str, actual: int, limit: int) -> None:
        self.result = {"outcome": "limited", "reason": reason, "actual": actual, "limit": limit}


def _bound(reason: str, actual: int, limit: int) -> None:
    if actual > limit:
        raise _RequestLimit(reason, actual, limit)


def _native_metadata(model: Any, encoder: Any) -> Payload:
    parameter = next(model.parameters())
    return {
        "head": type(model).__name__,
        "dtype": str(parameter.dtype),
        "device": str(parameter.device),
        "attention_implementation": encoder.config._attn_implementation,
    }


def load_maverick(assets: Path, device: str) -> tuple[Payload, Inference]:
    native = cast(Any, import_module("maverick.models.maverick_model"))
    mes = cast(Any, import_module("maverick.models.model_mes"))
    post_tokenizer = 0

    class BoundedMaverick(native.Maverick):
        def eos_mask(self, input_ids_len: int, eos_indices: list[int]) -> Any:
            nonlocal post_tokenizer
            post_tokenizer = input_ids_len
            _bound("post_tokenizer_tokens", input_ids_len, _MAVERICK_TOKENS)
            return super().eos_mask(input_ids_len, eos_indices)

    auto_model = mes.AutoModel

    def load_encoder(name: str) -> Any:
        if name != _MAVERICK_ENCODER:
            raise ValueError("unexpected Maverick encoder")
        return auto_model.from_pretrained(name, dtype="float32", local_files_only=True)

    # Transformers would allocate the downloaded backbone in FP16 before
    # Lightning copies the trained FP32 weights. Select FP32 before that copy.
    # The public wrapper exposes neither this setting nor weights_only for its
    # reviewed Lightning checkpoint containing OmegaConf objects.
    previous = os.environ.get("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD")
    os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
    mes.AutoModel = SimpleNamespace(from_pretrained=load_encoder)
    try:
        maverick = BoundedMaverick(str(assets / "maverick"), device=device)
    finally:
        mes.AutoModel = auto_model
        if previous is None:
            del os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"]
        else:
            os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = previous
    model = maverick.model.to(device)
    if (
        type(model).__name__ != "Maverick_mes"
        or model.encoder_hf_model_name != _MAVERICK_ENCODER
        or model.encoder.config.max_position_embeddings != _MAVERICK_TOKENS
        or {str(parameter.dtype) for parameter in model.parameters()} != {"torch.float32"}
    ):
        raise ValueError("unexpected Maverick MES head or encoder")
    native_extract = model.eos_mention_extraction

    def bounded_extraction(*args: Any, **kwargs: Any) -> Any:
        result = native_extract(*args, **kwargs)
        _bound("detected_mentions", sum(len(row) for row in result[1]), _MAVERICK_MENTIONS)
        return result

    model.eos_mention_extraction = bounded_extraction

    def infer(request: Payload) -> Payload:
        sentences = request.get("sentences")
        if not isinstance(sentences, list) or any(
            not isinstance(sentence, list)
            or not sentence
            or any(not isinstance(token, str) or not token.strip() for token in sentence)
            for sentence in sentences
        ):
            raise ValueError("Maverick requires lists of nonempty canonical sentence tokens")
        if not sentences:
            return {
                "outcome": "empty",
                "tokens": [],
                "mentions": [],
                "mentions_subtokens": [],
                "unmapped_mentions": [],
                "clusters": [],
                "clusters_subtokens": [],
            }
        count = sum(len(sentence) for sentence in sentences)
        inventory: list[list[int]] = []
        mentions_subtokens: list[list[int]] = []
        unmapped: list[Payload] = []
        clusters_subtokens: list[list[list[int]]] = []

        def capture(_model: Any, _args: Any, kwargs: Payload, result: Payload) -> None:
            subtoken_to_word = kwargs["subtoken_map"][0]
            word_to_token = kwargs["new_token_map"][0]
            native = result["pred_dict"]
            for start, end in native["mention_idxs"][0].tolist():
                pair = [start, end]
                mentions_subtokens.append(pair)
                if not 0 <= start <= end < len(subtoken_to_word):
                    reason = "invalid_subtoken_extent"
                else:
                    left, right = subtoken_to_word[start], subtoken_to_word[end]
                    if left is None or right is None:
                        reason = "special_token_endpoint"
                    else:
                        token_start, token_end = word_to_token[left], word_to_token[right]
                        if token_start is None or token_end is None:
                            reason = "injected_speaker_endpoint"
                        elif not 0 <= token_start <= token_end < count:
                            reason = "invalid_canonical_token_extent"
                        else:
                            inventory.append([token_start, token_end])
                            continue
                unmapped.append({"subtokens": pair, "reason": reason})
            clusters_subtokens.extend(
                [[int(start), int(end)] for start, end in cluster] for cluster in native["clusters"]
            )

        try:
            _bound(
                "input_bytes",
                sum(len(token.encode()) for sentence in sentences for token in sentence),
                _TEXT_BYTES,
            )
            supplied = request.get("predefined_mentions")
            if supplied is not None:
                if not isinstance(supplied, list):
                    raise ValueError("predefined Maverick mentions require inclusive endpoints")
                _bound("predefined_mentions", len(supplied), _MAVERICK_MENTIONS)
                for span in supplied:
                    if (
                        not isinstance(span, list)
                        or len(span) != 2
                        or any(type(endpoint) is not int for endpoint in span)
                        or not 0 <= span[0] <= span[1] < count
                    ):
                        raise ValueError("Maverick predefined mention has invalid token endpoints")
            hook = model.register_forward_hook(capture, with_kwargs=True)
            try:
                result = maverick.predict(sentences, predefined_mentions=supplied)
            finally:
                hook.remove()
        except _RequestLimit as exc:
            return exc.result
        clusters = []
        for cluster in result["clusters_token_offsets"]:
            endpoints = [
                [int(start), int(end)]
                for start, end in cluster
                if start is not None and end is not None
            ]
            if any(not 0 <= start <= end < count for start, end in endpoints):
                raise ValueError("Maverick emitted an invalid cluster endpoint")
            if endpoints:
                clusters.append(endpoints)
        return {
            "outcome": "succeeded"
            if supplied or mentions_subtokens or clusters_subtokens
            else "empty",
            "post_tokenizer_tokens": post_tokenizer,
            "tokens": result["tokens"],
            "mentions": inventory,
            "mentions_subtokens": mentions_subtokens,
            "unmapped_mentions": unmapped,
            "clusters": clusters,
            "clusters_subtokens": clusters_subtokens,
        }

    return {
        **_native_metadata(model, model.encoder),
        "encoder": model.encoder_hf_model_name,
        "coordinate_unit": "inclusive_canonical_token",
        "native_coordinate_unit": "inclusive_subtoken",
        "bounds": {"post_tokenizer_tokens": _MAVERICK_TOKENS, "mentions": _MAVERICK_MENTIONS},
    }, infer


def load_dipo(assets: Path, device: str) -> tuple[Payload, Inference]:
    native = cast(Any, import_module("dipo.rst.parsers.dmrst.modeling_dmrst"))
    post_tokenizer = 0

    class BoundedDmrst(native.DMRSTParser):
        def _encode_tokens(self, input_ids: Any) -> Any:
            nonlocal post_tokenizer
            post_tokenizer = len(input_ids)
            _bound("post_tokenizer_tokens", post_tokenizer, _DIPO_TOKENS)
            return super()._encode_tokens(input_ids)

        def _build_edu_reprs(self, embeddings: Any, edu_mapping: Any) -> Any:
            # predict_both bypasses the raw post-merge recovery seam.
            _bound("edus", len(edu_mapping), _DIPO_EDUS)
            return super()._build_edu_reprs(embeddings, edu_mapping)

    parser = BoundedDmrst.from_pretrained(
        str(assets / "dipo"), device=device, compile_encoder=False, token=False
    )
    if (
        parser.config.model_name != "jhu-clsp/ettin-encoder-400m"
        or parser.stride != 100
        or parser.config.encoder_window_size is not None
        or parser.segmenter is None
        or parser.config.segmentation.scheme != "BIE"
        or parser.config.segmentation.loss != "crf"
        or str(next(parser.parameters()).dtype) != "torch.float32"
    ):
        raise ValueError("unexpected Dipo DMRST configuration")
    native_recover = native.edus_from_breaks
    native_breaks = parser.segmenter.predict_breaks
    native_tokenize = native.tokenize_document

    def splits(tree: Any) -> list[Payload]:
        return [
            {"left": left, "right": right, "nuclearity": nuclearity, "relation": relation}
            for (left, right), nuclearity, relation in tree.spans_with_ranges()
        ]

    def raw_parse(text: str, mode: str) -> Payload:
        edus = []
        learned: list[int] = []
        boundaries = []

        def predict_breaks(embeddings: Any) -> list[int]:
            result = native_breaks(embeddings)
            learned.extend(result)
            return result

        def recover(
            source: str, char_map: list[int], offsets: list[tuple[int, int]], breaks: list[int]
        ) -> Any:
            mapping, texts = native_recover(source, char_map, offsets, breaks)
            _bound("edus", len(mapping), _DIPO_EDUS)
            forced = set(
                native.with_forced_breaks(
                    source, char_map, offsets, [], native.line_start_breaks(source)
                )
                if mode == "layout_forced"
                else ()
            )
            learned_set = set(learned)
            if set(breaks) != learned_set | forced:
                raise ValueError("Dipo boundary provenance differs from native breaks")
            final = {end - 1 for _, end in mapping}
            boundaries.extend(
                {
                    "token_end": stop + 1,
                    "learned": stop in learned_set,
                    "forced": stop in forced,
                    "disposition": "retained" if stop in final else "merged",
                }
                for stop in breaks
            )
            starts = [char_map[offsets[begin][0]] for begin, _end in mapping]
            ends = [*starts[1:], len(source)]
            for (begin, stop), start, end, value in zip(mapping, starts, ends, texts, strict=True):
                if native.collapse_whitespace(source[start:end]) != value:
                    raise ValueError("Dipo EDU recovery and source coordinates differ")
                edus.append({"tokens": [begin, stop], "chars": [start, end], "text": value})
            return mapping, texts

        native.edus_from_breaks = recover
        parser.segmenter.predict_breaks = predict_breaks
        try:
            tree = parser.predict_from_text(text, break_at_paragraphs=mode == "layout_forced")
        finally:
            native.edus_from_breaks = native_recover
            parser.segmenter.predict_breaks = native_breaks
        if len(tree.edus) != len(edus):
            raise ValueError("Dipo recovered EDU count differs from its native tree")
        return {
            "outcome": "succeeded",
            "mode": mode,
            "post_tokenizer_tokens": post_tokenizer,
            "edus": edus,
            "spans": splits(tree),
            "boundaries": boundaries,
        }

    def paired_parse(text: str, ranges: Any) -> Payload:
        if not isinstance(ranges, list) or not ranges:
            raise ValueError("Dipo supplied EDUs require ordered source ranges")
        _bound("supplied_edus", len(ranges), _DIPO_EDUS)
        edus = []
        prefixes = []
        previous = 0
        for bounds in ranges:
            if (
                not isinstance(bounds, list)
                or len(bounds) != 2
                or any(type(bound) is not int for bound in bounds)
            ):
                raise ValueError("invalid Dipo supplied EDU range")
            start, end = bounds
            if (
                not previous <= start < end <= len(text)
                or text[previous:start].strip()
                or not text[start:end].strip()
            ):
                raise ValueError("Dipo supplied EDUs must cover ordered non-whitespace source")
            edus.append(text[start:end])
            prefixes.append(text[previous:start])
            previous = end
        if text[previous:].strip():
            raise ValueError("Dipo supplied EDUs omit trailing source text")
        origin = ranges[0][0]
        # predict_both reads the leaves and their prefixes. These scaffold splits
        # only construct a valid native input and are never returned as predictions.
        relation = next(name for name, kind in parser.config.relation_types if kind == "rst")
        tree = native.RstTree.from_parsing_actions(
            [(index, "NS", relation) for index in range(1, len(edus))],
            edus,
            relation_types=parser.config.relation_types,
        )
        for edu, prefix in zip(tree.edus, prefixes, strict=True):
            edu.prefix = prefix

        reconstruction = None

        def tokenize(*args: Any, **kwargs: Any) -> Any:
            nonlocal reconstruction
            result = native_tokenize(*args, **kwargs)
            _, _, rebuilt, offsets = result
            if rebuilt != text[origin:previous]:
                raise ValueError("Dipo paired reconstruction differs from its retained source")
            reconstruction = (rebuilt, offsets)
            return result

        native.tokenize_document = tokenize
        try:
            result = parser.predict_both(tree)
        finally:
            native.tokenize_document = native_tokenize
        if reconstruction is None or result["e2e_pred"] is None:
            raise ValueError("Dipo paired prediction omitted its reconstructed input or arm")
        rebuilt, offsets = reconstruction
        supplied = [
            {"tokens": pair, "chars": [start - origin, end - origin], "text": value}
            for pair, (start, end), value in zip(
                result["gold_edu_mapping"], ranges, edus, strict=True
            )
        ]
        predicted = [
            {
                "tokens": [begin, end],
                "chars": [offsets[begin][0], offsets[end - 1][1]],
                "text": value,
            }
            for (begin, end), value in zip(
                result["pred_edu_mapping"], result["e2e_pred"].edu_strings, strict=True
            )
        ]
        return {
            "outcome": "succeeded",
            "mode": "supplied_edus",
            "post_tokenizer_tokens": post_tokenizer,
            "reconstruction": {"text": rebuilt, "raw_start": origin, "raw_end": previous},
            "arms": {
                "supplied": {"edus": supplied, "spans": splits(result["gold_pred"])},
                "predicted": {"edus": predicted, "spans": splits(result["e2e_pred"])},
            },
        }

    def infer(request: Payload) -> Payload:
        text = request.get("text")
        mode = request.get("mode", "learned")
        if not isinstance(text, str):
            raise ValueError("Dipo requires a rendered text scope")
        if mode not in ("learned", "layout_forced", "supplied_edus"):
            raise ValueError("unsupported Dipo prediction mode")
        if mode != "supplied_edus" and "edu_ranges" in request:
            raise ValueError("reviewed EDU ranges require the Dipo supplied mode")
        try:
            _bound("input_bytes", len(text.encode()), _TEXT_BYTES)
            if mode == "supplied_edus":
                return paired_parse(text, request.get("edu_ranges"))
            if not text.strip():
                return {"outcome": "empty", "edus": [], "spans": [], "mode": mode}
            return raw_parse(text, mode)
        except _RequestLimit as exc:
            return {**exc.result, "mode": mode}

    return {
        **_native_metadata(parser, parser.encoder),
        "head": "DMRSTParser",
        "encoder": parser.config.model_name,
        "stride": parser.stride,
        "tokenizer_max_length": parser.tokenizer.model_max_length,
        "encoder_max_positions": parser.encoder.config.max_position_embeddings,
        "coordinate_unit": "half_open_token_char_and_edu",
        "bounds": {"post_tokenizer_tokens": _DIPO_TOKENS, "edus": _DIPO_EDUS},
    }, infer
