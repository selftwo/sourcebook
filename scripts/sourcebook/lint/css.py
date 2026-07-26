"""A CSS tokenizer, not a parser. Enough to be honest and never enough to guess.

Any value the tokenizer cannot resolve is reported in an `unresolved` tally, and no rule
fires on a value it could not resolve.
"""

from __future__ import annotations

import re

COMMENT = re.compile(r"/\*.*?\*/", re.S)
LENGTH = re.compile(r"(-?\d*\.?\d+)\s*(px|rem|em|%|vw|vh|dvh|ch|pt|cm|mm|in|q)?", re.I)
VAR = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,\s*([^()]*(?:\([^()]*\)[^()]*)*))?\)")

ROOT_SELECTORS = {":root", "html", "body", "html,body", ":root,html"}


class Rule:
    __slots__ = ("selector", "decls", "at_rule", "line")

    def __init__(self, selector: str, decls: dict[str, str], at_rule: str | None, line: int):
        self.selector = selector
        self.decls = decls
        self.at_rule = at_rule
        self.line = line

    @property
    def selectors(self) -> list[str]:
        return [s.strip() for s in self.selector.split(",") if s.strip()]

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"Rule({self.selector!r}, at={self.at_rule!r})"


def _strip_comments(css: str) -> str:
    return COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), css)


def _split_decls(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    depth = 0
    buf = ""
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == ";" and depth == 0:
            _one(buf, out)
            buf = ""
        else:
            buf += ch
    _one(buf, out)
    return out


def _one(chunk: str, out: dict[str, str]) -> None:
    if ":" not in chunk:
        return
    prop, _, value = chunk.partition(":")
    prop = prop.strip().lower()
    value = value.strip()
    if prop and value:
        out[prop] = value


def rules(css: str, _at: str | None = None, _line_base: int = 1) -> list[Rule]:
    """Flatten a stylesheet into rules. @media/@supports contents are walked with at_rule set;
    @keyframes contents are recorded but deliberately not walked."""
    css = _strip_comments(css)
    out: list[Rule] = []
    i = 0
    n = len(css)
    line = _line_base
    while i < n:
        brace = css.find("{", i)
        if brace == -1:
            break
        prelude = css[i:brace].strip()
        line += css.count("\n", i, brace)
        depth = 1
        j = brace + 1
        while j < n and depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        body = css[brace + 1:j - 1]
        if prelude.startswith("@"):
            name = prelude.split()[0].lower()
            if name in ("@media", "@supports", "@layer", "@container"):
                out.extend(rules(body, prelude, line))
            elif name in ("@keyframes", "@-webkit-keyframes"):
                out.append(Rule(prelude, {}, prelude, line))
            elif name in ("@font-face", "@page", "@property"):
                out.append(Rule(prelude, _split_decls(body), _at, line))
            # @import has no block; handled by the raw-text scan in rules.py
        elif prelude:
            out.append(Rule(prelude, _split_decls(body), _at, line))
        line += css.count("\n", brace, j)
        i = j
    return out


def custom_props(rule_list: list[Rule]) -> dict[str, str]:
    props: dict[str, str] = {}
    for r in rule_list:
        if r.at_rule:
            continue
        if any(s in ROOT_SELECTORS or s == ":root" for s in r.selectors):
            for k, v in r.decls.items():
                if k.startswith("--"):
                    props[k] = v
    for r in rule_list:  # a second pass picks up custom props declared anywhere else
        for k, v in r.decls.items():
            if k.startswith("--"):
                props.setdefault(k, v)
    return props


def resolve_var(value: str, props: dict[str, str], depth: int = 1) -> tuple[str, bool]:
    """One level of var() substitution (plus its declared fallback). Deeper chains are honest
    failures rather than guesses."""
    if "var(" not in value:
        return value, True
    if depth < 0:
        return value, False
    resolved_all = True

    def sub(m):
        nonlocal resolved_all
        name, fallback = m.group(1), (m.group(2) or "").strip()
        if name in props:
            inner = props[name]
            if "var(" in inner:
                deeper, ok = resolve_var(inner, props, depth - 1)
                if not ok:
                    resolved_all = False
                return deeper
            return inner
        if fallback:
            return fallback
        resolved_all = False
        return m.group(0)

    out = VAR.sub(sub, value)
    if "var(" in out:
        resolved_all = False
    return out, resolved_all


def length_px(value: str, root_px: float = 16.0, font_px: float = 16.0) -> float | None:
    """Absolute length in px, or None when the unit is viewport-relative or unresolvable."""
    value = value.strip()
    m = LENGTH.fullmatch(value)
    if not m:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "px").lower()
    if unit == "px":
        return num
    if unit == "rem":
        return num * root_px
    if unit == "em":
        return num * font_px
    if unit == "pt":
        return num * 96 / 72
    if unit in ("cm", "mm", "in", "q"):
        return num * {"cm": 96 / 2.54, "mm": 96 / 25.4, "in": 96.0, "q": 96 / 101.6}[unit]
    return None


def clamp_bounds(value: str, root_px: float = 16.0) -> tuple[float | None, float | None]:
    """(min, max) of a clamp(); contrast evaluates at the minimum, the worst small-viewport case."""
    m = re.match(r"clamp\((.*)\)\s*$", value.strip(), re.I | re.S)
    if not m:
        return None, None
    parts = _split_args(m.group(1))
    if len(parts) != 3:
        return None, None
    return length_px(parts[0], root_px), length_px(parts[2], root_px)


def _split_args(s: str) -> list[str]:
    out, depth, buf = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(buf.strip())
    return out


split_args = _split_args
