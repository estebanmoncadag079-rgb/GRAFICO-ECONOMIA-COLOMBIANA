import unittest

import dashboard_colombia as dashboard
from exportar_pages import build_payload, render


class PagesExportTests(unittest.TestCase):
    def test_layout_keeps_main_controls_and_no_dash_store(self):
        markup = render(dashboard.app.layout)
        for element_id in ("chart-bolsa", "chart-inflacion", "chart-tes",
                           "curve-chart", "cycle-chart", "detail-chart",
                           "bolsa-layers", "inf-layers", "curve-toggle"):
            self.assertIn(f'id="{element_id}"', markup)
        self.assertNotIn('id="xrange-store"', markup)
        self.assertIn('src="assets/Logo Schema.png"', markup)

    def test_payload_keeps_observed_periods(self):
        payload = build_payload()
        self.assertEqual(payload["tables"]["tes"][-1]["fecha"][:10],
                         dashboard.df_tes.iloc[-1]["fecha"].strftime("%Y-%m-%d"))
        self.assertEqual(payload["tables"]["gdp"][-1]["reference_end"][:10],
                         (dashboard.df_pib.iloc[-1]["fecha"] +
                          dashboard.pd.offsets.QuarterEnd(0)).strftime("%Y-%m-%d"))
        self.assertEqual(len(payload["figures"]["chart-bolsa"]["data"]), 3)
        self.assertEqual(len(payload["figures"]["chart-inflacion"]["data"]), 3)


if __name__ == "__main__":
    unittest.main()
