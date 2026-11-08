"""Run a serial, resumable Chandra panel using the pinned Docling VLM pipeline."""

import argparse
import hashlib
import json
import time
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import torch
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import VlmConvertOptions, VlmPipelineOptions
from docling.datamodel.vlm_engine_options import TransformersVlmEngineOptions
from docling.document_converter import DocumentConverter, ImageFormatOption, PdfFormatOption
from docling.models.stages.vlm_convert.vlm_convert_model import VlmConvertModel
from docling.pipeline.vlm_pipeline import VlmPipeline


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class InputRecorder:
    """Evidence hook at the Docling engine boundary, before model-specific tokenization."""

    def __init__(self):
        self.submissions = []
        self.build_inputs = VlmConvertModel._build_engine_inputs

    def record(self, model, images, prompts):
        inputs = self.build_inputs(model, images, prompts)
        for item in inputs:
            self.submissions.append(
                {
                    "image_size": list(item.image.size),
                    "image_mode": item.image.mode,
                    "pixel_sha256": hashlib.sha256(item.image.tobytes()).hexdigest(),
                    "prompt_sha256": hashlib.sha256(item.prompt.encode()).hexdigest(),
                    "temperature": item.temperature,
                    "max_new_tokens": item.max_new_tokens,
                }
            )
        return inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--page", type=int, action="append", default=[])
    parser.add_argument("--image", type=Path, action="append", default=[])
    args = parser.parse_args()
    cases = json.loads(Path(__file__).with_name("cases.json").read_text())
    pdf_hash = hashlib.sha256(args.pdf.read_bytes()).hexdigest()
    assert pdf_hash == cases["source_sha256"]
    assert version("docling") == "2.148.0"
    assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    options = VlmPipelineOptions(
        artifacts_path=args.artifacts,
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CUDA),
        vlm_options=VlmConvertOptions.from_preset(
            "chandra_ocr2",
            engine_options=TransformersVlmEngineOptions(
                load_in_8bit=False, trust_remote_code=True, compile_model=False
            ),
        ),
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_cls=VlmPipeline, pipeline_options=options),
            InputFormat.IMAGE: ImageFormatOption(
                pipeline_cls=VlmPipeline, pipeline_options=options
            ),
        }
    )
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(
        args.out / "runtime.json",
        {
            "packages": {
                name: version(name)
                for name in ("docling", "docling-slim", "docling-core", "transformers", "torch")
            },
            "device": torch.cuda.get_device_name(),
            "options": options.model_dump(mode="json"),
        },
    )
    pages = args.page or ([] if args.image else list(map(int, cases["pages"])))
    for source, physical in [(args.pdf, p) for p in pages] + [(i, None) for i in args.image]:
        tag = f"p{physical:03d}" if physical else source.stem
        receipt_path = args.out / f"{tag}.json"
        if receipt_path.exists():
            continue
        print(f"Starting {tag}", flush=True)
        start = time.monotonic()
        bounds = (physical, physical) if physical else (1, 1)
        recorder = InputRecorder()
        with patch.object(
            VlmConvertModel, "_build_engine_inputs", autospec=True, side_effect=recorder.record
        ):
            result = converter.convert(source, page_range=bounds, raises_on_error=False)
        predictions = []
        for page in result.pages:
            prediction = page.predictions.vlm_response
            if prediction:
                (args.out / f"{tag}.html").write_text(prediction.text)
                predictions.append(
                    prediction.model_dump(mode="json", exclude={"text", "generated_tokens"})
                )
            image = page.image
            if image:
                image.save(args.out / f"{tag}.png")
        if result.document is not None:
            write_json(args.out / f"{tag}.native.json", result.document.export_to_dict())
            (args.out / f"{tag}.md").write_text(result.document.export_to_markdown())
        receipt = {
            "case": tag,
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "physical_page": physical,
            "docling_pages": [page.page_no for page in result.pages],
            "render_sizes": [
                list(page.image.size) if page.image else None for page in result.pages
            ],
            "status": result.status.value,
            "submitted": recorder.submissions,
            "predictions": predictions,
            "errors": [error.model_dump(mode="json") for error in result.errors],
            "seconds": round(time.monotonic() - start, 3),
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        }
        write_json(receipt_path, receipt)
        print(tag, receipt["status"], receipt["seconds"], flush=True)


if __name__ == "__main__":
    main()
