"""Тесты этапа 2: получение прямых зависимостей."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from repository import (FileRepository, NotFoundError,  # noqa: E402
                        NugetRepository, RepositoryError, choose_version,
                        parse_nuspec)

BASE = "https://api.nuget.org/v3-flatcontainer/"
NUSPEC = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>Serilog</id>
    <version>4.0.0</version>
    <dependencies>
      <group targetFramework=".NETFramework4.6.2">
        <dependency id="System.Diagnostics.DiagnosticSource"
                    version="8.0.1" />
        <dependency id="System.Threading.Channels" version="8.0.0" />
      </group>
      <group targetFramework="net6.0">
        <dependency id="System.Diagnostics.DiagnosticSource"
                    version="8.0.1" />
      </group>
      <group targetFramework="net8.0" />
    </dependencies>
  </metadata>
</package>"""


def fake_fetch(pages):
    """Создать функцию загрузки, отдающую текст из словаря pages."""
    def fetch(url):
        """Вернуть страницу url или сообщить, что её нет."""
        if url not in pages:
            raise NotFoundError(f"not found: {url}")
        return pages[url]
    return fetch


class NuspecTest(unittest.TestCase):
    """Разбор .nuspec и выбор версии."""

    def test_parse_groups(self):
        """Зависимости из всех групп объединяются без повторов."""
        deps = parse_nuspec(NUSPEC)
        self.assertEqual([name for name, _ in deps],
                         ["System.Diagnostics.DiagnosticSource",
                          "System.Threading.Channels"])

    def test_no_dependencies(self):
        """Пакет без зависимостей."""
        self.assertEqual(parse_nuspec("<package><metadata/></package>"), [])

    def test_bad_xml(self):
        """Повреждённый .nuspec."""
        with self.assertRaises(RepositoryError):
            parse_nuspec("<package>")

    def test_choose_version(self):
        """Выбирается последняя стабильная версия."""
        self.assertEqual(choose_version(["1.0.0", "2.0.0", "3.0.0-beta"]),
                         "2.0.0")
        self.assertEqual(choose_version(["1.0.0-rc"]), "1.0.0-rc")
        with self.assertRaises(RepositoryError):
            choose_version([])


class NugetRepositoryTest(unittest.TestCase):
    """Работа с репозиторием NuGet через подменённую загрузку."""

    def setUp(self):
        """Подготовить репозиторий с двумя страницами."""
        pages = {
            BASE + "serilog/index.json": '{"versions": ["3.1.1", "4.0.0"]}',
            BASE + "serilog/4.0.0/serilog.nuspec": NUSPEC,
        }
        self.repo = NugetRepository(BASE, fetch=fake_fetch(pages))

    def test_direct_dependencies(self):
        """Версия и прямые зависимости пакета."""
        version, deps = self.repo.direct_dependencies("Serilog")
        self.assertEqual(version, "4.0.0")
        self.assertEqual(deps[1], ("System.Threading.Channels", "8.0.0"))

    def test_names_only(self):
        """get_dependencies возвращает только имена."""
        self.assertEqual(len(self.repo.get_dependencies("Serilog")), 2)

    def test_not_found(self):
        """Неизвестный пакет - ошибка."""
        with self.assertRaises(RepositoryError):
            self.repo.get_dependencies("NoSuchPackage")

    def test_bad_json(self):
        """Некорректный ответ сервера."""
        repo = NugetRepository(BASE, fetch=lambda url: "not json")
        with self.assertRaises(RepositoryError):
            repo.get_dependencies("Serilog")


class ServiceIndexTest(unittest.TestCase):
    """Адрес репозитория в виде служебного индекса api.nuget.org/v3."""

    def test_find_base_address(self):
        """Адрес flat container берётся из index.json."""
        index = ('{"resources": [{"@id": "' + BASE + '", '
                 '"@type": "PackageBaseAddress/3.0.0"}]}')
        url = "https://api.nuget.org/v3/index.json"
        repo = NugetRepository(url, fetch=fake_fetch({url: index}))
        self.assertEqual(repo.base_url, BASE)

    def test_bad_index(self):
        """В индексе нет нужного ресурса."""
        url = "https://api.nuget.org/v3/index.json"
        with self.assertRaises(RepositoryError):
            NugetRepository(url, fetch=fake_fetch({url: '{"resources": []}'}))


class FileRepositoryTest(unittest.TestCase):
    """Тестовый репозиторий из файла."""

    def load(self, text):
        """Записать text во временный файл и загрузить репозиторий."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "repo.txt")
            with open(path, "w", encoding="utf-8") as file:
                file.write(text)
            return FileRepository(path)

    def test_simple(self):
        """Файл repos/simple.txt."""
        path = os.path.join(os.path.dirname(__file__), "..",
                            "repos", "simple.txt")
        repo = FileRepository(path)
        self.assertEqual(repo.get_dependencies("A"), ["B", "C"])
        self.assertEqual(repo.get_dependencies("D"), [])

    def test_errors(self):
        """Неверный формат, строчные буквы, дубликат."""
        for text in ("A B\n", "A: b\n", "A: B\nA: C\n", "a1: B\n"):
            with self.assertRaises(RepositoryError):
                self.load(text)

    def test_unknown_package(self):
        """Пакета нет в тестовом репозитории."""
        with self.assertRaises(RepositoryError):
            self.load("A: B\n").get_dependencies("Z")


if __name__ == "__main__":
    unittest.main()