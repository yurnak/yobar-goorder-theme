#!/usr/bin/env python3
"""Generate the "GoOrder dark-mode base" block of yobar-dark.css.

GoOrder ships a built-in dark mode (rules prefixed with `.dark-mode`) that
covers the cart, checkout, order status, account drawer, vouchers etc.
The storefront never switches it on for this store, so we re-scope those
rules to `.body` (a class the <body> always has), recolor the navy palette
to the Yo Bar palette, and splice the result into yobar-dark.css between
the GENERATED markers. Areas the theme styles by hand are skipped.

Usage: python3 tools/gen_dark_base.py [path/to/main.css]
       (without an argument it downloads the live main.*.css)
"""
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "yobar-dark.css"
START = "/* ===== GENERATED: GoOrder dark-mode base (tools/gen_dark_base.py) ===== */"
END = "/* ===== END GENERATED ===== */"

# first class after `.dark-mode` -> skip, the theme styles these itself
SKIP = {
    "navbar", "navbar-nav-menus", "navbar-back", "menu-items", "menu-items-grid",
    "menu-category", "menu-category-header", "menu-tabs-container", "promotions",
    "btn-promotion", "sticky-outer-wrapper", "indiana-scroll-container",
    "navigate-left", "navigate-right", "homepage-menus", "hero-bg", "hero",
    "multistore-page", "multistore-with-map-home-page", "multistore-places",
    "multistore-list", "multistore-full", "multistore-map", "multistore-map-controls",
    "menu", "container-menu-picker", "menu-category-items-modal-dialog",
}

COLORS = {
    "#94a3b8": "#9a9d8f", "#ccd5e0": "#f1f2ea", "#334155": "#2a2d24",
    "#101729": "#151612", "#48c2ff": "#e3fc62", "#171e2f": "#1d1f19",
    "#1f293a": "#25281f", "#54d483": "#e3fc62", "#232a3a": "#25281f",
    "#2d3343": "#2f3228", "#0085e9": "#e3fc62", "#1ea2ff": "#e3fc62",
    "#526077": "#7c7f71", "#1e293a": "#25281f", "#3341558c": "#2a2d248c",
    "#33415500": "#2a2d2400", "#2cb7ff": "#e3fc62", "#0d1326": "#0b0c0a",
    "#1f293a40": "#25281f40", "#324155": "#2a2d24", "#1017292b": "#1516122b",
    "#101729c2": "#151612c2", "#83d9ff": "#eefd9c", "#d6f0ff": "#f5fec4",
    "#080c22": "#0b0c0a", "#070c22": "#000000", "#bff3d1": "#f5fec4",
    "#1f2637": "#1d1f19", "#2a2f40": "#2a2d24", "#086ec5": "#e3fc62",
    "#111729a6": "#151612a6", "#353b48": "#33362c", "#070c2266": "#00000066",
    "#192031": "#1b1d18",
}
COLOR_RE = re.compile("|".join(sorted(map(re.escape, COLORS), key=len, reverse=True)) + r"(?![0-9a-fA-F])", re.I)


def load_css():
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).read_text()
    html = urllib.request.urlopen("https://yobarpub.goorder.pl/").read().decode()
    href = re.search(r'href="(/static/css/main\.[^"]+\.css)"', html).group(1)
    return urllib.request.urlopen("https://yobarpub.goorder.pl" + href).read().decode()


def blocks(css):
    """Yield (prelude, body) for top-level blocks; body keeps nested braces."""
    i, n = 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j == -1:
            return
        depth, k = 1, j + 1
        while depth and k < n:
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        yield css[i:j].strip(), css[j + 1:k - 1]
        i = k


def keep_selector(sel):
    m = re.search(r"\.dark-mode\)?\s*[.#]?([\w-]+)", sel)
    return not (m and m.group(1) in SKIP)


def split_selectors(prelude):
    """Split a selector list on top-level commas (not inside :not(...) etc.)."""
    parts, depth, cur = [], 0, ""
    for ch in prelude:
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
            continue
        depth += {"(": 1, ")": -1}.get(ch, 0)
        cur += ch
    parts.append(cur.strip())
    return parts


def convert_rule(prelude, body):
    sels = [s for s in split_selectors(prelude) if ".dark-mode" in s]
    sels = [s for s in sels if keep_selector(s)]
    if not sels:
        return None
    sels = [s.replace("html:has(.dark-mode)", "html:has(body.body)").replace(".dark-mode", ".body") for s in sels]
    return ",".join(sels) + "{" + COLOR_RE.sub(lambda m: COLORS[m.group(0).lower()], body) + "}"


def convert(css):
    out = []
    for prelude, body in blocks(css):
        if prelude.startswith("@media") or prelude.startswith("@supports"):
            inner = [r for r in (convert_rule(p, b) for p, b in blocks(body)) if r]
            if inner:
                out.append(prelude + "{" + "".join(inner) + "}")
        elif not prelude.startswith("@") and ".dark-mode" in prelude:
            r = convert_rule(prelude, body)
            if r:
                out.append(r)
    return "\n".join(out)


def main():
    generated = convert(load_css())
    theme = THEME.read_text()
    block = f"{START}\n{generated}\n{END}"
    if START in theme:
        theme = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, theme, flags=re.S)
    else:
        # right after :root, so hand-written rules below win on equal specificity
        anchor = "/* ---------- Base ---------- */"
        theme = theme.replace(anchor, block + "\n\n" + anchor, 1)
    THEME.write_text(theme)
    print(f"{generated.count('{')} blocks written to {THEME.name}")


if __name__ == "__main__":
    main()
