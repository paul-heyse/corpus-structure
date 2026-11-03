"""Spawned native diagnostics preserve the CLI stdout and the typed pipe separately.

This CPU process control uses the actual TableFormer logger and native child loop, not a
recognizer or provider. Only conversion work is replaced with a bounded fixture result.
"""

import json
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


def test_spawned_native_diagnostics_leave_parent_json_and_pipe_replies_intact(tmp_path: Path):
    runner = tmp_path / "native_stdio_control.py"
    runner.write_text(
        dedent(
            r"""
            import json
            import logging
            import multiprocessing
            import os

            from corpus_structure.ingest.pdf import PdfConversion, PdfRecipe
            from corpus_structure.ingest.pdf_hierarchy import NativeSnapshot
            from corpus_structure.ingest.pdf_worker import ConvertRequest, NativeReply


            def child(connection, recipe):
                # Bind the real logger to stdout BEFORE the native entry point starts.
                # Redirecting only a newly created Python stream would miss this handler.
                from docling_ibm_models.tableformer.settings import get_custom_logger
                from corpus_structure.ingest import pdf_worker

                logger = get_custom_logger("UM-TableFormer-control", logging.WARNING)

                class Converter:
                    def __init__(self, recipe, *, assets):
                        self.recipe = recipe

                    def convert_bytes(self, original, *, name, page_range):
                        logger.warning("tableformer-native-warning")
                        os.write(1, b"native-fd-diagnostic\n")
                        if original == b"reject":
                            raise RuntimeError("native-error-preserved")
                        return PdfConversion(
                            "a" * 64,
                            self.recipe.to_bytes(),
                            NativeSnapshot(b"{}", "b" * 64, "stdio-control"),
                            "partial_success",
                            ("explicit process control",),
                            (),
                            (),
                            None,
                        )

                pdf_worker.PdfConverter = Converter
                pdf_worker._native_child(connection, recipe, None)


            if __name__ == "__main__":
                context = multiprocessing.get_context("spawn")
                parent, native = context.Pipe()
                recipe = PdfRecipe("a" * 40, "b" * 40, device="cpu")
                process = context.Process(target=child, args=(native, recipe))
                process.start()
                native.close()
                try:
                    parent.send(ConvertRequest(b"accept", "control.pdf", None))
                    assert parent.poll(15), "native success reply unavailable"
                    success = parent.recv()
                    assert isinstance(success, NativeReply)
                    assert isinstance(success.value, PdfConversion)
                    assert success.value.conversion_status == "partial_success"
                    assert success.value.errors == ("explicit process control",)
                    assert success.error is None
                    parent.send(ConvertRequest(b"reject", "control.pdf", None))
                    assert parent.poll(15), "native error reply unavailable"
                    failed = parent.recv()
                    assert isinstance(failed, NativeReply)
                    assert failed.value is None
                    assert "native-error-preserved" in failed.error
                    parent.send(None)
                    process.join(5)
                    assert not process.is_alive(), "native child did not settle"
                    assert process.exitcode == 0
                finally:
                    parent.close()
                    if process.is_alive():
                        process.terminate()
                        process.join(5)
                    if process.is_alive():
                        process.kill()
                        process.join(5)
                    process.close()
                print(json.dumps({"success": "partial_success", "error": "preserved"}))
            """
        )
    )
    result = subprocess.run(
        [sys.executable, str(runner)], capture_output=True, text=True, timeout=45, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {"success": "partial_success", "error": "preserved"}
    assert result.stderr.count("tableformer-native-warning") == 2
    assert result.stderr.count("native-fd-diagnostic") == 2
