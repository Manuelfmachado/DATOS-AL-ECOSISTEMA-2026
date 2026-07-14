"""Verifica que la navegacion no solapa con el contenido."""
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

    print("Nav overlap check:")
    for i in range(total):
        page.evaluate(f"goTo({i})")
        page.wait_for_timeout(500)
        info = page.evaluate("""() => {
            const nav = document.querySelector('.nav-controls');
            const navRect = nav.getBoundingClientRect();
            const slide = document.querySelector('.slide.active');
            if (!slide) return null;
            const navBox = {left: navRect.left, top: navRect.top, right: navRect.right, bottom: navRect.bottom};
            const elements = slide.querySelectorAll('div, span, p, td, th');
            let overlaps = [];
            elements.forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.width < 5 || r.height < 5) return;
                const intersects = !(r.right < navBox.left || r.left > navBox.right || r.bottom < navBox.top || r.top > navBox.bottom);
                if (intersects && el !== nav) {
                    overlaps.push({
                        text: el.textContent.substring(0, 50).trim()
                    });
                }
            });
            return {navBox, overlaps: overlaps.slice(0, 3)};
        }""")
        if info and info["overlaps"]:
            print(f"  Slide {i+1}: {len(info['overlaps'])} elementos solapados con nav")
            for o in info["overlaps"]:
                print(f"    -> '{o['text'][:40]}'")
        else:
            print(f"  Slide {i+1}: OK")

    browser.close()