# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon face shading: the face mask, the ellipsoid proxy fitted to the head and the panel
(docs/superpowers/specs/2026-10-04-dasktoon-face-shading-design.md, sections 3 and 5)."""

from contextlib import contextmanager

import bpy
import numpy as np
from bpy.types import Operator, Panel
from mathutils import Matrix, Vector

from . import dasktoon_face_shading_nodes as fsn

PROXY_PREFIX = "DT_FaceProxy::"
PROXY_PROP = "dasktoon_face_proxy"     # on the mesh object: the proxy it uses
PROXY_MARK = "dasktoon_is_face_proxy"  # on the proxy Empty
HEAD_NAMES = ("head", "j_bip_c_head", "mixamorig:head", "頭")
NOT_HEAD = ("end", "top", "tip", "nub")
HEAD_WEIGHT = 0.5
STRIP = 0.25
MIN_FACE_WIDTH = 0.25  # of the head width
FRONT_PERCENTILE = 5.0
MIN_DEPTH = 0.85


class FaceShadingError(Exception):
    """Why face shading cannot be set up, worded for the user."""


def find_armature(obj):
    """The armature deforming obj: its first Armature modifier, else an armature parent (face spec 5.1)."""
    for modifier in obj.modifiers:
        if modifier.type == 'ARMATURE' and modifier.object is not None:
            return modifier.object
    if obj.parent is not None and obj.parent.type == 'ARMATURE':
        return obj.parent
    return None


def find_head_bone(armature):
    """Exact names first (any case), then a name with "head" that is not an end, top, tip or nub bone."""
    names = [bone.name for bone in armature.data.bones]
    for name in names:
        if name.lower() in HEAD_NAMES:
            return name
    for name in names:
        low = name.lower()
        if "head" in low and not any(word in low for word in NOT_HEAD):
            return name
    return None


@contextmanager
def rest_pose(armatures):
    """The armatures in Rest Position meanwhile; their pose position comes back even on error."""
    saved = [(a.data, a.data.pose_position) for a in dict.fromkeys(armatures)
             if a is not None and a.data.library is None]
    try:
        for data, _position in saved:
            data.pose_position = 'REST'
        bpy.context.view_layer.update()
        yield
    finally:
        for data, position in saved:
            data.pose_position = position
        bpy.context.view_layer.update()


def _check_editable(obj):
    if obj is None or obj.type != 'MESH':
        raise FaceShadingError("Hãy chọn mesh nhân vật")
    if obj.library is not None or obj.data.library is not None:
        raise FaceShadingError("Mesh %s được link từ thư viện, không sửa được" % obj.name)


def _group_weights(obj, name):
    weights = np.zeros(len(obj.data.vertices))
    group = obj.vertex_groups.get(name)
    if group is None:
        return weights
    for vertex in obj.data.vertices:
        for element in vertex.groups:
            if element.group == group.index:
                weights[vertex.index] = element.weight
    return weights


def head_vertices(obj, bone, selected=None):
    """Vertices weighted >= 0.5 to the head bone, else the vertices selected in Edit Mode (face spec 5.2)."""
    if bone is not None:
        found = np.flatnonzero(_group_weights(obj, bone) >= HEAD_WEIGHT)
        if len(found):
            return found
    if selected is not None and len(selected):
        return np.array(sorted(selected), dtype=np.int64)
    raise FaceShadingError("Không tìm thấy vùng đầu (không có xương đầu có trọng số). "
                           "Hãy vào Edit Mode, chọn vùng mặt rồi bấm lại")


def _world_coords(obj):
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    matrix = np.array(obj.matrix_world)
    return co.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]


def _island(mesh, seed):
    """Vertices edge-connected to `seed`."""
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", edges)
    a, b = edges[0::2], edges[1::2]
    inside = np.zeros(len(mesh.vertices), dtype=bool)
    inside[seed] = True
    while True:
        grow = inside[a] != inside[b]
        if not grow.any():
            return np.flatnonzero(inside)
        inside[a[grow]] = True
        inside[b[grow]] = True


def _moved_by_shape_keys(obj):
    """Vertices that some shape key moves away from the reference key (the expressions)."""
    count = len(obj.data.vertices)
    moved = np.zeros(count, dtype=bool)
    keys = obj.data.shape_keys
    if keys is None:
        return moved
    reference = np.empty(count * 3, dtype=np.float32)
    keys.reference_key.data.foreach_get("co", reference)
    other = np.empty(count * 3, dtype=np.float32)
    for key in keys.key_blocks:
        if key != keys.reference_key:
            key.data.foreach_get("co", other)
            moved |= np.abs(other - reference).reshape(-1, 3).max(axis=1) > 1e-6
    return moved


def face_island(obj, head):
    """The face skin (face spec 5.3, with two guards found on a real character): the island holding the most head
    vertices moved by expression shape keys, else the island of the most forward head vertex near the middle of the
    head. Islands narrower than a quarter of the head (a lock of hair in front of the face, an eye, the teeth) are
    passed over unless nothing else is found."""
    world = _world_coords(obj)
    x = world[head, 0]
    low, high = x.min(), x.max()
    in_head = np.zeros(len(world), dtype=bool)
    in_head[head] = True
    seen = np.zeros(len(world), dtype=bool)

    def wide(island):
        xs = world[island[in_head[island]], 0]
        return xs.max() - xs.min() >= MIN_FACE_WIDTH * (high - low)

    moved = _moved_by_shape_keys(obj) & in_head
    best, best_count = None, 0
    for seed in np.flatnonzero(moved):
        if not seen[seed]:
            island = _island(obj.data, seed)
            seen[island] = True
            count = int(moved[island].sum())
            if count > best_count and wide(island):
                best, best_count = island, count
    if best is not None:
        return best
    middle = head[np.abs(x - (low + high) / 2.0) <= STRIP * (high - low)]
    seen[:] = False
    first = None
    for seed in middle[np.argsort(world[middle, 1], kind="stable")]:
        if not seen[seed]:
            island = _island(obj.data, seed)
            seen[island] = True
            if wide(island):
                return island
            first = island if first is None else first
    if first is None:
        raise FaceShadingError("Không thấy da mặt ở giữa vùng đầu; hãy chọn cả vùng mặt (gồm mũi) rồi bấm lại")
    return first


def fit(points):
    """Centre and radii of the proxy for the head points of the face skin, world space (face spec 5.4)."""
    low, high = points.min(axis=0), points.max(axis=0)
    rx, rz = (high[0] - low[0]) / 2.0, (high[2] - low[2]) / 2.0
    if min(rx, rz) < 1e-5:
        raise FaceShadingError("Vùng mặt quá nhỏ để đặt khối trứng")
    ry = max((high[1] - low[1]) / 2.0, MIN_DEPTH * rx)
    front = float(np.percentile(points[:, 1], FRONT_PERCENTILE))
    return Vector(((low[0] + high[0]) / 2.0, front + ry, (low[2] + high[2]) / 2.0)), Vector((rx, ry, rz))


def _face_points(obj, head, face):
    points = _world_coords(obj)[np.intersect1d(head, face)]
    if not len(points):
        raise FaceShadingError("Vùng %s không nằm trong vùng đầu; hãy tô lại vertex group đó" % fsn.MASK_NAME)
    return points


def _write_mask(obj, indices):
    """DT_Face = the face island with weight 1; the active vertex group stays the same."""
    active = obj.vertex_groups.active.name if obj.vertex_groups.active is not None else None
    old = obj.vertex_groups.get(fsn.MASK_NAME)
    if old is not None:
        obj.vertex_groups.remove(old)
    obj.vertex_groups.new(name=fsn.MASK_NAME).add(indices.tolist(), 1.0, 'REPLACE')
    if active is not None and active in obj.vertex_groups:
        obj.vertex_groups.active_index = obj.vertex_groups[active].index


def proxy_of(obj):
    """The proxy obj uses: the modifier's Proxy input, else the object's dasktoon_face_proxy property."""
    modifier = fsn.get_modifier(obj)
    if modifier is not None:
        proxy = fsn.input_socket(modifier, "Proxy").value
        if proxy is not None:
            return proxy
    proxy = obj.get(PROXY_PROP)
    return proxy if isinstance(proxy, bpy.types.Object) else None


def proxy_users(proxy):
    return [o for o in bpy.data.objects if o.type == 'MESH' and proxy_of(o) == proxy]


def find_proxy(armature, bone, obj):
    """The proxy already made for this head bone, or for obj when there is no head bone (one per head bone)."""
    for other in bpy.data.objects:
        if other.type != 'EMPTY' or not other.get(PROXY_MARK) or other.library is not None:
            continue
        if bone is not None and (other.parent, other.parent_type, other.parent_bone) == (armature, 'BONE', bone):
            return other
        if bone is None and (other.parent, other.parent_type) == (obj, 'OBJECT'):
            return other
    return None


def _new_proxy(obj, armature, bone):
    name = PROXY_PREFIX + ("%s:%s" % (armature.name, bone) if bone is not None else obj.name)
    proxy = bpy.data.objects.new(name, None)
    proxy.empty_display_type = 'SPHERE'
    proxy.empty_display_size = 1.0
    proxy.hide_render = True
    proxy[PROXY_MARK] = True
    collection = obj.users_collection[0] if obj.users_collection else bpy.context.scene.collection
    collection.objects.link(proxy)
    return proxy


def place_proxy(proxy, armature, bone, obj, centre, radii):
    """Hang the proxy from the head bone (or from obj) so that at rest it sits at `centre` with scale `radii`."""
    if bone is not None:
        rest = armature.data.bones[bone]
        parent = armature.matrix_world @ rest.matrix_local @ Matrix.Translation((0.0, rest.length, 0.0))
        proxy.parent = armature
        proxy.parent_type = 'BONE'
        proxy.parent_bone = bone
    else:
        parent = obj.matrix_world.copy()
        proxy.parent = obj
        proxy.parent_type = 'OBJECT'
    proxy.matrix_parent_inverse = parent.inverted()
    proxy.matrix_basis = Matrix.LocRotScale(centre, None, radii)


def _rig(obj):
    armature = find_armature(obj)
    return armature, (find_head_bone(armature) if armature is not None else None)


def _connect(obj, proxy):
    modifier = fsn.ensure_modifier(obj)
    fsn.set_inputs(modifier, {"Proxy": proxy})
    obj[PROXY_PROP] = proxy


def setup(obj, selected=None):
    """Face spec 3.1: DT_Face, the proxy (the head bone's existing one is reused as it is) and the modifier."""
    _check_editable(obj)
    armature, bone = _rig(obj)
    with rest_pose([armature]):
        head = head_vertices(obj, bone, selected)
        face = face_island(obj, head)
        proxy = find_proxy(armature, bone, obj)
        if proxy is None:
            centre, radii = fit(_face_points(obj, head, face))
            proxy = _new_proxy(obj, armature, bone)
            place_proxy(proxy, armature, bone, obj, centre, radii)
        _write_mask(obj, face)
    _connect(obj, proxy)
    return proxy


def refit(obj, selected=None):
    """Face spec 3.4: place and size the proxy again from the face (DT_Face as painted); the sliders stay."""
    _check_editable(obj)
    if fsn.get_modifier(obj) is None:
        raise FaceShadingError("%s chưa có bóng mặt; bấm Tạo bóng mặt anime trước" % obj.name)
    armature, bone = _rig(obj)
    with rest_pose([armature]):
        face = np.flatnonzero(_group_weights(obj, fsn.MASK_NAME) >= HEAD_WEIGHT)
        try:
            head = head_vertices(obj, bone, selected)
        except FaceShadingError:
            if not len(face):
                raise
            head = face
        if not len(face):
            face = face_island(obj, head)
            _write_mask(obj, face)
        centre, radii = fit(_face_points(obj, head, face))
        proxy = proxy_of(obj) or find_proxy(armature, bone, obj) or _new_proxy(obj, armature, bone)
        place_proxy(proxy, armature, bone, obj, centre, radii)
    _connect(obj, proxy)
    return proxy


def remove(obj):
    """Face spec 3.5: the modifier, DT_Face, the property, and the proxy when no other mesh uses it."""
    _check_editable(obj)
    proxy = proxy_of(obj)
    fsn.remove_modifier(obj)
    group = obj.vertex_groups.get(fsn.MASK_NAME)
    if group is not None:
        obj.vertex_groups.remove(group)
    if PROXY_PROP in obj:
        del obj[PROXY_PROP]
    if proxy is not None and proxy.library is None and not proxy_users(proxy):
        bpy.data.objects.remove(proxy)


def panel_target(context):
    """The mesh the panel works on: the active mesh, or the first mesh using the active proxy."""
    obj = context.active_object
    if obj is None:
        return None
    if obj.type == 'MESH':
        return obj
    if obj.type == 'EMPTY' and obj.get(PROXY_MARK):
        users = proxy_users(obj)
        return users[0] if users else None
    return None


SLIDERS = (("Coverage", "Độ phủ"), ("Falloff", "Vùng chuyển"), ("Nose Keep", "Giữ bóng mũi"),
           ("Chin Keep", "Giữ bóng cằm"))


def _run(operator, context, action, done):
    """Run action(mesh, selected) on the panel's mesh. In Edit Mode the selection is read and Edit Mode is left
    meanwhile (vertex groups cannot be written in Edit Mode)."""
    obj = panel_target(context)
    if obj is None:
        operator.report({'ERROR'}, "Hãy chọn mesh nhân vật")
        return {'CANCELLED'}
    editing = obj.mode == 'EDIT'
    selected = None
    if editing:
        obj.update_from_editmode()
        flags = np.zeros(len(obj.data.vertices), dtype=bool)
        obj.data.vertices.foreach_get("select", flags)
        selected = np.flatnonzero(flags)
        bpy.ops.object.mode_set(mode='OBJECT')
    try:
        action(obj, selected)
    except FaceShadingError as ex:
        operator.report({'ERROR'}, str(ex))
        return {'CANCELLED'}
    finally:
        if editing:
            bpy.ops.object.mode_set(mode='EDIT')
    operator.report({'INFO'}, done % obj.name)
    return {'FINISHED'}


class DASKTOON_OT_face_shading_setup(Operator):
    """Shade the face like an egg: find the head, fit an egg-shaped proxy to it and add the Face Shading modifier"""
    bl_idname = "dasktoon.face_shading_setup"
    bl_label = "Tạo bóng mặt anime"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return _run(self, context, setup, "Đã tạo bóng mặt cho %s: kéo khối trứng hoặc chỉnh thanh trượt")


class DASKTOON_OT_face_shading_refit(Operator):
    """Fit the egg-shaped proxy to the face again (position and size); the sliders stay"""
    bl_idname = "dasktoon.face_shading_refit"
    bl_label = "Căn lại khối trứng"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return _run(self, context, refit, "Đã căn lại khối trứng của %s")


class DASKTOON_OT_face_shading_remove(Operator):
    """Remove the face shading of the mesh: the modifier, DT_Face and the proxy when no other mesh uses it"""
    bl_idname = "dasktoon.face_shading_remove"
    bl_label = "Gỡ bóng mặt"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return _run(self, context, lambda obj, _selected: remove(obj), "Đã gỡ bóng mặt của %s")


class DASKTOON_OT_face_shading_select_proxy(Operator):
    """Select the egg-shaped proxy to move, rotate or scale it; the face shading follows right away"""
    bl_idname = "dasktoon.face_shading_select_proxy"
    bl_label = "Chọn khối trứng"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = panel_target(context)
        proxy = proxy_of(obj) if obj is not None else None
        if proxy is None:
            self.report({'ERROR'}, "Mesh chưa có khối trứng: bấm Tạo bóng mặt anime hoặc Căn lại khối trứng")
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        try:
            proxy.hide_set(False)
            proxy.hide_viewport = False
            for other in context.selected_objects:
                other.select_set(False)
            proxy.select_set(True)
        except RuntimeError:
            self.report({'ERROR'}, "Khối trứng %s không nằm trong view layer đang mở" % proxy.name)
            return {'CANCELLED'}
        context.view_layer.objects.active = proxy
        return {'FINISHED'}


class DASKTOON_PT_face_shading(Panel):
    bl_label = "Bóng mặt"
    bl_idname = "DASKTOON_PT_face_shading"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"
    bl_order = 15

    def draw(self, context):
        layout = self.layout
        obj = panel_target(context)
        if obj is None:
            layout.label(text="Chọn mesh nhân vật hoặc khối trứng", icon='INFO')
            return
        if obj.library is not None or obj.data.library is not None:
            layout.label(text="Mesh link từ thư viện, không sửa được", icon='ERROR')
            return
        modifier = fsn.get_modifier(obj)
        if modifier is None:
            col = layout.column()
            col.scale_y = 1.4
            col.operator(DASKTOON_OT_face_shading_setup.bl_idname, icon='SHADING_RENDERED')
        else:
            if context.active_object != obj:
                layout.label(text="Khối trứng của " + obj.name, icon='MESH_UVSPHERE')
            if proxy_of(obj) is None:
                layout.label(text="Chưa có khối trứng: bấm Căn lại khối trứng", icon='ERROR')
            layout.operator(DASKTOON_OT_face_shading_select_proxy.bl_idname, icon='RESTRICT_SELECT_OFF')
            col = layout.column(align=True)
            for name, label in SLIDERS:
                col.prop(fsn.input_socket(modifier, name), "value", text=label, slider=True)
            row = layout.row(align=True)
            row.operator(DASKTOON_OT_face_shading_refit.bl_idname, icon='FILE_REFRESH')
            row.operator(DASKTOON_OT_face_shading_remove.bl_idname, icon='X')
        if obj.data.has_custom_normals and context.active_object == obj:
            box = layout.box()
            box.label(text="Mesh còn custom normal cũ: bóng mũi, cằm", icon='INFO')
            box.label(text="sẽ theo normal đó, không theo hình khối thật")
            box.operator("mesh.customdata_custom_splitnormals_clear", icon='LOOP_BACK')


classes = (
    DASKTOON_OT_face_shading_setup,
    DASKTOON_OT_face_shading_refit,
    DASKTOON_OT_face_shading_remove,
    DASKTOON_OT_face_shading_select_proxy,
    DASKTOON_PT_face_shading,
)
