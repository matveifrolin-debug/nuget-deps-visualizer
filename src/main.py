"""Точка входа: инструмент визуализации графа зависимостей NuGet."""

import argparse
import sys

from config import ConfigError, load_config
from graph import GraphError, build_graph, build_reverse_graph, find_cycles
from repository import RepositoryError, open_repository
from visualize import VisualizeError, ascii_tree, save_svg, to_dot

DEFAULT_CONFIG = "config.xml"


def parse_args(argv):
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Визуализатор графа зависимостей пакетов NuGet")
    parser.add_argument("config", nargs="?", default=DEFAULT_CONFIG,
                        help="путь к XML-файлу конфигурации "
                             f"(по умолчанию {DEFAULT_CONFIG})")
    parser.add_argument("--reverse", action="store_true",
                        help="вывести обратные зависимости: пакеты, "
                             "которые зависят от заданного")
    return parser.parse_args(argv)


def print_problems(config, graph):
    """Вывести циклы, исключённые фильтром и ненайденные пакеты."""
    cycles = find_cycles(graph)
    for cycle in cycles:
        print("Cycle: " + " -> ".join(cycle))
    if not cycles:
        print("Cycles: none")
    if config.filter:
        excluded = ", ".join(sorted(graph.excluded)) or "(none)"
        print(f"Excluded by filter '{config.filter}': {excluded}")
    if graph.missing:
        print("Not found in repository: " + ", ".join(graph.missing))


def print_graph(config, graph):
    """Этап 3: вывести граф зависимостей с учётом транзитивности."""
    print(f"Dependency graph of {config.package} (DFS order):")
    for name, deps in graph.edges.items():
        print(f"  {name} -> {', '.join(deps) if deps else '(none)'}")
    print(f"Packages: {len(graph.edges)}, "
          f"dependencies: {graph.edge_count()}")
    print_problems(config, graph)


def print_reverse(config, graph):
    """Этап 4: вывести пакеты, которые зависят от заданного."""
    print(f"Reverse dependencies of {config.package} (DFS order):")
    for name, users in graph.edges.items():
        print(f"  {name} <- {', '.join(users) if users else '(none)'}")
    dependents = [name for name in graph.edges if name != graph.root]
    print(f"Packages depending on {config.package} "
          f"({len(dependents)}): {', '.join(dependents) or '(none)'}")
    print_problems(config, graph)


def visualize(config, graph):
    """Этап 5: вывести DOT, сохранить SVG и при необходимости дерево."""
    dot_text = to_dot(graph)
    print("Graphviz (DOT):")
    print(dot_text, end="")
    dot_path = save_svg(dot_text, config.output)
    print(f"Saved: {dot_path}, {config.output}")
    if config.ascii_tree:
        print("ASCII tree:")
        print("\n".join(ascii_tree(graph)))


def run(config, reverse):
    """Построить и вывести прямой или обратный граф зависимостей."""
    repo = open_repository(config)
    if reverse:
        graph = build_reverse_graph(config.package, repo.package_names(),
                                    repo.get_dependencies, config.filter)
        print_reverse(config, graph)
    else:
        graph = build_graph(config.package, repo.get_dependencies,
                            config.filter)
        print_graph(config, graph)
        visualize(config, graph)


def main(argv=None):
    """Загрузить конфигурацию и выполнить выбранный режим."""
    args = parse_args(argv)
    try:
        run(load_config(args.config), args.reverse)
    except ConfigError as error:
        print(f"Configuration error ({args.config}):", file=sys.stderr)
        print(error, file=sys.stderr)
        return 1
    except RepositoryError as error:
        print(f"Repository error: {error}", file=sys.stderr)
        return 1
    except GraphError as error:
        print(f"Graph error: {error}", file=sys.stderr)
        return 1
    except VisualizeError as error:
        print(f"Visualization error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
