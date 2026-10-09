# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The DaskToon Anime Engine renders with EEVEE, so it shows the EEVEE settings: every panel that supports
BLENDER_EEVEE also supports DASKTOON_ANIME."""

import bpy

classes = ()


def register():
    for cls in bpy.types.Panel.__subclasses__():
        engines = getattr(cls, "COMPAT_ENGINES", None)
        if isinstance(engines, set) and 'BLENDER_EEVEE' in engines:
            engines.add('DASKTOON_ANIME')
