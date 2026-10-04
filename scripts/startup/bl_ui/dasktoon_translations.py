# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Vietnamese translation of the DaskToon interface (docs/superpowers/specs/2026-10-04-dasktoon-ui-reorganization-design.md,
section 6). The source strings are English; with Preferences › Interface › Language set to Tiếng Việt Blender shows
these. Strings Blender already translates keep Blender's wording. Every entry is registered for the default context
("*") and for operator names ("Operator")."""

import bpy

# Names that stay as they are in Vietnamese (brands, standards, shape key names).
KEEP = {
    "DaskToon", "Unity", "Unity 6 (URP)", "VRM", "VRoid", "ARKit", "FBX", "URP",
}

VI = {
    # bl_ui/dasktoon_engine_export.py
    "Engine Export": "Xuất sang engine",
    "Engine Export…": "Xuất sang engine…",
    "Export the model, its DaskToon materials and the shaders for a game engine":
        "Xuất model, material DaskToon và shader cho game engine",
    "Folder": "Thư mục",
    "Model": "Mô hình",
    "Export the model as FBX": "Xuất model dạng FBX",
    "No Model": "Không xuất model",
    "Export only the materials and shaders": "Chỉ xuất material và shader",
    "Include Animation": "Kèm animation",
    "Export Materials and Shaders": "Xuất material và shader",
    "Bake Size": "Cỡ ảnh bake",
    "Writes straight into the Unity project": "Ghi thẳng vào project Unity",
    "Creates the folder %s": "Tạo thư mục %s",
    "This engine is coming soon; only Unity 6 (URP) is supported for now":
        "Engine này sắp có; hiện chỉ hỗ trợ Unity 6 (URP)",
    "No destination folder chosen": "Chưa chọn thư mục đích",
    "Nothing to export (no object selected?)": "Không có gì để xuất (chưa chọn object?)",

    # bl_ui/dasktoon_outline.py
    "Remove DaskToon Outline": "Gỡ outline DaskToon",
    "Turn off the DaskToon outline this material got before outlines moved onto the Anime BSDF and Dask Cel nodes":
        "Tắt outline DaskToon mà material này được bật từ trước khi outline chuyển lên node Anime BSDF và Dask Cel",

    # bl_ui/dasktoon_outline_gamedata.py
    "Prepare Outline for Games": "Chuẩn bị outline cho game",
    "Write smoothed outline normals and the width mask into real UV maps for game export":
        "Ghi normal outline đã làm mượt và mặt nạ độ dày vào UV map thật để xuất sang game",
    "%s: needs at least one UV map": "%s: cần ít nhất một UV map",
    "%s: has faces with more than 4 sides (n-gons); triangulate or split them first":
        "%s: có mặt nhiều hơn 4 cạnh (ngon); hãy Triangulate hoặc chia lại trước",
    "%s: wrote %s and %s": "%s: đã ghi %s và %s",
    "Prepared %d mesh(es), %d error(s)": "Đã chuẩn bị %d mesh, %d lỗi",
}


def _table():
    table = {}
    for msgid, msgstr in VI.items():
        for context in ("*", "Operator"):
            table[(context, msgid)] = msgstr
    return {"vi_VN": table}


translations = _table()
classes = ()


def register():
    try:
        bpy.app.translations.unregister(__name__)
    except (ValueError, RuntimeError):
        pass
    bpy.app.translations.register(__name__, translations)


def unregister():
    bpy.app.translations.unregister(__name__)
