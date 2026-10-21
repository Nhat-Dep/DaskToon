# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Checks the Guide's pages in this repository (dasktoon_guide.page_check; the rules: docs/guide-writing/rules.md) and
prints every problem; exits with 1 while there are any. Sync the build first, so DaskToon has this repository's
translations:

<DaskToon 5.2 folder>/python/bin/python.exe tools/dasktoon_sync_build.py <DaskToon 5.2 folder>
DaskToon.exe -b --factory-startup --python tools/dasktoon_guide_check.py
"""
import os
import sys

from dasktoon_guide import page_check

PAGES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "scripts", "modules", "dasktoon_guide", "pages")

found = page_check.problems(PAGES)
for line in found:
    print("PROBLEM", line)
print("GUIDE CHECK: %d problems" % len(found))
sys.exit(1 if found else 0)
