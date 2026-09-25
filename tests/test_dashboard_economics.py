import unittest

import pandas as pd

import dashboard_colombia as dashboard


class EconomicChartTests(unittest.TestCase):
    def test_quarterly_gdp_uses_end_of_reference_period(self):
        figure = dashboard.make_fig_inflacion(dashboard.df_daily)
        gdp = next(trace for trace in figure.data if trace.meta["frequency"] == "quarterly")
        index = list(gdp.customdata).index("T2 2026")
        self.assertEqual(gdp.x[index], "2026-06-30T00:00:00")
        self.assertEqual(figure.layout.xaxis.title.text, "Período de referencia")
        self.assertTrue(figure.layout.xaxis.showline)

    def test_sidebar_cannot_use_unfinished_quarter(self):
        observation = dashboard.latest_on_or_before(
            dashboard.df_pib, pd.Timestamp("2019-09-01"),
            ["pib_real_yoy"], pd.offsets.QuarterEnd(0),
        )
        self.assertEqual(observation["trimestre"], "T2 2019")

    def test_values_live_outside_plot_and_empty_layers_work(self):
        market = dashboard.make_fig_bolsa(dashboard.df_colcap)
        macro = dashboard.make_fig_inflacion(dashboard.df_daily)
        self.assertTrue(all(trace.hoverinfo == "none" for trace in market.data))
        self.assertTrue(all(trace.hoverinfo == "none" for trace in macro.data))
        self.assertFalse(market.layout.showlegend)
        self.assertFalse(macro.layout.showlegend)
        self.assertEqual(len(dashboard.make_fig_inflacion(
            dashboard.df_daily, show_layers=[]).data), 0)


if __name__ == "__main__":
    unittest.main()
