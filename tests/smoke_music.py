"""Quick visual smoke test of the music UI."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(__file__).parent / "screenshots"

async def main():
    OUT.mkdir(exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        page = await b.new_page(viewport={"width": 1100, "height": 800})
        await page.goto("http://localhost:9001", wait_until="load", timeout=15_000)
        await page.wait_for_selector("text=Imperial March (8-bit)", timeout=10_000)
        # Click the first Play button — generates inter-pod calls
        await page.locator("button[data-id='t1']").first.click()
        await page.wait_for_timeout(2500)
        await page.screenshot(path=str(OUT / "05-music-ui.png"), full_page=True)
        print("music ui screenshot saved")
        await b.close()

asyncio.run(main())
