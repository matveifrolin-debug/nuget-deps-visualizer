"""Тесты этапа 5: Graphviz (DOT), SVG и ASCII-дерево."""

import os
import shutil
import tempfile
import unittest

import context
from graph import build_graph
from repository import NotFoundError
from visualize import VisualizeError, ascii_tree, save_svg, to_dot

SIMPLE = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
CYCLE = {"A": ["B"], "B": ["C"], "C": ["A", "D"], "D": []}
MISSING = {"A": ["B", "Z"], "B": []}


def graph_of(repo, root="A"):
    """Построить граф по словарю repo; отсутствующие пакеты - missing."""
    def get_dependencies(name):
        """Вернуть зависимости пакета или сообщить, что его нет."""
        if name not in repo:
            raise NotFoundError(name)
        return list(repo[name])
    return build_graph(root, get_dependencies)


class DotTest(unittest.TestCase):
    """Текстовое представление на языке Graphviz."""

    def test_structure(self):
        """Есть заголовок digraph и все рёбра графа."""
        text = to_dot(graph_of(SIMPLE))
        self.assertTrue(text.startswith("digraph dependencies {"))
        self.assertTrue(text.rstrip().endswith("}"))
        edges = ['"A" -> "B"', '"A" -> "C"', '"B" -> "D"', '"C" -> "D"']
        for edge in edges:
            self.assertIn(edge, text)
        self.assertEqual(text.count("->"), 4)

    def test_root_highlighted(self):
        """Корневой пакет закрашен."""
        self.assertIn('"A" [style="rounded,filled"',
                      to_dot(graph_of(SIMPLE)))

    def test_cycle_red(self):
        """Рёбра цикла выделены красным, остальные - нет."""
        text = to_dot(graph_of(CYCLE))
        self.assertIn('"C" -> "A" [color=red]', text)
        self.assertIn('"C" -> "D";', text)

    def test_missing_dashed(self):
        """Ненайденный пакет нарисован пунктиром."""
        self.assertIn('"Z" [style="rounded,dashed"',
                      to_dot(graph_of(MISSING)))

    def test_dotted_names_quoted(self):
        """Имена NuGet с точками записываются в кавычках."""
        repo = {"Serilog": ["System.Threading.Channels"],
                "System.Threading.Channels": []}
        text = to_dot(graph_of(repo, "Serilog"))
        self.assertIn('"Serilog" -> "System.Threading.Channels";', text)


class AsciiTreeTest(unittest.TestCase):
    """Вывод зависимостей в виде ASCII-дерева."""

    def test_tree(self):
        """Повторно встреченный пакет помечается (*)."""
        self.assertEqual(ascii_tree(graph_of(SIMPLE)),
                         ["A", "|-- B", "|   \\-- D",
                          "\\-- C", "    \\-- D (*)"])

    def test_cycle(self):
        """Возврат в пакет на текущем пути помечается (cycle)."""
        lines = ascii_tree(graph_of(CYCLE))
        self.assertIn("        |-- A (cycle)", lines)
        self.assertEqual(len(lines), 5)

    def test_long_chain(self):
        """Длинная цепочка выводится без рекурсии."""
        size = 3000
        names = [f"P{i}" for i in range(size)]
        repo = {name: [nxt] for name, nxt in zip(names, names[1:])}
        repo[names[-1]] = []
        self.assertEqual(len(ascii_tree(graph_of(repo, names[0]))), size)


class SaveSvgTest(unittest.TestCase):
    """Сохранение изображения через Graphviz."""

    def test_dot_not_installed(self):
        """Нет программы dot - понятная ошибка."""
        with tempfile.TemporaryDirectory() as folder:
            output = os.path.join(folder, "graph.svg")
            with self.assertRaises(VisualizeError):
                save_svg("digraph g {}", output, "no-such-dot-command")

    @unittest.skipUnless(shutil.which("dot"), "Graphviz is not installed")
    def test_svg_created(self):
        """Создаются файлы .dot и .svg."""
        with tempfile.TemporaryDirectory() as folder:
            output = os.path.join(folder, "out", "graph.svg")
            dot_path = save_svg(to_dot(graph_of(SIMPLE)), output)
            self.assertTrue(os.path.isfile(dot_path))
            with open(output, encoding="utf-8") as file:
                self.assertIn("<svg", file.read())

    @unittest.skipUnless(shutil.which("dot"), "Graphviz is not installed")
    def test_bad_dot_text(self):
        """Ошибка в тексте DOT - VisualizeError."""
        with tempfile.TemporaryDirectory() as folder:
            output = os.path.join(folder, "graph.svg")
            with self.assertRaises(VisualizeError):
                save_svg("digraph {", output)


if __name__ == "__main__":
    unittest.main()
