# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime painting (docs/superpowers/specs/2026-10-20-dasktoon-paint-layers-design.md): the paint layers of an image
(their data, the operators, the list drawn into Blender's Texture Slots panel and the Image Editor's Image panel, no
DaskToon panel of its own: UI spec of 2026-10-04), Start Painting (the material menu, Texture Slots without slots), the
Fill Part tool of Texture Paint, and the handlers: composites right after loading and undoing, painted images saved
with the file."""

import bpy
from bpy.app.handlers import persistent
from bpy.app.translations import pgettext_n as n_, pgettext_rpt as rpt_
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, \
    StringProperty
from bpy.types import Operator, PropertyGroup, UIList, WorkSpaceTool

BLENDS = (
    ('NORMAL', n_("Normal"), n_("The layer covers what is under it"), 0),
    ('MULTIPLY', n_("Multiply"), n_("Darkens: shadows and lines"), 1),
    ('ADD', n_("Add"), n_("Brightens by adding: glows"), 2),
    ('SCREEN', n_("Screen"), n_("Brightens softly: highlights"), 3),
    ('OVERLAY', n_("Overlay"), n_("Darkens the darks and brightens the lights: patterns and texture"), 4),
)


def _layer_changed(self, _context):
    from dasktoon_paint import layers
    owner = self.id_data
    if isinstance(owner, bpy.types.Image) and len(owner.dasktoon_layers):
        layers.composite(owner)


class DaskPaintLayer(PropertyGroup):
    """One paint layer of an image"""
    image: PointerProperty(name="Image", type=bpy.types.Image, description="The layer's pixels")
    opacity: FloatProperty(name="Opacity", default=1.0, min=0.0, max=1.0, subtype='FACTOR', update=_layer_changed,
                           description="How strongly the layer shows")
    blend: EnumProperty(name="Blend", items=BLENDS, default='NORMAL', update=_layer_changed,
                        translation_context="DaskToon", description="How the layer mixes with the layers under it")
    hide: BoolProperty(name="Hide", update=_layer_changed, description="Hide the layer (strokes still go to it)")


def paint_image(context):
    """The image the 3D view's texture paint strokes go to: the active slot's image, or the canvas."""
    settings = context.tool_settings.image_paint
    if settings.mode == 'IMAGE':
        return settings.canvas
    obj = context.active_object
    mat = obj.active_material if obj is not None else None
    if mat is None or not mat.texture_paint_images:
        return None
    return mat.texture_paint_images[min(mat.paint_active_slot, len(mat.texture_paint_images) - 1)]


def _image(context, name):
    return bpy.data.images.get(name) if name else None


class DaskPaintLayerOperator:
    bl_options = {'REGISTER', 'UNDO'}

    image: StringProperty(name="Image", options={'SKIP_SAVE', 'HIDDEN'})

    def owner(self, context):
        return _image(context, self.image)


class DASKTOON_OT_paint_layer_add(DaskPaintLayerOperator, Operator):
    """Add an empty paint layer above the active one (the first time, the picture becomes the layer Base)"""
    bl_idname = "dasktoon.paint_layer_add"
    bl_label = "Add Layer"

    def execute(self, context):
        from dasktoon_paint import layers
        owner = self.owner(context)
        if owner is None or owner.source == 'TILED' or not owner.has_data:
            return {'CANCELLED'}
        layers.add(owner)
        return {'FINISHED'}


class DASKTOON_OT_paint_layer_duplicate(DaskPaintLayerOperator, Operator):
    """Make a copy of the active paint layer above it"""
    bl_idname = "dasktoon.paint_layer_duplicate"
    bl_label = "Duplicate Layer"

    def execute(self, context):
        from dasktoon_paint import layers
        owner = self.owner(context)
        if owner is None or not len(owner.dasktoon_layers):
            return {'CANCELLED'}
        layers.duplicate(owner, owner.dasktoon_layer_index)
        return {'FINISHED'}


class DASKTOON_OT_paint_layer_remove(DaskPaintLayerOperator, Operator):
    """Remove the active paint layer"""
    bl_idname = "dasktoon.paint_layer_remove"
    bl_label = "Remove Layer"

    def execute(self, context):
        from dasktoon_paint import layers
        owner = self.owner(context)
        if owner is None or not len(owner.dasktoon_layers):
            return {'CANCELLED'}
        layers.remove(owner, owner.dasktoon_layer_index)
        return {'FINISHED'}


class DASKTOON_OT_paint_layer_move(DaskPaintLayerOperator, Operator):
    """Move the active paint layer up or down"""
    bl_idname = "dasktoon.paint_layer_move"
    bl_label = "Move Layer"

    direction: EnumProperty(name="Direction", items=(('UP', n_("Up"), ""), ('DOWN', n_("Down"), "")))

    def execute(self, context):
        from dasktoon_paint import layers
        owner = self.owner(context)
        if owner is None or not len(owner.dasktoon_layers):
            return {'CANCELLED'}
        layers.move(owner, owner.dasktoon_layer_index, 1 if self.direction == 'UP' else -1)
        return {'FINISHED'}


class DASKTOON_OT_paint_layer_merge_down(DaskPaintLayerOperator, Operator):
    """Merge the active paint layer into the one under it"""
    bl_idname = "dasktoon.paint_layer_merge_down"
    bl_label = "Merge Down"

    def execute(self, context):
        from dasktoon_paint import layers
        owner = self.owner(context)
        if owner is None or owner.dasktoon_layer_index <= 0:
            return {'CANCELLED'}
        layers.merge_down(owner, owner.dasktoon_layer_index)
        return {'FINISHED'}


class DASKTOON_OT_paint_layers_flatten(DaskPaintLayerOperator, Operator):
    """Drop every paint layer; the image keeps what shows"""
    bl_idname = "dasktoon.paint_layers_flatten"
    bl_label = "Flatten"

    def execute(self, context):
        from dasktoon_paint import layers
        owner = self.owner(context)
        if owner is None or not len(owner.dasktoon_layers):
            return {'CANCELLED'}
        layers.flatten(owner)
        return {'FINISHED'}


class DASKTOON_OT_paint_start(Operator):
    """Make the mesh ready to paint: UV map, a picture of each anime material's colour, anime brushes"""
    bl_idname = "dasktoon.paint_start"
    bl_label = "Start Painting"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and len(obj.material_slots) > 0

    def execute(self, context):
        from dasktoon_paint import brushes, start
        obj = context.active_object
        made = start.start(context, obj)
        brushes.ensure()
        if obj.mode != 'TEXTURE_PAINT':
            bpy.ops.object.mode_set(mode='TEXTURE_PAINT')
        context.tool_settings.image_paint.mode = 'MATERIAL'
        brushes.activate(context, 'PEN')
        if made:
            self.report({'INFO'}, rpt_("Ready to paint: %d new pictures") % len(made))
        else:
            self.report({'INFO'}, rpt_("Ready to paint"))
        return {'FINISHED'}


class DASKTOON_OT_paint_fill_part(Operator):
    """Fill the part under the cursor with the brush colour, on the active layer (face mask on: selected faces)"""
    bl_idname = "dasktoon.paint_fill_part"
    bl_label = "Fill Part"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None and obj.type == 'MESH' and obj.mode == 'TEXTURE_PAINT'
                and context.region is not None and context.region.type == 'WINDOW')

    def invoke(self, context, event):
        return self.fill(context, (event.mouse_region_x, event.mouse_region_y))

    def fill(self, context, coord):
        from bpy_extras import view3d_utils
        from dasktoon_paint import brushes, fill
        obj = context.active_object
        origin = view3d_utils.region_2d_to_origin_3d(context.region, context.region_data, coord)
        direction = view3d_utils.region_2d_to_vector_3d(context.region, context.region_data, coord)
        face = fill.face_under(obj, origin, direction)
        if face is None:
            return {'CANCELLED'}
        mesh = obj.data
        faces = [p.index for p in mesh.polygons if p.select] if mesh.use_paint_mask else fill.part_faces(mesh, face)
        settings = context.tool_settings.image_paint
        unified = settings.unified_paint_settings
        color = tuple(unified.color if unified.use_unified_color or settings.brush is None else settings.brush.color)
        point = {"name": "", "location": (0.0, 0.0, 0.0), "mouse": coord, "mouse_event": coord, "pressure": 1.0,
                 "size": 10.0, "time": 0.0, "is_start": True, "x_tilt": 0.0, "y_tilt": 0.0}
        tool = context.workspace.tools.from_space_view3d_mode('PAINT_TEXTURE', create=False)
        tool_before = tool.idname if tool is not None else ""  # read now: going back to the brush changes it
        with fill.only_faces(obj, faces), brushes.using(context, 'FILL') as brush:
            brush.color = color
            bpy.ops.paint.image_paint(stroke=[point])
        if tool_before == DaskFillPartTool.bl_idname:
            bpy.ops.wm.tool_set_by_id(name=DaskFillPartTool.bl_idname)  # going back to the brush chose its tool
        return {'FINISHED'}


class DaskFillPartTool(WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'PAINT_TEXTURE'
    bl_idname = "dasktoon.fill_part"
    bl_label = "Fill Part"
    bl_description = "Click a part of the model to fill it with the brush colour, on the active paint layer"
    bl_icon = "brush.paint_texture.fill"
    bl_keymap = (("dasktoon.paint_fill_part", {"type": 'LEFTMOUSE', "value": 'PRESS'}, None),)

    @staticmethod
    def draw_settings(context, layout, _tool):
        settings = context.tool_settings.image_paint
        unified = settings.unified_paint_settings
        owner = unified if unified.use_unified_color or settings.brush is None else settings.brush
        layout.prop(owner, "color", text="")
        image = paint_image(context)
        if image is not None and len(image.dasktoon_layers):
            layer = image.dasktoon_layers[min(image.dasktoon_layer_index, len(image.dasktoon_layers) - 1)]
            layout.label(text=layer.name, icon='RENDERLAYERS', translate=False)


class DASKTOON_UL_paint_layers(UIList):
    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        row = layout.row(align=True)
        row.prop(item, "hide", text="", emboss=False, icon='HIDE_ON' if item.hide else 'HIDE_OFF')
        row.prop(item, "name", text="", emboss=False)

    def filter_items(self, _context, data, propname):
        items = getattr(data, propname)
        return [self.bitflag_filter_item] * len(items), list(range(len(items) - 1, -1, -1))  # the top layer first


def draw_layers(layout, image):
    """The layer list of `image`, its buttons and the active layer's settings."""
    if image is None:
        return
    box = layout.box()
    header = box.row()
    header.label(text="Paint Layers", icon='RENDERLAYERS')
    if image.source == 'TILED':
        box.label(text="Layers are for single images, not tiled ones", icon='INFO')
        return
    name = image.name
    if not len(image.dasktoon_layers):
        box.operator("dasktoon.paint_layer_add", text="Add Layer", icon='ADD').image = name
        return
    row = box.row()
    row.template_list("DASKTOON_UL_paint_layers", "", image, "dasktoon_layers", image, "dasktoon_layer_index",
                      rows=3)
    column = row.column(align=True)
    column.operator("dasktoon.paint_layer_add", text="", icon='ADD').image = name
    column.operator("dasktoon.paint_layer_remove", text="", icon='REMOVE').image = name
    column.separator()
    column.operator("dasktoon.paint_layer_move", text="", icon='TRIA_UP').image = name
    down = column.operator("dasktoon.paint_layer_move", text="", icon='TRIA_DOWN')
    down.image, down.direction = name, 'DOWN'
    index = image.dasktoon_layer_index
    if 0 <= index < len(image.dasktoon_layers):
        layer = image.dasktoon_layers[index]
        column = box.column()
        column.prop(layer, "blend")
        column.prop(layer, "opacity")
        if layer.hide:
            column.label(text="The active layer is hidden: strokes on it do not show", icon='ERROR')
    column = box.column(align=True)
    column.operator("dasktoon.paint_layer_duplicate", text="Duplicate", icon='DUPLICATE').image = name
    column.operator("dasktoon.paint_layer_merge_down", text="Merge Down", icon='TRIA_DOWN_BAR').image = name
    column.operator("dasktoon.paint_layers_flatten", text="Flatten", icon='IMAGE_DATA').image = name


def draw_texture_slots(self, context):
    """Appended to Blender's Texture Slots panel (3D texture paint)."""
    image = paint_image(context)
    if image is None:
        self.layout.operator("dasktoon.paint_start", text="Start Painting", icon='BRUSH_DATA')
        return
    draw_layers(self.layout, image)


def draw_material_menu(self, _context):
    """Appended to the material slots' menu, after Use DaskToon Shader."""
    self.layout.operator("dasktoon.paint_start", text="Start Painting", icon='BRUSH_DATA')


def draw_image_panel(self, context):
    """Appended to the Image Editor's Image panel."""
    sima = context.space_data
    from dasktoon_paint import layers
    if sima.image is not None and not layers.is_layer(sima.image):
        draw_layers(self.layout, sima.image)


@persistent
def _composite_all(*_args):
    if any(len(image.dasktoon_layers) for image in bpy.data.images):
        from dasktoon_paint import layers
        layers.composite()


@persistent
def _save_painted(*_args):
    from dasktoon_paint import saving
    saving.save_painted()


_HANDLERS = ((bpy.app.handlers.load_post, _composite_all), (bpy.app.handlers.undo_post, _composite_all),
             (bpy.app.handlers.redo_post, _composite_all), (bpy.app.handlers.save_pre, _save_painted))

classes = (
    DaskPaintLayer,
    DASKTOON_OT_paint_layer_add,
    DASKTOON_OT_paint_layer_duplicate,
    DASKTOON_OT_paint_layer_remove,
    DASKTOON_OT_paint_layer_move,
    DASKTOON_OT_paint_layer_merge_down,
    DASKTOON_OT_paint_layers_flatten,
    DASKTOON_OT_paint_start,
    DASKTOON_OT_paint_fill_part,
    DASKTOON_UL_paint_layers,
)


def register():  # bl_ui registers the classes first
    from .space_image import IMAGE_PT_image_properties
    from .space_view3d_toolbar import VIEW3D_PT_slots_projectpaint
    bpy.types.Image.dasktoon_layers = CollectionProperty(type=DaskPaintLayer, name="Paint Layers")
    bpy.types.Image.dasktoon_layer_index = IntProperty(name="Active Layer", min=0,
                                                       description="The paint layer strokes go to")
    from .properties_material import MATERIAL_MT_context_menu
    VIEW3D_PT_slots_projectpaint.append(draw_texture_slots)
    IMAGE_PT_image_properties.append(draw_image_panel)
    MATERIAL_MT_context_menu.append(draw_material_menu)
    bpy.utils.register_tool(DaskFillPartTool, after={"builtin.brush"}, separator=True)
    for handlers, handler in _HANDLERS:
        if handler not in handlers:
            handlers.append(handler)


def unregister():
    from .space_image import IMAGE_PT_image_properties
    from .space_view3d_toolbar import VIEW3D_PT_slots_projectpaint
    for handlers, handler in _HANDLERS:
        if handler in handlers:
            handlers.remove(handler)
    from .properties_material import MATERIAL_MT_context_menu
    bpy.utils.unregister_tool(DaskFillPartTool)
    MATERIAL_MT_context_menu.remove(draw_material_menu)
    IMAGE_PT_image_properties.remove(draw_image_panel)
    VIEW3D_PT_slots_projectpaint.remove(draw_texture_slots)
    del bpy.types.Image.dasktoon_layer_index
    del bpy.types.Image.dasktoon_layers
