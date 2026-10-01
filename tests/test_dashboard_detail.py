import unittest

import dashboard_colombia as dashboard
from tests.test_dashboard_navigation import find_component

TENORS = ["1A", "5A", "10A"]


class DetailViewTests(unittest.TestCase):
    def detail(self, variable, window):
        return dashboard.update_detail(variable, window, TENORS,
                                       ["inf_mensual", "inf_anual", "pib"],
                                       ["oficial", "equiponderado", "grandes"])

    def test_changing_period_or_series_resets_the_view(self):
        # Con la misma uirevision, Plotly conservaba el zoom anterior y el
        # período nuevo quedaba fuera de la vista: el gráfico parecía vacío.
        revisions = {self.detail(v, w).layout.uirevision
                     for v in ["bolsa", "tes", "inflacion"] for w in ["3M", "1A", "ALL"]}
        self.assertEqual(len(revisions), 9)

    def test_base_100_line_only_when_it_falls_inside_the_data(self):
        # En 3 meses el COLCAP está lejos de 100: la línea aplastaba la serie.
        short = self.detail("bolsa", "3M")
        self.assertFalse(any(s.y0 == 100 for s in short.layout.shapes))
        full = self.detail("bolsa", "ALL")
        self.assertTrue(any(s.y0 == 100 for s in full.layout.shapes))

    def test_period_buttons_are_readable(self):
        for window in ["3M", "6M", "1A", "3A", "5A", "ALL"]:
            style = find_component(dashboard.app.layout, f"detail-btn-{window}").style
            self.assertNotEqual(style["background"], "#1c2128")
            self.assertEqual(style["color"], dashboard.TEXT)


if __name__ == "__main__":
    unittest.main()
