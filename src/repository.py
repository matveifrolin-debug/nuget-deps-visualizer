"""Источники данных о зависимостях: репозиторий NuGet и тестовый файл.

Оба класса предоставляют методы:
get_dependencies(name)     - список имён прямых зависимостей;
direct_dependencies(name)  - (версия пакета, [(зависимость, версия)]).
"""

import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree

TIMEOUT_SECONDS = 15
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2
HTTP_NOT_FOUND = 404
PRERELEASE_MARK = "-"
TEST_NAME_RE = re.compile(r"^[A-Z]+$")
COMMENT = "#"
SERVICE_INDEX = "index.json"
BASE_ADDRESS_TYPE = "PackageBaseAddress"


class RepositoryError(Exception):
    """Ошибка получения данных о зависимостях."""


class NotFoundError(RepositoryError):
    """Запрошенный ресурс (пакет) отсутствует в репозитории."""


def http_get_once(url):
    """Один раз скачать url и вернуть текст ответа."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "nuget-deps-visualizer"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as r:
            return r.read().decode("utf-8-sig")
    except urllib.error.HTTPError as error:
        if error.code == HTTP_NOT_FOUND:
            raise NotFoundError(f"not found: {url}") from error
        raise RepositoryError(f"HTTP {error.code} for {url}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RepositoryError(f"cannot connect to {url}: {error}") from error


def http_get(url):
    """Скачать url, повторяя попытку при сбое сети. Бросает RepositoryError.

    Отсутствие ресурса (HTTP 404) не повторяется: сразу NotFoundError.
    """
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return http_get_once(url)
        except NotFoundError:
            raise
        except RepositoryError:
            if attempt == RETRY_ATTEMPTS:
                raise
            time.sleep(RETRY_DELAY_SECONDS)
    raise RepositoryError(f"cannot download {url}")


def choose_version(versions):
    """Выбрать последнюю стабильную версию (без суффикса -beta и т.п.)."""
    if not versions:
        raise RepositoryError("package has no versions")
    stable = [v for v in versions if PRERELEASE_MARK not in v]
    return (stable or versions)[-1]


def local_name(tag):
    """Вернуть имя XML-тега без пространства имён {...}."""
    return tag.rsplit("}", 1)[-1]


def parse_nuspec(text):
    """Извлечь прямые зависимости из XML-файла .nuspec.

    Зависимости могут быть разбиты на группы по целевым платформам
    (<group targetFramework=...>); возвращается их объединение без
    повторов: список пар (имя, версия).
    """
    try:
        root = xml.etree.ElementTree.fromstring(text)
    except xml.etree.ElementTree.ParseError as error:
        raise RepositoryError(f"invalid .nuspec XML: {error}") from error
    result, seen = [], set()
    for element in root.iter():
        if local_name(element.tag) != "dependency":
            continue
        name = element.get("id", "").strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            result.append((name, element.get("version", "")))
    return result


def find_flat_container(service_index):
    """Найти адрес PackageBaseAddress в служебном индексе NuGet v3."""
    try:
        resources = json.loads(service_index).get("resources", [])
    except (json.JSONDecodeError, AttributeError) as error:
        raise RepositoryError("invalid NuGet service index") from error
    for resource in resources:
        if str(resource.get("@type", "")).startswith(BASE_ADDRESS_TYPE):
            return resource.get("@id", "")
    raise RepositoryError("PackageBaseAddress not found in service index")


class NugetRepository:
    """Репозиторий NuGet (API v3 flat container).

    Можно указать либо служебный индекс .../v3/index.json (адрес
    хранилища пакетов будет найден в нём), либо сразу адрес
    flat container (.../v3-flatcontainer/).
    """

    def __init__(self, base_url, fetch=http_get):
        """base_url - адрес репозитория; fetch - функция загрузки."""
        if base_url.endswith(SERVICE_INDEX):
            base_url = find_flat_container(fetch(base_url))
        self.base_url = base_url.rstrip("/") + "/"
        self.fetch = fetch
        self.versions = {}

    def latest_version(self, name):
        """Узнать последнюю стабильную версию пакета."""
        url = f"{self.base_url}{name.lower()}/index.json"
        try:
            data = json.loads(self.fetch(url))
        except NotFoundError as error:
            raise NotFoundError(
                f"package '{name}' not found in repository") from error
        except json.JSONDecodeError as error:
            raise RepositoryError(f"invalid JSON from {url}") from error
        return choose_version(data.get("versions", []))

    def direct_dependencies(self, name):
        """Вернуть (версия пакета, список пар (зависимость, версия))."""
        version = self.latest_version(name)
        self.versions[name] = version
        lower = name.lower()
        url = f"{self.base_url}{lower}/{version.lower()}/{lower}.nuspec"
        return version, parse_nuspec(self.fetch(url))

    def get_dependencies(self, name):
        """Вернуть список имён прямых зависимостей пакета."""
        _, deps = self.direct_dependencies(name)
        return [dep for dep, _ in deps]


def parse_test_line(line, number):
    """Разобрать строку тестового репозитория 'A: B C'."""
    if ":" not in line:
        raise RepositoryError(f"line {number}: expected 'NAME: DEPS'")
    name, _, deps = line.partition(":")
    names = [name.strip()] + deps.split()
    for item in names:
        if not TEST_NAME_RE.match(item):
            raise RepositoryError(
                f"line {number}: package names must be capital Latin "
                f"letters: '{item}'")
    return names[0], names[1:]


class FileRepository:
    """Тестовый репозиторий из файла: строки вида 'A: B C'."""

    def __init__(self, path):
        """Прочитать файл описания графа."""
        self.graph = {}
        try:
            with open(path, encoding="utf-8") as file:
                lines = file.read().splitlines()
        except OSError as error:
            raise RepositoryError(f"cannot read '{path}': {error}") from error
        for number, raw in enumerate(lines, start=1):
            line = raw.split(COMMENT, 1)[0].strip()
            if not line:
                continue
            name, deps = parse_test_line(line, number)
            if name in self.graph:
                raise RepositoryError(f"line {number}: duplicate '{name}'")
            self.graph[name] = deps

    def get_dependencies(self, name):
        """Вернуть список прямых зависимостей пакета."""
        if name not in self.graph:
            raise NotFoundError(f"package '{name}' not found in repository")
        return list(self.graph[name])

    def direct_dependencies(self, name):
        """Вернуть ('', список пар (зависимость, '')): версий нет."""
        return "", [(dep, "") for dep in self.get_dependencies(name)]


def open_repository(config):
    """Создать репозиторий по конфигурации (тестовый или NuGet)."""
    if config.test_mode:
        return FileRepository(config.repository)
    return NugetRepository(config.repository)