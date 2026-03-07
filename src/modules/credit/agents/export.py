"""Export agent — renders a liberation plan as printable HTML."""

from __future__ import annotations

import html
from datetime import date
from typing import Any

_esc = html.escape

# ---------------------------------------------------------------------------
# CSS (inline, print-friendly)
# ---------------------------------------------------------------------------

_CSS = """
body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
h1 { color: #1a1a2e; border-bottom: 2px solid #16213e; }
h2 { color: #16213e; margin-top: 30px; }
.section { margin-bottom: 30px; page-break-inside: avoid; }
.metric { font-size: 24px; font-weight: bold; color: #e94560; }
.action-item { background: #f5f5f5; padding: 10px; margin: 5px 0; border-left: 3px solid #16213e; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; }
th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
th { background: #16213e; color: white; }
.phase { border: 1px solid #ddd; padding: 15px; margin: 10px 0; }
.phase-header { background: #16213e; color: white; padding: 8px; margin: -15px -15px 10px; }
@media print { .no-print { display: none; } body { padding: 0; } }
""".strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_get(data: dict, *keys: str, default: Any = "") -> Any:
    """Safely navigate nested dicts, returning *default* if any key is missing."""
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _section(title: str, content: str) -> str:
    """Wrap *content* in a div.section with an h2 title."""
    return f'<div class="section"><h2>{_esc(title)}</h2>{content}</div>'


def _html_wrap(body: str) -> str:
    """Wrap body content in full HTML document with CSS."""
    return (
        "<!DOCTYPE html>\n<html>\n<head>\n"
        '  <meta charset="utf-8">\n'
        "  <title>Liberation Plan</title>\n"
        f"  <style>{_CSS}</style>\n"
        "</head>\n<body>\n"
        f"{body}\n"
        "</body>\n</html>"
    )


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_situation(plan: dict) -> str:
    sit = _safe_get(plan, "situation", default={})
    tax = sit.get("poverty_tax", "Unknown") if isinstance(sit, dict) else "Unknown"
    barriers = sit.get("barriers", []) if isinstance(sit, dict) else []
    items = "".join(f"<li>{_esc(str(b))}</li>" for b in barriers)
    body = f'<p class="metric">{_esc(str(tax))}</p>'
    if items:
        body += f"<ul>{items}</ul>"
    return _section("Your Situation", body)


def _render_monday_morning(plan: dict) -> str:
    mm = _safe_get(plan, "monday_morning", default={})
    actions = mm.get("actions", []) if isinstance(mm, dict) else []
    items = "".join(
        f'<div class="action-item">{_esc(str(a.get("step", a) if isinstance(a, dict) else a))}</div>'
        for a in actions[:3]
    )
    return _section("Monday Morning Actions", items or "<p>No actions available.</p>")


def _render_battle_plan(plan: dict) -> str:
    bp = _safe_get(plan, "battle_plan", default={})
    phases = bp.get("phases", []) if isinstance(bp, dict) else []
    parts: list[str] = []
    for phase in phases:
        name = _esc(str(phase.get("name", "Phase")))
        acts = phase.get("actions", [])
        act_html = "".join(f"<li>{_esc(str(a))}</li>" for a in acts)
        parts.append(
            f'<div class="phase">'
            f'<div class="phase-header">{name}</div>'
            f"<ul>{act_html}</ul></div>"
        )
    return _section("Battle Plan", "".join(parts) or "<p>No phases defined.</p>")


def _render_impact(plan: dict) -> str:
    imp = _safe_get(plan, "impact", default={})
    if not isinstance(imp, dict):
        imp = {}
    rows = (
        f"<tr><td>Current</td><td>{_esc(str(imp.get('current_score', '—')))}</td></tr>"
        f"<tr><td>30-day</td><td>{_esc(str(imp.get('projected_30_day', '—')))}</td></tr>"
        f"<tr><td>90-day</td><td>{_esc(str(imp.get('projected_90_day', '—')))}</td></tr>"
    )
    table = f"<table><tr><th>Timeline</th><th>Score</th></tr>{rows}</table>"
    return _section("Your Impact", table)


def _render_legal_rights(plan: dict) -> str:
    lr = _safe_get(plan, "legal_rights", default=None)
    if not lr or not isinstance(lr, dict) or not lr.get("rights"):
        return _section("Your Legal Rights", "<p>No denial context provided.</p>")
    items = "".join(f"<li>{_esc(str(r))}</li>" for r in lr["rights"])
    return _section("Your Legal Rights", f"<ul>{items}</ul>")


def _render_local_resources(plan: dict) -> str:
    ac = _safe_get(plan, "attack_cycles", default={})
    cycles = ac.get("cycles", []) if isinstance(ac, dict) else []
    items = "".join(
        f'<div class="action-item">'
        f"Month {_esc(str(c.get('month', '?')))}: {_esc(str(c.get('focus', '')))}</div>"
        for c in cycles
    )
    return _section(
        "Local Resources", items or "<p>See your local HUD-approved counselor.</p>"
    )


def _render_bureau_intel(plan: dict) -> str:
    bi = _safe_get(plan, "bureau_intelligence", default=None)
    if not bi or not isinstance(bi, dict) or not bi.get("discrepancies"):
        return _section("Bureau Intelligence", "<p>No cross-bureau data provided.</p>")
    items = "".join(f"<li>{_esc(str(d))}</li>" for d in bi["discrepancies"])
    return _section("Bureau Intelligence", f"<ul>{items}</ul>")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_liberation_plan(plan: dict) -> str:
    """Render a liberation plan dict as a printable HTML string."""
    lp = plan.get("liberation_plan")
    if not lp or not isinstance(lp, dict):
        return _html_wrap(
            "<h1>Liberation Plan</h1>"
            '<p class="metric" style="color:red;">Error: no liberation plan data.</p>'
        )

    sections = [
        "<h1>Liberation Plan</h1>",
        _render_situation(lp),
        _render_monday_morning(lp),
        _render_battle_plan(lp),
        _render_impact(lp),
        _render_legal_rights(lp),
        _render_local_resources(lp),
        _render_bureau_intel(lp),
    ]

    # Footer
    community = _esc(str(plan.get("community_impact", "")))
    why = _esc(str(plan.get("why_deterministic", "")))
    footer = (
        '<div class="section">'
        f"<p><strong>Community impact:</strong> {community}</p>"
        f"<p><em>{why}</em></p>"
        f"<p>Generated by Baby INERTIA — Montgomery, AL | {date.today()}</p>"
        "</div>"
    )
    sections.append(footer)

    return _html_wrap("\n".join(sections))
