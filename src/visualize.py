"""Визуализация графа: текст Graphviz (DOT), SVG и ASCII-дерево."""

import os
import subprocess

from graph import find_cycles

DOT_COMMAND = "dot"
DOT_EXT = ".dot"
DOT_TIMEOUT_SECONDS = 60
BRANCH = "|-- "
LAST_BRANCH = "\\-- "
PIPE = "|   "
SPACE = "    "
CYCLE_MARK = " (cycle)"
SHOWN_MARK = " (*)"


class VisualizeError(Exception):
    """Ошибка сохранения изображения графа."""


def quote(name):
    """Записать имя узла в кавычках, как требует язык DOT."""
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def cycle_edges(graph):
    """Вернуть множество рёбер (откуда, куда), входящих в циклы."""
    edges = set()
    for cycle in find_cycles(graph):
        edges.update(zip(cycle, cycle[1:]))
    return edges


def node_line(graph, name):
    """Описание узла: корень закрашен, ненайденные - пунктиром."""
    if name == graph.root:
        return (f"    {quote(name)} [style=\"rounded,filled\", "
                "fillcolor=lightblue];")
    if name in graph.missing:
        return f"    {quote(name)} [style=\"rounded,dashed\", color=gray];"
    return f"    {quote(name)};"


def to_dot(graph):
    """Сформировать текстовое представление графа на языке Graphviz."""
    in_cycles = cycle_edges(graph)
    lines = ["digraph dependencies {",
             "    rankdir=LR;",
             "    node [shape=box, style=rounded, fontname=Arial];"]
    lines.extend(node_line(graph, name) for name in graph.edges)
    for name, deps in graph.edges.items():
        for dep in deps:
            style = " [color=red]" if (name, dep) in in_cycles else ""
            lines.append(f"    {quote(name)} -> {quote(dep)}{style};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_text(path, text):
    """Записать текст в файл, создав при необходимости папку."""
    folder = os.path.dirname(path)
    try:
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
    except OSError as error:
        raise VisualizeError(f"cannot write '{path}': {error}") from error


def save_svg(dot_text, output, dot_command=DOT_COMMAND):
    """Сохранить DOT-файл рядом с output и построить SVG через Graphviz.

    Возвращает путь к сохранённому DOT-файлу.
    """
    dot_path = os.path.splitext(output)[0] + DOT_EXT
    write_text(dot_path, dot_text)
    command = [dot_command, "-Tsvg", "-o", output, dot_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=DOT_TIMEOUT_SECONDS, check=False)
    except FileNotFoundError as error:
        raise VisualizeError(
            f"Graphviz is not installed: command '{dot_command}' "
            "not found (https://graphviz.org/download/)") from error
    except subprocess.TimeoutExpired as error:
        raise VisualizeError("Graphviz did not finish in time") from error
    if result.returncode != 0:
        raise VisualizeError(f"Graphviz failed: {result.stderr.strip()}")
    return dot_path


def child_entries(graph, name, prefix, path):
    """Элементы стека для зависимостей пакета (в обратном порядке)."""
    deps = graph.edges.get(name, [])
    last = len(deps) - 1
    entries = [(dep, prefix, index == last, path)
               for index, dep in enumerate(deps)]
    entries.reverse()
    return entries


def ascii_tree(graph):
    """Вернуть строки ASCII-дерева зависимостей (обход без рекурсии).

    Пакет, уже показанный выше, повторно не раскрывается и помечается
    (*); возврат в пакет на текущем пути помечается (cycle).
    """
    lines = [graph.root]
    shown = {graph.root}
    stack = child_entries(graph, graph.root, "", (graph.root,))
    while stack:
        name, prefix, last, path = stack.pop()
        branch = LAST_BRANCH if last else BRANCH
        if name in path:
            lines.append(prefix + branch + name + CYCLE_MARK)
        elif name in shown:
            lines.append(prefix + branch + name + SHOWN_MARK)
        else:
            lines.append(prefix + branch + name)
            shown.add(name)
            child_prefix = prefix + (SPACE if last else PIPE)
            stack.extend(child_entries(graph, name, child_prefix,
                                       path + (name,)))
    return lines
