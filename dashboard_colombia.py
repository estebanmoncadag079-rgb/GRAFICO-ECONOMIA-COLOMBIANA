"""
╔══════════════════════════════════════════════════════════════════╗
║   DASHBOARD FINANCIERO COLOMBIA — v8.0                          ║
║   Panel ① COLCAP oficial y canastas historicas                 ║
║   Panel ② Inflación + PIB (toggle)                              ║
║   Panel ③ TES Pesos 1A · 5A · 10A                               ║
╠══════════════════════════════════════════════════════════════════╣
║  Archivos requeridos (misma carpeta):                           ║
║    • colcap_oficial.csv                                         ║
║    • indices_colombia.csv                                      ║
║    • tasas_interes_clean.csv                                     ║
║    • inflacion_clean.csv                                        ║
║    • pib_colombia.csv                                           ║
║                                                                  ║
║  pip install dash plotly pandas                                 ║
║  python dashboard_colombia.py  →  http://127.0.0.1:8050        ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os, threading, time, webbrowser
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ClientsideFunction, dcc, html, ctx, no_update
from plotly.subplots import make_subplots
from validar_datos import isolated_tes_spikes

# ══════════════════════════════════════════════════════════
# 0. RUTAS
# ══════════════════════════════════════════════════════════
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CSV_COLCAP  = os.path.join(BASE_DIR, "colcap_oficial.csv")
CSV_INDICES = os.path.join(BASE_DIR, "indices_colombia.csv")
CSV_TES     = os.path.join(BASE_DIR, "tasas_interes_clean.csv")
CSV_INF     = os.path.join(BASE_DIR, "inflacion_clean.csv")
CSV_PIB     = os.path.join(BASE_DIR, "pib_colombia.csv")
CSV_ESTADO  = os.path.join(BASE_DIR, "estado_fuentes.csv")
CSV_EXP     = os.path.join(BASE_DIR, "indices_experimentales_mensuales.csv")
COLCAP_MSCI_TRANSITION = pd.Timestamp("2021-05-28")

# ══════════════════════════════════════════════════════════
# 1. CARGA Y PREPARACIÓN
# ══════════════════════════════════════════════════════════
df_colcap  = pd.read_csv(CSV_COLCAP,  parse_dates=["fecha"])
df_indices = pd.read_csv(CSV_INDICES, parse_dates=["fecha"])
df_tes     = pd.read_csv(CSV_TES,     parse_dates=["fecha"])
df_inf     = pd.read_csv(CSV_INF,     parse_dates=["fecha"])

df_pib  = pd.read_csv(CSV_PIB, parse_dates=["fecha"])
df_estado = pd.read_csv(CSV_ESTADO)
df_exp = pd.read_csv(CSV_EXP, parse_dates=["fecha"])
last_reviewable_month = df_exp.loc[df_exp["estado"] == "revisable", "fecha"].max()
last_reviewable_label = (last_reviewable_month.strftime("%Y-%m")
                         if pd.notna(last_reviewable_month) else "sin mes revisable")

# Merge diario principal
for _df in [df_colcap, df_tes]:
    _df["date"] = _df["fecha"].dt.normalize()

df_daily = (pd.DataFrame({"date": pd.concat(
        [df_colcap["date"], df_tes["date"]]
    ).drop_duplicates().sort_values().reset_index(drop=True)})
    .merge(df_colcap[["date","colcap_puntos","colcap_base100"]], on="date", how="left")
    .merge(df_tes[["date","tes_pesos_1y","tes_pesos_5y","tes_pesos_10y"]], on="date", how="left")
    )
df_daily["fecha"] = df_daily["date"]
df_daily = df_daily[df_daily["fecha"] <= pd.Timestamp.today().normalize()].reset_index(drop=True)

# El PIB es trimestral y se conserva en su tabla original.
df_pib = df_pib.dropna(subset=["pib_real_yoy"]).copy()

FECHA_INI = df_daily["fecha"].min()
FECHA_FIN = df_daily["fecha"].max()

print(f"Dataset: {len(df_daily):,} filas | {FECHA_INI.date()} -> {FECHA_FIN.date()}")

# ══════════════════════════════════════════════════════════
# 2. PALETA
# ══════════════════════════════════════════════════════════
BG_APP    = "#ffffff"
BG_PANEL  = "#f8fafc"
BG_CARD   = "#f1f5f9"
BG_MODAL  = "#ffffff"
BORDER    = "#e2e8f0"
TEXT      = "#0f172a"
MUTED     = "#64748b"

C_BOLSA    = "#3fb950"   # COLCAP oficial
C_SINTET   = "#38bdf8"   # Sintético igualitario
C_GRANDES  = "#fbbf24"   # 7 Grandes
C_INF_M    = "#fb923c"
C_INF_A    = "#f43f5e"
C_INF_BAJA = "#4ade80"
C_PIB      = "#14b8a6"   # PIB crecimiento
C_TES1     = "#ffa657"
C_TES5     = "#38bdf8"
C_TES10    = "#bc8cff"
C_AZUL     = "#58a6ff"
C_VERDE    = "#3fb950"
C_ROJO     = "#ff7b72"
C_AMARILLO = "#e3b341"

# Colores por empresa (7 grandes)
COLORES_GRANDES = {
    "ECOPETROL": "#f97316", "PFBCOLOM":  "#3b82f6", "GRUPOSURA": "#8b5cf6",
    "GRUPOARGOS":"#10b981", "PFAVAL":    "#f59e0b", "ISA":       "#06b6d4",
    "NUTRESA":   "#ec4899",
}

TENOR_COLORS = {"tes_pesos_1y": C_TES1, "tes_pesos_5y": C_TES5, "tes_pesos_10y": C_TES10}
GRID_CLR  = "rgba(100,116,139,0.18)"
SPIKE_CFG = dict(
    showspikes=True, spikecolor="#64748b", spikethickness=1,
    spikedash="solid", spikemode="across", spikesnap="cursor",
)

# ══════════════════════════════════════════════════════════
# 3. HELPERS
# ══════════════════════════════════════════════════════════
MESES_ES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
            7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

def fecha_es(ts):
    ts = pd.to_datetime(ts)
    return f"{ts.day:02d} {MESES_ES[ts.month]} {ts.year}"

def mes_es(ts):
    ts = pd.to_datetime(ts)
    return f"{MESES_ES[ts.month]} {ts.year}"

def periodo_fuente(item):
    ts = pd.to_datetime(item["ultima_observacion"])
    if item["frecuencia"] == "trimestral":
        return f"T{ts.quarter} {ts.year}"
    if item["frecuencia"] == "mensual":
        return mes_es(ts)
    return fecha_es(ts)

OFFSETS = {
    "3M": pd.DateOffset(months=3), "6M": pd.DateOffset(months=6),
    "1A": pd.DateOffset(years=1),  "3A": pd.DateOffset(years=3),
    "5A": pd.DateOffset(years=5),
}

def filter_window(dff, window):
    if window in OFFSETS:
        return dff[dff["fecha"] >= dff["fecha"].max() - OFFSETS[window]].copy()
    return dff.copy()

def filter_window_pib(window):
    dff = df_pib.copy()
    if window in OFFSETS:
        return dff[dff["fecha"] >= dff["fecha"].max() - OFFSETS[window]]
    return dff

def latest_on_or_before(table, fecha, required, period_end=None):
    dates = table["fecha"] if period_end is None else table["fecha"] + period_end
    dff = table[dates <= pd.to_datetime(fecha)].dropna(subset=required)
    return None if dff.empty else dff.iloc[-1]

def nearest_row(dff, x_val):
    if dff.empty or not x_val:
        return None
    try:
        idx = (dff["fecha"] - pd.to_datetime(x_val)).abs().idxmin()
        return dff.loc[idx]
    except Exception:
        return None

def get_hover_row(hover_data, dff):
    if not hover_data or not hover_data.get("points"):
        return dff.iloc[-1]
    for pt in hover_data["points"]:
        if pt.get("x"):
            try:
                return pd.Series({"fecha": pd.Timestamp(pt["x"])})
            except (ValueError, TypeError):
                continue
    return dff.iloc[-1]

def latest_inflation_row(fecha):
    return latest_on_or_before(df_inf, fecha, ["inflacion_anual"], pd.offsets.MonthEnd(0))

# ══════════════════════════════════════════════════════════
# 4. BASE LAYOUT
# ══════════════════════════════════════════════════════════
BASE_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor=BG_PANEL, plot_bgcolor=BG_PANEL,
    hovermode="closest",
    hoverdistance=30,
    dragmode="zoom",
    font=dict(family="Arial, sans-serif", size=12, color="#25343b"),
    showlegend=False,
    hoverlabel=dict(bgcolor="#ffffff", font_size=12, namelength=-1, bordercolor=BORDER),
    margin=dict(l=60, r=65, t=10, b=38),
    legend=dict(
        orientation="h", xanchor="center", x=0.5, yanchor="top", y=-0.18,
        bgcolor="rgba(15,23,42,0.0)", bordercolor="rgba(0,0,0,0)", borderwidth=0,
        font=dict(color=MUTED, size=9),
        itemwidth=30, tracegroupgap=0,
    ),
)

def xaxis_base(x_range=None):
    return dict(type="date", showgrid=False, gridcolor=GRID_CLR,
                range=x_range, title=dict(text="Fecha", standoff=12),
                showline=True, linecolor="#64748b", linewidth=1,
                ticks="outside", ticklen=6, tickcolor="#64748b",
                showticklabels=True, tickfont=dict(size=12, color="#25343b"),
                side="bottom", anchor="y", automargin=True, nticks=6,
                tickformatstops=[
                    dict(dtickrange=[None, "M1"], value="%d/%m\n%Y"),
                    dict(dtickrange=["M1", "M12"], value="%m/%Y"),
                    dict(dtickrange=["M12", None], value="%Y"),
                ],
                **{**SPIKE_CFG, "spikedash": "dot", "spikesnap": "data"})

def yaxis_base(title, suffix=""):
    return dict(title=title, showgrid=False, gridcolor=GRID_CLR, zeroline=False,
                ticksuffix=suffix, automargin=True, fixedrange=True,
                showspikes=False, tickfont=dict(size=12, color="#25343b"))


CHART_CONFIG = {
    "displaylogo": False, "scrollZoom": False, "responsive": True,
    "displayModeBar": "hover", "doubleClick": "reset",
    "modeBarButtons": [["zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "resetScale2d", "toImage"]],
}


def analysis_figure(fig, height=420, period_axis=False):
    # Preserve events for the external readout without drawing a floating box.
    for trace in fig.data:
        if trace.hoverinfo != "skip":
            trace.update(hovertemplate=None, hoverinfo="none")
        if trace.y is not None:
            trace.y = [float(value) if pd.notna(value) else None for value in trace.y]
        if trace.x is not None:
            trace.x = [pd.Timestamp(x).isoformat() for x in trace.x]
    fig.update_layout(height=height, margin=dict(l=62, r=64, t=18, b=66),
                      showlegend=False)
    if period_axis:
        fig.update_xaxes(title_text="Período de referencia")
    return fig

# ══════════════════════════════════════════════════════════
# 5A. COLCAP OFICIAL Y SERIES HEREDADAS BAJO REVISION
# ══════════════════════════════════════════════════════════
def make_fig_bolsa(dff, x_range=None, layers=None):
    if layers is None:
        layers = ["oficial", "equiponderado", "grandes"]
    fig = go.Figure()

    if "oficial" in layers:
        fig.add_trace(go.Scatter(
            x=dff["fecha"], y=dff["colcap_base100"],
            name="COLCAP oficial",
            mode="lines", line=dict(color=C_BOLSA, width=2.5),
            meta=dict(label="COLCAP oficial", unit="base 100", frequency="daily"),
            hovertemplate="COLCAP oficial %{x|%d %b %Y}: %{y:.2f} (base 100)<extra></extra>",
        ))

    legacy = df_indices[df_indices["fecha"].between(dff["fecha"].min(), dff["fecha"].max())]
    legacy_series = [
        ("equiponderado", "sintetico_base100", "Índice equiponderado · legado", C_SINTET),
        ("grandes", "grandes_base100", "7 Magníficas · legado", C_GRANDES),
    ]
    for key, column, label, color in legacy_series:
        if key in layers:
            fig.add_trace(go.Scatter(
                x=legacy["fecha"], y=legacy[column], name=label,
                mode="lines", line=dict(color=color, width=1.8, dash="dash"),
                meta=dict(label=label.replace(" · legado", ""), unit="base 100", frequency="daily"),
                hovertemplate=f"{label} %{{x|%d %b %Y}}: %{{y:.2f}} (base 100)<extra></extra>",
            ))

    fig.add_hline(y=100, line_dash="dot", line_color="#64748b", line_width=1)

    visible_start, visible_end = dff["fecha"].min(), dff["fecha"].max()
    if x_range:
        visible_start = max(visible_start, pd.Timestamp(x_range[0]))
        visible_end = min(visible_end, pd.Timestamp(x_range[1]))
    if "oficial" in layers and visible_start <= COLCAP_MSCI_TRANSITION <= visible_end:
        span = visible_end - visible_start
        position = ((COLCAP_MSCI_TRANSITION - visible_start) / span
                    if span > pd.Timedelta(0) else 0.5)
        anchor = "left" if position < 0.3 else "right" if position > 0.7 else "center"
        fig.add_shape(
            type="line", xref="x", yref="paper",
            x0=COLCAP_MSCI_TRANSITION, x1=COLCAP_MSCI_TRANSITION,
            y0=0, y1=1,
            line=dict(color="#475569", width=1.5, dash="dot"),
        )
        fig.add_annotation(
            x=COLCAP_MSCI_TRANSITION, xref="x", y=0.98, yref="paper",
            text="BVC → MSCI<br>28 may 2021", showarrow=False,
            xanchor=anchor, yanchor="top", align="center",
            bgcolor="rgba(255,255,255,0.94)", bordercolor="#94a3b8",
            borderwidth=1, borderpad=4,
            font=dict(size=10, color="#334155"),
        )

    fig.update_layout(
        **{**BASE_LAYOUT, "margin": dict(l=60, r=65, t=10, b=90)}, height=420,
        xaxis=xaxis_base(x_range),
        yaxis=yaxis_base("Índice (base 100)"),
    )
    return analysis_figure(fig)

# ══════════════════════════════════════════════════════════
# 5D. PANEL INFLACIÓN + PIB
# ══════════════════════════════════════════════════════════
def _color_inf_mensual(v):
    if pd.isna(v):  return "#475569"
    if v >= 1.0:    return "#ef4444"   # rojo  — inflación muy alta
    if v >= 0.6:    return "#f97316"   # naranja
    if v >= 0.3:    return "#eab308"   # amarillo
    return "#4ade80"                   # verde  — inflación baja / controlada

def make_fig_inflacion(dff, x_range=None, show_layers=None):
    if show_layers is None:
        show_layers = ["inf_mensual", "inf_anual", "pib"]
    layer_order = [layer for layer in ["inf_anual", "inf_mensual", "pib"] if layer in show_layers]
    fig = go.Figure()
    first, last = dff["fecha"].min(), dff["fecha"].max()
    # Align a quarter with its final month, rather than its first month.
    ipc = df_inf.assign(plot_date=df_inf["fecha"] + pd.offsets.MonthEnd(0))
    pib = df_pib.assign(plot_date=df_pib["fecha"] + pd.offsets.QuarterEnd(0))
    ipc = ipc[ipc["plot_date"].between(first, last)]
    pib = pib[pib["plot_date"].between(first, last)]

    if "inf_mensual" in layer_order:
        fig.add_trace(go.Bar(
            x=ipc["plot_date"], y=ipc["inflacion_mensual"], yaxis="y2",
            meta=dict(label="IPC mensual", unit="%", frequency="monthly", axis="derecha"),
            name="IPC mensual · derecha", marker_color=C_INF_M, opacity=0.55,
            hovertemplate="IPC mensual %{x|%b %Y}: <b>%{y:.2f}%</b><extra></extra>",
        ))
    if "inf_anual" in layer_order:
        fig.add_trace(go.Scatter(
            x=ipc["plot_date"], y=ipc["inflacion_anual"], name="IPC anual · izquierda",
            meta=dict(label="IPC anual", unit="%", frequency="monthly", axis="izquierda"),
            mode="lines", line=dict(color=C_INF_A, width=2.5),
            marker=dict(size=4), connectgaps=False,
            hovertemplate="IPC anual %{x|%b %Y}: <b>%{y:.2f}%</b><extra></extra>",
        ))
    if "pib" in layer_order:
        fig.add_trace(go.Scatter(
            x=pib["plot_date"], y=pib["pib_real_yoy"],
            meta=dict(label="PIB real interanual", unit="%", frequency="quarterly", axis="izquierda"),
            name="PIB interanual · izquierda", mode="lines+markers",
            line=dict(color=C_PIB, width=2.5, dash="dot"),
            marker=dict(color=C_PIB, size=6), connectgaps=False,
            customdata=pib["trimestre"],
            hovertemplate="PIB real %{customdata}: %{y:.2f}%<extra></extra>",
        ))

    # A fixed 10:1 ratio preserves a shared zero without changing source values.
    values = [0.0]
    for trace in fig.data:
        dates = pd.to_datetime(trace.x)
        series = pd.Series(trace.y, index=dates, dtype=float)
        if x_range:
            series = series.loc[series.index.to_series().between(
                pd.to_datetime(x_range[0]), pd.to_datetime(x_range[1])).values]
        factor = 10 if trace.yaxis == "y2" else 1
        values.extend((series.dropna() * factor).tolist())
    low, high = min(values), max(values)
    pad = max((high - low) * 0.08, 0.5)
    axis_range = [low - pad, high + pad]

    fig.update_layout(**{
        **BASE_LAYOUT,
        "height": 460,
        "margin": dict(l=65, r=65, t=12, b=105),
        "xaxis": xaxis_base(x_range),
        "yaxis": dict(title=dict(text="Anual / PIB (%)", standoff=8),
                      range=axis_range, ticksuffix="%", automargin=True,
                      fixedrange=True, showspikes=False,
                      showgrid=False, gridcolor=GRID_CLR, zeroline=True, zerolinecolor=MUTED,
                      visible=any(k in layer_order for k in ["inf_anual", "pib"])),
        "yaxis2": dict(title=dict(text="Mensual (%)", font=dict(color="#b45309"), standoff=8),
                       overlaying="y", side="right", range=[v / 10 for v in axis_range],
                       ticksuffix="%", tickformat=".2f", tickfont=dict(color="#b45309"),
                       automargin=True, showgrid=False, zeroline=False,
                       fixedrange=True, showspikes=False,
                       visible="inf_mensual" in layer_order),
    })
    fig.update_layout(legend=dict(orientation="h", x=0, xanchor="left", y=-0.2))
    return analysis_figure(fig, height=450, period_axis=True)

# ══════════════════════════════════════════════════════════
# 5E. PANEL TES PESOS
# ══════════════════════════════════════════════════════════
_TES_FILL = {
    "tes_pesos_1y":  "rgba(255,166,87,0.09)",
    "tes_pesos_5y":  "rgba(56,189,248,0.09)",
    "tes_pesos_10y": "rgba(188,140,255,0.09)",
}

def make_fig_tes(dff, active_tenors, x_range=None):
    fig = go.Figure()
    for key, col, color, label in [
        ("1A",  "tes_pesos_1y",  C_TES1,  "TES 1 año  (corto plazo)"),
        ("5A",  "tes_pesos_5y",  C_TES5,  "TES 5 años (medio plazo)"),
        ("10A", "tes_pesos_10y", C_TES10, "TES 10 años (largo plazo)"),
    ]:
        vis = True if key in active_tenors else "legendonly"
        grp = f"tes_{key}"
        values = dff[col].mask(isolated_tes_spikes(dff[col]))
        # Área rellena (vinculada al grupo de leyenda)
        fig.add_trace(go.Scatter(
            x=dff["fecha"], y=values,
            mode="lines", line=dict(color=color, width=0),
            fill="tozeroy", fillcolor=_TES_FILL[col],
            legendgroup=grp, showlegend=False, hoverinfo="skip",
            visible=vis,
        ))
        # Línea principal
        fig.add_trace(go.Scatter(
            x=dff["fecha"], y=values,
            name=label, visible=vis, mode="lines",
            line=dict(color=color, width=2.5),
            legendgroup=grp,
            meta=dict(label=f"TES {key}", unit="%", frequency="daily"),
            hovertemplate=f"<b>{label}:</b> %{{y:.2f}}%<extra></extra>",
        ))
    fig.update_layout(
        **BASE_LAYOUT, height=310,
        xaxis=xaxis_base(x_range),
        yaxis=yaxis_base("Tasa anual (%)", "%"),
    )
    return analysis_figure(fig, height=350)

# ══════════════════════════════════════════════════════════
# 6. CURVA TES (panel derecho)
# ══════════════════════════════════════════════════════════
def make_curve_fig(row, active_tenors):
    col_map  = {"1A":"tes_pesos_1y","5A":"tes_pesos_5y","10A":"tes_pesos_10y"}
    x_labels = {"1A":"1 Año\n(corto)","5A":"5 Años\n(medio)","10A":"10 Años\n(largo)"}
    tenors   = [k for k in ["1A","5A","10A"] if k in active_tenors]
    if not tenors:
        return go.Figure()
    x_vals = [x_labels[t] for t in tenors]
    y_vals = [float(row[col_map[t]]) for t in tenors]
    c_vals = [TENOR_COLORS[col_map[t]] for t in tenors]
    pad    = max((max(y_vals)-min(y_vals))*0.55, 0.6)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_vals, y=y_vals, fill="tozeroy",
        fillcolor="rgba(88,166,255,0.06)", line=dict(width=0),
        showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals, mode="lines+markers+text",
        text=[f"<b>{v:.2f}%</b>" for v in y_vals],
        textposition="top center", cliponaxis=False,
        textfont=dict(color=TEXT, size=13),
        line=dict(color=C_AZUL, width=2.5),
        marker=dict(size=13, color=c_vals, line=dict(width=2, color="#fff")),
        hovertemplate="<b>%{x}:</b> %{y:.2f}%<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        template="plotly_white", paper_bgcolor=BG_PANEL, plot_bgcolor=BG_PANEL,
        height=260, margin=dict(l=50, r=15, t=15, b=45),
        hoverlabel=dict(bgcolor="#ffffff", font_size=12),
        xaxis=dict(title="Plazo del bono", showgrid=False, color=TEXT, tickfont=dict(size=11)),
        yaxis=dict(title="Tasa (%)", range=[min(y_vals)-pad, max(y_vals)+pad],
                   showgrid=False, gridcolor=GRID_CLR, zeroline=False,
                   color=TEXT, ticksuffix="%"),
    )
    return fig

# ══════════════════════════════════════════════════════════
# 7. TARJETA MÉTRICA
# ══════════════════════════════════════════════════════════
LABEL_HELP = {
    "COLCAP oficial": "Índice accionario publicado por BanRep. Hasta el 27 de mayo de 2021 seguía la metodología BVC; desde el 28 de mayo, la de MSCI. La transición conservó los niveles históricos, no la misma composición ni los mismos pesos. Aquí se expresa en base 100 al 9 de febrero de 2009.",
    "Índice equiponderado": "Promedio de los retornos mensuales de las acciones disponibles de la canasta historica. Cada accion valida pesa igual; las que no tienen datos se excluyen ese mes. La composicion varia. La curva diaria es una reconstruccion, no precios diarios observados.",
    "7 Magníficas": "Canasta de este proyecto: Ecopetrol (ECOPETROL), Bancolombia preferencial (PFBCOLOM), Grupo Sura (GRUPOSURA), Grupo Argos (GRUPOARGOS), Grupo Aval preferencial (PFAVAL), ISA (ISA) y Nutresa (NUTRESA). Son nombres y tickers historicos. Igual peso entre las acciones elegibles con datos: algunos meses participan menos de siete. No es un indice oficial.",
    "Inflación mensual": "Variacion del indice de precios al consumidor (IPC) frente al mes anterior. Barras naranjas; se lee en el eje derecho. Por ejemplo, 0,5% significa que la canasta de consumo subio 0,5% en ese mes.",
    "Inflación anual": "Variación del IPC frente al mismo mes del año anterior: abarca 12 meses. Línea rosada; se lee en el eje izquierdo. No es la inflación mensual multiplicada por doce.",
    "PIB real": "Cambio de la producción de la economía, descontando el efecto de los precios, frente al mismo trimestre del año anterior. Línea verde punteada y eje izquierdo. Cada punto es trimestral; los segmentos solo conectan observaciones.",
    "1A": "TES a 1 año: tasa anual de la curva cero cupón de deuda del Gobierno colombiano en pesos. Representa el plazo corto; no es el precio de un bono ni una rentabilidad garantizada.",
    "5A": "TES a 5 años: tasa anual de la curva cero cupón de deuda del Gobierno colombiano en pesos. Representa el plazo medio.",
    "10A": "TES a 10 años: tasa anual de la curva cero cupón de deuda del Gobierno colombiano en pesos. Representa el plazo largo.",
    "Spread 10A-1A": "Diferencia entre la tasa TES a 10 años y la de 1 año, en puntos porcentuales (pp). Si es positiva, la tasa larga supera a la corta; si es negativa, ocurre lo contrario. No es una variación porcentual.",
}
for alias, source in {"TES 1A": "1A", "TES 5A": "5A", "TES 10A": "10A",
                      "Inflación anual 12M": "Inflación anual",
                      "PIB real interanual": "PIB real"}.items():
    LABEL_HELP[alias] = LABEL_HELP[source]


def chart_description(title, text):
    tone = {
        "Bolsa colombiana: mercado y canastas": "market",
        "Inflación y PIB: precios y actividad": "macro",
        "TES: tasas de la deuda pública": "rates",
    }[title]
    return html.Section([
        html.P(text),
    ], className=f"panel-explainer panel-explainer--{tone}", **{"aria-label": title})


def chart_readout(chart_id):
    return html.Div(id=f"{chart_id}-readout", className="chart-readout",
                    role="group", **{"aria-label": "Valores por serie y período"})


def help_label(label):
    return html.Span(label, className="help-label", tabIndex=0,
                     **{"data-help": LABEL_HELP[label],
                        "aria-label": f"{label}: {LABEL_HELP[label]}"})


def metric_card(title, value, color, subtitle=""):
    return html.Div([
        html.Div(help_label(title) if title in LABEL_HELP else title,
                 style={"fontSize":"10px","color":MUTED,"marginBottom":"2px"}),
        html.Div(value,    style={"fontSize":"16px","fontWeight":"700","color":color,"lineHeight":"1.1"}),
        html.Div(subtitle, style={"fontSize":"10px","color":MUTED,"marginTop":"2px"}),
    ], style={
        "background":BG_CARD,"border":f"1px solid {BORDER}",
        "borderRadius":"10px","padding":"7px 10px","minWidth":"85px","flex":"1",
    })

def story_step(number, title, body, accent):
    return html.Div([
        html.Div(str(number), style={
            "width":"30px","height":"30px","borderRadius":"8px",
            "display":"flex","alignItems":"center","justifyContent":"center",
            "background":accent,"color":"#ffffff","fontWeight":"900","fontSize":"14px",
            "flex":"0 0 auto",
        }),
        html.Div([
            html.Div(title, style={"fontSize":"13px","fontWeight":"900","color":TEXT,"marginBottom":"4px"}),
            html.Div(body, style={"fontSize":"12px","color":MUTED,"lineHeight":"1.45"}),
        ]),
    ], className="story-step", style={
        "display":"flex","gap":"10px","alignItems":"flex-start",
        "background":BG_PANEL,"border":f"1px solid {BORDER}",
        "borderRadius":"8px","padding":"12px","minWidth":"0",
    })

def story_badge(title, value, subtitle, color):
    return html.Div([
        html.Div(title, style={"fontSize":"10px","fontWeight":"800","color":MUTED,"textTransform":"uppercase"}),
        html.Div(value, style={"fontSize":"20px","fontWeight":"900","color":color,"lineHeight":"1.15","marginTop":"3px"}),
        html.Div(subtitle, style={"fontSize":"11px","color":MUTED,"lineHeight":"1.35","marginTop":"4px"}),
    ], className="story-badge", style={
        "background":BG_PANEL,"border":f"1px solid {BORDER}",
        "borderRadius":"8px","padding":"12px","minWidth":"145px","flex":"1",
    })

def latest_story_values():
    inf = df_inf.dropna(subset=["inflacion_anual"]).iloc[-1]
    pib = df_pib.dropna(subset=["pib_real_yoy"]).iloc[-1]
    tes = df_tes.dropna(subset=["tes_pesos_1y","tes_pesos_10y"]).iloc[-1]
    colcap = df_colcap.dropna(subset=["colcap_puntos"]).iloc[-1]

    inf_prev = df_inf.dropna(subset=["inflacion_anual"]).iloc[-4] if len(df_inf.dropna(subset=["inflacion_anual"])) >= 4 else inf
    pib_prev = df_pib.dropna(subset=["pib_real_yoy"]).iloc[-2] if len(df_pib.dropna(subset=["pib_real_yoy"])) >= 2 else pib
    inf_delta = float(inf["inflacion_anual"] - inf_prev["inflacion_anual"])
    pib_delta = float(pib["pib_real_yoy"] - pib_prev["pib_real_yoy"])

    if pib_delta >= 0 and inf_delta < 0:
        phase = "Recuperacion posible"
        phase_note = "PIB mejora mientras la inflacion cede: terreno favorable para revisar renta variable."
        phase_color = C_VERDE
    elif pib_delta >= 0 and inf_delta >= 0:
        phase = "Expansion con presion"
        phase_note = "Actividad e inflacion avanzan juntas: conviene vigilar si la inflacion empieza a dominar."
        phase_color = C_AMARILLO
    elif pib_delta < 0 and inf_delta >= 0:
        phase = "Auge tensionado"
        phase_note = "La actividad pierde fuerza con inflacion al alza: senal de cautela para activos de riesgo."
        phase_color = C_ROJO
    else:
        phase = "Enfriamiento"
        phase_note = "PIB e inflacion pierden traccion: la lectura se acerca a una fase defensiva."
        phase_color = C_AZUL

    spread = float(tes["tes_pesos_10y"] - tes["tes_pesos_1y"])
    return {
        "phase": phase,
        "phase_note": phase_note,
        "phase_color": phase_color,
        "inflation": f"{float(inf['inflacion_anual']):.2f}%",
        "inflation_date": mes_es(inf["fecha"]),
        "pib": f"{float(pib['pib_real_yoy']):.2f}%",
        "pib_date": str(pib["trimestre"]),
        "tes_spread": f"{spread:+.2f} pp",
        "tes_date": fecha_es(tes["fecha"]),
        "colcap": f"{float(colcap['colcap_puntos']):,.0f}",
        "colcap_date": fecha_es(colcap["fecha"]),
    }

STORY = latest_story_values()

# ══════════════════════════════════════════════════════════
# 8. LAYOUT
# ══════════════════════════════════════════════════════════
app = Dash(__name__, title="Dashboard Colombia", suppress_callback_exceptions=True)
server = app.server  # WSGI expuesto para despliegue (gunicorn)

# Todos los IDs de gráficos para el sistema de sincronización
ALL_CHARTS = ["chart-inflacion","chart-tes","chart-bolsa"]
PANEL_IDS  = {
    "chart-bolsa":      "bolsa",
    "chart-inflacion":  "inflacion",
    "chart-tes":        "tes",
}

# ── MODAL DE DETALLE ─────────────────────────────────────
modal = html.Div(id="modal", children=[
    html.Div([
        html.Div([
            html.Div("Vista de Detalle",
                     style={"fontSize":"16px","fontWeight":"700","color":TEXT}),
            html.Button("✕ Cerrar", id="close-modal", style={
                "background":"none","border":f"1px solid {BORDER}","color":TEXT,
                "cursor":"pointer","borderRadius":"6px","padding":"4px 12px","fontSize":"12px",
            }),
        ], style={"display":"flex","justifyContent":"space-between",
                  "alignItems":"center","marginBottom":"14px"}),
        html.Div([
            html.Div("¿Qué quieres ver?",
                     style={"fontSize":"11px","color":MUTED,"marginBottom":"6px"}),
            dcc.RadioItems(id="detail-var",
                options=[
                    {"label":" COLCAP y canastas", "value":"bolsa"},
                    {"label":" Inflación (mensual + anual)",    "value":"inflacion"},
                    {"label":" PIB real DANE",                  "value":"pib"},
                    {"label":" Inflación + PIB (comparación)",  "value":"inf_pib"},
                    {"label":" TES Pesos (1A · 5A · 10A)",      "value":"tes"},
                ],
                value="bolsa", inline=True,
                inputStyle={"marginRight":"5px","marginLeft":"14px"},
                labelStyle={"color":TEXT,"fontSize":"13px"},
            ),
        ], style={"marginBottom":"14px","background":BG_CARD,
                  "border":f"1px solid {BORDER}","borderRadius":"10px","padding":"12px"}),
        html.Div([
            html.Div("Período:",
                     style={"fontSize":"11px","color":MUTED,"marginBottom":"6px"}),
            html.Div([
                html.Button(lbl, id=f"detail-btn-{val}", n_clicks=0,
                    style={"background":"#1c2128","color":TEXT,"border":f"1px solid {BORDER}",
                           "borderRadius":"8px","padding":"6px 14px","fontSize":"13px",
                           "cursor":"pointer","marginRight":"6px"})
                for lbl, val in [("3 meses","3M"),("6 meses","6M"),("1 año","1A"),
                                  ("3 años","3A"),("5 años","5A"),("Todo","ALL")]
            ], style={"display":"flex","flexWrap":"wrap","gap":"4px"}),
            html.Div(id="detail-periodo-label",
                     style={"fontSize":"11px","color":C_AZUL,"marginTop":"8px","fontWeight":"600"}),
        ], style={"marginBottom":"14px","background":BG_CARD,
                  "border":f"1px solid {BORDER}","borderRadius":"10px","padding":"12px"}),
        chart_readout("detail-chart"),
        dcc.Graph(id="detail-chart", config=CHART_CONFIG),
    ], style={
        "background":BG_MODAL,"border":f"1px solid {BORDER}","borderRadius":"14px",
        "padding":"20px","maxWidth":"980px","width":"92%","margin":"30px auto",
    }),
], style={"display":"none","position":"fixed","top":"0","left":"0",
          "width":"100%","height":"100%","backgroundColor":"rgba(0,0,0,0.80)",
          "zIndex":"1000","overflowY":"auto"})

# ── MAIN LAYOUT ──────────────────────────────────────────
app.layout = html.Div([
    modal,

    # HEADER
    html.Div([
        # Logos anclados a la izquierda con posición absoluta
        html.Div([
            html.Img(src="/assets/logo universisas.png",
                     style={"height":"58px","objectFit":"contain"}),
            html.Img(src="/assets/Logo Schema.png",
                     style={"height":"58px","objectFit":"contain"}),
        ], className="header-logos", style={
            "position":"absolute","left":"18px","top":"50%",
            "transform":"translateY(-50%)",
            "display":"flex","flexDirection":"row","alignItems":"center","gap":"10px",
        }),
        # Título centrado en el ancho total
        html.Div([
            html.Div("ColombiaMacro",
                     style={"fontSize":"36px","fontWeight":"900","color":TEXT,
                            "letterSpacing":"1px","textAlign":"center"}),
            html.Div("Lectura del ciclo economico colombiano para decisiones de mercado",
                     style={"fontSize":"15px","color":MUTED,"textAlign":"center",
                            "marginTop":"5px","letterSpacing":"0.3px"}),
        ], className="header-title", style={"width":"100%"}),
    ], className="dashboard-header", style={
        "position":"relative",
        "background":BG_PANEL,"border":f"1px solid {BORDER}",
        "borderRadius":"12px","padding":"16px 18px","marginBottom":"12px",
        "display":"flex","alignItems":"center","justifyContent":"center",
    }),

    html.Div([
        html.Div([
            html.Div("La historia que cuenta este tablero",
                     style={"fontSize":"12px","fontWeight":"900","color":C_AZUL,
                            "letterSpacing":"0.8px","textTransform":"uppercase","marginBottom":"8px"}),
            html.Div("¿En que parte del ciclo economico esta Colombia?",
                     style={"fontSize":"26px","fontWeight":"900","color":TEXT,
                            "lineHeight":"1.12","marginBottom":"8px"}),
            html.Div([
                "El objetivo no es mirar graficas sueltas: es conectar ",
                html.Strong("PIB e inflacion", style={"color":TEXT}),
                " para ubicar el ciclo, leer ",
                html.Strong("tasas TES", style={"color":TEXT}),
                " como precio del dinero y contrastar eso con ",
                html.Strong("renta variable colombiana", style={"color":TEXT}),
                ". Asi se aterriza una idea usada en mercados grandes, como Estados Unidos, al caso local.",
            ], style={"fontSize":"14px","color":MUTED,"lineHeight":"1.55","maxWidth":"880px"}),
        ], className="story-intro-text", style={"flex":"2","minWidth":"260px"}),

        html.Div([
            story_badge("Lectura ultimo corte", STORY["phase"], STORY["phase_note"], STORY["phase_color"]),
            story_badge("IPC anual", STORY["inflation"], STORY["inflation_date"], C_INF_A),
            story_badge("PIB real", STORY["pib"], STORY["pib_date"], C_PIB),
        ], className="story-badges", style={
            "display":"flex","gap":"8px","flexWrap":"wrap","flex":"1.4","minWidth":"280px",
        }),
    ], className="story-hero", style={
        "display":"flex","gap":"16px","alignItems":"stretch","flexWrap":"wrap",
        "background":BG_PANEL,"border":f"1px solid {BORDER}",
        "borderRadius":"12px","padding":"16px","marginBottom":"12px",
    }),

    html.Div([
        story_step(1, "Primero: ciclo economico",
                   "PIB real dice si la actividad acelera o se frena. Inflacion dice si el costo de vida presiona o se calma.",
                   C_PIB),
        story_step(2, "Despues: precio del dinero",
                   "La curva TES muestra cuanto exige el mercado por prestar a corto, medio y largo plazo.",
                   C_TES5),
        story_step(3, "Luego: activos",
                   "Con ciclo y tasas se comparan clases de activos: renta variable, renta fija, materias primas y divisas.",
                   C_GRANDES),
        story_step(4, "Finalmente: bolsa local",
                   "COLCAP es la referencia oficial; las lineas punteadas son reconstrucciones para auditar amplitud y liderazgo.",
                   C_BOLSA),
    ], className="story-steps", style={
        "display":"grid","gridTemplateColumns":"repeat(4, minmax(0, 1fr))",
        "gap":"10px","marginBottom":"12px",
    }),

    # Controles principales
    html.Div([
        html.Div("Período", style={"fontSize":"11px","fontWeight":"700","color":MUTED,"marginBottom":"4px"}),
        dcc.Dropdown(id="time-window",
            options=[{"label":l,"value":v} for l,v in [
                ("3 meses","3M"),("6 meses","6M"),("1 año","1A"),
                ("3 años","3A"),("5 años","5A"),("Todo","ALL")]],
            value="ALL", clearable=False, style={"minWidth":"160px"}),
        html.Button("Ver detalle", id="open-modal", n_clicks=0, style={
            "background":TEXT,"color":"#ffffff","border":"0","borderRadius":"8px",
            "padding":"8px 14px","fontSize":"12px","fontWeight":"700",
            "cursor":"pointer","marginLeft":"auto",
        }),
    ], style={
        "display":"flex","alignItems":"center","gap":"6px","flexWrap":"wrap",
        "background":BG_PANEL,"border":f"1px solid {BORDER}",
        "borderRadius":"12px","padding":"10px 12px","marginBottom":"12px",
    }),

    html.Div([
        html.Div([
            html.Span(str(item["fuente"]), style={"fontWeight":"700","color":TEXT}),
            html.Span(periodo_fuente(item),
                      style={"color":MUTED,"marginLeft":"7px"}),
            html.Span("●", title=str(item["estado"]),
                      style={"color":"#16a34a" if item["estado"] == "vigente" else "#d97706",
                             "marginLeft":"7px"}),
        ], style={"whiteSpace":"nowrap","fontSize":"11px"})
        for _, item in df_estado[df_estado["fuente"] != "Canastas experimentales"].iterrows()
    ], style={"display":"flex","gap":"18px","flexWrap":"wrap","padding":"0 4px 10px"}),

    # CUERPO
    html.Div([

        # ── PANEL IZQUIERDO ──────────────────────────────
        html.Div([
            # sync-panels oculto (necesario para callbacks)
            html.Div(dcc.Checklist(id="sync-panels",
                options=[{"label":"","value":v} for v in ["inflacion","tes","bolsa"]],
                value=[]), style={"display":"none"}),

            # Los 3 gráficos — orden: ① COLCAP/mercado · ② Inflación/PIB · ③ TES
            html.Div([
                html.Div("COLCAP Y CANASTAS COLOMBIANAS",
                         style={"fontSize":"19px","fontWeight":"900","color":TEXT,
                                "textAlign":"center","letterSpacing":"1.5px"}),
            ], style={"padding":"8px 14px","background":BG_CARD,"border":f"1px solid {BORDER}",
                      "borderRadius":"8px","marginBottom":"3px"}),
            chart_description("Bolsa colombiana: mercado y canastas",
                "El COLCAP oficial procede de BanRep. El 28 de mayo de 2021 pasó de la metodología BVC a la de MSCI: "
                "conservó su nivel histórico, pero cambió cómo se seleccionan y ponderan las acciones. "
                "Las líneas punteadas son dos canastas propias heredadas bajo revisión, "
                "calculadas con retornos mensuales. Sus puntos diarios no son precios observados. "
                "Todas las curvas se expresan en base 100 al 9 de febrero de 2009."),
            dcc.Checklist(id="bolsa-layers", options=[
                {"label":help_label("COLCAP oficial"), "value":"oficial"},
                {"label":help_label("Índice equiponderado"), "value":"equiponderado"},
                {"label":help_label("7 Magníficas"), "value":"grandes"},
            ], value=["oficial", "equiponderado", "grandes"],
                inline=True, className="bolsa-layers",
                style={"fontSize":"12px","color":TEXT,"padding":"8px 4px",
                       "background":BG_PANEL,"border":f"1px solid {BORDER}",
                       "borderRadius":"8px","marginBottom":"4px"},
                inputStyle={"marginRight":"4px","marginLeft":"12px"}),
            chart_readout("chart-bolsa"),
            dcc.Graph(id="chart-bolsa", clear_on_unhover=False, config=CHART_CONFIG),
            html.Div([
                html.Div("INFLACIÓN Y PIB",
                         style={"fontSize":"19px","fontWeight":"900","color":TEXT,
                                "textAlign":"center","letterSpacing":"1.5px"}),
            ], style={"padding":"8px 14px","background":BG_CARD,"border":f"1px solid {BORDER}",
                      "borderRadius":"8px","marginBottom":"3px"}),
            chart_description("Inflación y PIB: precios y actividad",
                "La inflación mensual y anual procede del IPC de DANE/BanRep: compara los precios de consumo "
                "con el mes anterior y con el mismo mes del año anterior, respectivamente. El PIB real del DANE "
                "registra la variación de la producción frente al mismo trimestre del año anterior, descontando "
                "el efecto de los precios. Las series conservan sus frecuencias originales: mensual para el IPC "
                "y trimestral para el PIB. La escala mensual mantiene una relación visual de 1 a 10 con la anual, "
                "sin modificar los porcentajes originales. Las fechas corresponden al cierre del mes o trimestre "
                "de referencia, no a la publicación. El PIB incorpora las revisiones del archivo DANE utilizado."),
            html.Div([
                html.Div("Capas del gráfico",
                         style={"fontSize":"11px","fontWeight":"800","color":MUTED,"marginRight":"6px"}),
                dcc.Checklist(id="inf-layers",
                    options=[
                        {"label":help_label("Inflación mensual"),"value":"inf_mensual"},
                        {"label":help_label("Inflación anual"),"value":"inf_anual"},
                        {"label":help_label("PIB real"),"value":"pib"},
                    ],
                    value=["inf_mensual","inf_anual","pib"], inline=True,
                    inputStyle={"marginRight":"5px","marginLeft":"10px"},
                    labelStyle={"fontSize":"12px","color":TEXT,"whiteSpace":"nowrap"}),
            ], className="chart-local-controls", style={
                "display":"flex","alignItems":"center","gap":"4px","flexWrap":"wrap",
                "background":BG_PANEL,"border":f"1px solid {BORDER}",
                "borderRadius":"8px","padding":"8px 10px","marginBottom":"4px",
            }),
            chart_readout("chart-inflacion"),
            dcc.Graph(id="chart-inflacion", clear_on_unhover=False, config=CHART_CONFIG,
                style={"marginBottom":"4px"}),
            html.Div([
                html.Div("SEÑALES DE MERCADO COLOMBIANO",
                         style={"fontSize":"19px","fontWeight":"900","color":TEXT,
                                "textAlign":"center","letterSpacing":"1.5px"}),
                html.Div("Curva cero cupón TES pesos · observaciones diarias",
                         style={"fontSize":"13px","color":MUTED,"textAlign":"center","marginTop":"3px"}),
            ], style={"padding":"8px 14px","background":BG_CARD,"border":f"1px solid {BORDER}",
                      "borderRadius":"8px","marginBottom":"3px"}),
            chart_description("TES: tasas de la deuda pública",
                "Tasas anuales de la curva cero cupón de TES en pesos, publicadas por el Banco de la República "
                "para plazos de 1, 5 y 10 años. La serie reúne observaciones de días de mercado sobre la deuda "
                "del Gobierno colombiano. La diferencia entre las tasas de 10 y 1 año, expresada en puntos "
                "porcentuales, resume la pendiente entre los plazos largo y corto."),
            html.Div([
                html.Div("Plazos visibles",
                         style={"fontSize":"11px","fontWeight":"800","color":MUTED,"marginRight":"6px"}),
                dcc.Checklist(id="curve-toggle",
                    options=[{"label":help_label(v),"value":v} for v in ["1A","5A","10A"]],
                    value=["1A","5A","10A"], inline=True,
                    inputStyle={"marginRight":"5px","marginLeft":"10px"},
                    labelStyle={"fontSize":"12px","color":TEXT,"whiteSpace":"nowrap"}),
            ], className="chart-local-controls", style={
                "display":"flex","alignItems":"center","gap":"4px","flexWrap":"wrap",
                "background":BG_PANEL,"border":f"1px solid {BORDER}",
                "borderRadius":"8px","padding":"8px 10px","marginBottom":"4px",
            }),
            chart_readout("chart-tes"),
            dcc.Graph(id="chart-tes", clear_on_unhover=False, config=CHART_CONFIG,
                style={"marginBottom":"4px"}),

        ], className="dashboard-main", style={"width":"72%","background":BG_PANEL,
                  "border":f"1px solid {BORDER}","borderRadius":"12px","padding":"10px"}),

        # ── PANEL DERECHO ────────────────────────────────
        html.Div([
            html.Div("CURVA DE RENDIMIENTOS TES", style={
                "fontSize":"19px","fontWeight":"900","color":TEXT,
                "textAlign":"center","letterSpacing":"1.5px",
                "padding":"8px 14px","background":BG_CARD,
                "border":f"1px solid {BORDER}","borderRadius":"8px",
                "marginBottom":"8px",
            }),
            html.Button("×", id="btn-soltar", n_clicks=0,
                        title="Liberar fecha fijada", **{"aria-label": "Liberar fecha fijada"},
                        style={"alignSelf":"flex-end","width":"32px","height":"32px",
                               "border":f"1px solid {BORDER}","background":"#fff",
                               "borderRadius":"4px","cursor":"pointer","fontSize":"22px"}),

            html.Div(id="fecha-activa", style={
                "fontSize":"12px","fontWeight":"800","color":TEXT,
                "background":BG_CARD,"border":f"1px solid {BORDER}",
                "borderRadius":"8px","padding":"8px 10px","marginBottom":"8px",
            }),

            # Leyenda TES
            html.Div([
                *[html.Span([
                    html.Span("━━", style={"color":c,"marginRight":"4px","fontWeight":"900"}),
                    html.Span(help_label(lbl), style={"fontSize":"9px","color":MUTED}),
                ], style={"marginRight":"12px","whiteSpace":"nowrap"}) for c, lbl in [
                    (C_TES1, "TES 1A"),
                    (C_TES5, "TES 5A"),
                    (C_TES10,"TES 10A"),
                ]],
            ], style={"display":"flex","flexDirection":"row","alignItems":"center",
                      "marginBottom":"8px","flexWrap":"nowrap"}),

            dcc.Graph(id="curve-chart",
                config={
                    "displaylogo": False,
                    "responsive": True,
                    "displayModeBar": "hover",
                    "modeBarButtons": [["toImage", "zoomIn2d", "resetScale2d"]],
                },
                style={"height":"260px"}),

            html.Hr(style={"borderColor":BORDER,"margin":"8px 0"}),
            html.Div("Últimas observaciones por frecuencia",
                     style={"fontSize":"10px","color":MUTED,"marginBottom":"6px"}),
            html.Div(id="curve-metrics",
                     style={"display":"flex","gap":"5px","flexWrap":"wrap"}),

            html.Hr(style={"borderColor":BORDER,"margin":"8px 0"}),

            html.Div("Guion rapido para explicarlo",
                     style={"fontSize":"12px","fontWeight":"900","color":TEXT,
                            "marginBottom":"8px"}),
            html.Ol([
                html.Li("Empieza por PIB e inflacion: ahi se ubica la fase del ciclo.", style={"marginBottom":"6px"}),
                html.Li("Luego mira TES: si el dinero se encarece, empresas y consumo sienten presion.", style={"marginBottom":"6px"}),
                html.Li("Cierra con COLCAP: la bolsa muestra como reaccionan las empresas listadas, no toda la economia.", style={"marginBottom":"6px"}),
                html.Li("Aclara que las lineas punteadas son comparaciones heredadas bajo revision.", style={"marginBottom":"0"}),
            ], style={"fontSize":"12px","color":MUTED,"lineHeight":"1.45","paddingLeft":"18px","margin":"0"}),

            html.Hr(style={"borderColor":BORDER,"margin":"10px 0"}),
            html.Div("Clases de activos en la historia",
                     style={"fontSize":"12px","fontWeight":"900","color":TEXT,
                            "marginBottom":"8px"}),
            html.Div([
                html.Span("Renta variable", className="asset-pill"),
                html.Span("Renta fija", className="asset-pill"),
                html.Span("Materias primas", className="asset-pill"),
                html.Span("Divisas", className="asset-pill"),
            ], style={"display":"flex","gap":"6px","flexWrap":"wrap"}),

        ], className="dashboard-side", style={"width":"28%","background":BG_PANEL,
                  "border":f"1px solid {BORDER}","borderRadius":"12px","padding":"14px",
                  "display":"flex","flexDirection":"column",
                  "overflowY":"auto","maxHeight":"1060px"}),

    ], className="dashboard-body", style={"display":"flex","gap":"12px","alignItems":"flex-start"}),

    # Stores
    dcc.Store(id="detail-window",  data="1A"),
    dcc.Store(id="fecha-fijada",   data=None),
    dcc.Store(id="xrange-store",   data={}),

], style={"background":BG_APP,"minHeight":"100vh",
          "padding":"14px","fontFamily":"Inter, Segoe UI, Arial, sans-serif"})


# ══════════════════════════════════════════════════════════
# 9. CALLBACKS
# ══════════════════════════════════════════════════════════

# ── Sincronización de zoom ────────────────────────────────
@app.callback(
    Output("xrange-store","data"),
    [Input(cid, "relayoutData") for cid in ALL_CHARTS],
    Input("sync-panels","value"),
    State("xrange-store","data"),
    prevent_initial_call=True,
)
def sync_zoom(*args):
    relay_list = args[:len(ALL_CHARTS)]
    synced     = args[len(ALL_CHARTS)]
    current    = args[len(ALL_CHARTS)+1]
    trigger    = ctx.triggered_id

    if trigger == "sync-panels":
        return {}

    panel_val = PANEL_IDS.get(trigger)
    if not panel_val or panel_val not in (synced or []):
        return current or {}

    idx   = ALL_CHARTS.index(trigger)
    relay = relay_list[idx]
    if not relay:
        return current or {}

    if "xaxis.range[0]" in relay and "xaxis.range[1]" in relay:
        return {"range": [relay["xaxis.range[0]"], relay["xaxis.range[1]"]]}
    elif "xaxis.autorange" in relay or "autosize" in relay:
        return {}
    return current or {}


for chart_id in [*ALL_CHARTS, "detail-chart"]:
    app.clientside_callback(
        ClientsideFunction(namespace="analysis", function_name="readout"),
        Output(f"{chart_id}-readout", "children"),
        Input(chart_id, "hoverData"), Input(chart_id, "figure"),
    )


# ── Callbacks individuales de cada panel ─────────────────
@app.callback(
    Output("chart-bolsa","figure"),
    Input("time-window","value"),
    Input("xrange-store","data"),
    Input("sync-panels","value"),
    Input("bolsa-layers","value"),
)
def upd_bolsa(window, xrd, synced, layers):
    if ctx.triggered_id == "xrange-store" and (xrd or {}).get("range") and "bolsa" not in (synced or []):
        return no_update
    dff = filter_window(df_colcap, window)
    xr  = (xrd or {}).get("range") if "bolsa" in (synced or []) else None
    return make_fig_bolsa(dff, xr, layers)

@app.callback(
    Output("chart-inflacion","figure"),
    Input("time-window","value"),
    Input("xrange-store","data"),
    Input("sync-panels","value"),
    Input("inf-layers","value"),
)
def upd_inflacion(window, xrd, synced, layers):
    if ctx.triggered_id == "xrange-store" and (xrd or {}).get("range") and "inflacion" not in (synced or []):
        return no_update
    dff = filter_window(df_daily, window)
    xr  = (xrd or {}).get("range") if "inflacion" in (synced or []) else None
    return make_fig_inflacion(dff, xr, layers)

@app.callback(
    Output("chart-tes","figure"),
    Input("time-window","value"),
    Input("xrange-store","data"),
    Input("sync-panels","value"),
    Input("curve-toggle","value"),
)
def upd_tes(window, xrd, synced, active_tenors):
    if ctx.triggered_id == "xrange-store" and (xrd or {}).get("range") and "tes" not in (synced or []):
        return no_update
    dff = filter_window(df_tes, window)
    xr  = (xrd or {}).get("range") if "tes" in (synced or []) else None
    return make_fig_tes(dff, active_tenors, xr)


# ── Curva TES + métricas (hover/click) ───────────────────
@app.callback(
    Output("curve-chart",   "figure"),
    Output("fecha-activa",  "children"),
    Output("curve-metrics", "children"),
    Output("fecha-fijada",  "data"),
    [Input(cid, "clickData") for cid in ALL_CHARTS],
    [Input(cid, "hoverData") for cid in ALL_CHARTS],
    Input("time-window",  "value"),
    Input("curve-toggle", "value"),
    Input("btn-soltar", "n_clicks"),
    State("fecha-fijada", "data"),
)
def update_curve(*args):
    n = len(ALL_CHARTS)
    click_list = args[:n]
    hover_list = args[n:2*n]
    window, active_tenors, fecha_fijada = args[2*n], args[2*n+1], args[2*n+3]

    dff     = filter_window(df_daily, window)
    trigger = ctx.triggered_id

    click_map = {cid: click_list[i] for i, cid in enumerate(ALL_CHARTS)}
    hover_map = {cid: hover_list[i]  for i, cid in enumerate(ALL_CHARTS)}

    triggered_property = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
    if trigger == "btn-soltar" or trigger == "time-window":
        row = dff.iloc[-1]
        nueva_fecha = None
    elif triggered_property.endswith(".clickData") and click_map.get(trigger):
        row = get_hover_row(click_map[trigger], dff)
        nueva_fecha = str(row["fecha"])
    elif fecha_fijada:
        row = pd.Series({"fecha": pd.Timestamp(fecha_fijada)})
        nueva_fecha = fecha_fijada
    elif trigger in ALL_CHARTS:
        row = get_hover_row(hover_map.get(trigger), dff)
        nueva_fecha = None
    else:
        row = dff.iloc[-1]
        nueva_fecha = None

    # Cada frecuencia conserva su propia ultima observacion anterior a la fecha activa.
    tes_row = latest_on_or_before(df_tes, row["fecha"],
                                  ["tes_pesos_1y","tes_pesos_5y","tes_pesos_10y"])
    col_map = {"1A":"tes_pesos_1y","5A":"tes_pesos_5y","10A":"tes_pesos_10y"}
    desc    = {"1A":"Corto plazo","5A":"Medio plazo","10A":"Largo plazo"}
    cards   = []
    for key in ["1A","5A","10A"]:
        if key in active_tenors and tes_row is not None:
            cards.append(metric_card(f"TES {key}",
                f"{float(tes_row[col_map[key]]):.2f}%", TENOR_COLORS[col_map[key]],
                f"{desc[key]} · {fecha_es(tes_row['fecha'])}"))
    if "1A" in active_tenors and "10A" in active_tenors and tes_row is not None:
        sp = float(tes_row["tes_pesos_10y"]) - float(tes_row["tes_pesos_1y"])
        st = "Normal" if sp > 0.3 else ("Invertida" if sp < 0 else "Plana")
        co = C_AZUL if sp > 0.3 else (C_ROJO if sp < 0 else C_AMARILLO)
        cards.append(metric_card("Spread 10A-1A", f"{sp:+.2f}pp", co,
                                 f"{st} · {fecha_es(tes_row['fecha'])}"))

    colcap_row = latest_on_or_before(df_colcap, row["fecha"], ["colcap_puntos"])
    if colcap_row is not None:
        cards.append(metric_card("COLCAP oficial", f"{float(colcap_row['colcap_puntos']):,.2f}",
                                 C_BOLSA, f"puntos · {fecha_es(colcap_row['fecha'])}"))
    inf_row = latest_inflation_row(row["fecha"])
    if inf_row is not None and pd.notna(inf_row.get("inflacion_mensual")):
        cards.append(metric_card("Inflación mensual",
            f"{float(inf_row['inflacion_mensual']):.2f}%", C_INF_M, mes_es(inf_row["fecha"])))
    if inf_row is not None and pd.notna(inf_row.get("inflacion_anual")):
        cards.append(metric_card("Inflación anual 12M",
            f"{float(inf_row['inflacion_anual']):.2f}%", C_INF_A, mes_es(inf_row["fecha"])))
    pib_row = latest_on_or_before(df_pib, row["fecha"], ["pib_real_yoy"], pd.offsets.QuarterEnd(0))
    if pib_row is not None:
        cards.append(metric_card("PIB real interanual",
            f"{float(pib_row['pib_real_yoy']):.2f}%", C_PIB,
            f"{pib_row['trimestre']} · vintage {pib_row['fecha_publicacion_vintage']}"))

    label_f = (f"Fecha fijada: {fecha_es(row['fecha'])}" if nueva_fecha
               else f"Referencia: {fecha_es(row['fecha'])}")
    return make_curve_fig(tes_row, active_tenors) if tes_row is not None else go.Figure(), label_f, cards, nueva_fecha


# ── Modal ─────────────────────────────────────────────────
@app.callback(
    Output("modal","style"),
    Input("open-modal","n_clicks"), Input("close-modal","n_clicks"),
    State("modal","style"), prevent_initial_call=True,
)
def toggle_modal(o, c, style):
    style = style or {}
    style["display"] = "block" if ctx.triggered_id == "open-modal" else "none"
    return style


@app.callback(
    Output("detail-window","data"),
    Output("detail-periodo-label","children"),
    *[Input(f"detail-btn-{v}","n_clicks")
      for v in ["3M","6M","1A","3A","5A","ALL"]],
    prevent_initial_call=True,
)
def set_detail_window(*args):
    labels = {"3M":"3 meses","6M":"6 meses","1A":"1 año",
              "3A":"3 años","5A":"5 años","ALL":"Todo el período"}
    val = ctx.triggered_id.replace("detail-btn-","")
    return val, f"Mostrando: {labels.get(val,'')}"


@app.callback(
    Output("detail-chart","figure"),
    Input("detail-var","value"),
    Input("detail-window","data"),
    Input("curve-toggle","value"),
    Input("inf-layers","value"),
    Input("bolsa-layers","value"),
)
def update_detail(variable, window, active_tenors, layers, bolsa_layers):
    dff = filter_window(df_daily, window or "1A")
    if variable == "bolsa":
        return make_fig_bolsa(filter_window(df_colcap, window or "1A"), layers=bolsa_layers)
    elif variable == "inflacion":
        return make_fig_inflacion(dff, show_layers=["inf_mensual","inf_anual"])
    elif variable == "pib":
        return make_fig_inflacion(dff, show_layers=["pib"])
    elif variable == "inf_pib":
        return make_fig_inflacion(dff, show_layers=["inf_anual","pib"])
    elif variable == "tes":
        return make_fig_tes(dff, active_tenors)
    return go.Figure()


# ══════════════════════════════════════════════════════════
# 10. RUN
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    def abrir():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8050")
    threading.Thread(target=abrir, daemon=True).start()
    print("\n" + "="*55)
    print("  Dashboard v8.1 Colombia -> http://127.0.0.1:8050")
    print("  Para cerrar: Ctrl + C")
    print("="*55 + "\n")
    app.run(debug=False, host="127.0.0.1", port=8050)
