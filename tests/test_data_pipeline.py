import unittest

import pandas as pd

from actualizar_pib import build_table
from construir_tablas_experimentales import calculate
from validar_datos import isolated_tes_spikes


class DataPipelineTests(unittest.TestCase):
    def test_real_and_nominal_growth_are_distinct(self):
        dates = pd.date_range("2023-01-01", periods=9, freq="QS")
        real = pd.Series([100, 100, 100, 100, 110, 110, 110, 110, 121], index=dates)
        adjusted = pd.Series([100, 102, 104, 106, 108, 110, 112, 114, 116], index=dates)
        nominal = pd.Series([200, 200, 200, 200, 300, 300, 300, 300, 450], index=dates)
        table = build_table(real, adjusted, nominal, pd.Timestamp("2025-08-01"), "DANE")
        self.assertAlmostEqual(table.iloc[-1]["pib_real_yoy"], 10)
        self.assertAlmostEqual(table.iloc[-1]["pib_nominal_yoy"], 50)
        self.assertEqual(table.iloc[-1]["trimestre"], "T1 2025")

    def test_incomplete_month_does_not_publish_return(self):
        tickers = ["ECOPETROL", "PFBCOLOM", "GRUPOSURA", "GRUPOARGOS",
                   "PFAVAL", "ISA", "NUTRESA"]
        dates = pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01"])
        prices = pd.DataFrame([[100] * 7, [105] * 7, [110, 110] + [None] * 5],
                              index=dates, columns=tickers)
        baskets = {date: frozenset(tickers) for date in dates}
        table = calculate(prices, baskets, today="2026-03-20")
        self.assertAlmostEqual(table.iloc[0]["retorno_equiponderado_pct"], 5)
        self.assertTrue(pd.isna(table.iloc[1]["retorno_equiponderado_pct"]))
        self.assertEqual(table.iloc[1]["estado"], "sin_cobertura_o_atipicos")

    def test_isolated_tes_spike_is_flagged(self):
        flags = isolated_tes_spikes(pd.Series([10.0, 10.2, 0.5, 10.1, 10.2]))
        self.assertEqual(flags.tolist(), [False, False, True, False, False])


if __name__ == "__main__":
    unittest.main()
