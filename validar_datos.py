"""Valida las tablas publicadas y genera el estado de cada fuente."""

from pathlib import Path
import sys
import pandas as pd

BASE = Path(__file__).resolve().parent
TODAY = pd.Timestamp.today().normalize()
SOURCES = {
    "PIB real DANE": ("pib_colombia.csv", "trimestral", 130),
    "IPC DANE/BanRep": ("inflacion_clean.csv", "mensual", 45),
    "TES BanRep": ("tasas_interes_clean.csv", "diaria_mercado", 10),
    "COLCAP BanRep/BVC": ("colcap_oficial.csv", "diaria_mercado", 7),
    "Canastas experimentales": ("indices_experimentales_mensuales.csv", "mensual", 100),
}

def isolated_tes_spikes(series):
    previous = series.shift(1)
    following = series.shift(-1)
    return ((series - previous).abs() > 2
            ) & ((series - following).abs() > 2
                 ) & ((previous - following).abs() < 1)


def validate():
    errors, warnings, states, alerts = [], [], [], []
    tables = {}
    for name, (filename, frequency, stale_days) in SOURCES.items():
        path = BASE / filename
        if not path.exists():
            errors.append(f"{filename}: archivo ausente")
            continue
        df = pd.read_csv(path, parse_dates=["fecha"])
        tables[filename] = df
        if df.empty or df["fecha"].isna().any():
            errors.append(f"{filename}: tabla vacia o fechas invalidas")
            continue
        if df["fecha"].duplicated().any() or not df["fecha"].is_monotonic_increasing:
            errors.append(f"{filename}: fechas duplicadas o desordenadas")
        if (df["fecha"] > TODAY).any():
            errors.append(f"{filename}: observaciones futuras")
        visible = df[df["estado"] == "revisable"] if filename == "indices_experimentales_mensuales.csv" else df
        latest = visible["fecha"].max()
        published = latest
        if filename in ("pib_colombia.csv", "inflacion_clean.csv"):
            dates = pd.to_datetime(df["fecha_publicacion_vintage"], format="%Y-%m-%d",
                                   errors="coerce").dropna()
            if dates.empty:
                errors.append(f"{filename}: falta fecha de publicacion")
            else:
                published = dates.max()
        age = (TODAY - published).days
        states.append({"fuente": name, "archivo": filename, "frecuencia": frequency,
                       "ultima_observacion": latest.strftime("%Y-%m-%d"),
                       "ultima_publicacion_o_corte": published.strftime("%Y-%m-%d"),
                       "estado": "rezagado" if age > stale_days else "vigente"})
        if age > stale_days:
            warnings.append(f"{filename}: ultima observacion {latest.date()} ({age} dias)")

    if len(tables) != len(SOURCES):
        return errors, warnings, states, alerts

    pib = tables["pib_colombia.csv"].set_index("fecha")
    if not pib.index.equals(pd.date_range(pib.index.min(), pib.index.max(), freq="QS")):
        errors.append("PIB: faltan trimestres o fechas fuera de trimestre")
    for level, rate, lag in (
        ("pib_real_miles_millones_ref2015", "pib_real_yoy", 4),
        ("pib_real_ajustado_miles_millones_ref2015", "pib_real_qoq_sa", 1),
        ("pib_nominal_billones_cop", "pib_nominal_yoy", 4),
    ):
        expected = pib[level].pct_change(lag, fill_method=None) * 100
        if (expected - pib[rate]).abs().dropna().gt(0.0001).any():
            errors.append(f"PIB: {rate} no coincide con {level}")
    if not pib["fecha_publicacion_vintage"].nunique() == 1:
        errors.append("PIB: vintages mezclados")

    ipc = tables["inflacion_clean.csv"].set_index("fecha")
    if not ipc.index.equals(pd.date_range(ipc.index.min(), ipc.index.max(), freq="MS")):
        errors.append("IPC: faltan meses")
    if ipc[["inflacion_mensual", "inflacion_anual"]].isna().any().any():
        errors.append("IPC: variaciones faltantes")
    if not ipc["inflacion_mensual"].between(-5, 10).all() or not ipc["inflacion_anual"].between(-10, 50).all():
        errors.append("IPC: valores fuera de rango de control")
    if ipc.iloc[-1]["fuente_anual"] != "DANE_variacion_reportada":
        errors.append("IPC: la ultima variacion anual no esta contrastada con DANE")

    tes = tables["tasas_interes_clean.csv"]
    required_tes = ["tes_pesos_1y", "tes_pesos_5y", "tes_pesos_10y"]
    if tes[required_tes].isna().any().any() or not tes[required_tes].apply(
        lambda col: col.between(-5, 40).all()
    ).all():
        errors.append("TES: tasas pesos faltantes o fuera de rango")
    for col in required_tes:
        for _, point in tes.loc[isolated_tes_spikes(tes[col]), ["fecha", col]].iterrows():
            alerts.append({"archivo": "tasas_interes_clean.csv",
                           "fecha": point["fecha"].strftime("%Y-%m-%d"),
                           "variable": col, "valor": float(point[col]),
                           "tipo": "salto_aislado_revertido_mayor_2pp",
                           "accion": "conservado_en_csv_omitido_en_grafico"})
    if alerts:
        warnings.append(f"TES: {len(alerts)} observaciones aisladas sospechosas")

    colcap = tables["colcap_oficial.csv"]
    if (colcap["colcap_puntos"] <= 0).any() or colcap["colcap_puntos"].pct_change(
        fill_method=None
    ).abs().gt(0.25).any():
        errors.append("COLCAP: valor o salto diario invalido")
    base_row = colcap.loc[colcap["fecha"] == pd.Timestamp("2009-02-09"), "colcap_puntos"]
    if len(base_row) != 1 or (
        colcap["colcap_base100"] - colcap["colcap_puntos"] / base_row.iloc[0] * 100
    ).abs().gt(0.0001).any():
        errors.append("COLCAP: base 100 incorrecta")

    experimental = tables["indices_experimentales_mensuales.csv"]
    bad = experimental.loc[
        experimental["estado"] != "revisable",
        ["retorno_equiponderado_pct", "retorno_lideres_pct"],
    ]
    if bad["retorno_equiponderado_pct"].notna().any():
        errors.append("Canastas: se publico retorno sin cobertura")
    if experimental["fecha"].max() > TODAY.replace(day=1):
        errors.append("Canastas: mes futuro")
    raw_prices = BASE / "precios_icolcap_limpios.csv"
    if raw_prices.exists():
        raw = pd.read_csv(raw_prices, parse_dates=["fecha"])
        future = int((raw["fecha"] > TODAY.replace(day=1)).sum())
        if future:
            warnings.append(f"Precios historicos legados: {future} meses futuros en cuarentena")

    return errors, warnings, states, alerts


def main():
    errors, warnings, states, alerts = validate()
    for item in warnings:
        print("AVISO:", item)
    for item in errors:
        print("ERROR:", item)
    if errors:
        return 1
    pd.DataFrame(states).to_csv(BASE / "estado_fuentes.csv", index=False)
    pd.DataFrame(alerts, columns=["archivo", "fecha", "variable", "valor", "tipo", "accion"]
                 ).to_csv(BASE / "alertas_datos.csv", index=False)
    print(pd.DataFrame(states).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
