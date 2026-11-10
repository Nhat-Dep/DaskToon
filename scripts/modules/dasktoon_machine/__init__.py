# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon machine rig (docs/superpowers/specs/2026-11-10-dasktoon-machine-rig-design.md): rigid pieces on joints,
joint kinds and limits, IK legs, aiming. A machine is an armature whose data has `dasktoon_machine.is_machine`; each
piece of its meshes is weighted 100% to one bone, the root holding the pieces not given a joint yet. The interface is
bl_ui/dasktoon_machine.py."""

import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_

ROOT = "Root"
MODIFIER = "DT Machine"


class MachineError(Exception):
    pass


def is_machine(obj):
    return (obj is not None and obj.type == 'ARMATURE' and
            getattr(obj.data, "dasktoon_machine", None) is not None and obj.data.dasktoon_machine.is_machine)


def root_name(rig):
    return rig.data.dasktoon_machine.root or ROOT


def meshes(rig):
    """The meshes the machine moves: those with an Armature modifier on it."""
    return [o for o in bpy.data.objects if o.type == 'MESH' and any(
        m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]


def rig_of_mesh(obj):
    if obj is None or obj.type != 'MESH':
        return None
    for m in obj.modifiers:
        if m.type == 'ARMATURE' and is_machine(m.object):
            return m.object
    return None


def set_mode(context, obj, mode):
    """`obj` active and alone selected, in `mode`."""
    active = context.view_layer.objects.active
    if active is not None and active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in context.view_layer.objects:
        o.select_set(o == obj)
    context.view_layer.objects.active = obj
    if mode != 'OBJECT':
        bpy.ops.object.mode_set(mode=mode)


class EditSession:
    """`with EditSession(context, rig) as edit_bones:` the rig in Edit Mode; afterwards back to the mode and active
    object it had (Pose Mode stays Pose Mode)."""

    def __init__(self, context, rig):
        self.context, self.rig = context, rig

    def __enter__(self):
        context = self.context
        self.active = context.view_layer.objects.active
        self.mode = self.active.mode if self.active is not None else 'OBJECT'
        self.selected = [o for o in context.view_layer.objects if o.select_get()]
        self.hidden = self.rig.hide_get()
        self.rig.hide_set(False)
        set_mode(context, self.rig, 'EDIT')
        return self.rig.data.edit_bones

    def __exit__(self, *_exc):
        context = self.context
        bpy.ops.object.mode_set(mode='OBJECT')
        self.rig.hide_set(self.hidden)
        for o in context.view_layer.objects:
            o.select_set(o in self.selected)
        if self.active is not None and self.active.name in context.view_layer.objects:
            context.view_layer.objects.active = self.active
            if self.mode != 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode=self.mode)
                except (RuntimeError, TypeError):
                    pass
        return False


def _world_points(obj):
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    mw = np.array(obj.matrix_world)
    return co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]


def add_modifier(obj, rig):
    """The Armature modifier on `rig`, first in the stack (before the outline and anything that makes geometry)."""
    mod = next((m for m in obj.modifiers if m.type == 'ARMATURE' and m.object == rig), None)
    if mod is None:
        mod = obj.modifiers.new(MODIFIER, 'ARMATURE')
        mod.object = rig
    mod.use_vertex_groups = True
    mod.use_bone_envelopes = False
    index = list(obj.modifiers).index(mod)
    if index:
        obj.modifiers.move(index, 0)
    return mod


def create(context, objects, name=None):
    """A machine rig for the meshes `objects`: an armature "<name> Machine" with one Root bone at the middle of the
    floor of their bounds, every vertex on it. Returns the armature object."""
    objects = [o for o in objects if o.type == 'MESH']
    if not objects:
        raise MachineError(rpt_("Select the meshes of the machine first"))
    taken = [o.name for o in objects if rig_of_mesh(o) is not None]
    if taken:
        raise MachineError(rpt_("Already part of a machine: %s") % ", ".join(taken))
    points = np.concatenate([_world_points(o) for o in objects if len(o.data.vertices)] or [np.zeros((1, 3))])
    lo, hi = points.min(axis=0), points.max(axis=0)
    size = float(np.linalg.norm(hi - lo)) or 1.0
    base = (lo + hi) / 2
    base[2] = lo[2]
    name = name or objects[0].name
    arm = bpy.data.armatures.new(rpt_("%s Machine") % name)
    rig = bpy.data.objects.new(arm.name, arm)
    collection = objects[0].users_collection[0] if objects[0].users_collection else context.scene.collection
    collection.objects.link(rig)
    arm.dasktoon_machine.is_machine = True
    arm.dasktoon_machine.root = ROOT
    arm.display_type = 'WIRE'
    rig.show_in_front = True
    with EditSession(context, rig) as edit_bones:
        eb = edit_bones.new(ROOT)
        eb.head = base
        eb.tail = base + np.array((0.0, size * 0.25, 0.0))
        eb.roll = 0.0
    from . import pieces, shapes
    for obj in objects:
        pieces.ensure(obj)
        group = obj.vertex_groups.get(ROOT) or obj.vertex_groups.new(name=ROOT)
        group.add(range(len(obj.data.vertices)), 1.0, 'REPLACE')
        add_modifier(obj, rig)
    shapes.style_root(rig)
    return rig
