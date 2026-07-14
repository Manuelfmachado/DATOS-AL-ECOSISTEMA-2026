"""Verifica overflow en cada slide activandolos uno por uno."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HTML_FILE = ROOT / "recursos" / "alba_slides.html"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(f"file:///{HTML_FILE.resolve().as_posix()}")
    page.wait_for_timeout(2000)

    total = page.evaluate("document.querySelectorAll('.slide').length")

    print("Overflow check por slide activo:")
    for i in range(total):
        page.evaluate(f"goTo({i})")
        page.wait_for_timeout(500)
        info = page.evaluate("""() => {
            const s = document.querySelector('.slide.active');
            if (!s) return null;
            return {
                scrollH: s.scrollHeight,
                clientH: s.clientHeight,
                scrollW: s.scrollWidth,
                clientW: s.clientWidth,
                hasOverflowV: s.scrollHeight > s.clientHeight,
                hasOverflowH: s.scrollWidth > s.clientWidth
            };
        }""")
        status = "OK"
        if info["hasOverflowV"]:
            status = f"OVERFLOW V ({info['scrollH']} > {info['clientH']})"
        if info["hasOverflowH"]:
            status += f" OVERFLOW H ({info['scrollW']} > {info['clientW']})"
        print(f"  Slide {i+1}: {status}")

    browser.close()