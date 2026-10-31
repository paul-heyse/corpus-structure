"""Author the small active PDF source; historical HTML inputs/batches remain archived controls."""

from __future__ import annotations

import ctypes
import textwrap
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as raw

SECTIONS = (
    (
        "Ownership register",
        (
            (
                "Acme (ORG-101) owns P-17 in 2020 and 2022, files F1 and F2 for 2021, "
                "records shares 0.5 and 0.8, and is reported by Alpha and Beta."
            ),
            "This register is an informational notice.",
        ),
    ),
    ("Registry identities", ("Acme (ORG-202) and Acme (org-101) each own P-17.",)),
    (
        "Qualified ownership and inspection",
        (
            (
                "Custodian Acme (ORG-101) owns vessel P-17 from 2020-01-01 through "
                "2020-12-31. Register Alpha reports this holding."
            ),
            (
                "Inspector Boreal (ORG-202) inspected vessel P-17, held by custodian Acme "
                "(ORG-101), on 2020-07-01. The vessel was intact and its measured cargo "
                "quantity was exactly 12.3400 kg, on a dry-mass basis."
            ),
            (
                "Register Beta separately reports that custodian Acme (ORG-101) owns vessel "
                "P-17 from 2020-01-01 through 2020-12-31."
            ),
        ),
    ),
)


def write_pdf(destination: Path, sections=SECTIONS) -> None:
    document = pdfium.PdfDocument.new()
    try:
        for title, paragraphs in sections:
            page = document.new_page(612, 792)
            try:
                lines = [(title, 16, 740)]
                y = 700
                for paragraph in paragraphs:
                    for line in textwrap.wrap(paragraph, width=85):
                        lines.append((line, 10, y))
                        y -= 15
                    y -= 15
                for value, size, top in lines:
                    handle = raw.FPDFPageObj_NewTextObj(document, b"Helvetica", size)
                    if not handle:
                        raise RuntimeError("PDFium could not create a native text object")
                    encoded = (value + "\0").encode("utf-16-le")
                    wide_text = (ctypes.c_ushort * (len(encoded) // 2)).from_buffer_copy(encoded)
                    if not raw.FPDFText_SetText(handle, wide_text):
                        raise RuntimeError("PDFium could not set fixture text")
                    raw.FPDFPageObj_SetFillColor(handle, 0, 0, 0, 255)
                    raw.FPDFPageObj_Transform(handle, 1, 0, 0, 1, 36, top)
                    page.insert_obj(pdfium.PdfObject(handle, pdf=document))
                page.gen_content()
            finally:
                page.close()
        destination.parent.mkdir(parents=True, exist_ok=True)
        document.save(destination, version=17)
    finally:
        document.close()


if __name__ == "__main__":
    write_pdf(Path(__file__).parent / "corpus/toy.pdf")
