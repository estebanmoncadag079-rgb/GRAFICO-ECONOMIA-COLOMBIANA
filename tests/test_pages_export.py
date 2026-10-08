import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import dashboard_colombia as dashboard
import exportar_pages
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
        self.assertIn('data-help="Canasta de este proyecto:', markup)
        for name in ("Recuperación", "Expansión", "Auge", "Recesión"):
            self.assertIn(name, markup)
        for name in ("Impulso con inflación", "Impulso con desinflación",
                     "Freno con inflación", "Freno con desinflación"):
            self.assertNotIn(name, markup)

    def test_payload_keeps_observed_periods(self):
        payload = build_payload()
        self.assertEqual(payload["tables"]["tes"][-1]["fecha"][:10],
                         dashboard.df_tes.iloc[-1]["fecha"].strftime("%Y-%m-%d"))
        self.assertEqual(payload["tables"]["gdp"][-1]["reference_end"][:10],
                         (dashboard.df_pib.iloc[-1]["fecha"] +
                          dashboard.pd.offsets.QuarterEnd(0)).strftime("%Y-%m-%d"))
        self.assertEqual(len(payload["figures"]["chart-bolsa"]["data"]), 3)
        self.assertEqual(len(payload["figures"]["chart-inflacion"]["data"]), 3)

    def test_export_includes_interactive_chart_assets(self):
        with TemporaryDirectory() as folder, patch.object(exportar_pages, "OUTPUT", Path(folder)):
            exportar_pages.build()
            document = (Path(folder) / "index.html").read_text(encoding="utf-8")
            for name in ("responsive.css", "responsive_layout.css"):
                self.assertRegex(document, f'<link rel="stylesheet" href="assets/{name}\\?v=[a-f0-9]{{12}}">')
                self.assertTrue((Path(folder) / "assets" / name).is_file())
            for name in ("label_help.js", "chart_navigation.js"):
                self.assertRegex(document, f'<script defer src="assets/{name}\\?v=[a-f0-9]{{12}}"></script>')
                self.assertTrue((Path(folder) / "assets" / name).is_file())


if __name__ == "__main__":
    unittest.main()
