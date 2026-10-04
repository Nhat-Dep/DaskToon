# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export report: Text datablock, popup, README.txt and the light hints (spec 3, 5)."""

import math
from dataclasses import dataclass, field

import bpy

from . import unity_yaml

REPORT_TEXT = "DaskToon Engine Export Report"
POPUP_LINES = 14
SHADER_STATE = {
    'INSTALLED': "Shader: đã cài hoặc cập nhật",
    'UP_TO_DATE': "Shader: project đã có bản đủ mới, không ghi lại",
    'SKIPPED': "Shader: không xuất (đã tắt xuất material)",
}


@dataclass
class Report:
    mode: str
    root: str
    name: str
    shaders: str = 'SKIPPED'
    model: str = ""
    materials: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    baked: list = field(default_factory=list)
    outline_meshes: list = field(default_factory=list)
    face_meshes: list = field(default_factory=list)
    modifier_notes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    light_hint: str = ""
    ambient_hint: str = ""

    def summary(self):
        return "Engine Export: %d material, %s, %d cảnh báo" % (
            len(self.materials), "có FBX" if self.model else "không có model", len(self.warnings))

    def lines(self):
        where = "ghi thẳng vào project Unity" if self.mode == 'PROJECT' else "thư mục để kéo vào Unity"
        out = ["Đích: %s (%s)" % (self.root, where), SHADER_STATE[self.shaders]]
        if self.model:
            out.append("Model: " + self.model)
        out.append("Material đã xuất (%d): %s" % (len(self.materials), ", ".join(self.materials) or "không có"))
        out += ["Bỏ qua material %s: %s (Unity giữ material mặc định của FBX)" % item for item in self.skipped]
        if self.baked:
            out.append("Đã bake: " + ", ".join(self.baked))
        if self.outline_meshes:
            out.append("Đã ghi DT_OutlineN/W cho: " + ", ".join(self.outline_meshes))
        if self.face_meshes:
            out.append("Bóng mặt: đã ghi normal khối trứng (tư thế nghỉ) cho: %s; blend shape trong FBX không đổi normal"
                       % ", ".join(self.face_meshes))
        out += self.modifier_notes
        out += ["Cảnh báo: " + w for w in self.warnings]
        out += [hint for hint in (self.light_hint, self.ambient_hint) if hint]
        out.append("Project Unity phải dùng Linear color space (mặc định của URP).")
        out.append("Export lại sẽ ghi đè mọi chỉnh sửa tay trên các asset này trong Unity.")
        return out


def light_hint(scene):
    """Unity Directional intensity = Blender Sun strength / pi (measured: Sun 1 gives 1/pi of diffuse light)."""
    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.data.type == 'SUN':
            strength = obj.data.energy
            return "Đèn gợi ý: Sun %s → Directional %.3f" % (round(strength, 3), strength / math.pi)
    return "Đèn gợi ý: scene không có Sun; Directional của Unity = Sun strength ÷ π"


def ambient_hint(scene):
    """The World colour is the ambient, 1:1 (Environment Lighting › Source: Color)."""
    world = scene.world
    background = None
    if world is not None and world.node_tree is not None:
        background = next((n for n in world.node_tree.nodes if n.bl_idname == 'ShaderNodeBackground'), None)
    if background is None or background.inputs["Color"].is_linked or background.inputs["Strength"].is_linked:
        return "Ambient: World không phải một màu đơn; tự đặt Environment Lighting trong Unity"
    strength = background.inputs["Strength"].default_value
    linear = [c * strength for c in background.inputs["Color"].default_value[:3]]
    hexa = "".join("%02X" % min(255, int(round(unity_yaml.linear_to_srgb(c) * 255))) for c in linear)
    return "Ambient gợi ý (Environment Lighting › Source: Color): #%s (linear %.3f, %.3f, %.3f)" % (hexa, *linear)


def readme_text(report):
    head = [
        "DaskToon Engine Export: %s" % report.name,
        "",
        "Cách dùng (Unity 6, URP 17.5):",
        "1. Kéo cả thư mục %s_Unity vào cửa sổ Project của Unity." % report.name,
        "2. Project phải dùng Linear color space (Project Settings › Player › Other Settings › Color Space).",
        "3. Đặt Directional Light và Ambient theo gợi ý bên dưới.",
        "",
        "Lưu ý: kéo thư mục của nhân vật thứ hai vào cùng project, Unity sẽ báo trùng GUID của thư mục Shaders.",
        "Material vẫn chạy đúng. Để tránh, hãy chọn thẳng thư mục project Unity khi export, hoặc dùng Dự án DaskToon.",
        "",
    ]
    return "\n".join(head + report.lines()) + "\n"


def write_text(report):
    text = bpy.data.texts.get(REPORT_TEXT) or bpy.data.texts.new(REPORT_TEXT)
    text.clear()
    text.write("\n".join(report.lines()) + "\n")
    return text


def show_popup(report):
    if bpy.app.background:
        return
    lines = report.lines()

    def draw(self, _context):
        for line in lines[:POPUP_LINES]:
            self.layout.label(text=line)
        if len(lines) > POPUP_LINES:
            self.layout.label(text="… xem đầy đủ trong Text '%s'" % REPORT_TEXT)

    bpy.context.window_manager.popup_menu(draw, title="DaskToon Engine Export", icon='INFO')
