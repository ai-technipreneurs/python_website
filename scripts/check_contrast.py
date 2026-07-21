"""WCAG contrast audit of inline style="color: X; background: Y;" pairs on
the deployed notebook pages.

Handles:
- #rgb / #rrggbb hex, rgb()/rgba() colors, and named colors we care about
- Gradient backgrounds: the effective background is checked against BOTH
  gradient endpoints (the worst-case ratio is what matters for accessibility)
- rgba text on translucent overlays: alpha-composites the text color onto
  each candidate background before computing ratio
- Nested-element inheritance is NOT modeled (that would need a full DOM
  layout); we check only pairs that appear together in the same `style=`.

Prints WCAG AA fails (< 4.5:1 for normal text, < 3:1 for large text).
"""

from __future__ import annotations

import re
import sys
import urllib.request

# --- Color parsing ---------------------------------------------------------

NAMED = {
    "black": (0, 0, 0), "white": (255, 255, 255),
    "gray": (128, 128, 128), "grey": (128, 128, 128),
    "red": (255, 0, 0), "green": (0, 128, 0), "blue": (0, 0, 255),
    "yellow": (255, 255, 0), "transparent": (255, 255, 255),
}


def parse_color(s: str) -> tuple[int, int, int, float] | None:
    """Return (r,g,b,a) in [0,255],[0,255],[0,255],[0,1] or None."""
    s = s.strip().lower()
    if not s or s == "transparent":
        return None
    if s in NAMED:
        r, g, b = NAMED[s]
        return (r, g, b, 1.0)
    m = re.fullmatch(r"#([0-9a-f]{3})", s)
    if m:
        r, g, b = (int(c * 2, 16) for c in m.group(1))
        return (r, g, b, 1.0)
    m = re.fullmatch(r"#([0-9a-f]{6})", s)
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    m = re.fullmatch(r"rgba?\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)", s)
    if m:
        r, g, b = (int(float(x)) for x in m.group(1, 2, 3))
        a = float(m.group(4)) if m.group(4) else 1.0
        return (r, g, b, a)
    return None


def composite(fg: tuple[int, int, int, float], bg: tuple[int, int, int, float]) -> tuple[int, int, int]:
    """Alpha-composite fg over bg (bg treated as fully opaque; nested transparency ignored)."""
    fr, fg_, fb, fa = fg
    br, bg_c, bb, _ = bg
    return (
        round(fr * fa + br * (1 - fa)),
        round(fg_ * fa + bg_c * (1 - fa)),
        round(fb * fa + bb * (1 - fa)),
    )


def rel_lum(rgb: tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        cs = c / 255.0
        return cs / 12.92 if cs <= 0.03928 else ((cs + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = rel_lum(a), rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def bg_candidates(bg_decl: str) -> list[tuple[int, int, int, float]]:
    """Return one or two candidate opaque colors representing this background
    declaration. For gradients, both endpoints are returned."""
    hex_hits = re.findall(r"#[0-9a-fA-F]{3,6}", bg_decl)
    rgba_hits = re.findall(r"rgba?\([^\)]*\)", bg_decl)
    out: list[tuple[int, int, int, float]] = []
    for t in list(dict.fromkeys(hex_hits + rgba_hits)):
        c = parse_color(t)
        if c and c[3] >= 0.5:
            out.append(c)
    return out or [(255, 255, 255, 1.0)]  # default page bg = white


# --- Auditor ---------------------------------------------------------------

TARGETS = [
    "https://ai-technipreneurs.github.io/python_website/notebooks/00-shell.html",
    "https://ai-technipreneurs.github.io/python_website/intro.html",
]

STYLE_RE = re.compile(r'style="([^"]*)"', re.IGNORECASE)


def audit(url: str) -> None:
    print(f"\n=== {url} ===")
    html = urllib.request.urlopen(url, timeout=15).read().decode("utf-8", errors="replace")
    fails: list[tuple[float, str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for m in STYLE_RE.finditer(html):
        style = m.group(1)
        color_m = re.search(r"(?<!background-)color\s*:\s*([^;]+)", style, re.IGNORECASE)
        bg_m = re.search(r"background(?:-color)?\s*:\s*([^;]+)", style, re.IGNORECASE)
        if not color_m or not bg_m:
            continue
        color_v = color_m.group(1).strip()
        bg_v = bg_m.group(1).strip()
        key = (color_v, bg_v)
        if key in seen:
            continue
        seen.add(key)
        fg = parse_color(color_v)
        if not fg:
            continue
        for bg in bg_candidates(bg_v):
            composited = composite(fg, bg)
            ratio = contrast(composited, bg[:3])
            if ratio < 4.5:
                fails.append((ratio, color_v, bg_v[:60], f"AA fail (need 4.5:1, got {ratio:.2f}:1)"))
    if not fails:
        print("  All checked color/background pairs meet WCAG AA (4.5:1).")
        return
    fails.sort()
    for r, c, b, msg in fails:
        print(f"  {msg}")
        print(f"    color:      {c}")
        print(f"    background: {b}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for url in TARGETS:
        audit(url)
