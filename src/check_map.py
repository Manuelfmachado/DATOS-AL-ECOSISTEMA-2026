"""Verifica que el mapa SVG se renderiza correctamente."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HTML_FILE = ROOT / "recursos" / "alba_slides.html"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(f"file:///{HTML_FILE.resolve().as_posix()}")
    page.wait_for_timeout(2000)

    # Ir al slide 6 (mapa)
    page.evaluate("goTo(5)")
    page.wait_for_timeout(1500)

    # Verificar SVG
    svg_info = page.evaluate("""() => {
        const svg = document.getElementById('colombiaMap');
        if (!svg) return {error: 'No SVG found'};
        const rect = svg.getBoundingClientRect();
        const polys = svg.querySelectorAll('polygon');
        return {
            viewBox: svg.getAttribute('viewBox'),
            width: rect.width,
            height: rect.height,
            polygonCount: polys.length,
            innerHTML_length: svg.innerHTML.length,
            containerRect: document.getElementById('mapContainer').getBoundingClientRect()
        };
    }""")
    print("SVG info:", svg_info)

    # Verificar todos los slides para overflow
    overflow_info = page.evaluate("""() => {
        const slides = document.querySelectorAll('.slide');
        const results = [];
        slides.forEach((s, i) => {
            results.push({
                slide: i + 1,
                scrollHeight: s.scrollHeight,
                clientHeight: s.clientHeight,
                hasOverflow: s.scrollHeight > s.clientHeight
            });
        });
        return results;
    }""")
    print("\nOverflow check:")
    for r in overflow_info:
        status = "OVERFLOW!" if r["hasOverflow"] else "OK"
        print(f"  Slide {r['slide']}: scroll={r['scrollHeight']} client={r['clientHeight']} {status}")

    # Verificar nav overlap
    nav_info = page.evaluate("""() => {
        const nav = document.querySelector('.nav-controls');
        const rect = nav.getBoundingClientRect();
        return {bottom: rect.bottom, top: rect.top, right: rect.right, left: rect.left};
    }""")
    print(f"\nNav position: top={nav_info['top']:.0f} bottom={nav_info['bottom']:.0f} left={nav_info['left']:.0f} right={nav_info['right']:.0f}")

    browser.close()