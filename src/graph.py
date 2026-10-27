"""Построение графа зависимостей обходом в глубину (DFS) без рекурсии."""

from dataclasses import dataclass, field

from repository import NotFoundError


class GraphError(Exception):
    """Ошибка построения графа зависимостей."""


@dataclass
class Graph:
    """Граф зависимостей пакета.

    edges    - словарь {пакет: [прямые зависимости]} в порядке обхода DFS;
    excluded - пакеты, отброшенные фильтром по подстроке;
    missing  - пакеты, которых нет в репозитории.
    """

    root: str
    edges: dict = field(default_factory=dict)
    excluded: set = field(default_factory=set)
    missing: list = field(default_factory=list)

    def edge_count(self):
        """Вернуть число рёбер (зависимостей) в графе."""
        return sum(len(deps) for deps in self.edges.values())


def is_excluded(name, name_filter):
    """Проверить, содержит ли имя пакета подстроку фильтра."""
    return bool(name_filter) and name_filter.lower() in name.lower()


def fetch_dependencies(graph, name, get_dependencies):
    """Получить зависимости пакета; отсутствующий пакет - без зависимостей."""
    try:
        return get_dependencies(name)
    except NotFoundError:
        if name == graph.root:
            raise
        graph.missing.append(name)
        return []


def build_graph(root, get_dependencies, name_filter=""):
    """Построить граф зависимостей пакета root обходом DFS без рекурсии.

    Вместо рекурсии используется явный стек. Уже посещённые пакеты
    (ключи graph.edges) повторно не обрабатываются, поэтому циклические
    зависимости не приводят к зацикливанию. Пакеты, имя которых
    содержит name_filter, в граф не попадают.
    """
    if is_excluded(root, name_filter):
        raise GraphError(f"package '{root}' is excluded by filter "
                         f"'{name_filter}'")
    graph = Graph(root)
    stack = [root]
    while stack:
        name = stack.pop()
        if name in graph.edges:
            continue
        deps = []
        for dep in fetch_dependencies(graph, name, get_dependencies):
            if is_excluded(dep, name_filter):
                graph.excluded.add(dep)
            elif dep not in deps:
                deps.append(dep)
        graph.edges[name] = deps
        stack.extend(dep for dep in reversed(deps)
                     if dep not in graph.edges)
    return graph


def find_cycles(graph):
    """Найти циклы: рёбра, ведущие в пакет, который сейчас на пути DFS.

    Обход без рекурсии: в стеке хранятся пары (пакет, итератор по его
    зависимостям). Возвращает список циклов, каждый - список пакетов
    от начала цикла до возврата в него.
    """
    path, on_path, done, cycles = [], set(), set(), []
    stack = [(graph.root, iter(graph.edges.get(graph.root, [])))]
    path.append(graph.root)
    on_path.add(graph.root)
    while stack:
        name, deps = stack[-1]
        dep = next(deps, None)
        if dep is None:
            stack.pop()
            path.pop()
            on_path.discard(name)
            done.add(name)
        elif dep in on_path:
            cycles.append(path[path.index(dep):] + [dep])
        elif dep not in done:
            stack.append((dep, iter(graph.edges.get(dep, []))))
            path.append(dep)
            on_path.add(dep)
    return cycles