"""Тесты этапа 4: обратные зависимости тем же DFS без рекурсии."""

import io
import os
import unittest
from contextlib import redirect_stdout

import context
from graph import GraphError, build_reverse_graph, build_reverse_index
from main import main
from repository import FileRepository, NugetRepository, RepositoryError

SIMPLE = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
COMPLEX = {"A": ["B", "C", "D"], "B": ["E", "F"], "C": ["F", "G"],
           "D": ["H"], "E": [], "F": ["H"], "G": ["A"], "H": []}


def reverse_of(repo, target, name_filter=""):
    """Построить граф обратных зависимостей по словарю repo."""
    def get_dependencies(name):
        """Вернуть прямые зависимости пакета из словаря."""
        return list(repo[name])
    return build_reverse_graph(target, list(repo), get_dependencies,
                               name_filter)


class ReverseIndexTest(unittest.TestCase):
    """Построение обратного индекса."""

    def test_index(self):
        """Ребро A -> B превращается в B -> A."""
        index = build_reverse_index(list(SIMPLE), SIMPLE.get)
        self.assertEqual(index["D"], ["B", "C"])
        self.assertEqual(index["A"], [])

    def test_undescribed_package(self):
        """Пакет, который только упоминается, тоже попадает в индекс."""
        index = build_reverse_index(["A"], {"A": ["Z"]}.get)
        self.assertEqual(index["Z"], ["A"])


class ReverseGraphTest(unittest.TestCase):
    """Обход обратных зависимостей."""

    def test_transitive_dependents(self):
        """От D зависят B и C напрямую и A транзитивно."""
        graph = reverse_of(SIMPLE, "D")
        self.assertEqual(list(graph.edges), ["D", "B", "A", "C"])

    def test_root_has_no_dependents(self):
        """От корневого пакета A никто не зависит."""
        graph = reverse_of(SIMPLE, "A")
        self.assertEqual(graph.edges, {"A": []})

    def test_cycle(self):
        """Цикл G -> A -> C -> G не приводит к зацикливанию."""
        graph = reverse_of(COMPLEX, "H")
        self.assertEqual(set(graph.edges),
                         {"H", "D", "F", "A", "B", "C", "G"})
        self.assertNotIn("E", graph.edges)

    def test_filter(self):
        """Пакеты с подстрокой фильтра исключаются из обхода."""
        graph = reverse_of(SIMPLE, "D", "B")
        self.assertEqual(list(graph.edges), ["D", "C", "A"])
        self.assertEqual(graph.excluded, {"B"})

    def test_unknown_package(self):
        """Пакета нет в репозитории - ошибка."""
        with self.assertRaises(GraphError):
            reverse_of(SIMPLE, "X")

    def test_no_recursion_on_long_chain(self):
        """Длинная цепочка обходится без переполнения стека."""
        size = 5000
        names = [f"P{i}" for i in range(size)]
        repo = {name: [nxt] for name, nxt in zip(names, names[1:])}
        repo[names[-1]] = []
        graph = reverse_of(repo, names[-1])
        self.assertEqual(len(graph.edges), size)


class ReverseRepositoryTest(unittest.TestCase):
    """Обратные зависимости на тестовых репозиториях и в NuGet."""

    def test_complex_file(self):
        """Файл repos/complex.txt: от H зависят 6 пакетов."""
        repo = FileRepository(os.path.join(context.ROOT, "repos",
                                           "complex.txt"))
        graph = build_reverse_graph("H", repo.package_names(),
                                    repo.get_dependencies)
        self.assertEqual(len(graph.edges) - 1, 6)

    def test_nuget_not_supported(self):
        """Для NuGet список всех пакетов недоступен - ошибка."""
        repo = NugetRepository("https://example.com/flat/")
        with self.assertRaises(RepositoryError):
            repo.package_names()

    def test_main_reverse(self):
        """Запуск main с ключом --reverse выводит зависимые пакеты."""
        path = os.path.join(context.ROOT, "configs", "reverse_simple.xml")
        output = io.StringIO()
        current = os.getcwd()
        os.chdir(context.ROOT)
        try:
            with redirect_stdout(output):
                code = main([path, "--reverse"])
        finally:
            os.chdir(current)
        self.assertEqual(code, 0)
        self.assertIn("Packages depending on D (3): B, A, C",
                      output.getvalue())


if __name__ == "__main__":
    unittest.main()
