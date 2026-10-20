"""Точка входа: инструмент визуализации графа зависимостей NuGet."""

import argparse
import sys

from config import ConfigError, load_config
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


def print_direct_dependencies(config, repo):
    """Этап 2: вывести прямые зависимости заданного пакета."""
    version, deps = repo.direct_dependencies(config.package)
    print(f"Package: {config.package} {version}".rstrip())
    if not deps:
        print("No direct dependencies")
        return
    print(f"Direct dependencies ({len(deps)}):")
    for name, dep_version in deps:
        print(f"  {name} {dep_version}".rstrip())


def main(argv=None):
    """Загрузить конфигурацию и вывести прямые зависимости пакета."""
    args = parse_args(argv)
    try:
        config = load_config(args.config)
        repo = open_repository(config)
        print_direct_dependencies(config, repo)
    except ConfigError as error:
        print(f"Configuration error ({args.config}):", file=sys.stderr)
        print(error, file=sys.stderr)
        return 1
    except RepositoryError as error:
        print(f"Repository error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())