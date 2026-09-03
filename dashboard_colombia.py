"""
╔══════════════════════════════════════════════════════════════════╗
║   DASHBOARD FINANCIERO COLOMBIA — v8.0                          ║
║   Panel ① ICOLCAP real · Sintético · 7 Grandes                  ║
║   Panel ② Inflación + PIB (toggle)                              ║
║   Panel ③ TES Pesos 1A · 5A · 10A                               ║
╠══════════════════════════════════════════════════════════════════╣
║  Archivos requeridos (misma carpeta):                           ║
║    • datos_colombia_clean.csv                                   ║
║    • tasas_interes_clean.csv                                     ║
║    • inflacion_clean.csv                                        ║
║    • indices_colombia.csv                                       ║
║    • icolcap_composicion.csv                                    ║
║    • pib_colombia.csv                                           ║
║                                                                  ║
║  pip install dash plotly pandas                                 ║
║  python dashboard_colombia.py  →  http://127.0.0.1:8050        ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os, threading, time, webbrowser
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html, ctx, no_update
from plotly.subplots import make_subplots

# ══════════════════════════════════════════════════════════
# 0. RUTAS
# ══════════════════════════════════════════════════════════
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CSV_PRECIO  = os.path.join(BASE_DIR, "datos_colombia_clean.csv")
CSV_TES     = os.path.join(BASE_DIR, "tasas_interes_clean.csv")
CSV_INF     = os.path.join(BASE_DIR, "inflacion_clean.csv")
CSV_INDICES = os.path.join(BASE_DIR, "indices_colombia.csv")
CSV_COMP    = os.path.join(BASE_DIR, "icolcap_composicion.csv")
CSV_PIB     = os.path.join(BASE_DIR, "pib_colombia.csv")

# ══════════════════════════════════════════════════════════
# 1. CARGA Y PREPARACIÓN
# ══════════════════════════════════════════════════════════
df_precio  = pd.read_csv(CSV_PRECIO,  parse_dates=["fecha"])
df_tes     = pd.read_csv(CSV_TES,     parse_dates=["fecha"])
df_inf     = pd.read_csv(CSV_INF,     parse_dates=["fecha"])

# Todos los índices diarios: ICOLCAP base100, sintético, 7 grandes
df_indices = pd.read_csv(CSV_INDICES, parse_dates=["fecha"])
df_indices["date"] = df_indices["fecha"].dt.normalize()

df_comp = pd.read_csv(CSV_COMP)
df_pib  = pd.read_csv(CSV_PIB, parse_dates=["fecha"])

# Merge diario principal
for _df in [df_precio, df_tes]:
    _df["date"] = _df["fecha"].dt.normalize()

df_daily = (df_precio
    .merge(df_tes[["date","tes_pesos_1y","tes_pesos_5y","tes_pesos_10y"]], on="date", how="left")
    .merge(df_indices[["date","icolcap_base100","sintetico_base100","grandes_base100"]], on="date", how="left")
    .dropna(subset=["tes_pesos_1y"]).reset_index(drop=True))

# (sintetico_base100 y grandes_base100 ya vienen diarios desde indices_colombia.csv)
df_daily["mes"] = df_daily["fecha"].dt.to_period("M")
df_inf["mes"]   = df_inf["fecha"].dt.to_period("M")
df_daily = df_daily.merge(
    df_inf[["mes","inflacion_mensual","inflacion_anual"]], on="mes", how="left")

# PIB: preparar crecimiento YoY limpio
df_pib = df_pib.dropna(subset=["pib_crecimiento_yoy"]).copy()

FECHA_INI = df_daily["fecha"].min()
FECHA_FIN = df_daily["fecha"].max()

# Empresas grandes
GRANDES = df_comp[df_comp["es_grande"]]["ticker"].tolist()
GRANDES_NOMBRES = dict(zip(df_comp["ticker"], df_comp["nombre"]))

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

C_BOLSA    = "#3fb950"   # ICOLCAP real
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
        row = nearest_row(dff, pt.get("x"))
        if row is not None:
            return row
    return dff.iloc[-1]

def agg_inflacion(dff):
    return (dff.groupby("mes", as_index=False)
               .agg(fecha=("fecha","first"),
                    inflacion_mensual=("inflacion_mensual","first"),
                    inflacion_anual=("inflacion_anual","first"))
               .sort_values("fecha"))

# ══════════════════════════════════════════════════════════
# 4. BASE LAYOUT
# ══════════════════════════════════════════════════════════
BASE_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor=BG_PANEL, plot_bgcolor=BG_PANEL,
    hovermode="x unified",
    dragmode="pan",
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
    return dict(type="date", showgrid=True, gridcolor=GRID_CLR,
                range=x_range, **SPIKE_CFG)

def yaxis_base(title, suffix=""):
    return dict(title=title, gridcolor=GRID_CLR, zeroline=False,
                ticksuffix=suffix, **SPIKE_CFG)

# ══════════════════════════════════════════════════════════
# 5A. PANEL ① — BOLSA UNIFICADO
#   Línea 1: ICOLCAP real (base 100) — verde
#   Línea 2: Índice Sintético igualitario (base 100) — celeste
#   Línea 3: Las 7 Grandes Colombia (base 100) — amarillo
#   Línea 4: Media 20D del ICOLCAP — gris punteado
#   Línea 5: Media 50D del ICOLCAP — amarillo punteado
# ══════════════════════════════════════════════════════════
def make_fig_bolsa(dff, x_range=None):
    fig = go.Figure()

    # ── ICOLCAP real base 100 ─────────────────────────────
    fig.add_trace(go.Scatter(
        x=dff["fecha"], y=dff["icolcap_base100"],
        name="ICOLCAP General",
        mode="lines", line=dict(color=C_BOLSA, width=2.5),
        fill="tozeroy", fillcolor="rgba(63,185,80,0.06)",
        hovertemplate="<b>ICOLCAP General:</b> %{y:.2f}<extra></extra>",
    ))

    # ── Índice Igual Ponderación ───────────────────────
    fig.add_trace(go.Scatter(
        x=dff["fecha"], y=dff["sintetico_base100"],
        name="Índice Diversificado Colombia",
        mode="lines", line=dict(color=C_SINTET, width=2.0), opacity=0.85,
        hovertemplate="<b>Índice Diversificado:</b> %{y:.2f}<extra></extra>",
    ))

    # ── 7 Grandes Colombia ─────────────────────────────
    fig.add_trace(go.Scatter(
        x=dff["fecha"], y=dff["grandes_base100"],
        name="7 Magníficas Colombianas",
        mode="lines", line=dict(color=C_GRANDES, width=2.0), opacity=0.85,
        hovertemplate="<b>7 Magníficas:</b> %{y:.2f}<extra></extra>",
    ))

    fig.add_hline(y=100, line_dash="dot", line_color="#334155", line_width=1,
        annotation_text="  Base Ene 2009 = 100",
        annotation_font=dict(color="#475569", size=9),
        annotation_position="right")

    fig.update_layout(
        **BASE_LAYOUT, height=355,
        xaxis=xaxis_base(x_range),
        yaxis=yaxis_base("Índice (base 100)"),
    )
    return fig

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

    df_inf_m = agg_inflacion(dff)
    dff_pib  = filter_window_pib(None)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # ── Zona meta BanRep 2–4 % (fondo sutil) ─────────────
    if "inf_anual" in show_layers:
        fig.add_hrect(
            y0=2.0, y1=4.0,
            fillcolor="rgba(74,222,128,0.05)", line_width=0, layer="below",
        )

    # ── Barras inflación mensual — escala de calor ────────
    if "inf_mensual" in show_layers:
        cb = [_color_inf_mensual(v) for v in df_inf_m["inflacion_mensual"]]
        fig.add_trace(go.Bar(
            x=df_inf_m["fecha"], y=df_inf_m["inflacion_mensual"],
            name="Inflación mensual",
            marker=dict(color=cb, opacity=0.75, line=dict(width=0)),
            hovertemplate="<b>Inflación mensual:</b> %{y:.2f}%<extra></extra>",
        ), secondary_y=False)

    # ── Área + línea inflación anual ──────────────────────
    if "inf_anual" in show_layers:
        fig.add_trace(go.Scatter(
            x=df_inf_m["fecha"], y=df_inf_m["inflacion_anual"],
            mode="lines",
            line=dict(color="rgba(244,63,94,0)", width=0),
            fill="tozeroy", fillcolor="rgba(244,63,94,0.10)",
            showlegend=False, hoverinfo="skip",
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=df_inf_m["fecha"], y=df_inf_m["inflacion_anual"],
            name="Inflación anual 12M",
            mode="lines", line=dict(color="#f43f5e", width=2.5),
            hovertemplate="<b>Inflación anual 12M:</b> %{y:.2f}%<extra></extra>",
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=[df_inf_m["fecha"].min(), df_inf_m["fecha"].max()],
            y=[3.0, 3.0],
            name="Meta BanRep 3%",
            mode="lines",
            line=dict(color="rgba(148,163,184,0.55)", width=1.5, dash="dash"),
            hovertemplate="<b>Meta BanRep:</b> 3.00%<extra></extra>",
        ), secondary_y=False)

    # ── PIB crecimiento YoY — barras semitransparentes ────
    if "pib" in show_layers:
        dff_pib_f = dff_pib[
            (dff_pib["fecha"] >= dff["fecha"].min()) &
            (dff_pib["fecha"] <= dff["fecha"].max())
        ]
        colores_pib = [
            "rgba(16,185,129,0.65)" if v >= 0 else "rgba(239,68,68,0.65)"
            for v in dff_pib_f["pib_crecimiento_yoy"]
        ]
        fig.add_trace(go.Bar(
            x=dff_pib_f["fecha"], y=dff_pib_f["pib_crecimiento_yoy"],
            name="PIB — Crecimiento anual (%)",
            marker=dict(color=colores_pib, line=dict(width=0)),
            hovertemplate=(
                "<b>PIB Colombia:</b> %{y:.2f}% interanual<br>"
                "<b>Trimestre:</b> %{customdata}<extra></extra>"
            ),
            customdata=dff_pib_f["trimestre"].values,
        ), secondary_y=True)
        fig.add_hline(y=0, line_dash="solid",
                      line_color="rgba(51,65,85,0.6)", line_width=1, row=1, col=1)

    fig.update_yaxes(
        title_text="Inflación (%)", ticksuffix="%",
        gridcolor=GRID_CLR, zeroline=False, **SPIKE_CFG,
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="", showticklabels=False,
        showgrid=False, zeroline=False, showline=False,
        secondary_y=True,
    )
    fig.update_layout(
        **BASE_LAYOUT, height=320,
        xaxis=dict(**xaxis_base(x_range)),
        barmode="overlay",
    )
    fig.update_layout(margin_r=15)
    return fig

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
        # Área rellena (vinculada al grupo de leyenda)
        fig.add_trace(go.Scatter(
            x=dff["fecha"], y=dff[col],
            mode="lines", line=dict(color=color, width=0),
            fill="tozeroy", fillcolor=_TES_FILL[col],
            legendgroup=grp, showlegend=False, hoverinfo="skip",
            visible=vis,
        ))
        # Línea principal
        fig.add_trace(go.Scatter(
            x=dff["fecha"], y=dff[col],
            name=label, visible=vis, mode="lines",
            line=dict(color=color, width=2.5),
            legendgroup=grp,
            hovertemplate=f"<b>{label}:</b> %{{y:.2f}}%<extra></extra>",
        ))
    fig.update_layout(
        **BASE_LAYOUT, height=310,
        xaxis=xaxis_base(x_range),
        yaxis=yaxis_base("Tasa anual (%)", "%"),
    )
    return fig

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
        textfont=dict(color="#fff", size=13),
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
                   showgrid=True, gridcolor=GRID_CLR, zeroline=False,
                   color=TEXT, ticksuffix="%"),
    )
    return fig

# ══════════════════════════════════════════════════════════
# 7. TARJETA MÉTRICA
# ══════════════════════════════════════════════════════════
def metric_card(title, value, color, subtitle=""):
    return html.Div([
        html.Div(title,    style={"fontSize":"10px","color":MUTED,"marginBottom":"2px"}),
        html.Div(value,    style={"fontSize":"16px","fontWeight":"700","color":color,"lineHeight":"1.1"}),
        html.Div(subtitle, style={"fontSize":"10px","color":MUTED,"marginTop":"2px"}),
    ], style={
        "background":BG_CARD,"border":f"1px solid {BORDER}",
        "borderRadius":"10px","padding":"7px 10px","minWidth":"85px","flex":"1",
    })

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
                    {"label":" Bolsa (ICOLCAP · Sintético · 7 Grandes)", "value":"bolsa"},
                    {"label":" Inflación (mensual + anual)",    "value":"inflacion"},
                    {"label":" PIB Colombia",                   "value":"pib"},
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
        dcc.Graph(id="detail-chart",
                  config={
    "displaylogo": False,
    "scrollZoom": True,
    "responsive": True,
    "displayModeBar": "hover",
    "modeBarButtons": [["toImage", "zoomIn2d", "resetScale2d"]],
}),
        html.Div([
            html.Span("💡 Tip: ", style={"color":C_AZUL,"fontWeight":"700","fontSize":"11px"}),
            html.Span("Usa el rangeslider debajo del gráfico para precisar el período.",
                      style={"color":MUTED,"fontSize":"11px"}),
        ], style={"marginTop":"10px"}),
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
        ], style={
            "position":"absolute","left":"18px","top":"50%",
            "transform":"translateY(-50%)",
            "display":"flex","flexDirection":"row","alignItems":"center","gap":"10px",
        }),
        # Título centrado en el ancho total
        html.Div([
            html.Div("ColombiaMacro",
                     style={"fontSize":"36px","fontWeight":"900","color":TEXT,
                            "letterSpacing":"1px","textAlign":"center"}),
            html.Div("Dashboard de Indicadores Económicos y Bursátiles",
                     style={"fontSize":"15px","color":MUTED,"textAlign":"center",
                            "marginTop":"5px","letterSpacing":"0.3px"}),
        ], style={"width":"100%"}),
    ], style={
        "position":"relative",
        "background":BG_PANEL,"border":f"1px solid {BORDER}",
        "borderRadius":"12px","padding":"16px 18px","marginBottom":"12px",
        "display":"flex","alignItems":"center","justifyContent":"center",
    }),

    # Controles ocultos (necesarios para callbacks)
    html.Div([
        dcc.Dropdown(id="time-window",
            options=[{"label":l,"value":v} for l,v in [
                ("3 meses","3M"),("6 meses","6M"),("1 año","1A"),
                ("3 años","3A"),("5 años","5A"),("Todo","ALL")]],
            value="ALL", clearable=False),
        dcc.Checklist(id="inf-layers",
            options=[
                {"label":"inf_mensual","value":"inf_mensual"},
                {"label":"inf_anual",  "value":"inf_anual"},
                {"label":"pib",        "value":"pib"},
            ],
            value=["inf_mensual","inf_anual","pib"]),
        dcc.Checklist(id="curve-toggle",
            options=[{"label":v,"value":v} for v in ["1A","5A","10A"]],
            value=["1A","5A","10A"]),
        html.Button("Ver en Detalle", id="open-modal", n_clicks=0),
    ], style={"display":"none"}),

    # CUERPO
    html.Div([

        # ── PANEL IZQUIERDO ──────────────────────────────
        html.Div([
            # sync-panels oculto (necesario para callbacks)
            html.Div(dcc.Checklist(id="sync-panels",
                options=[{"label":"","value":v} for v in ["inflacion","tes","bolsa"]],
                value=[]), style={"display":"none"}),

            # Los 3 gráficos — orden: ① Inflación/PIB · ② TES · ③ Bolsa
            html.Div([
                html.Div("INFLACIÓN COLOMBIA & PIB",
                         style={"fontSize":"19px","fontWeight":"900","color":TEXT,
                                "textAlign":"center","letterSpacing":"1.5px"}),
            ], style={"padding":"8px 14px","background":BG_CARD,"border":f"1px solid {BORDER}",
                      "borderRadius":"8px","marginBottom":"3px"}),
            dcc.Graph(id="chart-inflacion", clear_on_unhover=False,
                config={
    "displaylogo": False,
    "scrollZoom": True,
    "responsive": True,
    "displayModeBar": "hover",
    "modeBarButtons": [["toImage", "zoomIn2d", "resetScale2d"]],
},
                style={"marginBottom":"4px"}),

            html.Div([
                html.Div("SEÑALES DE MERCADO COLOMBIANO",
                         style={"fontSize":"19px","fontWeight":"900","color":TEXT,
                                "textAlign":"center","letterSpacing":"1.5px"}),
                html.Div("Tasas TES Pesos — Bonos Soberanos",
                         style={"fontSize":"13px","color":MUTED,"textAlign":"center","marginTop":"3px"}),
            ], style={"padding":"8px 14px","background":BG_CARD,"border":f"1px solid {BORDER}",
                      "borderRadius":"8px","marginBottom":"3px"}),
            dcc.Graph(id="chart-tes", clear_on_unhover=False,
                config={
    "displaylogo": False,
    "scrollZoom": True,
    "responsive": True,
    "displayModeBar": "hover",
    "modeBarButtons": [["toImage", "zoomIn2d", "resetScale2d"]],
},
                style={"marginBottom":"4px"}),

            html.Div([
                html.Div("EVOLUCIÓN DEL ICOLCAP",
                         style={"fontSize":"19px","fontWeight":"900","color":TEXT,
                                "textAlign":"center","letterSpacing":"1.5px"}),
            ], style={"padding":"8px 14px","background":BG_CARD,"border":f"1px solid {BORDER}",
                      "borderRadius":"8px","marginBottom":"3px"}),
            dcc.Graph(id="chart-bolsa", clear_on_unhover=False,
                config={
    "displaylogo": False,
    "scrollZoom": True,
    "responsive": True,
    "displayModeBar": "hover",
    "modeBarButtons": [["toImage", "zoomIn2d", "resetScale2d"]],
}),

        ], style={"width":"72%","background":BG_PANEL,
                  "border":f"1px solid {BORDER}","borderRadius":"12px","padding":"10px"}),

        # ── PANEL DERECHO ────────────────────────────────
        html.Div([
            html.Div([
                html.Div("CURVA DE RENDIMIENTOS TES",
                         style={"fontSize":"19px","fontWeight":"900","color":TEXT,
                                "textAlign":"center","letterSpacing":"1.5px"}),
                html.Div("Tasas soberanas · hover para explorar · clic para fijar",
                         style={"fontSize":"11px","color":MUTED,"textAlign":"center"}),
            ], style={"padding":"8px 14px","background":BG_CARD,"border":f"1px solid {BORDER}",
                      "borderRadius":"8px","marginBottom":"8px"}),

            # Controles ocultos necesarios para callbacks
            html.Div([
                html.Button("", id="btn-soltar", n_clicks=0),
                html.Div(id="fecha-activa"),
            ], style={"display":"none"}),

            # Leyenda TES
            html.Div([
                *[html.Span([
                    html.Span("━━", style={"color":c,"marginRight":"4px","fontWeight":"900"}),
                    html.Span(lbl, style={"fontSize":"9px","color":MUTED}),
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
            html.Div("Valores en la fecha activa",
                     style={"fontSize":"10px","color":MUTED,"marginBottom":"6px"}),
            html.Div(id="curve-metrics",
                     style={"display":"flex","gap":"5px","flexWrap":"wrap"}),

            html.Hr(style={"borderColor":BORDER,"margin":"8px 0"}),

        ], style={"width":"28%","background":BG_PANEL,
                  "border":f"1px solid {BORDER}","borderRadius":"12px","padding":"14px",
                  "display":"flex","flexDirection":"column",
                  "overflowY":"auto","maxHeight":"1060px"}),

    ], style={"display":"flex","gap":"12px","alignItems":"flex-start"}),

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


# ── Callbacks individuales de cada panel ─────────────────
@app.callback(
    Output("chart-bolsa","figure"),
    Input("time-window","value"),
    Input("xrange-store","data"),
    Input("sync-panels","value"),
)
def upd_bolsa(window, xrd, synced):
    if ctx.triggered_id == "xrange-store" and (xrd or {}).get("range") and "bolsa" not in (synced or []):
        return no_update
    dff = filter_window(df_daily, window)
    xr  = (xrd or {}).get("range") if "bolsa" in (synced or []) else None
    return make_fig_bolsa(dff, xr)

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
    dff = filter_window(df_daily, window)
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
    State("fecha-fijada", "data"),
)
def update_curve(*args):
    n = len(ALL_CHARTS)
    click_list = args[:n]
    hover_list = args[n:2*n]
    window, active_tenors, fecha_fijada = args[2*n], args[2*n+1], args[2*n+2]

    dff     = filter_window(df_daily, window)
    trigger = ctx.triggered_id

    click_map = {cid: click_list[i] for i, cid in enumerate(ALL_CHARTS)}
    hover_map = {cid: hover_list[i]  for i, cid in enumerate(ALL_CHARTS)}

    if trigger in ALL_CHARTS and click_map.get(trigger):
        row = get_hover_row(click_map[trigger], dff)
        nueva_fecha = str(row["fecha"])
    elif fecha_fijada and trigger not in ALL_CHARTS:
        row = nearest_row(dff, fecha_fijada) or dff.iloc[-1]
        nueva_fecha = fecha_fijada
    elif trigger in ALL_CHARTS:
        row = get_hover_row(hover_map.get(trigger), dff)
        nueva_fecha = None
    else:
        row = dff.iloc[-1]
        nueva_fecha = None

    # Tarjetas de métricas
    col_map = {"1A":"tes_pesos_1y","5A":"tes_pesos_5y","10A":"tes_pesos_10y"}
    desc    = {"1A":"Corto plazo","5A":"Medio plazo","10A":"Largo plazo"}
    cards   = []
    for key in ["1A","5A","10A"]:
        if key in active_tenors:
            cards.append(metric_card(f"TES {key}",
                f"{float(row[col_map[key]]):.2f}%", TENOR_COLORS[col_map[key]], desc[key]))
    if "1A" in active_tenors and "10A" in active_tenors:
        sp = float(row["tes_pesos_10y"]) - float(row["tes_pesos_1y"])
        st = "Normal" if sp > 0.3 else ("Invertida" if sp < 0 else "Plana")
        co = C_AZUL if sp > 0.3 else (C_ROJO if sp < 0 else C_AMARILLO)
        cards.append(metric_card("Spread 10A-1A", f"{sp:+.2f}pp", co, st))

    cards.append(metric_card("ICOLCAP", f"{float(row['close']):,.2f}", C_BOLSA, "puntos"))
    if pd.notna(row.get("inflacion_mensual")):
        cards.append(metric_card("Inflación mensual",
            f"{float(row['inflacion_mensual']):.2f}%", C_INF_M, mes_es(row["fecha"])))
    if pd.notna(row.get("inflacion_anual")):
        cards.append(metric_card("Inflación anual 12M",
            f"{float(row['inflacion_anual']):.2f}%", C_INF_A, "acumulada"))
    # PIB más cercano
    pib_row = nearest_row(df_pib, row["fecha"])
    if pib_row is not None and pd.notna(pib_row.get("pib_crecimiento_yoy")):
        cards.append(metric_card("PIB crecimiento",
            f"{float(pib_row['pib_crecimiento_yoy']):.2f}%", C_PIB,
            str(pib_row.get("trimestre",""))))

    label_f = (f"📌 Fijado: {fecha_es(row['fecha'])}" if nueva_fecha
               else f"👁 Explorando: {fecha_es(row['fecha'])}")
    return make_curve_fig(row, active_tenors), label_f, cards, nueva_fecha


@app.callback(
    Output("fecha-fijada","data", allow_duplicate=True),
    Input("btn-soltar","n_clicks"),
    prevent_initial_call=True,
)
def soltar_fecha(n):
    return None


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
)
def update_detail(variable, window, active_tenors, layers):
    dff = filter_window(df_daily, window or "1A")
    if variable == "bolsa":
        return make_fig_bolsa(dff)
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