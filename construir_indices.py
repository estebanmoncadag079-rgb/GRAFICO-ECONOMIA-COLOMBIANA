"""
construir_indices.py
AVISO: la reconstruccion diaria descrita abajo es historica y ya no se publica.
Al ejecutarse se genera la tabla mensual experimental; el dashboard usa la
serie COLCAP oficial de BanRep.
Reconstruye los indices sintetico y grandes desde el origen usando precios
mensuales limpios de ACCIONES_HISTORICAS_ICOLCAP.xlsx.

DISEÑO:
  - ICOLCAP      : de icolcap_referencia.csv + retornos BlackRock NAV
  - Sintetico    : retorno mensual igual ponderado, canasta oficial BVC,
                   sin relleno de huecos (accion con dato faltante = excluida ese mes)
  - Grandes      : igual ponderado solo sobre las 7 empresas grandes
  - Distribucion : nivel mensual -> valores diarios usando forma del ICOLCAP

Fuentes:
  precios_icolcap_limpios.csv  : precios mensuales limpios (splits ajustados)
  Canasta_Historica_ICAP.xls   : composicion historica ICOLCAP 2008-2021 (BVC)
  icolcap_composicion.csv      : composicion actual (para meses post-2021)
  icolcap_referencia.csv       : niveles icolcap_real correctos
  datos_colombia_clean.csv     : NAV BlackRock (extension ICOLCAP diario)
"""

import os, re, sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Rutas ────────────────────────────────────────────────────
DIR_GRAF      = Path(__file__).resolve().parent
CSV_PRECIOS   = DIR_GRAF / "precios_icolcap_limpios.csv"
CSV_BLACKROCK = DIR_GRAF / "datos_colombia_clean.csv"
CSV_REF_IC    = DIR_GRAF / "icolcap_referencia.csv"
CSV_INDICES   = DIR_GRAF / "indices_colombia.csv"
XLS_CANASTAS  = DIR_GRAF / "Canasta_Historica_ICAP.xls"
CSV_COMPO     = DIR_GRAF / "icolcap_composicion.csv"

GRANDES = {"ECOPETROL", "PFBCOLOM", "GRUPOSURA", "GRUPOARGOS",
           "PFAVAL", "ISA", "NUTRESA"}

MESES_ES_FULL = {
    "Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12,
    "Ene.": 1, "Feb.": 2, "Mar.": 3, "Abr.": 4, "May.": 5, "Jun.": 6,
    "Jul.": 7, "Ago.": 8, "Sep.": 9, "Oct.": 10, "Nov.": 11, "Dic.": 12,
}

TRIMESTRE_MESES = {
    "I":   [2, 3, 4],
    "II":  [5, 6, 7],
    "III": [8, 9, 10],
    "IV":  [11, 12, 1],
}

# Nombres historicos BVC -> ticker en precios_icolcap_limpios.csv
ALIAS_TICKERS = {
    "SURAMINV":   "GRUPOSURA",
    "INVERARGOS": "GRUPOARGOS",
    "CHOCOLATES": "NUTRESA",
    "EEB":        "GEB",
    "BCOLOMBIA":  "PFBCOLOM",   # proxy ordinaria -> preferencial
    "BNA":        None,
    "PFBCREDITO": None,
    "COLINVERS":  None,
    "CNEC":       None,
    "CLH":        None,
    "PFCORFICOL": "PFCORFICOL",
    "CONCONCRET": "CONCONCRET",
    "PFGRUPOARG": "PFGRUPOARG",
    "PFGRUPSURA": "PFGRUPSURA",
}

MAX_RET_MENSUAL = 1.0   # winsorization ±100%


# ── Precios mensuales limpios ─────────────────────────────────

def cargar_precios() -> pd.DataFrame:
    """Carga precios_icolcap_limpios.csv. Sin relleno de huecos."""
    df = pd.read_csv(CSV_PRECIOS, parse_dates=["fecha"], index_col="fecha")
    df = df.sort_index()
    return df


# ── Canasta historica ICOLCAP ─────────────────────────────────

def _resolver_ticker(t: str, disponibles: set) -> str | None:
    if t in ALIAS_TICKERS:
        return ALIAS_TICKERS[t]
    return t if t in disponibles else None


def _parsear_periodo(texto: str, anho: int) -> list:
    t = re.sub(r'\s+', ' ', texto.strip())
    m = re.match(r'^(I{1,3}|IV)\s*[-–]?\s*(\d{4})?$', t)
    if m:
        q  = m.group(1)
        yr = int(m.group(2)) if m.group(2) else anho
        return [(yr + (1 if q == "IV" and mes == 1 else 0), mes)
                for mes in TRIMESTRE_MESES.get(q, [])]
    m = re.match(r'^(\w+\.?)\s*(?:(\d{4})\s*)?[-–]\s*(\w+\.?)\s*(\d{4})?$', t)
    if m:
        ms_ini = m.group(1).rstrip('.')
        yr_ini = int(m.group(2)) if m.group(2) else anho
        ms_fin = m.group(3).rstrip('.')
        yr_fin = int(m.group(4)) if m.group(4) else anho
        n_ini  = MESES_ES_FULL.get(ms_ini + '.') or MESES_ES_FULL.get(ms_ini)
        n_fin  = MESES_ES_FULL.get(ms_fin + '.') or MESES_ES_FULL.get(ms_fin)
        if n_ini and n_fin:
            result, y, mc = [], yr_ini, n_ini
            for _ in range(25):
                result.append((y, mc))
                if y == yr_fin and mc == n_fin:
                    break
                mc += 1
                if mc > 12:
                    mc, y = 1, y + 1
            return result
    return []


def cargar_canastas(disponibles: set) -> dict:
    """Retorna {pd.Timestamp(year,month,1): frozenset_of_tickers}."""
    if not XLS_CANASTAS.exists():
        print("  WARN: XLS canastas no encontrado.")
        return {}

    import xlrd
    wb   = xlrd.open_workbook(str(XLS_CANASTAS))
    mapa = {}

    for sheet_name in wb.sheet_names():
        sh = wb.sheet_by_name(sheet_name)

        if sheet_name == "COLCAP":
            tickers = set()
            for r in range(2, sh.nrows):
                if str(sh.cell_value(r, 1)).strip().upper() == "TOTAL":
                    break
                t = str(sh.cell_value(r, 3)).strip() if sh.ncols > 3 else ""
                if re.match(r'^[A-Z][A-Z0-9]{1,14}$', t):
                    res = _resolver_ticker(t, disponibles)
                    if res:
                        tickers.add(res)
            tks = frozenset(tickers)
            for mes in [8, 9, 10]:
                mapa[(2021, mes)] = tks
            continue

        if not sheet_name.isdigit():
            continue
        anho = int(sheet_name)
        val_r0 = str(sh.cell_value(0, 0)).strip()
        fmt_antiguo = bool(re.search(r'(I{1,3}|IV)\s*[-–]\s*\d{4}', val_r0))
        row_per  = 0 if fmt_antiguo else 1
        row_dat  = 2 if fmt_antiguo else 3

        for i in range(sh.ncols // 2):
            col_t = i * 2
            per_raw = str(sh.cell_value(row_per, col_t)).strip()
            if not per_raw:
                continue
            if fmt_antiguo:
                m = re.search(r'(I{1,3}|IV)\s*[-–]\s*(\d{4})', per_raw)
                per_raw = f"{m.group(1)} - {m.group(2)}" if m else ""
            meses = _parsear_periodo(per_raw, anho)
            if not meses:
                continue
            tickers = set()
            for r in range(row_dat, sh.nrows):
                t = str(sh.cell_value(r, col_t)).strip()
                if not t or re.match(r'TOTAL', t, re.I):
                    break
                if re.match(r'^[A-Z][A-Z0-9]{1,14}$', t):
                    res = _resolver_ticker(t, disponibles)
                    if res:
                        tickers.add(res)
            tks = frozenset(tickers)
            for (y, mc) in meses:
                mapa[(y, mc)] = tks

    result = {pd.Timestamp(y, mc, 1): tks for (y, mc), tks in mapa.items()}

    # Composicion actual para post-Oct 2021
    tickers_act = frozenset()
    if CSV_COMPO.exists():
        tmp = set()
        for t in pd.read_csv(CSV_COMPO)["ticker"]:
            res = _resolver_ticker(str(t).strip(), disponibles)
            if res:
                tmp.add(res)
        tickers_act = frozenset(tmp)

    # Rellenar huecos propagando hacia adelante + post-2021
    fechas_sorted = sorted(result)
    fecha_min   = fechas_sorted[0] if fechas_sorted else pd.Timestamp("2008-02-01")
    fecha_limite = pd.Timestamp.now().normalize().replace(day=1) + pd.DateOffset(months=2)
    ultima = result.get(fecha_min, tickers_act)
    fecha  = fecha_min
    while fecha <= fecha_limite:
        if fecha in result:
            ultima = result[fecha]
        else:
            result[fecha] = ultima if fecha <= pd.Timestamp("2021-10-01") else tickers_act
        fecha += pd.DateOffset(months=1)

    fs = sorted(result)
    print(f"  Canastas: {len(result)} meses "
          f"({fs[0].strftime('%Y-%m')} -> {fs[-1].strftime('%Y-%m')})")
    return result


# ── ICOLCAP: carga y extension ────────────────────────────────

def cargar_icolcap() -> pd.Series:
    ref = (pd.read_csv(CSV_REF_IC, parse_dates=["fecha"])
             .set_index("fecha")["icolcap_real"]
             .sort_index())
    nav = (pd.read_csv(CSV_BLACKROCK, parse_dates=["fecha"])
             .set_index("fecha")["close"]
             .sort_index())
    nav_ret = nav.pct_change()
    fechas_nuevas = nav.index[nav.index > ref.index[-1]]
    if len(fechas_nuevas) > 0:
        val = ref.iloc[-1]
        ext = {}
        for fecha in fechas_nuevas:
            r = nav_ret.get(fecha, np.nan)
            if pd.isna(r) or abs(r) > 0.20:
                r = 0.0
            val = val * (1 + r)
            ext[fecha] = val
        ref = pd.concat([ref, pd.Series(ext)]).sort_index()
        print(f"  ICOLCAP: {len(fechas_nuevas)} dias nuevos (BlackRock NAV)")
    return ref


# ── Retorno mensual igual ponderado ──────────────────────────

def retorno_mensual(df: pd.DataFrame, mes: pd.Timestamp,
                    canasta: frozenset) -> tuple[float, float, int, int]:
    """
    Retorna (ret_sintetico, ret_grandes, n_sin, n_gr).
    Solo usa acciones con precio en AMBOS meses (actual y anterior).
    Huecos = excluidos ese mes, sin relleno.
    """
    mes_ant = mes - pd.DateOffset(months=1)
    if mes not in df.index or mes_ant not in df.index:
        return 0.0, 0.0, 0, 0

    p_now = df.loc[mes]
    p_ant = df.loc[mes_ant]
    ret   = ((p_now - p_ant) / p_ant).clip(-MAX_RET_MENSUAL, MAX_RET_MENSUAL)

    cols_sin = [c for c in df.columns if c in canasta]
    ret_sin  = ret[cols_sin].dropna()
    cols_gr  = [c for c in cols_sin if c in GRANDES]
    ret_gr   = ret[cols_gr].dropna()

    r_sin = float(ret_sin.mean()) if len(ret_sin) > 0 else 0.0
    r_gr  = float(ret_gr.mean())  if len(ret_gr)  > 0 else 0.0
    return r_sin, r_gr, len(ret_sin), len(ret_gr)


# ── Interpolacion mensual -> diaria ──────────────────────────

def interpolar_mes(I_start: float, I_end: float, ic_mes: pd.Series) -> dict:
    """
    Distribuye I_start -> I_end en valores diarios con la forma del ICOLCAP.
    Fallback lineal si hay discontinuidad de escala.
    """
    if ic_mes.empty:
        return {}
    p0, pN, n = ic_mes.iloc[0], ic_mes.iloc[-1], len(ic_mes)
    ratio = pN / p0 if p0 > 0 else 1.0
    lineal = ratio > 20 or ratio < 0.05 or np.isclose(p0, pN)
    result = {}
    for i, (fecha, pv) in enumerate(ic_mes.items()):
        if n == 1:
            w = 1.0
        elif lineal:
            w = i / (n - 1)
        else:
            try:
                w = np.log(pv / p0) / np.log(pN / p0)
                w = max(0.0, min(1.0, w))
            except Exception:
                w = i / (n - 1)
        if I_start > 0 and I_end > 0:
            result[fecha] = I_start * ((I_end / I_start) ** w)
    return result


# ── Main ─────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  Construyendo indices Colombia")
    print("=" * 60)

    # 1. ICOLCAP diario
    print("\n--- ICOLCAP ---")
    icolcap = cargar_icolcap()
    print(f"  {len(icolcap)} dias: {icolcap.index[0].date()} -> {icolcap.index[-1].date()}")
    ic_base0 = icolcap.iloc[0]  # valor de referencia para icolcap_base100

    # 2. Precios mensuales limpios
    print("\n--- Precios mensuales ---")
    df_p = cargar_precios()
    print(f"  {len(df_p)} meses x {len(df_p.columns)} tickers  "
          f"({df_p.index[0].date()} -> {df_p.index[-1].date()})")

    # 3. Canastas historicas
    print("\n--- Canastas historicas ---")
    disponibles = frozenset(df_p.columns)
    canastas = cargar_canastas(disponibles)

    # 4. Reconstruir indice mensual desde Jan-2009
    print("\n--- Calculando retornos mensuales ---")
    meses = sorted(df_p.index)
    nivel_sin = 100.0
    nivel_gr  = 100.0

    niveles_sin = {}   # {mes: nivel_fin_de_mes}
    niveles_gr  = {}

    for mes in meses:
        if mes < pd.Timestamp("2009-02-01"):
            continue   # Jan-2009 es el mes base, empezamos a calcular desde Feb
        canasta = canastas.get(mes, frozenset())
        r_sin, r_gr, n_sin, n_gr = retorno_mensual(df_p, mes, canasta)
        nivel_sin = nivel_sin * (1 + r_sin)
        nivel_gr  = nivel_gr  * (1 + r_gr)
        niveles_sin[mes] = nivel_sin
        niveles_gr[mes]  = nivel_gr

    ultimo_mes = max(niveles_sin)
    print(f"  Meses calculados: {len(niveles_sin)}  "
          f"(hasta {ultimo_mes.strftime('%Y-%m')})")
    print(f"  Ultimo: sin={nivel_sin:.2f}  gr={nivel_gr:.2f}")

    # 5. Distribuir mensual -> diario usando forma del ICOLCAP
    print("\n--- Distribuyendo a diario ---")
    dias_sin = {}
    dias_gr  = {}

    # Nivel de arranque para el primer mes (Feb-2009): base=100
    nivel_sin_prev = 100.0
    nivel_gr_prev  = 100.0

    for mes in sorted(niveles_sin):
        nivel_sin_mes = niveles_sin[mes]
        nivel_gr_mes  = niveles_gr[mes]

        mask   = (icolcap.index.year == mes.year) & (icolcap.index.month == mes.month)
        ic_mes = icolcap[mask]

        dias_sin.update(interpolar_mes(nivel_sin_prev, nivel_sin_mes, ic_mes))
        dias_gr.update(interpolar_mes(nivel_gr_prev,  nivel_gr_mes,  ic_mes))

        nivel_sin_prev = nivel_sin_mes
        nivel_gr_prev  = nivel_gr_mes

    # 6. Construir DataFrame final
    fechas_dia = sorted(dias_sin)
    filas = []
    for fecha in fechas_dia:
        ic_real = icolcap.get(fecha, np.nan)
        filas.append({
            "fecha":             fecha.strftime("%Y-%m-%d"),
            "icolcap_real":      round(ic_real, 4)      if not np.isnan(ic_real) else np.nan,
            "icolcap_base100":   round(ic_real / ic_base0 * 100, 4) if not np.isnan(ic_real) else np.nan,
            "sintetico_base100": round(dias_sin[fecha], 4),
            "grandes_base100":   round(dias_gr[fecha], 4),
        })

    df_out = pd.DataFrame(filas)
    df_out.to_csv(CSV_INDICES, index=False)

    # Resumen
    print("\n" + "=" * 60)
    print("  Resultado final")
    print("=" * 60)
    print(f"  Filas totales : {len(df_out)}")
    print(f"  Periodo       : {df_out.fecha.iloc[0]} -> {df_out.fecha.iloc[-1]}")
    print(f"\n  Ultimo dia:")
    print(f"    icolcap_base100   : {df_out.icolcap_base100.iloc[-1]:.2f}")
    print(f"    sintetico_base100 : {df_out.sintetico_base100.iloc[-1]:.2f}")
    print(f"    grandes_base100   : {df_out.grandes_base100.iloc[-1]:.2f}")

    # Referencia: valor en Feb 2009 (primer mes calculado)
    primer = df_out[df_out.fecha >= "2009-02-01"].iloc[0]
    print(f"\n  Primer dia calculado ({primer.fecha}):")
    print(f"    sintetico : {primer.sintetico_base100:.2f}  (base=100 en Ene-2009)")
    print(f"    grandes   : {primer.grandes_base100:.2f}")
    print(f"\nOK -> {CSV_INDICES}")
    print("=" * 60)


if __name__ == "__main__":
    from construir_tablas_experimentales import main as build_monthly_table
    build_monthly_table()
