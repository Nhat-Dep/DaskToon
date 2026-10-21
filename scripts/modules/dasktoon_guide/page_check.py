# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The check a writer of the Guide's pages runs before handing them in (docs/guide-writing/rules.md): every page in
both languages and reached from the index, the two languages with the same sections and pictures, every link and
picture there, and every button name in <b> one the interface shows in that language: DaskToon's own
(bl_ui/dasktoon_translations.py) or Blender's (its Vietnamese .mo). <b> holds interface names only; "›" separates the
steps of a path (Add › Armature › Anime Humanoid).

DaskToon.exe -b --factory-startup --python tools/dasktoon_guide_check.py"""

import functools
import gettext
import html.parser
import os

LANGUAGES = ("en", "vi")
PATH_SEPARATOR = "›"


class _Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.sections = []
        self.pictures = []
        self.links = []  # (target, anchor) of every href and src that is not a web address
        self.names = []  # the text of every <b>
        self._bold = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang")
        if tag == "section" and attrs.get("id"):
            self.sections.append(attrs["id"])
        if tag == "img" and attrs.get("src"):
            self.pictures.append(attrs["src"])
        for key in ("href", "src"):
            value = attrs.get(key)
            if value and ":" not in value:
                target, _sep, anchor = value.partition("#")
                self.links.append((target, anchor))
        if tag == "b":
            self._bold = []

    def handle_data(self, data):
        if self._bold is not None:
            self._bold.append(data)

    def handle_endtag(self, tag):
        if tag == "b" and self._bold is not None:
            self.names.append(" ".join("".join(self._bold).split()))
            self._bold = None


def _read(path):
    page = _Page()
    with open(path, encoding="utf-8") as f:
        page.feed(f.read())
    return page


def _rna_names():
    """The English names Blender and DaskToon declare: panels, menus, tabs, operators, properties, enum items."""
    import bpy
    names = set()
    for attr in dir(bpy.types):
        cls = getattr(bpy.types, attr, None)
        for key in ("bl_label", "bl_category"):
            value = getattr(cls, key, None)
            if isinstance(value, str):
                names.add(value)
        rna = getattr(cls, "bl_rna", None)
        if rna is None:
            continue
        names.add(rna.name)
        for prop in rna.properties:
            names.add(prop.name)
            if prop.type == 'ENUM':
                names |= {item.name for item in prop.enum_items}
    for module in dir(bpy.ops):
        for op in dir(getattr(bpy.ops, module)):
            try:
                names.add(getattr(getattr(bpy.ops, module), op).get_rna_type().name)
            except (AttributeError, KeyError, RuntimeError):
                pass
    return names


@functools.lru_cache(maxsize=None)
def ui_names(language):
    """Every name the interface shows in `language`. English: DaskToon's source strings, Blender's names and
    translated strings, the anime brushes. Vietnamese: DaskToon's and Blender's Vietnamese, and the English names that
    have no Vietnamese (the interface shows those in English)."""
    import bpy
    from bl_ui import dasktoon_translations as tr
    from dasktoon_paint import brushes
    english = set(tr.KEEP) | set(tr.VI) | {name for name, _settings in brushes.BRUSHES.values()} | {"?"}
    vietnamese = set(tr.KEEP) | set(tr.VI.values())
    translated = set(tr.VI)
    for entries in tr.VI_CONTEXT.values():
        english |= set(entries)
        vietnamese |= set(entries.values())
    mo = os.path.join(bpy.utils.system_resource('DATAFILES'), "locale", "vi", "LC_MESSAGES", "blender.mo")
    if os.path.exists(mo):
        with open(mo, "rb") as f:
            catalog = gettext.GNUTranslations(f)._catalog
        for msgid, msgstr in catalog.items():
            if isinstance(msgid, str) and msgid:
                english.add(msgid.split("\x04")[-1])
                translated.add(msgid.split("\x04")[-1])
                vietnamese.add(msgstr)
    english |= _rna_names()
    if language == "en":
        return frozenset(english)
    return frozenset(vietnamese | (english - translated))


def _known(name, names):
    return name in names or name + "…" in names or name + "..." in names


def problems(root):
    """[problem line] of the pages under `root` (<root>/en, <root>/vi, <root>/pictures, <root>/guide.css)."""
    out = []
    files = {language: sorted(n for n in os.listdir(os.path.join(root, language)) if n.endswith(".html"))
             for language in LANGUAGES}
    pages = {}
    for language in LANGUAGES:
        other = LANGUAGES[1 - LANGUAGES.index(language)]
        for name in files[language]:
            where = "%s/%s" % (language, name)
            page = pages[language, name] = _read(os.path.join(root, language, name))
            if name not in files[other]:
                out.append("%s: there is no %s/%s" % (where, other, name))
            if page.lang != language:
                out.append('%s: <html lang="%s"> should be lang="%s"' % (where, page.lang, language))
            if ("../%s/%s" % (other, name), "") not in page.links:
                out.append("%s: no link to the same page in the other language (../%s/%s)" % (where, other, name))
            for target, anchor in page.links:
                path = os.path.normpath(os.path.join(root, language, target or name))
                if not os.path.exists(path):
                    out.append("%s: %s is not there" % (where, target))
                elif anchor and path.endswith(".html") and anchor not in _read(path).sections:
                    out.append('%s: %s has no section id="%s"' % (where, target or name, anchor))
            names = ui_names(language)
            for text in page.names:
                for step in (s.strip() for s in text.split(PATH_SEPARATOR)):
                    if not _known(step, names):
                        out.append("%s: <b>%s</b>: '%s' is not a name the interface shows in this language "
                                   "(<b> is for button and panel names only)" % (where, text, step))
    for name in files["en"]:
        if name not in files["vi"]:
            continue
        en, vi = pages["en", name], pages["vi", name]
        for label, a, b in (("section", en.sections, vi.sections), ("picture", en.pictures, vi.pictures)):
            for item in sorted(set(a) ^ set(b)):
                out.append('%s: %s "%s" is in %s only' % (name, label, item, "en" if item in a else "vi"))
    # Every page reached from the index by links.
    for language in LANGUAGES:
        reached, todo = set(), ["index.html"]
        while todo:
            name = todo.pop()
            if name in reached or (language, name) not in pages:
                continue
            reached.add(name)
            todo += [os.path.basename(t) for t, _a in pages[language, name].links
                     if t.endswith(".html") and "/" not in t]
        for name in files[language]:
            if name not in reached:
                out.append("%s/%s: no page links to it from index.html" % (language, name))
    return out
