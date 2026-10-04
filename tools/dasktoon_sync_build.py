#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Make an installed DaskToon match this repository: scripts/startup, scripts/modules and the translations.

    python tools/dasktoon_sync_build.py D:/build_windows_x64_vc17_Release/bin/Release/5.2 [--dry-run]

Changed files are copied, and files or folders the repository does not have are removed: copying alone left removed
modules behind, and Blender kept loading them. datafiles/locale/languages is copied and installed language folders
without a locale/po/<language>.po are removed."""

import argparse
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRRORED = ("scripts/startup", "scripts/modules")
SKIP = {"__pycache__"}


def same_file(a, b):
    """Byte comparison. filecmp caches by size and mtime, so two files of the same size written in the same instant
    would still count as different after one was copied over the other."""
    if not os.path.isfile(b) or os.path.getsize(a) != os.path.getsize(b):
        return False
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


def mirror_tree(src, dst, dry_run=False):
    """Make `dst` a copy of `src`, leaving __pycache__ folders alone. Returns [(verb, relative path)]."""
    actions = []
    for base, dirs, names in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        rel = os.path.relpath(base, src)
        for name in sorted(names):
            source = os.path.join(base, name)
            target = os.path.normpath(os.path.join(dst, rel, name))
            if not same_file(source, target):
                actions.append(("copy", os.path.normpath(os.path.join(rel, name))))
                if not dry_run:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    shutil.copy2(source, target)
    if not os.path.isdir(dst):
        return actions
    for base, dirs, names in os.walk(dst):
        rel = os.path.relpath(base, dst)
        source_dir = os.path.normpath(os.path.join(src, rel))
        kept = []
        for name in sorted(dirs):
            if name in SKIP:
                continue
            if os.path.isdir(os.path.join(source_dir, name)):
                kept.append(name)
                continue
            actions.append(("remove", os.path.normpath(os.path.join(rel, name)) + os.sep))
            if not dry_run:
                shutil.rmtree(os.path.join(base, name))
        dirs[:] = kept
        for name in sorted(names):
            if not os.path.exists(os.path.join(source_dir, name)):
                actions.append(("remove", os.path.normpath(os.path.join(rel, name))))
                if not dry_run:
                    os.remove(os.path.join(base, name))
    return actions


def sync_locale(repo, install, dry_run=False):
    """Copy locale/languages and remove installed language folders that have no .po file in the repository."""
    actions = []
    locale_dir = os.path.join(install, "datafiles", "locale")
    source = os.path.join(repo, "locale", "languages")
    target = os.path.join(locale_dir, "languages")
    if not same_file(source, target):
        actions.append(("copy", "datafiles/locale/languages"))
        if not dry_run:
            os.makedirs(locale_dir, exist_ok=True)
            shutil.copy2(source, target)
    kept = {os.path.splitext(n)[0] for n in os.listdir(os.path.join(repo, "locale", "po")) if n.endswith(".po")}
    if os.path.isdir(locale_dir):
        for name in sorted(os.listdir(locale_dir)):
            if os.path.isdir(os.path.join(locale_dir, name)) and name not in kept:
                actions.append(("remove", "datafiles/locale/%s/" % name))
                if not dry_run:
                    shutil.rmtree(os.path.join(locale_dir, name))
    return actions


def sync(install, dry_run=False, repo=REPO):
    actions = []
    for sub in MIRRORED:
        name = os.path.basename(sub)
        actions += [(verb, "scripts/%s/%s" % (name, path)) for verb, path in
                    mirror_tree(os.path.join(repo, *sub.split("/")), os.path.join(install, "scripts", name), dry_run)]
    actions += sync_locale(repo, install, dry_run)
    return actions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("install", help="the version folder of the install, e.g. .../bin/Release/5.2")
    parser.add_argument("--dry-run", action="store_true", help="only list what would change")
    args = parser.parse_args(argv)
    if not os.path.isdir(os.path.join(args.install, "scripts")):
        parser.error("%s has no scripts folder" % args.install)
    actions = sync(args.install, args.dry_run)
    for verb, path in actions:
        print("%-6s %s" % (verb, path.replace(os.sep, "/")))
    print("%d change(s)%s" % (len(actions), " (dry run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
