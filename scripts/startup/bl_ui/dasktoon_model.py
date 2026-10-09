# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Models and drafts (docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, sections 6, 8, 9, 10 and
12). A person's New, Open and Save reach these commands from DaskToon's menus, or from Blender's operators, which the
core hands over when they are invoked (source/blender/windowmanager/intern/wm_files.cc, "use_project_redirect")."""

import os

import bpy
from bpy.app.handlers import persistent
from bpy.app.translations import pgettext_iface as iface_, pgettext_n as n_, pgettext_rpt as rpt_
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator

from dasktoon_project import project as dtp, scene as dts, textures as dtt
from . import dasktoon_project as projects

START_FROM = (
    ('DASKTOON', n_("DaskToon Scene"),
     n_("An empty scene with a Sun, a camera looking at the origin, the DaskToon Anime engine and the Standard view")),
    ('EMPTY', n_("Empty Scene"), n_("A completely empty scene")),
    ('CURRENT', n_("Current Scene"), n_("Save the scene that is open now as the new model")),
    ('COPY', n_("Copy of Model"), n_("Start from a copy of another model of the project")),
)
_pending = {}  # the New Model waiting for the file read it asked for (DASKTOON_OT_model_new_finish)
_enum_items = {"models": [], "projects": []}  # Blender needs the strings of dynamic enum items kept alive


def keeps_current(draft, filepath, dirty):
    """True when New Model should start from the current scene: a draft that is a file from outside any project, or
    that has unsaved changes. The untouched scene DaskToon opens with starts from the DaskToon Scene instead (spec 6)."""
    return draft and (bool(filepath) or dirty)


def report_textures(op, collected):
    """The status bar line about copied textures; reported last so the status bar shows it (spec 10)."""
    if collected.summary():
        op.report({'INFO'}, collected.summary())


def save_into(op, project, path, copy=False):
    """Copy outside textures into `project` (spec 10) and write the open scene to `path`, a new file of the project,
    with exec so no Blender dialog shows: images with unsaved paint changes are named in warnings instead (spec 12).
    Without `copy`, `path` becomes the open file. Returns the textures report, or None when nothing was written."""
    collected = dtt.collect(project)
    for warning in collected.warnings:
        op.report({'WARNING'}, warning)
    for name in dtt.unsaved_images():
        op.report({'WARNING'}, rpt_("Image %s has unsaved paint changes: save it with Image › Save") % name)
    try:
        bpy.ops.wm.save_as_mainfile(filepath=path, copy=copy, relative_remap=True)
        if not copy and dtt.relink_absolute(collected.images):
            bpy.ops.wm.save_mainfile()
    except RuntimeError as ex:
        op.report({'ERROR'}, str(ex))
        return None
    projects.forget_models()
    return collected


def save_here(op, mode, filepath=""):
    """Save the open model where it is, or as `filepath` next to it (Save Incremental), after copying outside textures
    into its project. Invoked, Blender's own dialogs (modified images, a file from a newer version) still show."""
    collected = dtt.collect(projects.open_project())
    for warning in collected.warnings:
        op.report({'WARNING'}, warning)
    options = {"use_project_redirect": False}
    if filepath:
        options["filepath"] = filepath
    if mode == 'INVOKE_DEFAULT':
        options["show_save_modified_images_dialog"] = op.show_save_modified_images_dialog
    try:
        bpy.ops.wm.save_mainfile(mode, **options)
    except RuntimeError as ex:
        op.report({'ERROR'}, str(ex))
        return {'CANCELLED'}
    projects.forget_models()
    report_textures(op, collected)
    return {'FINISHED'}


def _save_draft():
    """Save and Save Model As on a draft open Save to Project (spec 9). Nothing is saved yet, so this is cancelled:
    the "save changes?" dialog stops what it was doing, as Blender does for a file never saved."""
    if projects.interactive():
        bpy.ops.dasktoon.save_to_project('INVOKE_DEFAULT')
    return {'CANCELLED'}


def _project_items(_self, _context):
    """The selected project, then the recent ones (Save to Project, spec 6)."""
    items = _enum_items["projects"]
    items.clear()
    selected = projects.selected_project()
    seen = set()
    for path in ([selected.file] if selected else []) + dtp.recent_projects():
        key = os.path.normcase(os.path.abspath(path))
        project = projects.load_project(path) if key not in seen else None
        seen.add(key)
        if project is not None:
            items.append((path, project.name, path))
    return items


def _current_name():
    return os.path.splitext(os.path.basename(bpy.data.filepath))[0] if bpy.data.filepath else "Untitled"


def _model_items(_self, _context):
    items = _enum_items["models"]
    items.clear()
    project = projects.selected_project()
    if project is not None:
        for path in projects.models(project):
            items.append((os.path.relpath(path, project.folder).replace(os.sep, "/"), dtp.model_label(project, path), ""))
    if not items:
        items.append(('NONE', iface_("No models yet"), ""))
    return items


class DASKTOON_OT_model_new(Operator):
    """Create a model in the selected project: Models/<name>.blend, saved at once and opened"""
    bl_idname = "dasktoon.model_new"
    bl_label = "New Model"

    name: StringProperty(name="Name", default="Untitled")
    start_from: EnumProperty(name="Start From", items=START_FROM, default='DASKTOON')
    copy_from: EnumProperty(name="Model", items=_model_items)

    def invoke(self, context, _event):
        project = projects.selected_project()
        if project is None:
            bpy.ops.dasktoon.project_create('INVOKE_DEFAULT')
            return {'CANCELLED'}
        if not self.properties.is_property_set("name"):
            self.name = dtp.free_model_name(project, project.name)
        if not self.properties.is_property_set("start_from"):
            keep = keeps_current(projects.is_draft(), bpy.data.filepath, bpy.data.is_dirty)
            self.start_from = 'CURRENT' if keep else 'DASKTOON'
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, _context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "name")
        layout.prop(self, "start_from")
        if self.start_from == 'COPY':
            layout.prop(self, "copy_from")

    def execute(self, _context):
        project = projects.selected_project()
        if project is None:
            self.report({'ERROR'}, rpt_("Create or open a project first"))
            return {'CANCELLED'}
        source = ""
        if self.start_from == 'COPY':
            source = os.path.join(project.folder, *self.copy_from.split("/"))
            if self.copy_from == 'NONE' or not os.path.isfile(source):
                self.report({'ERROR'}, rpt_("Choose the model to copy"))
                return {'CANCELLED'}
        try:
            path = dtp.new_model_path(project, self.name)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        projects.select_project(project)
        if self.start_from == 'CURRENT':
            collected = save_into(self, project, path)
            if collected is None:
                return {'CANCELLED'}
            self.report({'INFO'}, rpt_("Created model %s") % dtp.model_label(project, path))
            report_textures(self, collected)
            return {'FINISHED'}
        # The other starts leave the open file: Blender's own operator asks to save changes first (invoked), then reads
        # the file, then runs the finishing command from the core (post_read_operator). Cancelling never finishes.
        _pending.clear()
        _pending.update(project=project.file, path=path, start_from=self.start_from)
        finish = DASKTOON_OT_model_new_finish.bl_idname
        if source:
            bpy.ops.wm.open_mainfile(projects.call_mode(), filepath=source, display_file_selector=False,
                                     use_project_redirect=False, post_read_operator=finish)
        else:
            bpy.ops.wm.read_homefile(projects.call_mode(), use_empty=True, use_project_redirect=False,
                                     post_read_operator=finish)
        return {'FINISHED'}


class DASKTOON_OT_model_new_finish(Operator):
    """Finish New Model once the startup file or the model to copy has been read"""
    bl_idname = "dasktoon.model_new_finish"
    bl_label = "Finish New Model"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        request = dict(_pending)
        _pending.clear()
        project = projects.load_project(request["project"]) if request else None
        if project is None:
            return {'CANCELLED'}
        if os.path.exists(request["path"]):
            self.report({'ERROR'}, rpt_("The project already has a model named %s")
                        % dtp.model_label(project, request["path"]))
            return {'CANCELLED'}
        if request["start_from"] == 'DASKTOON':
            dts.build(context.scene)
        collected = save_into(self, project, request["path"])
        if collected is None:
            return {'CANCELLED'}
        projects.select_project(project)
        self.report({'INFO'}, rpt_("Created model %s") % dtp.model_label(project, request["path"]))
        report_textures(self, collected)
        return {'FINISHED'}


class DASKTOON_OT_open(Operator):
    """Open a model, a .blend file from outside any project (as a draft), or a project"""
    bl_idname = "dasktoon.open"
    bl_label = "Open"

    filepath: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})
    filter_blender: BoolProperty(default=True, options={'HIDDEN'})
    filter_folder: BoolProperty(default=True, options={'HIDDEN'})
    filter_glob: StringProperty(default="*.blend;" + dtp.PROJECT_FILE, options={'HIDDEN'})

    def invoke(self, context, _event):
        if not self.filepath:
            project = projects.selected_project()
            if project is not None:
                folder = project.models_folder if os.path.isdir(project.models_folder) else project.folder
                self.filepath = os.path.join(folder, "")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, _context):
        path = bpy.path.abspath(self.filepath)
        if os.path.isdir(path) or os.path.basename(path).lower() == dtp.PROJECT_FILE:
            try:
                return bpy.ops.dasktoon.project_open(filepath=path)
            except RuntimeError:
                return {'CANCELLED'}  # Open Project reported why
        if not os.path.isfile(path):
            self.report({'ERROR'}, rpt_("File not found: %s") % path)
            return {'CANCELLED'}
        projects.open_blend(path)
        return {'FINISHED'}


class DASKTOON_OT_project_save(Operator):
    """Save this model in its project, copying textures from outside into Textures/ first; a draft is saved into a project"""
    bl_idname = "dasktoon.project_save"
    bl_label = "Save"

    show_save_modified_images_dialog: BoolProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def invoke(self, _context, _event):
        if projects.open_project() is None:
            return _save_draft()
        return save_here(self, projects.call_mode())

    def execute(self, _context):
        if projects.open_project() is None:
            return _save_draft()
        return save_here(self, 'EXEC_DEFAULT')


class DASKTOON_OT_save_to_project(Operator):
    """Save this draft as a new model of a project; the file it came from is not changed"""
    bl_idname = "dasktoon.save_to_project"
    bl_label = "Save to Project"

    project: EnumProperty(name="Project", items=_project_items, translation_context="DaskToon")
    name: StringProperty(name="Name", default="Untitled")

    def invoke(self, context, _event):
        items = _project_items(self, context)
        if not items:
            bpy.ops.dasktoon.project_create('INVOKE_DEFAULT', model_start_from='CURRENT')
            return {'CANCELLED'}
        self.project = items[0][0]
        self.name = dtp.free_model_name(projects.load_project(self.project), _current_name())
        return context.window_manager.invoke_props_dialog(self, width=420)

    def execute(self, _context):
        project = projects.load_project(self.project) if self.project else None
        if project is None:
            self.report({'ERROR'}, rpt_("Choose a project"))
            return {'CANCELLED'}
        try:
            path = dtp.new_model_path(project, self.name)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        collected = save_into(self, project, path)
        if collected is None:
            return {'CANCELLED'}
        projects.select_project(project)
        self.report({'INFO'}, rpt_("Saved model %s in project %s") % (dtp.model_label(project, path), project.name))
        report_textures(self, collected)
        return {'FINISHED'}


class DASKTOON_OT_model_save_as(Operator):
    """Save this model under a new name in its project's Models/ folder and keep working on the new file"""
    bl_idname = "dasktoon.model_save_as"
    bl_label = "Save Model As"

    name: StringProperty(name="Name")

    def invoke(self, context, _event):
        project = projects.open_project()
        if project is None:
            return _save_draft()
        self.name = dtp.free_model_name(project, _current_name())
        return context.window_manager.invoke_props_dialog(self, width=420)

    def execute(self, _context):
        project = projects.open_project()
        if project is None:
            return _save_draft()
        try:
            path = dtp.new_model_path(project, self.name)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        collected = save_into(self, project, path)
        if collected is None:
            return {'CANCELLED'}
        self.report({'INFO'}, rpt_("Saved as model %s") % dtp.model_label(project, path))
        report_textures(self, collected)
        return {'FINISHED'}


class DASKTOON_OT_model_save_copy(Operator):
    """Write a copy of this model into its project's Models/ folder and keep working on this file"""
    bl_idname = "dasktoon.model_save_copy"
    bl_label = "Save Copy"

    name: StringProperty(name="Name")

    @classmethod
    def poll(cls, _context):
        return projects.open_project() is not None

    def invoke(self, context, _event):
        self.name = dtp.free_model_name(projects.open_project(), _current_name())
        return context.window_manager.invoke_props_dialog(self, width=420)

    def execute(self, _context):
        project = projects.open_project()
        try:
            path = dtp.new_model_path(project, self.name)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        collected = save_into(self, project, path, copy=True)
        if collected is None:
            return {'CANCELLED'}
        self.report({'INFO'}, rpt_("Saved a copy as model %s") % dtp.model_label(project, path))
        report_textures(self, collected)
        return {'FINISHED'}


class DASKTOON_OT_model_save_incremental(Operator):
    """Save this model as the next numbered file next to it (Hero.blend gives Hero_001.blend) and keep working on that one"""
    bl_idname = "dasktoon.model_save_incremental"
    bl_label = "Save Incremental"

    show_save_modified_images_dialog: BoolProperty(options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def poll(cls, _context):
        return projects.open_project() is not None

    def invoke(self, _context, _event):
        return save_here(self, projects.call_mode(), dtp.incremental_path(bpy.data.filepath))

    def execute(self, _context):
        return save_here(self, 'EXEC_DEFAULT', dtp.incremental_path(bpy.data.filepath))


def remember(filepath):
    """A model of a project goes to the top of the recent models, its project to the top of the recent projects
    (spec 4). A draft is not remembered."""
    project = dtp.find_project(filepath) if filepath else None
    if project is not None:
        dtp.add_recent_model(filepath)
        dtp.add_recent(project.file)


@persistent
def remember_on_file_change(filepath):
    """load_post and save_post. Background runs (scripts, tests) are not a person's work and are not remembered."""
    if not bpy.app.background:
        remember(filepath)


classes = (
    DASKTOON_OT_model_new,
    DASKTOON_OT_model_new_finish,
    DASKTOON_OT_open,
    DASKTOON_OT_project_save,
    DASKTOON_OT_save_to_project,
    DASKTOON_OT_model_save_as,
    DASKTOON_OT_model_save_copy,
    DASKTOON_OT_model_save_incremental,
)


# bl_ui registers `classes`; register()/unregister() manage the recent-models handler.
def register():
    for handlers in (bpy.app.handlers.load_post, bpy.app.handlers.save_post):
        if remember_on_file_change not in handlers:
            handlers.append(remember_on_file_change)


def unregister():
    for handlers in (bpy.app.handlers.load_post, bpy.app.handlers.save_post):
        if remember_on_file_change in handlers:
            handlers.remove(remember_on_file_change)
