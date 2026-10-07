"""Build the browser-only edition of the dashboard for GitHub Pages."""

import html
import json
import re
import shutil
from pathlib import Path

import pandas as pd
import plotly.io as pio
from plotly.offline import get_plotlyjs

import dashboard_colombia as dashboard


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "site"
UNIT_LESS = {"flex", "flexGrow", "flexShrink", "fontWeight", "lineHeight", "opacity", "order", "zIndex"}


def css_style(values):
    parts = []
    for key, value in (values or {}).items():
        name = key if key.startswith("--") else re.sub(r"[A-Z]", lambda m: "-" + m[0].lower(), key)
        if isinstance(value, (int, float)) and value != 0 and key not in UNIT_LESS:
            value = f"{value}px"
        parts.append(f"{name}:{value}")
    return ";".join(parts)


def attrs(props, allowed=None):
    names = {
        "className": "class", "tabIndex": "tabindex", "htmlFor": "for",
        "autoFocus": "autofocus", "srcSet": "srcset",
    }
    result = []
    for key, value in props.items():
        if allowed is not None and key not in allowed:
            continue
        if key in {"children", "options", "value", "inline", "inputStyle", "labelStyle"}:
            continue
        if key == "style":
            value = css_style(value)
        elif key == "src" and isinstance(value, str) and value.startswith("/assets/"):
            value = value.lstrip("/")
        if value is None or value is False:
            continue
        name = names.get(key, key)
        if value is True:
            result.append(name)
        elif isinstance(value, (str, int, float)):
            result.append(f'{name}="{html.escape(str(value), quote=True)}"')
    return (" " + " ".join(result)) if result else ""


def render_choices(kind, props):
    container = attrs(props, {"id", "className", "style", "title"})
    selected = props.get("value") or []
    if kind == "RadioItems":
        selected = [selected]
    input_type = "radio" if kind == "RadioItems" else "checkbox"
    pieces = []
    for option in props.get("options", []):
        value = str(option["value"])
        label_style = css_style(props.get("labelStyle"))
        input_style = css_style(props.get("inputStyle"))
        label_attrs = f' style="{html.escape(label_style, quote=True)}"' if label_style else ""
        input_attrs = f' style="{html.escape(input_style, quote=True)}"' if input_style else ""
        checked = " checked" if value in selected else ""
        pieces.append(
            f'<label{label_attrs}><input type="{input_type}" name="{html.escape(props["id"])}" '
            f'value="{html.escape(value, quote=True)}"{checked}{input_attrs}>'
            f'{render(option["label"])}</label>'
        )
    return f'<div{container}>{"".join(pieces)}</div>'


def render(component):
    if component is None or component is False:
        return ""
    if isinstance(component, (list, tuple)):
        return "".join(render(child) for child in component)
    if isinstance(component, (str, int, float)):
        return html.escape(str(component))
    if not hasattr(component, "to_plotly_json"):
        raise TypeError(f"Unsupported layout item: {type(component)}")

    item = component.to_plotly_json()
    kind = item["type"]
    props = item["props"]
    if kind == "Store":
        return ""
    if kind == "Graph":
        graph_props = {"id": props["id"], "style": props.get("style"),
                       "className": "static-graph " + props.get("className", "")}
        return f'<div{attrs(graph_props)}></div>'
    if kind in {"Checklist", "RadioItems"}:
        return render_choices(kind, props)

    tag = kind.lower()
    html_props = {key: value for key, value in props.items()
                  if key not in {"n_clicks", "disable_n_clicks"}}
    if tag in {"img", "hr", "br", "input"}:
        return f"<{tag}{attrs(html_props)}>"
    return f"<{tag}{attrs(html_props)}>{render(props.get('children'))}</{tag}>"


def records(frame, columns):
    return json.loads(frame[columns].to_json(orient="records", date_format="iso"))


def figure(fig):
    return json.loads(pio.to_json(fig, validate=True, pretty=False))


def build_payload():
    tes = dashboard.df_tes.copy()
    inflation = dashboard.df_inf.copy()
    inflation["reference_end"] = inflation["fecha"] + pd.offsets.MonthEnd(0)
    gdp = dashboard.df_pib.copy()
    gdp["reference_end"] = gdp["fecha"] + pd.offsets.QuarterEnd(0)
    last_tes = tes.dropna(subset=["tes_pesos_1y", "tes_pesos_5y", "tes_pesos_10y"]).iloc[-1]
    return {
        "figures": {
            "chart-bolsa": figure(dashboard.make_fig_bolsa(dashboard.df_colcap)),
            "chart-inflacion": figure(dashboard.make_fig_inflacion(dashboard.df_daily)),
            "chart-tes": figure(dashboard.make_fig_tes(tes, ["1A", "5A", "10A"])),
            "curve-chart": figure(dashboard.make_curve_fig(last_tes, ["1A", "5A", "10A"])),
            "cycle-6A": figure(dashboard.make_cycle_fig("6A")),
            "cycle-ALL": figure(dashboard.make_cycle_fig("ALL")),
        },
        "tables": {
            "tes": records(tes, ["fecha", "tes_pesos_1y", "tes_pesos_5y", "tes_pesos_10y"]),
            "colcap": records(dashboard.df_colcap, ["fecha", "colcap_puntos"]),
            "inflation": records(inflation, ["fecha", "reference_end", "inflacion_mensual", "inflacion_anual"]),
            "gdp": records(gdp, ["fecha", "reference_end", "pib_real_yoy", "trimestre", "fecha_publicacion_vintage"]),
        },
        "help": dashboard.LABEL_HELP,
    }


def build():
    OUTPUT.mkdir(exist_ok=True)
    assets = OUTPUT / "assets"
    assets.mkdir(exist_ok=True)
    for name in ("responsive.css", "responsive_layout.css", "Logo Schema.png", "logo universisas.png"):
        shutil.copy2(ROOT / "assets" / name, assets / name)
    (assets / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
    shutil.copy2(ROOT / "pages" / "dashboard.js", OUTPUT / "dashboard.js")
    shutil.copy2(ROOT / "pages" / "dashboard.css", OUTPUT / "dashboard.css")
    (OUTPUT / "dashboard.json").write_text(
        json.dumps(build_payload(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    markup = render(dashboard.app.layout)
    document = f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="ColombiaMacro: mercado accionario, inflación, PIB, TES y ciclo económico colombiano.">
<title>ColombiaMacro</title>
<link rel="stylesheet" href="assets/responsive.css">
<link rel="stylesheet" href="assets/responsive_layout.css">
<link rel="stylesheet" href="dashboard.css">
<script defer src="assets/plotly.min.js"></script>
<script defer src="dashboard.js"></script>
</head><body>{markup}</body></html>
"""
    (OUTPUT / "index.html").write_text(document, encoding="utf-8")
    (OUTPUT / ".nojekyll").touch()
    print(f"GitHub Pages build: {OUTPUT} ({len(document):,} HTML characters)")


if __name__ == "__main__":
    build()
