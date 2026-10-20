# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Guide tab of the 3D Viewport's sidebar (docs/superpowers/specs/2026-10-20-dasktoon-model-guide-design.md): the
Model Check (the checks of dasktoon_guide.checks, their fixes and pages) and the Steps from a new model to Unity. The
one DaskToon tab of the viewport sidebar, by the user's choice of 2026-10-20 (the sidebar stays in view while
modelling). The results live in the window, not in the file."""

import os

import bpy
from bpy.app.translations import pgettext_iface as iface_, pgettext_n as n_, pgettext_rpt as rpt_
from bpy.props import BoolProperty, CollectionProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup

CATEGORY = "Guide"
STATUS_ICONS = {'OK': 'CHECKMARK', 'WARN': 'ERROR', 'ERROR': 'CANCEL', 'LATER': 'TIME'}
GROUPS = (('STANDING', n_("Standing")), ('MESH', n_("Mesh")), ('MATERIALS', n_("Materials")),
          ('RIG', n_("After the Rig")))
PAGES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "modules",
                     "dasktoon_guide", "pages")


class DaskGuideResult(PropertyGroup):
    """One result of the Model Check"""
    check: StringProperty(name="Check")
    group: StringProperty(name="Group")
    step: StringProperty(name="Step")
    status: StringProperty(name="Status")
    text: StringProperty(name="Text")
    fixable: BoolProperty(name="Fixable")


def page_url(step_id, anchor="", language=None):
    """file:// URL of a step's page in the interface's language (English when it has none), at `anchor`."""
    if language is None:
        language = "vi" if bpy.app.translations.locale.startswith("vi") else "en"
    path = os.path.join(PAGES, language, step_id.lower() + ".html")
    if not os.path.exists(path):
        path = os.path.join(PAGES, "en", step_id.lower() + ".html")
    return "file:///" + path.replace("\\", "/") + ("#" + anchor if anchor else "")


def fill(context):
    """Run the Model Check on the selection's character into the window's list; returns the results."""
    from dasktoon_guide import checks
    found = checks.run(context)
    results = context.window_manager.dasktoon_guide_results
    results.clear()
    for result in found:
        item = results.add()
        item.check, item.group, item.step = result.id, result.group, result.step
        item.status, item.text, item.fixable = result.status, result.text, result.fixable
    return found


def statuses(context):
    return {item.check: item.status for item in context.window_manager.dasktoon_guide_results}


class DASKTOON_OT_guide_check(Operator):
    """Check the selected character (or every visible mesh) for what DaskToon's automatic tools need"""
    bl_idname = "dasktoon.guide_check"
    bl_label = "Check Model"
    bl_options = {'REGISTER'}

    def execute(self, context):
        found = fill(context)
        bad = sum(1 for result in found if result.status in ('WARN', 'ERROR'))
        self.report({'INFO'}, rpt_("Model Check: %d to fix") % bad if bad else rpt_("Model Check: nothing to fix"))
        return {'FINISHED'}


class DASKTOON_OT_guide_fix(Operator):
    """Let DaskToon fix this, then check again"""
    bl_idname = "dasktoon.guide_fix"
    bl_label = "Fix"
    bl_options = {'REGISTER', 'UNDO'}

    check: StringProperty(name="Check", options={'SKIP_SAVE'})

    def execute(self, context):
        from dasktoon_guide import fixes
        if self.check not in fixes.FIXES:
            return {'CANCELLED'}
        try:
            fixes.run(context, self.check)
        except Exception as ex:  # a fix that cannot run says why; the model is as it was or as far as it got
            self.report({'ERROR'}, rpt_("Could not fix it: %s") % ex)
            fill(context)
            return {'CANCELLED'}
        fill(context)
        return {'FINISHED'}


class DASKTOON_OT_guide_page(Operator):
    """Open the guide's page about this in the web browser"""
    bl_idname = "dasktoon.guide_page"
    bl_label = "Read the Guide"
    bl_options = {'REGISTER'}

    step: StringProperty(name="Step", options={'SKIP_SAVE'})
    anchor: StringProperty(name="Anchor", options={'SKIP_SAVE'})

    def execute(self, context):
        bpy.ops.wm.url_open(url=page_url(self.step or "NEW", self.anchor))
        return {'FINISHED'}


def draw_result(layout, item):
    from .dasktoon_rig import wrapped_label
    box = layout.box()
    wrapped_label(box, item.text, icon=STATUS_ICONS.get(item.status, 'NONE'))
    if item.status in ('WARN', 'ERROR') or item.fixable:
        row = box.row(align=True)
        if item.fixable:
            row.operator("dasktoon.guide_fix", text="Fix", icon='TOOL_SETTINGS').check = item.check
        page = row.operator("dasktoon.guide_page", text="", icon='QUESTION')
        page.step, page.anchor = item.step, item.check


class DaskGuidePanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY


class VIEW3D_PT_dasktoon_guide_check(DaskGuidePanel, Panel):
    bl_label = "Model Check"

    def draw(self, context):
        layout = self.layout
        results = context.window_manager.dasktoon_guide_results
        layout.operator("dasktoon.guide_check", text="Check Again" if len(results) else "Check Model",
                        icon='FILE_REFRESH' if len(results) else 'VIEWZOOM')
        if not len(results):
            layout.label(text="Select the character, or nothing to check every visible mesh")
            return
        for group, label in GROUPS:
            items = [item for item in results if item.group == group]
            if not items:
                continue
            layout.label(text=label)
            for item in items:
                draw_result(layout, item)


class VIEW3D_PT_dasktoon_guide_steps(DaskGuidePanel, Panel):
    bl_label = "Step by Step"  # not "Steps": Blender translates that one as a number of steps

    def draw(self, context):
        from dasktoon_guide import checks, steps
        from .dasktoon_rig import wrapped_label
        layout = self.layout
        meshes, _rig = checks.character(context)
        found = statuses(context)
        now = steps.current(found, context.scene, meshes)
        for number, step in enumerate(steps.STEPS, start=1):
            is_done = steps.done(step.id, found, context.scene, meshes)
            row = layout.row()
            row.label(text="%d. %s" % (number, iface_(step.title)), translate=False,
                      icon='CHECKMARK' if is_done else ('PLAY' if step.id == now else 'BLANK1'))
            if step.id != now:
                continue
            box = layout.box()
            wrapped_label(box, iface_(step.advice))
            for item in context.window_manager.dasktoon_guide_results:
                if item.step == step.id:
                    draw_result(box, item)
            for operator, label, icon in step.buttons:
                box.operator(operator, text=label, icon=icon)
            box.operator("dasktoon.guide_page", text="Read the Guide", icon='HELP').step = step.id


classes = (
    DaskGuideResult,
    DASKTOON_OT_guide_check,
    DASKTOON_OT_guide_fix,
    DASKTOON_OT_guide_page,
    VIEW3D_PT_dasktoon_guide_check,
    VIEW3D_PT_dasktoon_guide_steps,
)


def register():  # bl_ui registers the classes first
    bpy.types.WindowManager.dasktoon_guide_results = CollectionProperty(type=DaskGuideResult)


def unregister():
    del bpy.types.WindowManager.dasktoon_guide_results
