# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Painted images are saved with the file (spec section 3, ruling 7): an image with a file on disk is written to that
file; an image without one, and every layer image, is packed into the .blend (floats as OpenEXR, so they stay
floats)."""

import bpy


def _layer_images():
    return {item.image for owner in bpy.data.images for item in owner.dasktoon_layers if item.image is not None}


def save_painted():
    """Save every changed image as above; returns the names of those saved or packed."""
    layers = _layer_images()
    done = []
    for image in bpy.data.images:
        if image.type in {'RENDER_RESULT', 'COMPOSITING'} or not image.has_data:
            continue
        owner = len(image.dasktoon_layers) > 0
        if not (image.is_dirty or ((image in layers or owner) and image.packed_file is None)):
            continue
        on_disk = (image.source == 'FILE' and image.filepath and image.packed_file is None and image not in layers)
        if on_disk:
            image.save()
        else:
            if image.is_float:
                image.file_format = 'OPEN_EXR'
            image.pack()
        done.append(image.name)
    return done
