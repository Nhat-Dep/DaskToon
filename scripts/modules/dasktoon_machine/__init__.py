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


def drive(rig, con, target, prop, expression):
    """The influence of constraint `con` driven by the custom property `prop` of pose bone `target` through a simple
    expression in `v` (no Python needed to run it)."""
    driver = con.driver_add("influence").driver
    driver.type = 'SCRIPTED'
    for v in list(driver.variables):
        driver.variables.remove(v)
    var = driver.variables.new()
    var.name, var.type = "v", 'SINGLE_PROP'
    var.targets[0].id_type = 'OBJECT'
    var.targets[0].id = rig
    var.targets[0].data_path = 'pose.bones["%s"]["%s"]' % (target.replace('"', '\\"'), prop)
    driver.expression = expression


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


SPLIT = 0.6  # a piece whose strongest bone has less than this share of its weights is split between bones ...
SPLIT_VERTS = 0.05  # ... and so is one with this share of its vertices held mostly by another bone (a leg grown out of
# a body: one skin over several bones)


def adopt(context, rig):
    """Make the pieces of the meshes on an armature with its own skeleton rigid (machine rig spec 6): each piece goes
    100% to the bone holding most of it. A piece split between bones keeps its weights: making it rigid would stop it
    bending; it is reported for the user to cut it into pieces. The armature becomes a machine, its first root bone
    the root. Returns (number of pieces, [pieces split between bones])."""
    from . import joints, pieces, shapes
    arm = rig.data
    roots = [b for b in arm.bones if b.parent is None]
    if not roots:
        raise MachineError(rpt_("The armature has no bones"))
    objects = meshes(rig)
    if not objects:
        raise MachineError(rpt_("No mesh is moved by this armature"))
    if not arm.dasktoon_machine.is_machine:
        arm.dasktoon_machine.is_machine = True
        arm.dasktoon_machine.root = roots[0].name
    bones = {b.name for b in arm.bones}
    count, split, holding = 0, [], set()
    for obj in objects:
        ids = pieces.ensure(obj)
        groups = {g.index: g.name for g in obj.vertex_groups if g.name in bones}
        totals, members, strongest = {}, {name: [] for name in groups.values()}, {}
        for v in obj.data.vertices:
            piece = int(ids[v.index])
            best = (None, 0.5)
            for g in v.groups:
                name = groups.get(g.group)
                if name is not None and g.weight > 0.0:
                    t = totals.setdefault(piece, {})
                    t[name] = t.get(name, 0.0) + g.weight
                    members[name].append(v.index)
                    if g.weight > best[1]:
                        best = (name, g.weight)
            strongest[v.index] = best[0]
        winner = {}
        for piece, t in totals.items():
            best = max(t, key=t.get)
            verts = np.nonzero(ids == piece)[0]
            others = sum(1 for v in verts if strongest[int(v)] not in (None, best))
            if t[best] < SPLIT * sum(t.values()) or others >= SPLIT_VERTS * len(verts):
                split.append((obj, piece))
                winner[piece] = None
            else:
                winner[piece] = best
        count += len(np.unique(ids))
        kept = np.array([winner.get(int(p), "") is None for p in ids])
        for name in groups.values():
            group = obj.vertex_groups[name]
            keep = np.nonzero(np.array([winner.get(int(p)) == name for p in ids]))[0].tolist()
            drop = sorted(set(members[name]) - set(keep) - set(np.nonzero(kept)[0].tolist()))
            if drop:
                group.remove(drop)
            if keep:
                group.add(keep, 1.0, 'REPLACE')
                holding.add(name)
    binding = pieces.Binding(rig, objects)
    for name in holding:
        bone = arm.bones[name]
        if bone.use_deform and name != root_name(rig):
            joints.apply_kind(rig, name)
            shapes.style(rig, name, binding)
    shapes.style_root(rig)
    return count, split
