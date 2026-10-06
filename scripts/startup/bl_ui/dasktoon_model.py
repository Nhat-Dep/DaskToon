# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Models and drafts (docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, sections 6, 8, 9, 10 and
12). A person's New, Open and Save reach these commands from DaskToon's menus, or from Blender's operators, which the
core hands over when they are invoked (source/blender/windowmanager/intern/wm_files.cc, "use_project_redirect")."""

import os

import bpy
from bpy.app.translations import pgettext_iface as iface_, pgettext_n as n_, pgettext_rpt as rpt_
from bpy.props import EnumProperty, StringProperty
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


classes = (
    DASKTOON_OT_model_new,
    DASKTOON_OT_model_new_finish,
)
