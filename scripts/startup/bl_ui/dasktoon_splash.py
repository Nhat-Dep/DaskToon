# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The DaskToon start screen (docs/superpowers/specs/2026-10-05-dasktoon-project-workflow-design.md, section 5):
projects on the left, the selected project's models on the right, Recover Last Session and Continue as Draft below.
WM_MT_splash (bl_operators/wm.py) draws it under the splash image; DaskToon › Splash Screen shows it again."""

import os

from bpy.app.translations import pgettext_iface as iface_
from bpy.types import Operator

from dasktoon_project import project as dtp
from . import dasktoon_project as projects

MAX_MODELS = 12  # a taller start screen would not fit small screens; File › Models lists them all


def draw_splash(layout, _context):
    layout.operator_context = 'EXEC_DEFAULT'
    layout.emboss = 'PULLDOWN_MENU'
    selected = projects.selected_project()

    split = layout.split()
    left = split.column()
    left.label(text="Projects")
    sub = left.column()
    sub.operator_context = 'INVOKE_DEFAULT'
    sub.operator("dasktoon.project_create", text="New Project…", icon='NEWFOLDER')
    sub.operator("dasktoon.project_open", text="Open Project…", icon='FILE_FOLDER')
    left.separator()
    left.label(text="Recent")
    recent = dtp.recent_projects()
    if not recent:
        left.label(text="No recent projects")
    for path in recent:
        chosen = selected is not None and dtp.same_path(path, selected.file)
        left.operator("dasktoon.project_select", text=os.path.basename(os.path.dirname(path)),
                      icon='RADIOBUT_ON' if chosen else 'RADIOBUT_OFF', translate=False).filepath = path

    right = split.column()
    if selected is None:
        right.label(text="Create or open a project")
        sub = right.column()
        sub.enabled = False
        sub.operator("dasktoon.model_new", text="New Model…", icon='FILE_NEW')
    else:
        right.label(text=selected.name, icon='FILE_FOLDER', translate=False)
        right.label(text=projects.engine_label(selected), translate=False)
        sub = right.column()
        sub.operator_context = 'INVOKE_DEFAULT'
        sub.operator("dasktoon.model_new", text="New Model…", icon='FILE_NEW')
        found = projects.models(selected)
        for path in found[:MAX_MODELS]:
            right.operator("dasktoon.project_open_model", text=dtp.model_label(selected, path), icon='FILE_BLEND',
                           translate=False).filepath = path
        if len(found) > MAX_MODELS:
            right.label(text=iface_("%d more in File › Models") % (len(found) - MAX_MODELS), translate=False)

    col = layout.column()
    col.separator()
    col.separator(type='LINE')
    col.separator()

    split = layout.split()
    split.column().operator("wm.recover_last_session", icon='RECOVER_LAST')
    split.column().operator(DASKTOON_OT_continue_as_draft.bl_idname, icon='FILE_BLEND')
    layout.separator()


class DASKTOON_OT_continue_as_draft(Operator):
    """Close the start screen and keep working on the open scene as a draft, outside any project"""
    bl_idname = "dasktoon.continue_as_draft"
    bl_label = "Continue as Draft"

    def execute(self, _context):
        return {'FINISHED'}  # the start screen closes when one of its items is used


classes = (DASKTOON_OT_continue_as_draft,)
