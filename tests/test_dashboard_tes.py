import unittest

import pandas as pd

import dashboard_colombia as dashboard
from validar_datos import isolated_tes_spikes

ALL = ["1A", "5A", "10A"]


class TesChartTests(unittest.TestCase):
    def test_rates_are_clean_lines_without_stacked_fills(self):
        figure = dashboard.make_fig_tes(dashboard.df_tes, ALL)
        rates = [t for t in figure.data if (t.yaxis or "y") == "y"]
        self.assertEqual([t.meta["label"] for t in rates], ["TES 1A", "TES 5A", "TES 10A"])
        self.assertTrue(all(t.fill in (None, "none") for t in rates))

    def test_slope_panel_shows_10y_minus_1y_from_the_same_data(self):
        figure = dashboard.make_fig_tes(dashboard.df_tes, ALL)
        slope = next(t for t in figure.data if t.meta and t.meta.get("unit") == "pp")
        tes = dashboard.df_tes
        expected = (tes["tes_pesos_10y"].mask(isolated_tes_spikes(tes["tes_pesos_10y"]))
                    - tes["tes_pesos_1y"].mask(isolated_tes_spikes(tes["tes_pesos_1y"])))
        got = pd.Series(slope.y, dtype=float)
        self.assertEqual(slope.yaxis, "y2")
        pd.testing.assert_series_equal(got.round(6), expected.reset_index(drop=True).round(6),
                                       check_names=False)

    def test_slope_panel_hidden_without_both_ends_of_the_curve(self):
        figure = dashboard.make_fig_tes(dashboard.df_tes, ["5A", "10A"])
        self.assertFalse(any((t.yaxis or "y") == "y2" for t in figure.data))


if __name__ == "__main__":
    unittest.main()
