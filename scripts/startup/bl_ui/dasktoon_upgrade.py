# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""One-time upgrade of files saved before the shading/outline rewrite (spec section 6)."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.app.handlers import persistent

from . import dasktoon_outline as outline

DATA_VERSION = 1
VERSION_PROP = "dasktoon_data_version"
REPORT_TEXT = "DaskToon Upgrade Report"
LEGACY_MODIFIERS = {"DaskToon_Outline", "DaskToon_Outline_Solidify"}


def needs_upgrade():
    return any(scene.get(VERSION_PROP, 0) < DATA_VERSION for scene in bpy.data.scenes)


def _shader_trees():
    for mat in bpy.data.materials:
        if mat.node_tree is not None and mat.library is None:
            yield mat.node_tree
    for group in bpy.data.node_groups:
        if group.bl_idname == 'ShaderNodeTree' and group.library is None:
            yield group


def upgrade_nodes(lines):
    count = 0
    for tree in _shader_trees():
        for node in tree.nodes:
            if node.bl_idname == 'ShaderNodeAnimeCel':
                node.ambient_mode = 'HUE_SAT'
                node.light_blend_mode = 'MULTIPLY'
                count += 1
    if count:
        lines.append(rpt_("Anime Cel: %d nodes switched to Ambient HUE_SAT / Light MULTIPLY (closest to the old look)")
                     % count)


def _is_legacy_outline_material(mat):
    return mat is not None and mat.name.endswith("_DaskOutline")


def _legacy_settings(legacy_mat):
    node = outline.outline_node(legacy_mat)
    if node is None:
        return None
    return {
        "tint_mode": node.tint_mode,
        "color_socket": node.inputs["Outline Color"],
        "values": {name: node.inputs[name].default_value for name in
                   ("Outline Lighting Mix", "Light Bleed", "Hand Wobble", "Tint Darkness", "Tint Saturation Boost")},
    }


def _enable_outline(mat, width):
    main = next((n for n in mat.node_tree.nodes
                 if n.bl_idname in {'ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel'}), None)
    if main is not None and main.bl_idname == 'ShaderNodeAnimeCharacter':
        main.use_outline = True
    elif main is not None:
        main.inputs["Use Outline"].default_value = True
    else:
        mat[outline.OUTLINE_PROP] = True
    if width is not None:
        # The Solidify thickness is what the user saw. The old handler kept it equal to the largest
        # node width; it only differs after a manual Solidify edit or the old OUTLINE preset.
        if main is not None:
            main.inputs["Outline Width"].default_value = width
        else:
            outline.outline_node(outline.outline_material_for(mat)).inputs["Outline Width"].default_value = width
    return main


def upgrade_legacy_outline(lines):
    from .dasktoon_outline import _sync_outline_socket
    copied = {}
    removed_slots = 0
    for obj in list(bpy.data.objects):
        if obj.type != 'MESH':
            continue
        mods = [m for m in obj.modifiers if m.type == 'SOLIDIFY' and m.name in LEGACY_MODIFIERS]
        slots = [i for i, m in enumerate(obj.data.materials) if _is_legacy_outline_material(m)]
        if not mods and not slots:
            continue
        if obj.library is not None or obj.data.library is not None:
            lines.append(rpt_("Skipped %s (data linked from a library)") % obj.name)
            continue
        width = mods[0].thickness if mods else None
        legacy_mat = obj.data.materials[slots[0]] if slots else bpy.data.materials.get(obj.name + "_DaskOutline")
        settings = _legacy_settings(legacy_mat) if legacy_mat is not None else None
        for mod in mods:
            obj.modifiers.remove(mod)
        for i in reversed(slots):
            obj.data.materials.pop(index=i)
            removed_slots += 1
        for mat in obj.data.materials:
            if mat is None or mat.node_tree is None or _is_legacy_outline_material(mat):
                continue
            _enable_outline(mat, width)
            if settings is None:
                continue
            if mat in copied:
                if copied[mat] != obj.name:
                    lines.append(rpt_("Conflict: %s shares material %s; kept the settings of %s")
                                 % (obj.name, mat.name, copied[mat]))
                continue
            companion = outline.outline_material_for(mat)
            dask = outline.outline_node(companion)
            dask.tint_mode = settings["tint_mode"]
            for name, value in settings["values"].items():
                dask.inputs[name].default_value = value
            _sync_outline_socket(settings["color_socket"], companion.node_tree, dask.inputs["Outline Color"], {})
            copied[mat] = obj.name
        lines.append(rpt_("Upgraded the outline of %s") % obj.name)
    orphans = [m for m in bpy.data.materials if _is_legacy_outline_material(m) and m.users == 0]
    for mat in orphans:
        bpy.data.materials.remove(mat)
    if removed_slots or orphans:
        lines.append(rpt_("Removed %d extra slots and %d _DaskOutline materials") % (removed_slots, len(orphans)))


def _report(lines):
    text = bpy.data.texts.get(REPORT_TEXT) or bpy.data.texts.new(REPORT_TEXT)
    text.clear()
    text.write("\n".join(lines) + "\n")
    summary = rpt_("DaskToon upgraded the file: %s") % (lines[0] if lines else rpt_("nothing"))
    print(summary)
    if bpy.app.background:
        return

    def draw(self, _context):
        for line in lines[:8]:
            self.layout.label(text=line, translate=False)

    def show():
        wm = bpy.context.window_manager
        if wm.windows:
            wm.popup_menu(draw, title="DaskToon", icon='INFO')
        return None

    bpy.app.timers.register(show, first_interval=0.5)


@persistent
def upgrade_load_post(_filepath):
    if needs_upgrade():
        lines = []
        upgrade_nodes(lines)
        upgrade_legacy_outline(lines)
        for scene in bpy.data.scenes:
            if scene.library is None:
                scene[VERSION_PROP] = DATA_VERSION
        if lines:
            _report(lines)
    outline.reset_cache()
    for scene in bpy.data.scenes:
        outline.sync_all(scene)


@persistent
def stamp_save_pre(_filepath):
    for scene in bpy.data.scenes:
        if scene.library is None and scene.get(VERSION_PROP) != DATA_VERSION:
            scene[VERSION_PROP] = DATA_VERSION


classes = ()


# bl_ui registers `classes` itself; register()/unregister() only manage the handlers.
def register():
    if upgrade_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(upgrade_load_post)
    if stamp_save_pre not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(stamp_save_pre)


def unregister():
    if upgrade_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(upgrade_load_post)
    if stamp_save_pre in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(stamp_save_pre)
