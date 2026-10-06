# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon projects in the interface (docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, sections
3, 6, 7 and 11): the selected project, New Project, Open Project, Project Settings, Export This Model, Reinstall Shaders,
Open Project Folder, the Open Recent, Models and Project menus of File, and the top bar label."""

import os
import time

import bpy
from bpy.app.translations import pgettext_iface as iface_, pgettext_rpt as rpt_
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Menu, Operator

from dasktoon_export import targets
from dasktoon_project import project as dtp

_session = {"project_file": ""}  # the project chosen this session: start screen, Open Project, New Project
_models_cache = {"key": None, "time": 0.0, "models": []}
MODELS_REFRESH = 2.0  # seconds; menus redraw often and must not walk the folder every time
THEN = (('NONE', "", ""), ('EXPORT', "", ""), ('REINSTALL', "", ""))  # what Project Settings runs once Unity is linked


def forget_session_project():
    _session["project_file"] = ""
    _models_cache["key"] = None


def load_project(path):
    """The project at `path` (its file or its folder), or None when it is gone or unreadable."""
    try:
        return dtp.load(path)
    except (OSError, ValueError):
        return None


def select_project(project):
    """`project` becomes the selected project of this session and the most recent one."""
    _session["project_file"] = project.file
    dtp.add_recent(project.file)


def open_project():
    """The project that holds the open .blend file; None for a draft (spec 3)."""
    return dtp.find_project(bpy.data.filepath)


def is_draft():
    return open_project() is None


def selected_project():
    """The open project; for a draft, the project chosen last this session, else the most recent one (spec 3)."""
    project = open_project()
    if project is not None:
        return project
    for path in [_session["project_file"]] + dtp.recent_projects():
        project = load_project(path) if path else None
        if project is not None:
            return project
    return None


def models(project):
    """dtp.project_models(project), cached for MODELS_REFRESH seconds."""
    now = time.monotonic()
    if _models_cache["key"] != project.folder or now - _models_cache["time"] > MODELS_REFRESH:
        _models_cache.update(key=project.folder, time=now, models=dtp.project_models(project))
    return _models_cache["models"]


def forget_models():
    _models_cache["key"] = None


def engine_label(project):
    """"Engine: Unity 6 (URP)", or "Engine: not linked" until a Unity project is linked (spec 11)."""
    if not project.engines:
        return iface_("Engine: not linked")
    names = {key: label for key, label, _desc in targets.ENGINES}
    return iface_("Engine: %s") % iface_(names.get(project.engine, project.engine))


def interactive():
    """True when a person can answer dialogs. A background run has a window in its context too, but there Blender runs
    execute instead of invoke, so DaskToon must not open a dialog and wait for an answer."""
    return not bpy.app.background and bpy.context.window is not None


def call_mode():
    """How DaskToon calls Blender's file operators: invoked when a person can answer Blender's dialogs (save changes,
    modified images), executed otherwise (background, scripts)."""
    return 'INVOKE_DEFAULT' if interactive() else 'EXEC_DEFAULT'


def open_blend(path):
    """Open `path` as Blender does from a menu, asking to save changes first: a model when it lies in a project, a draft
    otherwise (spec 9). use_project_redirect=False: the core must not hand this back to DaskToon."""
    bpy.ops.wm.open_mainfile(call_mode(), filepath=path, display_file_selector=False, use_project_redirect=False)


def show_start_screen():
    if interactive():
        bpy.ops.wm.splash('INVOKE_DEFAULT')


def draw_topbar_label(layout):
    """Top bar, before the scene selector (spec 7): "Hero › Hero_Armor" for a model of a project, a warning for a
    draft."""
    project = open_project()
    if project is None:
        layout.label(text="Draft (not in a project)", icon='ERROR')
        return
    model = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
    layout.label(text="%s › %s" % (project.name, model), icon='FILE_FOLDER', translate=False)


def _choose(op, project):
    select_project(project)
    forget_models()
    op.report({'INFO'}, rpt_("Opened project %s") % project.name)
    show_start_screen()
    return {'FINISHED'}


def _linked_project(op, then):
    """The selected project when a Unity project is linked to it. Otherwise Project Settings opens to link one, and runs
    `then` afterwards (spec 11); returns None."""
    project = selected_project()
    if project is None:
        op.report({'ERROR'}, rpt_("No DaskToon project is open"))
        return None
    if not project.engines:
        if interactive():
            bpy.ops.dasktoon.project_settings('INVOKE_DEFAULT', then=then)
        else:
            op.report({'ERROR'}, rpt_("Project %s is not linked to a Unity project yet: link it in Project Settings")
                      % project.name)
        return None
    return project


class DASKTOON_OT_project_create(Operator):
    """Create a DaskToon project: a folder with Models/ and Textures/; link a Unity project now or later"""
    bl_idname = "dasktoon.project_create"
    bl_label = "New Project"

    name: StringProperty(name="Name", default="New Project")
    location: StringProperty(name="Location", subtype='DIR_PATH',
                             description="The folder that receives the project folder")
    engine_path: StringProperty(name="Unity Project", subtype='DIR_PATH',
                                description="Optional: the Unity project models are exported to (link it later in "
                                            "Project Settings)")
    model_start_from: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})  # passed on to New Model

    def invoke(self, context, _event):
        if not self.location:
            self.location = dtp.project_location()
        return context.window_manager.invoke_props_dialog(self, width=520)

    def execute(self, _context):
        location = bpy.path.abspath(self.location) if self.location else dtp.project_location()
        engine_path = bpy.path.abspath(self.engine_path) if self.engine_path else ""
        try:
            name = dtp.clean_name(self.name)
            project = dtp.create_project(name, os.path.join(location, name), engine_path)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        dtp.set_project_location(location)
        select_project(project)
        forget_models()
        self.report({'INFO'}, rpt_("Created project %s") % project.name)
        if interactive():
            options = {"name": dtp.free_model_name(project, project.name)}
            if self.model_start_from:
                options["start_from"] = self.model_start_from
            bpy.ops.dasktoon.model_new('INVOKE_DEFAULT', **options)
        return {'FINISHED'}


class DASKTOON_OT_project_open(Operator):
    """Open a DaskToon project (its dasktoon_project.json or its folder) and show its models on the start screen"""
    bl_idname = "dasktoon.project_open"
    bl_label = "Open Project"

    filepath: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})
    filter_glob: StringProperty(default=dtp.PROJECT_FILE, options={'HIDDEN'})
    filter_folder: BoolProperty(default=True, options={'HIDDEN'})

    def invoke(self, context, _event):
        if self.filepath and os.path.exists(self.filepath):
            return self.execute(context)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, _context):
        try:
            project = dtp.load(self.filepath)
        except ValueError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        except OSError:
            self.report({'ERROR'}, rpt_("%s is not a DaskToon project") % self.filepath)
            return {'CANCELLED'}
        return _choose(self, project)


class DASKTOON_OT_project_select(Operator):
    """Choose this project: the start screen shows its models"""
    bl_idname = "dasktoon.project_select"
    bl_label = "Choose Project"
    bl_options = {'INTERNAL'}

    filepath: StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, _context):
        project = load_project(self.filepath)
        if project is None:
            self.report({'ERROR'}, rpt_("%s is not a DaskToon project") % self.filepath)
            return {'CANCELLED'}
        return _choose(self, project)


class DASKTOON_OT_project_settings(Operator):
    """Rename the project and link it to a Unity project; the DaskToon shaders are installed when the link is new or changes"""
    bl_idname = "dasktoon.project_settings"
    bl_label = "Project Settings"

    name: StringProperty(name="Name")
    engine: EnumProperty(name="Engine", items=targets.ENGINES, default='UNITY_URP')
    engine_path: StringProperty(name="Unity Project", subtype='DIR_PATH',
                                description="The Unity project models are exported to; leave empty to unlink")
    then: EnumProperty(items=THEN, options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def poll(cls, _context):
        return selected_project() is not None

    def invoke(self, context, _event):
        project = selected_project()
        self.name = project.name
        if project.engines:
            if project.engine in {key for key, _label, _desc in targets.ENGINES}:
                self.engine = project.engine
            self.engine_path = project.engine_path
        return context.window_manager.invoke_props_dialog(self, width=520)

    def execute(self, _context):
        project = selected_project()
        try:
            project.name = dtp.clean_name(self.name)
            path = bpy.path.abspath(self.engine_path) if self.engine_path else ""
            warnings = dtp.link_engine(project, self.engine, path)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        for warning in warnings:
            self.report({'WARNING'}, warning)
        self.report({'INFO'}, rpt_("Saved the settings of project %s") % project.name)
        try:
            if project.engines and self.then == 'EXPORT':
                return bpy.ops.dasktoon.project_export()
            if project.engines and self.then == 'REINSTALL':
                return bpy.ops.dasktoon.project_reinstall_shaders()
        except RuntimeError:
            return {'CANCELLED'}  # the command reported why
        return {'FINISHED'}


class DASKTOON_OT_project_open_model(Operator):
    """Open this model of the project (DaskToon asks to save the current file first when it has changes)"""
    bl_idname = "dasktoon.project_open_model"
    bl_label = "Open"

    filepath: StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, _context):
        if not os.path.isfile(self.filepath):
            self.report({'ERROR'}, rpt_("File not found: %s") % self.filepath)
            return {'CANCELLED'}
        open_blend(self.filepath)
        return {'FINISHED'}


class DASKTOON_OT_project_export(Operator):
    """Export this file's model, materials and shaders straight into the project's Unity project"""
    bl_idname = "dasktoon.project_export"
    bl_label = "Export This Model"

    def execute(self, context):
        import dasktoon_export
        from dasktoon_export import model_fbx, report
        project = _linked_project(self, 'EXPORT')
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
        project = _linked_project(self, 'REINSTALL')
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
        project = selected_project()
        if project is None:
            self.report({'ERROR'}, rpt_("No DaskToon project is open"))
            return {'CANCELLED'}
        bpy.ops.wm.path_open(filepath=project.folder)
        return {'FINISHED'}


class TOPBAR_MT_file_open_recent(Menu):
    # Replaces Blender's list of recent files (project workflow spec 7): recent models first, then recent projects.
    bl_idname = "TOPBAR_MT_file_open_recent"
    bl_label = "Open Recent"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = 'EXEC_DEFAULT'
        recent_models, recent_projects = dtp.recent_models(), dtp.recent_projects()
        if not recent_models and not recent_projects:
            layout.label(text="No recent models or projects")
            return
        if recent_models:
            layout.label(text="Models")
            for path in recent_models:
                project = dtp.find_project(path)
                text = "%s › %s" % (project.name, dtp.model_label(project, path)) if project else os.path.basename(path)
                layout.operator(DASKTOON_OT_project_open_model.bl_idname, text=text, icon='FILE_BLEND',
                                translate=False).filepath = path
        if recent_projects:
            if recent_models:
                layout.separator()
            layout.label(text="Projects")
            for path in recent_projects:
                layout.operator(DASKTOON_OT_project_open.bl_idname, text=os.path.basename(os.path.dirname(path)),
                                icon='FILE_FOLDER', translate=False).filepath = path


class TOPBAR_MT_dasktoon_project_models(Menu):
    bl_idname = "TOPBAR_MT_dasktoon_project_models"
    bl_label = "Models"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = 'EXEC_DEFAULT'
        project = selected_project()
        if project is None:
            layout.label(text="Create or open a project")
            return
        found = models(project)
        if not found:
            layout.label(text="No models yet")
        for path in found:
            current = bool(bpy.data.filepath) and dtp.same_path(path, bpy.data.filepath)
            layout.operator(DASKTOON_OT_project_open_model.bl_idname, text=dtp.model_label(project, path),
                            icon='RADIOBUT_ON' if current else 'FILE_BLEND', translate=False).filepath = path


class TOPBAR_MT_dasktoon_project(Menu):
    bl_idname = "TOPBAR_MT_dasktoon_project"
    bl_label = "Project"
    # Blender's Vietnamese for "Project" in the default context means "projection".
    bl_translation_context = "DaskToon"

    def draw(self, _context):
        from dasktoon_export import shaders_install
        layout = self.layout
        project = selected_project()
        if project is None:
            layout.label(text="Create or open a project")
            return
        layout.label(text=project.name, icon='FILE_FOLDER', translate=False)
        layout.label(text=engine_label(project), translate=False)
        if project.engines:
            version = shaders_install.installed_version(os.path.join(project.engine_path, "Assets", "DaskToon"))
            layout.label(text=(iface_("Shaders: version %d") % version) if version else iface_("Shaders: not installed"),
                         icon='CHECKMARK' if version else 'ERROR', translate=False)
        layout.separator()
        layout.operator(DASKTOON_OT_project_settings.bl_idname, text="Project Settings…", icon='PREFERENCES')
        layout.operator(DASKTOON_OT_project_export.bl_idname, icon='EXPORT')
        layout.operator(DASKTOON_OT_project_reinstall_shaders.bl_idname, icon='FILE_REFRESH')
        layout.operator(DASKTOON_OT_project_open_folder.bl_idname, icon='FILEBROWSER')


classes = (
    DASKTOON_OT_project_create,
    DASKTOON_OT_project_open,
    DASKTOON_OT_project_select,
    DASKTOON_OT_project_settings,
    DASKTOON_OT_project_open_model,
    DASKTOON_OT_project_export,
    DASKTOON_OT_project_reinstall_shaders,
    DASKTOON_OT_project_open_folder,
    TOPBAR_MT_file_open_recent,
    TOPBAR_MT_dasktoon_project_models,
    TOPBAR_MT_dasktoon_project,
)
