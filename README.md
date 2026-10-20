# Визуализатор графа зависимостей NuGet (вариант 18)

CLI-инструмент для построения графа зависимостей пакетов .NET (NuGet).
Готовые менеджеры пакетов и библиотеки для получения зависимостей
не используются. Внешних зависимостей нет, нужен Python 3.10+.

## Запуск
```
run.bat [config.xml]        # Windows
./run.sh [config.xml]       # Linux / Git Bash
```
По умолчанию используется `config.xml` в текущем каталоге.

## Тесты
```
python -m unittest discover -s tests -v
```

## Этап 1. Конфигурация
Параметры задаются в XML-файле:
```xml
<config>
    <package>Serilog</package>
    <repository>https://api.nuget.org/v3-flatcontainer/</repository>
    <test_mode>false</test_mode>
    <output>graph.svg</output>
    <ascii_tree>true</ascii_tree>
    <filter></filter>
</config>
```

| Параметр     | Описание                                   | Проверка                                  |
|--------------|--------------------------------------------|-------------------------------------------|
| `package`    | имя анализируемого пакета                  | не пустое, `A-Z a-z 0-9 . _ -`, до 100 символов |
| `repository` | URL репозитория или путь к тестовому файлу | http(s)-URL, в тестовом режиме - существующий файл |
| `test_mode`  | режим работы с тестовым репозиторием       | `true` / `false`                          |
| `output`     | имя файла с изображением графа             | не пустое, расширение `.svg`              |
| `ascii_tree` | вывод зависимостей в виде ASCII-дерева     | `true` / `false`                          |
| `filter`     | подстрока для исключения пакетов           | необязательный; допустимые символы        |

При запуске все параметры выводятся в формате `ключ=значение`.
При ошибках выводится список **всех** найденных проблем, код выхода 1.

Демонстрация: `scripts\demo_stage1.bat` (примеры в папке `configs`).

## Этап 2. Сбор данных
Прямые зависимости пакета извлекаются из репозитория NuGet (API v3)
без менеджеров пакетов и сторонних библиотек:

1. `GET {repository}/{id}/index.json` - список версий, выбирается
   последняя стабильная (без суффикса `-beta`, `-rc` и т.п.);
2. `GET {repository}/{id}/{version}/{id}.nuspec` - описание пакета (XML);
3. из `.nuspec` извлекаются все `<dependency id="..." version="...">`;
   зависимости разных целевых платформ (`<group targetFramework>`)
   объединяются без повторов.

В `repository` можно указать адрес flat container
(`https://api.nuget.org/v3-flatcontainer/`) или служебный индекс
`https://api.nuget.org/v3/index.json`: тогда адрес хранилища
пакетов (`PackageBaseAddress`) берётся из него.

Пример вывода:
```
Package: Serilog 4.4.0
Direct dependencies (3):
  System.Diagnostics.DiagnosticSource 8.0.1
  System.Threading.Channels 8.0.0
  System.ValueTuple 4.5.0
```

Обрабатываемые ошибки: пакет не найден (HTTP 404), нет связи
с сервером, некорректный ответ (JSON/XML).

В тестовом режиме (`test_mode=true`) зависимости читаются из файла
вида `A: B C` (пакеты - заглавные латинские буквы).

Демонстрация: `scripts\demo_stage2.bat`.