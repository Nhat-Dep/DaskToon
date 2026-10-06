# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon projects in the UI: File › DaskToon Project (docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md,
section 7; docs/superpowers/specs/2026-10-04-dasktoon-ui-reorganization-design.md, section 3)."""

import os
import time

import bpy
from bpy.app.translations import pgettext_iface as iface_, pgettext_rpt as rpt_
from bpy.props import EnumProperty, StringProperty
from bpy.types import Menu, Operator

from dasktoon_export import targets
from dasktoon_project import project as dtp

_session = {"project_file": ""}  # project opened with Open Project…, remembered for this session only
_models_cache = {"key": None, "time": 0.0, "models": []}
MODELS_REFRESH = 2.0  # seconds; the menu redraws often and must not walk the folder every time


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
        op.report({'ERROR'}, rpt_("No DaskToon project is open"))
    return project


class DASKTOON_OT_project_create(Operator):
    """Create a DaskToon project linked to a Unity project and install the DaskToon shaders into it"""
    bl_idname = "dasktoon.project_create"
    bl_label = "Create DaskToon Project"
    bl_options = {'REGISTER'}

    name: StringProperty(name="Name", default="New Project")
    folder: StringProperty(name="Project Folder", subtype='DIR_PATH')
    engine: EnumProperty(name="Engine", items=targets.ENGINES, default='UNITY_URP')
    engine_path: StringProperty(name="Unity Project", subtype='DIR_PATH')

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self, width=520)

    def execute(self, _context):
        try:
            project = dtp.create_project(self.name, bpy.path.abspath(self.folder),
                                         bpy.path.abspath(self.engine_path) if self.engine_path else "", self.engine)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        _session["project_file"] = project.file
        self.report({'INFO'}, rpt_("Created project %s") % project.name)
        return {'FINISHED'}


class DASKTOON_OT_project_open(Operator):
    """Open a DaskToon project (dasktoon_project.json)"""
    bl_idname = "dasktoon.project_open"
    bl_label = "Open DaskToon Project"

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
        self.report({'INFO'}, rpt_("Opened project %s") % project.name)
        return {'FINISHED'}


class DASKTOON_OT_project_open_model(Operator):
    """Open this .blend file of the project (DaskToon asks to save the current file first when it has changes)"""
    bl_idname = "dasktoon.project_open_model"
    bl_label = "Open"

    filepath: StringProperty(subtype='FILE_PATH', options={'HIDDEN'})

    def execute(self, _context):
        bpy.ops.wm.open_mainfile('INVOKE_DEFAULT', filepath=self.filepath, display_file_selector=False)
        return {'FINISHED'}


class DASKTOON_OT_project_export(Operator):
    """Export this file's model, materials and shaders straight into the project's Unity project"""
    bl_idname = "dasktoon.project_export"
    bl_label = "Export This Model"

    def execute(self, context):
        import dasktoon_export
        from dasktoon_export import model_fbx, report
        project = _require_project(self)
        if project is None:
            return {'CANCELLED'}
        objects = model_fbx.export_objects(context, selected_only=False)
        if not objects:
            self.report({'ERROR'}, rpt_("This file has no object to export"))
            return {'CANCELLED'}
        target = dtp.project_target(project, targets.blend_name(bpy.data.filepath))
        rep = dasktoon_export.export_model(context, target, objects, dasktoon_export.ExportOptions())
        report.show_popup(rep)
        self.report({'WARNING'} if rep.warnings else {'INFO'}, rep.summary())
        return {'FINISHED'}


class DASKTOON_OT_project_reinstall_shaders(Operator):
    """Write the DaskToon shaders into the project's Unity project again"""
    bl_idname = "dasktoon.project_reinstall_shaders"
    bl_label = "Reinstall Shaders"

    def execute(self, _context):
        project = _require_project(self)
        if project is None:
            return {'CANCELLED'}
        _written, warnings = dtp.install_project_shaders(project, force=True)
        for warning in warnings:
            self.report({'WARNING'}, warning)
        self.report({'INFO'}, rpt_("Reinstalled the shaders into %s") % project.engine_path)
        return {'FINISHED'}


class DASKTOON_OT_project_open_folder(Operator):
    """Open the project folder in the file manager"""
    bl_idname = "dasktoon.project_open_folder"
    bl_label = "Open Project Folder"

    def execute(self, _context):
        project = _require_project(self)
        if project is None:
            return {'CANCELLED'}
        bpy.ops.wm.path_open(filepath=project.folder)
        return {'FINISHED'}


class TOPBAR_MT_dasktoon_project_recent(Menu):
    bl_idname = "TOPBAR_MT_dasktoon_project_recent"
    bl_label = "Open Recent"

    def draw(self, _context):
        layout = self.layout
        recent = dtp.recent_projects()
        if not recent:
            layout.label(text="No recent projects")
        for path in recent:
            op = layout.operator(DASKTOON_OT_project_open.bl_idname, text=os.path.basename(os.path.dirname(path)),
                                 icon='FILE_FOLDER', translate=False)
            op.filepath = path


class TOPBAR_MT_dasktoon_project_models(Menu):
    bl_idname = "TOPBAR_MT_dasktoon_project_models"
    bl_label = "Models"

    def draw(self, _context):
        layout = self.layout
        project = active_project()
        if project is None:
            return
        current = os.path.normcase(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else ""
        for path in _models(project):
            icon = 'RADIOBUT_ON' if os.path.normcase(path) == current else 'BLENDER'
            op = layout.operator(DASKTOON_OT_project_open_model.bl_idname, text=os.path.relpath(path, project.folder),
                                 icon=icon, translate=False)
            op.filepath = path


class TOPBAR_MT_dasktoon_project(Menu):
    bl_idname = "TOPBAR_MT_dasktoon_project"
    bl_label = "DaskToon Project"

    def draw(self, _context):
        from dasktoon_export import shaders_install
        layout = self.layout
        layout.operator(DASKTOON_OT_project_create.bl_idname, text="New Project…", icon='NEWFOLDER')
        layout.operator(DASKTOON_OT_project_open.bl_idname, text="Open Project…", icon='FILE_FOLDER')
        layout.menu(TOPBAR_MT_dasktoon_project_recent.bl_idname, icon='RECOVER_LAST')
        project = active_project()
        if project is None:
            return
        layout.separator()
        layout.label(text=project.name, icon='FILE_FOLDER', translate=False)
        engines = {key: label for key, label, _desc in targets.ENGINES}
        layout.label(text="%s: %s" % (iface_("Engine"), iface_(engines.get(project.engine, project.engine))),
                     translate=False)
        version = shaders_install.installed_version(os.path.join(project.engine_path, "Assets", "DaskToon"))
        layout.label(text=(iface_("Shaders: version %d") % version) if version else iface_("Shaders: not installed"),
                     icon='CHECKMARK' if version else 'ERROR', translate=False)
        layout.menu(TOPBAR_MT_dasktoon_project_models.bl_idname, icon='BLENDER')
        layout.operator(DASKTOON_OT_project_export.bl_idname, icon='EXPORT')
        layout.operator(DASKTOON_OT_project_reinstall_shaders.bl_idname, icon='FILE_REFRESH')
        layout.operator(DASKTOON_OT_project_open_folder.bl_idname, icon='FILEBROWSER')


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
    TOPBAR_MT_dasktoon_project_recent,
    TOPBAR_MT_dasktoon_project_models,
    TOPBAR_MT_dasktoon_project,
)


# bl_ui registers `classes` itself; register()/unregister() only manage the File menu entry. bl_ui registers this module
# before space_topbar, so the menu is reached through its Python class rather than bpy.types.
def register():
    from .space_topbar import TOPBAR_MT_file
    TOPBAR_MT_file.append(menu_func_file)


def unregister():
    from .space_topbar import TOPBAR_MT_file
    TOPBAR_MT_file.remove(menu_func_file)
