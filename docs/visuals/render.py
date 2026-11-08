# /// script
# requires-python = "==3.14.*"
# dependencies = ["playwright==1.64.1"]
# ///
"""Render the committed documentation assets with the pinned authoring tools."""

from pathlib import Path
from struct import unpack
from subprocess import check_output, run
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

SOURCE = Path(__file__).resolve().parent
ASSETS = SOURCE.parent / "assets"


def main() -> None:
    try:
        version = check_output(["d2", "--version"], text=True).strip()
    except FileNotFoundError as exc:
        raise SystemExit("Install D2 0.9.0 before running just docs-visuals.") from exc
    if version != "v0.9.0":
        raise SystemExit(f"Expected D2 v0.9.0, found {version}.")

    with TemporaryDirectory(dir=ASSETS) as staging:
        svg = Path(staging) / "pipeline.svg"
        png = Path(staging) / "social-preview.png"
        run(["d2", "--layout=elk", "--scale=1", "--pad=32", str(SOURCE / "pipeline.d2"), str(svg)], check=True)
        with sync_playwright() as playwright, playwright.chromium.launch() as browser:
            page = browser.new_page(viewport={"width": 1280, "height": 640}, device_scale_factor=1)
            page.goto((SOURCE / "social-preview.html").as_uri())
            page.evaluate("document.fonts.ready")
            page.locator("main").screenshot(path=png, animations="disabled", scale="css")
        image = png.read_bytes()
        if unpack(">II", image[16:24]) != (1280, 640) or len(image) >= 1_000_000:
            raise SystemExit("Social preview must be 1280 × 640 and under 1 MB.")
        for asset in (svg, png):
            asset.replace(ASSETS / asset.name)


if __name__ == "__main__":
    main()
