"""Audita retornos mensuales de canastas historicas sin inventar datos diarios."""

from pathlib import Path
import pandas as pd

from construir_indices import GRANDES, cargar_canastas

BASE = Path(__file__).resolve().parent
PRICES = BASE / "precios_icolcap_limpios.csv"
OUT = BASE / "indices_experimentales_mensuales.csv"


def calculate(prices, baskets, today=None):
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    prices = prices.copy().sort_index()
    prices = prices[prices.index <= today.replace(day=1)]
    prices = prices.dropna(how="all")
    if prices.index.has_duplicates:
        raise ValueError("Fechas mensuales de precios duplicadas")
    rows = []
    for date in prices.index[1:]:
        previous = date - pd.DateOffset(months=1)
        if previous not in prices.index:
            continue
        basket = sorted(set(baskets.get(date, ())) & set(prices.columns))
        leaders = [ticker for ticker in basket if ticker in GRANDES]
        returns = prices.loc[date].div(prices.loc[previous]).sub(1)
        valid = returns.where(returns.abs() <= 0.80)

        def stats(tickers):
            observed = returns[tickers].dropna()
            accepted = valid[tickers].dropna()
            coverage = len(accepted) / len(tickers) if tickers else 0
            outliers = len(observed) - len(accepted)
            publish = len(accepted) >= min(5, len(tickers)) and coverage >= 0.70 and outliers == 0
            return len(tickers), len(accepted), outliers, round(coverage, 4), (
                round(float(accepted.mean() * 100), 6) if publish else float("nan")
            )

        n, pairs, outliers, coverage, ret = stats(basket)
        nl, pairsl, outliersl, coveragel, retl = stats(leaders)
        rows.append({
            "fecha": date.strftime("%Y-%m-%d"),
            "canasta_tickers": n,
            "pares_precio_validos": pairs,
            "retornos_atipicos": outliers,
            "cobertura_canasta": coverage,
            "retorno_equiponderado_pct": ret,
            "lideres_tickers": nl,
            "lideres_pares_validos": pairsl,
            "lideres_atipicos": outliersl,
            "cobertura_lideres": coveragel,
            "retorno_lideres_pct": retl,
            "estado": "revisable" if pd.notna(ret) else "sin_cobertura_o_atipicos",
            "metodologia": "precios_mensuales_sin_ajustes_corporativos_verificados",
        })
    return pd.DataFrame(rows)


def main():
    prices = pd.read_csv(PRICES, parse_dates=["fecha"]).set_index("fecha")
    baskets = cargar_canastas(set(prices.columns))
    table = calculate(prices, baskets)
    if table.empty:
        raise ValueError("No se generaron meses de canastas")
    table.to_csv(OUT, index=False)
    valid = table[table["estado"] == "revisable"]
    print(f"Canastas experimentales: {len(table)} meses, {len(valid)} revisables, ultimo {valid['fecha'].max()}")


if __name__ == "__main__":
    main()
