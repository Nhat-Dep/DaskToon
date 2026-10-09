# DaskToon: rig anime R1 (khung chuẩn, phần, chuỗi, weight) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao **tự động 3 tiếng** (2026-10-06 16:44); Claude chạy **inline** (superpowers:executing-plans)
> trên nhánh `dasktoon-anime-rig`, commit từng task, tự quyết điểm mơ hồ và ghi vào báo cáo. Không push, không merge.

**Goal:** Người dùng thêm khung xương chuẩn (Add › Armature › Anime Humanoid), khai báo các phần của nhân vật với vai trò
(Body, Clothing, Accessory, Hair, Skirt), bấm Build Rig là có chuỗi xương tóc/váy và weight sẵn sàng cho Unity Humanoid.

**Architecture:** Thư viện `scripts/modules/dasktoon_rig/` chia theo trách nhiệm: `skeleton.py` (bảng 55 xương, thêm và
khớp khung), `chains.py` (toán numpy thuần cho chuỗi tóc, váy), `parts.py` (đỉnh của phần, mảnh, đoán vai trò),
`weights.py` (đọc/ghi weight dạng ma trận, bone heat, chép từ bề mặt, dọn weight), `build.py` (điều phối Build). Giao
diện `scripts/startup/bl_ui/dasktoon_rig.py` (PropertyGroup trên Armature, operator, panel Properties, mục menu Add).
Engine Export đổi `animationType` sang Humanoid khi model có đúng một khung chuẩn.

**Tech Stack:** Python `bpy`, `numpy`, `mathutils` (BVHTree), `unittest` chạy trong DaskToon nền.

**Spec:** `docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md` (R1 = §4–§8, §11–§14)

## Global Constraints

- Chữ hiện cho người dùng viết tiếng Anh kiểu Blender, không emoji, icon có sẵn của Blender; mọi chữ có bản tiếng Việt
  trong `scripts/startup/bl_ui/dasktoon_translations.py` (spec §13). Không có ký tự tiếng Việt hay emoji trong chuỗi mã
  nguồn (test bản dịch kiểm).
- Thông báo có biến: `rpt_("... %s") % x`; không f-string, không cộng chuỗi trong `text=`, `report`, lỗi.
- Không panel DaskToon ở thanh bên viewport; thiết lập ở Properties › Object Data (spec §7).
- Không driver kiểu script; không add-on hay package ngoài (spec §1.5).
- Tên xương khung chuẩn đúng `HumanBodyBones` của Unity, tiền tố `Left`/`Right` (spec §4.1).
- Tối đa **4** weight mỗi đỉnh, bỏ weight **< 0,01**, tổng **1** (spec §6.2).
- Xương sinh mang custom property `dt_part` (spec §3).
- Test chạy: `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/<file>.py`, sau khi đồng
  bộ bản cài bằng `"$PY" tools/dasktoon_sync_build.py "$INSTALL"`.
- Mỗi task một commit, đuôi `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Không push.

## Review Focus

1. **Mesh có Mirror modifier (dựng nửa người)**: Armature phải đứng sau Mirror, nếu không thì động tay trái kéo theo tay
   phải. Test ở Task 4 (`test_bind_puts_armature_after_mirror`).
2. **Build lần hai sau khi đổi phần**: không nhân đôi xương, modifier, không còn vertex group của xương sinh cũ. Test ở
   Task 5 (`test_second_build_replaces_generated_bones`, `test_stale_generated_groups_are_removed`).
3. **Nhân vật gộp một mesh, phần theo material**: đỉnh tóc chỉ theo `Head` và xương tóc, không dính xương thân. Test ở
   Task 5 (`test_merged_mesh_by_material`).
4. **Object có scale, vị trí, cha khác**: tính ở world; làm con của rig không làm object nhảy chỗ. Test ở Task 5
   (`test_scaled_hair_object_gets_world_joints`) và Task 4 (`test_bind_keeps_world_matrix`).
5. **Bấm Build khi đang ở Pose/Edit Mode hoặc khi lỗi**: quay về mode cũ; lỗi thì không đổi gì. Test ở Task 5
   (`test_build_returns_to_pose_mode`, `test_errors_change_nothing`).

---

## Môi trường và các lệnh dùng chung

Git Bash, thư mục gốc `d:/DaskToon`, nhánh `dasktoon-anime-rig`.

```bash
DT=/d/build_windows_x64_vc17_Release/bin/Release/DaskToon.exe
INSTALL=/d/build_windows_x64_vc17_Release/bin/Release/5.2
PY=$INSTALL/python/bin/python.exe
sync() { "$PY" tools/dasktoon_sync_build.py "$INSTALL" > /dev/null; }
run() { "$DT" --background --factory-startup --python-exit-code 1 --python "tests/python/$1.py" 2>&1 | tail -25; }
```

Mỗi task: viết test → `sync; run <test>` thấy FAIL → viết code → `sync; run <test>` thấy PASS → chạy test bản dịch nếu
task thêm chữ → commit.

Đăng ký test trong `tests/python/CMakeLists.txt`: thêm tên test vào danh sách `foreach(dasktoon_test ...)`, sau dòng
`dasktoon_sun_sync_test`.

---

### Task 1: Khung xương chuẩn (`skeleton.py`)

**Files:**
- Create: `scripts/modules/dasktoon_rig/__init__.py`, `scripts/modules/dasktoon_rig/skeleton.py`
- Test: `tests/python/dasktoon_rig_skeleton_test.py`
- Modify: `tests/python/CMakeLists.txt` (thêm `dasktoon_rig_skeleton_test`),
  `tests/python/dasktoon_translations_test.py` (mẫu `scripts/modules/dasktoon_rig/*.py` trong `dasktoon_files()`, thêm
  hai file vào `TRANSLATED`)

**Interfaces:**
- Produces: `skeleton.DEFAULT_HEIGHT = 1.6`, `REQUIRED` (15 tên), `FACE_BONES = ("LeftEye", "RightEye", "Jaw")`,
  `bones() -> list[(name, parent|None, head, tail, z_axis)]`, `BONE_NAMES`, `missing_bones(armature_data) -> list[str]`,
  `is_humanoid(obj) -> bool`, `bounds(objects) -> (Vector, Vector) | None`,
  `placement(objects, fallback_location) -> (height, Vector)`, `editing(context, rig)` (context manager, yield
  `edit_bones`), `set_joints(rig, matrix, create)`, `create_humanoid(context, height, location, name="Rig") -> Object`,
  `fit(context, rig, objects) -> height`.

- [ ] **Step 1: Viết test**

**File `tests/python/dasktoon_rig_skeleton_test.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The DaskToon standard skeleton: Unity's 55 human bones, T-pose, mirrored sides, fitted to meshes (anime rig spec 4)."""

import os
import sys
import unittest

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import skeleton  # noqa: E402

UNITY_HUMAN_BONES = {
    "Hips", "LeftUpperLeg", "RightUpperLeg", "LeftLowerLeg", "RightLowerLeg", "LeftFoot", "RightFoot", "Spine",
    "Chest", "UpperChest", "Neck", "Head", "LeftShoulder", "RightShoulder", "LeftUpperArm", "RightUpperArm",
    "LeftLowerArm", "RightLowerArm", "LeftHand", "RightHand", "LeftToes", "RightToes", "LeftEye", "RightEye", "Jaw",
} | {side + finger + segment for side in ("Left", "Right")
     for finger in ("Thumb", "Index", "Middle", "Ring", "Little")
     for segment in ("Proximal", "Intermediate", "Distal")}


def box(name, low, high):
    """A mesh object filling the box low-high (world)."""
    mesh = bpy.data.meshes.new(name)
    (x0, y0, z0), (x1, y1, z1) = low, high
    verts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def world_head(rig, name):
    return rig.matrix_world @ rig.data.bones[name].head_local


def world_tail(rig, name):
    return rig.matrix_world @ rig.data.bones[name].tail_local


class TemplateTest(unittest.TestCase):
    def test_bones_are_unity_human_bones(self):
        names = [b[0] for b in skeleton.bones()]
        self.assertEqual(len(names), 55)
        self.assertEqual(set(names), UNITY_HUMAN_BONES)
        self.assertEqual(tuple(names), skeleton.BONE_NAMES)

    def test_parents_come_first(self):
        seen = set()
        for name, parent, _head, _tail, _z in skeleton.bones():
            self.assertTrue(parent is None or parent in seen, name)
            seen.add(name)

    def test_sides_mirror(self):
        table = {b[0]: b for b in skeleton.bones()}
        for name, (_n, parent, head, tail, _z) in table.items():
            if not name.startswith("Left"):
                continue
            right = table["Right" + name[4:]]
            self.assertEqual(right[1], parent if parent is None or not parent.startswith("Left")
                             else "Right" + parent[4:])
            self.assertEqual(right[2], (-head[0], head[1], head[2]))
            self.assertEqual(right[3], (-tail[0], tail[1], tail[2]))
            self.assertGreater(head[0], 0.0, name)

    def test_required_bones_are_in_the_template(self):
        self.assertEqual(len(skeleton.REQUIRED), 15)
        self.assertTrue(set(skeleton.REQUIRED) <= set(skeleton.BONE_NAMES))
        self.assertTrue(set(skeleton.FACE_BONES) <= set(skeleton.BONE_NAMES))


class CreateTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_create_humanoid(self):
        rig = skeleton.create_humanoid(bpy.context, 1.6, (1.0, 2.0, 0.0))
        self.assertEqual(len(rig.data.bones), 55)
        self.assertTrue(skeleton.is_humanoid(rig))
        self.assertTrue(rig.data.use_mirror_x)
        self.assertTrue(rig.show_in_front)
        self.assertEqual(rig.mode, 'OBJECT')
        self.assertAlmostEqual((rig.matrix_world.translation - Vector((1.0, 2.0, 0.0))).length, 0.0, places=6)
        self.assertAlmostEqual(world_tail(rig, "Head").z, 0.99 * 1.6, places=5)
        self.assertGreater(world_head(rig, "LeftHand").x, 1.0)
        self.assertLess(world_head(rig, "RightHand").x, 1.0)
        self.assertEqual(rig.data.bones["LeftUpperArm"].parent.name, "LeftShoulder")
        self.assertTrue(rig.data.bones["LeftLowerArm"].use_connect)
        self.assertFalse(rig.data.bones["LeftShoulder"].use_connect)
        self.assertIsNone(rig.data.bones["Hips"].parent)

    def test_create_keeps_the_active_object(self):
        other = box("Other", (0, 0, 0), (1, 1, 1))
        bpy.context.view_layer.objects.active = other
        skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        self.assertEqual(bpy.context.view_layer.objects.active, other)

    def test_missing_bones(self):
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        with skeleton.editing(bpy.context, rig) as edit:
            edit.remove(edit["Spine"])
            edit.remove(edit["LeftIndexDistal"])
        self.assertEqual(skeleton.missing_bones(rig.data), ["Spine"])
        self.assertFalse(skeleton.is_humanoid(rig))
        self.assertFalse(skeleton.is_humanoid(None))
        self.assertFalse(skeleton.is_humanoid(box("Mesh", (0, 0, 0), (1, 1, 1))))

    def test_placement(self):
        mesh = box("Body", (4.0, -1.0, 1.0), (6.0, 1.0, 3.0))
        height, location = skeleton.placement([mesh], (0.0, 0.0, 0.0))
        self.assertAlmostEqual(height, 2.0, places=6)
        self.assertAlmostEqual((location - Vector((5.0, 0.0, 1.0))).length, 0.0, places=6)
        height, location = skeleton.placement([], (7.0, 0.0, 0.0))
        self.assertEqual(height, skeleton.DEFAULT_HEIGHT)
        self.assertEqual(tuple(location), (7.0, 0.0, 0.0))

    def test_fit_moves_joints_not_the_object(self):
        rig = skeleton.create_humanoid(bpy.context, 1.0, (0.0, 0.0, 0.0))
        with skeleton.editing(bpy.context, rig) as edit:
            edit.remove(edit["LeftLittleDistal"])
        mesh = box("Body", (4.0, -1.0, 1.0), (6.0, 1.0, 3.0))
        self.assertAlmostEqual(skeleton.fit(bpy.context, rig, [mesh]), 2.0, places=6)
        self.assertEqual(tuple(rig.matrix_world.translation), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(world_tail(rig, "Head").z, 1.0 + 0.99 * 2.0, places=5)
        self.assertAlmostEqual(world_head(rig, "Hips").x, 5.0, places=5)
        self.assertNotIn("LeftLittleDistal", rig.data.bones)
        self.assertEqual(len(rig.data.bones), 54)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, thấy FAIL** — `sync; run dasktoon_rig_skeleton_test` → `ModuleNotFoundError: No module named 'dasktoon_rig'`.

- [ ] **Step 3: Viết code**

**File `scripts/modules/dasktoon_rig/__init__.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon anime rig (docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md): the standard skeleton, the
parts of a character and their roles, generated chains, weights and Build Rig. The interface is bl_ui/dasktoon_rig.py."""
```

**File `scripts/modules/dasktoon_rig/skeleton.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The DaskToon standard skeleton (anime rig spec 4): Unity's 55 human bones (HumanBodyBones names), in T-pose, facing
-Y with the character's left at +X and the feet at z = 0. Positions are for a character 1 tall; they are scaled to the
character's height."""

from contextlib import contextmanager

import bpy
import numpy as np
from mathutils import Matrix, Vector

DEFAULT_HEIGHT = 1.6
REQUIRED = (
    "Hips", "Spine", "Head",
    "LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand",
    "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot",
)
# Never part of the automatic body weights: the eyes and the jaw get their weights from their own parts.
FACE_BONES = ("LeftEye", "RightEye", "Jaw")

_FRONT = (0.0, -1.0, 0.0)
_UP = (0.0, 0.0, 1.0)

# (name, parent, head, tail, where the bone's Z axis points)
_CENTER = (
    ("Hips", None, (0.0, 0.0, 0.52), (0.0, 0.0, 0.58), _FRONT),
    ("Spine", "Hips", (0.0, 0.0, 0.58), (0.0, 0.0, 0.645), _FRONT),
    ("Chest", "Spine", (0.0, 0.0, 0.645), (0.0, 0.0, 0.715), _FRONT),
    ("UpperChest", "Chest", (0.0, 0.0, 0.715), (0.0, 0.0, 0.80), _FRONT),
    ("Neck", "UpperChest", (0.0, 0.0, 0.80), (0.0, -0.005, 0.85), _FRONT),
    ("Head", "Neck", (0.0, -0.005, 0.85), (0.0, -0.005, 0.99), _FRONT),
    ("Jaw", "Head", (0.0, 0.0, 0.885), (0.0, -0.06, 0.855), _UP),
)
_LEFT = (
    ("LeftEye", "Head", (0.03, -0.045, 0.915), (0.03, -0.075, 0.915), _UP),
    ("LeftShoulder", "UpperChest", (0.015, 0.0, 0.78), (0.10, 0.0, 0.78), _UP),
    ("LeftUpperArm", "LeftShoulder", (0.10, 0.0, 0.78), (0.255, 0.005, 0.78), _UP),
    ("LeftLowerArm", "LeftUpperArm", (0.255, 0.005, 0.78), (0.39, 0.0, 0.78), _UP),
    ("LeftHand", "LeftLowerArm", (0.39, 0.0, 0.78), (0.44, 0.0, 0.78), _UP),
    ("LeftThumbProximal", "LeftHand", (0.395, -0.015, 0.775), (0.41, -0.03, 0.772), _UP),
    ("LeftThumbIntermediate", "LeftThumbProximal", (0.41, -0.03, 0.772), (0.422, -0.04, 0.771), _UP),
    ("LeftThumbDistal", "LeftThumbIntermediate", (0.422, -0.04, 0.771), (0.432, -0.048, 0.77), _UP),
    ("LeftUpperLeg", "Hips", (0.05, 0.0, 0.52), (0.055, -0.005, 0.28), _FRONT),
    ("LeftLowerLeg", "LeftUpperLeg", (0.055, -0.005, 0.28), (0.06, 0.0, 0.045), _FRONT),
    ("LeftFoot", "LeftLowerLeg", (0.06, 0.0, 0.045), (0.06, -0.06, 0.012), _UP),
    ("LeftToes", "LeftFoot", (0.06, -0.06, 0.012), (0.06, -0.09, 0.012), _UP),
)
# (finger, its y, the x where it starts, length scale); every finger has three bones along +X.
_FINGERS = (("Index", -0.012, 0.44, 1.0), ("Middle", -0.004, 0.442, 1.08), ("Ring", 0.004, 0.44, 1.0),
            ("Little", 0.012, 0.436, 0.8))
_SEGMENTS = (("Proximal", 0.02), ("Intermediate", 0.015), ("Distal", 0.012))


def _fingers():
    out = []
    for finger, y, x, scale in _FINGERS:
        parent = "LeftHand"
        for segment, length in _SEGMENTS:
            name = "Left" + finger + segment
            end = x + length * scale
            out.append((name, parent, (x, y, 0.78), (end, y, 0.78), _UP))
            parent, x = name, end
    return out


def _right(name):
    return "Right" + name[4:] if name is not None and name.startswith("Left") else name


def bones():
    """Every bone of the standard skeleton, parents before children: (name, parent, head, tail, z axis)."""
    left = list(_LEFT) + _fingers()
    right = [(_right(n), _right(p), (-h[0], h[1], h[2]), (-t[0], t[1], t[2]), z) for n, p, h, t, z in left]
    return list(_CENTER) + left + right


BONE_NAMES = tuple(b[0] for b in bones())


def missing_bones(armature):
    """The REQUIRED bones that the Armature data lacks, in REQUIRED order."""
    present = armature.edit_bones if armature.is_editmode else armature.bones
    return [name for name in REQUIRED if present.get(name) is None]


def is_humanoid(obj):
    """True for an armature object with every REQUIRED bone (spec 4.2)."""
    return obj is not None and obj.type == 'ARMATURE' and not missing_bones(obj.data)


def bounds(objects):
    """(low, high) world corners around `objects` (a mesh by its vertices, anything else by its bounding box), or None
    when there is none."""
    lows, highs = [], []
    for obj in objects:
        if obj.type == 'MESH':
            if not obj.data.vertices:
                continue
            co = np.empty(len(obj.data.vertices) * 3, np.float32)
            obj.data.vertices.foreach_get("co", co)
            matrix = np.array(obj.matrix_world)
            world = co.reshape(-1, 3).astype(float) @ matrix[:3, :3].T + matrix[:3, 3]
        else:
            world = np.array([tuple(obj.matrix_world @ Vector(corner)) for corner in obj.bound_box])
        lows.append(world.min(axis=0))
        highs.append(world.max(axis=0))
    if not lows:
        return None
    return Vector(np.min(lows, axis=0)), Vector(np.max(highs, axis=0))


def placement(objects, fallback_location):
    """(height, location of the feet) of a skeleton for `objects` (spec 4.3): the height of their bounding box and the
    middle of its bottom, or DEFAULT_HEIGHT at `fallback_location`."""
    box = bounds(objects)
    if box is None or box[1].z - box[0].z < 1e-4:
        return DEFAULT_HEIGHT, Vector(fallback_location)
    low, high = box
    return high.z - low.z, Vector(((low.x + high.x) / 2.0, (low.y + high.y) / 2.0, low.z))


@contextmanager
def editing(context, rig):
    """`rig` in Edit Mode meanwhile (yields its edit bones); afterwards Object Mode and the previous active object.
    An active object in another mode is put in Object Mode first."""
    view_layer = context.view_layer
    previous = view_layer.objects.active
    if previous is not None and previous.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        yield rig.data.edit_bones
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        view_layer.objects.active = previous


def set_joints(rig, matrix, create):
    """Put the standard bones of `rig` (in Edit Mode) where the template maps through `matrix` (template to armature
    space). `create` adds missing bones and sets parents and connections; otherwise only existing bones move."""
    edit = rig.data.edit_bones
    rotation = matrix.to_3x3()
    tails = {}
    for name, parent, head, tail, z_axis in bones():
        bone = edit.get(name)
        if bone is None:
            if not create:
                continue
            bone = edit.new(name)
        bone.head = matrix @ Vector(head)
        bone.tail = matrix @ Vector(tail)
        bone.align_roll(rotation @ Vector(z_axis))
        if create:
            bone.parent = edit.get(parent) if parent else None
            bone.use_connect = parent is not None and (Vector(head) - tails[parent]).length < 1e-9
        tails[name] = Vector(tail)


def create_humanoid(context, height=DEFAULT_HEIGHT, location=(0.0, 0.0, 0.0), name="Rig"):
    """A new armature object in the active collection with the standard skeleton of a character `height` tall whose
    feet are at `location`; X-Axis Mirror on and In Front shown, for fitting the joints."""
    data = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, data)
    context.collection.objects.link(rig)
    rig.matrix_world = Matrix.Translation(location)
    rig.show_in_front = True
    data.use_mirror_x = True
    with editing(context, rig):
        set_joints(rig, Matrix.Scale(height, 4), create=True)
    return rig


def fit(context, rig, objects):
    """Move the standard bones of `rig` to the bounding box of `objects` (the object itself stays, so meshes bound to it
    do not move; bones the user deleted stay deleted). Returns the height used."""
    height, location = placement(objects, rig.matrix_world.translation)
    matrix = rig.matrix_world.inverted() @ Matrix.Translation(location) @ Matrix.Scale(height, 4)
    with editing(context, rig):
        set_joints(rig, matrix, create=False)
    return height
```

- [ ] **Step 4: Đăng ký test, mẫu file bản dịch**

`tests/python/CMakeLists.txt`: thêm `dasktoon_rig_skeleton_test` sau `dasktoon_sun_sync_test`.

`tests/python/dasktoon_translations_test.py`: thêm `"scripts/modules/dasktoon_rig/*.py"` vào bộ mẫu của
`dasktoon_files()`; thêm vào `TRANSLATED`:
```python
    "scripts/modules/dasktoon_rig/__init__.py",
    "scripts/modules/dasktoon_rig/skeleton.py",
```

- [ ] **Step 5: Chạy test, thấy PASS** — `sync; run dasktoon_rig_skeleton_test; run dasktoon_translations_test`.

- [ ] **Step 6: Commit** — `git add scripts/modules/dasktoon_rig tests/python/dasktoon_rig_skeleton_test.py tests/python/CMakeLists.txt tests/python/dasktoon_translations_test.py` rồi
  `git commit -m "feat: add the DaskToon standard skeleton (Unity human bones, T-pose, fit to meshes)"`.

---

### Task 2: Toán chuỗi tóc, váy (`chains.py`)

**Files:**
- Create: `scripts/modules/dasktoon_rig/chains.py`
- Test: `tests/python/dasktoon_rig_chains_test.py`
- Modify: `tests/python/CMakeLists.txt`, `tests/python/dasktoon_translations_test.py` (`TRANSLATED` += `chains.py`)

**Interfaces:**
- Produces: `segment_distance(points, head, tail) -> ndarray(n)`, `components(count, edges) -> list[ndarray]`,
  `geodesic(points, edges, seeds) -> ndarray(n)`, `tent(u, count) -> ndarray(n, count+1)`,
  `Chain(joints (count+1, 3), weights (n, count+1))`, `is_long(points) -> bool`,
  `hair_chain(points, edges, attach_head, attach_tail, count) -> Chain | None`, `strip_angle(index, strips) -> float`, `Skirt(strips: list[ndarray (count+1, 3) | None], weights (n,
  1 + strips*count))`, `skirt_chains(points, count, strips) -> Skirt`. `edges` là mảng `(m, 2)` chỉ số trong `points`.

- [ ] **Step 1: Viết test**

**File `tests/python/dasktoon_rig_chains_test.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Chains of the anime rig as plain maths: geodesic distance, hair lock joints and weights, skirt strips (spec 6.3,
6.4)."""

import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import chains  # noqa: E402


def ribbon(path, width=0.04):
    """Points and edges of a ribbon two vertices wide along `path` (list of xyz), offset along X."""
    points, edges = [], []
    for i, (x, y, z) in enumerate(path):
        points += [(x - width / 2, y, z), (x + width / 2, y, z)]
        edges.append((2 * i, 2 * i + 1))
        if i:
            edges += [(2 * i - 2, 2 * i), (2 * i - 1, 2 * i + 1), (2 * i - 2, 2 * i + 1)]
    return np.array(points, float), np.array(edges, np.int64)


def straight(rings=20, top=1.0, bottom=0.5):
    return ribbon([(0.0, 0.0, top + (bottom - top) * r / rings) for r in range(rings + 1)])


def cone(rings=6, segments=16, top=0.5, bottom=0.2, r_top=0.1, r_bottom=0.2, start=0.0, sweep=2 * math.pi):
    points = []
    for r in range(rings + 1):
        t = r / rings
        radius = r_top + (r_bottom - r_top) * t
        for s in range(segments):
            a = start + sweep * s / segments
            points.append((radius * math.cos(a), radius * math.sin(a), top + (bottom - top) * t))
    return np.array(points, float)


class BasicsTest(unittest.TestCase):
    def test_segment_distance(self):
        points = np.array([(0.0, 0.0, 0.5), (1.0, 0.0, 0.5), (0.0, 0.0, 2.0)])
        d = chains.segment_distance(points, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        np.testing.assert_allclose(d, [0.0, 1.0, 1.0])

    def test_components(self):
        found = chains.components(5, np.array([(0, 1), (3, 4)]))
        self.assertEqual([c.tolist() for c in found], [[0, 1], [2], [3, 4]])

    def test_geodesic_walks_the_edges(self):
        points = np.array([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (5.0, 5.0, 0.0)])
        d = chains.geodesic(points, np.array([(0, 1), (1, 2)]), [0])
        np.testing.assert_allclose(d[:3], [0.0, 1.0, 2.0])
        self.assertTrue(math.isinf(d[3]))

    def test_tent_rows_sum_to_one_and_peak_at_their_bone(self):
        w = chains.tent(np.array([0.0, 0.5, 1.0, 2.5, 4.0, 5.0]), 4)
        np.testing.assert_allclose(w.sum(axis=1), 1.0)
        np.testing.assert_allclose(w[0], [1, 0, 0, 0, 0])
        np.testing.assert_allclose(w[1], [0.5, 0.5, 0, 0, 0])
        np.testing.assert_allclose(w[3], [0, 0, 0.5, 0.5, 0])
        np.testing.assert_allclose(w[4], [0, 0, 0, 0, 1])
        np.testing.assert_allclose(w[5], [0, 0, 0, 0, 1])


class HairTest(unittest.TestCase):
    HEAD = ((0.0, 0.0, 1.0), (0.0, 0.0, 1.3))

    def test_straight_lock(self):
        points, edges = straight()
        chain = chains.hair_chain(points, edges, *self.HEAD, 4)
        self.assertEqual(chain.joints.shape, (5, 3))
        self.assertTrue(np.all(np.diff(chain.joints[:, 2]) < 0.0))
        self.assertTrue(0.9 <= chain.joints[0, 2] <= 1.0, chain.joints[0])
        self.assertLess(chain.joints[4, 2], 0.53)
        np.testing.assert_allclose(chain.joints[:, 0], 0.0, atol=1e-9)
        np.testing.assert_allclose(chain.weights.sum(axis=1), 1.0)
        np.testing.assert_allclose(chain.weights[0], [1, 0, 0, 0, 0])
        self.assertEqual(int(np.argmax(chain.weights[-1])), 4)

    def test_curved_lock_follows_the_curve(self):
        arc = [(0.0, 0.3 * math.sin(a), 1.0 - 0.3 + 0.3 * math.cos(a))
               for a in np.linspace(0.0, math.pi / 2, 21)]
        points, edges = ribbon(arc, width=0.02)
        chain = chains.hair_chain(points, edges, *self.HEAD, 4)
        centre = np.array([0.0, 0.0, 0.7])
        radii = np.linalg.norm(chain.joints[:, 1:] - centre[1:], axis=1)
        np.testing.assert_allclose(radii, 0.3, atol=0.01)
        self.assertGreater(chain.joints[4, 1], 0.29)

    def test_short_wide_piece_is_rigid(self):
        grid = [(x, 0.0, z) for z in np.linspace(1.0, 0.9, 5) for x in np.linspace(-0.05, 0.05, 5)]
        points = np.array(grid, float)
        edges = [(r * 5 + c, r * 5 + c + 1) for r in range(5) for c in range(4)]
        edges += [(r * 5 + c, (r + 1) * 5 + c) for r in range(4) for c in range(5)]
        self.assertIsNone(chains.hair_chain(points, np.array(edges), *self.HEAD, 4))

    def test_too_few_vertices(self):
        points = np.array([(0.0, 0.0, 1.0), (0.0, 0.0, 0.5), (0.0, 0.0, 0.2)])
        self.assertIsNone(chains.hair_chain(points, np.array([(0, 1), (1, 2)]), *self.HEAD, 4))


class SkirtTest(unittest.TestCase):
    def test_full_skirt(self):
        points = cone()
        skirt = chains.skirt_chains(points, 3, 8)
        self.assertEqual(len(skirt.strips), 8)
        self.assertTrue(all(s is not None for s in skirt.strips))
        front = skirt.strips[0]
        self.assertAlmostEqual(front[0, 0], 0.0, places=6)
        self.assertLess(front[0, 1], 0.0)
        self.assertAlmostEqual(front[0, 2], 0.5, places=6)
        self.assertAlmostEqual(front[3, 2], 0.2, places=6)
        radii = np.linalg.norm(front[:, :2], axis=1)
        self.assertTrue(np.all(np.diff(radii) > 0.0))
        self.assertAlmostEqual(radii[0], 0.1, delta=0.01)
        self.assertAlmostEqual(radii[3], 0.2, delta=0.01)
        left = skirt.strips[2]  # strip 2 of 8 is 90 degrees counter-clockwise from the front: +X, the left side
        self.assertGreater(left[1, 0], 0.1)
        self.assertEqual(skirt.weights.shape, (len(points), 1 + 8 * 3))
        np.testing.assert_allclose(skirt.weights.sum(axis=1), 1.0)
        bottom_left = int(np.argmin(np.linalg.norm(points - (0.2, 0.0, 0.2), axis=1)))
        self.assertAlmostEqual(skirt.weights[bottom_left, 1 + 2 * 3 + 2], 1.0, places=6)
        top = int(np.argmin(np.linalg.norm(points - (0.1, 0.0, 0.5), axis=1)))
        self.assertAlmostEqual(skirt.weights[top, 0], 1.0, places=6)

    def test_front_panel_only(self):
        points = cone(start=-math.pi, sweep=math.pi * 15 / 16)
        skirt = chains.skirt_chains(points, 3, 8)
        self.assertIsNotNone(skirt.strips[0])
        self.assertIsNone(skirt.strips[4])  # the back
        np.testing.assert_allclose(skirt.weights[:, 1 + 4 * 3:1 + 5 * 3], 0.0)
        np.testing.assert_allclose(skirt.weights.sum(axis=1), 1.0)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, thấy FAIL** — `sync; run dasktoon_rig_chains_test` → `ImportError: cannot import name 'chains'`.

- [ ] **Step 3: Viết code**

**File `scripts/modules/dasktoon_rig/chains.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The maths of generated chains (anime rig spec 6.3, 6.4) on plain numpy arrays, so it is tested without meshes:
geodesic distance along edges, the joints and weights of a hair lock, and the strips of a skirt."""

import heapq
import math

import numpy as np

ROOT_SHARE = 0.10   # vertices this close (share of the distance range) to the attach bone lie on the head: the root
SHORT = 1.5         # a piece whose main spread is under SHORT times its second spread is wide: no chain
TIP_SHARE = 0.05    # the tip joint is the centre of this share of the farthest vertices
MIN_VERTICES = 4


def segment_distance(points, head, tail):
    """Distance of each point (n x 3) to the segment head-tail."""
    points = np.asarray(points, float)
    head, tail = np.asarray(head, float), np.asarray(tail, float)
    axis = tail - head
    length2 = float(axis @ axis)
    if length2 < 1e-18:
        return np.linalg.norm(points - head, axis=1)
    t = np.clip((points - head) @ axis / length2, 0.0, 1.0)
    return np.linalg.norm(points - (head + t[:, None] * axis), axis=1)


def components(count, edges):
    """Connected components of a graph of `count` vertices: sorted index arrays, ordered by their first vertex."""
    parent = list(range(count))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in np.asarray(edges, np.int64).reshape(-1, 2).tolist():
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    roots = np.array([find(i) for i in range(count)], np.int64)
    return [np.nonzero(roots == r)[0] for r in np.unique(roots)]


def geodesic(points, edges, seeds):
    """Shortest distance from any of `seeds` to every vertex walking along `edges` (inf where unreachable)."""
    points = np.asarray(points, float)
    edges = np.asarray(edges, np.int64).reshape(-1, 2)
    lengths = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1).tolist()
    neighbours = [[] for _ in range(len(points))]
    for (a, b), length in zip(edges.tolist(), lengths):
        neighbours[a].append((b, length))
        neighbours[b].append((a, length))
    dist = [math.inf] * len(points)
    heap = []
    for seed in seeds:
        dist[int(seed)] = 0.0
        heap.append((0.0, int(seed)))
    heapq.heapify(heap)
    while heap:
        d, v = heapq.heappop(heap)
        if d > dist[v]:
            continue
        for w, length in neighbours[v]:
            nd = d + length
            if nd < dist[w]:
                dist[w] = nd
                heapq.heappush(heap, (nd, w))
    return np.array(dist)


def tent(u, count):
    """Weights (n x count+1) along a chain for positions u in [0, count]: column 0 (the attach bone) peaks at u = 0
    and column j (the j-th chain bone) at u = j; each row sums to 1."""
    u = np.clip(np.asarray(u, float), 0.0, count)
    w = np.maximum(0.0, 1.0 - np.abs(u[:, None] - np.arange(count + 1)[None, :]))
    return w / w.sum(axis=1, keepdims=True)


class Chain:
    """One lock: joints (count+1 x 3) from root to tip, and weights (n x count+1, column 0 for the attach bone)."""

    def __init__(self, joints, weights):
        self.joints = joints
        self.weights = weights


def _fill(rows):
    """`rows` with the rows that are nan interpolated from the known rows around them."""
    known = np.nonzero(~np.isnan(rows[:, 0]))[0]
    for axis in range(rows.shape[1]):
        rows[:, axis] = np.interp(np.arange(len(rows)), known, rows[known, axis])
    return rows


def is_long(points):
    """True when the points spread at least SHORT times more along their main axis than along the second one."""
    centred = points - points.mean(axis=0)
    _values, vectors = np.linalg.eigh(centred.T @ centred)
    main, second = (float(np.ptp(centred @ vectors[:, i])) for i in (2, 1))
    return main >= SHORT * second


def hair_chain(points, edges, attach_head, attach_tail, count):
    """The chain of one lock (spec 6.3), or None for a piece that is too small or too wide for one. The root (vertices
    close to the attach bone, lying on the head) follows the attach bone; joint 0 is the middle of the root's rim."""
    points = np.asarray(points, float)
    if len(points) < MIN_VERTICES or not is_long(points):
        return None
    edges = np.asarray(edges, np.int64).reshape(-1, 2)
    near = segment_distance(points, attach_head, attach_tail)
    seeds = near <= near.min() + ROOT_SHARE * (near.max() - near.min()) + 1e-12
    dist = geodesic(points, edges, np.nonzero(seeds)[0])
    reached = np.isfinite(dist)
    dist[~reached] = dist[reached].max()
    length = float(dist.max())
    if length <= 1e-9:
        return None
    rim = np.zeros(len(points), bool)
    rim[edges[seeds[edges[:, 0]] != seeds[edges[:, 1]]].ravel()] = True
    rim &= seeds
    u = dist / length * count
    joints = np.full((count + 1, 3), np.nan)
    joints[0] = points[rim if rim.any() else seeds].mean(axis=0)
    joints[count] = points[np.argsort(dist)[-max(1, int(round(TIP_SHARE * len(points)))):]].mean(axis=0)
    for k in range(1, count):
        band = np.abs(u - k) <= 0.25
        if band.any():
            joints[k] = points[band].mean(axis=0)
    return Chain(_fill(joints), tent(u, count))


def strip_angle(index, strips):
    """Angle around the vertical axis of skirt strip `index`: strip 0 at the front (-Y), then counter-clockwise seen
    from above (towards the character's left, +X)."""
    return -math.pi / 2.0 + 2.0 * math.pi * index / strips


class Skirt:
    """Skirt strips: their joints (count+1 x 3, None for a strip with no vertex near it) and the weights (n x 1 +
    strips*count): column 0 for the attach bone, then strip c bone k (1..count) in column 1 + c*count + k-1."""

    def __init__(self, strips, weights):
        self.strips = strips
        self.weights = weights


def skirt_chains(points, count, strips):
    """`strips` strips of `count` bones around the vertical axis through the middle of `points` (spec 6.4)."""
    points = np.asarray(points, float)
    low, high = points.min(axis=0), points.max(axis=0)
    centre = (low[:2] + high[:2]) / 2.0
    top, height = float(high[2]), max(float(high[2] - low[2]), 1e-9)
    rel = points[:, :2] - centre
    radius = np.linalg.norm(rel, axis=1)
    u = (top - points[:, 2]) / height * count
    step = 2.0 * math.pi / strips
    a = np.mod(np.arctan2(rel[:, 1], rel[:, 0]) - strip_angle(0, strips), 2.0 * math.pi) / step
    lower = np.floor(a).astype(np.int64) % strips
    upper = (lower + 1) % strips
    frac = a - np.floor(a)
    nearest = np.where(frac < 0.5, lower, upper)
    used = np.zeros(strips, bool)
    used[np.unique(nearest)] = True
    level = np.rint(np.clip(u, 0.0, count)).astype(np.int64)
    out = []
    for c in range(strips):
        if not used[c]:
            out.append(None)
            continue
        radii = np.full((count + 1, 1), np.nan)
        for k in range(count + 1):
            here = (nearest == c) & (level == k)
            ring = here if here.any() else level == k
            if ring.any():
                radii[k, 0] = radius[ring].mean()
        radii = _fill(radii)[:, 0]
        theta = strip_angle(c, strips)
        out.append(np.array([(centre[0] + radii[k] * math.cos(theta), centre[1] + radii[k] * math.sin(theta),
                              top - k * height / count) for k in range(count + 1)]))
    along = tent(u, count)
    share_lower = np.where(used[upper], 1.0 - frac, 1.0)
    share_upper = np.where(used[upper], frac, 0.0)
    share_upper = np.where(used[lower], share_upper, 1.0)
    share_lower = np.where(used[lower], share_lower, 0.0)
    weights = np.zeros((len(points), 1 + strips * count))
    weights[:, 0] = along[:, 0]
    rows = np.arange(len(points))
    for k in range(1, count + 1):
        np.add.at(weights, (rows, 1 + lower * count + k - 1), share_lower * along[:, k])
        np.add.at(weights, (rows, 1 + upper * count + k - 1), share_upper * along[:, k])
    return Skirt(out, weights)
```

- [ ] **Step 4: Đăng ký** — CMake thêm `dasktoon_rig_chains_test`; `TRANSLATED` thêm
  `"scripts/modules/dasktoon_rig/chains.py"`.

- [ ] **Step 5: Chạy test, thấy PASS** — `sync; run dasktoon_rig_chains_test; run dasktoon_translations_test`.

- [ ] **Step 6: Commit** — `git commit -m "feat: compute hair and skirt chains for the anime rig"`.

---

### Task 3: Phần và vai trò (`parts.py`), nhân vật thử

**Files:**
- Create: `scripts/modules/dasktoon_rig/parts.py`, `tests/python/dasktoon_rig_fixtures.py` (module dùng chung, không
  phải test)
- Test: `tests/python/dasktoon_rig_parts_test.py`
- Modify: `tests/python/CMakeLists.txt`, `tests/python/dasktoon_translations_test.py` (`TRANSLATED` += `parts.py`),
  `scripts/startup/bl_ui/dasktoon_translations.py` (3 thông báo)

**Interfaces:**
- Consumes: `chains.components`, `chains.segment_distance`, `skeleton.bounds`.
- Produces: `ROLES`, `CHAIN_ROLES`, `DEFAULT_BONE`, `DEFAULT_BONE_COUNT`, `BONE_COUNT`, `CHAIN_COUNT`, `PartError`,
  `Part(name, obj, role='BODY', scope='OBJECT', material="", vertex_group="", bone="", bone_count=None,
  chain_count=8)`, `words(name)`, `ascii_name(name)`, `guess_role(name) -> str | None`,
  `initial_roles(objects, has_body=False) -> {obj: role}`, `mesh_arrays(obj) -> (world (n,3), edges (m,2))`,
  `part_vertices(part) -> ndarray`, `local_edges(edges, vertices)`, `pieces(edges, vertices) -> list[ndarray]`,
  `bone_segment(rig, name) -> (ndarray, ndarray)`, `nearest_bone(rig, point, names) -> str`.
- Fixtures: `HEIGHT = 1.6`, `mesh_object(name, verts, faces, materials=(), face_materials=None)`, `tube(...)`,
  `strip(...)`, `cube(centre, size)`, `combine(name, pieces)`, `character(merged=False) -> dict`, `rig_for(character)
  -> rig`.

- [ ] **Step 1: Viết nhân vật thử**

**File `tests/python/dasktoon_rig_fixtures.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Test characters for the anime rig (not a test): simple meshes around the standard skeleton of a character HEIGHT
tall, as separate objects or as one mesh with a material per piece. Sizes are in units of the height."""

import math

import bpy

HEIGHT = 1.6


def mesh_object(name, verts, faces, materials=(), face_materials=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    for mat_name in materials:
        mesh.materials.append(bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name))
    if face_materials is not None:
        mesh.polygons.foreach_set("material_index", face_materials)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def tube(z_top, z_bottom, r_top, r_bottom, rings=12, segments=16):
    """(verts, faces) of an open tube around the Z axis from z_top down to z_bottom; vertex s of a ring is at angle
    360 * s / segments degrees from +X (s = 12 of 16 is the front, -Y)."""
    verts, faces = [], []
    for r in range(rings + 1):
        t = r / rings
        z = (z_top + (z_bottom - z_top) * t) * HEIGHT
        radius = (r_top + (r_bottom - r_top) * t) * HEIGHT
        for s in range(segments):
            a = 2.0 * math.pi * s / segments
            verts.append((radius * math.cos(a), radius * math.sin(a), z))
    for r in range(rings):
        for s in range(segments):
            a, b = r * segments + s, r * segments + (s + 1) % segments
            faces.append((a, b, b + segments, a + segments))
    return verts, faces


def strip(top, bottom, width, rings=10):
    """(verts, faces) of a ribbon from `top` to `bottom` (xyz), `width` wide along X; the first ring is the top."""
    verts, faces = [], []
    for r in range(rings + 1):
        t = r / rings
        x, y, z = (top[i] + (bottom[i] - top[i]) * t for i in range(3))
        verts += [((x - width / 2) * HEIGHT, y * HEIGHT, z * HEIGHT), ((x + width / 2) * HEIGHT, y * HEIGHT, z * HEIGHT)]
    for r in range(rings):
        faces.append((2 * r, 2 * r + 1, 2 * r + 3, 2 * r + 2))
    return verts, faces


def cube(centre, size):
    (cx, cy, cz), h = centre, size / 2
    verts = [((cx + dx * h) * HEIGHT, (cy + dy * h) * HEIGHT, (cz + dz * h) * HEIGHT)
             for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return verts, faces


PIECES = (
    ("Body", lambda: tube(0.86, 0.05, 0.07, 0.07, rings=24)),
    ("Shirt", lambda: tube(0.78, 0.60, 0.08, 0.08, rings=6)),
    ("Hair", lambda: strip((0.0, 0.06, 0.96), (0.0, 0.10, 0.62), 0.04)),
    ("Skirt", lambda: tube(0.53, 0.36, 0.08, 0.13, rings=6)),
    ("Ribbon", lambda: cube((0.0, 0.07, 0.97), 0.02)),
    ("Eye", lambda: cube((0.03, -0.06, 0.915), 0.01)),
)


def combine(name, pieces):
    """One mesh object of (verts, faces, material name) pieces, a material slot per piece."""
    verts, faces, face_materials, materials = [], [], [], []
    for piece_verts, piece_faces, material in pieces:
        offset = len(verts)
        verts += piece_verts
        faces += [tuple(i + offset for i in f) for f in piece_faces]
        face_materials += [len(materials)] * len(piece_faces)
        materials.append(material)
    return mesh_object(name, verts, faces, materials, face_materials)


def character(merged=False):
    """{piece name: object}, or {"Character": object} with materials named after the pieces when `merged`."""
    if merged:
        return {"Character": combine("Character", [(*make(), name) for name, make in PIECES])}
    return {name: mesh_object(name, *make()) for name, make in PIECES}


def rig_for(context=None):
    from dasktoon_rig import skeleton
    return skeleton.create_humanoid(context or bpy.context, HEIGHT, (0.0, 0.0, 0.0))
```

- [ ] **Step 2: Viết test**

**File `tests/python/dasktoon_rig_parts_test.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Parts of the anime rig: role from a name, the vertices of a part, loose pieces, nearest bone (spec 5)."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import parts  # noqa: E402


class NameTest(unittest.TestCase):
    def test_words(self):
        self.assertEqual(parts.words("TwinTails_01"), ["twin", "tails"])
        self.assertEqual(parts.words("HairBack.001"), ["hair", "back"])
        self.assertEqual(parts.words("T\u00f3c m\u00e1i"), ["toc", "mai"])
        self.assertEqual(parts.ascii_name("T\u00f3c m\u00e1i 2"), "Tocmai2")
        self.assertEqual(parts.ascii_name("!!"), "Part")

    def test_guess_role(self):
        cases = {
            "Hair.001": 'HAIR', "T\u00f3c": 'HAIR', "Ponytail": 'HAIR', "\u9aea": 'HAIR', "CatTail": 'HAIR',
            "Skirt": 'SKIRT', "V\u00e1y": 'SKIRT', "Eye_L": 'ACCESSORY', "Hat": 'ACCESSORY', "Shirt": 'CLOTHING',
            "Body": 'BODY', "Face": 'BODY', "Chatty": None, "Mesh": None,
        }
        for name, role in cases.items():
            self.assertEqual(parts.guess_role(name), role, name)

    def test_initial_roles(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        tall = fx.mesh_object("A", *fx.tube(0.9, 0.0, 0.1, 0.1))
        short = fx.mesh_object("B", *fx.tube(0.5, 0.4, 0.1, 0.1))
        hair = fx.mesh_object("Hair", *fx.strip((0, 0, 1), (0, 0, 0.5), 0.04))
        self.assertEqual(parts.initial_roles([short, tall, hair]), {tall: 'BODY', short: 'CLOTHING', hair: 'HAIR'})
        self.assertEqual(parts.initial_roles([short, tall], has_body=True), {tall: 'CLOTHING', short: 'CLOTHING'})

    def test_part_defaults(self):
        self.assertEqual(parts.Part("S", None, role='SKIRT').bone_count, 3)
        self.assertEqual(parts.Part("H", None, role='HAIR').bone_count, 4)


class VerticesTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.obj = fx.character(merged=True)["Character"]
        self.counts = {name: len(make()[0]) for name, make in fx.PIECES}

    def test_whole_object(self):
        found = parts.part_vertices(parts.Part("All", self.obj))
        self.assertEqual(len(found), len(self.obj.data.vertices))

    def test_by_material(self):
        found = parts.part_vertices(parts.Part("Hair", self.obj, scope='MATERIAL', material="Hair"))
        start = self.counts["Body"] + self.counts["Shirt"]
        np.testing.assert_array_equal(found, np.arange(start, start + self.counts["Hair"]))

    def test_by_vertex_group(self):
        group = self.obj.vertex_groups.new(name="DT_Some")
        group.add([3, 5, 7], 1.0, 'REPLACE')
        group.add([9], 0.0, 'REPLACE')
        found = parts.part_vertices(parts.Part("Some", self.obj, scope='VERTEX_GROUP', vertex_group="DT_Some"))
        self.assertEqual(found.tolist(), [3, 5, 7])

    def test_errors(self):
        with self.assertRaises(parts.PartError):
            parts.part_vertices(parts.Part("X", self.obj, scope='MATERIAL', material="Nope"))
        with self.assertRaises(parts.PartError):
            parts.part_vertices(parts.Part("X", self.obj, scope='VERTEX_GROUP', vertex_group="Nope"))
        self.obj.vertex_groups.new(name="Empty")
        with self.assertRaises(parts.PartError):
            parts.part_vertices(parts.Part("X", self.obj, scope='VERTEX_GROUP', vertex_group="Empty"))

    def test_pieces(self):
        world, edges = parts.mesh_arrays(self.obj)
        self.assertEqual(len(parts.pieces(edges, np.arange(len(world)))), len(fx.PIECES))
        hair = parts.part_vertices(parts.Part("Hair", self.obj, scope='MATERIAL', material="Hair"))
        found = parts.pieces(edges, hair)
        self.assertEqual(len(found), 1)
        np.testing.assert_array_equal(found[0], hair)

    def test_mesh_arrays_are_world(self):
        self.obj.location = (1.0, 0.0, 0.0)
        self.obj.scale = (2.0, 2.0, 2.0)
        bpy.context.view_layer.update()
        world, _edges = parts.mesh_arrays(self.obj)
        local = np.array(self.obj.data.vertices[0].co)
        np.testing.assert_allclose(world[0], local * 2.0 + (1.0, 0.0, 0.0), atol=1e-6)


class BoneTest(unittest.TestCase):
    def test_nearest_bone(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        rig = fx.rig_for()
        eye = np.array([0.03, -0.06, 0.915]) * fx.HEIGHT
        self.assertEqual(parts.nearest_bone(rig, eye, ["Head", "LeftEye", "RightEye"]), "LeftEye")
        head, tail = parts.bone_segment(rig, "Head")
        np.testing.assert_allclose(tail, np.array([0.0, -0.005, 0.99]) * fx.HEIGHT, atol=1e-6)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 3: Chạy test, thấy FAIL** — `sync; run dasktoon_rig_parts_test` → `cannot import name 'parts'`.

- [ ] **Step 4: Viết code**

**File `scripts/modules/dasktoon_rig/parts.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Parts of a character (anime rig spec 5): the vertices of a part, its loose pieces, the role its name suggests and
the bones it hangs from. Positions are world space at rest: mesh coordinates without shape keys or modifiers."""

import re
import unicodedata

import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_

from . import chains, skeleton

ROLES = ('BODY', 'CLOTHING', 'ACCESSORY', 'HAIR', 'SKIRT')  # a later role wins a vertex (spec 5.2)
CHAIN_ROLES = ('HAIR', 'SKIRT')
DEFAULT_BONE = {'HAIR': "Head", 'SKIRT': "Hips"}
BONE_COUNT = 4
DEFAULT_BONE_COUNT = {'SKIRT': 3}
CHAIN_COUNT = 8
WORDS = (
    ('HAIR', {"hair", "bang", "bangs", "fringe", "ponytail", "twintail", "twintails", "tail", "tails", "ahoge",
              "braid", "toc", "kami"}),
    ('SKIRT', {"skirt", "vay"}),
    ('ACCESSORY', {"eye", "eyes", "eyeball", "glass", "glasses", "ribbon", "hairpin", "clip", "earring", "hat",
                   "cap", "bow"}),
    ('CLOTHING', {"cloth", "clothes", "shirt", "tshirt", "jacket", "coat", "dress", "pant", "pants", "shoe",
                  "shoes", "sock", "socks", "glove", "gloves", "uniform"}),
    ('BODY', {"body", "skin", "face", "head"}),
)
MARKS = (('HAIR', "\u9aea"), ('SKIRT', "\u30b9\u30ab\u30fc\u30c8"), ('ACCESSORY', "\u76ee"), ('CLOTHING', "\u670d"),
         ('BODY', "\u4f53"))


class PartError(Exception):
    """Why a part cannot be used, worded for the user."""


class Part:
    """A part outside Blender data (tests, scripts); the interface passes DaskRigPart items with the same fields."""

    def __init__(self, name, obj, role='BODY', scope='OBJECT', material="", vertex_group="", bone="",
                 bone_count=None, chain_count=CHAIN_COUNT):
        self.name = name
        self.object = obj
        self.role = role
        self.scope = scope
        self.material = material
        self.vertex_group = vertex_group
        self.bone = bone
        self.bone_count = DEFAULT_BONE_COUNT.get(role, BONE_COUNT) if bone_count is None else bone_count
        self.chain_count = chain_count


def _plain(name):
    """`name` with accents dropped (the Vietnamese d with stroke becomes d)."""
    name = name.replace(chr(0x111), "d").replace(chr(0x110), "D")
    return "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))


def words(name):
    """Lower-case words of a name: split at anything but a letter and where lower case turns to upper case."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", _plain(name))
    return [w.lower() for w in re.split(r"[^A-Za-z]+", spaced) if w]


def ascii_name(name):
    """The ASCII letters and digits of a name (accents dropped), or "Part": the start of generated bone names."""
    return re.sub(r"[^A-Za-z0-9]+", "", _plain(name)) or "Part"


def guess_role(name):
    """The role a name suggests (spec 5.3), or None; the first role of WORDS that matches wins."""
    found = set(words(name))
    for role, keys in WORDS:
        if found & keys:
            return role
    for role, mark in MARKS:
        if mark in name:
            return role
    return None


def _height(obj):
    box = skeleton.bounds([obj])
    return box[1].z - box[0].z if box else 0.0


def initial_roles(objects, has_body=False):
    """{object: role} for new whole-object parts: the role the name suggests; otherwise the tallest object is the Body
    when the rig has none yet, and the rest Clothing (spec 5.3)."""
    roles = {obj: guess_role(obj.name) for obj in objects}
    if not has_body and 'BODY' not in roles.values():
        unknown = [obj for obj in objects if roles[obj] is None]
        if unknown:
            roles[max(unknown, key=_height)] = 'BODY'
    return {obj: role or 'CLOTHING' for obj, role in roles.items()}


def mesh_arrays(obj):
    """(world positions n x 3, edges m x 2) of the vertices of obj's mesh, without shape keys or modifiers."""
    mesh = obj.data
    co = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", co)
    edges = np.empty(len(mesh.edges) * 2, np.int32)
    mesh.edges.foreach_get("vertices", edges)
    matrix = np.array(obj.matrix_world)
    world = co.reshape(-1, 3).astype(float) @ matrix[:3, :3].T + matrix[:3, 3]
    return world, edges.reshape(-1, 2).astype(np.int64)


def part_vertices(part):
    """Sorted indices of the vertices of `part` on its mesh (spec 5.1); PartError when there is none."""
    obj = part.object
    mesh = obj.data
    if part.scope == 'MATERIAL':
        slots = [i for i, slot in enumerate(obj.material_slots)
                 if slot.material is not None and slot.material.name == part.material]
        if not slots:
            raise PartError(rpt_("Part %s: material %s is not on %s") % (part.name, part.material, obj.name))
        face_material = np.empty(len(mesh.polygons), np.int32)
        mesh.polygons.foreach_get("material_index", face_material)
        sizes = np.empty(len(mesh.polygons), np.int32)
        mesh.polygons.foreach_get("loop_total", sizes)
        corners = np.empty(len(mesh.loops), np.int32)
        mesh.loops.foreach_get("vertex_index", corners)
        found = np.unique(corners[np.repeat(np.isin(face_material, slots), sizes)]).astype(np.int64)
    elif part.scope == 'VERTEX_GROUP':
        group = obj.vertex_groups.get(part.vertex_group)
        if group is None:
            raise PartError(rpt_("Part %s: vertex group %s is not on %s") % (part.name, part.vertex_group, obj.name))
        index = group.index
        found = np.array([v.index for v in mesh.vertices
                          if any(g.group == index and g.weight > 0.0 for g in v.groups)], np.int64)
    else:
        found = np.arange(len(mesh.vertices), dtype=np.int64)
    if len(found) == 0:
        raise PartError(rpt_("Part %s has no vertices") % part.name)
    return found


def local_edges(edges, vertices):
    """The edges with both ends in `vertices`, renumbered as positions in `vertices`."""
    if len(edges) == 0 or len(vertices) == 0:
        return np.zeros((0, 2), np.int64)
    local = np.full(max(int(vertices.max()), int(edges.max())) + 1, -1, np.int64)
    local[vertices] = np.arange(len(vertices))
    a, b = local[edges[:, 0]], local[edges[:, 1]]
    keep = (a >= 0) & (b >= 0)
    return np.stack([a[keep], b[keep]], axis=1)


def pieces(edges, vertices):
    """The loose pieces of `vertices`: sorted arrays of mesh vertex indices, joined by edges inside `vertices`."""
    return [vertices[c] for c in chains.components(len(vertices), local_edges(edges, vertices))]


def bone_segment(rig, name):
    """World (head, tail) of a bone of `rig` at rest."""
    bone = rig.data.bones[name]
    return np.array(rig.matrix_world @ bone.head_local), np.array(rig.matrix_world @ bone.tail_local)


def nearest_bone(rig, point, names):
    """The name in `names` of the bone of `rig` nearest to the world `point` (the first one on a tie)."""
    point = np.asarray(point, float)[None, :]
    best, best_distance = None, None
    for name in names:
        distance = float(chains.segment_distance(point, *bone_segment(rig, name))[0])
        if best_distance is None or distance < best_distance - 1e-12:
            best, best_distance = name, distance
    return best
```

- [ ] **Step 5: Bản dịch** — thêm vào cuối `VI` trong `dasktoon_translations.py`:
```python
    # dasktoon_rig/parts.py
    "Part %s: material %s is not on %s": "Phần %s: material %s không có trên %s",
    "Part %s: vertex group %s is not on %s": "Phần %s: vertex group %s không có trên %s",
    "Part %s has no vertices": "Phần %s không có đỉnh nào",
```

- [ ] **Step 6: Đăng ký** — CMake `dasktoon_rig_parts_test`; `TRANSLATED` += `"scripts/modules/dasktoon_rig/parts.py"`.

- [ ] **Step 7: Chạy test, thấy PASS** — `sync; run dasktoon_rig_parts_test; run dasktoon_translations_test`.

- [ ] **Step 8: Commit** — `git commit -m "feat: anime rig parts (vertices by object, material or vertex group, roles from names)"`.

---

### Task 4: Weight (`weights.py`)

**Files:**
- Create: `scripts/modules/dasktoon_rig/weights.py`
- Test: `tests/python/dasktoon_rig_weights_test.py`
- Modify: `tests/python/CMakeLists.txt`, `tests/python/dasktoon_translations_test.py` (`TRANSLATED` += `weights.py`)

**Interfaces:**
- Consumes: `parts.mesh_arrays`, `parts.bone_segment`, `chains.segment_distance`.
- Produces: `LIMIT = 4`, `MINIMUM = 0.01`, `read(obj, names) -> ndarray(n, len(names))`, `clear(obj, vertices, names)`,
  `write(obj, vertices, names, matrix)` (không xóa trước; cột 0 bỏ qua), `tidy(matrix) -> ndarray`,
  `bind(rig, obj)`, `body_heat(context, rig, obj, body_bones)`, `surface_weights(sources, names, points)` với
  `sources = [(obj, vertex_mask)]`, `nearest_bone_weights(rig, names, points)`.

- [ ] **Step 1: Viết test**

**File `tests/python/dasktoon_rig_weights_test.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Weights of the anime rig: matrices in and out of vertex groups, the Unity clean-up, binding, bone heat, weights
copied from a surface (spec 5.2, 6.2, 12)."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import weights  # noqa: E402


def plane(name, size=1.0, cuts=4):
    verts = [(x, y, 0.0) for y in np.linspace(-size, size, cuts + 1) for x in np.linspace(-size, size, cuts + 1)]
    n = cuts + 1
    faces = [(r * n + c, r * n + c + 1, (r + 1) * n + c + 1, (r + 1) * n + c) for r in range(cuts) for c in range(cuts)]
    return fx.mesh_object(name, verts, faces)


class MatrixTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.obj = plane("P")

    def test_write_read_clear(self):
        vertices = np.array([0, 1, 2])
        matrix = np.array([[1.0, 0.0], [0.25, 0.75], [0.0, 0.5]])
        weights.write(self.obj, vertices, ["A", "B"], matrix)
        out = weights.read(self.obj, ["A", "B", "C"])
        np.testing.assert_allclose(out[:3, :2], matrix)
        self.assertEqual(out[:, 2].sum(), 0.0)
        self.assertEqual(out[3:].sum(), 0.0)
        self.assertNotIn(0, [g.group for g in self.obj.data.vertices[0].groups if g.group == self.obj.vertex_groups["B"].index])
        weights.clear(self.obj, np.array([1]), ["A", "B"])
        out = weights.read(self.obj, ["A", "B"])
        np.testing.assert_allclose(out[1], [0.0, 0.0])
        np.testing.assert_allclose(out[0], [1.0, 0.0])

    def test_tidy(self):
        matrix = np.array([
            [0.5, 0.2, 0.1, 0.1, 0.05, 0.05],     # six weights: the two smallest go
            [0.005, 0.0, 0.0, 0.0, 0.0, 0.0],     # only a tiny weight: it stays, as 1
            [0.0] * 6,                            # nothing stays nothing
            [0.3, 0.3, 0.0, 0.0, 0.0, 0.009],     # under 0.01 goes
        ])
        out = weights.tidy(matrix)
        np.testing.assert_allclose(out[0], np.array([0.5, 0.2, 0.1, 0.1, 0.0, 0.0]) / 0.9)
        np.testing.assert_allclose(out[1], [1, 0, 0, 0, 0, 0])
        np.testing.assert_allclose(out[2], 0.0)
        np.testing.assert_allclose(out[3], [0.5, 0.5, 0, 0, 0, 0])
        self.assertTrue(np.all((out > 0).sum(axis=1) <= 4))


class BindTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.rig = fx.rig_for()
        self.rig.location = (0.5, 0.0, 0.0)
        bpy.context.view_layer.update()

    def test_bind_puts_armature_after_mirror(self):
        obj = plane("Half")
        obj.modifiers.new("Mirror", 'MIRROR')
        obj.modifiers.new("Subdivision", 'SUBSURF')
        weights.bind(self.rig, obj)
        self.assertEqual([m.type for m in obj.modifiers], ['MIRROR', 'ARMATURE', 'SUBSURF'])
        self.assertEqual(obj.modifiers[1].object, self.rig)
        weights.bind(self.rig, obj)
        self.assertEqual([m.type for m in obj.modifiers], ['MIRROR', 'ARMATURE', 'SUBSURF'])

    def test_bind_without_mirror_goes_first(self):
        obj = plane("P")
        obj.modifiers.new("Subdivision", 'SUBSURF')
        weights.bind(self.rig, obj)
        self.assertEqual([m.type for m in obj.modifiers], ['ARMATURE', 'SUBSURF'])

    def test_bind_keeps_world_matrix(self):
        obj = plane("P")
        other = bpy.data.objects.new("Other", None)
        bpy.context.scene.collection.objects.link(other)
        other.location = (0.0, 3.0, 0.0)
        obj.parent = other
        obj.location = (1.0, 0.0, 2.0)
        obj.scale = (2.0, 2.0, 2.0)
        bpy.context.view_layer.update()
        before = obj.matrix_world.copy()
        weights.bind(self.rig, obj)
        bpy.context.view_layer.update()
        self.assertEqual(obj.parent, self.rig)
        for a, b in zip(before, obj.matrix_world):
            np.testing.assert_allclose(tuple(a), tuple(b), atol=1e-6)

    def test_body_heat_uses_only_the_given_bones_and_restores_state(self):
        body = fx.mesh_object("Body", *fx.tube(0.86, 0.05, 0.07, 0.07, rings=24))
        other = plane("Other")
        other.select_set(True)
        bpy.context.view_layer.objects.active = other
        weights.body_heat(bpy.context, self.rig, body, {"Hips", "Spine", "Chest"})
        groups = {g.name for g in body.vertex_groups}
        self.assertTrue({"Hips", "Spine", "Chest"} <= groups)
        self.assertFalse(groups & {"Head", "LeftUpperLeg"})
        self.assertTrue(all(b.use_deform for b in self.rig.data.bones))
        self.assertEqual(bpy.context.view_layer.objects.active, other)
        self.assertTrue(other.select_get())
        self.assertFalse(body.select_get())
        self.assertFalse(self.rig.select_get())


class SurfaceTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_surface_weights_interpolate(self):
        source = plane("Body")
        world = np.array([tuple(v.co) for v in source.data.vertices])
        left = np.clip((1.0 - world[:, 0]) / 2.0, 0.0, 1.0)
        weights.write(source, np.arange(len(world)), ["A", "B"], np.stack([left, 1.0 - left], axis=1))
        mask = np.ones(len(world), bool)
        out = weights.surface_weights([(source, mask)], ["A", "B"], np.array([(0.0, 0.0, 0.1), (-1.0, 0.3, 0.2)]))
        np.testing.assert_allclose(out[0], [0.5, 0.5], atol=1e-6)
        np.testing.assert_allclose(out[1], [1.0, 0.0], atol=1e-6)

    def test_surface_weights_skip_masked_triangles(self):
        source = plane("Body")
        world = np.array([tuple(v.co) for v in source.data.vertices])
        weights.write(source, np.arange(len(world)), ["A"], np.ones((len(world), 1)))
        out = weights.surface_weights([(source, np.zeros(len(world), bool))], ["A"], np.array([(0.0, 0.0, 0.1)]))
        np.testing.assert_allclose(out, 0.0)

    def test_nearest_bone_weights(self):
        rig = fx.rig_for()
        points = np.array([[0.0, 0.0, 0.55], [0.0, -0.005, 0.95]]) * fx.HEIGHT
        out = weights.nearest_bone_weights(rig, ["Hips", "Head"], points)
        np.testing.assert_allclose(out, [[1.0, 0.0], [0.0, 1.0]])


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, thấy FAIL** — `cannot import name 'weights'`.

- [ ] **Step 3: Viết code**

**File `scripts/modules/dasktoon_rig/weights.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Vertex weights of the anime rig (spec 5.2, 6.2): vertex groups read and written as matrices, the clean-up for Unity,
binding a mesh to the rig, Blender's automatic weights for the body, and weights copied from the body surface."""

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

from . import chains, parts

LIMIT = 4
MINIMUM = 0.01


def read(obj, names):
    """Weights (vertices x len(names)) of obj in the vertex groups `names`; 0 where a vertex or group is missing."""
    columns = {}
    for j, name in enumerate(names):
        group = obj.vertex_groups.get(name)
        if group is not None:
            columns[group.index] = j
    out = np.zeros((len(obj.data.vertices), len(names)))
    if columns:
        for vertex in obj.data.vertices:
            for element in vertex.groups:
                j = columns.get(element.group)
                if j is not None:
                    out[vertex.index, j] = element.weight
    return out


def clear(obj, vertices, names):
    """Take `vertices` out of the vertex groups `names`."""
    indices = [int(i) for i in vertices]
    for name in names:
        group = obj.vertex_groups.get(name)
        if group is not None:
            group.remove(indices)


def write(obj, vertices, names, matrix):
    """Give vertices[i] the weight matrix[i, j] in the group names[j] (created on its first weight); zeros are left
    out. Weights the vertices had in other groups stay: clear them first."""
    vertices = np.asarray(vertices)
    for j, name in enumerate(names):
        column = matrix[:, j]
        rows = np.nonzero(column > 0.0)[0]
        if len(rows) == 0:
            continue
        group = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
        values = column[rows]
        if np.all(values == values[0]):
            group.add([int(i) for i in vertices[rows]], float(values[0]), 'REPLACE')
        else:
            for index, value in zip(vertices[rows].tolist(), values.tolist()):
                group.add([index], value, 'REPLACE')


def tidy(matrix, limit=LIMIT, minimum=MINIMUM):
    """Rows of `matrix` for Unity (spec 6.2 step 5): weights under `minimum` dropped, at most `limit` per row, summing
    to 1. A row whose weights are all under `minimum` keeps its largest one; an empty row stays empty."""
    out = np.where(matrix >= minimum, matrix, 0.0)
    if out.shape[1] > limit:
        drop = np.argsort(-out, axis=1, kind="stable")[:, limit:]
        np.put_along_axis(out, drop, 0.0, axis=1)
    lost = (out.sum(axis=1) <= 0.0) & (matrix.max(axis=1, initial=0.0) > 0.0)
    rows = np.nonzero(lost)[0]
    out[rows, matrix[rows].argmax(axis=1)] = 1.0
    sums = out.sum(axis=1)
    full = sums > 0.0
    out[full] /= sums[full, None]
    return out


def bind(rig, obj):
    """An Armature modifier on obj pointing at rig, right after the last Mirror modifier (so a half-modelled mesh is
    mirrored before it deforms) or else first; obj a child of rig where it is now (spec 6.2 step 3, 12)."""
    modifier = next((m for m in obj.modifiers if m.type == 'ARMATURE'), None)
    if modifier is None:
        modifier = obj.modifiers.new("Armature", 'ARMATURE')
    modifier.object = rig
    stack = list(obj.modifiers)
    current = stack.index(modifier)
    mirrors = [i for i, m in enumerate(stack) if m.type == 'MIRROR']
    target = mirrors[-1] + 1 if mirrors else 0
    if target > current:
        target -= 1
    if target != current:
        obj.modifiers.move(current, target)
    if obj.parent != rig:
        world = obj.matrix_world.copy()
        obj.parent = rig
        obj.parent_type = 'OBJECT'
        obj.matrix_parent_inverse = rig.matrix_world.inverted()
        obj.matrix_world = world


def body_heat(context, rig, obj, body_bones):
    """Blender's automatic weights (bone heat, Object › Parent › With Automatic Weights) of obj from `body_bones`
    only: the other bones of rig have Deform off meanwhile. Selection, active object and Deform flags come back."""
    bones = rig.data.bones
    deform = {bone.name: bone.use_deform for bone in bones}
    view_layer = context.view_layer
    selected = [o for o in view_layer.objects if o.select_get()]
    active = view_layer.objects.active
    try:
        for bone in bones:
            bone.use_deform = deform[bone.name] and bone.name in body_bones
        for o in selected:
            o.select_set(False)
        obj.select_set(True)
        rig.select_set(True)
        view_layer.objects.active = rig
        bpy.ops.object.parent_set(type='ARMATURE_AUTO', keep_transform=True)
    finally:
        for bone in bones:
            bone.use_deform = deform[bone.name]
        for o in view_layer.objects:
            o.select_set(o in selected)
        view_layer.objects.active = active


def _barycentric(p, a, b, c):
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
    d20, d21 = v2 @ v0, v2 @ v1
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-18:
        return np.array([1.0, 0.0, 0.0])
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    out = np.clip(np.array([1.0 - v - w, v, w]), 0.0, None)
    return out / out.sum()


def surface_weights(sources, names, points):
    """Weights (len(points) x len(names)) at world `points` copied from the nearest point of the source surfaces and
    interpolated between the corners of that triangle (spec 5.2, Clothing). `sources` is a list of (object, vertex
    mask); only triangles with every corner in the mask are used."""
    verts, tris, table, offset = [], [], [], 0
    for obj, mask in sources:
        mesh = obj.data
        mesh.calc_loop_triangles()
        corners = np.empty(len(mesh.loop_triangles) * 3, np.int32)
        mesh.loop_triangles.foreach_get("vertices", corners)
        corners = corners.reshape(-1, 3).astype(np.int64)
        corners = corners[mask[corners].all(axis=1)]
        world, _edges = parts.mesh_arrays(obj)
        verts.append(world)
        tris.append(corners + offset)
        table.append(read(obj, names))
        offset += len(world)
    out = np.zeros((len(points), len(names)))
    if not tris or sum(len(t) for t in tris) == 0:
        return out
    verts, tris, table = np.concatenate(verts), np.concatenate(tris), np.concatenate(table)
    tree = BVHTree.FromPolygons(verts.tolist(), tris.tolist(), all_triangles=True)
    for i, point in enumerate(np.asarray(points, float).tolist()):
        location, _normal, index, _distance = tree.find_nearest(point)
        if index is None:
            continue
        a, b, c = tris[index]
        bary = _barycentric(np.array(location), verts[a], verts[b], verts[c])
        out[i] = bary[0] * table[a] + bary[1] * table[b] + bary[2] * table[c]
    return out


def nearest_bone_weights(rig, names, points):
    """Weight 1 for the bone in `names` nearest to each world point (len(points) x len(names))."""
    points = np.asarray(points, float)
    distance = np.stack([chains.segment_distance(points, *parts.bone_segment(rig, name)) for name in names], axis=1)
    out = np.zeros_like(distance)
    out[np.arange(len(points)), distance.argmin(axis=1)] = 1.0
    return out
```

- [ ] **Step 4: Đăng ký** — CMake `dasktoon_rig_weights_test`; `TRANSLATED` += `"scripts/modules/dasktoon_rig/weights.py"`.

- [ ] **Step 5: Chạy test, thấy PASS** — `sync; run dasktoon_rig_weights_test; run dasktoon_translations_test`.

- [ ] **Step 6: Commit** — `git commit -m "feat: anime rig weights (matrices, Unity clean-up, binding, bone heat, surface copy)"`.

---

### Task 5: Build Rig (`build.py`)

**Files:**
- Create: `scripts/modules/dasktoon_rig/build.py`
- Test: `tests/python/dasktoon_rig_build_test.py`
- Modify: `tests/python/CMakeLists.txt`, `tests/python/dasktoon_translations_test.py` (`TRANSLATED` += `build.py`),
  `scripts/startup/bl_ui/dasktoon_translations.py`

**Interfaces:**
- Consumes: mọi hàm của Task 1–4.
- Produces: `MARK = "dt_part"`, `BuildError`, `Result` (`bones: list[str]`, `chains: int`, `objects: list[str]`,
  `warnings: list[str]`, `summary() -> str`), `check(rig, parts)`, `ownership(parts) -> {obj: ndarray}`,
  `build(context, rig, parts) -> Result`.

- [ ] **Step 1: Viết test**

**File `tests/python/dasktoon_rig_build_test.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Build Rig on test characters, as separate objects and as one mesh by material (anime rig spec 6)."""

import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import build, parts, weights  # noqa: E402

HAIR = ["Hair_%d" % k for k in range(1, 5)]
SKIRT = ["Skirt%d_%d" % (c, k) for c in range(1, 9) for k in range(1, 4)]


def deform_names(rig):
    return [b.name for b in rig.data.bones if b.use_deform]


def dominant(obj, rig, vertex):
    names = deform_names(rig)
    row = weights.read(obj, names)[vertex]
    return names[int(np.argmax(row))], float(row.max())


def separate_parts(objs):
    return [
        parts.Part("Body", objs["Body"], 'BODY'),
        parts.Part("Shirt", objs["Shirt"], 'CLOTHING'),
        parts.Part("Hair", objs["Hair"], 'HAIR'),
        parts.Part("Skirt", objs["Skirt"], 'SKIRT'),
        parts.Part("Ribbon", objs["Ribbon"], 'ACCESSORY'),
        parts.Part("Eye", objs["Eye"], 'ACCESSORY'),
    ]


class CheckedWeightsMixin:
    def assert_unity_weights(self, obj, rig):
        matrix = weights.read(obj, deform_names(rig))
        counts = (matrix > 0).sum(axis=1)
        self.assertTrue(np.all(counts >= 1), obj.name)
        self.assertTrue(np.all(counts <= 4), obj.name)
        np.testing.assert_allclose(matrix.sum(axis=1), 1.0, atol=1e-5, err_msg=obj.name)
        self.assertTrue(np.all(matrix[matrix > 0] >= 0.01 - 1e-9), obj.name)


class SeparateTest(CheckedWeightsMixin, unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.objs = fx.character()
        self.rig = fx.rig_for()
        self.parts = separate_parts(self.objs)
        self.result = build.build(bpy.context, self.rig, self.parts)

    def test_generated_bones(self):
        self.assertEqual(sorted(self.result.bones), sorted(HAIR + SKIRT))
        self.assertEqual(self.result.chains, 9)
        bones = self.rig.data.bones
        self.assertEqual(bones["Hair_1"].parent.name, "Head")
        self.assertEqual(bones["Hair_2"].parent.name, "Hair_1")
        self.assertTrue(bones["Hair_2"].use_connect)
        self.assertEqual(bones["Skirt1_1"].parent.name, "Hips")
        self.assertEqual(bones["Hair_3"]["dt_part"], "Hair")
        self.assertTrue(all(bones[n].use_deform for n in HAIR + SKIRT))
        self.assertIn("6 objects", self.result.summary())

    def test_every_object_is_bound_with_unity_weights(self):
        for obj in self.objs.values():
            self.assertEqual(obj.parent, self.rig)
            self.assertEqual([m.object for m in obj.modifiers if m.type == 'ARMATURE'], [self.rig])
            self.assert_unity_weights(obj, self.rig)

    def test_hair_root_follows_the_head_and_tip_the_last_bone(self):
        hair = self.objs["Hair"]
        self.assertEqual(dominant(hair, self.rig, 0), ("Head", 1.0))
        name, value = dominant(hair, self.rig, len(hair.data.vertices) - 1)
        self.assertEqual(name, "Hair_4")
        self.assertAlmostEqual(value, 1.0, places=5)

    def test_skirt_front_bottom_follows_the_front_strip(self):
        skirt = self.objs["Skirt"]
        front_bottom = 6 * 16 + 12  # last ring, the vertex at -Y
        self.assertEqual(dominant(skirt, self.rig, front_bottom), ("Skirt1_3", 1.0))
        self.assertEqual(dominant(skirt, self.rig, 12)[0], "Hips")

    def test_shirt_copies_the_body(self):
        shirt = self.objs["Shirt"]
        names = deform_names(self.rig)
        used = {names[j] for j in np.nonzero(weights.read(shirt, names).sum(axis=0))[0]}
        self.assertTrue(used & {"Spine", "Chest", "UpperChest"}, used)
        self.assertFalse(used & (set(HAIR + SKIRT) | {"Head", "LeftEye", "RightEye", "Jaw"}), used)

    def test_accessories_are_rigid_on_the_nearest_bone(self):
        self.assertEqual(set(dominant(self.objs["Ribbon"], self.rig, v) for v in range(8)), {("Head", 1.0)})
        self.assertEqual(set(dominant(self.objs["Eye"], self.rig, v) for v in range(8)), {("LeftEye", 1.0)})

    def test_second_build_replaces_generated_bones(self):
        again = build.build(bpy.context, self.rig, self.parts)
        self.assertEqual(sorted(again.bones), sorted(HAIR + SKIRT))
        self.assertEqual(len(self.rig.data.bones), 55 + len(HAIR) + len(SKIRT))
        for obj in self.objs.values():
            self.assertEqual(len([m for m in obj.modifiers if m.type == 'ARMATURE']), 1)
            self.assert_unity_weights(obj, self.rig)

    def test_stale_generated_groups_are_removed(self):
        self.parts[3].chain_count = 4
        build.build(bpy.context, self.rig, self.parts)
        skirt_groups = {g.name for g in self.objs["Skirt"].vertex_groups if g.name.startswith("Skirt")}
        self.assertEqual(skirt_groups, {"Skirt%d_%d" % (c, k) for c in range(1, 5) for k in range(1, 4)})
        self.assertNotIn("Skirt8_1", self.rig.data.bones)


class MergedTest(CheckedWeightsMixin, unittest.TestCase):
    def test_merged_mesh_by_material(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        obj = fx.character(merged=True)["Character"]
        rig = fx.rig_for()
        result = build.build(bpy.context, rig, [
            parts.Part("Body", obj, 'BODY'),
            parts.Part("Shirt", obj, 'CLOTHING', scope='MATERIAL', material="Shirt"),
            parts.Part("Hair", obj, 'HAIR', scope='MATERIAL', material="Hair"),
            parts.Part("Skirt", obj, 'SKIRT', scope='MATERIAL', material="Skirt"),
            parts.Part("Ribbon", obj, 'ACCESSORY', scope='MATERIAL', material="Ribbon"),
            parts.Part("Eye", obj, 'ACCESSORY', scope='MATERIAL', material="Eye"),
        ])
        self.assertEqual(sorted(result.bones), sorted(HAIR + SKIRT))
        self.assert_unity_weights(obj, rig)
        hair = parts.part_vertices(parts.Part("Hair", obj, scope='MATERIAL', material="Hair"))
        names = deform_names(rig)
        used = {names[j] for j in np.nonzero(weights.read(obj, names)[hair].sum(axis=0))[0]}
        self.assertTrue(used <= {"Head"} | set(HAIR), used)


class TransformTest(unittest.TestCase):
    def joints(self, scaled):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        hair = objs["Hair"]
        if scaled:
            offset = Vector((0.0, 0.0, 0.5 * fx.HEIGHT))
            for v in hair.data.vertices:
                v.co = (v.co - offset) / 2.0
            hair.scale = (2.0, 2.0, 2.0)
            hair.location = offset
        bpy.context.view_layer.update()
        before = hair.matrix_world.copy()
        rig = fx.rig_for()
        build.build(bpy.context, rig, separate_parts(objs))
        bpy.context.view_layer.update()
        for a, b in zip(before, hair.matrix_world):
            np.testing.assert_allclose(tuple(a), tuple(b), atol=1e-6)
        return [tuple(rig.matrix_world @ rig.data.bones[name].head_local) for name in HAIR]

    def test_scaled_hair_object_gets_world_joints(self):
        np.testing.assert_allclose(self.joints(True), self.joints(False), atol=1e-4)


class ModeAndErrorTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.objs = fx.character()
        self.rig = fx.rig_for()

    def test_build_returns_to_pose_mode(self):
        bpy.context.view_layer.objects.active = self.rig
        bpy.ops.object.mode_set(mode='POSE')
        build.build(bpy.context, self.rig, separate_parts(self.objs))
        self.assertEqual(self.rig.mode, 'POSE')
        self.assertEqual(bpy.context.view_layer.objects.active, self.rig)

    def test_errors_change_nothing(self):
        cases = [
            [],
            [parts.Part("Shirt", self.objs["Shirt"], 'CLOTHING')],
            [parts.Part("Body", self.objs["Body"], 'BODY', scope='MATERIAL', material="Nope")],
            [parts.Part("Body", self.objs["Body"], 'BODY'), parts.Part("Hair", self.objs["Hair"], 'HAIR', bone="Nope")],
            [parts.Part("Body", None, 'BODY')],
        ]
        for case in cases:
            with self.assertRaises(build.BuildError):
                build.build(bpy.context, self.rig, case)
        self.objs["Body"].hide_set(True)
        with self.assertRaises(build.BuildError):
            build.build(bpy.context, self.rig, [parts.Part("Body", self.objs["Body"], 'BODY')])
        self.assertEqual(len(self.rig.data.bones), 55)
        for obj in self.objs.values():
            self.assertEqual(len(obj.modifiers), 0)
            self.assertEqual(len(obj.vertex_groups), 0)
            self.assertIsNone(obj.parent)

    def test_not_a_standard_skeleton(self):
        from dasktoon_rig import skeleton
        with skeleton.editing(bpy.context, self.rig) as edit:
            edit.remove(edit["Spine"])
        with self.assertRaises(build.BuildError) as caught:
            build.build(bpy.context, self.rig, separate_parts(self.objs))
        self.assertIn("Spine", str(caught.exception))

    def test_shared_mesh_is_refused(self):
        twin = bpy.data.objects.new("Twin", self.objs["Body"].data)
        bpy.context.scene.collection.objects.link(twin)
        with self.assertRaises(build.BuildError):
            build.build(bpy.context, self.rig, [parts.Part("Body", self.objs["Body"], 'BODY')])

    def test_later_role_wins_a_vertex(self):
        body = self.objs["Body"]
        group = body.vertex_groups.new(name="DT_Top")
        top = list(range(16))
        group.add(top, 1.0, 'REPLACE')
        build.build(bpy.context, self.rig, [
            parts.Part("Top", body, 'ACCESSORY', scope='VERTEX_GROUP', vertex_group="DT_Top", bone="Neck"),
            parts.Part("Body", body, 'BODY'),
        ])
        self.assertEqual({dominant(body, self.rig, v) for v in top}, {("Neck", 1.0)})


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, thấy FAIL** — `cannot import name 'build'`.

- [ ] **Step 3: Viết code**

**File `scripts/modules/dasktoon_rig/build.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Build Rig (anime rig spec 6): check the rig and its parts, generate the hair and skirt chains, bind the meshes and
paint the weights of every part, then clean them up for Unity. Every build starts again from the parts."""

import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Vector

from . import chains, parts as rig_parts, skeleton, weights

MARK = "dt_part"
MIN_BONE = 1e-4


class BuildError(Exception):
    """Why the rig cannot be built, worded for the user."""


class Result:
    """What a build did: the generated bones, the chains, the objects it painted and the warnings."""

    def __init__(self):
        self.bones = []
        self.chains = 0
        self.objects = []
        self.warnings = []

    def summary(self):
        return rpt_("Built %d bones in %d chains, weights on %d objects") % (
            len(self.bones), self.chains, len(self.objects))


def check(rig, parts):
    """BuildError when the rig cannot be built (spec 6.1)."""
    if rig is None or rig.type != 'ARMATURE':
        raise BuildError(rpt_("The active object is not an armature"))
    if rig.library is not None or rig.data.library is not None:
        raise BuildError(rpt_("%s is linked from a library") % rig.name)
    missing = skeleton.missing_bones(rig.data)
    if missing:
        raise BuildError(rpt_("%s is not a standard skeleton; missing bones: %s") % (rig.name, ", ".join(missing)))
    if not rig.visible_get():
        raise BuildError(rpt_("%s is hidden; show it before building") % rig.name)
    if not parts:
        raise BuildError(rpt_("Add parts before building the rig"))
    for part in parts:
        obj = part.object
        if obj is None:
            raise BuildError(rpt_("Part %s has no object") % part.name)
        if obj.type != 'MESH':
            raise BuildError(rpt_("Part %s: %s is not a mesh") % (part.name, obj.name))
        if obj.library is not None or obj.data.library is not None:
            raise BuildError(rpt_("%s is linked from a library") % obj.name)
        if obj.data.users > 1:
            raise BuildError(rpt_("%s shares its mesh with other objects; make it single user first") % obj.name)
        if not obj.visible_get():
            raise BuildError(rpt_("%s is hidden; show it before building") % obj.name)
        if part.bone and rig.data.bones.get(part.bone) is None:
            raise BuildError(rpt_("Part %s: bone %s is not in %s") % (part.name, part.bone, rig.name))
        try:
            rig_parts.part_vertices(part)
        except rig_parts.PartError as ex:
            raise BuildError(str(ex)) from None
    roles = {part.role for part in parts}
    if 'CLOTHING' in roles and 'BODY' not in roles:
        raise BuildError(rpt_("Clothing copies its weights from a Body part; add a Body part first"))


def ownership(parts):
    """{object: array giving, for each vertex, the index in `parts` of the part that owns it (-1 for none)}: a later
    role wins, then a later part (spec 5.2)."""
    owners = {}
    for i in sorted(range(len(parts)), key=lambda i: (rig_parts.ROLES.index(parts[i].role), i)):
        obj = parts[i].object
        if obj not in owners:
            owners[obj] = np.full(len(obj.data.vertices), -1, np.int64)
        owners[obj][rig_parts.part_vertices(parts[i])] = i
    return owners


class _Plan:
    """Chains to generate: bones (name, parent, world head, world tail, part name) and paint jobs (part index,
    vertices, bone names, weights) whose names are the planned ones."""

    def __init__(self):
        self.bones = []
        self.paint = []
        self.chains = 0


def _local_x(rig, point):
    return (rig.matrix_world.inverted() @ Vector(point)).x


def _plan_hair(rig, index, part, vertices, plan):
    attach = part.bone or rig_parts.DEFAULT_BONE['HAIR']
    head, tail = rig_parts.bone_segment(rig, attach)
    world, edges = rig_parts.mesh_arrays(part.object)
    locks = []
    for piece in rig_parts.pieces(edges, vertices):
        chain = chains.hair_chain(world[piece], rig_parts.local_edges(edges, piece), head, tail, part.bone_count)
        if chain is None:
            plan.paint.append((index, piece, [attach], np.ones((len(piece), 1))))
        else:
            locks.append((piece, chain))
    locks.sort(key=lambda lock: _local_x(rig, lock[1].joints[0]))
    base = rig_parts.ascii_name(part.name)
    for number, (piece, chain) in enumerate(locks, 1):
        prefix = base if len(locks) == 1 else "%s%d" % (base, number)
        names = ["%s_%d" % (prefix, k) for k in range(1, part.bone_count + 1)]
        parent = attach
        for k, name in enumerate(names):
            plan.bones.append((name, parent, chain.joints[k], chain.joints[k + 1], part.name))
            parent = name
        plan.paint.append((index, piece, [attach] + names, chain.weights))
        plan.chains += 1


def _plan_skirt(rig, index, part, vertices, plan):
    attach = part.bone or rig_parts.DEFAULT_BONE['SKIRT']
    world, _edges = rig_parts.mesh_arrays(part.object)
    skirt = chains.skirt_chains(world[vertices], part.bone_count, part.chain_count)
    base = rig_parts.ascii_name(part.name)
    names = [attach]
    for c, joints in enumerate(skirt.strips):
        strip = ["%s%d_%d" % (base, c + 1, k) for k in range(1, part.bone_count + 1)]
        names += strip
        if joints is None:
            continue
        parent = attach
        for k, name in enumerate(strip):
            plan.bones.append((name, parent, joints[k], joints[k + 1], part.name))
            parent = name
        plan.chains += 1
    plan.paint.append((index, vertices, names, skirt.weights))


def _make_bones(context, rig, plan):
    """Remove the bones of the last build and add the planned ones. Returns ({planned name: actual name}, the names
    of the removed bones)."""
    to_rig = rig.matrix_world.inverted()
    actual, removed = {}, []
    with skeleton.editing(context, rig) as edit:
        for bone in list(edit):
            if MARK in bone:
                removed.append(bone.name)
                edit.remove(bone)
        for name, parent, head, tail, part_name in plan.bones:
            bone = edit.new(name)
            bone.head = to_rig @ Vector(head)
            bone.tail = to_rig @ Vector(tail)
            if (bone.tail - bone.head).length < MIN_BONE:
                bone.tail = bone.head + Vector((0.0, 0.0, -MIN_BONE))
            parent_bone = edit.get(actual.get(parent, parent))
            bone.parent = parent_bone
            if parent in actual and (parent_bone.tail - bone.head).length < 1e-6:
                bone.use_connect = True
            outward = bone.head - (parent_bone.head + parent_bone.tail) / 2.0
            if outward.length > 1e-9:
                bone.align_roll(outward)
            bone.use_deform = True
            bone[MARK] = part_name
            actual[name] = bone.name
    return actual, removed


def _paint(context, rig, parts, owners, plan, actual, result):
    deform = [b.name for b in rig.data.bones if b.use_deform]
    generated = set(actual.values())
    body_bones = [n for n in deform if n not in generated and n not in skeleton.FACE_BONES]
    fixed_bones = [n for n in deform if n not in generated]
    body_ids = [i for i, part in enumerate(parts) if part.role == 'BODY']
    for obj in owners:
        weights.bind(rig, obj)
    sources = []
    for obj, owner in owners.items():
        body = np.isin(owner, body_ids)
        if not body.any():
            continue
        sources.append((obj, body))
        weights.clear(obj, np.arange(len(owner)), deform)
        weights.body_heat(context, rig, obj, set(body_bones))
        vertices = np.nonzero(body)[0]
        matrix = weights.read(obj, body_bones)[vertices]
        empty = matrix.sum(axis=1) <= 0.0
        if empty.any():
            world, _edges = rig_parts.mesh_arrays(obj)
            weights.write(obj, vertices[empty], body_bones,
                          weights.nearest_bone_weights(rig, body_bones, world[vertices[empty]]))
            result.warnings.append(rpt_("%s: %d vertices took the nearest bone (automatic weights found no "
                                        "solution there)") % (obj.name, int(empty.sum())))
    for i, part in enumerate(parts):
        obj = part.object
        vertices = np.nonzero(owners[obj] == i)[0]
        if len(vertices) == 0 or part.role in ('BODY',) + rig_parts.CHAIN_ROLES:
            continue
        weights.clear(obj, vertices, deform)
        if part.role == 'CLOTHING':
            world, _edges = rig_parts.mesh_arrays(obj)
            matrix = weights.surface_weights(sources, body_bones, world[vertices])
            if not (matrix.sum(axis=1) > 0.0).all():
                result.warnings.append(rpt_("%s: no Body surface to copy weights from") % part.name)
            weights.write(obj, vertices, body_bones, matrix)
        else:
            world, _edges = rig_parts.mesh_arrays(obj)
            bone = part.bone or rig_parts.nearest_bone(rig, world[vertices].mean(axis=0), fixed_bones)
            weights.write(obj, vertices, [bone], np.ones((len(vertices), 1)))
    for index, vertices, names, matrix in plan.paint:
        obj = parts[index].object
        weights.clear(obj, vertices, deform)
        weights.write(obj, vertices, [actual.get(n, n) for n in names], matrix)


def _drop_stale_groups(owners, removed, current):
    for obj in owners:
        for name in removed:
            group = obj.vertex_groups.get(name)
            if group is not None and name not in current:
                obj.vertex_groups.remove(group)


def _tidy(rig, owners):
    names = [b.name for b in rig.data.bones if b.use_deform]
    for obj in owners:
        matrix = weights.read(obj, names)
        rows = np.nonzero(matrix.sum(axis=1) > 0.0)[0]
        weights.clear(obj, rows, names)
        weights.write(obj, rows, names, weights.tidy(matrix[rows]))


def build(context, rig, parts):
    """Build the rig from `parts` (spec 6.2); BuildError, before any change, when it cannot be built. The active object
    and its mode come back afterwards."""
    parts = list(parts)
    view_layer = context.view_layer
    active = view_layer.objects.active
    mode = active.mode if active is not None else 'OBJECT'
    if mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    try:
        check(rig, parts)
        result = Result()
        owners = ownership(parts)
        plan = _Plan()
        for i, part in enumerate(parts):
            vertices = np.nonzero(owners[part.object] == i)[0]
            if len(vertices) == 0:
                continue
            if part.role == 'HAIR':
                _plan_hair(rig, i, part, vertices, plan)
            elif part.role == 'SKIRT':
                _plan_skirt(rig, i, part, vertices, plan)
        actual, removed = _make_bones(context, rig, plan)
        _paint(context, rig, parts, owners, plan, actual, result)
        _drop_stale_groups(owners, removed, set(actual.values()))
        _tidy(rig, owners)
        result.bones = list(actual.values())
        result.chains = plan.chains
        result.objects = [obj.name for obj in owners]
        return result
    finally:
        view_layer.objects.active = active
        if active is not None and mode != 'OBJECT' and active.mode != mode:
            bpy.ops.object.mode_set(mode=mode)
```

- [ ] **Step 4: Bản dịch** — thêm vào cuối `VI`:
```python
    # dasktoon_rig/build.py
    "Built %d bones in %d chains, weights on %d objects": "Đã dựng %d xương trong %d chuỗi, vẽ weight trên %d object",
    "The active object is not an armature": "Object đang chọn không phải armature",
    "%s is linked from a library": "%s được link từ thư viện",
    "%s is not a standard skeleton; missing bones: %s": "%s không phải khung chuẩn; thiếu xương: %s",
    "%s is hidden; show it before building": "%s đang ẩn; hãy hiện nó trước khi dựng",
    "Add parts before building the rig": "Hãy thêm phần trước khi dựng rig",
    "Part %s has no object": "Phần %s chưa có object",
    "Part %s: %s is not a mesh": "Phần %s: %s không phải mesh",
    "%s shares its mesh with other objects; make it single user first":
        "%s dùng chung mesh với object khác; hãy tách riêng (Single User) trước",
    "Part %s: bone %s is not in %s": "Phần %s: xương %s không có trong %s",
    "Clothing copies its weights from a Body part; add a Body part first":
        "Quần áo chép weight từ phần Body; hãy thêm phần Body trước",
    "%s: %d vertices took the nearest bone (automatic weights found no solution there)":
        "%s: %d đỉnh lấy theo xương gần nhất (weight tự động không tìm được nghiệm ở đó)",
    "%s: no Body surface to copy weights from": "%s: không có bề mặt Body để chép weight",
```

- [ ] **Step 5: Đăng ký** — CMake `dasktoon_rig_build_test`; `TRANSLATED` += `"scripts/modules/dasktoon_rig/build.py"`.

- [ ] **Step 6: Chạy test, thấy PASS** — `sync; run dasktoon_rig_build_test; run dasktoon_translations_test`.

- [ ] **Step 7: Commit** — `git commit -m "feat: Build Rig generates hair and skirt chains and paints weights by role"`.

---

### Task 6: Giao diện (`bl_ui/dasktoon_rig.py`)

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_rig.py`
- Test: `tests/python/dasktoon_rig_ui_test.py`
- Modify: `scripts/startup/bl_ui/__init__.py` (`_modules` += `"dasktoon_rig"` sau `"dasktoon_shape_key_manager"`),
  `tests/python/CMakeLists.txt`, `tests/python/dasktoon_translations_test.py` (`TRANSLATED` +=
  `"scripts/startup/bl_ui/dasktoon_rig.py"`), `scripts/startup/bl_ui/dasktoon_translations.py`

**Interfaces:**
- Consumes: `skeleton.create_humanoid/placement/fit/missing_bones/is_humanoid`, `parts.initial_roles/guess_role/
  DEFAULT_BONE_COUNT/BONE_COUNT`, `build.build/BuildError`.
- Produces: `bpy.types.Armature.dasktoon_rig` (`DaskRig`: `parts`, `active_part_index`), `DaskRigPart` (trường như
  spec §5.1), operator `dasktoon.rig_add_humanoid`, `rig_edit_joints`, `rig_fit`, `rig_add_selected`,
  `rig_add_material_part`, `rig_remove_part`, `rig_build`, `rig_part_from_selection`; panel `DATA_PT_dasktoon_rig`
  (+ `_joints`, `_parts`, `_build`), `DATA_PT_dasktoon_rig_mesh`; hàm `find_rig(context, obj)`,
  `add_meshes(rig, meshes) -> int`, `add_part(rig, obj, role, ...)`.

- [ ] **Step 1: Viết test**

**File `tests/python/dasktoon_rig_ui_test.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime rig interface: Add › Armature › Anime Humanoid, the Anime Rig panels and their commands (spec 7)."""

import os
import sys
import types
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_i18n_utils as iu  # noqa: E402
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from bl_ui import dasktoon_translations as dt  # noqa: E402
from dasktoon_rig import skeleton  # noqa: E402


def select_only(objects, active):
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in objects)
    bpy.context.view_layer.objects.active = active


def panel_context(obj):
    return types.SimpleNamespace(object=obj, scene=bpy.context.scene, mode='OBJECT')


class AddTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_menu_entry(self):
        from bl_ui.space_view3d import VIEW3D_MT_armature_add
        self.assertTrue(VIEW3D_MT_armature_add.is_extended())
        log = tu.RecordingLayout()
        for draw in VIEW3D_MT_armature_add._dyn_ui_initialize():
            draw(types.SimpleNamespace(layout=log), bpy.context)
        self.assertIn(("dasktoon.rig_add_humanoid", "Anime Humanoid"), tu.operators(log.log))

    def test_add_fits_and_makes_parts(self):
        objs = fx.character()
        select_only([objs["Body"], objs["Hair"], objs["Shirt"]], objs["Body"])
        bpy.ops.dasktoon.rig_add_humanoid()
        rig = bpy.context.view_layer.objects.active
        self.assertTrue(skeleton.is_humanoid(rig))
        self.assertTrue(rig.select_get())
        self.assertFalse(objs["Body"].select_get())
        top = (rig.matrix_world @ rig.data.bones["Head"].tail_local).z
        self.assertAlmostEqual(top, 0.05 * fx.HEIGHT + 0.99 * (0.96 - 0.05) * fx.HEIGHT, places=3)
        roles = {p.object.name: p.role for p in rig.data.dasktoon_rig.parts}
        self.assertEqual(roles, {"Body": 'BODY', "Hair": 'HAIR', "Shirt": 'CLOTHING'})

    def test_add_without_meshes_uses_the_cursor(self):
        bpy.context.scene.cursor.location = (2.0, 0.0, 0.0)
        bpy.ops.dasktoon.rig_add_humanoid()
        rig = bpy.context.view_layer.objects.active
        self.assertEqual(tuple(rig.matrix_world.translation), (2.0, 0.0, 0.0))
        self.assertEqual(len(rig.data.dasktoon_rig.parts), 0)


class PanelTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.objs = fx.character()
        self.rig = fx.rig_for()
        select_only([self.rig], self.rig)

    def test_joints_panel(self):
        log = tu.draw(ui.DATA_PT_dasktoon_rig_joints, panel_context(self.rig))
        self.assertIn("Standard skeleton", tu.labels(log))
        ops = [name for name, _text in tu.operators(log)]
        self.assertEqual(ops, ["dasktoon.rig_edit_joints", "dasktoon.rig_fit"])
        with skeleton.editing(bpy.context, self.rig) as edit:
            edit.remove(edit["Spine"])
        log = tu.draw(ui.DATA_PT_dasktoon_rig_joints, panel_context(self.rig))
        self.assertIn("Missing bones: Spine", tu.labels(log))

    def test_parts_panel_and_commands(self):
        log = tu.draw(ui.DATA_PT_dasktoon_rig_parts, panel_context(self.rig))
        self.assertIn("Select meshes and press + to add them as parts", tu.labels(log))
        select_only([self.rig, self.objs["Body"], self.objs["Skirt"]], self.rig)
        bpy.ops.dasktoon.rig_add_selected()
        bpy.ops.dasktoon.rig_add_selected()  # already there: nothing new
        parts = self.rig.data.dasktoon_rig.parts
        self.assertEqual([(p.name, p.role, p.bone_count) for p in parts], [("Body", 'BODY', 4), ("Skirt", 'SKIRT', 3)])
        log = tu.draw(ui.DATA_PT_dasktoon_rig_parts, panel_context(self.rig))
        props = [entry[1] for entry in log if entry[0] == "prop"]
        self.assertEqual(props, ["object", "scope", "role", "bone_count", "chain_count"])
        self.assertIn(("call", "prop_search"), [entry[:2] for entry in log])
        self.objs["Body"].data.materials.append(bpy.data.materials.new("Skin"))
        self.rig.data.dasktoon_rig.active_part_index = 0
        bpy.ops.dasktoon.rig_add_material_part(material="Skin")
        self.assertEqual((parts[2].scope, parts[2].material, parts[2].role), ('MATERIAL', "Skin", 'BODY'))
        bpy.ops.dasktoon.rig_remove_part()
        self.assertEqual(len(parts), 2)

    def test_build_command(self):
        select_only([self.rig] + list(self.objs.values()), self.rig)
        bpy.ops.dasktoon.rig_add_selected()
        bpy.ops.dasktoon.rig_build()
        self.assertIn("Hair_4", self.rig.data.bones)
        self.assertEqual(bpy.context.view_layer.objects.active, self.rig)
        self.assertEqual(len(tu.draw(ui.DATA_PT_dasktoon_rig_build, panel_context(self.rig))), 2)

    def test_build_error_is_reported(self):
        with self.assertRaises(RuntimeError) as caught:
            bpy.ops.dasktoon.rig_build()
        self.assertIn("Add parts before building the rig", str(caught.exception))

    def test_part_from_selection(self):
        body = self.objs["Body"]
        select_only([body], body)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        for v in body.data.vertices[:16]:
            v.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        self.assertIs(ui.find_rig(bpy.context, body), self.rig)
        bpy.ops.dasktoon.rig_part_from_selection(part_name="Collar", role='ACCESSORY', rig=self.rig.name)
        self.assertEqual(body.mode, 'EDIT')
        part = self.rig.data.dasktoon_rig.parts[-1]
        self.assertEqual((part.name, part.scope, part.vertex_group, part.role),
                         ("Collar", 'VERTEX_GROUP', "DT_Collar", 'ACCESSORY'))
        bpy.ops.object.mode_set(mode='OBJECT')
        members = [v.index for v in body.data.vertices if any(g.group == body.vertex_groups["DT_Collar"].index
                                                                for g in v.groups)]
        self.assertEqual(members, list(range(16)))
        log = tu.draw(ui.DATA_PT_dasktoon_rig_mesh, panel_context(body))
        self.assertIn("dasktoon.rig_part_from_selection", [name for name, _text in tu.operators(log)])
        self.assertIn("role", [entry[1] for entry in log if entry[0] == "prop"])


class TextTest(unittest.TestCase):
    def test_properties_and_enums_are_translated(self):
        strings = {bpy.types.DaskRigPart.bl_rna.description, bpy.types.DaskRig.bl_rna.description}
        operators = [getattr(bpy.types, name) for name in dir(bpy.types) if name.startswith("DASKTOON_OT_rig_")]
        self.assertEqual(len(operators), 8)
        for struct in operators:
            strings.update((struct.bl_rna.name, struct.bl_rna.description))
        for struct in [bpy.types.DaskRigPart, bpy.types.DaskRig] + operators:
            for prop in struct.bl_rna.properties:
                if prop.identifier == "rna_type":
                    continue
                strings.update((prop.name, prop.description))
                if prop.type == 'ENUM':
                    for item in prop.enum_items_static:
                        strings.update((item.name, item.description))
        strings.discard("")
        with iu.language('vi_VN'):
            self.assertEqual(iu.untranslated(strings, dt.KEEP), [])

    def test_role_icons_exist(self):
        icons = {i.identifier for i in bpy.types.UILayout.bl_rna.functions["label"].parameters["icon"].enum_items}
        self.assertTrue(set(ui.ROLE_ICONS.values()) <= icons)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, thấy FAIL** — `cannot import name 'dasktoon_rig' from 'bl_ui'`.

- [ ] **Step 3: Viết code**

**File `scripts/startup/bl_ui/dasktoon_rig.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime rig, R1 (docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md, section 7): Add › Armature › Anime
Humanoid; the Anime Rig panel in Properties › Object Data of an armature (Joints, Parts, Build) and of a mesh (its
parts, Add Part from Selection). The work is done by the dasktoon_rig module."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
from bpy.props import CollectionProperty, EnumProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup, UIList

ROLE_ITEMS = (
    ('BODY', "Body", "Skin and face: automatic weights from the body bones", 'USER', 0),
    ('CLOTHING', "Clothing", "Follows the body: weights copied from the nearest Body surface", 'MATCLOTH', 1),
    ('ACCESSORY', "Accessory", "Rigid on one bone", 'PINNED', 2),
    ('HAIR', "Hair", "A chain of bones for each long lock", 'STRANDS', 3),
    ('SKIRT', "Skirt", "Chains of bones around the hips", 'MOD_CLOTH', 4),
)
ROLE_ICONS = {item[0]: item[3] for item in ROLE_ITEMS}


def _is_mesh(_self, obj):
    return obj.type == 'MESH'


class DaskRigPart(PropertyGroup):
    """A part of the character and how it is rigged"""
    name: StringProperty(name="Name", description="Name of the part; generated bones start with it", default="Part")
    object: PointerProperty(name="Object", description="Mesh that holds the part", type=bpy.types.Object,
                            poll=_is_mesh)
    scope: EnumProperty(
        name="Scope",
        description="Which vertices of the mesh make the part",
        items=[
            ('OBJECT', "Whole Object", "Every vertex of the mesh"),
            ('MATERIAL', "Material", "The faces that use a material"),
            ('VERTEX_GROUP', "Vertex Group", "The vertices of a vertex group"),
        ],
        default='OBJECT',
    )
    material: StringProperty(name="Material", description="Material whose faces make the part")
    vertex_group: StringProperty(name="Vertex Group", description="Vertex group whose vertices make the part")
    role: EnumProperty(name="Role", description="How the part is rigged", items=ROLE_ITEMS, default='BODY')
    bone: StringProperty(
        name="Bone",
        description="Bone the part hangs from or sits on; empty picks one automatically (Head for hair, Hips for a "
                    "skirt, the nearest bone for an accessory)",
    )
    bone_count: IntProperty(name="Bones per Chain", description="Number of bones along each chain", default=4, min=1,
                            max=12)
    chain_count: IntProperty(name="Chains", description="Number of chains around the skirt", default=8, min=3, max=24)


class DaskRig(PropertyGroup):
    """The parts of an anime rig"""
    parts: CollectionProperty(type=DaskRigPart)
    active_part_index: IntProperty(name="Active Part", description="Part shown below the list", default=0)


def rig_of(context):
    obj = getattr(context, "object", None)
    return obj if obj is not None and obj.type == 'ARMATURE' else None


def humanoid_rigs(scene):
    from dasktoon_rig import skeleton
    return [obj for obj in scene.objects if skeleton.is_humanoid(obj)]


def find_rig(context, obj):
    """The rig a mesh belongs to (spec 7.2): one with a part on it, its Armature modifier, its parent, or the only
    standard skeleton in the scene; None when it is not clear."""
    rigs = humanoid_rigs(context.scene)
    for rig in rigs:
        if any(part.object == obj for part in rig.data.dasktoon_rig.parts):
            return rig
    for modifier in obj.modifiers:
        if modifier.type == 'ARMATURE' and modifier.object in rigs:
            return modifier.object
    if obj.parent in rigs:
        return obj.parent
    return rigs[0] if len(rigs) == 1 else None


def add_part(rig, obj, role, name=None, scope='OBJECT', material="", vertex_group=""):
    from dasktoon_rig import parts as rig_parts
    data = rig.data.dasktoon_rig
    part = data.parts.add()
    part.name = name or obj.name
    part.object = obj
    part.scope = scope
    part.material = material
    part.vertex_group = vertex_group
    part.role = role
    part.bone_count = rig_parts.DEFAULT_BONE_COUNT.get(role, rig_parts.BONE_COUNT)
    data.active_part_index = len(data.parts) - 1
    return part


def add_meshes(rig, meshes):
    """Whole-object parts for the meshes not yet in the rig, with the roles their names suggest; returns how many."""
    from dasktoon_rig import parts as rig_parts
    data = rig.data.dasktoon_rig
    have = {part.object for part in data.parts if part.scope == 'OBJECT'}
    new = [mesh for mesh in meshes if mesh not in have]
    roles = rig_parts.initial_roles(new, has_body=any(part.role == 'BODY' for part in data.parts))
    for mesh in new:
        add_part(rig, mesh, roles[mesh])
    return len(new)


def _active_part(rig):
    data = rig.data.dasktoon_rig
    if 0 <= data.active_part_index < len(data.parts):
        return data.parts[data.active_part_index]
    return None


class DASKTOON_OT_rig_add_humanoid(Operator):
    """Add the DaskToon standard skeleton, fitted to the selected meshes, which become its parts"""
    bl_idname = "dasktoon.rig_add_humanoid"
    bl_label = "Anime Humanoid"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        from dasktoon_rig import skeleton
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        height, location = skeleton.placement(meshes, context.scene.cursor.location)
        rig = skeleton.create_humanoid(context, height, location)
        if meshes:
            add_meshes(rig, meshes)
        for obj in context.view_layer.objects:
            obj.select_set(obj == rig)
        context.view_layer.objects.active = rig
        self.report({'INFO'}, rpt_("Fit the joints in Edit Mode, then press Build Rig in Properties › Object Data"))
        return {'FINISHED'}


class DASKTOON_OT_rig_edit_joints(Operator):
    """Edit the joints of the skeleton with X-Axis Mirror on, so both sides move together"""
    bl_idname = "dasktoon.rig_edit_joints"
    bl_label = "Edit Joints"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        rig = rig_of(context)
        return rig is not None and rig.mode != 'EDIT' and context.view_layer.objects.active == rig

    def execute(self, context):
        rig_of(context).data.use_mirror_x = True
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


class DASKTOON_OT_rig_fit(Operator):
    """Move and scale the skeleton to the meshes of the parts; the joints you placed are replaced"""
    bl_idname = "dasktoon.rig_fit"
    bl_label = "Fit to Parts"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        rig = rig_of(context)
        return rig is not None and any(part.object is not None for part in rig.data.dasktoon_rig.parts)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        from dasktoon_rig import skeleton
        rig = rig_of(context)
        meshes = list(dict.fromkeys(part.object for part in rig.data.dasktoon_rig.parts
                                    if part.object is not None and part.object.type == 'MESH'))
        skeleton.fit(context, rig, meshes)
        return {'FINISHED'}


class DASKTOON_OT_rig_add_selected(Operator):
    """Add each selected mesh as a part of the rig, with the role its name suggests"""
    bl_idname = "dasktoon.rig_add_selected"
    bl_label = "Add Selected Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return rig_of(context) is not None and any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        if add_meshes(rig_of(context), [obj for obj in context.selected_objects if obj.type == 'MESH']) == 0:
            self.report({'INFO'}, rpt_("The selected meshes are already parts"))
        return {'FINISHED'}


_material_items = []


def _materials(_self, context):
    rig = rig_of(context)
    part = _active_part(rig) if rig is not None else None
    obj = part.object if part is not None else None
    names = sorted({slot.material.name for slot in obj.material_slots if slot.material}) if obj is not None else []
    _material_items[:] = [(name, name, "") for name in names]
    return _material_items


class DASKTOON_OT_rig_add_material_part(Operator):
    """Add the faces of one material of the active part's mesh as a new part"""
    bl_idname = "dasktoon.rig_add_material_part"
    bl_label = "Add Material Part"
    bl_options = {'REGISTER', 'UNDO'}
    bl_property = "material"

    material: EnumProperty(name="Material", description="Material whose faces make the new part", items=_materials)

    @classmethod
    def poll(cls, context):
        rig = rig_of(context)
        part = _active_part(rig) if rig is not None else None
        return part is not None and part.object is not None and any(s.material for s in part.object.material_slots)

    def invoke(self, context, _event):
        context.window_manager.invoke_search_popup(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from dasktoon_rig import parts as rig_parts
        rig = rig_of(context)
        obj = _active_part(rig).object
        if not self.material:
            return {'CANCELLED'}
        add_part(rig, obj, rig_parts.guess_role(self.material) or 'CLOTHING', name=self.material, scope='MATERIAL',
                 material=self.material)
        return {'FINISHED'}


class DASKTOON_OT_rig_remove_part(Operator):
    """Remove the active part from the rig; its weights stay until the next build"""
    bl_idname = "dasktoon.rig_remove_part"
    bl_label = "Remove Part"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        rig = rig_of(context)
        return rig is not None and _active_part(rig) is not None

    def execute(self, context):
        data = rig_of(context).data.dasktoon_rig
        index = data.active_part_index
        data.parts.remove(index)
        data.active_part_index = max(0, min(index, len(data.parts) - 1))
        return {'FINISHED'}


class DASKTOON_OT_rig_build(Operator):
    """Generate the hair and skirt chains and paint the weights of every part"""
    bl_idname = "dasktoon.rig_build"
    bl_label = "Build Rig"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return rig_of(context) is not None

    def execute(self, context):
        from dasktoon_rig import build
        rig = rig_of(context)
        try:
            result = build.build(context, rig, list(rig.data.dasktoon_rig.parts))
        except build.BuildError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        for warning in result.warnings:
            self.report({'WARNING'}, warning)
        self.report({'INFO'}, result.summary())
        return {'FINISHED'}


_rig_items = []


def _rigs(_self, context):
    _rig_items[:] = [(rig.name, rig.name, "") for rig in humanoid_rigs(context.scene)]
    return _rig_items


class DASKTOON_OT_rig_part_from_selection(Operator):
    """Make the selected vertices a part of the rig, kept in a new vertex group"""
    bl_idname = "dasktoon.rig_part_from_selection"
    bl_label = "Add Part from Selection"
    bl_options = {'REGISTER', 'UNDO'}

    part_name: StringProperty(name="Name", description="Name of the new part", default="Hair")
    role: EnumProperty(name="Role", description="How the part is rigged", items=ROLE_ITEMS, default='HAIR')
    rig: EnumProperty(name="Armature", description="Standard skeleton the part belongs to", items=_rigs)

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT' and bool(humanoid_rigs(context.scene))

    def invoke(self, context, _event):
        found = find_rig(context, context.object)
        if found is not None:
            self.rig = found.name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "part_name")
        layout.prop(self, "role")
        if len(humanoid_rigs(context.scene)) > 1:
            layout.prop(self, "rig")

    def execute(self, context):
        obj = context.object
        rig = context.scene.objects.get(self.rig) if self.rig else find_rig(context, obj)
        if rig is None:
            self.report({'ERROR'}, rpt_("No standard skeleton to add the part to"))
            return {'CANCELLED'}
        obj.update_from_editmode()
        selected = [v.index for v in obj.data.vertices if v.select]
        if not selected:
            self.report({'ERROR'}, rpt_("Select the vertices of the part first"))
            return {'CANCELLED'}
        name = self.part_name.strip() or "Part"
        bpy.ops.object.mode_set(mode='OBJECT')
        group = obj.vertex_groups.new(name="DT_" + name)
        group.add(selected, 1.0, 'REPLACE')
        bpy.ops.object.mode_set(mode='EDIT')
        add_part(rig, obj, self.role, name=name, scope='VERTEX_GROUP', vertex_group=group.name)
        self.report({'INFO'}, rpt_("Added part %s to %s") % (name, rig.name))
        return {'FINISHED'}


class DASKTOON_UL_rig_parts(UIList):
    """Parts of the anime rig"""

    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon=ROLE_ICONS[item.role])
        row.label(text=item.object.name if item.object is not None else "", translate=False)


class DaskRigPanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return rig_of(context) is not None


class DATA_PT_dasktoon_rig(DaskRigPanel, Panel):
    bl_label = "Anime Rig"

    def draw(self, _context):
        pass


class DATA_PT_dasktoon_rig_joints(DaskRigPanel, Panel):
    bl_label = "Joints"
    bl_parent_id = "DATA_PT_dasktoon_rig"

    def draw(self, context):
        from dasktoon_rig import skeleton
        layout = self.layout
        missing = skeleton.missing_bones(rig_of(context).data)
        if missing:
            layout.label(text=rpt_("Missing bones: %s") % ", ".join(missing), icon='ERROR', translate=False)
            layout.label(text="Add › Armature › Anime Humanoid adds a standard skeleton")
        else:
            layout.label(text="Standard skeleton", icon='CHECKMARK')
        row = layout.row(align=True)
        row.operator("dasktoon.rig_edit_joints", icon='EDITMODE_HLT')
        row.operator("dasktoon.rig_fit", icon='FULLSCREEN_ENTER')


class DATA_PT_dasktoon_rig_parts(DaskRigPanel, Panel):
    bl_label = "Parts"
    bl_parent_id = "DATA_PT_dasktoon_rig"

    def draw(self, context):
        layout = self.layout
        rig = rig_of(context)
        data = rig.data.dasktoon_rig
        row = layout.row()
        row.template_list("DASKTOON_UL_rig_parts", "", data, "parts", data, "active_part_index", rows=4)
        col = row.column(align=True)
        col.operator("dasktoon.rig_add_selected", text="", icon='ADD')
        col.operator("dasktoon.rig_add_material_part", text="", icon='MATERIAL')
        col.operator("dasktoon.rig_remove_part", text="", icon='REMOVE')
        part = _active_part(rig)
        if part is None:
            layout.label(text="Select meshes and press + to add them as parts")
            return
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(part, "object")
        layout.prop(part, "scope")
        obj = part.object
        if part.scope == 'MATERIAL' and obj is not None:
            layout.prop_search(part, "material", obj.data, "materials")
        elif part.scope == 'VERTEX_GROUP' and obj is not None:
            layout.prop_search(part, "vertex_group", obj, "vertex_groups")
        layout.prop(part, "role")
        if part.role in ('ACCESSORY', 'HAIR', 'SKIRT'):
            layout.prop_search(part, "bone", rig.data, "bones")
        if part.role in ('HAIR', 'SKIRT'):
            layout.prop(part, "bone_count")
        if part.role == 'SKIRT':
            layout.prop(part, "chain_count")


class DATA_PT_dasktoon_rig_build(DaskRigPanel, Panel):
    bl_label = "Build"
    bl_parent_id = "DATA_PT_dasktoon_rig"

    def draw(self, _context):
        layout = self.layout
        layout.operator("dasktoon.rig_build", icon='MOD_ARMATURE')
        layout.label(text="Build replaces the weights of every part", icon='INFO')


class DATA_PT_dasktoon_rig_mesh(Panel):
    bl_label = "Anime Rig"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'MESH' and bool(humanoid_rigs(context.scene))

    def draw(self, context):
        layout = self.layout
        obj = context.object
        rig = find_rig(context, obj)
        if rig is not None:
            layout.label(text=rig.name, icon='ARMATURE_DATA', translate=False)
            for part in rig.data.dasktoon_rig.parts:
                if part.object == obj:
                    row = layout.row()
                    row.label(text=part.name, translate=False)
                    row.prop(part, "role", text="")
        layout.operator("dasktoon.rig_part_from_selection", icon='ADD')
        if obj.mode != 'EDIT':
            layout.label(text="Select the vertices of a part in Edit Mode", icon='INFO')


def menu_func(self, _context):
    self.layout.operator(DASKTOON_OT_rig_add_humanoid.bl_idname, text="Anime Humanoid", icon='OUTLINER_OB_ARMATURE')


classes = (
    DaskRigPart,
    DaskRig,
    DASKTOON_OT_rig_add_humanoid,
    DASKTOON_OT_rig_edit_joints,
    DASKTOON_OT_rig_fit,
    DASKTOON_OT_rig_add_selected,
    DASKTOON_OT_rig_add_material_part,
    DASKTOON_OT_rig_remove_part,
    DASKTOON_OT_rig_build,
    DASKTOON_OT_rig_part_from_selection,
    DASKTOON_UL_rig_parts,
    DATA_PT_dasktoon_rig,
    DATA_PT_dasktoon_rig_joints,
    DATA_PT_dasktoon_rig_parts,
    DATA_PT_dasktoon_rig_build,
    DATA_PT_dasktoon_rig_mesh,
)


# bl_ui registers `classes`; register() adds the rig data to armatures and the Add › Armature entry.
def register():
    from .space_view3d import VIEW3D_MT_armature_add
    bpy.types.Armature.dasktoon_rig = PointerProperty(type=DaskRig)
    VIEW3D_MT_armature_add.append(menu_func)


def unregister():
    from .space_view3d import VIEW3D_MT_armature_add
    VIEW3D_MT_armature_add.remove(menu_func)
    del bpy.types.Armature.dasktoon_rig
```

- [ ] **Step 4: Đăng ký module** — `scripts/startup/bl_ui/__init__.py`: thêm `"dasktoon_rig",` sau
  `"dasktoon_shape_key_manager",`. CMake `dasktoon_rig_ui_test`; `TRANSLATED` += `"scripts/startup/bl_ui/dasktoon_rig.py"`.

- [ ] **Step 5: Bản dịch** — thêm vào cuối `VI` (trừ chữ Blender đã dịch và chữ đã có trong bảng):
```python
    # bl_ui/dasktoon_rig.py
    "Anime Humanoid": "Khung người anime",
    "Add the DaskToon standard skeleton, fitted to the selected meshes, which become its parts":
        "Thêm khung xương chuẩn của DaskToon, khớp với các mesh đang chọn và lấy chúng làm phần",
    "Edit Joints": "Sửa khớp",
    "Edit the joints of the skeleton with X-Axis Mirror on, so both sides move together":
        "Sửa khớp của khung xương với X-Axis Mirror bật, hai bên cùng di chuyển",
    "Fit to Parts": "Khớp theo các phần",
    "Move and scale the skeleton to the meshes of the parts; the joints you placed are replaced":
        "Dời và co giãn khung xương theo mesh của các phần; vị trí khớp bạn đã đặt sẽ bị thay",
    "Add Selected Meshes": "Thêm các mesh đang chọn",
    "Add each selected mesh as a part of the rig, with the role its name suggests":
        "Thêm mỗi mesh đang chọn thành một phần của rig, với vai trò đoán theo tên",
    "Add Material Part": "Thêm phần theo material",
    "Add the faces of one material of the active part's mesh as a new part":
        "Thêm các mặt mang một material của mesh thuộc phần đang chọn thành một phần mới",
    "Remove Part": "Xóa phần",
    "Remove the active part from the rig; its weights stay until the next build":
        "Xóa phần đang chọn khỏi rig; weight của nó còn giữ tới lần dựng sau",
    "Build Rig": "Dựng rig",
    "Generate the hair and skirt chains and paint the weights of every part":
        "Sinh chuỗi xương tóc, váy và vẽ weight cho mọi phần",
    "Add Part from Selection": "Thêm phần từ vùng chọn",
    "Make the selected vertices a part of the rig, kept in a new vertex group":
        "Biến các đỉnh đang chọn thành một phần của rig, lưu trong một vertex group mới",
    "Fit the joints in Edit Mode, then press Build Rig in Properties › Object Data":
        "Chỉnh khớp trong Edit Mode, rồi bấm Dựng rig ở Properties › Object Data",
    "The selected meshes are already parts": "Các mesh đang chọn đã là phần của rig",
    "No standard skeleton to add the part to": "Không có khung chuẩn nào để thêm phần vào",
    "Select the vertices of the part first": "Hãy chọn các đỉnh của phần trước",
    "Added part %s to %s": "Đã thêm phần %s vào %s",
    "Anime Rig": "Rig anime",
    "Joints": "Khớp",
    "Parts": "Các phần",
    "Missing bones: %s": "Thiếu xương: %s",
    "Add › Armature › Anime Humanoid adds a standard skeleton":
        "Add › Armature › Khung người anime thêm một khung chuẩn",
    "Standard skeleton": "Khung chuẩn",
    "Select meshes and press + to add them as parts": "Chọn mesh rồi bấm + để thêm chúng làm phần",
    "Build replaces the weights of every part": "Dựng lại sẽ thay weight của mọi phần",
    "Select the vertices of a part in Edit Mode": "Chọn các đỉnh của một phần trong Edit Mode",
    "A part of the character and how it is rigged": "Một phần của nhân vật và cách rig nó",
    "Name of the part; generated bones start with it": "Tên phần; tên các xương sinh ra bắt đầu bằng nó",
    "Mesh that holds the part": "Mesh chứa phần",
    "Scope": "Phạm vi",
    "Which vertices of the mesh make the part": "Những đỉnh nào của mesh tạo nên phần",
    "Whole Object": "Cả object",
    "Every vertex of the mesh": "Mọi đỉnh của mesh",
    "The faces that use a material": "Các mặt dùng một material",
    "The vertices of a vertex group": "Các đỉnh của một vertex group",
    "Material whose faces make the part": "Material có các mặt tạo nên phần",
    "Vertex group whose vertices make the part": "Vertex group có các đỉnh tạo nên phần",
    "Role": "Vai trò",
    "How the part is rigged": "Cách rig phần này",
    "Skin and face: automatic weights from the body bones": "Da và mặt: weight tự động theo xương thân",
    "Clothing": "Quần áo",
    "Follows the body: weights copied from the nearest Body surface": "Đi theo thân: weight chép từ bề mặt Body gần nhất",
    "Accessory": "Phụ kiện",
    "Rigid on one bone": "Gắn cứng vào một xương",
    "A chain of bones for each long lock": "Một chuỗi xương cho mỗi lọn tóc dài",
    "Skirt": "Váy",
    "Chains of bones around the hips": "Các chuỗi xương quanh hông",
    "Bone the part hangs from or sits on; empty picks one automatically (Head for hair, Hips for a skirt, the nearest "
    "bone for an accessory)":
        "Xương mà phần treo vào hoặc gắn lên; để trống thì tự chọn (Head cho tóc, Hips cho váy, xương gần nhất cho phụ "
        "kiện)",
    "Bones per Chain": "Số xương mỗi chuỗi",
    "Number of bones along each chain": "Số xương dọc mỗi chuỗi",
    "Chains": "Số chuỗi",
    "Number of chains around the skirt": "Số chuỗi quanh váy",
    "The parts of an anime rig": "Các phần của một rig anime",
    "Active Part": "Phần đang chọn",
    "Part shown below the list": "Phần hiện bên dưới danh sách",
    "Parts of the anime rig": "Các phần của rig anime",
    "Material whose faces make the new part": "Material có các mặt tạo nên phần mới",
    "Name of the new part": "Tên của phần mới",
    "Standard skeleton the part belongs to": "Khung chuẩn chứa phần này",
```
  Trước khi thêm, kiểm tra không trùng khóa đã có (`"Body"` đã có). Chạy `run dasktoon_rig_ui_test` để biết chữ nào
  Blender chưa dịch mà bảng còn thiếu.

- [ ] **Step 6: Chạy test, thấy PASS** — `sync; run dasktoon_rig_ui_test; run dasktoon_translations_test; run dasktoon_ui_layout_test`.

- [ ] **Step 7: Commit** — `git commit -m "feat: Anime Rig panels and Add › Armature › Anime Humanoid"`.

---

### Task 7: Engine Export xuất Humanoid

**Files:**
- Modify: `scripts/modules/dasktoon_export/unity_yaml.py` (`model_meta(..., humanoid=False)`),
  `scripts/modules/dasktoon_export/__init__.py` (`_write_model` truyền `humanoid=_humanoid(objects)`)
- Test: `tests/python/dasktoon_export_yaml_test.py`, `tests/python/dasktoon_rig_build_test.py` (thêm `HumanoidTest`)

**Interfaces:**
- Consumes: `skeleton.is_humanoid`.
- Produces: `unity_yaml.model_meta(guid, materials, import_animation, blend_shape_normals=True, humanoid=False)`;
  `dasktoon_export._humanoid(objects) -> bool`.

- [ ] **Step 1: Viết test** — trong `dasktoon_export_yaml_test.py`, cạnh `test_model_meta_turns_blend_shape_normals_off_for_face_shading`:
```python
    def test_model_meta_humanoid(self):
        self.assertIn("  animationType: 2\n", uy.model_meta(TEX, {}, True))
        self.assertIn("  animationType: 3\n", uy.model_meta(TEX, {}, True, humanoid=True))
```
  và trong `dasktoon_rig_build_test.py`:
```python
class HumanoidTest(unittest.TestCase):
    def test_export_is_humanoid_for_one_standard_skeleton(self):
        import dasktoon_export
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        rig = fx.rig_for()
        self.assertTrue(dasktoon_export._humanoid([rig] + list(objs.values())))
        self.assertFalse(dasktoon_export._humanoid(list(objs.values())))
        second = fx.rig_for()
        self.assertFalse(dasktoon_export._humanoid([rig, second]))
        from dasktoon_rig import skeleton
        with skeleton.editing(bpy.context, second) as edit:
            edit.remove(edit["Head"])
        self.assertFalse(dasktoon_export._humanoid([second]))
```

- [ ] **Step 2: Chạy test, thấy FAIL** — `TypeError: model_meta() got an unexpected keyword argument 'humanoid'`.

- [ ] **Step 3: Viết code** — `unity_yaml.model_meta`:
```python
def model_meta(guid, materials, import_animation, blend_shape_normals=True, humanoid=False):
    """... `humanoid` makes Unity build a Humanoid avatar, mapping the bones by name (anime rig spec 8)."""
    ...
        "  animationType: %d" % (3 if humanoid else 2),
```
  `dasktoon_export/__init__.py`:
```python
def _humanoid(objects):
    """True when the model has exactly one armature and it is a DaskToon standard skeleton (anime rig spec 8)."""
    from dasktoon_rig import skeleton
    rigs = [obj for obj in objects if obj.type == 'ARMATURE']
    return len(rigs) == 1 and skeleton.is_humanoid(rigs[0])
```
  và trong `_write_model`: `unity_yaml.model_meta(guid, mat_guids, options.include_animation,
  blend_shape_normals=not rep.face_meshes, humanoid=_humanoid(objects))`.

- [ ] **Step 4: Chạy test, thấy PASS** — `sync; run dasktoon_export_yaml_test; run dasktoon_rig_build_test; run dasktoon_export_fbx_test; run dasktoon_translations_test`.

- [ ] **Step 5: Commit** — `git commit -m "feat: Engine Export marks a model with a standard skeleton as Humanoid"`.

---

### Task 8: Kiểm tra toàn bộ, báo cáo

- [ ] **Step 1:** Chạy mọi test DaskToon (`for t in $(ls tests/python/dasktoon_*_test.py)`; trừ
  `dasktoon_project_window_test`, `dasktoon_unity_*` cần Unity) và ghi số test.
- [ ] **Step 2:** Thử tay trong cửa sổ thật (script `--python` không `--background`): thêm khung cho nhân vật thử, Build,
  chụp panel Anime Rig (Object Data) và tư thế xoay `LeftUpperArm`, `Hair_1` để thấy weight đúng; lưu ảnh vào
  `docs/superpowers/reports/anime-rig/`.
- [ ] **Step 3:** Viết `docs/superpowers/reports/2026-10-06-dasktoon-anime-rig-r1-report.md` (tiếng Việt): đã làm gì,
  test, ảnh, các quyết định tự chốt, việc còn lại (R2, R3, A).
- [ ] **Step 4:** Commit `docs: add the anime rig R1 report`.
