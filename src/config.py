"""Загрузка и проверка конфигурации из XML-файла.

Пример конфигурации:
<config>
    <package>Serilog</package>
    <repository>https://api.nuget.org/v3-flatcontainer/</repository>
    <test_mode>false</test_mode>
    <output>graph.svg</output>
    <ascii_tree>true</ascii_tree>
    <filter></filter>
</config>
"""

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import urlparse

ROOT_TAG = "config"
FIELDS = ["package", "repository", "test_mode", "output",
          "ascii_tree", "filter"]
OPTIONAL_FIELDS = {"filter"}
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
MAX_NAME_LENGTH = 100
BOOL_VALUES = {"true": True, "false": False}
URL_SCHEMES = ("http", "https")
IMAGE_EXT = ".svg"
FORBIDDEN_FILE_CHARS = set('<>:"|?*')


class ConfigError(Exception):
    """Ошибка конфигурации: содержит список всех найденных проблем."""

    def __init__(self, errors):
        """Сохранить список ошибок и сформировать общее сообщение."""
        self.errors = list(errors)
        super().__init__("\n".join(f"  - {e}" for e in self.errors))


def format_value(value):
    """Представить значение параметра как в XML (true/false)."""
    if isinstance(value, bool):
        return str(value).lower()
    return value


@dataclass
class Config:
    """Параметры, настраиваемые пользователем."""

    package: str
    repository: str
    test_mode: bool
    output: str
    ascii_tree: bool
    filter: str

    def items(self):
        """Вернуть параметры в виде пар (ключ, значение)."""
        return [(name, format_value(getattr(self, name)))
                for name in FIELDS]


def read_root(path):
    """Прочитать XML-файл и вернуть корневой элемент <config>."""
    if not os.path.isfile(path):
        raise ConfigError([f"config file not found: '{path}'"])
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        raise ConfigError([f"invalid XML in '{path}': {error}"]) from error
    if root.tag != ROOT_TAG:
        raise ConfigError(
            [f"root element must be <{ROOT_TAG}>, got <{root.tag}>"])
    return root


def collect_values(root, errors):
    """Собрать текст параметров из XML, проверяя состав тегов."""
    values = {}
    for child in root:
        if child.tag not in FIELDS:
            errors.append(f"unknown parameter <{child.tag}>")
        elif child.tag in values:
            errors.append(f"duplicate parameter <{child.tag}>")
        else:
            values[child.tag] = (child.text or "").strip()
    for name in FIELDS:
        if name not in values and name not in OPTIONAL_FIELDS:
            errors.append(f"missing parameter <{name}>")
    return values


def check_name(value, tag, errors, allow_empty=False):
    """Проверить имя пакета (или подстроку фильтра)."""
    if not value:
        if not allow_empty:
            errors.append(f"<{tag}> must not be empty")
        return
    if len(value) > MAX_NAME_LENGTH:
        errors.append(f"<{tag}> is longer than {MAX_NAME_LENGTH} chars")
    elif not NAME_RE.match(value):
        errors.append(f"<{tag}> may contain only letters, digits, "
                      f"'.', '_' and '-': '{value}'")


def parse_bool(value, tag, errors):
    """Преобразовать строку true/false в логическое значение."""
    key = value.lower()
    if key not in BOOL_VALUES:
        errors.append(f"<{tag}> must be true or false: '{value}'")
        return False
    return BOOL_VALUES[key]


def check_repository(value, test_mode, errors):
    """Проверить URL репозитория или путь к файлу тестового репозитория."""
    if not value:
        errors.append("<repository> must not be empty")
    elif test_mode:
        if not os.path.isfile(value):
            errors.append(f"test repository file not found: '{value}'")
    else:
        url = urlparse(value)
        if url.scheme not in URL_SCHEMES or not url.netloc:
            errors.append(f"<repository> must be an http(s) URL: '{value}'")


def check_output(value, errors):
    """Проверить имя файла с изображением графа."""
    if not value:
        errors.append("<output> must not be empty")
    elif not value.lower().endswith(IMAGE_EXT):
        errors.append(f"<output> must have {IMAGE_EXT} extension: "
                      f"'{value}'")
    elif FORBIDDEN_FILE_CHARS & set(os.path.basename(value)):
        errors.append(f"<output> contains forbidden characters: '{value}'")


def check_values(values, errors):
    """Проверить значения всех заданных параметров."""
    test_mode = parse_bool(values.get("test_mode", "false"),
                           "test_mode", errors)
    ascii_tree = parse_bool(values.get("ascii_tree", "false"),
                            "ascii_tree", errors)
    if "package" in values:
        check_name(values["package"], "package", errors)
    if "repository" in values:
        check_repository(values["repository"], test_mode, errors)
    if "output" in values:
        check_output(values["output"], errors)
    check_name(values.get("filter", ""), "filter", errors, allow_empty=True)
    return test_mode, ascii_tree


def load_config(path):
    """Загрузить и проверить конфигурацию. Бросает ConfigError."""
    root = read_root(path)
    errors = []
    values = collect_values(root, errors)
    test_mode, ascii_tree = check_values(values, errors)
    if errors:
        raise ConfigError(errors)
    return Config(values["package"], values["repository"], test_mode,
                  values["output"], ascii_tree, values.get("filter", ""))