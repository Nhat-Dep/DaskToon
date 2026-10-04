# DaskToon: bóng mặt anime bằng khối trứng (Face Shading) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng đã chọn chạy **tự động, inline** (superpowers:executing-plans) trên nhánh `dasktoon-face-shading`, commit từng task, tự quyết các điểm mơ hồ và ghi vào báo cáo. Không push.

**Goal:** Một nút *Tạo bóng mặt anime* thay normal vùng mặt bằng normal của một khối trứng (ellipsoid) gắn vào xương đầu, chỉnh được bằng 4 thanh trượt và bằng cách kéo khối trứng; Engine Export ghi đúng bóng mặt đó sang Unity.

**Architecture:**
- `scripts/startup/bl_ui/dasktoon_face_shading_nodes.py`: node group Geometry Nodes dùng chung `DaskToon_FaceShading` (có số phiên bản) và các hàm quản lý modifier **DaskToon Face Shading**.
- `scripts/startup/bl_ui/dasktoon_face_shading.py`: tự căn khối trứng, vertex group `DT_Face`, khối trứng (Empty) gắn vào xương đầu, các operator và panel *DaskToon › Bóng mặt* (thay panel cũ, công cụ cũ vào *Nâng cao*).
- `scripts/modules/dasktoon_export/face_shading.py`: khi export, ghi tạm normal hình trứng ở tư thế nghỉ thành custom normal rồi trả mesh về nguyên trạng.
- Outline (Dự án 1) lên phiên bản lõi 2: hướng đẩy đọc normal hình học, vỏ được tô bằng normal đảo của nguồn (giống pass outline của Unity).

**Tech Stack:** Python `bpy` + `numpy`, Geometry Nodes của DaskToon 5.2, `unittest` chạy trong DaskToon, Unity 6000.5.4f1 batchmode cho bài so sánh render.

**Spec:** `docs/superpowers/specs/2026-10-04-dasktoon-face-shading-design.md` (liên quan: `docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md`, `docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md`).

---

## Môi trường và các lệnh dùng chung

Mọi lệnh chạy trong Git Bash, thư mục gốc là `d:/DaskToon`.

```bash
DT=/d/build_windows_x64_vc17_Release/bin/Release/DaskToon.exe
BUILD=/d/build_windows_x64_vc17_Release
```

- **Đồng bộ script** (không sửa C++/GLSL nên không cần build). Chạy trước mỗi lần test:
  ```bash
  cp -r scripts/startup/. "$BUILD/bin/Release/5.2/scripts/startup/" && cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"
  ```
- **Chạy một file test** (exit code 0 là PASS):
  ```bash
  "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/<file>.py 2>&1 | tail -30
  ```
- **Trích code từ kế hoạch:** mỗi khối code tạo file mới có dòng ``File: `đường/dẫn` `` ngay phía trên.

### Những điều đã kiểm chứng trong DaskToon 5.2 (headless, trước khi viết kế hoạch)

- Node **Normal** (mặc định, không bật `legacy_corner_normals`) trả về custom normal ở cả domain Corner và Point.
  Output **True Normal** ở domain Point bằng đúng normal hình học của đỉnh.
- **Set Mesh Normal** chế độ `FREE`, domain `CORNER`: input `Custom Normal` là field ngầm (mặc định là Normal hiện có), phải
  nối link thì giá trị mới có tác dụng. Kết quả là attribute `custom_normal` (`FLOAT_VECTOR`, Corner).
- **Flip Faces** không đảo custom normal. **Join Geometry** điền normal thật cho phần không có custom normal.
- **Object Info** (`RELATIVE`) cho ma trận `obj.matrix_world⁻¹ @ proxy.matrix_world`; không có object thì là ma trận đơn vị.
- **Map Range** `SMOOTHSTEP` là smoothstep có kẹp `[0, 1]`. Khi `From Min == From Max` nó chia cho 0 (ra 0).
- Input của modifier Geometry Nodes nằm ở `modifier.properties.inputs.<identifier>.value` (không còn là ID property).
  Ghi từ Python **không** tính lại object và **không** dựng lại quan hệ depsgraph (Object Info của khối trứng);
  gán lại `modifier.node_group = modifier.node_group` thì làm cả hai. Sửa trong giao diện thì Blender tự cập nhật.
- `normals_split_custom_set` nhận mảng numpy, và **có thể đánh dấu thêm cạnh sắc** (`sharp_edge`) khi normal trong một
  "quạt" khác nhau. Lưu/khôi phục thô attribute `custom_normal` (`INT16_2D`) và `sharp_edge` cho kết quả y hệt.
- Empty gắn xương (`parent_type='BONE'`) với `matrix_parent_inverse = (arm.matrix_world @ bone.matrix_local @
  Translation(0, bone.length, 0))⁻¹` thì ở tư thế nghỉ nằm đúng ma trận mong muốn; `pose_position='REST'` đưa nó về đó.
- `obj.show_only_shape_key = True` + `active_shape_key_index = 0` cho mesh đánh giá chỉ có Basis.

## Global Constraints

- Không push. Commit từng task trên nhánh `dasktoon-face-shading`.
- Không sửa C++/GLSL của DaskToon, không sửa shader Unity, không sửa node Face Shadow (SDF).
- Không bao giờ ghi vào project Unity của người dùng trong `D:\Unity\`; test Unity chỉ dùng project tạm `%TEMP%/dasktoon_unity_test`.
- Không lưu hay sửa file nhân vật của người dùng (`tdt.blend`): chỉ mở headless để render ảnh duyệt.
- Tên cố định (spec 3–6):
  - Node group `DaskToon_FaceShading`, phiên bản lưu ở `tree["dasktoon_version"]`; modifier `DaskToon Face Shading`.
  - Input của modifier: `Proxy` (Object), `Coverage` 1.0, `Falloff` 0.3, `Nose Keep` 0.6, `Chin Keep` 0.8, `Mask Name` "DT_Face".
  - Vertex group `DT_Face`; ID property trên mesh object `dasktoon_face_proxy`.
  - Khối trứng: Empty `SPHERE`, display size 1, scale `(rx, ry, rz)`, `hide_render`, tên `DT_FaceProxy::<armature>:<xương>`
    (hoặc `DT_FaceProxy::<object>`), cùng collection với mesh, gắn vào xương đầu.
  - Panel *DaskToon › Bóng mặt* (VIEW_3D, UI, tab DaskToon), nút *Tạo bóng mặt anime*, *Chọn khối trứng*, *Căn lại khối trứng*,
    *Gỡ bóng mặt*, thanh trượt *Độ phủ*, *Vùng chuyển*, *Giữ bóng mũi*, *Giữ bóng cằm*; mục *Nâng cao* chứa công cụ cũ.
- Công thức (spec 4), domain Corner, không gian object:
  `q = M⁻¹P`, `r = |q|`, `d = q/r`, `n_e = normalize((L⁻¹)ᵀd)`, `down = normalize(L(0,0,−1))`,
  `region = DT_Face × (1 − smoothstep(1, 1+Falloff, r))`,
  `nose = smoothstep(0.80, 0.95, −d.y) × smoothstep(0.02, 0.08, r−1)`,
  `chin = smoothstep(0.25, 0.55, −d.z) × smoothstep(0.35, 0.70, N₀·down)`,
  `w = Coverage × region × (1 − NoseKeep×nose) × (1 − ChinKeep×chin)`, `N = normalize(mix(N₀, n_e, w))`.
- Tự căn (spec 5): xương đầu theo tên `head`, `j_bip_c_head`, `mixamorig:head`, `頭` (không phân biệt hoa thường), rồi tên chứa
  `head` không chứa `end`/`top`/`tip`/`nub`; đỉnh đầu = trọng số ≥ 0.5; dải giữa `|x − tâm_x| ≤ 0.25 × chiều rộng`;
  `y_front` = phân vị 5%; `ry = max(nửa chiều sâu, 0.85 × rx)`; tâm y = `y_front + ry`.
- Export (spec 6): `.meta` của FBX đặt `blendShapeNormalImportMode: 2` khi có mesh dùng bóng mặt (mặc định vẫn là 0).
- Sai số trong test Unity: ≤ 0.03 trên giá trị sRGB như các trường hợp khác.
- Lỗ hổng AI Bridge (cổng 9998, commit b9dbe7997f9) vẫn chưa sửa: nhắc lại trong báo cáo cuối. Không chép access token trong
  `Editor.log` của Unity.

## Review Focus

1. **Mesh có cạnh sắc hoặc mặt phẳng (flat) trong vùng mặt.** N₀ khác nhau theo góc; người dùng mong cạnh sắc ngoài vùng mặt
   giữ nguyên, và sau export attribute `sharp_edge` y như trước (vì `normals_split_custom_set` có thể đánh dấu thêm cạnh sắc).
   Test: Task 5 `test_existing_custom_normals_and_sharp_edges_come_back_exactly`.
2. **Bấm *Tạo bóng mặt* khi nhân vật đang tạo dáng** (đầu đang quay). Khối trứng phải được căn theo tư thế nghỉ và đi theo xương.
   Test: Task 2 `test_setup_while_posed_fits_the_rest_pose`.
3. **Rig không nằm ở gốc toạ độ / có xoay, scale.** Tự căn dùng toạ độ world, Geometry Nodes dùng ma trận tương đối.
   Test: Task 1 (object bị dời và xoay), Task 2 `test_fit_with_a_transformed_rig`.
4. **Hai object dùng chung một mesh data** khi export: chỉ ghi một lần, trả về đúng một lần.
   Test: Task 5 `test_shared_mesh_data_is_baked_once`.
5. **Export lỗi giữa chừng** (ghi FBX thất bại): mesh phải được trả về nguyên trạng.
   Test: Task 5 `test_failed_export_gives_the_mesh_back`.

---

### Task 1: Node group `DaskToon_FaceShading`, modifier và đầu thử

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_face_shading_nodes.py`
- Create: `tests/python/dasktoon_face_shading_nodes_test.py`
- Modify: `tests/python/dasktoon_test_utils.py` (thêm `add_test_head`)
- Modify: `tests/python/CMakeLists.txt` (đăng ký test)

**Interfaces:**
- Consumes: `bl_ui.dasktoon_outline_nodes`: `MODIFIER_NAME`, `_feed`, `_math`, `_new_socket`, `_vector_math`.
- Produces:
  - `fsn.GROUP = "DaskToon_FaceShading"`, `fsn.VERSION = 1`, `fsn.MODIFIER_NAME = "DaskToon Face Shading"`, `fsn.MASK_NAME = "DT_Face"`.
  - `fsn.ensure_group() -> bpy.types.GeometryNodeTree`
  - `fsn.get_modifier(obj) -> NodesModifier | None` (chỉ trả modifier đang chạy đúng node group)
  - `fsn.ensure_modifier(obj) -> NodesModifier` (tạo hoặc sửa, đặt ngay trước `DaskToon Outline`)
  - `fsn.input_socket(modifier, name)` → struct có `.value` (dùng cho `layout.prop(..., "value")`)
  - `fsn.set_inputs(modifier, {name: value})` (ghi rồi gán lại node group để depsgraph cập nhật)
  - `fsn.remove_modifier(obj)`
  - `tu.add_test_head(radius=0.1, centre=(0, 0, 1.5), with_armature=True, name="Head") -> (head, rig | None)`;
    `head["dt_skin_vertices"]` = số đỉnh da (đứng đầu mảng đỉnh), mảnh tóc là các đỉnh sau đó.

- [ ] **Step 1: Thêm đầu thử vào `tests/python/dasktoon_test_utils.py`**

Thêm sau hàm `add_sphere`:

```python
TEST_HEAD_SEGMENTS = (48, 24)


def add_test_head(radius=0.1, centre=(0.0, 0.0, 1.5), with_armature=True, name="Head"):
    """Face shading test head (face spec 8), upright and facing -Y with the object at the world origin like a
    character: a UV sphere skin with a nose bump and two eye dents, then a hair cap that is a separate island. With an
    armature, every vertex is weighted 1 to bone "Head" of armature "Rig". Returns (head, rig or None);
    head["dt_skin_vertices"] is the number of skin vertices, which come first."""
    import bmesh
    from mathutils import Matrix, Vector
    bm = bmesh.new()
    bm.loops.layers.uv.verify()
    segments, rings = TEST_HEAD_SEGMENTS
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius, calc_uvs=True)
    skin = len(bm.verts)
    for v in bm.verts:
        d = v.co.normalized()
        if d.y < 0.0:
            nose = max(0.0, 1.0 - (d.x / 0.2) ** 2 - ((d.z + 0.15) / 0.2) ** 2)
            dents = sum(max(0.0, 1.0 - ((d.x - side) / 0.16) ** 2 - ((d.z - 0.12) / 0.12) ** 2) for side in (-0.38, 0.38))
            v.co += d * radius * (0.12 * nose - 0.08 * dents)
    hair = Matrix.LocRotScale(Vector((0.0, 0.25 * radius, 0.45 * radius)), None, Vector((1.1, 1.1, 0.7)))
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=radius, matrix=hair, calc_uvs=True)
    bmesh.ops.translate(bm, verts=list(bm.verts), vec=Vector(centre))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.shade_smooth()
    head = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(head)
    head["dt_skin_vertices"] = skin
    rig = None
    if with_armature:
        rig = bpy.data.objects.new("Rig", bpy.data.armatures.new("Rig"))
        bpy.context.scene.collection.objects.link(rig)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        bone = rig.data.edit_bones.new("Head")
        bone.head = (centre[0], centre[1], centre[2] - radius)
        bone.tail = (centre[0], centre[1], centre[2] + radius)
        bpy.ops.object.mode_set(mode='OBJECT')
        head.vertex_groups.new(name="Head").add(list(range(len(mesh.vertices))), 1.0, 'REPLACE')
        head.parent = rig
        head.modifiers.new("Armature", 'ARMATURE').object = rig
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == head)
    bpy.context.view_layer.objects.active = head
    return head, rig
```

- [ ] **Step 2: Viết test của node group (chưa có module nên phải đỏ)**

File: `tests/python/dasktoon_face_shading_nodes_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Face shading Geometry Nodes against a numpy reference of the formula in face spec 4."""

import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_face_shading_nodes as fsn  # noqa: E402
from bl_ui import dasktoon_outline_nodes as outline_nodes  # noqa: E402


def smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def reference(position, n0, mask, matrix, coverage, falloff, nose_keep, chin_keep):
    """Face spec 4 per corner, in object space: position and n0 are (n, 3), mask (n,), matrix the proxy relative to the
    object. Returns a dict with the result N and the intermediate terms."""
    m = np.array(matrix)
    inv = np.linalg.inv(m)
    q = position @ inv[:3, :3].T + inv[:3, 3]
    r = np.linalg.norm(q, axis=1)
    d = q / r[:, None]
    n_e = normalize(d @ inv[:3, :3])  # (L^-1)^T d, written for row vectors
    down = normalize(m[:3, :3] @ np.array([0.0, 0.0, -1.0]))
    region = mask * (1.0 - smoothstep(1.0, 1.0 + falloff, r))
    nose = smoothstep(0.80, 0.95, -d[:, 1]) * smoothstep(0.02, 0.08, r - 1.0)
    chin = smoothstep(0.25, 0.55, -d[:, 2]) * smoothstep(0.35, 0.70, n0 @ down)
    w = coverage * region * (1.0 - nose_keep * nose) * (1.0 - chin_keep * chin)
    return {"N": normalize(n0 + (n_e - n0) * w[:, None]), "n_e": n_e, "w": w, "r": r, "nose": nose, "chin": chin}


def corner_normals(obj, evaluated=True):
    holder = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else None
    mesh = holder.to_mesh() if evaluated else obj.data
    values = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.corner_normals.foreach_get("vector", values)
    if holder is not None:
        holder.to_mesh_clear()
    return values.reshape(-1, 3).astype(np.float64)


def degrees(a, b):
    return np.degrees(np.arccos(np.clip((normalize(a) * normalize(b)).sum(axis=1), -1.0, 1.0)))


class FaceShadingNodesTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        self.obj, _rig = tu.add_test_head(with_armature=False)
        self.obj.location = (0.3, -0.2, 0.1)  # the proxy matrix is relative to the object
        self.obj.rotation_euler = (0.0, 0.0, 0.4)
        bpy.context.view_layer.update()
        self.obj.vertex_groups.new(name=fsn.MASK_NAME).add(list(range(len(self.obj.data.vertices))), 1.0, 'REPLACE')
        self.proxy = bpy.data.objects.new("Proxy", None)
        bpy.context.scene.collection.objects.link(self.proxy)
        self.place_proxy(Vector((0.0, 0.0, 1.5)), Vector((0.095, 0.1, 0.1)))
        self.mod = fsn.ensure_modifier(self.obj)
        fsn.set_inputs(self.mod, {"Proxy": self.proxy})

    def place_proxy(self, centre, radii):
        self.proxy.matrix_world = self.obj.matrix_world @ Matrix.LocRotScale(centre, Euler((0.1, 0.0, 0.2)), radii)
        bpy.context.view_layer.update()

    def run_case(self, coverage=1.0, falloff=0.3, nose_keep=0.6, chin_keep=0.8):
        """(N0, N from the modifier, reference terms); asserts that the modifier matches the reference within 1 degree."""
        fsn.set_inputs(self.mod, {"Coverage": coverage, "Falloff": falloff, "Nose Keep": nose_keep,
                                  "Chin Keep": chin_keep})
        self.mod.show_viewport = False
        n0 = corner_normals(self.obj)
        self.mod.show_viewport = True
        got = corner_normals(self.obj)
        mesh = self.obj.data
        corner_vert = np.empty(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", corner_vert)
        co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", co)
        weights = np.zeros(len(mesh.vertices))
        group = self.obj.vertex_groups.get(fsn.MASK_NAME)
        for v in mesh.vertices:
            for g in v.groups:
                if group is not None and g.group == group.index:
                    weights[v.index] = g.weight
        relative = self.obj.matrix_world.inverted() @ self.proxy.matrix_world
        ref = reference(co.reshape(-1, 3).astype(np.float64)[corner_vert], n0, weights[corner_vert], relative,
                        coverage, falloff, nose_keep, chin_keep)
        self.assertLessEqual(degrees(got, ref["N"]).max(), 1.0)
        return n0, got, ref

    def test_matches_the_reference_with_the_defaults(self):
        n0, got, _ref = self.run_case()
        self.assertGreater(degrees(got, n0).max(), 5.0)

    def test_full_coverage_without_keeps_is_the_ellipsoid_normal(self):
        self.place_proxy(Vector((0.0, 0.0, 1.5)), Vector((0.12, 0.13, 0.12)))  # the skin lies inside: region = 1
        _n0, got, ref = self.run_case(nose_keep=0.0, chin_keep=0.0)
        inside = ref["r"] <= 1.0
        self.assertGreater(inside.sum(), 100)
        self.assertLessEqual(degrees(got[inside], ref["n_e"][inside]).max(), 1.0)

    def test_coverage_zero_changes_nothing(self):
        n0, got, _ref = self.run_case(coverage=0.0)
        self.assertLessEqual(degrees(got, n0).max(), 0.1)

    def test_outside_the_falloff_is_unchanged(self):
        self.place_proxy(Vector((0.0, 0.0, 1.5)), Vector((0.05, 0.05, 0.05)))
        n0, got, ref = self.run_case(falloff=0.3)
        outside = ref["r"] > 1.3
        self.assertGreater(outside.sum(), 100)
        self.assertLessEqual(degrees(got[outside], n0[outside]).max(), 0.1)

    def test_nose_keep_keeps_the_real_nose_normal(self):
        n0, kept, ref = self.run_case(nose_keep=1.0, chin_keep=0.0)
        tip = ref["nose"] >= 0.999
        self.assertGreaterEqual(tip.sum(), 1)
        self.assertLessEqual(degrees(kept[tip], n0[tip]).max(), 0.1)
        bump = ref["nose"] >= 0.5
        _n0, free, _ref = self.run_case(nose_keep=0.0, chin_keep=0.0)
        self.assertGreater(degrees(free[bump], n0[bump]).mean(), degrees(kept[bump], n0[bump]).mean() + 1.0)

    def test_chin_keep_keeps_the_underside(self):
        n0, got, ref = self.run_case(nose_keep=0.0, chin_keep=1.0)
        chin = ref["chin"] >= 0.999
        self.assertGreaterEqual(chin.sum(), 4)
        self.assertLessEqual(degrees(got[chin], n0[chin]).max(), 0.1)

    def test_moving_the_proxy_changes_the_normals(self):
        _n0, before, _ref = self.run_case()
        self.place_proxy(Vector((0.03, 0.0, 1.5)), Vector((0.095, 0.1, 0.1)))
        _n0, after, _ref = self.run_case()
        self.assertGreater(degrees(before, after).max(), 1.0)

    def test_missing_mask_changes_nothing(self):
        self.obj.vertex_groups.remove(self.obj.vertex_groups[fsn.MASK_NAME])
        n0, got, _ref = self.run_case()
        self.assertLessEqual(degrees(got, n0).max(), 0.1)

    def test_existing_custom_normals_are_the_base(self):
        mesh = self.obj.data
        geometric = corner_normals(self.obj, evaluated=False)
        mesh.normals_split_custom_set_from_vertices([(v.normal + Vector((0.4, 0.0, 0.0))).normalized()
                                                     for v in mesh.vertices])
        mesh.update()
        custom = corner_normals(self.obj, evaluated=False)
        self.assertGreater(degrees(custom, geometric).max(), 5.0)
        n0, _got, _ref = self.run_case(coverage=0.5)
        self.assertLessEqual(degrees(n0, custom).max(), 0.1)  # N0 is the custom normal, not the geometric one

    def test_group_is_rebuilt_when_its_version_differs(self):
        tree = fsn.ensure_group()
        tree["dasktoon_version"] = 0
        rebuilt = fsn.ensure_group()
        self.assertEqual(rebuilt, tree)
        self.assertEqual(rebuilt["dasktoon_version"], fsn.VERSION)
        self.assertEqual([s.name for s in rebuilt.interface.items_tree if s.in_out == 'INPUT'],
                         ["Geometry", "Proxy", "Coverage", "Falloff", "Nose Keep", "Chin Keep", "Mask Name"])

    def test_modifier_goes_right_before_the_outline(self):
        obj = tu.add_sphere(segments=8, rings=4)
        obj.modifiers.new("Armature", 'ARMATURE')
        obj.modifiers.new(outline_nodes.MODIFIER_NAME, 'NODES')
        fsn.ensure_modifier(obj)
        self.assertEqual([m.name for m in obj.modifiers], ["Armature", fsn.MODIFIER_NAME, outline_nodes.MODIFIER_NAME])
        plain = tu.add_sphere(segments=8, rings=4)
        plain.modifiers.new("Armature", 'ARMATURE')
        fsn.ensure_modifier(plain)
        self.assertEqual([m.name for m in plain.modifiers], ["Armature", fsn.MODIFIER_NAME])
        self.assertEqual(fsn.ensure_modifier(plain), plain.modifiers[fsn.MODIFIER_NAME])
        self.assertEqual(len(plain.modifiers), 2)

    def test_get_modifier_ignores_a_modifier_without_the_group(self):
        obj = tu.add_sphere(segments=8, rings=4)
        obj.modifiers.new(fsn.MODIFIER_NAME, 'NODES')
        self.assertIsNone(fsn.get_modifier(obj))
        modifier = fsn.ensure_modifier(obj)
        self.assertEqual(fsn.get_modifier(obj), modifier)
        fsn.remove_modifier(obj)
        self.assertEqual(len(obj.modifiers), 0)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 3: Chạy test, phải đỏ**

Run: đồng bộ script rồi `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_face_shading_nodes_test.py 2>&1 | tail -30`
Expected: FAIL — `ImportError`/`ModuleNotFoundError: ... dasktoon_face_shading_nodes`.

- [ ] **Step 4: Viết module node group**

File: `scripts/startup/bl_ui/dasktoon_face_shading_nodes.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Geometry Nodes of DaskToon face shading (docs/superpowers/specs/2026-10-04-dasktoon-face-shading-design.md,
section 4): the corner normals of the face lean towards the normals of an ellipsoid proxy. Builders and modifier
helpers only."""

import bpy

from .dasktoon_outline_nodes import MODIFIER_NAME as OUTLINE_MODIFIER
from .dasktoon_outline_nodes import _feed, _math, _new_socket, _vector_math

GROUP = "DaskToon_FaceShading"
VERSION = 1
MODIFIER_NAME = "DaskToon Face Shading"
MASK_NAME = "DT_Face"
# Group inputs after Geometry: (name, socket type, default, min, max). Falloff stays above 0 because Map Range divides
# by From Max - From Min.
INPUTS = (
    ("Proxy", 'NodeSocketObject', None, None, None),
    ("Coverage", 'NodeSocketFloat', 1.0, 0.0, 1.0),
    ("Falloff", 'NodeSocketFloat', 0.3, 0.01, 2.0),
    ("Nose Keep", 'NodeSocketFloat', 0.6, 0.0, 1.0),
    ("Chin Keep", 'NodeSocketFloat', 0.8, 0.0, 1.0),
    ("Mask Name", 'NodeSocketString', MASK_NAME, None, None),
)


def _smoothstep(tree, edge0, edge1, x):
    """Clamped smoothstep: Map Range in Smooth Step mode."""
    node = tree.nodes.new('ShaderNodeMapRange')
    node.interpolation_type = 'SMOOTHSTEP'
    _feed(tree, node.inputs["Value"], x)
    _feed(tree, node.inputs["From Min"], edge0)
    _feed(tree, node.inputs["From Max"], edge1)
    return node.outputs["Result"]


def ensure_group():
    tree = bpy.data.node_groups.get(GROUP)
    if tree is not None and tree.get("dasktoon_version") == VERSION:
        return tree
    if tree is None:
        tree = bpy.data.node_groups.new(GROUP, 'GeometryNodeTree')
    else:
        tree.nodes.clear()
        tree.interface.clear()
    tree["dasktoon_version"] = VERSION
    _new_socket(tree, "Geometry", 'INPUT', 'NodeSocketGeometry')
    for name, socket_type, default, low, high in INPUTS:
        socket = _new_socket(tree, name, 'INPUT', socket_type, default)
        if low is not None:
            socket.min_value = low
            socket.max_value = high
    _new_socket(tree, "Geometry", 'OUTPUT', 'NodeSocketGeometry')

    nodes, links = tree.nodes, tree.links
    group_in, group_out = nodes.new('NodeGroupInput'), nodes.new('NodeGroupOutput')
    inp = group_in.outputs

    # M: the proxy relative to this object. In the proxy's own space the proxy is the unit sphere.
    info = nodes.new('GeometryNodeObjectInfo')
    info.transform_space = 'RELATIVE'
    links.new(inp["Proxy"], info.inputs["Object"])
    invert = nodes.new('FunctionNodeInvertMatrix')
    links.new(info.outputs["Transform"], invert.inputs["Matrix"])
    to_proxy = nodes.new('FunctionNodeTransformPoint')
    links.new(nodes.new('GeometryNodeInputPosition').outputs[0], to_proxy.inputs["Vector"])
    links.new(invert.outputs["Matrix"], to_proxy.inputs["Transform"])
    q = to_proxy.outputs[0]
    r = _vector_math(tree, 'LENGTH', q)
    d = _vector_math(tree, 'NORMALIZE', q)

    # n_e = normalize((L^-1)^T d), the ellipsoid normal through the point; down = normalize(L (0, 0, -1)).
    transpose = nodes.new('FunctionNodeTransposeMatrix')
    links.new(invert.outputs["Matrix"], transpose.inputs["Matrix"])
    ellipsoid = nodes.new('FunctionNodeTransformDirection')
    links.new(d, ellipsoid.inputs["Direction"])
    links.new(transpose.outputs["Matrix"], ellipsoid.inputs["Transform"])
    n_e = _vector_math(tree, 'NORMALIZE', ellipsoid.outputs[0])
    down_dir = nodes.new('FunctionNodeTransformDirection')
    down_dir.inputs["Direction"].default_value = (0.0, 0.0, -1.0)
    links.new(info.outputs["Transform"], down_dir.inputs["Transform"])
    down = _vector_math(tree, 'NORMALIZE', down_dir.outputs[0])

    # N0: the corner normal as it is, custom normals included.
    n0 = nodes.new('GeometryNodeInputNormal').outputs["Normal"]
    split = nodes.new('ShaderNodeSeparateXYZ')
    links.new(d, split.inputs[0])
    mask = nodes.new('GeometryNodeInputNamedAttribute')
    mask.data_type = 'FLOAT'
    links.new(inp["Mask Name"], mask.inputs["Name"])

    outer = _smoothstep(tree, 1.0, _math(tree, 'ADD', inp["Falloff"], 1.0), r)
    region = _math(tree, 'MULTIPLY', mask.outputs["Attribute"], _math(tree, 'SUBTRACT', 1.0, outer))
    nose = _math(tree, 'MULTIPLY',
                 _smoothstep(tree, 0.80, 0.95, _math(tree, 'MULTIPLY', split.outputs["Y"], -1.0)),
                 _smoothstep(tree, 0.02, 0.08, _math(tree, 'SUBTRACT', r, 1.0)))
    chin = _math(tree, 'MULTIPLY',
                 _smoothstep(tree, 0.25, 0.55, _math(tree, 'MULTIPLY', split.outputs["Z"], -1.0)),
                 _smoothstep(tree, 0.35, 0.70, _vector_math(tree, 'DOT_PRODUCT', n0, down)))
    keep_nose = _math(tree, 'SUBTRACT', 1.0, _math(tree, 'MULTIPLY', inp["Nose Keep"], nose))
    keep_chin = _math(tree, 'SUBTRACT', 1.0, _math(tree, 'MULTIPLY', inp["Chin Keep"], chin))
    weight = _math(tree, 'MULTIPLY', _math(tree, 'MULTIPLY', inp["Coverage"], region),
                   _math(tree, 'MULTIPLY', keep_nose, keep_chin))
    lean = _vector_math(tree, 'SCALE', _vector_math(tree, 'SUBTRACT', n_e, n0), scale=weight)
    normal = _vector_math(tree, 'NORMALIZE', _vector_math(tree, 'ADD', n0, lean))

    set_normal = nodes.new('GeometryNodeSetMeshNormal')
    set_normal.mode = 'FREE'
    set_normal.domain = 'CORNER'
    links.new(inp["Geometry"], set_normal.inputs["Mesh"])
    links.new(normal, set_normal.inputs["Custom Normal"])
    links.new(set_normal.outputs[0], group_out.inputs["Geometry"])
    return tree


def get_modifier(obj):
    """obj's Face Shading modifier when it runs DaskToon's node group, else None."""
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is None or modifier.type != 'NODES' or modifier.node_group is None:
        return None
    return modifier if modifier.node_group.name == GROUP else None


def input_socket(modifier, name):
    """The modifier's input `name`; its `.value` is what the panel's slider shows."""
    identifier = modifier.node_group.interface.items_tree[name].identifier
    return getattr(modifier.properties.inputs, identifier)


def set_inputs(modifier, values):
    """Python writes to modifier inputs neither re-evaluate the object nor rebuild the depsgraph relations (the proxy is
    read through Object Info); assigning the node group again does both."""
    for name, value in values.items():
        input_socket(modifier, name).value = value
    modifier.node_group = modifier.node_group


def ensure_modifier(obj):
    """obj's Face Shading modifier, after the deforming modifiers and right before the outline (face spec 4)."""
    tree = ensure_group()
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is None or modifier.type != 'NODES':
        modifier = obj.modifiers.new(MODIFIER_NAME, 'NODES')
    if modifier.node_group != tree:
        modifier.node_group = tree
    outline = obj.modifiers.find(OUTLINE_MODIFIER)
    index = obj.modifiers.find(modifier.name)
    if 0 <= outline < index:
        obj.modifiers.move(index, outline)
    return modifier


def remove_modifier(obj):
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is not None:
        obj.modifiers.remove(modifier)
```

- [ ] **Step 5: Chạy test, phải xanh**

Run: đồng bộ script rồi chạy lại lệnh ở Step 3.
Expected: `Ran 12 tests ... OK`.

- [ ] **Step 6: Đăng ký test trong CMake**

Trong `tests/python/CMakeLists.txt`, thêm `dasktoon_face_shading_nodes_test` vào cuối danh sách `foreach(dasktoon_test ...)` (sau
`dasktoon_project_ui_test`).

- [ ] **Step 7: Commit**

```bash
git add scripts/startup/bl_ui/dasktoon_face_shading_nodes.py tests/python/dasktoon_face_shading_nodes_test.py tests/python/dasktoon_test_utils.py tests/python/CMakeLists.txt
git commit -m "feat: add the DaskToon_FaceShading Geometry Nodes group that leans face normals towards an ellipsoid proxy"
```

---

### Task 2: Tự căn khối trứng, `DT_Face`, tạo / căn lại / gỡ

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_face_shading.py` (phần lõi; Task 3 thêm operator và panel)
- Create: `tests/python/dasktoon_face_shading_test.py`
- Modify: `tests/python/CMakeLists.txt`

**Interfaces:**
- Consumes: Task 1 (`fsn.*`), `tu.add_test_head`.
- Produces (module `bl_ui.dasktoon_face_shading`, gọi tắt `fs`):
  - `fs.FaceShadingError(Exception)` — thông điệp tiếng Việt cho người dùng.
  - `fs.PROXY_PREFIX = "DT_FaceProxy::"`, `fs.PROXY_PROP = "dasktoon_face_proxy"` (trên mesh object),
    `fs.PROXY_MARK = "dasktoon_is_face_proxy"` (trên Empty).
  - `fs.find_armature(obj) -> Object | None`, `fs.find_head_bone(armature) -> str | None`
  - `fs.rest_pose(armatures)` — context manager, armature về Rest Position rồi trả lại (kể cả khi lỗi).
  - `fs.head_vertices(obj, bone, selected=None) -> np.ndarray[int]`
  - `fs.face_island(obj, head) -> np.ndarray[int]`
  - `fs.fit(points) -> (Vector centre, Vector radii)` (world)
  - `fs.proxy_of(obj) -> Object | None`, `fs.proxy_users(proxy) -> list[Object]`
  - `fs.setup(obj, selected=None) -> proxy`, `fs.refit(obj, selected=None) -> proxy`, `fs.remove(obj)`
  - `fs.panel_target(context) -> Object | None` (mesh đang chọn, hoặc mesh của khối trứng đang chọn)

- [ ] **Step 1: Viết test của phần lõi**

File: `tests/python/dasktoon_face_shading_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Face shading set-up: head bone, DT_Face, the proxy fitted to the face, refit and removal (face spec 3, 5)."""

import os
import sys
import tempfile
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_face_shading as fs  # noqa: E402
from bl_ui import dasktoon_face_shading_nodes as fsn  # noqa: E402


def weights(obj, name):
    out = np.zeros(len(obj.data.vertices))
    group = obj.vertex_groups.get(name)
    if group is None:
        return out
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == group.index:
                out[v.index] = g.weight
    return out


def rig_with_bones(names):
    rig = bpy.data.objects.new("Bones", bpy.data.armatures.new("Bones"))
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for i, name in enumerate(names):
        bone = rig.data.edit_bones.new(name)
        bone.head = (0.0, 0.0, i)
        bone.tail = (0.0, 0.0, i + 0.5)
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def expected_fit(head):
    """Face spec 5.4 on the skin of the test head, world space, at rest."""
    skin = head["dt_skin_vertices"]
    world = np.array([tuple(head.matrix_world @ v.co) for v in head.data.vertices[:skin]])
    low, high = world.min(axis=0), world.max(axis=0)
    rx, rz = (high[0] - low[0]) / 2.0, (high[2] - low[2]) / 2.0
    ry = max((high[1] - low[1]) / 2.0, 0.85 * rx)
    centre = Vector(((low[0] + high[0]) / 2.0, np.percentile(world[:, 1], 5.0) + ry, (low[2] + high[2]) / 2.0))
    return centre, Vector((rx, ry, rz))


def face_proxies():
    return [o for o in bpy.data.objects if o.get(fs.PROXY_MARK)]


class FaceShadingSetupTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()

    def assert_at_rest(self, proxy, head, rig):
        if rig is not None:
            rig.data.pose_position = 'REST'
        bpy.context.view_layer.update()
        centre, radii = expected_fit(head)
        location, _rotation, scale = proxy.matrix_world.decompose()
        self.assertLess((location - centre).length, 1e-4)
        self.assertLess((scale - radii).length, 1e-4)
        if rig is not None:
            rig.data.pose_position = 'POSE'
            bpy.context.view_layer.update()

    def test_head_bone_names(self):
        self.assertEqual(fs.find_head_bone(rig_with_bones(["Hips", "Spine", "J_Bip_C_Head"])), "J_Bip_C_Head")
        self.assertEqual(fs.find_head_bone(rig_with_bones(["mixamorig:HeadTop_End", "mixamorig:Head"])),
                         "mixamorig:Head")
        self.assertEqual(fs.find_head_bone(rig_with_bones(["首", "頭"])), "頭")
        self.assertEqual(fs.find_head_bone(rig_with_bones(["HeadTop_End", "Head_tip", "MyHeadBone"])), "MyHeadBone")
        self.assertIsNone(fs.find_head_bone(rig_with_bones(["Spine", "Neck"])))

    def test_dt_face_holds_the_face_island_not_the_hair(self):
        head, _rig = tu.add_test_head()
        fs.setup(head)
        skin = head["dt_skin_vertices"]
        face = weights(head, fsn.MASK_NAME)
        self.assertTrue((face[:skin] == 1.0).all())
        self.assertTrue((face[skin:] == 0.0).all())

    def test_proxy_fits_the_skin_and_hangs_from_the_head_bone(self):
        head, rig = tu.add_test_head()
        proxy = fs.setup(head)
        self.assertEqual((proxy.parent, proxy.parent_type, proxy.parent_bone), (rig, 'BONE', "Head"))
        self.assertEqual(proxy.name, "DT_FaceProxy::Rig:Head")
        self.assertEqual((proxy.empty_display_type, proxy.empty_display_size, proxy.hide_render), ('SPHERE', 1.0, True))
        self.assertEqual(proxy.users_collection[0], head.users_collection[0])
        self.assertEqual(fs.proxy_of(head), proxy)
        self.assertEqual(head[fs.PROXY_PROP], proxy)
        self.assertEqual(fsn.input_socket(fsn.get_modifier(head), "Proxy").value, proxy)
        self.assert_at_rest(proxy, head, rig)
        rest = proxy.matrix_world.copy()
        bone = rig.pose.bones["Head"]
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = (0.0, 0.0, 0.6)
        bpy.context.view_layer.update()
        self.assertGreater((proxy.matrix_world.translation - rest.translation).length, 1e-3)

    def test_setup_while_posed_fits_the_rest_pose(self):
        head, rig = tu.add_test_head()
        bone = rig.pose.bones["Head"]
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = (0.4, 0.0, 0.7)
        bpy.context.view_layer.update()
        proxy = fs.setup(head)
        self.assertEqual(rig.data.pose_position, 'POSE')
        self.assert_at_rest(proxy, head, rig)

    def test_fit_with_a_transformed_rig(self):
        head, rig = tu.add_test_head()
        rig.location = (1.0, 2.0, 0.5)
        rig.rotation_euler = (0.0, 0.0, 0.3)
        rig.scale = (1.2, 1.2, 1.2)
        bpy.context.view_layer.update()
        proxy = fs.setup(head)
        self.assert_at_rest(proxy, head, rig)

    def test_second_mesh_reuses_the_proxy_without_refitting(self):
        head, _rig = tu.add_test_head()
        brows = head.copy()
        brows.data = head.data.copy()
        brows.name = "Brows"
        bpy.context.scene.collection.objects.link(brows)
        proxy = fs.setup(head)
        proxy.location.x += 0.01
        moved = proxy.location.copy()
        self.assertEqual(fs.setup(brows), proxy)
        self.assertEqual(proxy.location, moved)
        self.assertEqual(len(face_proxies()), 1)
        self.assertEqual(set(o.name for o in fs.proxy_users(proxy)), {"Head", "Brows"})

    def test_selected_vertices_without_an_armature(self):
        head, _rig = tu.add_test_head(with_armature=False)
        skin = head["dt_skin_vertices"]
        proxy = fs.setup(head, selected=range(skin))
        self.assertEqual((proxy.parent, proxy.parent_type), (head, 'OBJECT'))
        self.assertEqual(proxy.name, "DT_FaceProxy::Head")
        self.assert_at_rest(proxy, head, None)

    def test_head_vertices_fallbacks(self):
        head, _rig = tu.add_test_head()
        self.assertEqual(len(fs.head_vertices(head, "Head")), len(head.data.vertices))
        self.assertEqual(list(fs.head_vertices(head, "Missing", selected=[3, 1, 2])), [1, 2, 3])
        with self.assertRaises(fs.FaceShadingError):
            fs.head_vertices(head, None)

    def test_nothing_to_work_with_raises(self):
        head, _rig = tu.add_test_head(with_armature=False)
        with self.assertRaises(fs.FaceShadingError):
            fs.setup(head)
        self.assertIsNone(fsn.get_modifier(head))
        self.assertEqual(face_proxies(), [])

    def test_refit_moves_the_proxy_back_and_keeps_the_sliders(self):
        head, rig = tu.add_test_head()
        proxy = fs.setup(head)
        modifier = fsn.get_modifier(head)
        fsn.set_inputs(modifier, {"Coverage": 0.5})
        proxy.location.z += 0.05
        proxy.scale = (0.3, 0.3, 0.3)
        self.assertEqual(fs.refit(head), proxy)
        self.assertAlmostEqual(fsn.input_socket(modifier, "Coverage").value, 0.5, places=6)
        self.assert_at_rest(proxy, head, rig)

    def test_refit_rebuilds_a_deleted_proxy(self):
        head, rig = tu.add_test_head()
        bpy.data.objects.remove(fs.setup(head))
        proxy = fs.refit(head)
        self.assertEqual(fs.proxy_of(head), proxy)
        self.assert_at_rest(proxy, head, rig)

    def test_remove_cleans_up_and_keeps_a_shared_proxy(self):
        head, _rig = tu.add_test_head()
        brows = head.copy()
        brows.data = head.data.copy()
        bpy.context.scene.collection.objects.link(brows)
        proxy = fs.setup(head)
        fs.setup(brows)
        name = proxy.name
        fs.remove(head)
        self.assertIsNone(head.modifiers.get(fsn.MODIFIER_NAME))
        self.assertIsNone(head.vertex_groups.get(fsn.MASK_NAME))
        self.assertNotIn(fs.PROXY_PROP, head)
        self.assertIn(name, bpy.data.objects)
        fs.remove(brows)
        self.assertNotIn(name, bpy.data.objects)

    def test_linked_mesh_is_refused(self):
        head, _rig = tu.add_test_head()
        path = os.path.join(tempfile.mkdtemp(prefix="dt_face_lib_"), "lib.blend")
        bpy.data.libraries.write(path, {head})
        tu.reset_scene()
        with bpy.data.libraries.load(path, link=True) as (_src, dst):
            dst.objects = ["Head"]
        linked = dst.objects[0]
        bpy.context.scene.collection.objects.link(linked)
        with self.assertRaises(fs.FaceShadingError):
            fs.setup(linked)

    def test_panel_target_follows_the_proxy(self):
        head, _rig = tu.add_test_head()
        proxy = fs.setup(head)
        self.assertEqual(fs.panel_target(bpy.context), head)
        bpy.context.view_layer.objects.active = proxy
        self.assertEqual(fs.panel_target(bpy.context), head)
        bpy.context.view_layer.objects.active = None
        self.assertIsNone(fs.panel_target(bpy.context))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, phải đỏ**

Run: đồng bộ script rồi `"$DT" ... --python tests/python/dasktoon_face_shading_test.py 2>&1 | tail -30`
Expected: FAIL — `ImportError: cannot import name 'dasktoon_face_shading'`.

- [ ] **Step 3: Viết phần lõi**

File: `scripts/startup/bl_ui/dasktoon_face_shading.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon face shading: the face mask, the ellipsoid proxy fitted to the head and the panel
(docs/superpowers/specs/2026-10-04-dasktoon-face-shading-design.md, sections 3 and 5)."""

from contextlib import contextmanager

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import dasktoon_face_shading_nodes as fsn

PROXY_PREFIX = "DT_FaceProxy::"
PROXY_PROP = "dasktoon_face_proxy"     # on the mesh object: the proxy it uses
PROXY_MARK = "dasktoon_is_face_proxy"  # on the proxy Empty
HEAD_NAMES = ("head", "j_bip_c_head", "mixamorig:head", "頭")
NOT_HEAD = ("end", "top", "tip", "nub")
HEAD_WEIGHT = 0.5
STRIP = 0.25
FRONT_PERCENTILE = 5.0
MIN_DEPTH = 0.85


class FaceShadingError(Exception):
    """Why face shading cannot be set up, worded for the user."""


def find_armature(obj):
    """The armature deforming obj: its first Armature modifier, else an armature parent (face spec 5.1)."""
    for modifier in obj.modifiers:
        if modifier.type == 'ARMATURE' and modifier.object is not None:
            return modifier.object
    if obj.parent is not None and obj.parent.type == 'ARMATURE':
        return obj.parent
    return None


def find_head_bone(armature):
    """Exact names first (any case), then a name with "head" that is not an end, top, tip or nub bone."""
    names = [bone.name for bone in armature.data.bones]
    for name in names:
        if name.lower() in HEAD_NAMES:
            return name
    for name in names:
        low = name.lower()
        if "head" in low and not any(word in low for word in NOT_HEAD):
            return name
    return None


@contextmanager
def rest_pose(armatures):
    """The armatures in Rest Position meanwhile; their pose position comes back even on error."""
    saved = [(a.data, a.data.pose_position) for a in dict.fromkeys(armatures)
             if a is not None and a.data.library is None]
    try:
        for data, _position in saved:
            data.pose_position = 'REST'
        bpy.context.view_layer.update()
        yield
    finally:
        for data, position in saved:
            data.pose_position = position
        bpy.context.view_layer.update()


def _check_editable(obj):
    if obj is None or obj.type != 'MESH':
        raise FaceShadingError("Hãy chọn mesh nhân vật")
    if obj.library is not None or obj.data.library is not None:
        raise FaceShadingError("Mesh %s được link từ thư viện, không sửa được" % obj.name)


def _group_weights(obj, name):
    weights = np.zeros(len(obj.data.vertices))
    group = obj.vertex_groups.get(name)
    if group is None:
        return weights
    for vertex in obj.data.vertices:
        for element in vertex.groups:
            if element.group == group.index:
                weights[vertex.index] = element.weight
    return weights


def head_vertices(obj, bone, selected=None):
    """Vertices weighted >= 0.5 to the head bone, else the vertices selected in Edit Mode (face spec 5.2)."""
    if bone is not None:
        found = np.flatnonzero(_group_weights(obj, bone) >= HEAD_WEIGHT)
        if len(found):
            return found
    if selected is not None and len(selected):
        return np.array(sorted(selected), dtype=np.int64)
    raise FaceShadingError("Không tìm thấy vùng đầu (không có xương đầu có trọng số). "
                           "Hãy vào Edit Mode, chọn vùng mặt rồi bấm lại")


def _world_coords(obj):
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    matrix = np.array(obj.matrix_world)
    return co.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]


def _island(mesh, seed):
    """Vertices edge-connected to `seed`."""
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", edges)
    a, b = edges[0::2], edges[1::2]
    inside = np.zeros(len(mesh.vertices), dtype=bool)
    inside[seed] = True
    while True:
        grow = inside[a] != inside[b]
        if not grow.any():
            return np.flatnonzero(inside)
        inside[a[grow]] = True
        inside[b[grow]] = True


def face_island(obj, head):
    """The face skin (face spec 5.3): the island of the most forward head vertex near the middle of the head."""
    world = _world_coords(obj)
    x = world[head, 0]
    low, high = x.min(), x.max()
    middle = head[np.abs(x - (low + high) / 2.0) <= STRIP * (high - low)]
    return _island(obj.data, middle[np.argmin(world[middle, 1])])


def fit(points):
    """Centre and radii of the proxy for the head points of the face skin, world space (face spec 5.4)."""
    low, high = points.min(axis=0), points.max(axis=0)
    rx, rz = (high[0] - low[0]) / 2.0, (high[2] - low[2]) / 2.0
    if min(rx, rz) < 1e-5:
        raise FaceShadingError("Vùng mặt quá nhỏ để đặt khối trứng")
    ry = max((high[1] - low[1]) / 2.0, MIN_DEPTH * rx)
    front = float(np.percentile(points[:, 1], FRONT_PERCENTILE))
    return Vector(((low[0] + high[0]) / 2.0, front + ry, (low[2] + high[2]) / 2.0)), Vector((rx, ry, rz))


def _face_points(obj, head, face):
    points = _world_coords(obj)[np.intersect1d(head, face)]
    if not len(points):
        raise FaceShadingError("Vùng %s không nằm trong vùng đầu; hãy tô lại vertex group đó" % fsn.MASK_NAME)
    return points


def _write_mask(obj, indices):
    """DT_Face = the face island with weight 1; the active vertex group stays the same."""
    active = obj.vertex_groups.active.name if obj.vertex_groups.active is not None else None
    old = obj.vertex_groups.get(fsn.MASK_NAME)
    if old is not None:
        obj.vertex_groups.remove(old)
    obj.vertex_groups.new(name=fsn.MASK_NAME).add(indices.tolist(), 1.0, 'REPLACE')
    if active is not None and active in obj.vertex_groups:
        obj.vertex_groups.active_index = obj.vertex_groups[active].index


def proxy_of(obj):
    """The proxy obj uses: the modifier's Proxy input, else the object's dasktoon_face_proxy property."""
    modifier = fsn.get_modifier(obj)
    if modifier is not None:
        proxy = fsn.input_socket(modifier, "Proxy").value
        if proxy is not None:
            return proxy
    proxy = obj.get(PROXY_PROP)
    return proxy if isinstance(proxy, bpy.types.Object) else None


def proxy_users(proxy):
    return [o for o in bpy.data.objects if o.type == 'MESH' and proxy_of(o) == proxy]


def find_proxy(armature, bone, obj):
    """The proxy already made for this head bone, or for obj when there is no head bone (one per head bone)."""
    for other in bpy.data.objects:
        if other.type != 'EMPTY' or not other.get(PROXY_MARK) or other.library is not None:
            continue
        if bone is not None and (other.parent, other.parent_type, other.parent_bone) == (armature, 'BONE', bone):
            return other
        if bone is None and (other.parent, other.parent_type) == (obj, 'OBJECT'):
            return other
    return None


def _new_proxy(obj, armature, bone):
    name = PROXY_PREFIX + ("%s:%s" % (armature.name, bone) if bone is not None else obj.name)
    proxy = bpy.data.objects.new(name, None)
    proxy.empty_display_type = 'SPHERE'
    proxy.empty_display_size = 1.0
    proxy.hide_render = True
    proxy[PROXY_MARK] = True
    collection = obj.users_collection[0] if obj.users_collection else bpy.context.scene.collection
    collection.objects.link(proxy)
    return proxy


def place_proxy(proxy, armature, bone, obj, centre, radii):
    """Hang the proxy from the head bone (or from obj) so that at rest it sits at `centre` with scale `radii`."""
    if bone is not None:
        rest = armature.data.bones[bone]
        parent = armature.matrix_world @ rest.matrix_local @ Matrix.Translation((0.0, rest.length, 0.0))
        proxy.parent = armature
        proxy.parent_type = 'BONE'
        proxy.parent_bone = bone
    else:
        parent = obj.matrix_world.copy()
        proxy.parent = obj
        proxy.parent_type = 'OBJECT'
    proxy.matrix_parent_inverse = parent.inverted()
    proxy.matrix_basis = Matrix.LocRotScale(centre, None, radii)


def _rig(obj):
    armature = find_armature(obj)
    return armature, (find_head_bone(armature) if armature is not None else None)


def _connect(obj, proxy):
    modifier = fsn.ensure_modifier(obj)
    fsn.set_inputs(modifier, {"Proxy": proxy})
    obj[PROXY_PROP] = proxy


def setup(obj, selected=None):
    """Face spec 3.1: DT_Face, the proxy (the head bone's existing one is reused as it is) and the modifier."""
    _check_editable(obj)
    armature, bone = _rig(obj)
    with rest_pose([armature]):
        head = head_vertices(obj, bone, selected)
        face = face_island(obj, head)
        proxy = find_proxy(armature, bone, obj)
        if proxy is None:
            centre, radii = fit(_face_points(obj, head, face))
            proxy = _new_proxy(obj, armature, bone)
            place_proxy(proxy, armature, bone, obj, centre, radii)
        _write_mask(obj, face)
    _connect(obj, proxy)
    return proxy


def refit(obj, selected=None):
    """Face spec 3.4: place and size the proxy again from the face (DT_Face as painted); the sliders stay."""
    _check_editable(obj)
    if fsn.get_modifier(obj) is None:
        raise FaceShadingError("%s chưa có bóng mặt; bấm Tạo bóng mặt anime trước" % obj.name)
    armature, bone = _rig(obj)
    with rest_pose([armature]):
        face = np.flatnonzero(_group_weights(obj, fsn.MASK_NAME) >= HEAD_WEIGHT)
        try:
            head = head_vertices(obj, bone, selected)
        except FaceShadingError:
            if not len(face):
                raise
            head = face
        if not len(face):
            face = face_island(obj, head)
            _write_mask(obj, face)
        centre, radii = fit(_face_points(obj, head, face))
        proxy = proxy_of(obj) or find_proxy(armature, bone, obj) or _new_proxy(obj, armature, bone)
        place_proxy(proxy, armature, bone, obj, centre, radii)
    _connect(obj, proxy)
    return proxy


def remove(obj):
    """Face spec 3.5: the modifier, DT_Face, the property, and the proxy when no other mesh uses it."""
    _check_editable(obj)
    proxy = proxy_of(obj)
    fsn.remove_modifier(obj)
    group = obj.vertex_groups.get(fsn.MASK_NAME)
    if group is not None:
        obj.vertex_groups.remove(group)
    if PROXY_PROP in obj:
        del obj[PROXY_PROP]
    if proxy is not None and proxy.library is None and not proxy_users(proxy):
        bpy.data.objects.remove(proxy)


def panel_target(context):
    """The mesh the panel works on: the active mesh, or the first mesh using the active proxy."""
    obj = context.active_object
    if obj is None:
        return None
    if obj.type == 'MESH':
        return obj
    if obj.type == 'EMPTY' and obj.get(PROXY_MARK):
        users = proxy_users(obj)
        return users[0] if users else None
    return None


classes = ()
```

- [ ] **Step 4: Chạy test, phải xanh**

Run: đồng bộ script rồi chạy lại lệnh ở Step 2.
Expected: `Ran 15 tests ... OK`.

- [ ] **Step 5: Đăng ký test và commit**

Thêm `dasktoon_face_shading_test` vào danh sách `foreach(dasktoon_test ...)` trong `tests/python/CMakeLists.txt`.

```bash
git add scripts/startup/bl_ui/dasktoon_face_shading.py tests/python/dasktoon_face_shading_test.py tests/python/CMakeLists.txt
git commit -m "feat: fit the face shading proxy to the head, write DT_Face, and set up, refit or remove face shading"
```

---

### Task 3: Operator, panel *DaskToon › Bóng mặt*, đăng ký và thay panel cũ

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_face_shading.py` (thêm operator, panel, `classes`)
- Modify: `scripts/startup/bl_ui/dasktoon_face_normals.py` (bỏ panel cũ `DASKTOON_PT_face_normals`)
- Modify: `scripts/startup/bl_ui/__init__.py` (thêm `"dasktoon_face_shading"` vào `_modules`, ngay sau `"dasktoon_face_normals"`)
- Modify: `tests/python/dasktoon_face_shading_test.py` (thêm lớp test giao diện)

**Interfaces:**
- Consumes: Task 2 (`fs.setup`, `fs.refit`, `fs.remove`, `fs.proxy_of`, `fs.panel_target`, `fs.FaceShadingError`), Task 1 (`fsn.input_socket`).
- Produces: operator `dasktoon.face_shading_setup`, `dasktoon.face_shading_refit`, `dasktoon.face_shading_remove`,
  `dasktoon.face_shading_select_proxy`; panel `DASKTOON_PT_face_shading` và panel con `DASKTOON_PT_face_shading_advanced`;
  `fs.SLIDERS`.

- [ ] **Step 1: Viết test giao diện**

Thêm vào `tests/python/dasktoon_face_shading_test.py`, trước khối `if __name__ == "__main__":`:

```python
class Recorder:
    """Stands in for UILayout: records the labels, operators and properties a panel draws."""

    def __init__(self, log=None):
        self.log = [] if log is None else log
        self.scale_y = 1.0

    def column(self, **_kw):
        return Recorder(self.log)

    def row(self, **_kw):
        return Recorder(self.log)

    def box(self):
        return Recorder(self.log)

    def separator(self, **_kw):
        pass

    def label(self, text="", **_kw):
        self.log.append(("label", text))

    def operator(self, idname, text=None, **_kw):
        self.log.append(("operator", idname))

    def prop(self, _data, _prop, text=None, **_kw):
        self.log.append(("prop", text))


def draw(panel):
    recorder = Recorder()

    class Fake:
        layout = recorder

    panel.draw(Fake(), bpy.context)
    return recorder.log


class FaceShadingUITest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()

    def test_classes_are_registered_and_the_old_panel_is_gone(self):
        for name in ("DASKTOON_OT_face_shading_setup", "DASKTOON_OT_face_shading_refit",
                     "DASKTOON_OT_face_shading_remove", "DASKTOON_OT_face_shading_select_proxy",
                     "DASKTOON_PT_face_shading", "DASKTOON_PT_face_shading_advanced",
                     "DASKTOON_OT_fix_face_normals", "DASKTOON_OT_reset_face_normals"):
            self.assertTrue(hasattr(bpy.types, name), name)
        self.assertFalse(hasattr(bpy.types, "DASKTOON_PT_face_normals"))
        panel = bpy.types.DASKTOON_PT_face_shading
        self.assertEqual((panel.bl_space_type, panel.bl_region_type, panel.bl_category), ('VIEW_3D', 'UI', "DaskToon"))
        self.assertEqual(bpy.types.DASKTOON_PT_face_shading_advanced.bl_parent_id, "DASKTOON_PT_face_shading")

    def test_setup_operator_on_the_active_mesh(self):
        head, _rig = tu.add_test_head()
        self.assertEqual(bpy.ops.dasktoon.face_shading_setup(), {'FINISHED'})
        self.assertIsNotNone(fsn.get_modifier(head))

    def test_setup_operator_uses_the_edit_mode_selection(self):
        head, _rig = tu.add_test_head(with_armature=False)
        skin = head["dt_skin_vertices"]
        for v in head.data.vertices:
            v.select = v.index < skin
        bpy.ops.object.mode_set(mode='EDIT')
        self.assertEqual(bpy.ops.dasktoon.face_shading_setup(), {'FINISHED'})
        self.assertEqual(head.mode, 'EDIT')
        bpy.ops.object.mode_set(mode='OBJECT')
        self.assertEqual(fs.proxy_of(head).parent, head)

    def test_setup_operator_reports_what_is_missing(self):
        tu.add_test_head(with_armature=False)
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.face_shading_setup()

    def test_select_proxy_then_refit_and_remove_from_the_proxy(self):
        head, _rig = tu.add_test_head()
        bpy.ops.dasktoon.face_shading_setup()
        proxy = fs.proxy_of(head)
        self.assertEqual(bpy.ops.dasktoon.face_shading_select_proxy(), {'FINISHED'})
        self.assertEqual(bpy.context.view_layer.objects.active, proxy)
        self.assertTrue(proxy.select_get())
        self.assertFalse(head.select_get())
        self.assertEqual(bpy.ops.dasktoon.face_shading_refit(), {'FINISHED'})
        self.assertEqual(bpy.ops.dasktoon.face_shading_remove(), {'FINISHED'})
        self.assertIsNone(fsn.get_modifier(head))

    def test_panel_offers_setup_then_the_sliders(self):
        log = draw(bpy.types.DASKTOON_PT_face_shading)
        self.assertEqual(log[0][0], "label")
        head, _rig = tu.add_test_head()
        self.assertIn(("operator", "dasktoon.face_shading_setup"), draw(bpy.types.DASKTOON_PT_face_shading))
        fs.setup(head)
        log = draw(bpy.types.DASKTOON_PT_face_shading)
        self.assertEqual([text for kind, text in log if kind == "prop"],
                         ["Độ phủ", "Vùng chuyển", "Giữ bóng mũi", "Giữ bóng cằm"])
        for idname in ("dasktoon.face_shading_select_proxy", "dasktoon.face_shading_refit",
                       "dasktoon.face_shading_remove"):
            self.assertIn(("operator", idname), log)
        self.assertNotIn(("operator", "dasktoon.reset_face_normals"), log)
        bpy.context.view_layer.objects.active = fs.proxy_of(head)
        self.assertIn(("label", "Khối trứng của Head"), draw(bpy.types.DASKTOON_PT_face_shading))

    def test_panel_suggests_clearing_old_custom_normals(self):
        head, _rig = tu.add_test_head()
        head.data.normals_split_custom_set_from_vertices([v.normal for v in head.data.vertices])
        self.assertIn(("operator", "dasktoon.reset_face_normals"), draw(bpy.types.DASKTOON_PT_face_shading))

    def test_advanced_panel_holds_the_old_tools(self):
        log = draw(bpy.types.DASKTOON_PT_face_shading_advanced)
        for idname in ("dasktoon.fix_face_normals", "dasktoon.reset_face_normals",
                       "dasktoon.toggle_face_normals_display"):
            self.assertIn(("operator", idname), log)
```

- [ ] **Step 2: Chạy test, phải đỏ**

Run: đồng bộ script rồi chạy `tests/python/dasktoon_face_shading_test.py`.
Expected: FAIL — các test của `FaceShadingUITest` lỗi (`AttributeError: DASKTOON_PT_face_shading`, operator không tồn tại);
15 test của Task 2 vẫn qua.

- [ ] **Step 3: Thêm operator và panel**

Trong `scripts/startup/bl_ui/dasktoon_face_shading.py`: thêm `from bpy.types import Operator, Panel` vào phần import, rồi
thay dòng `classes = ()` ở cuối file bằng:

```python
SLIDERS = (("Coverage", "Độ phủ"), ("Falloff", "Vùng chuyển"), ("Nose Keep", "Giữ bóng mũi"),
           ("Chin Keep", "Giữ bóng cằm"))


def _run(operator, context, action, done):
    """Run action(mesh, selected) on the panel's mesh. In Edit Mode the selection is read and Edit Mode is left
    meanwhile (vertex groups cannot be written in Edit Mode)."""
    obj = panel_target(context)
    if obj is None:
        operator.report({'ERROR'}, "Hãy chọn mesh nhân vật")
        return {'CANCELLED'}
    editing = obj.mode == 'EDIT'
    selected = None
    if editing:
        obj.update_from_editmode()
        flags = np.zeros(len(obj.data.vertices), dtype=bool)
        obj.data.vertices.foreach_get("select", flags)
        selected = np.flatnonzero(flags)
        bpy.ops.object.mode_set(mode='OBJECT')
    try:
        action(obj, selected)
    except FaceShadingError as ex:
        operator.report({'ERROR'}, str(ex))
        return {'CANCELLED'}
    finally:
        if editing:
            bpy.ops.object.mode_set(mode='EDIT')
    operator.report({'INFO'}, done % obj.name)
    return {'FINISHED'}


class DASKTOON_OT_face_shading_setup(Operator):
    """Shade the face like an egg: find the head, fit an egg-shaped proxy to it and add the Face Shading modifier"""
    bl_idname = "dasktoon.face_shading_setup"
    bl_label = "Tạo bóng mặt anime"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return _run(self, context, setup, "Đã tạo bóng mặt cho %s: kéo khối trứng hoặc chỉnh thanh trượt")


class DASKTOON_OT_face_shading_refit(Operator):
    """Fit the egg-shaped proxy to the face again (position and size); the sliders stay"""
    bl_idname = "dasktoon.face_shading_refit"
    bl_label = "Căn lại khối trứng"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return _run(self, context, refit, "Đã căn lại khối trứng của %s")


class DASKTOON_OT_face_shading_remove(Operator):
    """Remove the face shading of the mesh: the modifier, DT_Face and the proxy when no other mesh uses it"""
    bl_idname = "dasktoon.face_shading_remove"
    bl_label = "Gỡ bóng mặt"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return _run(self, context, lambda obj, _selected: remove(obj), "Đã gỡ bóng mặt của %s")


class DASKTOON_OT_face_shading_select_proxy(Operator):
    """Select the egg-shaped proxy to move, rotate or scale it; the face shading follows right away"""
    bl_idname = "dasktoon.face_shading_select_proxy"
    bl_label = "Chọn khối trứng"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = panel_target(context)
        proxy = proxy_of(obj) if obj is not None else None
        if proxy is None:
            self.report({'ERROR'}, "Mesh chưa có khối trứng: bấm Tạo bóng mặt anime hoặc Căn lại khối trứng")
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        try:
            proxy.hide_set(False)
            proxy.hide_viewport = False
            for other in context.selected_objects:
                other.select_set(False)
            proxy.select_set(True)
        except RuntimeError:
            self.report({'ERROR'}, "Khối trứng %s không nằm trong view layer đang mở" % proxy.name)
            return {'CANCELLED'}
        context.view_layer.objects.active = proxy
        return {'FINISHED'}


class DASKTOON_PT_face_shading(Panel):
    bl_label = "Bóng mặt"
    bl_idname = "DASKTOON_PT_face_shading"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"
    bl_order = 15

    def draw(self, context):
        layout = self.layout
        obj = panel_target(context)
        if obj is None:
            layout.label(text="Chọn mesh nhân vật hoặc khối trứng", icon='INFO')
            return
        if obj.library is not None or obj.data.library is not None:
            layout.label(text="Mesh link từ thư viện, không sửa được", icon='ERROR')
            return
        modifier = fsn.get_modifier(obj)
        if modifier is None:
            col = layout.column()
            col.scale_y = 1.4
            col.operator(DASKTOON_OT_face_shading_setup.bl_idname, icon='SHADING_RENDERED')
        else:
            if context.active_object != obj:
                layout.label(text="Khối trứng của " + obj.name, icon='MESH_UVSPHERE')
            if proxy_of(obj) is None:
                layout.label(text="Chưa có khối trứng: bấm Căn lại khối trứng", icon='ERROR')
            layout.operator(DASKTOON_OT_face_shading_select_proxy.bl_idname, icon='RESTRICT_SELECT_OFF')
            col = layout.column(align=True)
            for name, label in SLIDERS:
                col.prop(fsn.input_socket(modifier, name), "value", text=label, slider=True)
            row = layout.row(align=True)
            row.operator(DASKTOON_OT_face_shading_refit.bl_idname, icon='FILE_REFRESH')
            row.operator(DASKTOON_OT_face_shading_remove.bl_idname, icon='X')
        if obj.data.has_custom_normals and context.active_object == obj:
            box = layout.box()
            box.label(text="Mesh còn custom normal cũ: bóng mũi, cằm", icon='INFO')
            box.label(text="sẽ theo normal đó, không theo hình khối thật")
            box.operator("dasktoon.reset_face_normals", text="Xóa normal tùy chỉnh cũ", icon='LOOP_BACK')


class DASKTOON_PT_face_shading_advanced(Panel):
    bl_label = "Nâng cao"
    bl_idname = "DASKTOON_PT_face_shading_advanced"
    bl_parent_id = "DASKTOON_PT_face_shading"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, _context):
        layout = self.layout
        layout.label(text="Công cụ cũ: ghi thẳng normal vào mesh", icon='INFO')
        layout.operator("dasktoon.fix_face_normals", icon='SPHERE')
        row = layout.row(align=True)
        row.operator("dasktoon.reset_face_normals", text="Reset Normals", icon='LOOP_BACK')
        row.operator("dasktoon.toggle_face_normals_display", text="Normal Lines", icon='HIDE_OFF')


classes = (
    DASKTOON_OT_face_shading_setup,
    DASKTOON_OT_face_shading_refit,
    DASKTOON_OT_face_shading_remove,
    DASKTOON_OT_face_shading_select_proxy,
    DASKTOON_PT_face_shading,
    DASKTOON_PT_face_shading_advanced,
)
```

- [ ] **Step 4: Bỏ panel cũ và đăng ký module mới**

Trong `scripts/startup/bl_ui/dasktoon_face_normals.py`: xóa class `DASKTOON_PT_face_normals` (cả khối comment "Sidebar
N-Panel" phía trên nó), bỏ nó khỏi tuple `classes`, và bỏ `Panel` khỏi dòng `from bpy.types import ...`. Thêm vào đầu file
docstring: `"""Legacy face normal tools; their buttons live under DaskToon › Bóng mặt › Nâng cao (dasktoon_face_shading)."""`.

Trong `scripts/startup/bl_ui/__init__.py`: thêm `"dasktoon_face_shading",` ngay sau dòng `"dasktoon_face_normals",`.

- [ ] **Step 5: Chạy test, phải xanh**

Run: đồng bộ script rồi chạy `tests/python/dasktoon_face_shading_test.py`.
Expected: `Ran 23 tests ... OK`.

- [ ] **Step 6: Commit**

```bash
git add scripts/startup/bl_ui/dasktoon_face_shading.py scripts/startup/bl_ui/dasktoon_face_normals.py scripts/startup/bl_ui/__init__.py tests/python/dasktoon_face_shading_test.py
git commit -m "feat: add the DaskToon › Bóng mặt panel and operators; the old face normal tools move under Nâng cao"
```

---

### Task 4: Tương thích với outline (lõi outline phiên bản 2)

Vì sao: node **Normal** ở domain Point trả về custom normal, nên khi Face Shading đứng trước outline thì vỏ outline ở vùng mặt bị
đẩy theo normal hình trứng, trong khi Unity đẩy theo `DT_OutlineN` (normal hình học). Ngoài ra Flip Faces không đảo custom normal,
nên vỏ ở vùng mặt sẽ được tô bằng normal hướng ra ngoài, còn pass outline của Unity tô bằng `-normal`. Lõi phiên bản 2:
hướng đẩy dùng **True Normal**; vỏ được gán custom normal = `-(normal góc của nguồn)` (bắt trước khi dựng vỏ). Với mesh không có
custom normal, kết quả trùng phiên bản 1.

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_outline_nodes.py` (`CORE_VERSION = 2`, True Normal, normal của vỏ)
- Modify: `tests/python/dasktoon_outline_nodes_test.py` (2 test)
- Modify: `tests/python/dasktoon_face_shading_test.py` (lớp `OutlineCompatibilityTest`)

**Interfaces:**
- Consumes: Task 2 (`fs.setup`), `bl_ui.dasktoon_outline` (`sync_all`, `sync_material`, `reset_cache`).
- Produces: `gn.CORE_VERSION == 2`; hành vi: vỏ không phụ thuộc custom normal của nguồn về vị trí; normal góc của vỏ = `-N` nguồn.

- [ ] **Step 1: Viết test**

Thêm vào lớp `OutlineNodesTest` trong `tests/python/dasktoon_outline_nodes_test.py`:

```python
    def test_hull_direction_ignores_custom_normals(self):
        obj = tu.add_sphere(segments=16, rings=8)
        obj.data.materials.append(tu.emission_material("Skin", (1, 1, 1, 1)))
        count = len(obj.data.vertices)
        self._apply(obj, width=0.05)
        plain = hull_verts(obj, count, expected=count)
        obj.data.normals_split_custom_set_from_vertices([(0.0, 0.0, 1.0)] * count)
        obj.data.update()
        bpy.context.view_layer.update()
        for a, b in zip(plain, hull_verts(obj, count, expected=count)):
            self.assertLess((a - b).length, 1e-5)

    def test_hull_is_shaded_with_the_negated_source_normal(self):
        obj = tu.add_sphere(segments=16, rings=8)
        obj.data.materials.append(tu.emission_material("Skin", (1, 1, 1, 1)))
        faces = len(obj.data.polygons)
        self._apply(obj, width=0.05)
        mesh = evaluated_mesh(obj)
        for poly in mesh.polygons[faces:]:
            for i in poly.loop_indices:
                self.assertLess(mesh.corner_normals[i].vector.dot(mesh.vertices[mesh.loops[i].vertex_index].co), 0.0)
        obj.data.normals_split_custom_set_from_vertices([(0.0, 0.0, 1.0)] * len(obj.data.vertices))
        obj.data.update()
        bpy.context.view_layer.update()
        mesh = evaluated_mesh(obj)
        for poly in mesh.polygons[faces:]:
            for i in poly.loop_indices:
                self.assertAlmostEqual(mesh.corner_normals[i].vector.z, -1.0, delta=1e-4)
```

Thêm vào `tests/python/dasktoon_face_shading_test.py` (trước `if __name__ == "__main__":`), và thêm
`from bl_ui import dasktoon_outline as outline` vào phần import:

```python
class OutlineCompatibilityTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()
        self.head, self.rig = tu.add_test_head()
        self.mat, self.node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        self.node.use_outline = True
        tu.assign(self.head, self.mat)
        outline.sync_all(bpy.context.scene)

    def hull(self):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = self.head.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        count = len(self.head.data.vertices)
        points = [tuple(v.co) for v in mesh.vertices[count:]]
        evaluated.to_mesh_clear()
        return np.array(points)

    def test_face_shading_stays_right_before_the_outline(self):
        fs.setup(self.head)
        names = ["Armature", fsn.MODIFIER_NAME, "DaskToon Outline"]
        self.assertEqual([m.name for m in self.head.modifiers], names)
        self.node.inputs["Outline Width"].default_value = 0.02
        outline.sync_all(bpy.context.scene)
        self.assertEqual([m.name for m in self.head.modifiers], names)

    def test_outline_hull_does_not_follow_the_face_normals(self):
        fs.setup(self.head)
        modifier = fsn.get_modifier(self.head)
        with_face = self.hull()
        modifier.show_viewport = False
        without_face = self.hull()
        self.assertEqual(with_face.shape, without_face.shape)
        self.assertLess(np.abs(with_face - without_face).max(), 1e-5)
```

- [ ] **Step 2: Chạy test, phải đỏ**

Run: đồng bộ script rồi chạy `tests/python/dasktoon_outline_nodes_test.py` và `tests/python/dasktoon_face_shading_test.py`.
Expected: FAIL — `test_hull_direction_ignores_custom_normals`, `test_hull_is_shaded_with_the_negated_source_normal` (phần có
custom normal: z = +1) và `test_outline_hull_does_not_follow_the_face_normals` đỏ; `test_face_shading_stays_right_before_the_outline` xanh
(Task 1 đã đặt đúng chỗ, test này giữ hành vi).

- [ ] **Step 3: Sửa lõi outline**

Trong `scripts/startup/bl_ui/dasktoon_outline_nodes.py`:

1. `CORE_VERSION = 1` → `CORE_VERSION = 2`.
2. Thay đoạn Separate đầu hàm `ensure_core_group` bằng (bắt normal góc của nguồn trước khi dựng vỏ):

```python
    # The hull is shaded with the negated corner normal of the source, like the Unity outline pass (N = -normal). It is
    # captured before the hull is built: Flip Faces keeps custom normals (e.g. DaskToon face shading) as they are.
    capture = nodes.new('GeometryNodeCaptureAttribute')
    capture.domain = 'CORNER'
    capture.capture_items.new('VECTOR', "Normal")
    links.new(inp["Geometry"], capture.inputs["Geometry"])
    links.new(nodes.new('GeometryNodeInputNormal').outputs["Normal"], capture.inputs["Normal"])

    # Faces whose material has outline enabled are the hull source.
    separate = nodes.new('GeometryNodeSeparateGeometry')
    separate.domain = 'FACE'
    links.new(capture.outputs["Geometry"], separate.inputs["Geometry"])
    links.new(inp["Enabled"], separate.inputs["Selection"])
```

3. Trong đoạn "Smoothed normal", thay `nodes.new('GeometryNodeInputNormal').outputs[0]` bằng
   `nodes.new('GeometryNodeInputNormal').outputs["True Normal"]` và sửa comment thành:
   `# Smoothed geometric normal (True Normal: custom normals such as face shading are ignored, like DT_OutlineN in game
   engines): merge coincident vertices, then sample their normal back (no cracks on split seams).`
4. Thay hai dòng cuối dựng vỏ (`flip` và link ra `Hull`) bằng:

```python
    flip = nodes.new('GeometryNodeFlipFaces')
    links.new(set_position.outputs[0], flip.inputs["Mesh"])
    hull_normal = nodes.new('GeometryNodeSetMeshNormal')
    hull_normal.mode = 'FREE'
    hull_normal.domain = 'CORNER'
    links.new(flip.outputs[0], hull_normal.inputs["Mesh"])
    links.new(_vector_math(tree, 'SCALE', capture.outputs["Normal"], scale=-1.0), hull_normal.inputs["Custom Normal"])

    links.new(inp["Geometry"], group_out.inputs["Original"])
    links.new(hull_normal.outputs[0], group_out.inputs["Hull"])
    return tree
```

- [ ] **Step 4: Chạy test, phải xanh (kèm toàn bộ test outline cũ)**

Run: đồng bộ script rồi chạy `dasktoon_outline_nodes_test.py`, `dasktoon_outline_sync_test.py`, `dasktoon_outline_gamedata_test.py`,
`dasktoon_face_shading_test.py`.
Expected: tất cả OK (`dasktoon_face_shading_test.py`: `Ran 25 tests ... OK`).

- [ ] **Step 5: Commit**

```bash
git add scripts/startup/bl_ui/dasktoon_outline_nodes.py tests/python/dasktoon_outline_nodes_test.py tests/python/dasktoon_face_shading_test.py
git commit -m "fix: push the outline hull along geometric normals and shade it with the negated source normal (outline core v2)"
```

---

### Task 5: Engine Export ghi bóng mặt ở tư thế nghỉ

**Files:**
- Create: `scripts/modules/dasktoon_export/face_shading.py`
- Create: `tests/python/dasktoon_face_shading_export_test.py`
- Modify: `scripts/modules/dasktoon_export/__init__.py` (`export_model`)
- Modify: `scripts/modules/dasktoon_export/unity_yaml.py` (`model_meta(..., blend_shape_normals=True)`)
- Modify: `scripts/modules/dasktoon_export/model_fbx.py` (`modifier_notes` bỏ qua Face Shading)
- Modify: `scripts/modules/dasktoon_export/report.py` (`face_meshes`)
- Modify: `tests/python/dasktoon_export_yaml_test.py`, `tests/python/dasktoon_export_fbx_test.py`, `tests/python/CMakeLists.txt`

**Interfaces:**
- Consumes: Task 1 (`fsn.get_modifier`, `fsn.MODIFIER_NAME`), Task 2 (`fs.find_armature`, `fs.proxy_of`, `fs.rest_pose`, `fs.setup`).
- Produces:
  - `dasktoon_export.face_shading.face_shaded(objects) -> list[Object]` (mesh có modifier đang hiện, mỗi mesh data một lần)
  - `dasktoon_export.face_shading.bake_rest_normals(context, objects) -> (snapshots, names, warnings)`
  - `dasktoon_export.face_shading.restore_normals(snapshots)`
  - `unity_yaml.model_meta(guid, materials, import_animation, blend_shape_normals=True)`
  - `report.Report.face_meshes: list[str]`

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_face_shading_export_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export of face shading: rest-pose ellipsoid normals in the FBX, the mesh given back exactly (face spec 6)."""

import os
import sys
import tempfile
import unittest
from unittest import mock

import bpy
import numpy as np
from mathutils import kdtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_face_shading as fs  # noqa: E402
from bl_ui import dasktoon_face_shading_nodes as fsn  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import face_shading as export_face  # noqa: E402
from dasktoon_export import model_fbx, targets  # noqa: E402

OPTIONS = dasktoon_export.ExportOptions(include_animation=False, bake_size=16, bake_samples=1)


def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def corner_normals(mesh):
    values = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.corner_normals.foreach_get("vector", values)
    return values.reshape(-1, 3).astype(np.float64)


def raw(mesh, name):
    attr = mesh.attributes.get(name)
    if attr is None:
        return None
    key, width, dtype = {'INT16_2D': ("value", 2, np.int32), 'FLOAT_VECTOR': ("vector", 3, np.float32),
                         'BOOLEAN': ("value", 1, bool)}[attr.data_type]
    values = np.empty(len(attr.data) * width, dtype=dtype)
    attr.data.foreach_get(key, values)
    return attr.domain, attr.data_type, values


def face_head():
    tu.reset_scene()
    head, rig = tu.add_test_head()
    mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    tu.assign(head, mat)
    smile = head.shape_key_add(name="Basis")
    smile = head.shape_key_add(name="Smile")
    for point in smile.data[:200]:
        point.co.z += 0.01
    smile.value = 1.0
    fs.setup(head)
    bone = rig.pose.bones["Head"]
    bone.rotation_mode = 'XYZ'
    bone.rotation_euler = (0.3, 0.0, 0.5)
    bpy.context.view_layer.update()
    return head, rig


def rest_normals(head, rig):
    """What the modifier gives at rest with only the Basis shape (face spec 6.2), in object space."""
    only, index = head.show_only_shape_key, head.active_shape_key_index
    head.show_only_shape_key = True
    head.active_shape_key_index = 0
    with fs.rest_pose([rig]):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = head.evaluated_get(depsgraph)
        normals = corner_normals(evaluated.to_mesh())
        evaluated.to_mesh_clear()
    head.show_only_shape_key = only
    head.active_shape_key_index = index
    bpy.context.view_layer.update()
    return normals


def to_world(obj, normals):
    """Object-space normals to world space (inverse transpose of the 3x3, for row vectors)."""
    return normalize(normals @ np.linalg.inv(np.array(obj.matrix_world.to_3x3())))


def degrees(a, b):
    return np.degrees(np.arccos(np.clip((normalize(a) * normalize(b)).sum(axis=1), -1.0, 1.0)))


class FaceShadingExportTest(unittest.TestCase):
    def test_rest_normals_are_written_and_the_state_comes_back(self):
        head, rig = face_head()
        want = rest_normals(head, rig)
        before = [(m.name, m.show_viewport) for m in head.modifiers]
        shape_index = head.active_shape_key_index
        snapshots, names, warnings = export_face.bake_rest_normals(bpy.context, [head, rig])
        self.assertEqual((names, warnings), (["Head"], []))
        self.assertLessEqual(degrees(corner_normals(head.data), want).max(), 0.5)
        self.assertEqual(rig.data.pose_position, 'POSE')
        self.assertAlmostEqual(rig.pose.bones["Head"].rotation_euler.z, 0.5, places=6)
        self.assertFalse(head.show_only_shape_key)
        self.assertEqual(head.active_shape_key_index, shape_index)
        self.assertEqual([(m.name, m.show_viewport) for m in head.modifiers], before)
        export_face.restore_normals(snapshots)
        self.assertFalse(head.data.has_custom_normals)
        self.assertIsNone(head.data.attributes.get("sharp_edge"))

    def test_existing_custom_normals_and_sharp_edges_come_back_exactly(self):
        head, _rig = face_head()
        mesh = head.data
        for edge in mesh.edges[:40]:
            edge.use_edge_sharp = True
        mesh.normals_split_custom_set_from_vertices([(v.normal.x, v.normal.y + 0.3, v.normal.z) for v in mesh.vertices])
        mesh.update()
        custom, sharp = raw(mesh, "custom_normal"), raw(mesh, "sharp_edge")
        snapshots, names, _warnings = export_face.bake_rest_normals(bpy.context, [head])
        self.assertEqual(names, ["Head"])
        export_face.restore_normals(snapshots)
        for name, saved in (("custom_normal", custom), ("sharp_edge", sharp)):
            now = raw(mesh, name)
            self.assertEqual(now[:2], saved[:2], name)
            self.assertTrue(np.array_equal(now[2], saved[2]), name)

    def test_topology_changing_modifier_before_face_shading_is_skipped(self):
        head, _rig = face_head()
        subdivision = head.modifiers.new("Subdivision", 'SUBSURF')
        head.modifiers.move(head.modifiers.find(subdivision.name), head.modifiers.find(fsn.MODIFIER_NAME))
        snapshots, names, warnings = export_face.bake_rest_normals(bpy.context, [head])
        self.assertEqual((snapshots, names), ([], []))
        self.assertEqual(len(warnings), 1)
        self.assertIn("Subdivision", warnings[0])
        self.assertFalse(head.data.has_custom_normals)

    def test_hidden_modifier_is_not_baked(self):
        head, _rig = face_head()
        fsn.get_modifier(head).show_viewport = False
        self.assertEqual(export_face.bake_rest_normals(bpy.context, [head])[:2], ([], []))

    def test_shared_mesh_data_is_baked_once(self):
        head, _rig = face_head()
        twin = head.copy()
        bpy.context.scene.collection.objects.link(twin)
        snapshots, names, _warnings = export_face.bake_rest_normals(bpy.context, [head, twin])
        self.assertEqual((len(snapshots), len(names)), (1, 1))
        export_face.restore_normals(snapshots)
        self.assertFalse(head.data.has_custom_normals)

    def test_export_model_writes_rest_normals_and_the_meta(self):
        head, rig = face_head()
        want_world = to_world(head, rest_normals(head, rig))
        out = tempfile.mkdtemp(prefix="dt_face_export_")
        target = targets.make_target(out, "Hero")
        rep = dasktoon_export.export_model(bpy.context, target, [head, rig], OPTIONS)
        self.assertEqual(rep.face_meshes, ["Head"])
        self.assertFalse(any(fsn.MODIFIER_NAME in note for note in rep.modifier_notes))
        self.assertTrue(any("Bóng mặt" in line for line in rep.lines()))
        self.assertFalse(head.data.has_custom_normals)
        self.assertEqual(rig.data.pose_position, 'POSE')
        with open(os.path.join(target.root, "Hero/Model/Hero.fbx.meta"), encoding="utf-8") as f:
            self.assertIn("    blendShapeNormalImportMode: 2\n", f.read())
        # Re-import: compare each original corner with the imported corner of the same world vertex and face.
        original = [(tuple(head.matrix_world @ head.data.vertices[loop.vertex_index].co),
                     tuple(head.matrix_world @ poly.center), want_world[loop.index])
                    for poly in head.data.polygons for loop in (head.data.loops[i] for i in poly.loop_indices)]
        tu.reset_scene()
        bpy.ops.import_scene.fbx(filepath=os.path.join(target.root, "Hero/Model/Hero.fbx"))
        imported = next(o for o in bpy.data.objects if o.type == 'MESH')
        mesh = imported.data
        normals = to_world(imported, corner_normals(mesh))
        tree = kdtree.KDTree(len(mesh.loops))
        for poly in mesh.polygons:
            centre = imported.matrix_world @ poly.center
            for i in poly.loop_indices:
                tree.insert((imported.matrix_world @ mesh.vertices[mesh.loops[i].vertex_index].co) * 0.5 + centre * 0.5, i)
        tree.balance()
        worst = 0.0
        for vertex, centre, want in original:
            _co, index, dist = tree.find([(a + b) * 0.5 for a, b in zip(vertex, centre)])
            self.assertLess(dist, 1e-3)
            worst = max(worst, float(degrees(normals[index:index + 1], want[None, :])[0]))
        self.assertLessEqual(worst, 1.0)

    def test_export_without_face_shading_keeps_blend_shape_normals(self):
        tu.reset_scene()
        body = tu.add_sphere(segments=8, rings=4)
        mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        tu.assign(body, mat)
        target = targets.make_target(tempfile.mkdtemp(prefix="dt_face_plain_"), "Plain")
        rep = dasktoon_export.export_model(bpy.context, target, [body], OPTIONS)
        self.assertEqual(rep.face_meshes, [])
        with open(os.path.join(target.root, "Plain/Model/Plain.fbx.meta"), encoding="utf-8") as f:
            self.assertIn("    blendShapeNormalImportMode: 0\n", f.read())

    def test_failed_export_gives_the_mesh_back(self):
        head, rig = face_head()
        target = targets.make_target(tempfile.mkdtemp(prefix="dt_face_fail_"), "Broken")
        with mock.patch.object(model_fbx, "write_fbx", side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                dasktoon_export.export_model(bpy.context, target, [head, rig], OPTIONS)
        self.assertFalse(head.data.has_custom_normals)
        self.assertEqual(rig.data.pose_position, 'POSE')


if __name__ == "__main__":
    tu.run_tests()
```

Thêm vào `tests/python/dasktoon_export_yaml_test.py` (lớp có `test_model_meta_remaps_materials_by_fbx_name`):

```python
    def test_model_meta_turns_blend_shape_normals_off_for_face_shading(self):
        self.assertIn("    blendShapeNormalImportMode: 0\n", uy.model_meta(TEX, {}, False))
        self.assertIn("    blendShapeNormalImportMode: 2\n", uy.model_meta(TEX, {}, False, blend_shape_normals=False))
```

Thêm vào `tests/python/dasktoon_export_fbx_test.py` (lớp `FbxTest`), và import `from bl_ui import dasktoon_face_shading_nodes as fsn`:

```python
    def test_modifier_notes_skip_face_shading(self):
        obj = outlined_character()
        fsn.ensure_modifier(obj)
        self.assertEqual(model_fbx.modifier_notes([obj]), [])
```

- [ ] **Step 2: Chạy test, phải đỏ**

Run: đồng bộ script rồi chạy `dasktoon_face_shading_export_test.py`, `dasktoon_export_yaml_test.py`, `dasktoon_export_fbx_test.py`.
Expected: FAIL — `ImportError: cannot import name 'face_shading' from 'dasktoon_export'`; yaml: `TypeError: model_meta() got an
unexpected keyword argument 'blend_shape_normals'`; fbx: `modifier_notes` liệt kê `DaskToon Face Shading`.

- [ ] **Step 3: Viết module export**

File: `scripts/modules/dasktoon_export/face_shading.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Face shading for game engines (docs/superpowers/specs/2026-10-04-dasktoon-face-shading-design.md, section 6):
the ellipsoid normals at rest are written as the mesh's custom normals for the FBX, then the mesh is given back as it
was (custom_normal and sharp_edge, which normals_split_custom_set may change)."""

from contextlib import contextmanager

import bpy
import numpy as np

# Attribute data type -> (foreach key, values per element, numpy type)
_LAYOUTS = {
    'INT16_2D': ("value", 2, np.int32),
    'FLOAT_VECTOR': ("vector", 3, np.float32),
    'BOOLEAN': ("value", 1, bool),
}
_SAVED = ("custom_normal", "sharp_edge")


def face_shaded(objects):
    """Mesh objects whose Face Shading modifier is shown in the viewport, one per mesh data."""
    from bl_ui import dasktoon_face_shading_nodes as fsn
    found, seen = [], set()
    for obj in objects:
        modifier = fsn.get_modifier(obj) if obj.type == 'MESH' else None
        if modifier is None or not modifier.show_viewport or obj.data in seen:
            continue
        seen.add(obj.data)
        found.append(obj)
    return found


def _snapshot(mesh):
    saved = {}
    for name in _SAVED:
        attr = mesh.attributes.get(name)
        if attr is None:
            saved[name] = None
            continue
        key, width, dtype = _LAYOUTS[attr.data_type]
        values = np.empty(len(attr.data) * width, dtype=dtype)
        attr.data.foreach_get(key, values)
        saved[name] = (attr.domain, attr.data_type, values)
    return saved


def _supported(mesh):
    return all(mesh.attributes.get(name) is None or mesh.attributes[name].data_type in _LAYOUTS for name in _SAVED)


def _restore(mesh, saved):
    for name, value in saved.items():
        attr = mesh.attributes.get(name)
        if attr is not None:
            mesh.attributes.remove(attr)
        if value is not None:
            domain, data_type, values = value
            mesh.attributes.new(name, data_type, domain).data.foreach_set(_LAYOUTS[data_type][0], values)
    mesh.update()


def _armatures(objects):
    from bl_ui import dasktoon_face_shading as fs
    rigs = []
    for obj in objects:
        rigs.append(fs.find_armature(obj))
        proxy = fs.proxy_of(obj)
        if proxy is not None and proxy.parent is not None and proxy.parent.type == 'ARMATURE':
            rigs.append(proxy.parent)
    return [rig for rig in dict.fromkeys(rigs) if rig is not None]


@contextmanager
def _rest_state(objects):
    """Rest Position, the Basis shape only and nothing after Face Shading (face spec 6.2); restored even on error."""
    from bl_ui import dasktoon_face_shading as fs
    from bl_ui import dasktoon_face_shading_nodes as fsn
    keys = [(o, o.show_only_shape_key, o.active_shape_key_index) for o in objects if o.data.shape_keys is not None]
    hidden = []
    for obj in objects:
        index = obj.modifiers.find(fsn.MODIFIER_NAME)
        hidden += [m for m in list(obj.modifiers)[index + 1:] if m.show_viewport]
    try:
        for obj, _only, _index in keys:
            obj.show_only_shape_key = True
            obj.active_shape_key_index = 0
        for modifier in hidden:
            modifier.show_viewport = False
        with fs.rest_pose(_armatures(objects)):
            yield
    finally:
        for modifier in hidden:
            modifier.show_viewport = True
        for obj, only, index in keys:
            obj.show_only_shape_key = only
            obj.active_shape_key_index = index
        bpy.context.view_layer.update()


def _before_face_shading(obj):
    from bl_ui import dasktoon_face_shading_nodes as fsn
    names = []
    for modifier in obj.modifiers:
        if modifier.name == fsn.MODIFIER_NAME:
            break
        if modifier.type != 'ARMATURE':
            names.append(modifier.name)
    return names


def bake_rest_normals(context, objects):
    """Face spec 6.1-6.4: write the rest-pose face shading normals as custom normals of each face-shaded mesh.
    Returns (snapshots, names, warnings); always hand the snapshots to restore_normals() after the FBX."""
    targets, warnings = [], []
    for obj in face_shaded(objects):
        if obj.data.library is not None:
            warnings.append("%s: mesh link từ thư viện, không ghi được bóng mặt" % obj.name)
        elif not _supported(obj.data):
            warnings.append("%s: custom normal kiểu lạ, không ghi được bóng mặt" % obj.name)
        else:
            targets.append(obj)
    if not targets:
        return [], [], warnings
    normals = {}
    with _rest_state(targets):
        depsgraph = context.evaluated_depsgraph_get()
        for obj in targets:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            if len(mesh.loops) == len(obj.data.loops):
                values = np.empty(len(mesh.loops) * 3, dtype=np.float32)
                mesh.corner_normals.foreach_get("vector", values)
                normals[obj] = values.reshape(-1, 3)
            else:
                warnings.append("%s: modifier %s đổi số đỉnh trước Face Shading; hãy Apply trước khi export, bóng mặt "
                                "chưa được ghi" % (obj.name, ", ".join(_before_face_shading(obj)) or "?"))
            evaluated.to_mesh_clear()
    snapshots, names = [], []
    for obj, values in normals.items():
        snapshots.append((obj.data, _snapshot(obj.data)))
        obj.data.normals_split_custom_set(values)
        names.append(obj.name)
    return snapshots, names, warnings


def restore_normals(snapshots):
    for mesh, saved in snapshots:
        _restore(mesh, saved)
```

- [ ] **Step 4: Nối vào `export_model`, `.meta`, `modifier_notes`, báo cáo**

`scripts/modules/dasktoon_export/unity_yaml.py`: đổi chữ ký thành
`def model_meta(guid, materials, import_animation, blend_shape_normals=True):`, thêm vào docstring câu
`` `blend_shape_normals` False sets the blend shape normals to None (face shading, face spec 6). ``, và thay dòng
`"    blendShapeNormalImportMode: 0",` bằng `"    blendShapeNormalImportMode: %d" % (0 if blend_shape_normals else 2),`.

`scripts/modules/dasktoon_export/model_fbx.py`: trong `modifier_notes`, thêm `from bl_ui import dasktoon_face_shading_nodes as fsn`,
đổi docstring thành `"""Modifiers other than Armature, the DaskToon outline and face shading are not in the FBX (Apply
Modifiers is off; face shading is written as normals)."""` và điều kiện thành
`m.type != 'ARMATURE' and m.name not in (gn.MODIFIER_NAME, fsn.MODIFIER_NAME)`.

`scripts/modules/dasktoon_export/report.py`: thêm trường `face_meshes: list = field(default_factory=list)` sau `outline_meshes`,
và trong `lines()` ngay sau dòng `DT_OutlineN/W`:

```python
        if self.face_meshes:
            out.append("Bóng mặt: đã ghi normal khối trứng (tư thế nghỉ) cho: %s; blend shape trong FBX không đổi normal"
                       % ", ".join(self.face_meshes))
```

`scripts/modules/dasktoon_export/__init__.py`: tách phần giữa của `export_model` thành `_write_model` và bọc bằng `try/finally`:

```python
def _write_model(context, target, objects, meshes, options, rep):
    """Outline data, materials, shaders and the FBX (spec 3-5)."""
    from . import assets, graph, model_fbx, shaders_install, unity_yaml
    rep.outline_meshes, errors = model_fbx.prepare_outline_data(meshes)
    rep.warnings += errors
    rep.modifier_notes = model_fbx.modifier_notes(meshes)
    shaders_install.ensure_root(target)
    writer = _Writer(target, options, rep)
    writer.folder(target.name)
    mat_guids = {}
    if options.export_materials:
        rep.shaders = 'INSTALLED' if shaders_install.install_shaders(target, rep.warnings) else 'UP_TO_DATE'
        for mat, users in _materials(meshes).items():
            mesh_data = list(dict.fromkeys(o.data for o in users))
            spec, reason = graph.analyze_material(mat, mesh_data)
            if spec is None:
                rep.skipped.append((mat.name, reason))
                continue
            guid = writer.material(spec, users)
            if guid is not None:
                mat_guids[mat.name] = guid
    if options.model_format == 'FBX':
        model_dir = target.name + "/Model"
        writer.folder(model_dir)
        rel = "%s/%s.fbx" % (model_dir, safe_name(target.name))
        guid = writer.guid(rel)
        meta = unity_yaml.model_meta(guid, mat_guids, options.include_animation,
                                     blend_shape_normals=not rep.face_meshes)
        left_out = []

        def write_fbx(path):
            left_out.extend(model_fbx.write_fbx(context, objects, path, options.include_animation))

        if assets.write_asset(target.root, rel, guid, meta, rep.warnings, writer=write_fbx):
            rep.model = rel
        if left_out:
            rep.warnings.append("Không đưa vào FBX: %s (không nằm trong view layer hiện tại, ví dụ collection bị loại trừ)"
                                % ", ".join(left_out))
    return writer


def export_model(context, target, objects, options):
    """Write `objects` (FBX), their DaskToon materials and the shaders to `target` (spec 3-5). Returns a Report.
    Face-shaded meshes get their rest-pose face normals for the FBX and are given back afterwards (face spec 6)."""
    from . import assets, face_shading, targets, unity_yaml
    if target.engine not in targets.SUPPORTED_ENGINES:
        raise ValueError("Engine %s chưa được hỗ trợ" % target.engine)
    rep = report.Report(mode=target.mode, root=target.root, name=target.name)
    meshes = [o for o in objects if o.type == 'MESH']
    snapshots, rep.face_meshes, errors = face_shading.bake_rest_normals(context, meshes)
    rep.warnings += errors
    try:
        writer = _write_model(context, target, objects, meshes, options, rep)
    finally:
        face_shading.restore_normals(snapshots)
    rep.light_hint = report.light_hint(context.scene)
    rep.ambient_hint = report.ambient_hint(context.scene)
    if target.mode == 'FOLDER':
        guid = writer.guid("README.txt")
        assets.write_asset(target.root, "README.txt", guid, unity_yaml.text_meta(guid), rep.warnings,
                           data=report.readme_text(rep).encode("utf-8"))
    report.write_text(rep)
    return rep
```

Lưu ý: `bake_rest_normals` nhận cả các mesh đi kèm (danh sách `meshes`); armature được tìm từ chính mesh nên không cần truyền.

- [ ] **Step 5: Chạy test, phải xanh**

Run: đồng bộ script rồi chạy `dasktoon_face_shading_export_test.py`, `dasktoon_export_yaml_test.py`, `dasktoon_export_fbx_test.py`,
`dasktoon_export_layout_test.py`, `dasktoon_export_textures_test.py`, `dasktoon_engine_export_ui_test.py`.
Expected: tất cả OK (`dasktoon_face_shading_export_test.py`: `Ran 8 tests ... OK`).

- [ ] **Step 6: Đăng ký test và commit**

Thêm `dasktoon_face_shading_export_test` vào danh sách `foreach(dasktoon_test ...)` trong `tests/python/CMakeLists.txt`.

```bash
git add scripts/modules/dasktoon_export/ tests/python/dasktoon_face_shading_export_test.py tests/python/dasktoon_export_yaml_test.py tests/python/dasktoon_export_fbx_test.py tests/python/CMakeLists.txt
git commit -m "feat: export face shading to Unity as rest-pose ellipsoid normals and give the mesh back afterwards"
```

---

### Task 6: So sánh render Unity và ảnh duyệt

**Files:**
- Modify: `tests/python/dasktoon_unity_render_test.py` (trường hợp `face_shading`)
- Create: `tests/python/dasktoon_face_review.py` (script ảnh duyệt, không phải test tự động)
- Create: `docs/superpowers/reports/2026-10-04-face-shading-review.png` (do script sinh ra)
- Modify: `docs/superpowers/reports/2026-10-03-unity-compare.png` (bài so sánh ghi lại)

**Interfaces:**
- Consumes: `tu.add_test_head`, `fs.setup`, `fsn.MODIFIER_NAME`, `dasktoon_export.export_model`.
- Produces: không có hàm mới cho task khác.

- [ ] **Step 1: Thêm trường hợp vào bài so sánh Unity (test tích hợp, kiểm ở Step 2)**

Trong `tests/python/dasktoon_unity_render_test.py`:
- import thêm `from bl_ui import dasktoon_face_shading as face_shading  # noqa: E402`;
- thêm hằng `FACE_CASE = "face_shading"` sau `MODEL_NAME`;
- thêm `(FACE_CASE, lambda: bsdf(FACE_CASE)[0], True),` vào cuối `CASES`;
- thêm hàm:

```python
def face_head(location):
    """The face shading test head at the size of the spheres, set up from all its vertices (no armature)."""
    head, _rig = tu.add_test_head(radius=0.5, centre=location, with_armature=False)
    face_shading.setup(head, selected=range(len(head.data.vertices)))
    return head
```

- trong `build_scene`, thay khối tạo sphere trong vòng lặp bằng:

```python
    for i, (name, builder, _graded) in enumerate(CASES):
        location = (i * SPACING, 0.0, 0.0)
        if name == FACE_CASE:
            obj = face_head(location)
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, segments=48, ring_count=24, location=location)
            obj = bpy.context.active_object
            obj.data.shade_smooth()
        obj.name = "Case_" + name
        tu.assign(obj, builder())
        spheres.append(obj)
```

- [ ] **Step 2: Chạy bài so sánh Unity**

Run: đồng bộ script rồi `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_unity_render_test.py 2>&1 | tail -60`
Expected: `OK`; trong bảng JSON in ra, `face_shading` có `max_diff ≤ 0.03`. Ảnh `docs/superpowers/reports/2026-10-03-unity-compare.png`
có thêm một hàng. Nếu lệch: so ảnh hai bên trước khi kết luận (normal FBX, `.meta`, vị trí camera).

- [ ] **Step 3: Viết script ảnh duyệt**

File: `tests/python/dasktoon_face_review.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Before / after sheet of DaskToon face shading for human review (not an automated test, face spec 8).

DaskToon.exe --background --factory-startup --python tests/python/dasktoon_face_review.py [-- <character.blend>]

Rows, top to bottom: the test head without / with face shading, then (when a .blend is given) the character's head
without / with. Columns: three Sun angles. The .blend is opened read-only and never saved.
Writes docs/superpowers/reports/2026-10-04-face-shading-review.png."""

import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_face_shading as fs  # noqa: E402
from bl_ui import dasktoon_face_shading_nodes as fsn  # noqa: E402
from dasktoon_export import textures  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHEET = os.path.join(REPO, "docs", "superpowers", "reports", "2026-10-04-face-shading-review.png")
SIZE = 256
# Sun rotations: key light from the front left and above, front right and lower, then a side light.
SUNS = ((math.radians(60.0), 0.0, math.radians(-40.0)),
        (math.radians(75.0), 0.0, math.radians(30.0)),
        (math.radians(40.0), 0.0, math.radians(-100.0)))


def srgb(x):
    x = np.clip(x, 0.0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def prepare_render(scene):
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'OPEN_EXR'
    scene.eevee.taa_render_samples = 16
    if scene.camera is None:
        cam = bpy.data.objects.new("ReviewCamera", bpy.data.cameras.new("ReviewCamera"))
        scene.collection.objects.link(cam)
        scene.camera = cam


def front_camera(scene, centre, scale):
    cam = scene.camera
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = scale
    cam.data.clip_start = 0.01
    cam.data.clip_end = 100.0
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)  # looks along +Y, at the face
    cam.location = (centre.x, centre.y - 10.0, centre.z)


def render(name):
    pixels, (w, h) = tu.render_pixels(name)
    return np.array(pixels).reshape(h, w, 4)


def before_after(faced, sun, tag):
    """[[tiles without face shading], [tiles with]] over the Sun angles."""
    rows = []
    for on in (False, True):
        for obj in faced:
            modifier = fsn.get_modifier(obj)
            modifier.show_viewport = modifier.show_render = on
        tiles = []
        for i, rotation in enumerate(SUNS):
            sun.rotation_euler = rotation
            tiles.append(render("%s_%d_%d" % (tag, on, i)))
        rows.append(tiles)
    return rows


def test_head_rows():
    scene = tu.reset_scene(SIZE)
    prepare_render(scene)
    tu.set_world_color((0.05, 0.06, 0.08))
    sun = tu.add_sun(3.0)
    sun.data.use_shadow = False
    head, _rig = tu.add_test_head(radius=1.0, centre=(0.0, 0.0, 0.0))
    mat, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    node.inputs["Base Color"].default_value = (0.95, 0.80, 0.72, 1.0)
    tu.assign(head, mat)
    fs.setup(head)
    front_camera(scene, Vector((0.0, 0.0, 0.0)), 2.8)
    return before_after([head], sun, "head")


def face_mesh(scene):
    """(mesh, armature): among meshes weighted to a head bone, the one with the most forward vertex in the middle strip
    of its head (the face skin, face spec 5.3)."""
    best = None
    for obj in scene.objects:
        if obj.type != 'MESH' or not obj.visible_get():
            continue
        armature = fs.find_armature(obj)
        bone = fs.find_head_bone(armature) if armature is not None else None
        if bone is None:
            continue
        try:
            head = fs.head_vertices(obj, bone)
        except fs.FaceShadingError:
            continue
        with fs.rest_pose([armature]):
            world = np.array([tuple(obj.matrix_world @ obj.data.vertices[i].co) for i in head])
        low, high = world[:, 0].min(), world[:, 0].max()
        middle = world[np.abs(world[:, 0] - (low + high) / 2.0) <= 0.25 * (high - low)]
        front = middle[:, 1].min()
        if best is None or front < best[0]:
            best = (front, obj, armature)
    return (best[1], best[2]) if best else (None, None)


def character_rows(path):
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    scene = bpy.context.scene
    face, armature = face_mesh(scene)
    if face is None:
        print("REVIEW: no face mesh found in", path)
        return []
    print("REVIEW: face mesh", face.name, "armature", armature.name)
    proxy = fs.setup(face)
    prepare_render(scene)
    for obj in scene.objects:
        if obj.type == 'LIGHT':
            obj.hide_render = True
    sun = tu.add_sun(3.0)
    sun.data.use_shadow = False
    bpy.context.view_layer.update()
    centre = proxy.matrix_world.translation
    front_camera(scene, centre, 3.2 * max(proxy.matrix_world.to_scale()))
    return before_after([face], sun, "character")


def write_sheet(rows):
    height, width = SIZE * len(rows), SIZE * len(SUNS)
    sheet = np.zeros((height, width, 4))
    for r, tiles in enumerate(rows):
        y0 = height - (r + 1) * SIZE
        for c, tile in enumerate(tiles):
            sheet[y0:y0 + SIZE, c * SIZE:(c + 1) * SIZE] = tile
    sheet[..., :3] = srgb(sheet[..., :3])
    sheet[..., 3] = 1.0
    data = (np.clip(sheet, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).tobytes()
    with open(SHEET, "wb") as f:
        f.write(textures.png_bytes(width, height, data))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    rows = test_head_rows()
    if argv:
        rows += character_rows(argv[0])
    write_sheet(rows)
    print("REVIEW SHEET", SHEET)


main()
```

- [ ] **Step 4: Sinh ảnh duyệt và tự xem**

Run: đồng bộ script rồi
`"$DT" --background --factory-startup --python tests/python/dasktoon_face_review.py -- "D:/game/lagote rabina/tdt.blend" 2>&1 | grep REVIEW`
Expected: `REVIEW: face mesh ...` và `REVIEW SHEET .../2026-10-04-face-shading-review.png`. Mở ảnh: hàng "with" có ranh giới sáng
tối cong mượt trên mặt, còn bóng mũi nhỏ và bóng dưới cằm; không có vệt lạ ở cổ, tóc. Không lưu `tdt.blend`.

- [ ] **Step 5: Commit**

```bash
git add tests/python/dasktoon_unity_render_test.py tests/python/dasktoon_face_review.py docs/superpowers/reports/2026-10-04-face-shading-review.png docs/superpowers/reports/2026-10-03-unity-compare.png
git commit -m "test: compare face shading between DaskToon and Unity, and render a before/after review sheet"
```

---

### Task 7: Toàn bộ test, báo cáo

**Files:**
- Create: `docs/superpowers/reports/2026-10-04-dasktoon-face-shading-report.md`

**Interfaces:**
- Consumes: kết quả các task trước, ledger `.superpowers/sdd/2026-10-04-dasktoon-face-shading/progress.md`.
- Produces: báo cáo cho người dùng.

- [ ] **Step 1: Chạy toàn bộ test DaskToon**

Run: đồng bộ script rồi chạy lần lượt mọi file trong danh sách `foreach(dasktoon_test ...)` của `tests/python/CMakeLists.txt`.
Expected: mọi file OK.

- [ ] **Step 2: Viết báo cáo**

`docs/superpowers/reports/2026-10-04-dasktoon-face-shading-report.md` (tiếng Việt, cho người dùng), gồm: tóm tắt; cách dùng
(3 bước); những gì đã kiểm chứng (số test, bài Unity với số liệu `face_shading`, ảnh duyệt); các quyết định đã tự đưa ra
(chép từ các dòng `Ruling:` của ledger, kèm cái giá nếu sai); giới hạn còn lại; nhắc lỗ hổng AI Bridge (cổng 9998, commit
b9dbe7997f9) chưa sửa; việc người dùng cần làm (export lại nhân vật, xem ảnh duyệt, chọn merge / PR / giữ nhánh).

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/reports/2026-10-04-dasktoon-face-shading-report.md
git commit -m "docs: add the face shading report"
```
