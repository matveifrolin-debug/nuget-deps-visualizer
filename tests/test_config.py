"""Тесты этапа 1: загрузка и проверка XML-конфигурации."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import ConfigError, load_config  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
VALID = {
    "package": "Serilog",
    "repository": "https://api.nuget.org/v3-flatcontainer/",
    "test_mode": "false",
    "output": "graph.svg",
    "ascii_tree": "true",
    "filter": "",
}


def make_xml(values, root="config"):
    """Сформировать текст XML-конфигурации из словаря."""
    body = "".join(f"<{k}>{v}</{k}>" for k, v in values.items())
    return f"<{root}>{body}</{root}>"


class ConfigTestCase(unittest.TestCase):
    """Базовый класс: запись конфигурации во временный файл."""

    def load(self, text):
        """Записать text во временный файл и загрузить конфигурацию."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "config.xml")
            with open(path, "w", encoding="utf-8") as file:
                file.write(text)
            return load_config(path)

    def errors_for(self, text):
        """Вернуть список ошибок для конфигурации text."""
        with self.assertRaises(ConfigError) as context:
            self.load(text)
        return context.exception.errors

    def with_value(self, name, value):
        """Ошибки для корректной конфигурации с одним изменённым полем."""
        values = dict(VALID, **{name: value})
        return self.errors_for(make_xml(values))


class ValidConfigTest(ConfigTestCase):
    """Проверки корректных конфигураций."""

    def test_valid(self):
        """Все параметры считываются."""
        config = self.load(make_xml(VALID))
        self.assertEqual(config.package, "Serilog")
        self.assertFalse(config.test_mode)
        self.assertTrue(config.ascii_tree)

    def test_items(self):
        """Параметры выводятся в формате ключ-значение."""
        items = dict(self.load(make_xml(VALID)).items())
        self.assertEqual(items["test_mode"], "false")
        self.assertEqual(list(items), list(VALID))

    def test_filter_optional(self):
        """Параметр filter можно не указывать."""
        values = {k: v for k, v in VALID.items() if k != "filter"}
        self.assertEqual(self.load(make_xml(values)).filter, "")

    def test_example_files(self):
        """Примеры configs/config.xml и configs/test_mode.xml корректны."""
        old = os.getcwd()
        os.chdir(ROOT)
        try:
            self.assertTrue(load_config("configs/test_mode.xml").test_mode)
            self.assertFalse(load_config("configs/config.xml").test_mode)
        finally:
            os.chdir(old)


class FileErrorTest(ConfigTestCase):
    """Ошибки файла конфигурации."""

    def test_not_found(self):
        """Файл не найден."""
        with self.assertRaises(ConfigError):
            load_config("no_such_config.xml")

    def test_bad_xml(self):
        """Повреждённый XML."""
        self.assertTrue(self.errors_for("<config><package>"))

    def test_bad_root(self):
        """Неверный корневой элемент."""
        self.assertTrue(self.errors_for(make_xml(VALID, root="settings")))

    def test_unknown_duplicate_missing(self):
        """Неизвестный, повторный и отсутствующий параметры."""
        text = "<config><package>A</package><package>B</package>" \
               "<color>red</color></config>"
        errors = self.errors_for(text)
        self.assertTrue(any("unknown" in e for e in errors))
        self.assertTrue(any("duplicate" in e for e in errors))
        self.assertTrue(any("missing parameter <output>" in e
                            for e in errors))


class ValueErrorTest(ConfigTestCase):
    """Ошибки значений каждого параметра."""

    def test_package(self):
        """Пустое, недопустимое и слишком длинное имя пакета."""
        self.assertTrue(self.with_value("package", ""))
        self.assertTrue(self.with_value("package", "bad name!"))
        self.assertTrue(self.with_value("package", "A" * 101))

    def test_repository(self):
        """Не http(s) URL и пустой репозиторий."""
        self.assertTrue(self.with_value("repository", "ftp://x.org"))
        self.assertTrue(self.with_value("repository", "not a url"))
        self.assertTrue(self.with_value("repository", ""))

    def test_test_repository_missing(self):
        """В тестовом режиме файл репозитория должен существовать."""
        values = dict(VALID, test_mode="true", repository="no_such.txt")
        self.assertTrue(self.errors_for(make_xml(values)))

    def test_bools(self):
        """test_mode и ascii_tree принимают только true/false."""
        self.assertTrue(self.with_value("test_mode", "yes"))
        self.assertTrue(self.with_value("ascii_tree", "1"))

    def test_output(self):
        """Пустое имя, не .svg и запрещённые символы."""
        self.assertTrue(self.with_value("output", ""))
        self.assertTrue(self.with_value("output", "graph.png"))
        self.assertTrue(self.with_value("output", "gr?aph.svg"))

    def test_filter(self):
        """Подстрока фильтра с недопустимыми символами."""
        self.assertTrue(self.with_value("filter", "a b"))

    def test_all_errors_reported(self):
        """Сообщаются сразу все ошибки, а не только первая."""
        values = {"package": "!", "repository": "x", "test_mode": "yes",
                  "output": "a.png", "ascii_tree": "no", "filter": "a b"}
        self.assertEqual(len(self.errors_for(make_xml(values))), 6)


if __name__ == "__main__":
    unittest.main()