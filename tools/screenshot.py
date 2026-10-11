"""Capture the README images from a running, connected GUI: the first screen and the cell panels."""

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PANEL_ONLY = ".readout { visibility: hidden; }"


def main() -> int:
    url = os.environ["GUI_URL"]
    directory = Path(os.environ["SCREENSHOT_DIR"])
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.goto(url)
        page.wait_for_selector("#battery .tile", timeout=60000)
        page.wait_for_selector("#chart rect", timeout=60000)
        page.screenshot(path=str(directory / "overview.png"))
        page.locator("#cells-panel").screenshot(path=str(directory / "cell-voltages.png"), style=PANEL_ONLY)
        page.wait_for_selector("#health-chart rect", timeout=60000)
        page.locator("#health-heading").locator("..").screenshot(
            path=str(directory / "group-health.png"), style=PANEL_ONLY
        )
        browser.close()
    print(f"saved overview.png, cell-voltages.png and group-health.png to {directory}")
    for error in errors:
        print(f"page error: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
