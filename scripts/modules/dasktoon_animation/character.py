# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""A character (Animation tab spec 4): an armature, the objects that have it among their parents (hair, accessories, a
weapon on a bone) and the objects whose Armature modifiers use it. The Dope Sheet's Whole Character filter applies the
same rule in C++ (anim_filter.cc)."""


def armatures_of(obj):
    """The armatures whose characters `obj` belongs to: itself, an armature among its parents, the objects of its
    Armature modifiers; no duplicates, in that order."""
    found = []
    if obj.type == 'ARMATURE':
        found.append(obj)
    parent = obj.parent
    while parent is not None:
        if parent.type == 'ARMATURE':
            found.append(parent)
        parent = parent.parent
    for modifier in obj.modifiers:
        if modifier.type == 'ARMATURE' and modifier.object is not None:
            found.append(modifier.object)
    return list(dict.fromkeys(found))


def members(armature, objects):
    """The objects of `objects` that belong to the character of `armature` (the armature itself included)."""
    return [obj for obj in objects if armature in armatures_of(obj)]


def selected_characters(context):
    """The armatures of the characters that have a selected part (an object in Pose Mode counts as selected, as for the
    Dope Sheet's Only Show Selected), sorted by name."""
    found = {armature for obj in context.view_layer.objects if obj.select_get() or obj.mode == 'POSE'
             for armature in armatures_of(obj)}
    return sorted(found, key=lambda armature: armature.name)
