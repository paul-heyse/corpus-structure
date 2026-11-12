"""Pinned HanLP multitask worker over canonical sentence tokens."""

from __future__ import annotations

import importlib
import json
import os
import sys
from collections.abc import Callable
from copy import copy
from pathlib import Path
from typing import Any
from unittest.mock import patch

Payload = dict[str, Any]
_CHECKPOINT = "en_tok_lem_pos_ner_srl_udep_sdp_con_modernbert_large_prepend_false_20250107_181612"
_BACKBONE = "answerdotai/ModernBERT-large"
_TASKS = ("lem", "pos", "dep", "srl", "con")
_MAX_SENTENCES = 8
_MAX_WORDS = 128
_MAX_TOKEN_CHARS = 1024
_MAX_BATCH_CHARS = 32_768
_MAX_SUBWORDS = 512
_MAX_PADDED_SUBWORDS = 2048


def _offline_only(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("HanLP profile has an unstaged native resource")


def _load_archive(directory: Path, backbone: str, device: Any) -> tuple[Any, list[str]]:
    hanlp = importlib.import_module("hanlp")
    multitask = importlib.import_module("hanlp.components.mtl.multi_task_learning")
    component = importlib.import_module("hanlp.utils.component_util")
    io_util = importlib.import_module("hanlp.utils.io_util")
    load_state = multitask.MultiTaskModel.load_state_dict
    omitted_buffers: list[str] = []
    loaded = False

    def checked_state(model: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal loaded
        result = load_state(model, *args, **kwargs)
        missing_parameters = set(result.missing_keys).intersection(
            name for name, _ in model.named_parameters()
        )
        if missing_parameters or result.unexpected_keys:
            raise RuntimeError(
                "HanLP checkpoint and loaded MTL model differ "
                f"(missing parameters={sorted(missing_parameters)[:8]}, "
                f"unexpected keys={result.unexpected_keys[:8]})"
            )
        omitted_buffers.extend(result.missing_keys)
        loaded = True
        return result

    encoder_config = json.loads((directory / "config.json").read_bytes())["encoder"]
    if encoder_config["transformer"] != backbone or not encoder_config["trainable"]:
        raise RuntimeError("HanLP checkpoint encoder differs from the staged MTL profile")
    # Keep the logical ModernBERT name. HanLP selects its pretokenization
    # convention by that name. The caller verified its immutable offline cache.
    with (
        patch.object(multitask.MultiTaskModel, "load_state_dict", checked_state),
        patch.object(component, "get_latest_info_from_pypi", return_value=None),
        patch.object(io_util, "download", _offline_only),
    ):
        model = hanlp.load(str(directory), devices=device, verbose=False)
    if not loaded:
        raise RuntimeError("HanLP did not load the archived MTL state")
    return model, omitted_buffers


def _prepare(
    model: Any, resolved: list[list[str]], sentences: list[list[str]]
) -> tuple[list[Payload], int]:
    tasks = [model.tasks[name] for group in resolved for name in group]
    first = tasks[0]
    bos = any(task.cls_is_bos for task in tasks)
    eos = any(task.sep_is_eos for task in tasks)
    encoder, transform = model.build_transform(first)
    limit = min(_MAX_SUBWORDS, encoder.max_seq_length)
    # Use the actual task's sample and dataset pipeline with the encoder cap
    # disabled for inspection. Admitted samples already fit the native window.
    uncapped = copy(encoder)
    uncapped.cls_is_bos, uncapped.sep_is_eos = bos, eos
    uncapped.max_seq_length = sys.maxsize
    transform[transform.index(encoder)] = uncapped
    samples = first.build_samples([list(row) for row in sentences], cls_is_bos=bos, sep_is_eos=eos)
    dataset = first.build_dataloader(samples, transform=transform, device=None).dataset
    preparation = []
    for index, sentence in enumerate(sentences):
        sample = dataset[index]
        input_ids = sample["token_input_ids"]
        bounds = slice(int(bos), -1 if eos else None)
        prepared_words = sample["token"][bounds]
        word_subwords = sample["token_token_span"][bounds]
        indices = [position for span in word_subwords for position in span]
        if (
            len(prepared_words) != len(sentence)
            or len(word_subwords) != len(sentence)
            or indices != list(range(1, len(input_ids) - 1))
        ):
            raise RuntimeError(
                "HanLP native word and subword coverage differs from canonical input"
            )
        preparation.append(
            {
                "input_ids": input_ids,
                "prepared_words": prepared_words,
                "word_subwords": word_subwords,
            }
        )
    return preparation, limit


def load_hanlp(assets: Path, device: str) -> tuple[Payload, Callable[[Payload], Payload]]:
    """Load the staged checkpoint and return bounded, ordered native observations."""
    return _load_hanlp(assets, device, assets / "hanlp" / _CHECKPOINT, _BACKBONE)


def _load_hanlp(
    assets: Path, device: str, directory: Path, backbone: str
) -> tuple[Payload, Callable[[Payload], Payload]]:
    os.environ.update(
        HF_HUB_CACHE=str(assets / "hub"), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1"
    )
    torch = importlib.import_module("torch")
    model, omitted_buffers = _load_archive(directory, backbone, torch.device(device))
    resolved = model.resolve_tasks(list(_TASKS), "tok")
    heads = [name for group in resolved for name in group]
    if not all(any(head.split("/")[0] == task for head in heads) for task in _TASKS):
        raise RuntimeError("HanLP loaded heads differ from the required MTL profile")
    if any(head.startswith("tok") for head in heads):
        raise RuntimeError("HanLP retokenization is excluded from this profile")
    parameter = next(model.model_.parameters())
    if parameter.device.type != device or parameter.dtype != torch.float32:
        raise RuntimeError("HanLP loaded device or dtype differs from the profile")
    eos_token = importlib.import_module("hanlp_common.constant").EOS
    native_transform = model.config.transform
    # Freeze executed defaults before installing the local sentinel repair callable.
    native_configuration = json.dumps(
        model._savable_config,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

    def restore_native_eos(sample: Payload) -> Payload:
        original_tokens = sample["token"]
        transformed = native_transform(sample)
        # PrependSpace rewrites the sentinel in pretokenized MTL. The encoder
        # drops it, but the native constituency decoder needs its exact value.
        if original_tokens[-1] == eos_token:
            transformed["token"][-1] = eos_token
        return transformed

    model.config.transform = restore_native_eos

    def infer(request: Payload) -> Payload:
        sentences = request.get("sentences")
        if not isinstance(sentences, list) or not sentences:
            raise ValueError("HanLP requires a nonempty ordered sentence batch")
        if len(sentences) > _MAX_SENTENCES:
            return {"outcome": "limited", "reason": "sentences", "limit": _MAX_SENTENCES}
        if request.get("prepare_bulk") is True:
            members: list[Payload | None] = [None for _ in sentences]
            admitted = []
            for ordinal, sentence in enumerate(sentences):
                reason = None
                if (
                    not isinstance(sentence, list)
                    or not sentence
                    or any(not isinstance(word, str) or not word.strip() for word in sentence)
                ):
                    raise ValueError("HanLP bulk preparation requires canonical token lists")
                if len(sentence) > _MAX_WORDS:
                    reason = ("sentence_words", _MAX_WORDS)
                elif max(map(len, sentence)) > _MAX_TOKEN_CHARS:
                    reason = ("token_chars", _MAX_TOKEN_CHARS)
                elif sum(map(len, sentence)) > _MAX_BATCH_CHARS:
                    reason = ("sentence_chars", _MAX_BATCH_CHARS)
                if reason is not None:
                    members[ordinal] = dict(
                        ordinal=ordinal, outcome="limited", reason=reason[0], limit=reason[1]
                    )
                else:
                    admitted.append(ordinal)
            if admitted:
                prepared, limit = _prepare(
                    model, resolved, [sentences[index] for index in admitted]
                )
                for ordinal, sample in zip(admitted, prepared, strict=True):
                    length = len(sample["input_ids"])
                    members[ordinal] = dict(
                        ordinal=ordinal,
                        outcome="prepared" if length <= limit else "limited",
                        row_tokens=length,
                        limit=limit,
                        reason=None if length <= limit else "sentence_subwords",
                    )
            return dict(
                outcome="prepared_batch", members=members, max_padded_subwords=_MAX_PADDED_SUBWORDS
            )
        if any(not isinstance(row, list) or not row for row in sentences):
            raise ValueError("HanLP requires nonempty canonical token lists")
        if max(map(len, sentences)) > _MAX_WORDS:
            return {"outcome": "limited", "reason": "sentence_words", "limit": _MAX_WORDS}
        if any(not isinstance(word, str) or not word.strip() for row in sentences for word in row):
            raise ValueError("HanLP requires nonblank canonical token strings")
        if max(len(word) for row in sentences for word in row) > _MAX_TOKEN_CHARS:
            return {"outcome": "limited", "reason": "token_chars", "limit": _MAX_TOKEN_CHARS}
        if sum(len(word) for row in sentences for word in row) > _MAX_BATCH_CHARS:
            return {"outcome": "limited", "reason": "batch_chars", "limit": _MAX_BATCH_CHARS}
        preparation, limit = _prepare(model, resolved, sentences)
        lengths = [len(row["input_ids"]) for row in preparation]
        if max(lengths) > limit:
            return {
                "outcome": "limited",
                "reason": "sentence_subwords",
                "limit": limit,
                "row_tokens": lengths,
            }
        if request.get("prepare_only") is True:
            # Exposes actual native subword population without inference. The caller
            # can make smaller outer batches without silently cutting a sentence.
            return {
                "outcome": "prepared",
                "preparation": preparation,
                "row_tokens": lengths,
                "limit": limit,
                "max_padded_subwords": _MAX_PADDED_SUBWORDS,
            }
        if len(lengths) * max(lengths) > _MAX_PADDED_SUBWORDS:
            return {
                "outcome": "limited",
                "reason": "padded_subwords",
                "limit": _MAX_PADDED_SUBWORDS,
                "row_tokens": lengths,
            }
        # HanLP disables gradients around inference and enables them locally
        # for the native constituency CRF's marginal calculation.
        result = model(sentences, tasks=list(_TASKS), skip_tasks="tok", resolved_tasks=resolved)
        if result.get("tok") != sentences:
            raise RuntimeError("HanLP native token output differs from canonical input")
        if any(len(result[head]) != len(sentences) for head in heads):
            raise RuntimeError("HanLP native head output differs from sentence population")
        return {"outcome": "succeeded", "preparation": preparation, "native": result.to_dict()}

    config = model.model_.encoder.transformer.config
    return {
        "native_configuration": native_configuration,
        "srl_max_arg_width": int(
            model.tasks[
                next(name for name in heads if name.split("/")[0] == "srl")
            ].config.max_arg_width
        ),
        "dtype": str(parameter.dtype),
        "device": str(parameter.device),
        "attention_implementation": config._attn_implementation,
        "heads": heads,
        "skip_tasks": ["tok"],
        "constituency_eos": "restore-native-sentinel-after-prepend-space",
        "omitted_checkpoint_buffers": omitted_buffers,
        "max_sentences": _MAX_SENTENCES,
        "max_words": _MAX_WORDS,
        "max_token_chars": _MAX_TOKEN_CHARS,
        "max_batch_chars": _MAX_BATCH_CHARS,
        "max_subwords": min(_MAX_SUBWORDS, model.config.encoder.transform().max_seq_length),
        "max_padded_subwords": _MAX_PADDED_SUBWORDS,
    }, infer
