# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""File › Import › Unreal Model (.uemodel) and MikuMikuDance Model (.pmx, .pmd), also by dropping the file on the
window: DaskToon's own reader (dasktoon_import.uemodel) and MMD Tools, which DaskToon ships on. With DaskToon Character
on (the default) the model comes in ready for DaskToon (dasktoon_import.adopt, docs/superpowers/specs/2026-11-10-
dasktoon-import-adopt-design.md); Object › Make DaskToon Character does the same to a model imported before."""

import os

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import BoolProperty, CollectionProperty, FloatProperty, StringProperty
from bpy.types import FileHandler, Operator, OperatorFileListElement
from bpy_extras.io_utils import ImportHelper

ADOPT_DESCRIPTION = ("Make the model a DaskToon character: standing in the middle facing the front, DaskToon's skeleton "
                     "with the model's own weights, swaying hair and skirts, DaskToon's expression names and shader")


def _report_adopted(op, result):
    op.report({'INFO'}, rpt_("%s is a DaskToon character: %d swaying chains, %d expressions, %d materials") % (
        result.rig.name, result.chains, len(result.expressions), result.materials))


SHADER_DESCRIPTION = "Give every material of the model DaskToon's shader with an outline, keeping its colour or texture"


def _new_objects(before):
    return [obj for obj in bpy.data.objects if obj not in before]


def _shade(op, objects):
    """DaskToon's shader on the materials of the new meshes, whether or not they became a character."""
    from dasktoon_import import adopt
    if op.shader:
        # not MMD Tools' rigid bodies and joints, shown as meshes when the physics is imported
        adopt.convert_materials([obj for obj in objects if obj.type == 'MESH'
                                 and getattr(obj, "mmd_type", 'NONE') == 'NONE'])


def _paths(op):
    paths = [os.path.join(op.directory, f.name) for f in op.files if f.name] if op.files else []
    return paths or [op.filepath]


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
    dasktoon: BoolProperty(name="DaskToon Character", description=ADOPT_DESCRIPTION, default=True)
    shader: BoolProperty(name="DaskToon Shader", description=SHADER_DESCRIPTION, default=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        from dasktoon_import import adopt, uemodel
        done = 0
        before = set(bpy.data.objects)
        for path in _paths(self):
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
            if self.dasktoon and rig is not None:
                try:
                    _report_adopted(self, adopt.adopt(context, rig, [obj], kind='UNREAL'))
                except adopt.AdoptError as ex:
                    self.report({'WARNING'}, "%s: %s" % (os.path.basename(path), ex))
        _shade(self, _new_objects(before))
        return {'FINISHED'} if done else {'CANCELLED'}


class DASKTOON_OT_import_mmd(Operator, ImportHelper):
    """Import a MikuMikuDance model (.pmx, .pmd) with MMD Tools"""
    bl_idname = "dasktoon.import_mmd"
    bl_label = "Import MikuMikuDance Model"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    filename_ext = ".pmx"
    filter_glob: StringProperty(default="*.pmx;*.pmd", options={'HIDDEN'})
    files: CollectionProperty(type=OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    scale: FloatProperty(
        name="Scale", description="MikuMikuDance units are 8 cm: 0.08 gives metres", default=0.08, min=1e-6,
        soft_max=1.0)
    dasktoon: BoolProperty(name="DaskToon Character", description=ADOPT_DESCRIPTION, default=True)
    shader: BoolProperty(name="DaskToon Shader", description=SHADER_DESCRIPTION, default=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and hasattr(bpy.ops.mmd_tools, "import_model")

    def execute(self, context):
        from dasktoon_import import adopt, mmd
        done = 0
        before = set(bpy.data.objects)
        for path in _paths(self):
            start = set(bpy.data.objects)
            try:
                if self.dasktoon:
                    mmd.import_file(context, path, self.scale)
                else:
                    bpy.ops.mmd_tools.import_model(filepath=path, scale=self.scale)
            except (RuntimeError, OSError) as ex:
                self.report({'ERROR'}, "%s: %s" % (os.path.basename(path), ex))
                continue
            done += 1
            if self.dasktoon:
                try:
                    _report_adopted(self, mmd.adopt_imported(context, path, _new_objects(start)))
                except adopt.AdoptError as ex:  # a skeleton DaskToon does not know: the model stays as imported
                    self.report({'WARNING'}, "%s: %s" % (os.path.basename(path), ex))
        _shade(self, _new_objects(before))
        return {'FINISHED'} if done else {'CANCELLED'}


class DASKTOON_OT_adopt_character(Operator):
    bl_idname = "dasktoon.adopt_character"
    bl_label = "Make DaskToon Character"
    bl_description = ("Make the selected imported model a DaskToon character: standing in the middle facing the front, "
                      "DaskToon's skeleton with the model's own weights, swaying hair and skirts, DaskToon's expression "
                      "names and shader")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        from dasktoon_rig import skeleton
        armatures = [o for o in context.selected_objects if o.type == 'ARMATURE']
        return context.mode == 'OBJECT' and armatures and not any(skeleton.is_humanoid(o) for o in armatures)

    def execute(self, context):
        from dasktoon_import import adopt
        armature, meshes = adopt.source_of(context.selected_objects)
        if armature is None or not meshes:
            self.report({'ERROR'}, rpt_("Select the model's skeleton and the meshes it moves"))
            return {'CANCELLED'}
        kind = 'MMD' if armature.pose.bones and hasattr(armature.pose.bones[0], "mmd_bone") and any(
            pb.mmd_bone.name_j for pb in armature.pose.bones) else 'OTHER'
        swaying = None
        root = armature.parent
        if kind == 'MMD' and root is not None and getattr(root, "mmd_type", None) == 'ROOT':
            swaying = _mmd_swaying(armature, root)
        try:
            _report_adopted(self, adopt.adopt(context, armature, meshes, kind=kind, swaying=swaying))
        except adopt.AdoptError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        return {'FINISHED'}


def _mmd_swaying(armature, root):
    """The bones MMD Tools' dynamic rigid bodies move, when the model was imported with its physics."""
    out = set()
    for obj in root.children_recursive:
        rigid = getattr(obj, "mmd_rigid", None)
        if obj.mmd_type == 'RIGID_BODY' and rigid is not None and rigid.type in {'1', '2'} and rigid.bone:
            if armature.data.bones.get(rigid.bone) is not None:
                out.add(rigid.bone)
    return out or None


class DASKTOON_FH_uemodel(FileHandler):
    bl_idname = "DASKTOON_FH_uemodel"
    bl_label = "Unreal Model"
    bl_import_operator = "dasktoon.import_uemodel"
    bl_file_extensions = ".uemodel"

    @classmethod
    def poll_drop(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'


class DASKTOON_FH_mmd(FileHandler):
    bl_idname = "DASKTOON_FH_mmd"
    bl_label = "MikuMikuDance Model"
    bl_import_operator = "dasktoon.import_mmd"
    bl_file_extensions = ".pmx;.pmd"

    @classmethod
    def poll_drop(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'


def menu_func_import(self, _context):
    self.layout.operator(DASKTOON_OT_import_mmd.bl_idname, text="MikuMikuDance Model (.pmx, .pmd)")
    self.layout.operator(DASKTOON_OT_import_uemodel.bl_idname, text="Unreal Model (.uemodel)")


def menu_func_object(self, _context):
    self.layout.separator()
    self.layout.operator(DASKTOON_OT_adopt_character.bl_idname, icon='ARMATURE_DATA')


classes = (
    DASKTOON_OT_import_uemodel,
    DASKTOON_OT_import_mmd,
    DASKTOON_OT_adopt_character,
    DASKTOON_FH_uemodel,
    DASKTOON_FH_mmd,
)


# bl_ui registers `classes` itself; register()/unregister() only manage the menu entries. bl_ui registers this module
# before space_topbar and space_view3d, so the menus are reached through their Python classes rather than bpy.types.
def register():
    from .space_topbar import TOPBAR_MT_file_import
    from .space_view3d import VIEW3D_MT_object
    TOPBAR_MT_file_import.append(menu_func_import)
    VIEW3D_MT_object.append(menu_func_object)


def unregister():
    from .space_topbar import TOPBAR_MT_file_import
    from .space_view3d import VIEW3D_MT_object
    TOPBAR_MT_file_import.remove(menu_func_import)
    VIEW3D_MT_object.remove(menu_func_object)
