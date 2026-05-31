"""
actualizar_tes.py
Actualiza tasas_interes_clean.csv con las tasas TES diarias del Banco de la Republica.

Fuente: API publica de BanRep (graficador de series estadisticas)
Series descargadas:
  TES pesos 1 anho  (ID 15272)
  TES pesos 5 anhos (ID 15273)
  TES pesos 10 anhos(ID 15274)
  TES UVR 1 anho    (ID 15275)
  TES UVR 5 anhos   (ID 15276)
  TES UVR 10 anhos  (ID 15277)

Uso:
  python actualizar_tes.py           # Agrega solo fechas nuevas
  python actualizar_tes.py --estado  # Muestra resumen actual
"""

import os, sys, argparse, datetime
import requests
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_TES  = os.path.join(BASE_DIR, "tasas_interes_clean.csv")

API_BASE = (
    "https://suameca.banrep.gov.co"
    "/graficador-series/rest/graficadorService"
    "/consultaSerieParaGraficar"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Accept": "application/json",
    "Referer": "https://suameca.banrep.gov.co/graficador-series/",
}

# ID de cada serie en BanRep
SERIES = {
    "tes_pesos_1y":  15272,
    "tes_pesos_5y":  15273,
    "tes_pesos_10y": 15274,
    "tes_uvr_1y":    15275,
    "tes_uvr_5y":    15276,
    "tes_uvr_10y":   15277,
}


def descargar_serie(nombre_col: str, id_serie: int) -> pd.DataFrame:
    """
    Descarga toda la serie historica de BanRep y la retorna como DataFrame
    con columnas: fecha, <nombre_col>
    """
    url = f"{API_BASE}?idSerie={id_serie}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()[0]["data"]  # lista de [timestamp_ms, valor]

        filas = []
        for ts_ms, valor in data:
            # Los timestamps son medianoche hora Colombia (UTC-5)
            # Convertir a fecha local: ts_ms / 1000 da segundos UTC
            fecha = datetime.datetime.fromtimestamp(
                ts_ms / 1000, tz=datetime.timezone.utc
            ).date()
            filas.append({"fecha": fecha, "valor": valor})

        df = pd.DataFrame(filas)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df = df.rename(columns={"valor": nombre_col})
        return df.sort_values("fecha").reset_index(drop=True)

    except Exception as e:
        print(f"  ERROR descargando {nombre_col} (ID {id_serie}): {e}")
        return pd.DataFrame(columns=["fecha", nombre_col])


def actualizar_tes():
    """
    Descarga las 6 series de BanRep y agrega al CSV las fechas
    que no existan todavia.
    """
    # Leer CSV existente
    df_exist = pd.read_csv(CSV_TES, parse_dates=["fecha"])
    ultima_fecha = df_exist["fecha"].max()
    print(f"CSV actual: {len(df_exist)} filas, ultimo dia: {ultima_fecha.date()}")

    # Descargar cada serie y quedarse solo con fechas nuevas
    print("\nDescargando series de BanRep...")
    dfs_nuevos = {}
    for col, id_serie in SERIES.items():
        print(f"  {col} (ID {id_serie})...", end=" ")
        df_serie = descargar_serie(col, id_serie)
        if df_serie.empty:
            continue
        ultimo_api = df_serie["fecha"].max()
        df_nuevos = df_serie[df_serie["fecha"] > ultima_fecha].copy()
        print(f"OK ({len(df_serie)} puntos hasta {ultimo_api.date()}, {len(df_nuevos)} nuevos)")
        dfs_nuevos[col] = df_nuevos

    if not dfs_nuevos:
        print("\nSin datos nuevos para agregar.")
        return

    # Merge de las 6 series nuevas por fecha
    cols = list(SERIES.keys())
    df_merge = dfs_nuevos.get(cols[0], pd.DataFrame(columns=["fecha"]))
    for col in cols[1:]:
        if col in dfs_nuevos:
            df_merge = pd.merge(df_merge, dfs_nuevos[col], on="fecha", how="outer")
        else:
            df_merge[col] = None

    df_merge = df_merge.sort_values("fecha").reset_index(drop=True)

    if df_merge.empty:
        print("\nSin datos nuevos para agregar.")
        return

    # Concatenar con el CSV existente
    df_total = (
        pd.concat([df_exist, df_merge])
        .drop_duplicates("fecha")
        .sort_values("fecha")
        .reset_index(drop=True)
    )

    df_total.to_csv(CSV_TES, index=False)
    print(f"\nOK - {len(df_merge)} dias nuevos agregados.")
    print(f"     CSV actualizado: {len(df_total)} filas en total -> {CSV_TES}")


def mostrar_estado():
    df = pd.read_csv(CSV_TES, parse_dates=["fecha"])
    print("\n" + "=" * 55)
    print("  Estado actual TES Colombia")
    print("=" * 55)
    print(f"  Total filas    : {len(df)}")
    print(f"  Primer dato    : {df['fecha'].iloc[0].date()}")
    print(f"  Ultimo dato    : {df['fecha'].iloc[-1].date()}")
    print("=" * 55)
    print("\nUltimos 5 dias:")
    cols_display = ["fecha", "tes_pesos_1y", "tes_pesos_5y", "tes_pesos_10y",
                    "tes_uvr_1y", "tes_uvr_5y", "tes_uvr_10y"]
    print(df[cols_display].tail(5).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Actualiza tasas_interes_clean.csv con datos TES de BanRep",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Ejemplos:
  Actualizar (solo agrega fechas nuevas):
    python actualizar_tes.py

  Ver estado actual:
    python actualizar_tes.py --estado
        """
    )
    parser.add_argument("--estado", action="store_true", help="Mostrar resumen actual")
    args = parser.parse_args()

    print("\n" + "=" * 55)
    print("  Actualizador TES Colombia - BanRep")
    print("=" * 55)

    if args.estado:
        mostrar_estado()
    else:
        actualizar_tes()
        mostrar_estado()

    print()
