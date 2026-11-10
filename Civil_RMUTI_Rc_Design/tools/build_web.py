"""Build the single-file web version (``web/dist/civil_rmuti_rc_design.html``).

The web page shares its definitions with the desktop program: every input
field, limit, unit label, built-in material and constant is exported from
the Python code into a JSON *spec* embedded in the page. Only the small
geometry engines, validation messages and report layout are re-implemented
in ``web/src/core.js``; ``tests/test_web_parity.py`` checks that they give
the same results as Python.

Usage::

    python tools/build_web.py
"""

from __future__ import annotations

import base64
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.constants import (  # noqa: E402
    APP_NAME,
    APP_PHASE,
    APP_VERSION,
    FILE_FORMAT_ID,
    FILE_FORMAT_VERSION,
    KSC_TO_MPA,
    PROJECT_FILE_EXTENSION,
    DesignStandard,
    DesignType,
    Quantity,
    UnitSystem,
    unit_label,
)
from app.core.project_model import DesignSettings  # noqa: E402
from app.design.registry import DESIGN_REGISTRY  # noqa: E402
from app.materials.concrete import DEFAULT_CONCRETE_GRADES  # noqa: E402
from app.materials.reinforcement import DEFAULT_REBAR_GRADES, DEFAULT_REBAR_SIZES  # noqa: E402

SRC = ROOT / "web" / "src"
DIST = ROOT / "web" / "dist" / "civil_rmuti_rc_design.html"
SPEC_PLACEHOLDER = "/*__RC_SPEC__*/null"
LOGO_PLACEHOLDER = "__LOGO_DATA_URI__"
LOGO_FILE = SRC / "logo.png"


def build_spec() -> dict[str, Any]:
    """Return the JSON-serializable spec shared with the web page."""
    design_types = []
    for design_type in DesignType:
        cls = DESIGN_REGISTRY[design_type]
        fields = []
        for spec in cls.FIELD_SPECS:
            data = asdict(spec)
            data["quantity"] = spec.quantity.value
            data["choices"] = list(spec.choices)
            data["visible_when"] = (
                [spec.visible_when[0], list(spec.visible_when[1])] if spec.visible_when else None
            )
            fields.append(data)
        design_types.append({
            "value": design_type.value,
            "title": design_type.title,
            "description": design_type.description,
            "description_th": design_type.description_th,
            "project_key": design_type.project_key,
            "prefix": design_type.name_prefix,
            "fields": fields,
        })
    return {
        "app": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "phase": APP_PHASE,
            "file_format": FILE_FORMAT_ID,
            "format_version": FILE_FORMAT_VERSION,
            "extension": PROJECT_FILE_EXTENSION,
            "ksc_to_mpa": KSC_TO_MPA,
        },
        "standards": [{"value": s.value, "label": s.label} for s in DesignStandard],
        "units": [{"value": u.value, "label": u.label} for u in UnitSystem],
        "unit_labels": {u.value: {q.value: unit_label(q, u) for q in Quantity} for u in UnitSystem},
        "design_types": design_types,
        "materials": {
            "concrete": [c.to_dict() for c in DEFAULT_CONCRETE_GRADES],
            "rebar_grades": [g.to_dict() for g in DEFAULT_REBAR_GRADES],
            "rebar_sizes": [s.to_dict() for s in DEFAULT_REBAR_SIZES],
        },
        "default_settings": DesignSettings().to_dict(),
    }


STANDALONE = ROOT / "web" / "dist" / "civil_rmuti_rc_design_standalone.html"

_LOGO_MARK = '<img class="logo" src="__LOGO_DATA_URI__" alt="RMUTI emblem" width="40" height="40">'
_TEXT_MARK = '<div class="mark" aria-hidden="true">RC</div>'

#: Head used for the standalone file (the Claude artifact host adds its own).
_STANDALONE_HEAD = """<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#1F4E79">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="RC Design">
<meta name="format-detection" content="telephone=no">
__TOUCH_ICON__
<style>:root{color-scheme:light}body{margin:0}[hidden]{display:none!important}
:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>
</head>
<body>
"""


def _logo_data_uri() -> str:
    return "data:image/png;base64," + base64.b64encode(LOGO_FILE.read_bytes()).decode("ascii")


def render(with_logo: bool = True) -> str:
    """Return the page body (artifact format: no doctype/head of its own)."""
    spec_json = json.dumps(build_spec(), ensure_ascii=False, separators=(",", ":"))
    html = (SRC / "index.html").read_text(encoding="utf-8")
    parts = {
        "/*__STYLES__*/": (SRC / "styles.css").read_text(encoding="utf-8"),
        "/*__CORE_JS__*/": (SRC / "core.js").read_text(encoding="utf-8"),
        "/*__UI_JS__*/": (SRC / "ui.js").read_text(encoding="utf-8"),
        "<!--__BRAND_MARK__-->": _LOGO_MARK if with_logo else _TEXT_MARK,
    }
    for placeholder, content in parts.items():
        if placeholder not in html:
            raise RuntimeError(f"Placeholder {placeholder} missing in index.html")
        html = html.replace(placeholder, content)
    if SPEC_PLACEHOLDER not in html:
        raise RuntimeError("Spec placeholder missing in core.js")
    html = html.replace(SPEC_PLACEHOLDER, spec_json.replace("</", "<\\/"))
    return html.replace(LOGO_PLACEHOLDER, _logo_data_uri() if with_logo else "")


def build(output: Path = DIST, with_logo: bool = True) -> Path:
    """Write the artifact page (body only) and return its path."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(with_logo), encoding="utf-8")
    return output


def build_standalone(output: Path = STANDALONE, with_logo: bool = True) -> Path:
    """Write a complete HTML document for any browser / web server / iPad home screen."""
    icon = (f'<link rel="apple-touch-icon" href="{_logo_data_uri()}">\n'
            f'<link rel="icon" type="image/png" href="{_logo_data_uri()}">') if with_logo else ""
    head = _STANDALONE_HEAD.replace("__TOUCH_ICON__", icon)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(head + render(with_logo) + "\n</body>\n</html>\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    no_logo = "--no-logo" in sys.argv
    print(f"Artifact page:   {build(with_logo=not no_logo)}")
    print(f"Standalone page: {build_standalone(with_logo=not no_logo)}")
