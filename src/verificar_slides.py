"""Toma screenshots de cada slide para verificacion visual."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HTML_FILE = ROOT / "recursos" / "alba_slides.html"
OUT = ROOT / "recursos" / "slide_check"
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(f"file:///{HTML_FILE.resolve().as_posix()}")
    page.wait_for_timeout(2000)

    total = page.evaluate("document.querySelectorAll('.slide').length")
    print(f"Total slides: {total}")

    for i in range(total):
        page.evaluate(f"goTo({i})")
        page.wait_for_timeout(1000)
        path = OUT / f"slide_{i+1:02d}.png"
        page.screenshot(path=str(path))
        print(f"  Slide {i+1}")

    browser.close()

print("Screenshots guardados en recursos/slide_check/")