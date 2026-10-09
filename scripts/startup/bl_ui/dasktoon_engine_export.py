# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""File › Export › Engine Export…: export the model, its DaskToon materials and the shaders for a game engine
(docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md, sections 3 and 5)."""

import os

import bpy
from bpy.app.translations import pgettext_iface as iface_, pgettext_rpt as rpt_
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import Operator

from dasktoon_export import targets


def default_directory(context):
    """(directory, engine) the dialog opens with: the open DaskToon project's engine project (spec 7), else the
    target remembered in this .blend file, else the .blend file's folder."""
    from . import dasktoon_project
    project = dasktoon_project.active_project()
    if project is not None and project.engine_path:
        return project.engine_path, project.engine
    remembered = targets.remembered_target(context.scene)
    if remembered and os.path.isdir(remembered[0]):
        return remembered
    if bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath), 'UNITY_URP'
    return "", 'UNITY_URP'


class EXPORT_SCENE_OT_dasktoon_engine(Operator):
    """Export the model, its DaskToon materials and the shaders for a game engine"""
    bl_idname = "export_scene.dasktoon_engine"
    bl_label = "Engine Export"
    bl_options = {'REGISTER'}

    directory: StringProperty(name="Folder", subtype='DIR_PATH')
    filter_folder: BoolProperty(default=True, options={'HIDDEN'})
    engine: EnumProperty(name="Engine", items=targets.ENGINES, default='UNITY_URP')
    model_format: EnumProperty(
        name="Model",
        items=(('FBX', "FBX", "Export the model as FBX"),
               ('NONE', "No Model", "Export only the materials and shaders")),
        default='FBX')
    use_selection: BoolProperty(name="Selected Objects Only", default=True)
    include_animation: BoolProperty(name="Include Animation", default=True)
    export_materials: BoolProperty(name="Export Materials and Shaders", default=True)
    bake_size: IntProperty(name="Bake Size", default=1024, min=64, max=8192, subtype='PIXEL')
    bake_samples: IntProperty(name="Bake Samples", default=16, min=1, max=4096)

    def invoke(self, context, _event):
        directory, engine = default_directory(context)
        if directory:
            self.directory = directory
        self.engine = engine
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, _context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "engine")
        layout.prop(self, "model_format")
        layout.prop(self, "use_selection")
        row = layout.row()
        row.enabled = self.model_format == 'FBX'
        row.prop(self, "include_animation")
        layout.prop(self, "export_materials")
        col = layout.column(align=True)
        col.enabled = self.export_materials
        col.prop(self, "bake_size")
        col.prop(self, "bake_samples")
        if self.directory:
            target = targets.make_target(self.directory, targets.blend_name(bpy.data.filepath), self.engine)
            box = layout.box()
            if target.mode == 'PROJECT':
                box.label(text="Writes straight into the Unity project", icon='CHECKMARK')
                box.label(text="%s/Assets/DaskToon" % os.path.basename(target.project), translate=False)
            else:
                box.label(text=iface_("Creates the folder %s") % os.path.basename(target.root), icon='FILE_FOLDER',
                          translate=False)

    def execute(self, context):
        import dasktoon_export
        from dasktoon_export import model_fbx, report
        if self.engine not in targets.SUPPORTED_ENGINES:
            self.report({'ERROR'}, rpt_("This engine is coming soon; only Unity 6 (URP) is supported for now"))
            return {'CANCELLED'}
        if not self.directory:
            self.report({'ERROR'}, rpt_("No destination folder chosen"))
            return {'CANCELLED'}
        objects = model_fbx.export_objects(context, self.use_selection)
        if not objects:
            self.report({'ERROR'}, rpt_("Nothing to export (no object selected?)"))
            return {'CANCELLED'}
        directory = bpy.path.abspath(self.directory)
        target = targets.make_target(directory, targets.blend_name(bpy.data.filepath), self.engine)
        options = dasktoon_export.ExportOptions(
            model_format=self.model_format, include_animation=self.include_animation,
            export_materials=self.export_materials, bake_size=self.bake_size, bake_samples=self.bake_samples)
        rep = dasktoon_export.export_model(context, target, objects, options)
        targets.remember_target(context.scene, self.directory, self.engine)
        report.show_popup(rep)
        self.report({'WARNING'} if rep.warnings else {'INFO'}, rep.summary())
        return {'FINISHED'}


def menu_func_export(self, _context):
    self.layout.operator(EXPORT_SCENE_OT_dasktoon_engine.bl_idname, text="Engine Export…")


classes = (EXPORT_SCENE_OT_dasktoon_engine,)


# bl_ui registers `classes` itself; register()/unregister() only manage the menu entry. bl_ui registers this module
# before space_topbar, so the menu is reached through its Python class rather than bpy.types.
def register():
    from .space_topbar import TOPBAR_MT_file_export
    TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    from .space_topbar import TOPBAR_MT_file_export
    TOPBAR_MT_file_export.remove(menu_func_export)
