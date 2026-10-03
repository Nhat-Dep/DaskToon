# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon projects in the UI: File › Dự án DaskToon and the sidebar panel DaskToon › Dự án
(docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md, section 7)."""

import os
import time

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Menu, Operator, Panel

from dasktoon_export import targets
from dasktoon_project import project as dtp

_session = {"project_file": ""}  # project opened with "Mở dự án…", remembered for this session only
_models_cache = {"key": None, "time": 0.0, "models": []}
MODELS_REFRESH = 2.0  # seconds; the panel redraws often and must not walk the folder every time


def forget_session_project():
    _session["project_file"] = ""


def active_project():
    """The project holding the open .blend file, else the one opened this session (spec 7)."""
    found = dtp.find_project(bpy.data.filepath)
    if found is not None:
        return found
    path = _session["project_file"]
    if path and os.path.isfile(path):
        try:
            return dtp.load(path)
        except (OSError, ValueError):
            return None
    return None


def _models(project):
    now = time.monotonic()
    if _models_cache["key"] != project.folder or now - _models_cache["time"] > MODELS_REFRESH:
        _models_cache.update(key=project.folder, time=now, models=dtp.project_models(project))
    return _models_cache["models"]


def _require_project(op):
    project = active_project()
    if project is None:
        op.report({'ERROR'}, "Chưa mở dự án DaskToon nào")
    return project


class DASKTOON_OT_project_create(Operator):
    """Create a DaskToon project linked to a Unity project and install the DaskToon shaders into it"""
    bl_idname = "dasktoon.project_create"
    bl_label = "Tạo dự án DaskToon"
    bl_options = {'REGISTER'}

    name: StringProperty(name="Tên", default="Dự án mới")
    folder: StringProperty(name="Thư mục dự án", subtype='DIR_PATH')
    engine: EnumProperty(name="Engine", items=targets.ENGINES, default='UNITY_URP')
    engine_path: StringProperty(name="Project Unity", subtype='DIR_PATH')
    save_current: BoolProperty(name="Lưu file hiện tại vào dự án", default=True)

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self, width=520)

    def execute(self, _context):
        try:
            project = dtp.create_project(self.name, bpy.path.abspath(self.folder), self.engine,
                                         bpy.path.abspath(self.engine_path), self.save_current)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        _session["project_file"] = project.file
        self.report({'INFO'}, "Đã tạo dự án %s và cài shader vào %s" % (project.name, project.engine_path))
        return {'FINISHED'}


class DASKTOON_OT_project_open(Operator):
    """Open a DaskToon project (dasktoon_project.json)"""
    bl_idname = "dasktoon.project_open"
    bl_label = "Mở dự án DaskToon"

    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default="dasktoon_project.json", options={'HIDDEN'})

    def invoke(self, context, _event):
        if self.filepath and os.path.isfile(self.filepath):
            return self.execute(context)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, _context):
        try:
            project = dtp.load(self.filepath)
        except (OSError, ValueError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        _session["project_file"] = project.file
        dtp.add_recent(project.file)
        self.report({'INFO'}, "Đã mở dự án %s" % project.name)
        return {'FINISHED'}


class DASKTOON_OT_project_open_model(Operator):
    """Open this .blend file of the project (DaskToon asks to save the current file first when it has changes)"""
    bl_idname = "dasktoon.project_open_model"
    bl_label = "Mở"

    filepath: StringProperty(subtype='FILE_PATH', options={'HIDDEN'})

    def execute(self, _context):
        bpy.ops.wm.open_mainfile('INVOKE_DEFAULT', filepath=self.filepath, display_file_selector=False)
        return {'FINISHED'}


class DASKTOON_OT_project_export(Operator):
    """Export this file's model, materials and shaders straight into the project's Unity project"""
    bl_idname = "dasktoon.project_export"
    bl_label = "Export model này"

    def execute(self, context):
        import dasktoon_export
        from dasktoon_export import model_fbx, report
        project = _require_project(self)
        if project is None:
            return {'CANCELLED'}
        objects = model_fbx.export_objects(context, selected_only=False)
        if not objects:
            self.report({'ERROR'}, "File không có object nào để export")
            return {'CANCELLED'}
        target = dtp.project_target(project, targets.blend_name(bpy.data.filepath))
        rep = dasktoon_export.export_model(context, target, objects, dasktoon_export.ExportOptions())
        report.show_popup(rep)
        self.report({'WARNING'} if rep.warnings else {'INFO'}, rep.summary())
        return {'FINISHED'}


class DASKTOON_OT_project_reinstall_shaders(Operator):
    """Write the DaskToon shaders into the project's Unity project again"""
    bl_idname = "dasktoon.project_reinstall_shaders"
    bl_label = "Cài lại shader"

    def execute(self, _context):
        project = _require_project(self)
        if project is None:
            return {'CANCELLED'}
        _written, warnings = dtp.install_project_shaders(project, force=True)
        for warning in warnings:
            self.report({'WARNING'}, warning)
        self.report({'INFO'}, "Đã cài lại shader vào %s" % project.engine_path)
        return {'FINISHED'}


class DASKTOON_OT_project_open_folder(Operator):
    """Open the project folder in the file manager"""
    bl_idname = "dasktoon.project_open_folder"
    bl_label = "Mở thư mục dự án"

    def execute(self, _context):
        project = _require_project(self)
        if project is None:
            return {'CANCELLED'}
        bpy.ops.wm.path_open(filepath=project.folder)
        return {'FINISHED'}


class TOPBAR_MT_dasktoon_project(Menu):
    bl_label = "Dự án DaskToon"

    def draw(self, _context):
        layout = self.layout
        layout.operator(DASKTOON_OT_project_create.bl_idname, text="Tạo dự án…", icon='NEWFOLDER')
        layout.operator(DASKTOON_OT_project_open.bl_idname, text="Mở dự án…", icon='FILE_FOLDER')


class VIEW3D_PT_dasktoon_project(Panel):
    bl_label = "Dự án"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"

    def draw(self, _context):
        from dasktoon_export import shaders_install
        layout = self.layout
        project = active_project()
        if project is None:
            col = layout.column(align=True)
            col.operator(DASKTOON_OT_project_create.bl_idname, text="Tạo dự án…", icon='NEWFOLDER')
            col.operator(DASKTOON_OT_project_open.bl_idname, text="Mở dự án…", icon='FILE_FOLDER')
            recent = dtp.recent_projects()
            if recent:
                layout.label(text="Dự án gần đây:")
                col = layout.column(align=True)
                for path in recent:
                    op = col.operator(DASKTOON_OT_project_open.bl_idname,
                                      text=os.path.basename(os.path.dirname(path)), icon='FILE_FOLDER')
                    op.filepath = path
            return
        box = layout.box()
        box.label(text=project.name, icon='FILE_FOLDER')
        engines = {key: label for key, label, _desc in targets.ENGINES}
        box.label(text="Engine: " + engines.get(project.engine, project.engine))
        box.label(text=project.engine_path)
        version = shaders_install.installed_version(os.path.join(project.engine_path, "Assets", "DaskToon"))
        box.label(text=("Shader: phiên bản %d" % version) if version else "Shader: chưa cài",
                  icon='CHECKMARK' if version else 'ERROR')
        current = os.path.normcase(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else ""
        col = layout.column(align=True)
        for path in _models(project):
            row = col.row(align=True)
            is_current = os.path.normcase(path) == current
            row.label(text=os.path.relpath(path, project.folder), icon='RADIOBUT_ON' if is_current else 'BLENDER')
            op = row.operator(DASKTOON_OT_project_open_model.bl_idname, text="Mở")
            op.filepath = path
        layout.operator(DASKTOON_OT_project_export.bl_idname, icon='EXPORT')
        row = layout.row(align=True)
        row.operator(DASKTOON_OT_project_reinstall_shaders.bl_idname, icon='FILE_REFRESH')
        row.operator(DASKTOON_OT_project_open_folder.bl_idname, icon='FILEBROWSER')


def menu_func_file(self, _context):
    self.layout.separator()
    self.layout.menu(TOPBAR_MT_dasktoon_project.bl_idname, icon='FILE_FOLDER')


classes = (
    DASKTOON_OT_project_create,
    DASKTOON_OT_project_open,
    DASKTOON_OT_project_open_model,
    DASKTOON_OT_project_export,
    DASKTOON_OT_project_reinstall_shaders,
    DASKTOON_OT_project_open_folder,
    TOPBAR_MT_dasktoon_project,
    VIEW3D_PT_dasktoon_project,
)


# bl_ui registers `classes` itself; register()/unregister() only manage the File menu entry. bl_ui registers this module
# before space_topbar, so the menu is reached through its Python class rather than bpy.types.
def register():
    from .space_topbar import TOPBAR_MT_file
    TOPBAR_MT_file.append(menu_func_file)


def unregister():
    from .space_topbar import TOPBAR_MT_file
    TOPBAR_MT_file.remove(menu_func_file)
