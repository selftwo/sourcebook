"""Color parsing, OKLCH conversion, and WCAG 2.1 contrast.

The OKLab matrices are Bjorn Ottosson's published constants (https://bottosson.github.io/
posts/oklab/), written as literals rather than derived at runtime.
"""

from __future__ import annotations

import math
import re

NAMED = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0), "green": (0, 128, 0),
    "blue": (0, 0, 255), "gray": (128, 128, 128), "grey": (128, 128, 128),
    "silver": (192, 192, 192), "maroon": (128, 0, 0), "olive": (128, 128, 0),
    "lime": (0, 255, 0), "aqua": (0, 255, 255), "cyan": (0, 255, 255),
    "teal": (0, 128, 128), "navy": (0, 0, 128), "fuchsia": (255, 0, 255),
    "magenta": (255, 0, 255), "purple": (128, 0, 128), "yellow": (255, 255, 0),
    "orange": (255, 165, 0), "beige": (245, 245, 220), "ivory": (255, 255, 240),
    "wheat": (245, 222, 179), "linen": (250, 240, 230), "cornsilk": (255, 248, 220),
}

_HEX = re.compile(r"^#([0-9a-fA-F]{3,8})$")
_FUNC = re.compile(r"^(rgba?|hsla?|oklch|oklab)\((.*)\)$", re.I | re.S)


def _nums(body: str) -> list[str]:
    return [p for p in re.split(r"[\s,/]+", body.strip()) if p]


def parse_color(s: str) -> tuple[float, float, float] | None:
    """Returns sRGB in 0..1, or None when the value is not a resolvable opaque color."""
    if not s:
        return None
    s = s.strip().lower()
    if s in ("transparent", "currentcolor", "inherit", "initial", "unset", "none"):
        return None
    if s in NAMED:
        r, g, b = NAMED[s]
        return r / 255, g / 255, b / 255
    m = _HEX.match(s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h[:3])
        elif len(h) in (6, 8):
            h = h[:6]
        else:
            return None
        return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)
    m = _FUNC.match(s)
    if not m:
        return None
    fn, body = m.group(1), m.group(2)
    parts = _nums(body)
    try:
        if fn in ("rgb", "rgba"):
            vals = []
            for p in parts[:3]:
                vals.append(float(p[:-1]) / 100 if p.endswith("%") else float(p) / 255)
            return tuple(min(1.0, max(0.0, v)) for v in vals)  # type: ignore[return-value]
        if fn in ("hsl", "hsla"):
            h = float(re.sub(r"deg$", "", parts[0]))
            sat = float(parts[1].rstrip("%")) / 100
            lig = float(parts[2].rstrip("%")) / 100
            return _hsl_to_rgb(h, sat, lig)
        if fn == "oklch":
            lig = float(parts[0].rstrip("%")) / (100 if parts[0].endswith("%") else 1)
            chroma = float(parts[1])
            hue = float(re.sub(r"deg$", "", parts[2])) if len(parts) > 2 else 0.0
            return oklch_to_srgb(lig, chroma, hue)
    except (ValueError, IndexError):
        return None
    return None


def _hsl_to_rgb(h: float, s: float, lightness: float) -> tuple[float, float, float]:
    h = (h % 360) / 360
    if s == 0:
        return lightness, lightness, lightness
    q = lightness * (1 + s) if lightness < 0.5 else lightness + s - lightness * s
    p = 2 * lightness - q

    def hue(t: float) -> float:
        t = t % 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    return hue(h + 1 / 3), hue(h), hue(h - 1 / 3)


def _to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _from_linear(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def srgb_to_oklch(r: float, g: float, b: float) -> tuple[float, float, float]:
    lr, lg, lb = _to_linear(r), _to_linear(g), _to_linear(b)
    l = 0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb
    m = 0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb
    s = 0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb
    l_, m_, s_ = _cbrt(l), _cbrt(m), _cbrt(s)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(a, bb)
    H = math.degrees(math.atan2(bb, a)) % 360
    return L, C, H


def oklch_to_srgb(L: float, C: float, H: float) -> tuple[float, float, float]:
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    lr = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    lg = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    lb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(min(1.0, max(0.0, _from_linear(c))) for c in (lr, lg, lb))  # type: ignore[return-value]


def _cbrt(x: float) -> float:
    return math.copysign(abs(x) ** (1 / 3), x)


def relative_luminance(r: float, g: float, b: float) -> float:
    return 0.2126 * _to_linear(r) + 0.7152 * _to_linear(g) + 0.0722 * _to_linear(b)


def contrast_ratio(fg: tuple[float, float, float], bg: tuple[float, float, float]) -> float:
    l1 = relative_luminance(*fg)
    l2 = relative_luminance(*bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


# A cream is a *perceptibly warm* off-white. Below 0.01 chroma the hue is noise, so the
# band deliberately does not fire on a true neutral.
CREAM_MIN_CHROMA = 0.01


def in_cream_band(L: float, C: float, h: float) -> bool:
    return 0.84 <= L <= 0.97 and CREAM_MIN_CHROMA <= C < 0.06 and 40 <= h <= 100


def is_neutral(rgb: tuple[float, float, float], threshold: float = 0.04) -> bool:
    _, C, _ = srgb_to_oklch(*rgb)
    return C < threshold


def hue_of(rgb: tuple[float, float, float]) -> float:
    return srgb_to_oklch(*rgb)[2]
