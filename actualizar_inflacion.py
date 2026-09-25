"""
actualizar_inflacion.py
Actualiza inflacion_clean.csv con datos del IPC desde el Banco de la Republica.

Fuente: API publica de BanRep (graficador de series estadisticas)
  Serie 15000: Indice de Precios al Consumidor (IPC) - Mensual

A partir del indice IPC se calculan:
  inflacion_mensual = variacion porcentual mensual (mes a mes)
  inflacion_anual   = variacion porcentual anual  (mismo mes anho anterior)

Uso:
  python actualizar_inflacion.py           # Agrega solo meses nuevos
  python actualizar_inflacion.py --estado  # Muestra resumen actual
"""

import os, sys, argparse, datetime
import io
import re
from pathlib import Path
from urllib.parse import urljoin
import requests
import pandas as pd
import truststore
from bs4 import BeautifulSoup
from openpyxl import load_workbook

truststore.inject_into_ssl()

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
CSV_INF   = os.path.join(BASE_DIR, "inflacion_clean.csv")

API_BASE  = (
    "https://suameca.banrep.gov.co"
    "/graficador-series/rest/graficadorService"
    "/consultaSerieParaGraficar"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Accept": "application/json",
    "Referer": "https://suameca.banrep.gov.co/graficador-series/",
}

# ID de la serie IPC total en BanRep
ID_IPC = 15000
DANE_IPC_PAGE = (
    "https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/"
    "indice-de-precios-al-consumidor-ipc/ipc-informacion-tecnica"
)
MESES_ARCHIVO = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
                 "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def descargar_ipc() -> pd.DataFrame:
    """
    Descarga el indice IPC total de BanRep y calcula variaciones mensuales y anuales.
    Retorna DataFrame con columnas: fecha, inflacion_mensual, inflacion_anual
    """
    url = f"{API_BASE}?idSerie={ID_IPC}"
    print(f"Descargando IPC de BanRep...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        payload = r.json()[0]
        if "ndice de Precios al Consumidor" not in payload.get("nombre", ""):
            raise ValueError("La serie BanRep ya no corresponde al IPC")
        data = payload["data"]
    except Exception as e:
        print(f"ERROR al descargar: {e}")
        return pd.DataFrame()

    filas = []
    for punto in data:
        ts_ms, valor = punto[0], punto[1]
        dt = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=ts_ms / 1000.0)
        # Normalizar al primer dia del mes (igual que el CSV)
        fecha = pd.Timestamp(dt.year, dt.month, 1)
        if valor is not None and valor > 0 and fecha <= pd.Timestamp.today().normalize():
            filas.append({"fecha": fecha, "ipc": valor})

    df = (pd.DataFrame(filas)
            .sort_values("fecha")
            .drop_duplicates("fecha")
            .reset_index(drop=True))
    if not df["fecha"].equals(pd.Series(pd.date_range(df["fecha"].min(), df["fecha"].max(), freq="MS"))):
        raise ValueError("Huecos mensuales en la serie IPC")

    # Calcular variaciones
    df["inflacion_mensual"] = (df["ipc"].pct_change(1)  * 100).round(2)
    df["inflacion_anual"]   = (df["ipc"].pct_change(12) * 100).round(2)

    ultimo = df["fecha"].iloc[-1]
    print(f"OK - {len(df)} meses descargados ({df['fecha'].iloc[0].date()} -> {ultimo.date()})")
    return df[["fecha", "inflacion_mensual", "inflacion_anual"]]


def variacion_publicada_dane():
    response = requests.get(DANE_IPC_PAGE, timeout=40)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    matches = []
    monthly_matches = []
    for a in soup.select("a[href]"):
        match = re.search(r"/anex-IPC-([a-z]{3})(20\d{2})\.xlsx$", a["href"], re.I)
        if match:
            matches.append((a["href"], match))
        if re.search(r"/anex-IPC-Variacion-[a-z]{3}20\d{2}\.xlsx$", a["href"], re.I):
            monthly_matches.append(a["href"])
    if len(matches) != 1:
        raise ValueError(f"Anexo IPC DANE vigente ambiguo: {len(matches)}")
    if len(monthly_matches) != 1:
        raise ValueError(f"Historia mensual IPC DANE ambigua: {len(monthly_matches)}")
    href, match = matches[0]
    anchor = next(a for a in soup.select("a[href]") if a["href"] == href)
    publication_text = anchor.find_parent("tr").get_text(" ", strip=True)
    publication_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", publication_text)
    if publication_match is None:
        raise ValueError("Fecha de publicacion IPC DANE ausente")
    publication = pd.to_datetime(publication_match.group(1), format="%d/%m/%Y")
    url = urljoin(DANE_IPC_PAGE, href)
    year = int(match.group(2))
    month = MESES_ARCHIVO[match.group(1).lower()]
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    wb = load_workbook(io.BytesIO(response.content), read_only=True, data_only=True)
    try:
        rows = list(wb["1"].values)
        candidates = [r for r in rows if str(r[0]).strip() == str(year)
                      and isinstance(r[1], (int, float))
                      and isinstance(r[3], (int, float))]
        if len(candidates) != 1:
            raise ValueError("Fila total nacional IPC no identificada")
        row = candidates[0]
        latest = (pd.Timestamp(year, month, 1), round(float(row[1]), 2),
                  round(float(row[3]), 2), url)
    finally:
        wb.close()
    monthly_url = urljoin(DANE_IPC_PAGE, monthly_matches[0])
    response = requests.get(monthly_url, timeout=60)
    response.raise_for_status()
    wb = load_workbook(io.BytesIO(response.content), read_only=True, data_only=True)
    try:
        rows = list(wb["VarNal"].values)
        if str(rows[6][0]).strip() != "Mes":
            raise ValueError("Estructura historia IPC DANE cambio")
        monthly = {}
        for col, candidate_year in enumerate(rows[6][1:], start=1):
            if not isinstance(candidate_year, int):
                continue
            for m in range(1, 13):
                value = rows[6 + m][col]
                if isinstance(value, (int, float)):
                    monthly[pd.Timestamp(candidate_year, m, 1)] = round(float(value), 2)
        if len(monthly) < 200:
            raise ValueError("Historia mensual IPC DANE incompleta")
        return (*latest, monthly, monthly_url, publication)
    finally:
        wb.close()


def actualizar_inflacion():
    """
    Descarga toda la historia para incorporar revisiones oficiales.
    """
    df_exist = pd.read_csv(CSV_INF, parse_dates=["fecha"])
    ultimo_mes = df_exist["fecha"].max()
    print(f"CSV actual: {len(df_exist)} meses, ultimo: {ultimo_mes.date()}")

    df_banrep = descargar_ipc()
    if df_banrep.empty:
        return

    if df_banrep.empty or df_banrep["fecha"].max() < ultimo_mes:
        raise ValueError("IPC API vacio o mas antiguo que el CSV")
    df_total = df_banrep[df_banrep["fecha"] >= df_exist["fecha"].min()].dropna().reset_index(drop=True)
    official_date, monthly, annual, dane_url, monthly_history, monthly_url, publication = variacion_publicada_dane()
    if official_date != df_total["fecha"].max():
        raise ValueError("IPC BanRep y DANE tienen ultimo mes distinto")
    idx = df_total.index[df_total["fecha"] == official_date][0]
    if abs(df_total.loc[idx, "inflacion_mensual"] - monthly) > 0.05 or abs(
        df_total.loc[idx, "inflacion_anual"] - annual
    ) > 0.05:
        raise ValueError("IPC BanRep y variaciones oficiales DANE no concuerdan")
    df_total["fuente_mensual"] = "BanRep_IPC_calculada_2_decimales"
    for fecha, value in monthly_history.items():
        mask = df_total["fecha"] == fecha
        if mask.any():
            if abs(df_total.loc[mask, "inflacion_mensual"].iloc[0] - value) > 0.10:
                raise ValueError(f"Variacion mensual DANE/BanRep incompatible: {fecha.date()}")
            df_total.loc[mask, "inflacion_mensual"] = value
            df_total.loc[mask, "fuente_mensual"] = "DANE_variacion_reportada"
    df_total.loc[idx, ["inflacion_mensual", "inflacion_anual"]] = [monthly, annual]
    df_total["fuente_anual"] = "BanRep_IPC_calculada_2_decimales"
    df_total.loc[idx, "fuente_anual"] = "DANE_variacion_reportada"
    df_total["fuente_oficial_ultimo_mes"] = dane_url
    df_total["fuente_historia_mensual"] = monthly_url
    df_total["fecha_publicacion_vintage"] = "no_disponible"
    df_total.loc[idx, "fecha_publicacion_vintage"] = publication.strftime("%Y-%m-%d")
    if df_total.empty or len(df_total) < len(df_exist):
        raise ValueError("IPC API incompleto")
    csv_text = df_total.to_csv(index=False, lineterminator="\n")
    if Path(CSV_INF).read_text(encoding="utf-8") != csv_text:
        with Path(CSV_INF).open("w", encoding="utf-8", newline="") as target:
            target.write(csv_text)
        print(f"OK - IPC actualizado: {len(df_total)} meses hasta {df_total['fecha'].max().date()}")
    else:
        print("Sin cambios de IPC")


def mostrar_estado():
    df = pd.read_csv(CSV_INF, parse_dates=["fecha"])
    print("\n" + "=" * 55)
    print("  Estado actual Inflacion Colombia")
    print("=" * 55)
    print(f"  Total meses    : {len(df)}")
    print(f"  Primer dato    : {df['fecha'].iloc[0].date()}")
    print(f"  Ultimo dato    : {df['fecha'].iloc[-1].date()}")
    print(f"  Inf. mensual   : {df['inflacion_mensual'].iloc[-1]:.2f}%")
    print(f"  Inf. anual     : {df['inflacion_anual'].iloc[-1]:.2f}%")
    print("=" * 55)
    print("\nUltimos 6 meses:")
    print(df[["fecha", "inflacion_mensual", "inflacion_anual"]].tail(6).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Actualiza inflacion_clean.csv con datos IPC de BanRep",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Ejemplos:
  Actualizar (agrega solo meses nuevos):
    python actualizar_inflacion.py

  Ver estado actual:
    python actualizar_inflacion.py --estado
        """
    )
    parser.add_argument("--estado", action="store_true", help="Mostrar resumen actual")
    args = parser.parse_args()

    print("\n" + "=" * 55)
    print("  Actualizador Inflacion Colombia - BanRep")
    print("=" * 55)

    if args.estado:
        mostrar_estado()
    else:
        actualizar_inflacion()
        mostrar_estado()

    print()
