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
import requests
import pandas as pd

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
        data = r.json()[0]["data"]  # lista de [timestamp_ms, valor_ipc]
    except Exception as e:
        print(f"ERROR al descargar: {e}")
        return pd.DataFrame()

    filas = []
    for punto in data:
        ts_ms, valor = punto[0], punto[1]
        dt = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=ts_ms / 1000.0)
        # Normalizar al primer dia del mes (igual que el CSV)
        fecha = pd.Timestamp(dt.year, dt.month, 1)
        filas.append({"fecha": fecha, "ipc": valor})

    df = (pd.DataFrame(filas)
            .sort_values("fecha")
            .drop_duplicates("fecha")
            .reset_index(drop=True))

    # Calcular variaciones
    df["inflacion_mensual"] = (df["ipc"].pct_change(1)  * 100).round(2)
    df["inflacion_anual"]   = (df["ipc"].pct_change(12) * 100).round(2)

    ultimo = df["fecha"].iloc[-1]
    print(f"OK - {len(df)} meses descargados ({df['fecha'].iloc[0].date()} -> {ultimo.date()})")
    return df[["fecha", "inflacion_mensual", "inflacion_anual"]]


def actualizar_inflacion():
    """
    Descarga el IPC de BanRep y agrega al CSV los meses que no existan todavia.
    """
    df_exist = pd.read_csv(CSV_INF, parse_dates=["fecha"])
    ultimo_mes = df_exist["fecha"].max()
    print(f"CSV actual: {len(df_exist)} meses, ultimo: {ultimo_mes.date()}")

    df_banrep = descargar_ipc()
    if df_banrep.empty:
        return

    # Solo meses nuevos
    df_nuevos = df_banrep[df_banrep["fecha"] > ultimo_mes].dropna().copy()

    if df_nuevos.empty:
        print("Sin meses nuevos para agregar.")
        return

    print(f"\nMeses nuevos a agregar: {len(df_nuevos)}")
    print(df_nuevos.to_string(index=False))

    df_total = (pd.concat([df_exist, df_nuevos])
                  .drop_duplicates("fecha")
                  .sort_values("fecha")
                  .reset_index(drop=True))

    df_total.to_csv(CSV_INF, index=False)
    print(f"\nOK - CSV actualizado: {len(df_total)} meses en total -> {CSV_INF}")


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
