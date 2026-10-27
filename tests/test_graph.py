"""Тесты этапа 3: построение графа зависимостей DFS без рекурсии."""

import os
import unittest

import context
from graph import GraphError, build_graph, find_cycles
from repository import FileRepository, NotFoundError

SIMPLE = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
CYCLE = {"A": ["B"], "B": ["C"], "C": ["A", "D"], "D": []}
COMPLEX = {"A": ["B", "C", "D"], "B": ["E", "F"], "C": ["F", "G"],
           "D": ["H"], "E": [], "F": ["H"], "G": ["A"], "H": []}


def make_source(repo):
    """Создать функцию получения зависимостей из словаря repo."""
    def get_dependencies(name):
        """Вернуть зависимости пакета или сообщить, что его нет."""
        if name not in repo:
            raise NotFoundError(f"package '{name}' not found")
        return list(repo[name])
    return get_dependencies


class BuildGraphTest(unittest.TestCase):
    """Построение графа с учётом транзитивности."""

    def test_transitive(self):
        """В граф попадают и транзитивные зависимости."""
        graph = build_graph("A", make_source(SIMPLE))
        self.assertEqual(set(graph.edges), {"A", "B", "C", "D"})
        self.assertEqual(graph.edge_count(), 4)

    def test_dfs_order(self):
        """Порядок обхода - в глубину: A, B, D, затем C."""
        graph = build_graph("A", make_source(SIMPLE))
        self.assertEqual(list(graph.edges), ["A", "B", "D", "C"])

    def test_shared_dependency_once(self):
        """Общая зависимость D обрабатывается один раз."""
        calls = []
        source = make_source(SIMPLE)

        def counting(name):
            """Запомнить запрос и вернуть зависимости."""
            calls.append(name)
            return source(name)

        build_graph("A", counting)
        self.assertEqual(calls.count("D"), 1)

    def test_no_recursion_on_long_chain(self):
        """Длинная цепочка не приводит к переполнению стека вызовов."""
        size = 5000
        repo = {f"P{i}": [f"P{i + 1}"] for i in range(size)}
        repo[f"P{size}"] = []
        graph = build_graph("P0", make_source(repo))
        self.assertEqual(len(graph.edges), size + 1)


class CycleTest(unittest.TestCase):
    """Обработка циклических зависимостей."""

    def test_cycle_terminates(self):
        """Цикл A-B-C-A не приводит к зацикливанию."""
        graph = build_graph("A", make_source(CYCLE))
        self.assertEqual(set(graph.edges), {"A", "B", "C", "D"})

    def test_find_cycle(self):
        """Цикл находится и выводится полностью."""
        graph = build_graph("A", make_source(CYCLE))
        self.assertEqual(find_cycles(graph), [["A", "B", "C", "A"]])

    def test_self_loop(self):
        """Пакет, зависящий сам от себя."""
        graph = build_graph("A", make_source({"A": ["A", "B"], "B": []}))
        self.assertEqual(find_cycles(graph), [["A", "A"]])

    def test_no_cycles(self):
        """В ромбе A-B-C-D циклов нет."""
        graph = build_graph("A", make_source(SIMPLE))
        self.assertEqual(find_cycles(graph), [])


class RepositoryFilesTest(unittest.TestCase):
    """Граф по файлам тестовых репозиториев из папки repos."""

    def load(self, name):
        """Построить граф пакета A по файлу repos/<name>.txt."""
        path = os.path.join(context.ROOT, "repos", f"{name}.txt")
        return build_graph("A", FileRepository(path).get_dependencies)

    def test_complex_file(self):
        """Файл complex.txt: 8 пакетов и цикл A-C-G-A."""
        graph = self.load("complex")
        self.assertEqual(len(graph.edges), 8)
        self.assertEqual(find_cycles(graph), [["A", "C", "G", "A"]])

    def test_missing_file(self):
        """Файл missing.txt: пакет Z не описан."""
        self.assertEqual(self.load("missing").missing, ["Z"])


class FilterTest(unittest.TestCase):
    """Исключение пакетов по подстроке."""

    def test_filter_removes_subtree(self):
        """Пакет F исключён, а H остаётся благодаря D."""
        graph = build_graph("A", make_source(COMPLEX), "F")
        self.assertNotIn("F", graph.edges)
        self.assertEqual(graph.excluded, {"F"})
        self.assertIn("H", graph.edges)

    def test_filter_case_insensitive(self):
        """Фильтр не зависит от регистра."""
        graph = build_graph("A", make_source(COMPLEX), "f")
        self.assertEqual(graph.excluded, {"F"})

    def test_root_excluded(self):
        """Фильтр, исключающий сам пакет, - ошибка."""
        with self.assertRaises(GraphError):
            build_graph("A", make_source(SIMPLE), "A")


class MissingTest(unittest.TestCase):
    """Пакеты, отсутствующие в репозитории."""

    def test_missing_dependency(self):
        """Отсутствующая зависимость запоминается, обход продолжается."""
        graph = build_graph("A", make_source({"A": ["B", "Z"], "B": []}))
        self.assertEqual(graph.missing, ["Z"])

    def test_missing_root(self):
        """Отсутствующий корневой пакет - ошибка."""
        with self.assertRaises(NotFoundError):
            build_graph("Q", make_source(SIMPLE))


if __name__ == "__main__":
    unittest.main()