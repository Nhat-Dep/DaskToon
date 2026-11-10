# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Machine rig (docs/superpowers/specs/2026-11-10-dasktoon-machine-rig-design.md): Object › Create Machine Rig, the
Add Joint tool, the Machine Rig panels of an armature and of a mesh. The work is done by the dasktoon_machine module."""

import math

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

KIND_ITEMS = (
    ('HINGE', "Hinge", "Turns about one axis (the red ring)", 'DRIVER_ROTATIONAL_DIFFERENCE', 0),
    ('BALL', "Ball Joint", "Turns every way", 'SPHERE', 1),
    ('SLIDE', "Slide", "Moves along one axis without turning", 'EMPTY_SINGLE_ARROW', 2),
    ('FIXED', "Fixed", "Does not move against its parent", 'LOCKED', 3),
)


def _joint_changed(self, _context):
    arm = self.id_data
    pointer = self.as_pointer()
    name = next((b.name for b in arm.bones if b.dasktoon_joint.as_pointer() == pointer), None)
    if name is None:
        return
    from dasktoon_machine import joints
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj.data == arm and name in obj.pose.bones:
            joints.apply_kind(obj, name)


class DaskMachineJoint(PropertyGroup):
    kind: EnumProperty(name="Kind", items=KIND_ITEMS, default='BALL', update=_joint_changed,
                       description="How the joint moves against its parent")
    use_limit: BoolProperty(name="Limit", default=False, update=_joint_changed,
                            description="Keep the joint between a smallest and a largest value")
    angle_min: FloatProperty(name="Smallest", subtype='ANGLE', default=-math.pi / 2, min=-math.pi, max=math.pi,
                             update=_joint_changed, description="The smallest angle of the hinge")
    angle_max: FloatProperty(name="Largest", subtype='ANGLE', default=math.pi / 2, min=-math.pi, max=math.pi,
                             update=_joint_changed, description="The largest angle of the hinge")
    distance_min: FloatProperty(name="Smallest", subtype='DISTANCE', default=-0.1, update=_joint_changed,
                                description="How far the slide moves back")
    distance_max: FloatProperty(name="Largest", subtype='DISTANCE', default=0.1, update=_joint_changed,
                                description="How far the slide moves forward")
    aim: BoolProperty(name="Aims", default=False, options={'HIDDEN'})
    aim_point: FloatVectorProperty(name="Aim Point", size=3, subtype='TRANSLATION', options={'HIDDEN'})


class DaskMachine(PropertyGroup):
    is_machine: BoolProperty(name="Machine", default=False, options={'HIDDEN'})
    root: StringProperty(name="Root", default="Root", options={'HIDDEN'})


classes = (
    DaskMachineJoint,
    DaskMachine,
)


def register():
    bpy.types.Bone.dasktoon_joint = PointerProperty(type=DaskMachineJoint)
    bpy.types.Armature.dasktoon_machine = PointerProperty(type=DaskMachine)


def unregister():
    del bpy.types.Armature.dasktoon_machine
    del bpy.types.Bone.dasktoon_joint
