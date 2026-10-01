import unittest

import dashboard_colombia as dashboard


def walk(node):
    yield node
    children = getattr(node, "children", None)
    for child in children if isinstance(children, list) else [children]:
        if child is not None and not isinstance(child, (str, int, float)):
            yield from walk(child)


def text(node):
    return " ".join(str(n.children) for n in walk(node)
                    if isinstance(getattr(n, "children", None), str))


class CycleGridTests(unittest.TestCase):
    def grid(self):
        return next(n for n in walk(dashboard.app.layout)
                    if getattr(n, "className", "") == "cycle-grid")

    def test_axes_use_plain_words_and_arrows(self):
        content = text(self.grid())
        for label in ["PIB ▼ se frena", "PIB ▲ acelera", "Inflación ▲ sube", "Inflación ▼ baja"]:
            self.assertIn(label, content)

    def test_every_quadrant_explains_itself(self):
        cells = [n for n in walk(self.grid())
                 if "cycle-cell" in (getattr(n, "className", "") or "").split()]
        self.assertEqual(len(cells), 4)
        for cell in cells:
            self.assertTrue(any("cycle-cell__text" == getattr(n, "className", None)
                                for n in walk(cell)))

    def test_current_quadrant_says_we_are_here(self):
        current = next(n for n in walk(self.grid())
                       if "cycle-cell--current" in (getattr(n, "className", "") or ""))
        self.assertIn("Estamos aquí", text(current))
        self.assertIn(dashboard.STORY["phase"], text(current))


if __name__ == "__main__":
    unittest.main()
