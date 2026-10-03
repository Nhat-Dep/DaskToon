# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Texture files for Unity: copied images, 256x1 ramp strips, baked branches as PNG or EXR (spec 4, 5)."""

import os
import struct
import tempfile
import zlib

import bpy
import numpy as np

RAMP_WIDTH = 256
UNITY_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tga", ".exr", ".psd", ".tif", ".tiff", ".bmp", ".hdr"}
FORMAT_EXTENSIONS = {'PNG': ".png", 'JPEG': ".jpg", 'TARGA': ".tga", 'TARGA_RAW': ".tga", 'OPEN_EXR': ".exr",
                     'TIFF': ".tif", 'BMP': ".bmp", 'HDR': ".hdr"}


def png_bytes(width, height, rgba):
    """8-bit RGBA PNG. `rgba` holds rows bottom-up, the way Blender stores pixels."""
    stride = width * 4
    raw = bytearray()
    for y in range(height - 1, -1, -1):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def _srgb(values):
    values = np.clip(values, 0.0, None)
    return np.where(values <= 0.0031308, values * 12.92, 1.055 * np.power(values, 1.0 / 2.4) - 0.055)


def _to_bytes(px):
    return (np.clip(px, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).tobytes()


def float_to_png(pixels, width, height, srgb):
    """PNG of float RGBA pixels (rows bottom-up): colour data is sRGB-encoded, numbers are stored as they are."""
    px = np.asarray(pixels, dtype=np.float64).reshape(-1, 4).copy()
    if srgb:
        px[:, :3] = _srgb(px[:, :3])
    return png_bytes(width, height, _to_bytes(px))


def needs_float(pixels):
    """True when a baked branch leaves the 0-1 range and must be stored as EXR."""
    rgb = np.asarray(pixels).reshape(-1, 4)[:, :3]
    return bool((rgb < -1e-4).any() or (rgb > 1.0 + 1e-4).any())


def ramp_pixels(ramp):
    """RGBA bytes of the 256x1 ramp strip: pixel i = ramp.evaluate((i + 0.5) / 256), sRGB-encoded."""
    px = np.array([ramp.evaluate((i + 0.5) / RAMP_WIDTH) for i in range(RAMP_WIDTH)], dtype=np.float64)
    px[:, 3] = 1.0
    px[:, :3] = _srgb(px[:, :3])
    return _to_bytes(px)


def ramp_png(ramp):
    return png_bytes(RAMP_WIDTH, 1, ramp_pixels(ramp))


def image_file(image):
    """(extension, bytes) of an image's own file, packed or on disk; None when Unity cannot use it as is."""
    if image.packed_file is not None:
        ext = os.path.splitext(image.filepath)[1].lower() or FORMAT_EXTENSIONS.get(image.file_format, "")
        data = bytes(image.packed_file.data)
    else:
        path = bpy.path.abspath(image.filepath, library=image.library)
        if not os.path.isfile(path):
            return None
        ext = os.path.splitext(path)[1].lower()
        with open(path, "rb") as f:
            data = f.read()
    if ext not in UNITY_IMAGE_EXTENSIONS:
        return None
    return ext, data


def exr_bytes(pixels, width, height):
    """Float RGBA pixels (rows bottom-up) as OpenEXR, written through a throwaway Blender image."""
    image = bpy.data.images.new("DT_ExportEXR", width, height, alpha=True, float_buffer=True, is_data=True)
    path = os.path.join(tempfile.mkdtemp(prefix="dt_exr_"), "texture.exr")
    try:
        image.pixels.foreach_set(np.asarray(pixels, dtype=np.float32).ravel())
        image.filepath_raw = path
        image.file_format = 'OPEN_EXR'
        image.save()
        with open(path, "rb") as f:
            return f.read()
    finally:
        bpy.data.images.remove(image)
        if os.path.exists(path):
            os.remove(path)
