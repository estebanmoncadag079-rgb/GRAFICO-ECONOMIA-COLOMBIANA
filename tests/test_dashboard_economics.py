import unittest

import pandas as pd

import dashboard_colombia as dashboard
from ciclo_economico import quarterly_cycle


class EconomicChartTests(unittest.TestCase):
    def test_cycle_quadrants_use_requested_names(self):
        self.assertEqual(
            {code: name for code, (name, _) in dashboard.REGIMES.items()},
            {
                "impulso_desinflacion": "Recuperación",
                "impulso_precios": "Expansión",
                "freno_precios": "Auge",
                "freno_desinflacion": "Recesión",
            },
        )

    def test_cycle_uses_only_completed_and_matching_quarters(self):
        gdp = pd.DataFrame({
            "fecha": pd.to_datetime(["2025-10-01", "2026-01-01", "2026-04-01", "2026-07-01"]),
            "pib_real_yoy": [2.0, 1.0, 3.0, 4.0],
        })
        ipc = pd.DataFrame({
            "fecha": pd.to_datetime(["2025-12-01", "2026-03-01", "2026-06-01", "2026-08-01"]),
            "inflacion_anual": [5.0, 5.5, 5.2, 6.0],
        })
        cycle = quarterly_cycle(gdp, ipc)
        self.assertEqual(list(cycle["regime"]), ["freno_precios", "impulso_desinflacion"])
        self.assertEqual(list(cycle["quarter_end"].dt.strftime("%Y-%m-%d")),
                         ["2026-03-31", "2026-06-30"])
        self.assertAlmostEqual(cycle.iloc[-1]["growth_change_pp"], 2.0)
        self.assertAlmostEqual(cycle.iloc[-1]["inflation_change_pp"], -0.3)

    def test_cycle_current_period_matches_dashboard_story(self):
        latest = dashboard.CYCLE.iloc[-1]
        self.assertLessEqual(latest["quarter_end"], pd.Timestamp.now())
        self.assertEqual(dashboard.STORY["phase"], dashboard.REGIMES[latest["regime"]][0])
        figure = dashboard.make_cycle_fig()
        self.assertEqual(pd.Timestamp(figure.data[0].x[-1]), latest["quarter_end"])
        self.assertIn("IPC anual", figure.data[0].text[-1])

    def test_chart_descriptions_are_collapsed_disclosures(self):
        description = dashboard.chart_description(
            "Inflación y PIB: precios y actividad", "Texto de prueba")
        self.assertEqual(description.__class__.__name__, "Details")
        self.assertFalse(description.open)
        self.assertEqual(description.children[0].__class__.__name__, "Summary")
        self.assertEqual(description.children[0].children[0].children,
                         "Descripción del gráfico")

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
