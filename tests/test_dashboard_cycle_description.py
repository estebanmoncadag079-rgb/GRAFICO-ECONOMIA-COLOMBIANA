import unittest

import dashboard_colombia as dashboard
from tests.test_dashboard_cycle_grid import text, walk

ASSETS = ["Acciones", "Bonos y TES", "Dólar y peso", "Petróleo y materias primas"]


class CycleDescriptionTests(unittest.TestCase):
    def description(self):
        section = next(n for n in walk(dashboard.app.layout)
                       if getattr(n, "className", "") == "cycle-section")
        return next(n for n in walk(section)
                    if "panel-explainer" in (getattr(n, "className", "") or ""))

    def test_is_a_closed_disclosure_like_the_other_charts(self):
        details = self.description()
        self.assertEqual(details.__class__.__name__, "Details")
        self.assertFalse(details.open)
        self.assertIn("Descripción del gráfico", text(details.children[0]))

    def test_each_phase_explains_the_four_asset_classes(self):
        phases = [n for n in walk(self.description())
                  if "cycle-asset-phase" in (getattr(n, "className", "") or "").split()]
        self.assertEqual(len(phases), 4)
        for phase in phases:
            content = text(phase)
            for asset in ASSETS:
                self.assertIn(asset, content)

    def test_current_phase_is_marked_and_it_is_not_a_recommendation(self):
        content = text(self.description())
        self.assertIn("Estamos aquí", content)
        self.assertIn("no son recomendaciones", content)


if __name__ == "__main__":
    unittest.main()
