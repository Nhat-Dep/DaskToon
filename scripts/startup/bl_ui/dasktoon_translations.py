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

    # bl_ui/dasktoon_face_shading.py
    "Face Shading": "Bóng mặt",
    "Set Up Face Shading": "Tạo bóng mặt anime",
    "Shade the face like an egg: find the head, fit an egg-shaped proxy to it and add the Face Shading modifier":
        "Đổ bóng mặt như một quả trứng: tìm đầu, căn một khối trứng ôm lấy nó và thêm modifier Face Shading",
    "Fit Proxy": "Căn lại khối trứng",
    "Fit the egg-shaped proxy to the face again (position and size); the sliders stay":
        "Căn lại khối trứng theo khuôn mặt (vị trí và kích thước); giữ nguyên các thanh trượt",
    "Remove Face Shading": "Gỡ bóng mặt",
    "Remove the face shading of the mesh: the modifier, DT_Face and the proxy when no other mesh uses it":
        "Gỡ bóng mặt khỏi mesh: modifier, DT_Face và khối trứng nếu không còn mesh nào dùng",
    "Select Proxy": "Chọn khối trứng",
    "Select the egg-shaped proxy to move, rotate or scale it; the face shading follows right away":
        "Chọn khối trứng để di chuyển, xoay hoặc co giãn; bóng mặt cập nhật ngay",
    "Keep Nose Shadow": "Giữ bóng mũi",
    "Keep Chin Shadow": "Giữ bóng cằm",
    "Proxy of %s": "Khối trứng của %s",
    "No proxy yet: press Fit Proxy": "Chưa có khối trứng: bấm Căn lại khối trứng",
    "Linked from a library, cannot be edited": "Link từ thư viện, không sửa được",
    "This mesh still has old custom normals:": "Mesh còn custom normal cũ:",
    "the nose and chin shadows follow them, not the real shape": "bóng mũi và cằm sẽ theo normal đó, không theo hình khối thật",
    "Select a character mesh": "Hãy chọn mesh nhân vật",
    "Mesh %s is linked from a library and cannot be edited": "Mesh %s được link từ thư viện, không sửa được",
    "No head found (no head bone with weights): select the face in Edit Mode and try again":
        "Không tìm thấy vùng đầu (không có xương đầu có trọng số): hãy chọn vùng mặt trong Edit Mode rồi bấm lại",
    "No face skin in the middle of the head: select the whole face, nose included, and try again":
        "Không thấy da mặt ở giữa vùng đầu: hãy chọn cả khuôn mặt, kể cả mũi, rồi bấm lại",
    "The face is too small to fit a proxy": "Vùng mặt quá nhỏ để đặt khối trứng",
    "%s is not inside the head: paint that vertex group again": "%s không nằm trong vùng đầu: hãy tô lại vertex group đó",
    "%s has no face shading yet: press Set Up Face Shading first":
        "%s chưa có bóng mặt: hãy bấm Tạo bóng mặt anime trước",
    "Face shading set up on %s: drag the proxy or use the sliders":
        "Đã tạo bóng mặt cho %s: kéo khối trứng hoặc chỉnh thanh trượt",
    "Proxy of %s fitted again": "Đã căn lại khối trứng của %s",
    "Face shading removed from %s": "Đã gỡ bóng mặt của %s",
    "This mesh has no proxy yet: press Set Up Face Shading or Fit Proxy":
        "Mesh chưa có khối trứng: bấm Tạo bóng mặt anime hoặc Căn lại khối trứng",
    "Proxy %s is not in the open view layer": "Khối trứng %s không nằm trong view layer đang mở",
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
