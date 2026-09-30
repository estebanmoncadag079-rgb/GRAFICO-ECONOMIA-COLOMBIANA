import unittest

import dashboard_colombia as dashboard


def find_component(node, component_id):
    if getattr(node, "id", None) == component_id:
        return node
    children = getattr(node, "children", None)
    for child in children if isinstance(children, list) else [children]:
        if child is not None and not isinstance(child, (str, int, float)):
            found = find_component(child, component_id)
            if found is not None:
                return found
    return None


class NavigationTests(unittest.TestCase):
    """Charts navigate like a trading platform: drag pans, the wheel zooms."""

    def figures(self):
        return {
            "bolsa": dashboard.make_fig_bolsa(dashboard.df_colcap),
            "inflacion": dashboard.make_fig_inflacion(dashboard.df_daily),
            "tes": dashboard.make_fig_tes(dashboard.df_tes, ["1A", "5A", "10A"]),
        }

    def test_wheel_zooms_and_drag_pans(self):
        self.assertTrue(dashboard.CHART_CONFIG["scrollZoom"])
        for name, figure in self.figures().items():
            with self.subTest(name):
                self.assertEqual(figure.layout.dragmode, "pan")

    def test_user_view_survives_redraws(self):
        for name, figure in self.figures().items():
            with self.subTest(name):
                self.assertTrue(figure.layout.uirevision)

    def test_release_button_explains_its_action(self):
        button = find_component(dashboard.app.layout, "btn-soltar")
        self.assertIn("Liberar fecha", str(button.children))


if __name__ == "__main__":
    unittest.main()
