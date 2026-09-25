import unittest

import dashboard_colombia as dashboard


class BolsaChartTests(unittest.TestCase):
    def test_original_comparisons_remain_available(self):
        figure = dashboard.make_fig_bolsa(dashboard.df_colcap)
        self.assertEqual(len(figure.data), 4)
        self.assertEqual(figure.data[0].name, "COLCAP oficial")
        self.assertIn("equiponderado", figure.data[2].name)
        self.assertIn("7 Magníficas", figure.data[3].name)

    def test_official_series_can_be_isolated(self):
        figure = dashboard.make_fig_bolsa(dashboard.df_colcap, layers=["oficial"])
        self.assertEqual(len(figure.data), 1)

    def test_msci_transition_marker_only_when_official_date_is_visible(self):
        figure = dashboard.make_fig_bolsa(dashboard.df_colcap)
        self.assertEqual(len(figure.layout.shapes), 2)  # Base 100 and transition.
        self.assertEqual(figure.layout.shapes[1].x0, dashboard.COLCAP_MSCI_TRANSITION)
        self.assertIn("BVC → MSCI", figure.layout.annotations[0].text)

        recent = dashboard.df_colcap[dashboard.df_colcap["fecha"] >= "2024-01-01"]
        self.assertEqual(len(dashboard.make_fig_bolsa(recent).layout.annotations), 0)
        self.assertEqual(len(dashboard.make_fig_bolsa(
            dashboard.df_colcap, x_range=["2024-01-01", "2025-01-01"]).layout.annotations), 0)
        self.assertEqual(len(dashboard.make_fig_bolsa(
            dashboard.df_colcap, layers=["referencia"]).layout.annotations), 0)

        transition_day = dashboard.df_colcap[
            dashboard.df_colcap["fecha"] == dashboard.COLCAP_MSCI_TRANSITION]
        self.assertEqual(len(dashboard.make_fig_bolsa(transition_day).layout.annotations), 1)


if __name__ == "__main__":
    unittest.main()
