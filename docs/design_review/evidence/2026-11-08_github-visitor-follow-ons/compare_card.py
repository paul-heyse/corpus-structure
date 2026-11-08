"""Compare the published citation against a card derived from its same text."""

import argparse
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import expect, sync_playwright

VIEWPORTS = ((1280, 800), (390, 844))
CARD_CSS = """
#citation-card {
  margin: 0.75rem 0;
  padding: 0.75rem 1rem;
  border: 1px solid currentColor;
  border-radius: 0.5rem;
}
#citation-card p { margin: 0.5em 0; overflow-wrap: anywhere; }
"""


def capture(base_url: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright, playwright.chromium.launch() as browser:
        print(f"Chromium {browser.version}")
        for width, height in VIEWPORTS:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(urljoin(base_url, "docs/examples/README.html"), wait_until="networkidle")
            heading = page.get_by_role("heading", name="A printed reference becomes a typed link")
            heading.evaluate("(heading) => { heading.scrollIntoView({block: 'start'}); window.scrollBy(0, -115); }")
            table = heading.locator("xpath=following-sibling::div[1]/table")
            expect(table).to_contain_text("27b19068cdac")
            evidence = heading.locator("xpath=following-sibling::p[1]")
            links = evidence.get_by_role("link").evaluate_all("(links) => links.map(link => link.href)")
            assert len(links) == 3
            page.screenshot(path=output / f"baseline-{width}.png", animations="disabled")

            page.add_style_tag(content=CARD_CSS)
            table.evaluate("""table => {
                const card = document.createElement('section');
                card.id = 'citation-card';
                card.setAttribute('aria-label', 'Retained citation');
                for (const row of table.tBodies[0].rows) {
                    const line = document.createElement('p');
                    const label = document.createElement('strong');
                    label.textContent = row.cells[0].textContent;
                    line.append(label, ' · ');
                    for (const node of row.cells[1].childNodes) {
                        line.append(node.cloneNode(true));
                    }
                    card.append(line);
                }
                table.parentElement.replaceWith(card);
            }""")
            expect(page.get_by_role("region", name="Retained citation")).to_contain_text("27b19068cdac")
            assert evidence.get_by_role("link").evaluate_all("(links) => links.map(link => link.href)") == links
            page.screenshot(path=output / f"card-{width}.png", animations="disabled")
            print(f"{width} × {height}: both treatments retained all three evidence links")
            page.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    capture(args.base_url, args.output)
