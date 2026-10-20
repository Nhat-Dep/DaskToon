# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Paint layers inside the image (spec section 2). An image's layers are `Image.dasktoon_layers` (bottom first) and
`Image.dasktoon_layer_index` (the active one, which strokes go to); each layer is a hidden image of the same size and
kind. The image itself is the composite; one compositing code, C++ (paint.dasktoon_layers_composite).

A layer's pixels are never changed here: merge down makes a new image, remove only takes the layer out of the list.
The old images stay in the file until it is saved, so Undo, which brings the list back, finds them as they were."""

import bpy
import numpy as np
from bpy.app.translations import pgettext_data as data_


def composite(image=None):
    """Composite `image` from its layers (every image with layers when None)."""
    bpy.ops.paint.dasktoon_layers_composite(image=image.name if image is not None else "")


def _pixels(image):
    px = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(px)
    return px


def _new_image(owner, name, pixels=None):
    """A hidden layer image the size, kind and colour space of `owner`, empty or holding `pixels`."""
    width, height = owner.size
    image = bpy.data.images.new("." + owner.name + " " + name, width, height, alpha=True,
                                float_buffer=owner.is_float)
    image.colorspace_settings.name = owner.colorspace_settings.name
    if pixels is None:
        pixels = np.zeros(width * height * 4, dtype=np.float32)
    image.pixels.foreach_set(pixels)
    image.update()
    return image


def _insert(owner, image, name, index):
    """Put a layer holding `image` at `index` of the list; returns it (its index is `index`)."""
    items = owner.dasktoon_layers
    item = items.add()
    item.name = name
    item.image = image
    items.move(len(items) - 1, index)
    owner.dasktoon_layer_index = index
    return items[index]


def _unique(owner, base):
    names = {item.name for item in owner.dasktoon_layers}
    number = 1
    while "%s %d" % (base, number) in names:
        number += 1
    return "%s %d" % (base, number)


def add(owner, name=None):
    """A new empty layer above the active one. On an image without layers its picture first becomes the layer
    Base, so what shows does not change."""
    items = owner.dasktoon_layers
    if not len(items):
        _insert(owner, _new_image(owner, data_("Base"), _pixels(owner)), data_("Base"), 0)
    name = name or _unique(owner, data_("Layer"))
    index = min(owner.dasktoon_layer_index + 1, len(items))
    layer = _insert(owner, _new_image(owner, name), name, index)
    composite(owner)
    return layer


def duplicate(owner, index):
    source = owner.dasktoon_layers[index]
    name = _unique(owner, source.name)
    layer = _insert(owner, _new_image(owner, name, _pixels(source.image)), name, index + 1)
    layer.opacity, layer.blend, layer.hide = source.opacity, source.blend, source.hide
    composite(owner)
    return layer


def remove(owner, index):
    """Take the layer out of the list; the image keeps what shows when it was the last one."""
    items = owner.dasktoon_layers
    items.remove(index)
    owner.dasktoon_layer_index = max(0, min(index, len(items) - 1))
    if len(items):
        composite(owner)


def move(owner, index, step):
    """Move the layer `step` places up (+1, toward the top) or down (-1)."""
    items = owner.dasktoon_layers
    target = max(0, min(index + step, len(items) - 1))
    if target != index:
        items.move(index, target)
        owner.dasktoon_layer_index = target
        composite(owner)


def merge_down(owner, index):
    """Merge the layer into the one under it: a new image of the two as they show (the result blends normally)."""
    items = owner.dasktoon_layers
    if index <= 0 or index >= len(items):
        return
    lower, upper = items[index - 1], items[index]
    merged = _new_image(owner, lower.name)
    pair = merged.dasktoon_layers
    for source, blend in ((lower, 'NORMAL'), (upper, upper.blend)):
        item = pair.add()
        item.image, item.opacity, item.hide, item.blend = source.image, source.opacity, source.hide, blend
    composite(merged)  # the two, as they show, into the new image
    pair.clear()
    merged.update()
    name = lower.name
    lower.image, lower.opacity, lower.blend, lower.hide = merged, 1.0, 'NORMAL', False
    lower.name = name
    items.remove(index)
    owner.dasktoon_layer_index = index - 1
    composite(owner)


def flatten(owner):
    """Drop every layer; the image keeps what shows."""
    composite(owner)
    owner.dasktoon_layers.clear()
    owner.dasktoon_layer_index = 0


def is_layer(image):
    """True when `image` is a layer of another image."""
    return any(item.image == image for owner in bpy.data.images for item in owner.dasktoon_layers)
