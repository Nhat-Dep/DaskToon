# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""File > Export > DaskLive (.dlive) and File > Import > DaskLive (.dlive)
(docs/superpowers/specs/2026-11-10-dasktoon-dlive-design.md). The work is done by the dasktoon_dlive module."""

import os

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy.types import Operator


class EXPORT_SCENE_OT_dasktoon_dlive(Operator):
    """Pack the character for DaskLive: model, skeleton, shape keys, materials, expressions and finish in one file"""
    bl_idname = "export_scene.dasktoon_dlive"
    bl_label = "DaskLive Export"
    bl_options = {'REGISTER'}

    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default="*.dlive", options={'HIDDEN'})
    use_selection: BoolProperty(name="Selected Objects Only", default=True)
    make_expressions: BoolProperty(
        name="Make Expressions", default=True,
        description="Make the blink, mouth and the 52 face tracking shape keys the character lacks, on copies: the "
                    "file you work on stays as it is")
    texture_size: IntProperty(name="Max Texture Size", default=2048, min=64, max=8192, subtype='PIXEL',
                              description="Larger images are scaled down to this")
    block_compress: BoolProperty(name="Pre-compress Images (DDS)", default=True,
                                 description="Add a block-compressed twin of each image: DaskLive then keeps it in a "
                                             "quarter of the video memory (the export takes a few seconds more)")
    thumbnail: BoolProperty(name="Thumbnail", default=True, description="Add a small picture of the character")

    def invoke(self, context, _event):
        if not self.filepath:
            base = os.path.splitext(os.path.basename(bpy.data.filepath))[0] or "character"
            self.filepath = base + ".dlive"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        import dasktoon_dlive
        from dasktoon_export import model_fbx
        objects = model_fbx.export_objects(context, self.use_selection)
        if not objects:
            self.report({'ERROR'}, rpt_("Nothing to export (no object selected?)"))
            return {'CANCELLED'}
        path = bpy.path.ensure_ext(bpy.path.abspath(self.filepath), ".dlive")
        options = dasktoon_dlive.Options(make_expressions=self.make_expressions, texture_size=self.texture_size,
                                         thumbnail=self.thumbnail, block_compress=self.block_compress)
        rep = dasktoon_dlive.export(context, path, objects, options)
        self.report({'WARNING'} if rep.warnings else {'INFO'}, rep.summary())
        return {'FINISHED'}


class IMPORT_SCENE_OT_dasktoon_dlive(Operator):
    """Bring in a DaskLive character: the model with its DaskToon materials, shape keys and sway"""
    bl_idname = "import_scene.dasktoon_dlive"
    bl_label = "DaskLive Import"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default="*.dlive", options={'HIDDEN'})

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from dasktoon_dlive import importer
        try:
            new = importer.import_dlive(context, bpy.path.abspath(self.filepath))
        except importer.DliveError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        self.report({'INFO'}, rpt_("DaskLive: %d objects imported") % len(new))
        return {'FINISHED'}


def menu_func_export(self, _context):
    self.layout.operator(EXPORT_SCENE_OT_dasktoon_dlive.bl_idname, text="DaskLive (.dlive)")


def menu_func_import(self, _context):
    self.layout.operator(IMPORT_SCENE_OT_dasktoon_dlive.bl_idname, text="DaskLive (.dlive)")


classes = (EXPORT_SCENE_OT_dasktoon_dlive, IMPORT_SCENE_OT_dasktoon_dlive)


# bl_ui registers `classes` itself; register()/unregister() only manage the menu entries (the menus are reached
# through their Python classes: bl_ui registers this module before space_topbar).
def register():
    from .space_topbar import TOPBAR_MT_file_export, TOPBAR_MT_file_import
    TOPBAR_MT_file_export.append(menu_func_export)
    TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    from .space_topbar import TOPBAR_MT_file_export, TOPBAR_MT_file_import
    TOPBAR_MT_file_export.remove(menu_func_export)
    TOPBAR_MT_file_import.remove(menu_func_import)
