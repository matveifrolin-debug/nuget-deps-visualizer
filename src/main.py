"""Точка входа: инструмент визуализации графа зависимостей NuGet."""

import argparse
import sys

from config import ConfigError, load_config
from graph import GraphError, build_graph, find_cycles
from repository import RepositoryError, open_repository

DEFAULT_CONFIG = "config.xml"


def parse_args(argv):
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Визуализатор графа зависимостей пакетов NuGet")
    parser.add_argument("config", nargs="?", default=DEFAULT_CONFIG,
                        help="путь к XML-файлу конфигурации "
                             f"(по умолчанию {DEFAULT_CONFIG})")
    return parser.parse_args(argv)


def print_graph(config, graph):
    """Этап 3: вывести граф зависимостей с учётом транзитивности."""
    print(f"Dependency graph of {config.package} (DFS order):")
    for name, deps in graph.edges.items():
        print(f"  {name} -> {', '.join(deps) if deps else '(none)'}")
    print(f"Packages: {len(graph.edges)}, "
          f"dependencies: {graph.edge_count()}")
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


def main(argv=None):
    """Загрузить конфигурацию, построить и вывести граф зависимостей."""
    args = parse_args(argv)
    try:
        config = load_config(args.config)
        repo = open_repository(config)
        graph = build_graph(config.package, repo.get_dependencies,
                            config.filter)
        print_graph(config, graph)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())