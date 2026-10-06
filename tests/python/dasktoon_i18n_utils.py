# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Collect the strings a DaskToon source file shows, and check them against the active translation (test helper)."""

import ast
import contextlib
import re

import bpy

UI_KEYWORDS = {"text", "name", "description", "label", "title", "message", "confirm_text"}
TRANSLATE_CALLS = {"pgettext", "pgettext_iface", "pgettext_tip", "pgettext_rpt", "pgettext_data", "pgettext_n",
                   "iface_", "tip_", "rpt_", "n_", "data_"}
UI_BASES = {"Operator", "Panel", "Menu", "PropertyGroup", "UIList", "AddonPreferences"}
VI_CHARS = re.compile("[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ"
                      "ĂÂĐÊÔƠƯÀÁẢÃẠẰẮẲẴẶẦẤẨẪẬÈÉẺẼẸỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌỒỐỔỖỘỜỚỞỠỢÙÚỦŨỤỪỨỬỮỰỲÝỶỸỴ]")
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")


def _name(func):
    return func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")


def _literal(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _roots(tree, classes):
    """The parts of `tree` to scan: the whole file, or only the named top-level classes."""
    if classes is None:
        return [tree]
    return [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in classes]


def module_strings(path, classes=None):
    """(strings, dynamic): the user-visible string literals of a Python file, and the places where a visible string
    is built at run time (f-string or concatenation in text=/report/an error message), which cannot be translated."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    strings, dynamic = set(), []

    def take(node, where):
        value = _literal(node)
        if value is not None:
            strings.add(value)
        elif isinstance(node, ast.JoinedStr) or (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)):
            dynamic.append("%s line %d: %s" % (where, node.lineno, ast.unparse(node)[:80]))

    for node in (n for root in _roots(tree, classes) for n in ast.walk(root)):
        if isinstance(node, ast.Call):
            name = _name(node.func)
            if name in TRANSLATE_CALLS and node.args:
                take(node.args[0], name)
            if name == "report" and len(node.args) >= 2:
                take(node.args[1], "report")
            if name.endswith("Error") and node.args:
                take(node.args[0], name)
            for kw in node.keywords:
                if kw.arg in UI_KEYWORDS:
                    take(kw.value, kw.arg)
                if kw.arg == "items" and isinstance(kw.value, (ast.List, ast.Tuple)):
                    for item in kw.value.elts:
                        if isinstance(item, ast.Tuple):
                            for part in item.elts[1:3]:
                                take(part, "enum item")
        elif isinstance(node, ast.ClassDef):
            bases = {_name(b) for b in node.bases}
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id in ("bl_label", "bl_description"):
                            take(stmt.value, target.id)
            if bases & UI_BASES:
                doc = ast.get_docstring(node)
                if doc:
                    strings.add(doc)
    strings.discard("")
    return strings, dynamic


def all_strings(path, classes=None):
    """Every string constant of a Python file except docstrings of modules and functions: what may reach the user."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    docstrings = set()
    for node in (n for root in _roots(tree, classes) for n in ast.walk(root)):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and _literal(first.value) is not None:
                docstrings.add(id(first.value))
    return {node.value for node in (n for root in _roots(tree, classes) for n in ast.walk(root))
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings}


def visible(msgid):
    return re.search("[A-Za-z]", msgid) is not None


@contextlib.contextmanager
def language(code):
    view = bpy.context.preferences.view
    saved = view.language
    view.language = code
    try:
        yield
    finally:
        view.language = saved


def untranslated(msgids, keep=()):
    """The visible msgids that the active language shows unchanged (neither Blender nor DaskToon translates them)."""
    tr = bpy.app.translations
    missing = []
    for msgid in sorted(msgids):
        if not visible(msgid) or msgid in keep:
            continue
        if any(fn(msgid, ctx) != msgid for fn in (tr.pgettext_iface, tr.pgettext_tip, tr.pgettext_rpt)
               for ctx in ("*", "Operator")):
            continue
        missing.append(msgid)
    return missing
