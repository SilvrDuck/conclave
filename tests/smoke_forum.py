"""Smoke test: bring up the Forum in headless chromium, drive the
proclamation flow, and screenshot each perspective.

Usage:
    uv run python tests/smoke_forum.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

FORUM_URL = "http://localhost:5173"
OUT_DIR = Path(__file__).parent / "screenshots"


async def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # `networkidle` never fires because SSE keeps a connection open.
        await page.goto(FORUM_URL, wait_until="load", timeout=20_000)
        await page.wait_for_selector("text=/conclave \\/ forum/")
        # Give SWR a moment to fetch the initial state.
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUT_DIR / "01-glance.png"), full_page=True)

        # Issue a proclamation (the platform should already have one or two from earlier).
        text = "Users can listen to music, see lyrics scroll, and start a shared jam."
        await page.fill('input[placeholder*="Proclaim"]', text)
        await page.get_by_role("button", name="Proclaim").click()
        await page.wait_for_timeout(2000)

        # Witness perspective — wait for at least one proclamation card.
        await page.get_by_role("tab", name="Witness").click()
        await page.wait_for_selector('text=/№\\s*\\d+/', timeout=10_000)
        await page.screenshot(path=str(OUT_DIR / "02-witness.png"), full_page=True)

        # Try perspective
        await page.get_by_role("tab", name="Try").click()
        await page.wait_for_selector("text=Try what they built")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUT_DIR / "03-try.png"), full_page=True)

        # Direct perspective
        await page.get_by_role("tab", name="Direct").click()
        await page.wait_for_selector("text=Inbox")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUT_DIR / "04-direct.png"), full_page=True)

        await browser.close()
    print(f"screenshots in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
