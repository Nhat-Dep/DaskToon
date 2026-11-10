# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Machine rig (docs/superpowers/specs/2026-11-10-dasktoon-machine-rig-design.md): Object › Create Machine Rig, the
Add Joint tool, the Machine Rig panels of an armature and of a mesh. The work is done by the dasktoon_machine module."""

import math

import bpy
import numpy as np
from bpy.app.translations import pgettext_iface as iface_, pgettext_rpt as rpt_
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, Panel, PropertyGroup

KIND_ITEMS = (
    ('HINGE', "Hinge", "Turns about one axis (the red ring)", 'DRIVER_ROTATIONAL_DIFFERENCE', 0),
    ('BALL', "Ball Joint", "Turns every way", 'SPHERE', 1),
    ('SLIDE', "Slide", "Moves along one axis without turning", 'EMPTY_SINGLE_ARROW', 2),
    ('FIXED', "Fixed", "Does not move against its parent", 'LOCKED', 3),
)
KIND_NAMES = {item[0]: item[1] for item in KIND_ITEMS}


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
    unbound: IntProperty(name="Pieces Without a Joint", default=-1, options={'HIDDEN'})


# Helpers


def machine_of(context):
    """The machine armature of the context: the active armature, or the machine of the active mesh."""
    import dasktoon_machine as machine
    obj = getattr(context, "object", None)
    if machine.is_machine(obj):
        return obj
    return machine.rig_of_mesh(obj)


def count_unbound(rig):
    from dasktoon_machine import pieces
    rig.data.dasktoon_machine.unbound = len(pieces.Binding(rig).unbound())


def active_joint(rig):
    import dasktoon_machine as machine
    bone = rig.data.bones.active
    if bone is None or bone.name == machine.root_name(rig) or not bone.use_deform:
        return None
    return bone


def _report_error(op, error):
    op.report({'WARNING'}, str(error))
    return {'CANCELLED'}


# Operators


class DASKTOON_OT_machine_create(Operator):
    """Make the selected meshes a machine: a rig with one Root joint holding every piece, ready for Add Joint"""
    bl_idname = "dasktoon.machine_create"
    bl_label = "Create Machine Rig"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(o.type == 'MESH' for o in context.selected_objects) and context.mode == 'OBJECT'

    def execute(self, context):
        import dasktoon_machine as machine
        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        active = context.view_layer.objects.active
        name = active.name if active in meshes else meshes[0].name
        try:
            rig = machine.create(context, meshes, name)
        except machine.MachineError as error:
            return _report_error(self, error)
        count_unbound(rig)
        for obj in context.view_layer.objects:
            obj.select_set(obj == rig)
        context.view_layer.objects.active = rig
        self.report({'INFO'}, rpt_("Machine rig made: %d pieces wait for a joint") % rig.data.dasktoon_machine.unbound)
        return {'FINISHED'}


class DASKTOON_OT_machine_piece_from_selection(Operator):
    """The selected faces become a piece of their own, to be given a joint apart from the rest of their part"""
    bl_idname = "dasktoon.machine_piece_from_selection"
    bl_label = "Make a Piece from Selection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        import dasktoon_machine as machine
        from dasktoon_machine import pieces
        obj = context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        try:
            number = pieces.from_selection(obj)
        except machine.MachineError as error:
            bpy.ops.object.mode_set(mode='EDIT')
            return _report_error(self, error)
        rig = machine.rig_of_mesh(obj)
        if rig is not None:
            count_unbound(rig)  # in Object Mode: an Edit Mode mesh has no vertices to read
        bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, rpt_("New piece %d") % number)
        return {'FINISHED'}


class DASKTOON_OT_machine_adopt(Operator):
    """Each piece of the meshes on this armature goes wholly to the bone holding most of it, so nothing bends"""
    bl_idname = "dasktoon.machine_adopt"
    bl_label = "Make Pieces Rigid"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'ARMATURE' and context.mode in ('OBJECT', 'POSE')

    def execute(self, context):
        import dasktoon_machine as machine
        from dasktoon_machine import pieces
        rig = context.object
        try:
            count, split = machine.adopt(context, rig)
        except machine.MachineError as error:
            return _report_error(self, error)
        count_unbound(rig)
        for obj in {o for o, _n in split}:
            ids = pieces.read(obj)
            inside = np.isin(ids, [n for o, n in split if o == obj])
            for poly in obj.data.polygons:
                poly.select = bool(inside[list(poly.vertices)].all())
            obj.data.vertices.foreach_set("select", inside)
        if split:
            self.report({'WARNING'}, rpt_("%d pieces are split between joints: they are selected in their meshes, "
                                          "split them with Make a Piece from Selection") % len(split))
        else:
            self.report({'INFO'}, rpt_("%d pieces made rigid") % count)
        return {'FINISHED'}


class DASKTOON_OT_machine_remove_joint(Operator):
    """Take the selected joint away: its pieces wait for a joint again, the joints below it hang from its parent"""
    bl_idname = "dasktoon.machine_remove_joint"
    bl_label = "Remove Joint"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        rig = machine_of(context)
        return rig is not None and active_joint(rig) is not None

    def execute(self, context):
        import dasktoon_machine as machine
        from dasktoon_machine import joints, pieces
        rig = machine_of(context)
        name = active_joint(rig).name
        try:
            joints.remove(context, pieces.Binding(rig), name)
        except machine.MachineError as error:
            return _report_error(self, error)
        count_unbound(rig)
        return {'FINISHED'}


class DASKTOON_OT_machine_leg_add(Operator):
    """The selected joint becomes a foot: an IK target moves it and bends the joints above it"""
    bl_idname = "dasktoon.machine_leg_add"
    bl_label = "Add IK Leg"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        rig = machine_of(context)
        return rig is not None and active_joint(rig) is not None

    def execute(self, context):
        import dasktoon_machine as machine
        from dasktoon_machine import legs
        rig = machine_of(context)
        try:
            target = legs.add(context, rig, active_joint(rig).name)
        except machine.MachineError as error:
            return _report_error(self, error)
        self.report({'INFO'}, rpt_("IK target added: %s") % target)
        return {'FINISHED'}


class DASKTOON_OT_machine_leg_remove(Operator):
    """Take this IK leg away; its joints stay"""
    bl_idname = "dasktoon.machine_leg_remove"
    bl_label = "Remove IK Leg"
    bl_options = {'REGISTER', 'UNDO'}

    target: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        from dasktoon_machine import legs
        rig = machine_of(context)
        if rig is None or self.target not in rig.pose.bones:
            return {'CANCELLED'}
        legs.remove(context, rig, self.target)
        return {'FINISHED'}


class DASKTOON_OT_machine_leg_snap(Operator):
    """Switch the leg over without moving it"""
    bl_idname = "dasktoon.machine_leg_snap"
    bl_label = "Snap Leg"
    bl_options = {'REGISTER', 'UNDO'}

    target: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    to: EnumProperty(items=(('IK', "IK", ""), ('FK', "FK", "")), options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        from dasktoon_machine import legs
        rig = machine_of(context)
        if rig is None or self.target not in rig.pose.bones:
            return {'CANCELLED'}
        legs.snap(context, rig, self.target, self.to)
        return {'FINISHED'}


class DASKTOON_OT_machine_aim_add(Operator):
    """The selected joint (a barrel, an eye) and the joints above it turn towards a target you can move"""
    bl_idname = "dasktoon.machine_aim_add"
    bl_label = "Add Aim Target"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        rig = machine_of(context)
        return rig is not None and active_joint(rig) is not None

    def execute(self, context):
        import dasktoon_machine as machine
        from dasktoon_machine import aim
        rig = machine_of(context)
        try:
            target = aim.add(context, rig, active_joint(rig).name)
        except machine.MachineError as error:
            return _report_error(self, error)
        self.report({'INFO'}, rpt_("Aim target added: %s") % target)
        return {'FINISHED'}


class DASKTOON_OT_machine_aim_remove(Operator):
    """Take this aim target away; the joints turn back to their own pose"""
    bl_idname = "dasktoon.machine_aim_remove"
    bl_label = "Remove Aim Target"
    bl_options = {'REGISTER', 'UNDO'}

    target: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        from dasktoon_machine import aim
        rig = machine_of(context)
        if rig is None or self.target not in rig.pose.bones:
            return {'CANCELLED'}
        aim.remove(context, rig, self.target)
        return {'FINISHED'}


# The Add Joint tool


_draw = {"handle": None, "tool": None}


def _view3d(context):
    """(area, region, region_3d) of the 3D view under the tool: the context's, or the largest of the window."""
    area = context.area if context.area is not None and context.area.type == 'VIEW_3D' else None
    if area is None:
        areas = [a for a in context.window.screen.areas if a.type == 'VIEW_3D']
        if not areas:
            return None
        area = max(areas, key=lambda a: a.width * a.height)
    region = next((r for r in area.regions if r.type == 'WINDOW'), None)
    if region is None:
        return None
    return area, region, area.spaces.active.region_3d


class _Overlay:
    """Triangles of each piece (world rest positions) for the tool's colours."""

    def __init__(self, binding):
        self.binding = binding
        self.tris = {}
        for obj in binding.objects:
            mesh = obj.data
            mesh.calc_loop_triangles()
            tri = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int64)
            mesh.loop_triangles.foreach_get("vertices", tri)
            tri = tri.reshape(-1, 3)
            self.tris[obj] = (tri, binding.ids[obj][tri[:, 0]])
        self.cache = {}

    def batch(self, pieces):
        import gpu
        from gpu_extras.batch import batch_for_shader
        key = tuple(sorted((o.name, n) for o, n in pieces))
        if key in self.cache:
            return self.cache[key]
        coords, indices = [], []
        for obj, (tri, owner) in self.tris.items():
            numbers = [n for o, n in pieces if o == obj]
            if not numbers:
                continue
            chosen = tri[np.isin(owner, numbers)]
            if not len(chosen):
                continue
            used, inverse = np.unique(chosen, return_inverse=True)
            offset = len(coords)
            coords += self.binding.world[obj][used].tolist()
            indices += (inverse.reshape(-1, 3) + offset).tolist()
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'TRIS', {"pos": coords}, indices=indices) if indices else None
        if len(self.cache) > 32:
            self.cache.clear()
        self.cache[key] = batch
        return batch


def _draw_tool():
    op = _draw["tool"]
    if op is None:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader
    state, overlay = op.state, op.overlay
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.depth_mask_set(False)
    parent = state.binding.pieces_of(state.parent) if state.parent not in (None, state.root) else []
    for pieces_, colour in ((op.unbound, (1.0, 0.25, 0.2, 0.35)), (parent, (0.2, 0.5, 1.0, 0.4)),
                            (state.child, (1.0, 0.6, 0.1, 0.55)),
                            ([op.hover] if op.hover is not None else [], (1.0, 1.0, 1.0, 0.25))):
        batch = overlay.batch(pieces_) if pieces_ else None
        if batch is not None:
            shader.uniform_float("color", colour)
            batch.draw(shader)
    gpu.state.depth_test_set('NONE')
    joint = state.joint
    if joint is not None:
        size = op.size * 0.6
        a, b = joint.pivot - joint.axis * size, joint.pivot + joint.axis * size
        gpu.state.line_width_set(3.0)
        line = batch_for_shader(shader, 'LINES', {"pos": [tuple(a), tuple(b)]})
        shader.uniform_float("color", (1.0, 0.9, 0.1, 1.0))
        line.draw(shader)
        gpu.state.point_size_set(12.0)
        point = batch_for_shader(shader, 'POINTS', {"pos": [tuple(joint.pivot)]})
        point.draw(shader)
        gpu.state.line_width_set(1.0)
        gpu.state.point_size_set(1.0)
    gpu.state.depth_mask_set(True)
    gpu.state.blend_set('NONE')


AXES = {'X': (1.0, 0.0, 0.0), 'Y': (0.0, 1.0, 0.0), 'Z': (0.0, 0.0, 1.0)}
NAVIGATION = {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADPAN', 'TRACKPADZOOM', 'MOUSEROTATE',
              'NDOF_MOTION', 'NUMPAD_1', 'NUMPAD_2', 'NUMPAD_3', 'NUMPAD_4', 'NUMPAD_5', 'NUMPAD_6', 'NUMPAD_7',
              'NUMPAD_8', 'NUMPAD_9', 'NUMPAD_PERIOD', 'NUMPAD_PLUS', 'NUMPAD_MINUS', 'HOME', 'F'}


class DASKTOON_OT_machine_joint_tool(Operator):
    """Click a piece, then the piece it hangs from; move the guessed pivot, change the axis or kind; Enter makes it"""
    bl_idname = "dasktoon.machine_joint_tool"
    bl_label = "Add Joint"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return machine_of(context) is not None and context.mode in ('OBJECT', 'POSE')

    def invoke(self, context, event):
        from dasktoon_machine import tool
        view = _view3d(context)
        if view is None:
            self.report({'WARNING'}, rpt_("Open a 3D Viewport to use the tool"))
            return {'CANCELLED'}
        self.area, self.region, self.rv3d = view
        self.rig = machine_of(context)
        self.pose_position = self.rig.data.pose_position
        self.rig.data.pose_position = 'REST'
        context.view_layer.update()
        self.state = tool.ToolState(context, self.rig)
        self.overlay = _Overlay(self.state.binding)
        points = np.concatenate([w for w in self.state.binding.world.values()] or [np.zeros((1, 3))])
        self.size = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0))) * 0.15 or 0.1
        self.unbound = self.state.unbound()
        self.hover, self.dragging = None, False
        _draw["tool"] = self
        if _draw["handle"] is None:
            _draw["handle"] = bpy.types.SpaceView3D.draw_handler_add(_draw_tool, (), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        self._status(context)
        return {'RUNNING_MODAL'}

    def _status(self, context):
        text = iface_(self.state.status())
        if self.state.message:
            text = self.state.message + "  |  " + text
        if self.state.joint is not None:
            text = "%s: %s  |  %s" % (iface_("Kind"), iface_(KIND_NAMES[self.state.joint.kind]), text)
        self.area.header_text_set(text)
        self.area.tag_redraw()

    def _mouse(self, event):
        """The mouse in the tool's region, or None when it is outside."""
        x, y = event.mouse_x - self.region.x, event.mouse_y - self.region.y
        if 0 <= x < self.region.width and 0 <= y < self.region.height:
            return x, y
        return None

    def _ray(self, coord):
        from bpy_extras import view3d_utils
        origin = view3d_utils.region_2d_to_origin_3d(self.region, self.rv3d, coord)
        direction = view3d_utils.region_2d_to_vector_3d(self.region, self.rv3d, coord)
        return self.state.binding.hit(origin, direction)[0]

    def _near_pivot(self, coord):
        from bpy_extras import view3d_utils
        if self.state.joint is None:
            return False
        p = view3d_utils.location_3d_to_region_2d(self.region, self.rv3d, tuple(self.state.joint.pivot))
        return p is not None and (p.x - coord[0]) ** 2 + (p.y - coord[1]) ** 2 < 14 ** 2

    def _drag_to(self, coord):
        from bpy_extras import view3d_utils
        point = view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, coord, tuple(self.state.joint.pivot))
        self.state.move_pivot(np.array(point))

    def _refresh(self, context):
        self.unbound = self.state.unbound()
        self.rig.data.dasktoon_machine.unbound = len(self.unbound)
        self._status(context)

    def _finish(self, context):
        self.rig.data.pose_position = self.pose_position
        self.area.header_text_set(None)
        _draw["tool"] = None
        if _draw["handle"] is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_draw["handle"], 'WINDOW')
            _draw["handle"] = None
        self.area.tag_redraw()
        return {'FINISHED'}

    def modal(self, context, event):
        import dasktoon_machine as machine
        state = self.state
        coord = self._mouse(event)
        try:
            if event.type in NAVIGATION:
                return {'PASS_THROUGH'}
            if event.type == 'MOUSEMOVE':
                if coord is not None:
                    if self.dragging and state.joint is not None:
                        self._drag_to(coord)
                    else:
                        self.hover = self._ray(coord)
                    self.area.tag_redraw()
                return {'RUNNING_MODAL'}
            if event.type in ('ESC', 'RIGHTMOUSE') and event.value == 'PRESS':
                if self.dragging:
                    self.dragging = False
                    return {'RUNNING_MODAL'}
                return self._finish(context)
            if event.type == 'LEFTMOUSE':
                if coord is None:
                    return {'PASS_THROUGH'}
                if event.value == 'RELEASE':
                    self.dragging = False
                    return {'RUNNING_MODAL'}
                if event.value != 'PRESS':
                    return {'RUNNING_MODAL'}
                if self.dragging:
                    self.dragging = False
                elif state.state == 'ADJUST' and self._near_pivot(coord):
                    self.dragging = True
                else:
                    state.click(self._ray(coord), shift=event.shift)
                    self.overlay.binding = state.binding
                    self._refresh(context)
                return {'RUNNING_MODAL'}
            if event.value != 'PRESS':
                return {'RUNNING_MODAL'} if coord is not None else {'PASS_THROUGH'}
            if event.type == 'G':
                self.dragging = state.joint is not None and not self.dragging
            elif event.type in AXES and not event.ctrl and not event.alt:
                state.set_axis(AXES[event.type])
            elif event.type == 'A':
                state.set_axis(None)
            elif event.type == 'T':
                state.cycle_kind()
            elif event.type == 'P':
                state.pick_parent()
            elif event.type in ('RET', 'NUMPAD_ENTER', 'SPACE'):
                state.confirm()
            elif event.type == 'BACK_SPACE':
                state.undo_last()
            else:
                return {'PASS_THROUGH'} if coord is None else {'RUNNING_MODAL'}
            self._refresh(context)
        except machine.MachineError as error:
            state.message = str(error)
            self._status(context)
        return {'RUNNING_MODAL'}


# Panels


class DaskMachinePanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        import dasktoon_machine as machine
        return machine.is_machine(getattr(context, "object", None))


class DATA_PT_dasktoon_machine(DaskMachinePanel, Panel):
    bl_label = "Machine Rig"

    def draw(self, context):
        layout = self.layout
        rig = context.object
        layout.operator("dasktoon.machine_joint_tool", icon='BONE_DATA')
        unbound = rig.data.dasktoon_machine.unbound
        if unbound > 0:
            layout.label(text=rpt_("%d pieces have no joint yet (red in the tool)") % unbound, icon='INFO',
                         translate=False)
        elif unbound == 0:
            layout.label(text="Every piece has a joint", icon='CHECKMARK')
        layout.label(text="In the tool: click a piece, then its parent, then Enter", icon='MOUSE_LMB')
        layout.operator("dasktoon.machine_adopt", icon='MESH_CUBE')


class DATA_PT_dasktoon_machine_joint(DaskMachinePanel, Panel):
    bl_label = "Selected Joint"
    bl_parent_id = "DATA_PT_dasktoon_machine"

    def draw(self, context):
        layout = self.layout
        rig = context.object
        bone = active_joint(rig)
        if bone is None:
            layout.label(text="Select a joint (a bone) to set it up", icon='INFO')
            return
        layout.label(text=bone.name, icon='BONE_DATA', translate=False)
        data = bone.dasktoon_joint
        layout.prop(data, "kind", expand=True)
        if data.kind in ('HINGE', 'SLIDE'):
            layout.prop(data, "use_limit")
            col = layout.column(align=True)
            col.active = data.use_limit
            if data.kind == 'HINGE':
                col.prop(data, "angle_min")
                col.prop(data, "angle_max")
            else:
                col.prop(data, "distance_min")
                col.prop(data, "distance_max")
        row = layout.row(align=True)
        row.operator("dasktoon.machine_leg_add", icon='CON_KINEMATIC')
        row.operator("dasktoon.machine_aim_add", icon='CON_TRACKTO')
        layout.operator("dasktoon.machine_remove_joint", icon='X')


class DATA_PT_dasktoon_machine_legs(DaskMachinePanel, Panel):
    bl_label = "IK Legs"
    bl_parent_id = "DATA_PT_dasktoon_machine"

    def draw(self, context):
        from dasktoon_machine import legs
        layout = self.layout
        rig = context.object
        found = legs.legs(rig)
        if not found:
            layout.label(text="Select the foot joint and press Add IK Leg", icon='INFO')
            return
        column = layout.column(align=True)
        for foot, target in found:
            row = column.row(align=True)
            row.label(text=foot, translate=False)
            row.prop(rig.pose.bones[target], '["%s"]' % legs.SWITCH, text="IK / FK", slider=True)
            op = row.operator("dasktoon.machine_leg_snap", text="To IK")
            op.target, op.to = target, 'IK'
            op = row.operator("dasktoon.machine_leg_snap", text="To FK")
            op.target, op.to = target, 'FK'
            row.operator("dasktoon.machine_leg_remove", text="", icon='X').target = target


class DATA_PT_dasktoon_machine_aim(DaskMachinePanel, Panel):
    bl_label = "Aiming"
    bl_parent_id = "DATA_PT_dasktoon_machine"

    def draw(self, context):
        from dasktoon_machine import aim
        layout = self.layout
        rig = context.object
        found = aim.aims(rig)
        if not found:
            layout.label(text="Select a barrel or an eye joint and press Add Aim Target", icon='INFO')
            return
        column = layout.column(align=True)
        for joint, target in found:
            row = column.row(align=True)
            row.label(text=joint, translate=False)
            row.prop(rig.pose.bones[target], '["%s"]' % aim.SWITCH, text="Aim", slider=True)
            row.operator("dasktoon.machine_aim_remove", text="", icon='X').target = target


class DATA_PT_dasktoon_machine_mesh(Panel):
    bl_label = "Machine Rig"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = getattr(context, "object", None)
        return obj is not None and obj.type == 'MESH'

    def draw(self, context):
        import dasktoon_machine as machine
        layout = self.layout
        obj = context.object
        rig = machine.rig_of_mesh(obj)
        if rig is None:
            layout.label(text="Rigid pieces on joints, for robots, weapons and machines")
            layout.operator("dasktoon.machine_create", icon='OUTLINER_OB_ARMATURE')
            return
        layout.label(text=rig.name, icon='ARMATURE_DATA', translate=False)
        layout.operator("dasktoon.machine_piece_from_selection", icon='SELECT_SUBTRACT')
        if obj.mode != 'EDIT':
            layout.label(text="Select the faces of a piece in Edit Mode", icon='INFO')


def menu_func_object(self, _context):
    self.layout.operator(DASKTOON_OT_machine_create.bl_idname, icon='OUTLINER_OB_ARMATURE')


classes = (
    DaskMachineJoint,
    DaskMachine,
    DASKTOON_OT_machine_create,
    DASKTOON_OT_machine_piece_from_selection,
    DASKTOON_OT_machine_adopt,
    DASKTOON_OT_machine_remove_joint,
    DASKTOON_OT_machine_leg_add,
    DASKTOON_OT_machine_leg_remove,
    DASKTOON_OT_machine_leg_snap,
    DASKTOON_OT_machine_aim_add,
    DASKTOON_OT_machine_aim_remove,
    DASKTOON_OT_machine_joint_tool,
    DATA_PT_dasktoon_machine,
    DATA_PT_dasktoon_machine_joint,
    DATA_PT_dasktoon_machine_legs,
    DATA_PT_dasktoon_machine_aim,
    DATA_PT_dasktoon_machine_mesh,
)


# bl_ui registers `classes`; register() adds the data and the Object menu entry (reached through its Python class, as
# bl_ui registers this module before space_view3d).
def register():
    from .space_view3d import VIEW3D_MT_object
    bpy.types.Bone.dasktoon_joint = PointerProperty(type=DaskMachineJoint)
    bpy.types.Armature.dasktoon_machine = PointerProperty(type=DaskMachine)
    VIEW3D_MT_object.append(menu_func_object)


def unregister():
    from .space_view3d import VIEW3D_MT_object
    VIEW3D_MT_object.remove(menu_func_object)
    if _draw["handle"] is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw["handle"], 'WINDOW')
        _draw["handle"] = None
    del bpy.types.Armature.dasktoon_machine
    del bpy.types.Bone.dasktoon_joint
