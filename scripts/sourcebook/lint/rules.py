"""The anti-slop and accessibility rule registry.

Severity `error` blocks the ship gate and cannot be waived. Severity `warn` must be
acknowledged in `sourcebook.json.lint_waivers` with a written reason or it becomes an error.
That asymmetry is the point: taste you can argue with is a warning; taste that is now
mechanical is an error.

Every rule refuses to fire on a value it could not resolve. Unresolved values are counted
and printed. Guessing is worse than reporting a gap.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .. import EXIT_GATE, EXIT_OK, EXIT_USAGE
from . import color as C
from . import css as CSS
from .html import Document, Node, parse

RULES_VERSION = 1

OVERUSED_FONTS = {"inter", "roboto", "geist", "space grotesk", "plus jakarta sans", "fraunces"}
GENERIC_FAMILIES = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
                    "ui-sans-serif", "ui-serif", "ui-monospace", "ui-rounded", "emoji",
                    "math", "fangsong", "-apple-system", "blinkmacsystemfont", "inherit"}
BUZZWORDS = ["streamline", "empower", "supercharge", "leverage", "unleash", "seamless",
             "world-class", "enterprise-grade", "next-generation", "cutting-edge",
             "game-changer", "mission-critical", "deep dive", "unlock"]
META_PHRASES = [
    (r"\b[a-z]+ theater\b", "X theater"),
    (r"\bnot just\b[^.]{0,60}\bit'?s\b", "not just X, it's Y"),
    (r"\b(it'?s|that'?s|this is) actually\b", "actually X"),
]
SUBRESOURCE = {"img": "src", "script": "src", "link": "href", "iframe": "src",
               "source": "src", "video": "src", "audio": "src", "embed": "src",
               "object": "data", "track": "src", "input": "src"}
INTERACTIVE_SEL = re.compile(r"(^|[\s,])(a|button|summary|\.btn|\.button|\[role=)", re.I)


@dataclass
class Finding:
    rule_id: str
    severity: str
    file: str
    line: int
    snippet: str
    detail: str

    def as_dict(self) -> dict:
        return {"rule": self.rule_id, "severity": self.severity, "file": self.file,
                "line": self.line, "snippet": self.snippet, "detail": self.detail}


@dataclass
class Ctx:
    doc: Document
    path: str
    css_rules: list = field(default_factory=list)
    props: dict = field(default_factory=dict)
    unresolved: int = 0

    def rv(self, value: str) -> tuple[str, bool]:
        out, ok = CSS.resolve_var(value, self.props)
        if not ok:
            self.unresolved += 1
        return out, ok

    def styled(self):
        """Rules that actually paint, i.e. everything except @keyframes shells."""
        return [r for r in self.css_rules if not (r.at_rule or "").startswith("@keyframes")
                and not r.selector.startswith("@")]


def build_ctx(html: str, path: str) -> Ctx:
    doc = parse(html, path)
    rule_list = CSS.rules(doc.css)
    return Ctx(doc=doc, path=path, css_rules=rule_list, props=CSS.custom_props(rule_list))


# --------------------------------------------------------------- selector matching


@dataclass
class Compound:
    tag: str | None
    classes: tuple
    ident: str | None


_COMPOUND = re.compile(r"^(\*|[a-zA-Z][a-zA-Z0-9-]*)?((?:[.#][A-Za-z0-9_-]+)*)$")


def parse_selector(sel: str) -> list[Compound] | None:
    """Supports element, .class, #id, and descendant combinators. Anything richer is
    reported as unsupported rather than approximated."""
    sel = sel.strip()
    if not sel or any(ch in sel for ch in (">", "+", "~", "[", "(", "*=")):
        return None
    parts = []
    for token in sel.split():
        if token == ":root":
            parts.append(Compound("html", (), None))
            continue
        if ":" in token or "::" in token:
            return None
        m = _COMPOUND.match(token)
        if not m:
            return None
        tag = m.group(1)
        classes, ident = [], None
        for piece in re.findall(r"[.#][A-Za-z0-9_-]+", m.group(2) or ""):
            (classes.append(piece[1:]) if piece[0] == "." else None)
            if piece[0] == "#":
                ident = piece[1:]
        parts.append(Compound(None if tag in (None, "*") else tag.lower(), tuple(classes), ident))
    return parts or None


def specificity(sel: str) -> tuple[int, int, int]:
    ids = len(re.findall(r"#[A-Za-z0-9_-]+", sel))
    classes = len(re.findall(r"[.:\[][A-Za-z0-9_-]+", sel))
    tags = len(re.findall(r"(?:^|[\s>+~])([a-zA-Z][a-zA-Z0-9-]*)", sel))
    return ids, classes, tags


def _matches_compound(node: Node, comp: Compound) -> bool:
    if comp.tag and node.tag != comp.tag:
        return False
    if comp.ident and node.attrs.get("id") != comp.ident:
        return False
    node_classes = set(node.classes)
    return all(c in node_classes for c in comp.classes)


def matches(chain: list[Node], compounds: list[Compound]) -> bool:
    """chain is root..node. Descendant matching, right to left."""
    i = len(chain) - 1
    j = len(compounds) - 1
    if not _matches_compound(chain[i], compounds[j]):
        return False
    i -= 1
    j -= 1
    while j >= 0:
        while i >= 0 and not _matches_compound(chain[i], compounds[j]):
            i -= 1
        if i < 0:
            return False
        i -= 1
        j -= 1
    return True


# ------------------------------------------------------------------ computed style

INHERITED = ("color", "font-size", "font-weight", "font-family")


def compute_styles(ctx: Ctx) -> dict[int, dict]:
    """Resolve color / background / font-size / font-weight per node, honestly.

    A node whose value depends on an unsupported selector or an unresolved var() simply has
    no entry for that property, and the contrast rules skip it.
    """
    matched: dict[int, list[tuple[tuple, int, dict]]] = {}
    order = 0
    for rule in ctx.styled():
        for sel in rule.selectors:
            compounds = parse_selector(sel)
            order += 1
            if compounds is None:
                continue
            spec = specificity(sel)
            for node in ctx.doc.walk():
                if node.tag.startswith("#"):
                    continue
                if matches(node.path(), compounds):
                    matched.setdefault(id(node), []).append((spec, order, rule.decls))

    computed: dict[int, dict] = {}

    def visit(node: Node, inherited: dict):
        if node.tag.startswith("#"):
            style = dict(inherited)
        else:
            decls: dict[str, str] = {}
            for _, _, d in sorted(matched.get(id(node), []), key=lambda t: (t[0], t[1])):
                decls.update(d)
            inline = node.attrs.get("style")
            if inline:
                decls.update(CSS._split_decls(inline))
            style = dict(inherited)
            parent_px = inherited.get("font_px", 16.0)
            if "font-size" in decls:
                value, ok = ctx.rv(decls["font-size"])
                px = None
                if value.startswith("clamp("):
                    lo, _hi = CSS.clamp_bounds(value)
                    px = lo  # the small-viewport case is the one that fails contrast
                else:
                    px = CSS.length_px(value, 16.0, parent_px)
                if ok and px:
                    style["font_px"] = px
            if "font-weight" in decls:
                value, ok = ctx.rv(decls["font-weight"])
                weight = {"bold": 700, "bolder": 700, "normal": 400, "lighter": 300}.get(
                    value.strip().lower())
                if weight is None:
                    try:
                        weight = int(float(value.strip()))
                    except ValueError:
                        weight = None
                if ok and weight:
                    style["weight"] = weight
            if "color" in decls:
                value, ok = ctx.rv(decls["color"])
                rgb = C.parse_color(value) if ok else None
                if rgb:
                    style["fg"] = rgb
                elif ok and value.strip().lower() not in ("inherit", "currentcolor"):
                    style.pop("fg", None)
            for prop in ("background-color", "background"):
                if prop in decls:
                    value, ok = ctx.rv(decls[prop])
                    if not ok:
                        continue
                    rgb = C.parse_color(value.split()[0] if prop == "background" and " " in value
                                        else value)
                    if rgb is None and prop == "background":
                        for token in CSS.split_args(value.replace(" ", ",")):
                            rgb = C.parse_color(token)
                            if rgb:
                                break
                    if rgb:
                        style["bg"] = rgb
        computed[id(node)] = style
        child_inherit = {k: v for k, v in style.items()
                         if k in ("fg", "font_px", "weight", "bg")}
        for child in node.children:
            visit(child, child_inherit)

    visit(ctx.doc.root, {"font_px": 16.0, "weight": 400})
    return computed


# ------------------------------------------------------------------------- helpers


def _lengths(value: str) -> list[float]:
    out = []
    for token in re.findall(r"-?\d*\.?\d+(?:px|rem|em|pt)?", value):
        px = CSS.length_px(token)
        if px is not None:
            out.append(px)
    return out


def _colors_in(value: str) -> list[tuple[float, float, float]]:
    out = []
    for token in re.findall(r"#[0-9a-fA-F]{3,8}|(?:rgba?|hsla?|oklch)\([^)]*\)|\b[a-z]{3,20}\b",
                            value):
        rgb = C.parse_color(token)
        if rgb:
            out.append(rgb)
    return out


def _font_px_of(ctx: Ctx, rule) -> float | None:
    if "font-size" not in rule.decls:
        return None
    value, ok = ctx.rv(rule.decls["font-size"])
    if not ok:
        return None
    if value.startswith("clamp("):
        lo, hi = CSS.clamp_bounds(value)
        return hi or lo
    return CSS.length_px(value)


def _text_nodes(ctx: Ctx):
    for node in ctx.doc.walk():
        if node.tag in ("script", "style", "head", "title", "#document"):
            continue
        if any(a.tag in ("head", "script", "style") for a in node.ancestors()):
            continue
        if node.own_text().strip():
            yield node


# ------------------------------------------------------------------------ the rules


def check_gradient_text(ctx: Ctx):
    for r in ctx.styled():
        clip = r.decls.get("background-clip") or r.decls.get("-webkit-background-clip")
        if not clip or "text" not in clip:
            continue
        bg = r.decls.get("background-image") or r.decls.get("background") or ""
        value, ok = ctx.rv(bg)
        if not ok:
            continue
        if "gradient(" in value:
            yield Finding("", "", ctx.path, r.line, r.selector,
                          "background-clip:text over a gradient")


def check_side_stripe(ctx: Ctx):
    for r in ctx.styled():
        for side in ("border-left", "border-right"):
            width = None
            col = None
            if side in r.decls:
                value, ok = ctx.rv(r.decls[side])
                if not ok:
                    continue
                lens = _lengths(value)
                width = lens[0] if lens else None
                cols = _colors_in(value)
                col = cols[0] if cols else None
            if f"{side}-width" in r.decls:
                value, ok = ctx.rv(r.decls[f"{side}-width"])
                if ok:
                    width = CSS.length_px(value)
            if f"{side}-color" in r.decls:
                value, ok = ctx.rv(r.decls[f"{side}-color"])
                if ok:
                    col = C.parse_color(value)
            if width is not None and width >= 2 and col is not None and not C.is_neutral(col):
                yield Finding("", "", ctx.path, r.line, f"{r.selector} {{ {side} }}",
                              f"{width:g}px accent stripe on the edge of a block")


def check_over_round(ctx: Ctx):
    for r in ctx.styled():
        if "border-radius" not in r.decls:
            continue
        value, ok = ctx.rv(r.decls["border-radius"])
        if not ok or "%" in value:
            continue
        lens = _lengths(value)
        if not lens:
            continue
        radius = max(lens)
        if radius >= 999:  # a pill, deliberately
            continue
        if radius >= 24:
            yield Finding("", "", ctx.path, r.line, r.selector,
                          f"border-radius {radius:g}px on a block that is neither pill nor circle")


def check_ghost_card(ctx: Ctx):
    for r in ctx.styled():
        border = r.decls.get("border") or r.decls.get("border-width")
        shadow = r.decls.get("box-shadow")
        if not border or not shadow:
            continue
        bval, ok1 = ctx.rv(border)
        sval, ok2 = ctx.rv(shadow)
        if not (ok1 and ok2) or sval.strip().lower() == "none":
            continue
        blens = _lengths(bval)
        slens = _lengths(sval)
        if blens and blens[0] <= 1.5 and len(slens) >= 3 and slens[2] >= 16:
            yield Finding("", "", ctx.path, r.line, r.selector,
                          f"1px border plus a {slens[2]:g}px blur shadow on the same rule")


def check_stripe_bg(ctx: Ctx):
    for r in ctx.styled():
        for prop in ("background", "background-image"):
            if prop not in r.decls:
                continue
            value, ok = ctx.rv(r.decls[prop])
            if ok and "repeating-linear-gradient(" in value.replace(" ", ""):
                yield Finding("", "", ctx.path, r.line, r.selector,
                              "repeating-linear-gradient used as a background")


PAGE_SELECTORS = {"html", "body", ":root", ".page", ".sheet", ".paper", "main"}


def check_cream_band(ctx: Ctx):
    for r in ctx.styled():
        if not any(s in PAGE_SELECTORS for s in r.selectors):
            continue
        for prop in ("background-color", "background"):
            if prop not in r.decls:
                continue
            value, ok = ctx.rv(r.decls[prop])
            if not ok:
                continue
            cols = _colors_in(value)
            if not cols:
                continue
            L, chroma, hue = C.srgb_to_oklch(*cols[0])
            if C.in_cream_band(L, chroma, hue):
                yield Finding("", "", ctx.path, r.line, r.selector,
                              f"page background sits in the cream band "
                              f"(OKLCH L={L:.2f} C={chroma:.3f} h={hue:.0f})")
                return


def check_ai_palette(ctx: Ctx):
    for r in ctx.styled():
        for prop, value in r.decls.items():
            if "gradient(" not in value:
                continue
            resolved, ok = ctx.rv(value)
            if not ok:
                continue
            violet = [c for c in _colors_in(resolved)
                      if 255 <= C.srgb_to_oklch(*c)[2] <= 330 and C.srgb_to_oklch(*c)[1] >= 0.05]
            if len(violet) >= 2:
                yield Finding("", "", ctx.path, r.line, r.selector,
                              "purple/violet gradient pair as the accent")
                return
    page_bg = None
    for r in ctx.styled():
        if any(s in PAGE_SELECTORS for s in r.selectors):
            for prop in ("background-color", "background"):
                if prop in r.decls:
                    value, ok = ctx.rv(r.decls[prop])
                    cols = _colors_in(value) if ok else []
                    if cols:
                        page_bg = cols[0]
    if page_bg is None or C.srgb_to_oklch(*page_bg)[0] >= 0.25:
        return
    for r in ctx.styled():
        for prop in ("color", "border-color", "background-color", "--accent"):
            if prop not in r.decls:
                continue
            value, ok = ctx.rv(r.decls[prop])
            rgb = C.parse_color(value) if ok else None
            if not rgb:
                continue
            L, chroma, hue = C.srgb_to_oklch(*rgb)
            if 180 <= hue <= 215 and chroma >= 0.08 and L > 0.6:
                yield Finding("", "", ctx.path, r.line, r.selector,
                              "cyan accent on near-black; the default AI palette")
                return


def _declared_families(ctx: Ctx) -> set[str]:
    fams: set[str] = set()
    for r in ctx.styled():
        for prop in ("font-family", "--font-display", "--font-body", "--font-mono"):
            if prop not in r.decls:
                continue
            value, ok = ctx.rv(r.decls[prop])
            if not ok:
                continue
            for name in value.split(","):
                clean = name.strip().strip("'\"").lower()
                if clean and clean not in GENERIC_FAMILIES:
                    fams.add(clean)
    return fams


def check_sole_overused_font(ctx: Ctx):
    fams = _declared_families(ctx)
    if len(fams) == 1 and next(iter(fams)) in OVERUSED_FONTS:
        yield Finding("", "", ctx.path, 0, next(iter(fams)),
                      "the only declared family is one of 2026's defaults")


def check_flat_scale(ctx: Ctx):
    sizes = set()
    for r in ctx.styled():
        px = _font_px_of(ctx, r)
        if px and px >= 10:
            sizes.add(round(px, 2))
    ladder = sorted(sizes)
    if len(ladder) < 3:
        return
    for a, b in zip(ladder, ladder[1:]):
        if b / a < 1.25 - 1e-6:
            yield Finding("", "", ctx.path, 0, f"{a:g}px -> {b:g}px",
                          f"adjacent type steps differ by {b / a:.2f}x; the scale reads as mush")
            return


def check_hero_shout(ctx: Ctx):
    for r in ctx.styled():
        if "font-size" not in r.decls:
            continue
        value, ok = ctx.rv(r.decls["font-size"])
        if not ok or not value.startswith("clamp("):
            continue
        _lo, hi = CSS.clamp_bounds(value)
        if hi and hi > 96:
            yield Finding("", "", ctx.path, r.line, r.selector,
                          f"clamp() tops out at {hi:g}px; that is a shout, not a hierarchy")


def check_tracking_floor(ctx: Ctx):
    for r in ctx.styled():
        if "letter-spacing" not in r.decls:
            continue
        value, ok = ctx.rv(r.decls["letter-spacing"])
        if not ok:
            continue
        m = re.match(r"^(-?\d*\.?\d+)em$", value.strip())
        if not m or float(m.group(1)) >= -0.04:
            continue
        px = _font_px_of(ctx, r)
        if px is None or px >= 32:
            yield Finding("", "", ctx.path, r.line, r.selector,
                          f"letter-spacing {value} at display size crushes the letterforms")


def check_eyebrow_reflex(ctx: Ctx):
    selectors = []
    for r in ctx.styled():
        if (r.decls.get("text-transform", "").strip().lower() != "uppercase"):
            continue
        ls, ok = ctx.rv(r.decls.get("letter-spacing", "0"))
        if not ok:
            continue
        m = re.match(r"^(\d*\.?\d+)(em|px)$", ls.strip())
        if not m or float(m.group(1)) <= 0:
            continue
        px = _font_px_of(ctx, r)
        if px is not None and px > 13.6:
            continue
        selectors.extend(r.selectors)
    if not selectors:
        return
    count = 0
    for sel in selectors:
        compounds = parse_selector(sel)
        if compounds is None:
            continue
        for node in ctx.doc.walk():
            if not node.tag.startswith("#") and matches(node.path(), compounds) \
                    and node.text().strip():
                count += 1
    if count >= 3:
        yield Finding("", "", ctx.path, 0, ", ".join(sorted(set(selectors))[:4]),
                      f"{count} tiny uppercase tracked kickers; the eyebrow is a reflex")


def check_numbered_scaffold(ctx: Ctx):
    hits = [n for n in _text_nodes(ctx) if re.fullmatch(r"0[1-9]", n.own_text().strip())]
    if len(hits) >= 3:
        yield Finding("", "", ctx.path, hits[0].line, hits[0].own_text().strip(),
                      f"{len(hits)} '01/02/03' section markers; numbering is not structure")


_SKIP_CLONE = {"li", "option", "tr", "td", "th", "dt", "dd", "br", "path"}


def check_card_grid_clone(ctx: Ctx):
    for node in ctx.doc.walk():
        if node.tag == "svg" or any(a.tag == "svg" for a in node.ancestors()):
            continue  # repeated ticks and gridlines are what a chart is made of
        groups: dict[tuple, list[Node]] = {}
        for child in node.children:
            if child.tag.startswith("#") or child.tag in _SKIP_CLONE:
                continue
            sig = (child.tag, tuple(sorted(child.classes)),
                   tuple(g.tag for g in child.children if not g.tag.startswith("#")))
            groups.setdefault(sig, []).append(child)
        for sig, members in groups.items():
            if len(members) >= 4 and len(sig[2]) >= 2:
                yield Finding("", "", ctx.path, members[0].line,
                              f"{sig[0]}.{'.'.join(sig[1])}",
                              f"{len(members)} identical sibling cards; the grid is doing no work")
                return


def check_em_dash(ctx: Ctx):
    text = ctx.doc.body_text()
    if "—" in text or " -- " in text:
        yield Finding("", "", ctx.path, 0, "—",
                      "em dash in body copy; a period or a colon is almost always better")


def check_buzzword(ctx: Ctx):
    text = ctx.doc.body_text().lower()
    hits = sorted({w for w in BUZZWORDS if re.search(r"\b" + re.escape(w) + r"\b", text)})
    if hits:
        yield Finding("", "", ctx.path, 0, ", ".join(hits),
                      "marketing vocabulary in a document whose whole claim is accuracy")


def check_meta_phrase(ctx: Ctx):
    text = ctx.doc.body_text().lower()
    for pattern, label in META_PHRASES:
        if re.search(pattern, text):
            yield Finding("", "", ctx.path, 0, label, "a stock rhetorical move, not a sentence")
            return


def _contrast(ctx: Ctx, large: bool):
    computed = compute_styles(ctx)
    seen: set[tuple] = set()
    for node in _text_nodes(ctx):
        style = computed.get(id(node), {})
        fg, bg = style.get("fg"), style.get("bg")
        if fg is None or bg is None:
            ctx.unresolved += 1
            continue
        px = style.get("font_px", 16.0)
        weight = style.get("weight", 400)
        is_large = px >= 18 or (weight >= 700 and px >= 14)
        if is_large != large:
            continue
        ratio = C.contrast_ratio(fg, bg)
        need = 3.0 if large else 4.5
        if ratio + 1e-9 >= need:
            continue
        key = (fg, bg, is_large)
        if key in seen:
            continue
        seen.add(key)
        fg_hex = "#%02x%02x%02x" % tuple(round(c * 255) for c in fg)
        bg_hex = "#%02x%02x%02x" % tuple(round(c * 255) for c in bg)
        yield Finding("", "", ctx.path, node.line, f"{fg_hex} on {bg_hex}",
                      f"contrast ratio {ratio:.2f}:1 at {px:g}px, below {need}:1")


def check_contrast_body(ctx: Ctx):
    yield from _contrast(ctx, large=False)


def check_contrast_large(ctx: Ctx):
    yield from _contrast(ctx, large=True)


def check_reduced_motion(ctx: Ctx):
    css = ctx.doc.css
    animates = "@keyframes" in css or any(
        k in r.decls for r in ctx.styled() for k in ("transition", "animation",
                                                     "transition-duration", "animation-name"))
    if not animates:
        return
    guarded = any("prefers-reduced-motion" in (r.at_rule or "") and "reduce" in (r.at_rule or "")
                  for r in ctx.css_rules)
    if not guarded:
        yield Finding("", "", ctx.path, 0, "@keyframes / transition",
                      "motion with no @media (prefers-reduced-motion: reduce) escape")


HIDDEN = {"opacity": "0", "visibility": "hidden", "display": "none"}


def _hides(rule) -> bool:
    return any(rule.decls.get(prop, "").strip() == want for prop, want in HIDDEN.items())


def _reveals(rule) -> bool:
    if rule.decls.get("display", "").strip() not in ("", "none"):
        return True
    if rule.decls.get("visibility", "").strip() == "visible":
        return True
    opacity = rule.decls.get("opacity", "").strip()
    return bool(opacity) and opacity != "0"


def check_reveal_gate(ctx: Ctx):
    """Hiding content behind a JS-added class is fine; hiding it unconditionally and
    revealing it with one is not. Only the second ships blank in a headless renderer."""
    script = "\n".join(ctx.doc.scripts)
    if not script.strip():
        return
    js_classes = set(re.findall(r"['\"`]([A-Za-z0-9_-]{2,})['\"`]", script))
    if not js_classes:
        return
    for r in ctx.styled():
        if not _hides(r):
            continue
        for sel in r.selectors:
            classes = set(re.findall(r"\.([A-Za-z0-9_-]+)", sel))
            if not classes or (classes & js_classes):
                continue  # the hide itself is gated behind JS: progressive enhancement
            for r2 in ctx.styled():
                if not _reveals(r2):
                    continue
                for sel2 in r2.selectors:
                    c2 = set(re.findall(r"\.([A-Za-z0-9_-]+)", sel2))
                    if classes <= c2 and (c2 - classes) & js_classes:
                        yield Finding("", "", ctx.path, r.line, sel,
                                      f"hidden by default and revealed only by the JS class "
                                      f"'{sorted((c2 - classes) & js_classes)[0]}'; "
                                      f"it ships blank in a headless renderer")
                        return


def check_tap_target(ctx: Ctx):
    for r in ctx.styled():
        if not INTERACTIVE_SEL.search(r.selector):
            continue
        for prop in ("height", "min-height", "width", "min-width"):
            if prop not in r.decls:
                continue
            value, ok = ctx.rv(r.decls[prop])
            if not ok:
                continue
            px = CSS.length_px(value)
            if px is not None and 0 < px < 44:
                yield Finding("", "", ctx.path, r.line, r.selector,
                              f"{prop}:{px:g}px on an interactive element, under the 44px floor")
                return


def check_img_alt(ctx: Ctx):
    for img in ctx.doc.find_all("img"):
        if "alt" not in img.attrs:
            yield Finding("", "", ctx.path, img.line, img.attrs.get("src", "<img>"),
                          "img without an alt attribute")


def check_lang_title(ctx: Ctx):
    html = ctx.doc.find_all("html")
    if not html or not html[0].attrs.get("lang"):
        yield Finding("", "", ctx.path, 1, "<html>", "missing lang attribute")
    if not ctx.doc.find_all("title"):
        yield Finding("", "", ctx.path, 1, "<head>", "missing <title>")
    if not any(m.attrs.get("name") == "viewport" for m in ctx.doc.find_all("meta")):
        yield Finding("", "", ctx.path, 1, "<head>", "missing viewport meta")


def check_focus_visible(ctx: Ctx):
    kills = [r for r in ctx.styled()
             if r.decls.get("outline", "").strip().lower() in ("none", "0")
             and ":focus-visible" not in r.selector]
    if not kills:
        return
    if any(":focus-visible" in r.selector for r in ctx.css_rules):
        return
    r = kills[0]
    yield Finding("", "", ctx.path, r.line, r.selector,
                  "outline:none with no :focus-visible replacement anywhere")


def _is_external(url: str) -> bool:
    u = url.strip().lower()
    return u.startswith(("http://", "https://", "//")) or u.startswith("file://")


def check_external_ref(ctx: Ctx):
    for node in ctx.doc.walk():
        attr = SUBRESOURCE.get(node.tag)
        if attr and _is_external(node.attrs.get(attr, "")):
            yield Finding("", "", ctx.path, node.line,
                          f"<{node.tag} {attr}={node.attrs.get(attr)}>",
                          "off-document subresource; the artifact stops working offline")
    for m in re.finditer(r"@import\s+(?:url\()?['\"]?([^'\")]+)", ctx.doc.css):
        if _is_external(m.group(1)):
            yield Finding("", "", ctx.path, 0, m.group(0), "@import of an external stylesheet")
    for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)", ctx.doc.css):
        if _is_external(m.group(1)):
            yield Finding("", "", ctx.path, 0, m.group(0), "url() pointing off-document")


def check_zindex_arbitrary(ctx: Ctx):
    for r in ctx.styled():
        if "z-index" not in r.decls:
            continue
        raw = r.decls["z-index"]
        if "var(" in raw:
            continue
        try:
            z = int(float(raw.strip()))
        except ValueError:
            continue
        if z >= 100:
            yield Finding("", "", ctx.path, r.line, r.selector,
                          f"z-index:{z} outside a named scale")


def check_overflow_risk(ctx: Ctx):
    container_max = 0.0
    for r in ctx.styled():
        if "max-width" in r.decls and "clamp(" not in r.decls["max-width"]:
            value, ok = ctx.rv(r.decls["max-width"])
            px = CSS.length_px(value) if ok else None
            if px:
                container_max = max(container_max, px)
    if not container_max:
        return
    for r in ctx.styled():
        for prop in ("width", "max-width"):
            if prop not in r.decls or "clamp(" not in r.decls[prop]:
                continue
            value, ok = ctx.rv(r.decls[prop])
            if not ok:
                continue
            _lo, hi = CSS.clamp_bounds(value)
            if hi and hi > container_max:
                yield Finding("", "", ctx.path, r.line, r.selector,
                              f"clamp() max {hi:g}px exceeds the {container_max:g}px container")
                return


RULES = [
    {"id": "slop.gradient-text", "severity": "error", "family": "slop", "check": check_gradient_text,
     "message": "Gradient text is decorative, never meaningful. Use a solid color; emphasize with weight or size."},
    {"id": "slop.side-stripe", "severity": "error", "family": "slop", "check": check_side_stripe,
     "message": "The colored left stripe is the 2023 dashboard card. Use a rule, a heading, or nothing."},
    {"id": "slop.over-round", "severity": "error", "family": "slop", "check": check_over_round,
     "message": "Radius that large is a soft-toy shape. Pills and circles are fine; blobs are not."},
    {"id": "slop.ghost-card", "severity": "error", "family": "slop", "check": check_ghost_card,
     "message": "A hairline border plus a big soft shadow is the ghost card. Pick one edge treatment."},
    {"id": "slop.stripe-bg", "severity": "error", "family": "slop", "check": check_stripe_bg,
     "message": "Repeating stripes are texture in place of structure."},
    {"id": "slop.cream-band", "severity": "error", "family": "slop", "check": check_cream_band,
     "message": "The warm off-white page is the default 'editorial' reflex. Commit to a real ground."},
    {"id": "slop.ai-palette", "severity": "error", "family": "slop", "check": check_ai_palette,
     "message": "Purple-violet gradients and cyan-on-black are the house style of every model."},
    {"id": "slop.sole-overused-font", "severity": "warn", "family": "slop", "check": check_sole_overused_font,
     "message": "One 2026 default family and nothing else reads as a template."},
    {"id": "slop.flat-scale", "severity": "warn", "family": "slop", "check": check_flat_scale,
     "message": "Type steps under 1.25x do not register as hierarchy."},
    {"id": "slop.hero-shout", "severity": "error", "family": "slop", "check": check_hero_shout,
     "message": "A hero over 6rem is volume, not emphasis."},
    {"id": "slop.tracking-floor", "severity": "error", "family": "slop", "check": check_tracking_floor,
     "message": "Negative tracking past -0.04em is a trend, and it damages legibility."},
    {"id": "slop.eyebrow-reflex", "severity": "error", "family": "slop", "check": check_eyebrow_reflex,
     "message": "Tiny uppercase tracked kickers on every section are a reflex, not a system."},
    {"id": "slop.numbered-scaffold", "severity": "warn", "family": "slop", "check": check_numbered_scaffold,
     "message": "01/02/03 markers imply a sequence the content does not have."},
    {"id": "slop.card-grid-clone", "severity": "warn", "family": "slop", "check": check_card_grid_clone,
     "message": "Four identical cards is a list wearing a costume."},
    {"id": "copy.em-dash", "severity": "warn", "family": "copy", "check": check_em_dash,
     "message": "The em dash is the tell. Use a period, a colon, or a comma."},
    {"id": "copy.buzzword", "severity": "warn", "family": "copy", "check": check_buzzword,
     "message": "Buzzwords in a cited artifact undermine the citations."},
    {"id": "copy.meta-phrase", "severity": "warn", "family": "copy", "check": check_meta_phrase,
     "message": "Stock rhetorical moves read as generated."},
    {"id": "a11y.contrast-body", "severity": "error", "family": "a11y", "check": check_contrast_body,
     "message": "Body text must clear 4.5:1."},
    {"id": "a11y.contrast-large", "severity": "error", "family": "a11y", "check": check_contrast_large,
     "message": "Large text must clear 3:1."},
    {"id": "a11y.reduced-motion", "severity": "error", "family": "a11y", "check": check_reduced_motion,
     "message": "Every animation needs a reduced-motion path."},
    {"id": "a11y.reveal-gate", "severity": "error", "family": "a11y", "check": check_reveal_gate,
     "message": "Content must be readable with JavaScript disabled. Interactivity may enhance; it may not gate."},
    {"id": "a11y.tap-target", "severity": "warn", "family": "a11y", "check": check_tap_target,
     "message": "Interactive targets under 44x44 fail on a phone."},
    {"id": "a11y.img-alt", "severity": "error", "family": "a11y", "check": check_img_alt,
     "message": "Every image needs alt text describing what it shows."},
    {"id": "a11y.lang-title", "severity": "error", "family": "a11y", "check": check_lang_title,
     "message": "lang, title, and viewport are the floor for a shippable document."},
    {"id": "a11y.focus-visible", "severity": "error", "family": "a11y", "check": check_focus_visible,
     "message": "Removing the focus ring without replacing it strands keyboard users."},
    {"id": "struct.external-ref", "severity": "error", "family": "struct", "check": check_external_ref,
     "message": "An artifact is one self-contained file. No CDN, no external font, no remote image."},
    {"id": "struct.zindex-arbitrary", "severity": "warn", "family": "struct", "check": check_zindex_arbitrary,
     "message": "Arbitrary z-index values are a stacking bug waiting to happen."},
    {"id": "struct.overflow-risk", "severity": "warn", "family": "struct", "check": check_overflow_risk,
     "message": "A clamp() wider than its container overflows on a narrow viewport."},
]

RULE_BY_ID = {r["id"]: r for r in RULES}


def run(html: str, path: str, waivers: dict | None = None) -> tuple[list[Finding], list[Finding], int]:
    """Returns (findings, waived, unresolved_count)."""
    ctx = build_ctx(html, path)
    waivers = waivers or {}
    findings: list[Finding] = []
    waived: list[Finding] = []
    for rule in RULES:
        for f in rule["check"](ctx):
            f.rule_id = rule["id"]
            f.severity = rule["severity"]
            if rule["severity"] == "warn" and rule["id"] in waivers:
                waived.append(f)
            else:
                findings.append(f)
    findings.sort(key=lambda f: (0 if f.severity == "error" else 1, f.rule_id, f.line))
    return findings, waived, ctx.unresolved


def lint_file(path: Path, waivers: dict | None = None, as_json: bool = False) -> int:
    path = Path(path)
    if not path.is_file():
        print(f"E-LINT  {path}  no such file", file=sys.stderr)
        return EXIT_USAGE
    findings, waived, unresolved = run(path.read_text(encoding="utf-8"), str(path), waivers)
    errors = [f for f in findings if f.severity == "error"]
    warns = [f for f in findings if f.severity == "warn"]

    if as_json:
        print(json.dumps({
            "file": str(path), "rules_version": RULES_VERSION,
            "errors": [f.as_dict() for f in errors], "warns": [f.as_dict() for f in warns],
            "waived": [f.as_dict() for f in waived], "unresolved": unresolved,
        }, indent=2, ensure_ascii=False))
    else:
        for f in errors + warns:
            print(f"{f.severity.upper():<5} {f.rule_id:<26} {f.file}:{f.line}  {f.snippet}")
            print(f"      {f.detail}")
            print(f"      {RULE_BY_ID[f.rule_id]['message']}")
        for f in waived:
            print(f"WAIVED {f.rule_id:<26} {f.file}:{f.line}  {f.snippet}")
        print(f"\n{len(errors)} error(s), {len(warns)} warn(s), {len(waived)} waived, "
              f"{unresolved} unresolved value(s)")
        if warns:
            print("Waive a warn in sourcebook.json.lint_waivers with a written reason, or fix it. "
                  "Errors cannot be waived.")
    return EXIT_GATE if errors or warns else EXIT_OK
