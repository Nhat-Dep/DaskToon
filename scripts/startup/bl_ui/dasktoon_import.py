# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""File › Import › Unreal Model (.uemodel), and dropping a .uemodel on the window: DaskToon's own reader
(dasktoon_import.uemodel). MikuMikuDance models come from MMD Tools, which DaskToon ships on."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import BoolProperty, CollectionProperty, FloatProperty, StringProperty
from bpy.types import FileHandler, Operator, OperatorFileListElement
from bpy_extras.io_utils import ImportHelper


class DASKTOON_OT_import_uemodel(Operator, ImportHelper):
    """Import an Unreal model (.uemodel, as FModel writes it): mesh, skeleton, shape keys and textures"""
    bl_idname = "dasktoon.import_uemodel"
    bl_label = "Import Unreal Model"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    filename_ext = ".uemodel"
    filter_glob: StringProperty(default="*.uemodel", options={'HIDDEN'})
    files: CollectionProperty(type=OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    scale: FloatProperty(
        name="Scale", description="Unreal works in centimetres: 0.01 gives metres", default=0.01, min=1e-6,
        soft_max=1.0)
    shape_keys: BoolProperty(name="Shape Keys", description="Import the morph targets as shape keys", default=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        import os
        from dasktoon_import import uemodel
        paths = [os.path.join(self.directory, f.name) for f in self.files if f.name] if self.files else []
        if not paths:
            paths = [self.filepath]
        done = 0
        for path in paths:
            try:
                rig, obj = uemodel.import_file(context, path, self.scale, self.shape_keys)
            except (OSError, uemodel.FormatError) as ex:
                self.report({'ERROR'}, "%s: %s" % (os.path.basename(path), ex))
                continue
            done += 1
            keys = obj.data.shape_keys
            self.report({'INFO'}, rpt_("Imported %s: %d vertices, %d bones, %d shape keys") % (
                obj.name, len(obj.data.vertices), len(rig.data.bones) if rig else 0,
                len(keys.key_blocks) - 1 if keys else 0))
        return {'FINISHED'} if done else {'CANCELLED'}


class DASKTOON_FH_uemodel(FileHandler):
    bl_idname = "DASKTOON_FH_uemodel"
    bl_label = "Unreal Model"
    bl_import_operator = "dasktoon.import_uemodel"
    bl_file_extensions = ".uemodel"

    @classmethod
    def poll_drop(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'


def menu_func_import(self, _context):
    self.layout.operator(DASKTOON_OT_import_uemodel.bl_idname, text="Unreal Model (.uemodel)")


classes = (
    DASKTOON_OT_import_uemodel,
    DASKTOON_FH_uemodel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
