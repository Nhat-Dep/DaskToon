# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Shading styles for the DaskToon shading ramp: built-in presets and the user's own styles.

Design: docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md, section 3.7.
"""

import json
import os
import re

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import Menu, Operator

SHADING_NODE_TYPES = {'ShaderNodeAnimeCharacter', 'ShaderNodeAnimeCel', 'ShaderNodeDaskCel'}

BUILTIN_STYLES = {
    "Anime 2 tông": {"interpolation": 'CONSTANT', "stops": [
        (0.0, (0.80, 0.62, 0.66, 1.0)), (0.5, (1.0, 1.0, 1.0, 1.0))]},
    "Anime 3 tông": {"interpolation": 'CONSTANT', "stops": [
        (0.0, (0.55, 0.42, 0.52, 1.0)), (0.3, (0.82, 0.66, 0.70, 1.0)), (0.55, (1.0, 1.0, 1.0, 1.0))]},
    "Mềm như vẽ": {"interpolation": 'EASE', "stops": [
        (0.2, (0.72, 0.58, 0.66, 1.0)), (0.7, (1.0, 1.0, 1.0, 1.0))]},
    "Da anime (viền ấm)": {"interpolation": 'CONSTANT', "stops": [
        (0.0, (0.82, 0.62, 0.64, 1.0)), (0.47, (1.0, 0.55, 0.50, 1.0)), (0.53, (1.0, 1.0, 1.0, 1.0))]},
    "Manga": {"interpolation": 'CONSTANT', "stops": [
        (0.0, (0.10, 0.10, 0.10, 1.0)), (0.5, (1.0, 1.0, 1.0, 1.0))]},
}


def user_styles_dir(create=False):
    override = os.environ.get("DASKTOON_STYLES_DIR")
    if override:
        if create:
            os.makedirs(override, exist_ok=True)
        return override
    return bpy.utils.user_resource('CONFIG', path=os.path.join("dasktoon", "shading_styles"), create=create)


def _file_name(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip() + ".json"


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_user_styles():
    folder = user_styles_dir()
    if not folder or not os.path.isdir(folder):
        return []
    names = []
    for entry in sorted(os.listdir(folder)):
        if entry.endswith(".json"):
            try:
                names.append(_read(os.path.join(folder, entry))["name"])
            except (OSError, ValueError, KeyError):
                continue
    return names


def get_style(name):
    if name in BUILTIN_STYLES:
        return BUILTIN_STYLES[name]
    path = os.path.join(user_styles_dir(), _file_name(name))
    if os.path.isfile(path):
        data = _read(path)
        return {"interpolation": data["interpolation"], "stops": [tuple(s) for s in data["stops"]]}
    return None


def apply_style(ramp, style):
    ramp.interpolation = style["interpolation"]
    elements = ramp.elements
    while len(elements) > 1:
        elements.remove(elements[-1])
    first_pos, first_color = style["stops"][0]
    elements[0].position = first_pos
    elements[0].color = first_color
    for pos, color in style["stops"][1:]:
        element = elements.new(pos)
        element.color = color


def style_from_ramp(ramp):
    return {"interpolation": ramp.interpolation,
            "stops": [(e.position, tuple(e.color)) for e in ramp.elements]}


def save_user_style(name, ramp):
    folder = user_styles_dir(create=True)
    path = os.path.join(folder, _file_name(name))
    data = {"version": 1, "name": name}
    data.update(style_from_ramp(ramp))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return path


def delete_user_style(name):
    path = os.path.join(user_styles_dir(), _file_name(name))
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def ramp_from_simple(node):
    """Approximate the Simple sliders with a ramp (spec 3.7). The boundary sits at t = 0.5."""
    def socket_rgb(name, fallback):
        socket = node.inputs[name]
        return fallback if socket.is_linked else tuple(socket.default_value)[:3]

    base = socket_rgb("Base Color", (0.8, 0.8, 0.8))
    shadow = socket_rgb("Shadow Color", (0.5, 0.5, 0.5))
    soft = max(node.inputs["Shadow Softness"].default_value, 0.001)
    if sum(c * c for c in shadow) ** 0.5 > 0.001:
        final = [s + (b * s * 1.25 - s) * 0.75 for s, b in zip(shadow, base)]
    else:
        final = [b * 0.5 for b in base]
    tint = [min(max(f / max(b, 0.01), 0.0), 1.0) for f, b in zip(final, base)]
    node.shading_mode = 'RAMP'
    apply_style(node.shading_ramp, {"interpolation": 'EASE', "stops": [
        (max(0.5 - soft * 0.5, 0.0), (tint[0], tint[1], tint[2], 1.0)),
        (min(0.5 + soft * 0.5, 1.0), (1.0, 1.0, 1.0, 1.0)),
    ]})


def _target_node(context, op):
    node = getattr(context, "node", None) or getattr(context, "active_node", None)
    if op.material and op.node:
        mat = bpy.data.materials.get(op.material)
        node = mat.node_tree.nodes.get(op.node) if mat and mat.node_tree else None
    if node is None or node.bl_idname not in SHADING_NODE_TYPES:
        return None
    return node


class _TargetProps:
    material: StringProperty(options={'SKIP_SAVE', 'HIDDEN'})
    node: StringProperty(options={'SKIP_SAVE', 'HIDDEN'})


class DASKTOON_OT_shading_style_apply(_TargetProps, Operator):
    """Apply a shading style to the node's ramp"""
    bl_idname = "dasktoon.shading_style_apply"
    bl_label = "Apply Shading Style"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty()

    def execute(self, context):
        node = _target_node(context, self)
        style = get_style(self.name)
        if node is None or style is None:
            self.report({'WARNING'}, "Không tìm thấy node hoặc style")
            return {'CANCELLED'}
        node.shading_mode = 'RAMP'
        apply_style(node.shading_ramp, style)
        return {'FINISHED'}


class DASKTOON_OT_shading_style_save(_TargetProps, Operator):
    """Save the current ramp as one of your own styles (shared by every file)"""
    bl_idname = "dasktoon.shading_style_save"
    bl_label = "Lưu style của tôi"

    name: StringProperty(name="Tên style", default="Style của tôi")
    overwrite: BoolProperty(name="Ghi đè nếu đã có", default=False)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        node = _target_node(context, self)
        if node is None or node.shading_ramp is None:
            self.report({'WARNING'}, "Hãy chọn một node DaskToon ở chế độ Dải đổ bóng")
            return {'CANCELLED'}
        name = self.name.strip()
        if not name or name in BUILTIN_STYLES:
            self.report({'ERROR'}, "Tên trống hoặc trùng preset có sẵn")
            return {'CANCELLED'}
        if name in list_user_styles() and not self.overwrite:
            self.report({'ERROR'}, "Style '%s' đã có. Tick 'Ghi đè nếu đã có' để thay" % name)
            return {'CANCELLED'}
        save_user_style(name, node.shading_ramp)
        self.report({'INFO'}, "Đã lưu style '%s'" % name)
        return {'FINISHED'}


class DASKTOON_OT_shading_style_delete(Operator):
    """Delete one of your own shading styles"""
    bl_idname = "dasktoon.shading_style_delete"
    bl_label = "Xóa style"

    name: StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if not delete_user_style(self.name):
            self.report({'WARNING'}, "Không tìm thấy style '%s'" % self.name)
            return {'CANCELLED'}
        return {'FINISHED'}


class DASKTOON_OT_shading_ramp_from_simple(_TargetProps, Operator):
    """Create a ramp that approximates the current Simple sliders"""
    bl_idname = "dasktoon.shading_ramp_from_simple"
    bl_label = "Chuyển từ Đơn giản"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        node = _target_node(context, self)
        if node is None:
            self.report({'WARNING'}, "Hãy chọn một node DaskToon")
            return {'CANCELLED'}
        ramp_from_simple(node)
        self.report({'INFO'}, "Đã tạo dải gần đúng với thanh trượt hiện tại")
        return {'FINISHED'}


class NODE_MT_dasktoon_shading_styles(Menu):
    bl_label = "Shading Style"

    def draw(self, context):
        layout = self.layout
        for name in BUILTIN_STYLES:
            layout.operator(DASKTOON_OT_shading_style_apply.bl_idname, text=name).name = name
        user = list_user_styles()
        if user:
            layout.separator()
            for name in user:
                layout.operator(DASKTOON_OT_shading_style_apply.bl_idname, text=name, icon='USER').name = name
            layout.menu("NODE_MT_dasktoon_shading_styles_delete", icon='TRASH')


class NODE_MT_dasktoon_shading_styles_delete(Menu):
    bl_label = "Xóa style"

    def draw(self, context):
        for name in list_user_styles():
            self.layout.operator(DASKTOON_OT_shading_style_delete.bl_idname, text=name).name = name


classes = (
    DASKTOON_OT_shading_style_apply,
    DASKTOON_OT_shading_style_save,
    DASKTOON_OT_shading_style_delete,
    DASKTOON_OT_shading_ramp_from_simple,
    NODE_MT_dasktoon_shading_styles,
    NODE_MT_dasktoon_shading_styles_delete,
)
