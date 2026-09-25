"""Descarga el nivel diario del indice COLCAP publicado por BanRep (serie 6)."""

from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import truststore

truststore.inject_into_ssl()

OUT = Path(__file__).resolve().parent / "colcap_oficial.csv"
API = (
    "https://suameca.banrep.gov.co/graficador-series/rest/graficadorService/"
    "consultaSerieParaGraficar"
)
SERIE = 6
BASE_DATE = pd.Timestamp("2009-02-09")


def fetch(session=None):
    session = session or requests.Session()
    response = session.get(API, params={"idSerie": SERIE}, timeout=40)
    response.raise_for_status()
    payload = response.json()
    if len(payload) != 1 or payload[0].get("id") != SERIE or "COLCAP" not in payload[0].get("nombre", ""):
        raise ValueError("BanRep no devolvio la serie COLCAP esperada")
    rows = []
    for timestamp_ms, value in payload[0]["data"]:
        date = (datetime(1970, 1, 1, tzinfo=timezone.utc)
                + timedelta(milliseconds=timestamp_ms)).date()
        if value is not None and value > 0 and date <= datetime.now().date():
            rows.append((date, float(value)))
    df = pd.DataFrame(rows, columns=["fecha", "colcap_puntos"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.drop_duplicates("fecha").sort_values("fecha").reset_index(drop=True)
    if len(df) < 4000 or BASE_DATE not in set(df["fecha"]):
        raise ValueError("Historia oficial COLCAP incompleta")
    if df["colcap_puntos"].pct_change(fill_method=None).abs().gt(0.25).any():
        raise ValueError("Salto diario COLCAP superior al control de 25%")
    base = float(df.loc[df["fecha"] == BASE_DATE, "colcap_puntos"].iloc[0])
    df["colcap_base100"] = (df["colcap_puntos"] / base * 100).round(6)
    df["fuente"] = "BanRep_serie_6_BVC"
    csv_text = df.to_csv(index=False, float_format="%.6f", lineterminator="\n")
    if OUT.exists():
        old = pd.read_csv(OUT, parse_dates=["fecha"])
        if df["fecha"].max() < old["fecha"].max():
            raise ValueError("API COLCAP mas antigua que la tabla guardada")
        if OUT.read_text(encoding="utf-8") == csv_text:
            print("COLCAP: sin cambios")
            return df
    with OUT.open("w", encoding="utf-8", newline="") as target:
        target.write(csv_text)
    print(f"COLCAP oficial: {len(df)} dias hasta {df['fecha'].max().date()}")
    return df


if __name__ == "__main__":
    fetch()
