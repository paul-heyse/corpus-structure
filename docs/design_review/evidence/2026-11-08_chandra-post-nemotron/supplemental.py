"""Author bounded, known-answer visual stimuli for Chandra's supplemental probes."""

from __future__ import annotations

import json
import math
import subprocess
from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ARABIC = "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"
DEVANAGARI = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
SCRIPT = "/usr/share/fonts/opentype/urw-base35/Z003-MediumItalic.otf"
INK = "#1b2532"


def page(title, height):
    image = Image.new("RGB", (1000, height), "white")
    draw = ImageDraw.Draw(image)
    label(draw, (500, 38), title, 39, BOLD)
    return image, draw


def label(draw, xy, value, size=26, font=SANS):
    draw.text(xy, value, font=ImageFont.truetype(font, size), fill=INK, anchor="mm")


def arrow(draw, start, end):
    draw.line((start, end), fill=INK, width=5)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    base = [
        (end[0] - 24 * math.cos(angle + delta), end[1] - 24 * math.sin(angle + delta))
        for delta in (-0.43, 0.43)
    ]
    draw.polygon((end, *base), fill=INK)


def diagram():
    image, draw = page("Figure 1. Sample handling workflow", 480)
    nodes = [
        ((65, 175, 240, 245), "Sample"),
        ((410, 175, 600, 245), "Inspect"),
        ((765, 95, 940, 165), "Archive"),
        ((765, 315, 940, 385), "Repeat"),
    ]
    for (left, top, right, bottom), name in nodes:
        draw.rounded_rectangle((left, top, right, bottom), 13, fill="#eaf4fb", outline=INK, width=3)
        label(draw, ((left + right) / 2, (top + bottom) / 2), name)
    arrow(draw, (240, 210), (410, 210))
    arrow(draw, (600, 190), (765, 130))
    arrow(draw, (600, 230), (765, 350))
    label(draw, (688, 133), "pass", 23)
    label(draw, (685, 312), "fail", 23)
    label(draw, (500, 450), "The inspection outcome determines the next step.", 22)
    return image, {
        "nodes": [name for _, name in nodes],
        "directed_edges": [
            ["Sample", "Inspect", None],
            ["Inspect", "Archive", "pass"],
            ["Inspect", "Repeat", "fail"],
        ],
        "caption": "The inspection outcome determines the next step.",
    }


def chart():
    image, draw = page("Figure 2. Buffer capacity by trial", 680)
    label(draw, (111, 93), "Capacity (mL)", 24)
    draw.line(((155, 115), (155, 540), (910, 540)), fill=INK, width=4)
    for value in range(0, 81, 20):
        y = 540 - 5 * value
        draw.line(((146, y), (155, y)), fill=INK, width=3)
        label(draw, (112, y), str(value))
    observations = [("North", 60, True), ("East", 40, False), ("West", 30, False)]
    for x, (name, value, printed) in zip((310, 535, 760), observations, strict=True):
        y = 540 - 5 * value
        draw.rectangle((x - 55, y, x + 55, 538), fill="#2879a8")
        label(draw, (x, 570), name)
        if printed:
            label(draw, (x, y - 22), str(value), 28, BOLD)
    label(draw, (545, 625), "Trial", 25)
    return image, {
        "x_axis": "Trial",
        "y_axis": "Capacity (mL)",
        "bars": [
            {"trial": name, "drawing_value_ml": value, "printed_above_bar": printed}
            for name, value, printed in observations
        ],
    }


def language():
    image, draw = page("Field note", 410)
    runs = [
        ("Température de l\u2019échantillon : 23 °C", SANS),
        ("तापमान २३ डिग्री है।", DEVANAGARI),
        ("درجة الحرارة ٢٣ مئوية", ARABIC),
        ("Return sample to shelf B.", SCRIPT),
    ]
    for index, (value, font) in enumerate(runs):
        label(draw, (500, 114 + 78 * index), value, 34, font)
    return image, {
        "lines_in_reading_order": [value for value, _ in runs],
        "fourth_line": "Script-font simulation of handwriting, typed and not human handwriting",
    }


def chemistry():
    image, draw = page("Figure 3. Structural formula", 450)
    # Bond-line representation of propan-2-ol. The two line ends are methyl carbons.
    center, left, right, top = (500, 245), (355, 330), (645, 330), (500, 156)
    draw.line((left, center, right), fill=INK, width=6, joint="curve")
    draw.line((center, top), fill=INK, width=6)
    label(draw, (500, 125), "OH", 37, BOLD)
    return image, {
        "molecule": "propan-2-ol",
        "equivalent_smiles_example": "CC(C)O",
        "visible_atom_label": "OH",
        "qualification": "Any equivalent valid SMILES suffices",
    }


def form(directory):
    from pypdf import PdfReader
    from reportlab.pdfgen.canvas import Canvas

    pdf = directory / "form.pdf"
    page = Canvas(str(pdf), pagesize=(600, 350), invariant=True)
    page.setFont("Helvetica-Bold", 24)
    page.drawString(50, 295, "Sample intake form")
    page.setFont("Helvetica", 16)
    page.drawString(50, 232, "Sample code")
    page.drawString(90, 170, "Sample arrived sealed")
    page.drawString(90, 112, "Retest requested")
    page.acroForm.textfield(name="sample_id", x=180, y=222, width=150, height=28, value="BX-71")
    page.acroForm.checkbox(name="sealed", x=50, y=163, size=24, checked=True)
    page.acroForm.checkbox(name="retest", x=50, y=105, size=24, checked=False)
    page.showPage()
    page.save()

    reader = PdfReader(pdf)
    fields = {key: str(field["/V"]) for key, field in reader.get_fields().items()}
    widget_states = {
        widget["/T"]: str(widget.get("/AS"))
        for ref in reader.pages[0]["/Annots"]
        if (widget := ref.get_object()).get("/Subtype") == "/Widget"
    }
    assert fields == {"sample_id": "BX-71", "sealed": "/Yes", "retest": "/Off"}
    assert widget_states == {"sample_id": "None", "sealed": "/Yes", "retest": "/Off"}
    subprocess.run(
        [
            "pdftoppm",
            "-r",
            "144",
            "-f",
            "1",
            "-l",
            "1",
            "-singlefile",
            "-png",
            str(pdf),
            str(directory / "form"),
        ],
        check=True,
    )
    return {
        "pdf_sha256": sha256(pdf.read_bytes()).hexdigest(),
        "image_sha256": sha256((directory / "form.png").read_bytes()).hexdigest(),
        "native_field_values": fields,
        "native_widget_appearance_states": widget_states,
        "visible_labels": {
            "sample_id": "Sample code",
            "sealed": "Sample arrived sealed",
            "retest": "Retest requested",
        },
    }


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("reference", type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    args.reference.parent.mkdir(parents=True, exist_ok=True)
    reference = {}
    for stimulus in (diagram, chart, language, chemistry):
        image, facts = stimulus()
        path = args.directory / f"{stimulus.__name__}.png"
        image.save(path)
        reference[path.name] = {"sha256": sha256(path.read_bytes()).hexdigest(), **facts}
    reference["form.pdf"] = form(args.directory)
    args.reference.write_text(json.dumps(reference, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
