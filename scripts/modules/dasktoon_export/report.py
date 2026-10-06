# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export report: Text datablock, popup, README.txt and the light hints (spec 3, 5)."""

import math
from dataclasses import dataclass, field

import bpy
from bpy.app.translations import pgettext_iface as iface_, pgettext_n as n_, pgettext_rpt as rpt_

from . import unity_yaml

REPORT_TEXT = "DaskToon Engine Export Report"
POPUP_LINES = 14
SHADER_STATE = {
    'INSTALLED': n_("Shaders: installed or updated"),
    'UP_TO_DATE': n_("Shaders: the project already has a recent enough version, not written again"),
    'SKIPPED': n_("Shaders: not exported (material export is off)"),
}
SCRIPT_STATE = {
    'INSTALLED': n_("Scripts: installed or updated"),
    'UP_TO_DATE': n_("Scripts: the project already has a recent enough version, not written again"),
    'SKIPPED': n_("Scripts: not needed (no hair or skirt chains)"),
}


@dataclass
class Report:
    mode: str
    root: str
    name: str
    shaders: str = 'SKIPPED'
    model: str = ""
    rig: str = ""
    scripts: str = 'SKIPPED'
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
        return rpt_("Engine Export: %d materials, %s, %d warnings") % (
            len(self.materials), rpt_("with FBX") if self.model else rpt_("no model"), len(self.warnings))

    def lines(self):
        where = rpt_("written straight into the Unity project") if self.mode == 'PROJECT' else \
            rpt_("a folder to drag into Unity")
        out = [rpt_("Destination: %s (%s)") % (self.root, where), rpt_(SHADER_STATE[self.shaders])]
        if self.model:
            out.append(rpt_("Model: %s") % self.model)
        if self.rig:
            out.append(rpt_("Rig: %s (DaskToon spring bones sway the hair and skirts in Unity)") % self.rig)
            out.append(rpt_(SCRIPT_STATE[self.scripts]))
        out.append(rpt_("Exported materials (%d): %s") % (len(self.materials), ", ".join(self.materials) or rpt_("none")))
        out += [rpt_("Skipped material %s: %s (Unity keeps the default material of the FBX)") % item
                for item in self.skipped]
        if self.baked:
            out.append(rpt_("Baked: %s") % ", ".join(self.baked))
        if self.outline_meshes:
            out.append(rpt_("Wrote DT_OutlineN/W for: %s") % ", ".join(self.outline_meshes))
        if self.face_meshes:
            out.append(rpt_("Face shading: wrote the egg proxy normals (rest pose) for: %s; blend shapes in the FBX do "
                            "not change normals") % ", ".join(self.face_meshes))
        out += self.modifier_notes
        out += [rpt_("Warning: %s") % w for w in self.warnings]
        out += [hint for hint in (self.light_hint, self.ambient_hint) if hint]
        out.append(rpt_("The Unity project must use the Linear color space (the URP default)."))
        out.append(rpt_("Exporting again overwrites any manual edits to these assets in Unity."))
        return out


def light_hint(scene):
    """Unity Directional intensity = Blender Sun strength / pi (measured: Sun 1 gives 1/pi of diffuse light)."""
    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.data.type == 'SUN':
            strength = obj.data.energy
            return rpt_("Suggested light: Sun %s → Directional %.3f") % (round(strength, 3), strength / math.pi)
    return rpt_("Suggested light: the scene has no Sun; Unity Directional = Sun strength ÷ π")


def ambient_hint(scene):
    """The World colour is the ambient, 1:1 (Environment Lighting › Source: Color)."""
    world = scene.world
    background = None
    if world is not None and world.node_tree is not None:
        background = next((n for n in world.node_tree.nodes if n.bl_idname == 'ShaderNodeBackground'), None)
    if background is None or background.inputs["Color"].is_linked or background.inputs["Strength"].is_linked:
        return rpt_("Ambient: the World is not a single color; set Environment Lighting in Unity yourself")
    strength = background.inputs["Strength"].default_value
    linear = [c * strength for c in background.inputs["Color"].default_value[:3]]
    hexa = "".join("%02X" % min(255, int(round(unity_yaml.linear_to_srgb(c) * 255))) for c in linear)
    return rpt_("Suggested ambient (Environment Lighting › Source: Color): #%s (linear %.3f, %.3f, %.3f)") % (
        hexa, *linear)


def readme_text(report):
    head = [
        rpt_("DaskToon Engine Export: %s") % report.name,
        "",
        rpt_("How to use (Unity 6, URP 17.5):"),
        rpt_("1. Drag the whole %s_Unity folder into the Project window of Unity.") % report.name,
        rpt_("2. The project must use the Linear color space (Project Settings › Player › Other Settings › "
             "Color Space)."),
        rpt_("3. Set the Directional Light and the Ambient as suggested below."),
        "",
        rpt_("Note: drag the folder of a second character into the same project and Unity reports a duplicate GUID "
             "for the Shaders folder."),
        rpt_("The materials still work. To avoid it, choose the Unity project folder itself when exporting, or use "
             "a DaskToon Project."),
    ]
    if report.rig:
        # Two copies of the same C# classes do not compile, unlike two copies of a shader.
        head.append(rpt_("Note: the Scripts folder may be in a Unity project only once. With a second character, "
                         "delete its Scripts folder after dragging it in, or export into the Unity project itself."))
    head.append("")
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
            self.layout.label(text=line, translate=False)
        if len(lines) > POPUP_LINES:
            self.layout.label(text=iface_("… the full report is in the Text %s") % REPORT_TEXT, translate=False)

    bpy.context.window_manager.popup_menu(draw, title=iface_("DaskToon Engine Export"), icon='INFO')
