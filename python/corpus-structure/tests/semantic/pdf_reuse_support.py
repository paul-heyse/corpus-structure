"""Standard capture and a finite HTTP recognition service for native reuse tests."""

import json
from contextlib import contextmanager
from dataclasses import dataclass, replace
from functools import cache
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from corpus_structure.ingest.pdf_recognition import NemotronRecipe
from semantic.actual_pdf_resume_support import prepared_pdf_resume_assets

ROOT = Path(__file__).resolve().parents[4]
SERVICE = ROOT / "services" / "nemotron-parse"
MODEL = "finite-pdf-reuse-fixture"
FULLPAGE = "<x_0.09><y_0.15>Controlled recognition differs.<x_0.86><y_0.24><class_Text>"
DETECTION = "<x_0.09><y_0.15><x_0.86><y_0.24><class_Text>"
WEIGHTS = sha256(json.dumps([FULLPAGE, DETECTION]).encode()).hexdigest()
TOKENIZER = sha256(b"finite literal response, no tokenizer or external model").hexdigest()
GENERATION = "finite-pdf-reuse-fixture-v1-" + WEIGHTS


@cache
def standard_capture_profile():
    from corpus_structure.ingest.pdf_producer_contract import standard_pdf_contract

    recipe, assets = prepared_pdf_resume_assets()
    recipe = replace(recipe, device="cpu", parser_threads=2, stage_batch_size=1)
    return recipe, assets, standard_pdf_contract()


def recognition_recipe():
    return NemotronRecipe(
        WEIGHTS, TOKENIZER, identity_assurance="trusted_managed_service", model=MODEL
    )


def recognition_interpreter():
    candidates = (
        SERVICE / ".venv" / "bin" / "python",
        Path.home() / ".cache/corpus-structure/nemotron-runtime-py312/bin/python",
    )
    return next(path for path in candidates if path.is_file())


def printed_original():
    """A single 400-point page with one known text line near the top."""
    stream = b"BT /F1 20 Tf 40 320 Td (Printed original evidence.) Tj ET\n"
    objects = (
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 400] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream",
    )
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(b"%d 0 obj\n" % number + body + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(b"%010d 00000 n \n" % offset)
    pdf.extend(b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % xref)
    return bytes(pdf)


@dataclass(frozen=True)
class FiniteRecognitionService:
    endpoint: str
    requests: list[str]


@contextmanager
def finite_recognition_service():
    """The real worker talks to a controlled service, with no model inference."""
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def reply(self, value):
            content = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(content)))
            self.send_header("x-corpus-generation", GENERATION)
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if self.path != "/corpus/generation":
                self.send_error(404)
                return
            self.reply(
                {
                    "protocol": "corpus-managed-recognition-1",
                    "assurance": "trusted_managed_service",
                    "generation": GENERATION,
                    "artifacts": {"model.safetensors": WEIGHTS, "tokenizer.json": TOKENIZER},
                }
            )

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                self.send_error(404)
                return
            if self.headers.get("x-corpus-generation") != GENERATION:
                self.send_error(409)
                return
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            parts = body["messages"][0]["content"]
            if body["model"] != MODEL or not parts[1]["image_url"]["url"].startswith(
                "data:image/png;base64,"
            ):
                self.send_error(400)
                return
            detect = "<output_no_text>" in parts[0]["text"]
            requests.append("detection" if detect else "reading")
            self.reply(
                {
                    "model": MODEL,
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": DETECTION if detect else FULLPAGE,
                            },
                            "finish_reason": "stop",
                        }
                    ],
                }
            )

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, name="finite-recognition-service", daemon=True)
        thread.start()
        try:
            yield FiniteRecognitionService(f"http://127.0.0.1:{server.server_port}/v1", requests)
        finally:
            server.shutdown()
            thread.join()
