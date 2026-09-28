"""Indicador descriptivo del ciclo a partir de PIB e IPC trimestrales."""

import pandas as pd


REGIMES = {
    "impulso_precios": ("Impulso con inflación", "#a45b00"),
    "impulso_desinflacion": ("Impulso con desinflación", "#087f5b"),
    "freno_precios": ("Freno con inflación", "#b43d48"),
    "freno_desinflacion": ("Freno con desinflación", "#3267a8"),
}


def quarterly_cycle(pib, ipc):
    """Align only completed quarters, then compare each with its predecessor."""
    growth = pib.dropna(subset=["pib_real_yoy"])[["fecha", "pib_real_yoy"]].copy()
    growth["quarter"] = growth["fecha"].dt.to_period("Q")
    growth = growth.sort_values("fecha").drop_duplicates("quarter", keep="last")

    prices = ipc.dropna(subset=["inflacion_anual"])[["fecha", "inflacion_anual"]].copy()
    prices["quarter"] = prices["fecha"].dt.to_period("Q")
    prices = prices.sort_values("fecha").drop_duplicates("quarter", keep="last")
    prices = prices[prices["fecha"].dt.month == prices["quarter"].dt.end_time.dt.month]

    result = growth.merge(prices[["quarter", "inflacion_anual"]], on="quarter", how="inner")
    result = result.sort_values("quarter").reset_index(drop=True)
    result["growth_change_pp"] = result["pib_real_yoy"].diff()
    result["inflation_change_pp"] = result["inflacion_anual"].diff()
    consecutive = result["quarter"].astype(int).diff().eq(1)
    result = result.loc[consecutive].copy()
    result["regime"] = result.apply(
        lambda row: ("impulso" if row["growth_change_pp"] >= 0 else "freno")
        + ("_precios" if row["inflation_change_pp"] >= 0 else "_desinflacion"),
        axis=1,
    )
    result["quarter_end"] = result["quarter"].dt.end_time.dt.normalize()
    return result.reset_index(drop=True)
