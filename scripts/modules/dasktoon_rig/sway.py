# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Live sway of the generated chains (anime rig spec 9.4); the next task fills it in."""

_cache = {}


def clear_cache(rig=None):
    if rig is None:
        _cache.clear()
    else:
        _cache.pop(rig.session_uid, None)
