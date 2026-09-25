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


if __name__ == "__main__":
    unittest.main()
