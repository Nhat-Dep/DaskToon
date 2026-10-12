# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Illustration Finish panel in Render Properties (docs/superpowers/specs/2026-10-13-dasktoon-illustration-finish-
design.md, sections 4 to 7): the scene's finish settings, made from dasktoon_finish.settings, kept in sync with the
finish's node group and the scene's compositor; the viewports that show it; colored lines for every material."""

import math

import bpy
from bpy.app.handlers import persistent
from bpy.app.translations import pgettext_iface as iface_, pgettext_rpt as rpt_
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, PointerProperty, StringProperty
from bpy.types import Menu, Operator, Panel, PropertyGroup

from dasktoon_finish import nodes, scene as finish_scene, settings

ENGINES = {'BLENDER_EEVEE', 'DASKTOON_ANIME'}
_suspended = [0]  # while a style sets many settings, they are synced once at the end


def computed(scene, depsgraph=None):
    """The group's computed inputs (nodes.COMPUTED): where the scene's Sun is on the picture and whether it is in
    front of the camera, the light direction (from the Sun, or the gradient angle), the focus (automatic, or the
    focus distance). Animated objects are read as `depsgraph` evaluated them."""
    from dasktoon_finish import sun

    def evaluated(obj):
        return obj.evaluated_get(depsgraph) if depsgraph is not None and obj is not None else obj

    finish = scene.dasktoon_finish
    angle = finish.gradient_angle
    out = {"focus": finish.focus_distance, "light_direction": (math.cos(angle), math.sin(angle), 0.0),
           "sun_visible": 0.0}
    camera = evaluated(scene.camera)
    if camera is None:
        return out
    light = evaluated(sun.find_sun(scene))
    if light is not None:
        (x, y), front = sun.sun_on_picture(scene, camera, light)
        out["sun_position"] = (x, y, 0.0)
        out["sun_visible"] = 1.0 if front else 0.0
        if finish.gradient_auto:
            direction = sun.light_direction(camera, light)
            out["light_direction"] = (direction.x, direction.y, 0.0)
    if finish.focus_auto:
        view_layer = bpy.context.view_layer if bpy.context.scene == scene else scene.view_layers[0]
        focus = sun.focus_distance(camera, evaluated(view_layer.objects.active))
        if focus is not None:
            out["focus"] = focus
    return out


def update_computed(scene, depsgraph=None):
    """Write the computed inputs into the finish's nodes; True when one changed."""
    finish = scene.dasktoon_finish
    if not finish.enabled or finish.group is None:
        return False
    values = computed(scene, depsgraph)
    changed = False
    for node in finish_scene.group_nodes(scene, finish.group):
        changed |= nodes.set_inputs(node, values)
    return changed


@persistent
def finish_depsgraph_post(scene, depsgraph):
    """The Sun, the camera or the selection moved."""
    update_computed(scene, depsgraph)


@persistent
def finish_frame_change_post(scene, depsgraph):
    """An animated Sun or camera moves on frame changes, which do not run depsgraph_update_post."""
    update_computed(scene, depsgraph)


def values_of(finish):
    """{key: value} of every setting of the scene's finish."""
    out = {}
    for setting in settings.SETTINGS:
        value = getattr(finish, setting.key)
        out[setting.key] = tuple(value) if setting.kind == 'COLOR' else value
    return out


def apply_viewport(mode):
    """Every 3D Viewport shows the compositor in `mode` (Disabled, Camera, Always)."""
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                shading = area.spaces.active.shading
                if shading.use_compositor != mode:
                    shading.use_compositor = mode


def sync(scene):
    """The finish's node group, the scene's compositor and the viewports follow the scene's settings."""
    if _suspended[0]:
        return
    finish = scene.dasktoon_finish
    if not finish.enabled:
        if finish.group is not None:
            finish_scene.set_enabled(scene, finish.group, False)
        return
    layers = {key for key in settings.LAYER_KEYS if getattr(finish, key)}
    group = nodes.ensure(finish.group, layers)
    if finish.group != group:
        finish.group = group
    finish_scene.ensure_compositor(scene, group)
    finish_scene.set_enabled(scene, group, True)
    values = nodes.input_values(values_of(finish), computed(scene))
    for node in finish_scene.group_nodes(scene, group):
        nodes.set_inputs(node, values)
    apply_viewport(finish.viewport)


def _changed(self, _context):
    sync(self.id_data)


def compositor_state(scene):
    """'OFF', 'IN' (the finish is in the scene's compositor), 'USER' (the user's own compositor, without it)."""
    finish = scene.dasktoon_finish
    if not finish.enabled or finish.group is None:
        return 'OFF'
    if finish_scene.group_nodes(scene, finish.group):
        return 'IN'
    return 'USER'


def _setting_property(setting):
    common = {"name": setting.label, "description": setting.description, "update": _changed}
    if setting.kind in {'LAYER', 'OPTION', 'SWITCH'}:
        return BoolProperty(default=setting.default, **common)
    if setting.kind == 'COLOR':
        # Colors as seen: the finish works on the colors on screen.
        return FloatVectorProperty(subtype='COLOR_GAMMA', size=3, default=setting.default, min=0.0, max=1.0,
                                   **common)
    if setting.kind == 'FACTOR':
        return FloatProperty(subtype='FACTOR', default=setting.default, min=setting.low, max=setting.high, **common)
    if setting.kind == 'DISTANCE':
        return FloatProperty(unit='LENGTH', default=setting.default, min=setting.low, soft_max=setting.high, **common)
    if setting.kind == 'ANGLE':
        return FloatProperty(subtype='ANGLE', default=setting.default, min=setting.low, max=setting.high, **common)
    return FloatProperty(default=setting.default, min=setting.low, max=setting.high, precision=3, **common)


def _is_compositor(_self, tree):
    return tree.bl_idname == 'CompositorNodeTree'


_annotations = {setting.key: _setting_property(setting) for setting in settings.SETTINGS}
_annotations.update(
    enabled=BoolProperty(
        name="Illustration Finish", update=_changed,
        description="Give the picture the finish a painter gives an illustration: light, colors, depth and texture"),
    viewport=EnumProperty(
        name="Show in Viewport", update=_changed, default='CAMERA',
        description="Which 3D Viewports in Rendered shading show the finish",
        items=(('DISABLED', "Off", "Only renders show the finish"),
               ('CAMERA', "Camera View", "Viewports looking through the camera show the finish"),
               ('ALWAYS', "Always", "Every viewport in Rendered shading shows the finish"))),
    group=PointerProperty(
        name="Node Group", type=bpy.types.NodeTree, poll=_is_compositor,
        description="The finish's compositor node group (DaskToon builds it again when a layer is switched)"),
    style=StringProperty(name="Style", description="The style last used or saved"),
)
DaskFinishSettings = type("DaskFinishSettings", (PropertyGroup,), {
    "__annotations__": _annotations, "__doc__": "The scene's illustration finish (DaskToon)"})


class DASKTOON_OT_finish_add_to_compositor(Operator):
    """Put the Illustration Finish right before the output of the scene's compositor"""
    bl_idname = "dasktoon.finish_add_to_compositor"
    bl_label = "Add to Compositor"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return compositor_state(context.scene) == 'USER'

    def execute(self, context):
        finish_scene.insert(context.scene, context.scene.dasktoon_finish.group)
        sync(context.scene)
        return {'FINISHED'}


def apply_style(scene, name):
    """Set every setting of the scene's finish from the style `name`, then sync once. False without that style."""
    from dasktoon_finish import styles
    values = styles.style_values(name)
    if values is None:
        return False
    finish = scene.dasktoon_finish
    _suspended[0] += 1
    try:
        for key, value in values.items():
            setattr(finish, key, value)
        finish.style = name
    finally:
        _suspended[0] -= 1
    sync(scene)
    return True


class DASKTOON_OT_finish_style_apply(Operator):
    """Set every layer of the finish from this style"""
    bl_idname = "dasktoon.finish_style_apply"
    bl_label = "Use Style"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name")

    def execute(self, context):
        if not apply_style(context.scene, self.name):
            self.report({'ERROR'}, rpt_("No style %s") % self.name)
            return {'CANCELLED'}
        return {'FINISHED'}


class DASKTOON_OT_finish_style_save(Operator):
    """Save every setting of the finish as a style of your own, for every file"""
    bl_idname = "dasktoon.finish_style_save"
    bl_label = "Save Style"

    name: StringProperty(name="Name", default="My Style")
    overwrite: BoolProperty(name="Overwrite Existing", default=False)

    def invoke(self, context, _event):
        self.name = context.scene.dasktoon_finish.style or self.name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        from dasktoon_finish import styles
        name = self.name.strip()
        if not name:
            self.report({'ERROR'}, rpt_("Give the style a name"))
            return {'CANCELLED'}
        if name in styles.BUILT_IN:
            self.report({'ERROR'}, rpt_("%s is a built-in style: choose another name") % name)
            return {'CANCELLED'}
        if name in styles.user_style_names() and not self.overwrite:
            self.report({'ERROR'}, rpt_("Style %s already exists: turn on Overwrite Existing to replace it") % name)
            return {'CANCELLED'}
        finish = context.scene.dasktoon_finish
        styles.save(name, values_of(finish))
        finish.style = name
        self.report({'INFO'}, rpt_("Saved style %s") % name)
        return {'FINISHED'}


class DASKTOON_OT_finish_style_delete(Operator):
    """Delete this style of your own"""
    bl_idname = "dasktoon.finish_style_delete"
    bl_label = "Delete Style"

    name: StringProperty(name="Name")

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, _context):
        from dasktoon_finish import styles
        styles.delete(self.name)
        self.report({'INFO'}, rpt_("Deleted style %s") % self.name)
        return {'FINISHED'}


class DASKTOON_MT_finish_styles(Menu):
    bl_label = "Styles"

    def draw(self, _context):
        from dasktoon_finish import styles
        layout = self.layout
        for name in styles.BUILT_IN:
            layout.operator(DASKTOON_OT_finish_style_apply.bl_idname, text=name).name = name
        mine = styles.user_style_names()
        if mine:
            layout.separator()
            for name in mine:
                layout.operator(DASKTOON_OT_finish_style_apply.bl_idname, text=name, icon='USER',
                                translate=False).name = name
            layout.separator()
            layout.menu(DASKTOON_MT_finish_styles_delete.__name__, icon='TRASH')


class DASKTOON_MT_finish_styles_delete(Menu):
    bl_label = "Delete Style"

    def draw(self, _context):
        from dasktoon_finish import styles
        for name in styles.user_style_names():
            self.layout.operator(DASKTOON_OT_finish_style_delete.bl_idname, text=name, translate=False).name = name


def colored_lines():
    """Every material with an outline takes the outline color from its own colors (Auto Harmonic). Returns how many."""
    from bl_ui import dasktoon_outline as outline
    count = 0
    for mat in bpy.data.materials:
        found = outline.find_source(mat)
        if found is None:
            continue
        _kind, node = found
        if node is None:
            dask = outline.outline_node(outline.outline_material_for(mat, create=False))
            if dask is None:
                continue
            node, prop = dask, "tint_mode"
        else:
            prop = "outline_tint_mode"
        harmonic = next(item.identifier for item in node.bl_rna.properties[prop].enum_items if item.value == 1)
        if getattr(node, prop) != harmonic:
            setattr(node, prop, harmonic)
        count += 1
    return count


class DASKTOON_OT_finish_colored_lines(Operator):
    """Give every outlined material lines in a deep shade of its own colors (Auto Harmonic), not one fixed color"""
    bl_idname = "dasktoon.finish_colored_lines"
    bl_label = "Colored Lines for All Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, _context):
        self.report({'INFO'}, rpt_("Colored lines on %d materials") % colored_lines())
        return {'FINISHED'}


def draw_main(layout, context):
    scene = context.scene
    finish = scene.dasktoon_finish
    layout.use_property_split = True
    layout.active = finish.enabled
    row = layout.row(align=True)
    row.menu(DASKTOON_MT_finish_styles.__name__, text=finish.style or iface_("Style"), icon='PRESET',
             translate=False)
    row.operator(DASKTOON_OT_finish_style_save.bl_idname, text="", icon='ADD')
    layout.prop(finish, "amount", slider=True)
    layout.prop(finish, "viewport")
    if compositor_state(scene) == 'USER':
        box = layout.box()
        box.label(text="The scene has its own compositor", icon='NODE_COMPOSITING')
        box.operator(DASKTOON_OT_finish_add_to_compositor.bl_idname, icon='ADD')
    layout.operator(DASKTOON_OT_finish_colored_lines.bl_idname, icon='BRUSH_DATA')


def draw_group(layout, context, group):
    """The layers of `group`: each one's switch, then its settings."""
    finish = context.scene.dasktoon_finish
    layout.use_property_split = True
    layout.active = finish.enabled
    for key, _label, layer_group in settings.LAYERS:
        if layer_group != group:
            continue
        col = layout.column()
        col.prop(finish, key)
        sub = col.column()
        sub.active = getattr(finish, key)
        for setting in settings.SETTINGS:
            if setting.layer != key or setting.kind == 'LAYER':
                continue
            row = sub.row()
            if setting.key == "focus_distance":
                row.active = not finish.focus_auto
            elif setting.key == "gradient_angle":
                row.active = not finish.gradient_auto
            row.prop(finish, setting.key)
        layout.separator()


class DASKTOON_PT_finish(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    bl_label = "Illustration Finish"
    COMPAT_ENGINES = ENGINES

    @classmethod
    def poll(cls, context):
        return context.engine in cls.COMPAT_ENGINES

    def draw_header(self, context):
        self.layout.prop(context.scene.dasktoon_finish, "enabled", text="")

    def draw(self, context):
        draw_main(self.layout, context)


def _group_panel(group, label):
    def draw(self, context):
        draw_group(self.layout, context, group)

    return type("DASKTOON_PT_finish_" + group, (Panel,), {
        "bl_space_type": 'PROPERTIES', "bl_region_type": 'WINDOW', "bl_context": "render", "bl_label": label,
        "bl_parent_id": DASKTOON_PT_finish.__name__, "bl_options": {'DEFAULT_CLOSED'}, "COMPAT_ENGINES": ENGINES,
        "poll": classmethod(lambda cls, context: context.engine in cls.COMPAT_ENGINES), "draw": draw})


_LABELS = dict(settings.GROUPS)
DASKTOON_PT_finish_COLOR = _group_panel('COLOR', _LABELS['COLOR'])
DASKTOON_PT_finish_DEPTH = _group_panel('DEPTH', _LABELS['DEPTH'])
DASKTOON_PT_finish_LIGHT = _group_panel('LIGHT', _LABELS['LIGHT'])
DASKTOON_PT_finish_TEXTURE = _group_panel('TEXTURE', _LABELS['TEXTURE'])

classes = (
    DaskFinishSettings,
    DASKTOON_OT_finish_add_to_compositor,
    DASKTOON_OT_finish_colored_lines,
    DASKTOON_OT_finish_style_apply,
    DASKTOON_OT_finish_style_save,
    DASKTOON_OT_finish_style_delete,
    DASKTOON_MT_finish_styles,
    DASKTOON_MT_finish_styles_delete,
    DASKTOON_PT_finish,
    DASKTOON_PT_finish_COLOR,
    DASKTOON_PT_finish_DEPTH,
    DASKTOON_PT_finish_LIGHT,
    DASKTOON_PT_finish_TEXTURE,
)


_HANDLERS = ((bpy.app.handlers.depsgraph_update_post, finish_depsgraph_post),
             (bpy.app.handlers.frame_change_post, finish_frame_change_post))


# bl_ui registers `classes`; register() adds the scene's settings and the handlers that follow the Sun.
def register():
    bpy.types.Scene.dasktoon_finish = PointerProperty(
        name="Illustration Finish", type=DaskFinishSettings,
        description="The scene's illustration finish (DaskToon)")
    for handlers, handler in _HANDLERS:
        if handler not in handlers:
            handlers.append(handler)


def unregister():
    for handlers, handler in _HANDLERS:
        if handler in handlers:
            handlers.remove(handler)
    del bpy.types.Scene.dasktoon_finish
