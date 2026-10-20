# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export report: Text datablock, popup, README.txt and the light hints (spec 3, 5; Godot spec 2)."""

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
GODOT_SHADER_STATE = {
    'INSTALLED': n_("Shaders and import script: installed or updated"),
    'UP_TO_DATE': n_("Shaders and import script: already up to date"),
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
    clips: list = field(default_factory=list)  # [(name, loop)] written as <Model>@<Clip>.fbx
    merged: tuple = ()  # (how many meshes, the name of the one they became)
    materials: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    baked: list = field(default_factory=list)
    outline_meshes: list = field(default_factory=list)
    face_meshes: list = field(default_factory=list)
    modifier_notes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    light_hint: str = ""
    ambient_hint: str = ""
    engine: str = 'UNITY_URP'

    def summary(self):
        if self.engine == 'GODOT_4':
            model = rpt_("with glTF") if self.model else rpt_("no model")
        else:
            model = rpt_("with FBX") if self.model else rpt_("no model")
        return rpt_("Engine Export: %d materials, %s, %d warnings") % (len(self.materials), model, len(self.warnings))

    def _godot_lines(self):
        where = rpt_("written straight into the Godot project") if self.mode == 'PROJECT' else \
            rpt_("a folder to copy into a Godot project")
        out = [rpt_("Destination: %s (%s)") % (self.root, where), rpt_(GODOT_SHADER_STATE[self.shaders])]
        if self.model:
            out.append(rpt_("Model: %s (Godot puts the DaskToon materials on it when it imports it)") % self.model)
        if self.merged:
            out.append(rpt_("Merged %d meshes of the character into one: %s") % self.merged)
        out.append(rpt_("Exported materials (%d): %s") % (len(self.materials), ", ".join(self.materials) or rpt_("none")))
        out += [rpt_("Skipped material %s: %s (Godot keeps the model's own material)") % item for item in self.skipped]
        if self.baked:
            out.append(rpt_("Baked: %s") % ", ".join(self.baked))
        if self.outline_meshes:
            out.append(rpt_("Wrote DT_OutlineN/W for: %s") % ", ".join(self.outline_meshes))
        if self.face_meshes:
            out.append(rpt_("Face shading: wrote the egg proxy normals (rest pose) for: %s; blend shapes do not "
                            "change normals") % ", ".join(self.face_meshes))
        out += self.modifier_notes
        out += [rpt_("Warning: %s") % w for w in self.warnings]
        out += [hint for hint in (self.light_hint, self.ambient_hint) if hint]
        out.append(rpt_("DaskToon's materials light themselves from World Ambient, not from Godot's ambient light."))
        out.append(rpt_("Exporting again overwrites any manual edits to these files in Godot."))
        return out

    def lines(self):
        if self.engine == 'GODOT_4':
            return self._godot_lines()
        where = rpt_("written straight into the Unity project") if self.mode == 'PROJECT' else \
            rpt_("a folder to drag into Unity")
        out = [rpt_("Destination: %s (%s)") % (self.root, where), rpt_(SHADER_STATE[self.shaders])]
        if self.model:
            out.append(rpt_("Model: %s") % self.model)
        if self.merged:
            out.append(rpt_("Merged %d meshes of the character into one: %s") % self.merged)
        if self.rig:
            out.append(rpt_("Rig: %s (DaskToon's Unity scripts read it: swaying hair and skirts, eyes, mouth, bend fixes)") % self.rig)
        if self.scripts != 'SKIPPED':
            out.append(rpt_(SCRIPT_STATE[self.scripts]))
        if self.clips:
            out.append(rpt_("Clips: %s") % ", ".join(rpt_("%s (loop)") % name if loop else name
                                                      for name, loop in self.clips))
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


def _hex(linear):
    return "".join("%02X" % min(255, int(round(unity_yaml.linear_to_srgb(c) * 255))) for c in linear)


def light_hint(scene, engine='UNITY_URP'):
    """Unity Directional intensity = Blender Sun strength / pi (measured: Sun 1 gives 1/pi of diffuse light). Godot's
    DirectionalLight3D energy is the same (measured: LIGHT_COLOR is colour x energy x pi); its colour is sRGB."""
    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.data.type == 'SUN':
            strength = obj.data.energy
            if engine == 'GODOT_4':
                return rpt_("Suggested light: Sun %s → DirectionalLight3D energy %.3f, color #%s") % (
                    round(strength, 3), strength / math.pi, _hex(obj.data.color))
            return rpt_("Suggested light: Sun %s → Directional %.3f") % (round(strength, 3), strength / math.pi)
    if engine == 'GODOT_4':
        return rpt_("Suggested light: the scene has no Sun; DirectionalLight3D energy = Sun strength ÷ π")
    return rpt_("Suggested light: the scene has no Sun; Unity Directional = Sun strength ÷ π")


def ambient_hint(scene, engine='UNITY_URP'):
    """The World colour is the ambient, 1:1 (Unity: Environment Lighting › Source: Color; Godot: the materials' World
    Ambient, written by the export)."""
    world = scene.world
    background = None
    if world is not None and world.node_tree is not None:
        background = next((n for n in world.node_tree.nodes if n.bl_idname == 'ShaderNodeBackground'), None)
    if background is None or background.inputs["Color"].is_linked or background.inputs["Strength"].is_linked:
        if engine == 'GODOT_4':
            return rpt_("Ambient: the World is not a single color; World Ambient in the materials is Blender's "
                        "default grey, change it in Godot if needed")
        return rpt_("Ambient: the World is not a single color; set Environment Lighting in Unity yourself")
    strength = background.inputs["Strength"].default_value
    linear = [c * strength for c in background.inputs["Color"].default_value[:3]]
    if engine == 'GODOT_4':
        return rpt_("Ambient: World Ambient in the materials is the World color #%s (linear %.3f, %.3f, %.3f)") % (
            _hex(linear), *linear)
    return rpt_("Suggested ambient (Environment Lighting › Source: Color): #%s (linear %.3f, %.3f, %.3f)") % (
        _hex(linear), *linear)


def _godot_readme(report):
    head = [
        rpt_("DaskToon Engine Export: %s") % report.name,
        "",
        rpt_("How to use (Godot 4.3 or newer, Forward+ or Mobile renderer):"),
        rpt_("1. Copy the DaskToon folder into the root of the Godot project, so that it becomes res://DaskToon. With a "
             "second character, copy it over the one already there."),
        rpt_("2. Godot imports the model and puts the DaskToon materials on it. Drag %s/%s.glb into a scene.")
        % (report.name, report.name),
        rpt_("3. Set the DirectionalLight3D as suggested below."),
        "",
    ]
    return "\n".join(head + report.lines()) + "\n"


def readme_text(report):
    if report.engine == 'GODOT_4':
        return _godot_readme(report)
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
