import unittest

import dashboard_colombia as dashboard


class HoverTests(unittest.TestCase):
    """The TES curve follows the cursor date, so every time-series chart must
    emit hover events at any x position, not only near a line."""

    def assert_hovers_by_date(self, figure):
        self.assertEqual(figure.layout.hovermode, "x")
        self.assertEqual(figure.layout.hoverdistance, -1)

    def test_market_chart_hovers_anywhere_on_the_date_axis(self):
        self.assert_hovers_by_date(dashboard.make_fig_bolsa(dashboard.df_colcap))

    def test_inflation_chart_hovers_anywhere_on_the_date_axis(self):
        self.assert_hovers_by_date(dashboard.make_fig_inflacion(dashboard.df_daily))

    def test_tes_chart_hovers_anywhere_on_the_date_axis(self):
        self.assert_hovers_by_date(dashboard.make_fig_tes(dashboard.df_tes, ["1A", "5A", "10A"]))


if __name__ == "__main__":
    unittest.main()
