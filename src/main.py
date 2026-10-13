"""Точка входа: инструмент визуализации графа зависимостей NuGet."""

import argparse
import sys

from config import ConfigError, load_config

DEFAULT_CONFIG = "config.xml"


def parse_args(argv):
    """Разобрать аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Визуализатор графа зависимостей пакетов NuGet")
    parser.add_argument("config", nargs="?", default=DEFAULT_CONFIG,
                        help="путь к XML-файлу конфигурации "
                             f"(по умолчанию {DEFAULT_CONFIG})")
    return parser.parse_args(argv)


def main(argv=None):
    """Загрузить конфигурацию и вывести параметры. Вернуть код выхода."""
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        print(f"Configuration error ({args.config}):", file=sys.stderr)
        print(error, file=sys.stderr)
        return 1
    for key, value in config.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())