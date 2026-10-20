# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime painting (docs/superpowers/specs/2026-10-20-dasktoon-paint-layers-design.md): the paint layers of an image
(their data, the operators, the list drawn into Blender's Texture Slots panel and the Image Editor's Image panel, no
DaskToon panel of its own: UI spec of 2026-10-04), and the handlers that keep the composites right after loading and
undoing."""

import bpy
from bpy.app.handlers import persistent
from bpy.app.translations import pgettext_n as n_
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, \
    StringProperty
from bpy.types import Operator, PropertyGroup, UIList

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
                        description="How the layer mixes with the layers under it")
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
    row = box.row(align=True)
    row.operator("dasktoon.paint_layer_duplicate", text="Duplicate", icon='DUPLICATE').image = name
    row.operator("dasktoon.paint_layer_merge_down", text="Merge Down", icon='TRIA_DOWN_BAR').image = name
    row.operator("dasktoon.paint_layers_flatten", text="Flatten", icon='IMAGE_DATA').image = name


def draw_texture_slots(self, context):
    """Appended to Blender's Texture Slots panel (3D texture paint)."""
    draw_layers(self.layout, paint_image(context))


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


_HANDLERS = ((bpy.app.handlers.load_post, _composite_all), (bpy.app.handlers.undo_post, _composite_all),
             (bpy.app.handlers.redo_post, _composite_all))

classes = (
    DaskPaintLayer,
    DASKTOON_OT_paint_layer_add,
    DASKTOON_OT_paint_layer_duplicate,
    DASKTOON_OT_paint_layer_remove,
    DASKTOON_OT_paint_layer_move,
    DASKTOON_OT_paint_layer_merge_down,
    DASKTOON_OT_paint_layers_flatten,
    DASKTOON_UL_paint_layers,
)


def register():  # bl_ui registers the classes first
    from .space_image import IMAGE_PT_image_properties
    from .space_view3d_toolbar import VIEW3D_PT_slots_projectpaint
    bpy.types.Image.dasktoon_layers = CollectionProperty(type=DaskPaintLayer, name="Paint Layers")
    bpy.types.Image.dasktoon_layer_index = IntProperty(name="Active Layer", min=0,
                                                       description="The paint layer strokes go to")
    VIEW3D_PT_slots_projectpaint.append(draw_texture_slots)
    IMAGE_PT_image_properties.append(draw_image_panel)
    for handlers, handler in _HANDLERS:
        if handler not in handlers:
            handlers.append(handler)


def unregister():
    from .space_image import IMAGE_PT_image_properties
    from .space_view3d_toolbar import VIEW3D_PT_slots_projectpaint
    for handlers, handler in _HANDLERS:
        if handler in handlers:
            handlers.remove(handler)
    IMAGE_PT_image_properties.remove(draw_image_panel)
    VIEW3D_PT_slots_projectpaint.remove(draw_texture_slots)
    del bpy.types.Image.dasktoon_layer_index
    del bpy.types.Image.dasktoon_layers
