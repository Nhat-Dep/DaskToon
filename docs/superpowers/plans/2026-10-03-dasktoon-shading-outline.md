# DaskToon: lõi đổ bóng và outline mới (Dự án 1) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng đã chọn chạy **inline** (superpowers:executing-plans), tự động, trên nhánh `dasktoon-shading-outline`, commit từng task.

**Goal:** Ba node cel (Anime BSDF, Anime Cel, Dask Cel) dùng chung một lõi đổ bóng hai chế độ (Đơn giản / Dải) có preset và style riêng của người dùng; outline được làm lại bằng Geometry Nodes, theo từng material, với độ dày thay đổi theo từng đỉnh và dữ liệu sẵn cho game.

**Architecture:**
- Phần GLSL dùng chung nằm trong `gpu_shader_material_dasktoon_shading.glsl`. Ba node C++ lưu dải màu trong storage `ColorBand` (giống node ColorRamp) và truyền lên GPU qua `GPU_color_band`.
- Phần Python (trong `scripts/startup/bl_ui/`) lo preset, đồng bộ outline (dựng node group Geometry Nodes theo từng object), dữ liệu game (UV map `DT_OutlineN/W`) và nâng cấp file cũ khi mở.

**Tech Stack:** C++ (Blender 5.2 core của DaskToon), GLSL (EEVEE), Python `bpy` + `numpy`, Geometry Nodes, MSBuild (VS 2022, v143), test `unittest` chạy trong `DaskToon.exe --background`.

**Spec:** `docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md`

---

## Môi trường và các lệnh dùng chung

Mọi lệnh chạy trong Git Bash, thư mục gốc là `d:/DaskToon`.

```bash
DT=/d/build_windows_x64_vc17_Release/bin/Release/DaskToon.exe
BUILD=/d/build_windows_x64_vc17_Release
MSBUILD="/c/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe"
```

- **Build** (bắt buộc sau mỗi thay đổi C++ hoặc GLSL). Target INSTALL build những gì đã đổi rồi chép exe, GLSL và scripts vào `bin/Release`.
  ```bash
  time MSYS_NO_PATHCONV=1 "$MSBUILD" "D:/build_windows_x64_vc17_Release/INSTALL.vcxproj" -p:Configuration=Release -m -v:m -nologo 2>&1 | tail -30
  ```
  Đóng DaskToon trước khi build. Build lâu nên chạy nền (`run_in_background`), và trong lúc chờ thì chỉ sửa những file *không* nằm trong lần build đó.
- **Đồng bộ script** khi chỉ sửa Python, không cần build:
  ```bash
  cp -r scripts/startup/. "$BUILD/bin/Release/5.2/scripts/startup/"
  ```
- **Chạy một file test:**
  ```bash
  "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/<file>.py 2>&1 | tail -40
  ```
  Exit code 0 nghĩa là PASS. Ảnh render tạm nằm trong `$DASKTOON_TEST_OUT` (mặc định là một thư mục temp).

## Global Constraints

- Chế độ Đơn giản phải cho ra **đúng** look hiện tại của Anime BSDF và Dask Cel (sai số ≤ 1e-3 trên ảnh EXR linear, so với baseline chụp trước khi refactor).
- Không thêm struct DNA mới. Dải màu dùng storage `"ColorBand"`. Cờ và enum dùng các bit theo bảng ở spec mục 3.5:
  - Anime BSDF: `custom1` bit 0–3 ambient, bit 4–7 outline tint, bit 8–11 light mode; `custom2` bit 0–5 module, bit 6 Dải.
  - Anime Cel: `custom1` ambient; `custom2` bit 0–3 light mode, bit 8 Dải.
  - Dask Cel: `custom1` outline tint; `custom2` bit 0 Dải.
- Giá trị enum Ambient Mode: `OVERLAY=0, HUE=1, HUE_SAT=2, SAT=3, VAL=4, MULTIPLY=5, MIX=6`.
- Giá trị enum Light Mode: `OVERLAY=0, HUE=1, MULTIPLY=2, ADD=3, PURE_CEL=4`. Công thức theo spec mục 3.10.
- Tên cố định:
  - Material đi kèm: `<tên material>.Outline`, trỏ tới qua ID property `dasktoon_outline_material`.
  - Cờ outline cho nguồn số 3: `dasktoon_outline`.
  - Modifier: `DaskToon Outline`, luôn nằm cuối stack.
  - Node group: `DaskToon_OutlineCore` và `DT_Outline::<tên object>`.
  - UV map: `DT_OutlineN`, `DT_OutlineW`. Dấu trên mesh: `dt_outline_sig`.
  - Dấu phiên bản: `scene["dasktoon_data_version"] = 1`.
- Chỉ `dasktoon.outline_prepare_game_data` và bước nâng cấp file cũ được ghi vào mesh data.
- **Không** sửa và không commit `scripts/startup/dasktoon_init.py`, `scripts/startup/dasktoon_ai_bridge.py`, `tools/dasktoon_mcp_server.py` (thay đổi chưa commit của người dùng). Không push.
- Chỗ nào spec chưa nói rõ: tự chọn phương án gần spec nhất và ghi vào `docs/superpowers/reports/2026-10-03-dasktoon-progress.md`.

## Review Focus

1. **Có node trung gian giữa node chính và Material Output** (Reroute, Frame, hoặc node chính không nối thẳng ra Output). Người dùng vẫn mong outline được nhận ra. Test nằm ở Task 8.
2. **Slot rỗng, object không có material, hoặc object không phải mesh**: bộ đồng bộ không được lỗi, và không thêm modifier. Test ở Task 8.
3. **Mesh không có UV map, hoặc có ngon**: outline vẫn chạy (chỉ tắt Wobble). Thao tác ghi dữ liệu game phải báo lỗi rõ ràng, không làm hỏng mesh. Test ở Task 7 và Task 9.
4. **Object có scale không đều** (ví dụ (1, 1, 2)): độ dày nét tính theo mét trong thế giới. Test ở Task 7.
5. **Đổi tên material hoặc object sau khi đã bật outline**: không sinh thêm một material `.Outline` thứ hai, và outline vẫn còn. Test ở Task 8.

## Cấu trúc file

| File | Trách nhiệm |
|---|---|
| `source/blender/gpu/shaders/material/gpu_shader_material_dasktoon_shading.glsl` (mới) | Lõi đổ bóng dùng chung: HSV, Simple, Ramp, Ambient Mode, Light Mode |
| `source/blender/gpu/shaders/material/gpu_shader_material_{anime_character,anime_cel,dask_cel}.glsl` | Gọi lõi chung |
| 8 file GLSL có lỗi weight | Sửa `w = weight` |
| `source/blender/nodes/NOD_dasktoon_shading.hh` (mới) | API dùng chung cho C++ và RNA: bit chế độ, dải mặc định, light mode |
| `source/blender/nodes/shader/node_shader_dasktoon_shading.{hh,cc}` (mới) | Phần cài đặt, liên kết GPU và vẽ giao diện dùng chung |
| `source/blender/nodes/shader/nodes/node_shader_{anime_character,anime_cel,dask_cel}.cc` | Storage, init, ẩn/hiện socket, vẽ giao diện, hàm GPU |
| `source/blender/makesrna/intern/rna_nodetree.cc` | `shading_mode`, `shading_ramp`, `light_blend_mode` (sửa lỗi ghi đè), RNA mới cho Anime Cel |
| `scripts/startup/bl_ui/dasktoon_shading_styles.py` (mới) | Preset, style của người dùng, các operator và menu |
| `scripts/startup/bl_ui/dasktoon_outline_nodes.py` (mới) | Dựng node group Geometry Nodes cho outline (chỉ dựng, không đồng bộ) |
| `scripts/startup/bl_ui/dasktoon_outline.py` (mới) | Nguồn outline, material `.Outline`, handler đồng bộ, panel |
| `scripts/startup/bl_ui/dasktoon_outline_gamedata.py` (mới) | Ghi `DT_OutlineN/W` và operator |
| `scripts/startup/bl_ui/dasktoon_upgrade.py` (mới) | Dấu phiên bản, nâng cấp node và outline cũ, báo cáo |
| `scripts/startup/bl_ui/dasktoon_anime_nodes.py` | Gỡ handler cũ, viết lại preset OUTLINE |
| `scripts/startup/bl_ui/__init__.py` | Đăng ký các module mới |
| `tests/python/dasktoon_*.py`, `tests/python/dasktoon_data/` | Test, fixture và baseline |

---

### Task 1: Hạ tầng test, fixture file cũ, kiểm chứng giả định của nền tảng

**Files:**
- Create: `tests/python/dasktoon_test_utils.py`
- Create: `tests/python/dasktoon_platform_test.py`
- Create: `tests/python/dasktoon_make_legacy_fixtures.py`
- Create (sinh ra): `tests/python/dasktoon_data/dasktoon_legacy_nodes.blend`, `tests/python/dasktoon_data/dasktoon_legacy_outline.blend`

**Interfaces:**
- Produces: module `dasktoon_test_utils`, import là `tu`:
  - `reset_scene(resolution=16)`, `setup_render_scene()`, `set_world_color(rgb)`
  - `add_plane(size)`, `add_sphere(radius, segments, rings)`, `add_sun(strength, rotation, color)`
  - `new_material(name)`, `emission_material(name, rgba, strength)`, `node_material(name, node_type) -> (mat, node)`, `mix_with_black_material(name, node_type) -> (mat, node)`, `assign(obj, mat)`
  - `render_pixels(name) -> (list, (w, h))`, `render_center(name) -> (r, g, b, a)`
  - `run_tests()`, cùng các hằng `OUT_DIR`, `DATA_DIR`

- [ ] **Step 1: Viết `tests/python/dasktoon_test_utils.py`**

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Helpers shared by the DaskToon tests. Runs inside DaskToon (--background)."""

import os
import sys
import tempfile
import unittest

import bpy

OUT_DIR = os.environ.get("DASKTOON_TEST_OUT") or tempfile.mkdtemp(prefix="dasktoon_test_")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dasktoon_data")


def _drop_legacy_outline_handler():
    """The pre-rewrite outline handler adds Solidify modifiers behind the tests' back."""
    handlers = bpy.app.handlers.depsgraph_update_post
    for handler in list(handlers):
        if getattr(handler, "__name__", "") == "dasktoon_vrm_outline_auto_sync":
            handlers.remove(handler)


def setup_render_scene(resolution=16):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'OPEN_EXR'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    if scene.world is None:
        scene.world = bpy.data.worlds.new("TestWorld")
    set_world_color((0.0, 0.0, 0.0))
    if scene.camera is None:
        cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
        scene.collection.objects.link(cam)
        cam.location = (0.0, 0.0, 5.0)
        scene.camera = cam
    return scene


def reset_scene(resolution=16):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _drop_legacy_outline_handler()
    return setup_render_scene(resolution)


def set_world_color(rgb):
    bg = bpy.context.scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)


def add_plane(size=4.0):
    bpy.ops.mesh.primitive_plane_add(size=size)
    return bpy.context.active_object


def add_sphere(radius=1.0, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=segments, ring_count=rings)
    obj = bpy.context.active_object
    obj.data.shade_smooth()
    return obj


def add_sun(strength=1.0, rotation=(0.0, 0.0, 0.0), color=(1.0, 1.0, 1.0)):
    data = bpy.data.lights.new("Sun", 'SUN')
    data.energy = strength
    data.color = color
    obj = bpy.data.objects.new("Sun", data)
    obj.rotation_euler = rotation
    bpy.context.scene.collection.objects.link(obj)
    return obj


def new_material(name):
    mat = bpy.data.materials.new(name)
    mat.node_tree.nodes.clear()
    return mat


def emission_material(name, rgba, strength=1.0):
    mat = new_material(name)
    nt = mat.node_tree
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emission = nt.nodes.new('ShaderNodeEmission')
    emission.inputs["Color"].default_value = rgba
    emission.inputs["Strength"].default_value = strength
    nt.links.new(emission.outputs[0], out.inputs["Surface"])
    return mat


def node_material(name, node_type):
    """Material whose Surface is driven directly by one node of `node_type`."""
    mat = new_material(name)
    nt = mat.node_tree
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    node = nt.nodes.new(node_type)
    nt.links.new(node.outputs[0], out.inputs["Surface"])
    return mat, node


def mix_with_black_material(name, node_type):
    """node -> Mix Shader slot 1, black emission -> slot 2, factor = Is Camera Ray (1, not constant)."""
    mat = new_material(name)
    nt = mat.node_tree
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    node = nt.nodes.new(node_type)
    mix = nt.nodes.new('ShaderNodeMixShader')
    black = nt.nodes.new('ShaderNodeEmission')
    black.inputs["Strength"].default_value = 0.0
    light_path = nt.nodes.new('ShaderNodeLightPath')
    nt.links.new(light_path.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(node.outputs[0], mix.inputs[1])
    nt.links.new(black.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat, node


def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def render_pixels(name):
    """Render to a linear EXR; return (flat RGBA list, (width, height))."""
    scene = bpy.context.scene
    path = os.path.join(OUT_DIR, name + ".exr")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path, check_existing=False)
    pixels = list(img.pixels)
    size = tuple(img.size)
    bpy.data.images.remove(img)
    return pixels, size


def render_center(name):
    pixels, (w, h) = render_pixels(name)
    i = ((h // 2) * w + w // 2) * 4
    return tuple(pixels[i:i + 4])


def run_tests():
    argv = [sys.argv[0]]
    if "--" in sys.argv:
        argv += sys.argv[sys.argv.index("--") + 1:]
    result = unittest.main(module="__main__", argv=argv, exit=False).result
    sys.exit(0 if result.wasSuccessful() else 1)
```

- [ ] **Step 2: Viết `tests/python/dasktoon_platform_test.py`.** Hai test này kiểm chứng giả định nền tảng ở spec mục 4.3 và 5, không phải kiểu TDD.

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402


def _geometry_group(name):
    tree = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    tree.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    return tree


class PlatformAssumptions(unittest.TestCase):
    def test_set_material_outside_slots_renders(self):
        """Spec 4.3: Set Material may use a material that is not in the object's slots."""
        tu.reset_scene()
        plane = tu.add_plane()
        red = tu.emission_material("Red", (1.0, 0.0, 0.0, 1.0))
        blue = tu.emission_material("Blue", (0.0, 0.0, 1.0, 1.0))
        plane.data.materials.append(red)
        tree = _geometry_group("Spike")
        nodes, links = tree.nodes, tree.links
        group_in, group_out = nodes.new('NodeGroupInput'), nodes.new('NodeGroupOutput')
        lift = nodes.new('GeometryNodeSetPosition')
        lift.inputs["Offset"].default_value = (0.0, 0.0, 0.5)
        set_material = nodes.new('GeometryNodeSetMaterial')
        set_material.inputs["Material"].default_value = blue
        join = nodes.new('GeometryNodeJoinGeometry')
        links.new(group_in.outputs[0], lift.inputs["Geometry"])
        links.new(lift.outputs[0], set_material.inputs["Geometry"])
        links.new(group_in.outputs[0], join.inputs[0])
        links.new(set_material.outputs[0], join.inputs[0])
        links.new(join.outputs[0], group_out.inputs[0])
        plane.modifiers.new("Spike", 'NODES').node_group = tree
        self.assertEqual(len(plane.material_slots), 1)
        r, _g, b, _a = tu.render_center("set_material_outside_slots")
        self.assertGreater(b, 0.5)
        self.assertLess(r, 0.1)

    def test_real_uv_map_and_shape_keys_survive_fbx(self):
        """Spec 5: real UV maps survive FBX export together with shape keys."""
        tu.reset_scene()
        obj = tu.add_sphere(segments=16, rings=8)
        obj.shape_key_add(name="Basis")
        key = obj.shape_key_add(name="Smile")
        key.data[0].co.z += 0.1
        obj.data.uv_layers.new(name="DT_OutlineN")
        path = os.path.join(tu.OUT_DIR, "uv_shape_keys.fbx")
        bpy.ops.export_scene.fbx(filepath=path, use_mesh_modifiers=False)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=path)
        imported = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
        self.assertIn("DT_OutlineN", [uv.name for uv in imported.data.uv_layers])
        self.assertEqual([k.name for k in imported.data.shape_keys.key_blocks], ["Basis", "Smile"])


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 3: Chạy test với bản build hiện tại**

Run: `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_platform_test.py`
Expected: PASS cả 2 test. Nếu `test_set_material_outside_slots_renders` FAIL thì dừng thiết kế mục 4.3: chuyển sang phương án dự phòng (object outline riêng), ghi vào báo cáo, rồi sửa Task 7 cho phù hợp.

- [ ] **Step 4: Viết `tests/python/dasktoon_make_legacy_fixtures.py`.** Script này phải chạy bằng bản build **cũ**, tức là trước mọi lần build và trước mọi lần đồng bộ script.

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Create legacy .blend fixtures with the PRE-CHANGE DaskToon build (run once, then commit the files).

DaskToon.exe --background --factory-startup --python tests/python/dasktoon_make_legacy_fixtures.py
"""

import os

import bpy

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dasktoon_data")


def _node(mat, idname):
    return next(n for n in mat.node_tree.nodes if n.bl_idname == idname)


def nodes_fixture():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for idname in ('ShaderNodeAnimeCharacter', 'ShaderNodeAnimeCel', 'ShaderNodeDaskCel'):
        mat = bpy.data.materials.new("Legacy_" + idname[len("ShaderNode"):])
        mat.use_fake_user = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        node = nt.nodes.new(idname)
        nt.links.new(node.outputs[0], out.inputs["Surface"])
    bsdf = _node(bpy.data.materials["Legacy_AnimeCharacter"], 'ShaderNodeAnimeCharacter')
    bsdf.use_ambient = True
    bsdf.use_rim = True
    bsdf.ambient_mode = 'HUE'
    bsdf.outline_tint_mode = 'LIGHT_REACTIVE'
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "dasktoon_legacy_nodes.blend"), compress=True)


def outline_fixture():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.mesh.primitive_uv_sphere_add()
    hero = bpy.context.active_object
    hero.name = "Hero"
    mat = bpy.data.materials.new("Skin")
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    node = nt.nodes.new('ShaderNodeAnimeCharacter')
    node.use_outline = True
    node.inputs["Outline Width"].default_value = 0.004
    node.inputs["Outline Color"].default_value = (0.3, 0.1, 0.05, 1.0)
    nt.links.new(node.outputs[0], out.inputs["Surface"])
    hero.data.materials.append(mat)
    bpy.context.view_layer.update()  # legacy handler: Solidify + Hero_DaskOutline slot
    for i in range(20):
        dup = hero.copy()  # linked duplicate: shares the mesh (bug #3 slot explosion)
        dup.name = "HeroDup%02d" % i
        scene.collection.objects.link(dup)
    bpy.context.view_layer.update()
    print("legacy slots:", len(hero.data.materials), "modifiers:", [m.name for m in hero.modifiers])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "dasktoon_legacy_outline.blend"), compress=True)


os.makedirs(OUT, exist_ok=True)
nodes_fixture()
outline_fixture()
```

- [ ] **Step 5: Sinh fixture rồi kiểm tra.** Kỳ vọng in ra khoảng `legacy slots: 22`, kèm modifier `DaskToon_Outline`.

Run: `"$DT" --background --factory-startup --python tests/python/dasktoon_make_legacy_fixtures.py 2>&1 | grep "legacy slots"`

- [ ] **Step 6: Commit**

```bash
git add tests/python/dasktoon_test_utils.py tests/python/dasktoon_platform_test.py tests/python/dasktoon_make_legacy_fixtures.py tests/python/dasktoon_data/*.blend
git commit -m "test: add DaskToon test helpers, platform checks and legacy fixtures"
```

---

### Task 2: Sửa weight trong Mix Shader (8 node) và Alpha của Anime BSDF, kèm build đầu tiên

**Files:**
- Modify: `source/blender/gpu/shaders/material/gpu_shader_material_{anime_character,artist_line_modulation,dask_ambient,dask_ao,dask_cel,dask_grade,dask_light,dask_outline}.glsl` (dòng `float w = ...`)
- Modify: `source/blender/gpu/shaders/material/gpu_shader_material_anime_character.glsl` (phần 9)
- Create: `tests/python/dasktoon_shading_test.py`

**Interfaces:** Consumes `tu` từ Task 1. Không tạo ra API mới.

- [ ] **Step 1: Viết test lỗi**

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import math
import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

WEIGHT_NODES = (
    'ShaderNodeAnimeCharacter', 'ShaderNodeArtistLineModulation', 'ShaderNodeDaskAmbient',
    'ShaderNodeDaskAO', 'ShaderNodeDaskCel', 'ShaderNodeDaskGrade', 'ShaderNodeDaskLight',
    'ShaderNodeDaskOutline',
)


class MixShaderWeightTest(unittest.TestCase):
    def test_factor_one_hides_dasktoon_node(self):
        for node_type in WEIGHT_NODES:
            with self.subTest(node=node_type):
                tu.reset_scene()
                plane = tu.add_plane()
                tu.add_sun(3.0)
                tu.set_world_color((0.2, 0.2, 0.2))
                alone_mat, _node = tu.node_material("Alone", node_type)
                tu.assign(plane, alone_mat)
                alone = tu.render_center("weight_alone_" + node_type)
                self.assertGreater(max(alone[:3]), 0.02, "renders black on its own; weight cannot be judged")
                mixed_mat, _node = tu.mix_with_black_material("Mixed", node_type)
                tu.assign(plane, mixed_mat)
                mixed = tu.render_center("weight_mixed_" + node_type)
                self.assertLess(max(mixed[:3]), 0.01)


class AnimeBsdfAlphaTest(unittest.TestCase):
    def test_alpha_controls_transparency(self):
        tu.reset_scene()
        bpy.context.scene.render.film_transparent = True
        plane = tu.add_plane()
        tu.add_sun(3.0)
        mat, node = tu.node_material("Alpha", 'ShaderNodeAnimeCharacter')
        mat.surface_render_method = 'BLENDED'
        tu.assign(plane, mat)
        node.inputs["Alpha"].default_value = 0.0
        self.assertLess(tu.render_center("alpha_0")[3], 0.01)
        node.inputs["Alpha"].default_value = 1.0
        self.assertGreater(tu.render_center("alpha_1")[3], 0.99)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy với bản build cũ để xác nhận test FAIL**

Run: `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_shading_test.py`
Expected: FAIL. `MixShaderWeightTest` fail ở ít nhất AnimeCharacter và DaskCel; `AnimeBsdfAlphaTest` fail ở `alpha_0`. Nếu có node render ra đen khi đứng riêng thì ghi vào báo cáo và chỉnh input của node đó trong test (ví dụ bật module) để nó có màu.

- [ ] **Step 3: Sửa lỗi weight bằng một lệnh thay thế, sau đó kiểm tra còn đúng 0 chỗ cũ**

```bash
cd source/blender/gpu/shaders/material
for f in anime_character artist_line_modulation dask_ambient dask_ao dask_cel dask_grade dask_light dask_outline; do
  sed -i 's/float w = (weight > 0\.0001f) ? weight : 1\.0f;/float w = weight;/' gpu_shader_material_$f.glsl
done
grep -c "weight > 0.0001f" gpu_shader_material_*.glsl | grep -v ":0" ; cd -
```
Expected: không in ra dòng nào.

- [ ] **Step 4: Sửa Alpha.** Trong `gpu_shader_material_anime_character.glsl`, thay khối cuối của phần 9 (từ `float w = weight;` tới `result = closure_eval(emission_data);`) bằng:

```glsl
  float a = clamp(alpha, 0.0f, 1.0f);
  ClosureTransparency transparency_data;
  transparency_data.weight = weight * (1.0f - a);
  transparency_data.transmittance = float3(1.0f);
  transparency_data.holdout = 0.0f;
  ClosureEmission emission_data;
  emission_data.weight = weight * a;
  emission_data.emission = surface_color;
  result = closure_add(closure_eval(transparency_data), closure_eval(emission_data));
```

- [ ] **Step 5: Build** (chạy nền, đo thời gian, ghi số phút vào báo cáo)

Run: lệnh build ở mục "Môi trường".
Expected: `0 Error(s)`. Có thể có cảnh báo.

- [ ] **Step 6: Chạy lại test**

Run: `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_shading_test.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add source/blender/gpu/shaders/material/*.glsl tests/python/dasktoon_shading_test.py
git commit -m "fix: respect Mix Shader weight in DaskToon nodes and make Anime BSDF alpha transparent"
```

---

### Task 3: Lõi đổ bóng GLSL dùng chung và refactor chế độ Đơn giản (không đổi look)

**Files:**
- Create: `source/blender/gpu/shaders/material/gpu_shader_material_dasktoon_shading.glsl`
- Modify: `source/blender/gpu/CMakeLists.txt` (thêm file vào danh sách, cạnh `gpu_shader_material_anime_character.glsl`)
- Modify: `gpu_shader_material_anime_character.glsl`, `gpu_shader_material_dask_cel.glsl`
- Create: `tests/python/dasktoon_shading_baseline.py`, `tests/python/dasktoon_data/shading_baseline.json`

**Interfaces:**
- Produces (GLSL, dùng ở Task 4 và 5):
  - `float3 dt_rgb_to_hsv(float3)`, `float3 dt_hsv_to_rgb(float3)`, `float dt_luminance(float3)`
  - `float3 dt_overlay(float3 a, float3 b)`, `float3 dt_light_norm(float3 light_col)`
  - `float3 dt_shade_simple(float light, float3 base, float3 shadow, float thresh, float softness, float &cel)`
  - `float3 dt_ramp_color(sampler1DArray ramp, float layer, float is_constant, float t)`
  - `float3 dt_shade_ramp(float light, float3 base, float thresh, sampler1DArray ramp, float layer, float is_constant, float &cel)`
  - `float3 dt_ambient_mode(float3 a, float3 b, int mode)`
  - `float3 dt_light_mode(float3 c, float3 light_col, float3 light_norm, float strength, int mode)`

- [ ] **Step 1: Viết script baseline**

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Simple mode must keep today's look (spec 3.2).

Capture BEFORE the refactor:  DaskToon.exe -b --factory-startup --python dasktoon_shading_baseline.py -- --capture
Check (normal test run):      same command without --capture.
"""

import json
import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

BASELINE = os.path.join(tu.DATA_DIR, "shading_baseline.json")
GRID = 5


def cases():
    result = []
    for node in ('ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel'):
        for sun in (0.4, 1.0, 1.6, 3.0):
            for thr in (0.3, 0.46, 0.7):
                result.append({"node": node, "sun": sun, "thr": thr, "soft": 0.035})
        result.append({"node": node, "sun": 1.0, "thr": 0.46, "soft": 0.3})
    for mode in ('OVERLAY', 'HUE', 'HUE_SAT', 'SAT', 'VAL', 'MULTIPLY', 'MIX'):
        result.append({"node": 'ShaderNodeAnimeCharacter', "sun": 1.0, "thr": 0.46, "soft": 0.035,
                       "use_ambient": True, "ambient_mode": mode, "world": [0.2, 0.3, 0.6]})
    result.append({"node": 'ShaderNodeAnimeCharacter', "sun": 2.0, "thr": 0.46, "soft": 0.035,
                   "use_light": True, "sun_color": [1.0, 0.6, 0.4]})
    result.append({"node": 'ShaderNodeAnimeCharacter', "sun": 1.5, "thr": 0.46, "soft": 0.035, "use_rim": True})
    result.append({"node": 'ShaderNodeAnimeCharacter', "sun": 1.5, "thr": 0.46, "soft": 0.035, "use_grade": True})
    result.append({"node": 'ShaderNodeDaskCel', "sun": 1.5, "thr": 0.46, "soft": 0.035, "use_outline": True})
    return result


def case_key(case):
    return json.dumps(case, sort_keys=True)


def render_case(case):
    tu.reset_scene()
    tu.set_world_color(case.get("world", (0.0, 0.0, 0.0)))
    tu.add_sun(case["sun"], rotation=(0.6, 0.3, 0.0), color=case.get("sun_color", (1.0, 1.0, 1.0)))
    obj = tu.add_sphere()
    mat, node = tu.node_material("Case", case["node"])
    tu.assign(obj, mat)
    node.inputs["Shadow Threshold"].default_value = case["thr"]
    node.inputs["Shadow Softness"].default_value = case["soft"]
    for flag in ("use_ambient", "use_light", "use_rim", "use_grade"):
        if case.get(flag):
            setattr(node, flag, True)
    if "ambient_mode" in case:
        node.ambient_mode = case["ambient_mode"]
        node.inputs["Use Custom Color"].default_value = False
    if "Use Outline" in node.inputs:
        node.inputs["Use Outline"].default_value = bool(case.get("use_outline"))
        node.inputs["Outline Width"].default_value = 0.004
    bpy.app.handlers.depsgraph_update_post.clear()  # isolate shading from any outline handler
    pixels, (w, h) = tu.render_pixels("baseline")
    samples = []
    for gy in range(GRID):
        for gx in range(GRID):
            x = int((gx + 0.5) * w / GRID)
            y = int((gy + 0.5) * h / GRID)
            i = (y * w + x) * 4
            samples.extend(round(v, 6) for v in pixels[i:i + 3])
    return samples


class SimpleModeBaseline(unittest.TestCase):
    def test_simple_mode_matches_baseline(self):
        with open(BASELINE, encoding="utf-8") as f:
            stored = json.load(f)
        for case in cases():
            with self.subTest(case=case_key(case)):
                got = render_case(case)
                want = stored[case_key(case)]
                worst = max(abs(a - b) for a, b in zip(got, want))
                self.assertLess(worst, 1e-3)


def capture():
    data = {case_key(case): render_case(case) for case in cases()}
    os.makedirs(tu.DATA_DIR, exist_ok=True)
    with open(BASELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=0, sort_keys=True)
    print("captured", len(data), "cases into", BASELINE)


if __name__ == "__main__":
    if "--capture" in sys.argv:
        capture()
    else:
        tu.run_tests()
```

- [ ] **Step 2: Chụp baseline** bằng bản build của Task 2, trước khi sửa GLSL.

Run: `"$DT" --background --factory-startup --python tests/python/dasktoon_shading_baseline.py -- --capture 2>&1 | grep captured`
Expected: `captured 40 cases ...`

- [ ] **Step 3: Kiểm tra baseline tự khớp với chính nó** (để biết render có ổn định giữa các lần chạy)

Run: `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_shading_baseline.py`
Expected: PASS. Nếu FAIL thì render không ổn định. Khi đó nâng sai số lên 2e-3 và ghi vào báo cáo.

- [ ] **Step 4: Tạo file lõi GLSL `gpu_shader_material_dasktoon_shading.glsl`**

```glsl
/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/* Shared DaskToon stylized shading core used by Anime BSDF, Anime Cel and Dask Cel.
 * Design: docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md (3.2, 3.3, 3.10). */

#include "gpu_shader_common_color_ramp.glsl"

float3 dt_rgb_to_hsv(float3 c)
{
  float4 K = float4(0.0f, -1.0f / 3.0f, 2.0f / 3.0f, -1.0f);
  float4 p = mix(float4(c.bg, K.wz), float4(c.gb, K.xy), step(c.b, c.g));
  float4 q = mix(float4(p.xyw, c.r), float4(c.r, p.yzx), step(p.x, c.r));
  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10f;
  return float3(abs(q.z + (q.w - q.y) / (6.0f * d + e)), d / (q.x + e), q.x);
}

float3 dt_hsv_to_rgb(float3 c)
{
  float4 K = float4(1.0f, 2.0f / 3.0f, 1.0f / 3.0f, 3.0f);
  float3 p = abs(fract(c.xxx + K.xyz) * 6.0f - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0f, 1.0f), c.y);
}

/* Rec.709 luminance, identical to Blender's default OCIO luminance coefficients. */
float dt_luminance(float3 c)
{
  return dot(c, float3(0.2126f, 0.7152f, 0.0722f));
}

float3 dt_overlay(float3 a, float3 b)
{
  return mix(2.0f * a * b, 1.0f - 2.0f * (1.0f - a) * (1.0f - b), step(float3(0.5f), a));
}

float3 dt_light_norm(float3 light_col)
{
  float l_max = max(max(light_col.r, light_col.g), light_col.b);
  return (l_max > 0.001f) ? (light_col / l_max) : float3(1.0f);
}

float3 dt_shade_simple(
    float light, float3 base, float3 shadow, float thresh, float softness, float &cel)
{
  float s_soft = max(softness, 0.001f);
  float s_min = clamp(thresh - s_soft * 0.5f, 0.0f, 1.0f);
  float s_max = clamp(thresh + s_soft * 0.5f, s_min + 0.0001f, 1.0f);
  cel = smoothstep(s_min, s_max, light);
  float3 auto_shadow = base * shadow * 1.25f;
  float3 final_shadow = (length(shadow) > 0.001f) ? mix(shadow, auto_shadow, 0.75f) : base * 0.5f;
  return mix(final_shadow, base, cel);
}

float3 dt_ramp_color(sampler1DArray ramp, float layer, float is_constant, float t)
{
  float4 col;
  float alpha;
  if (is_constant > 0.5f) {
    valtorgb_nearest(t, ramp, layer, col, alpha);
  }
  else {
    valtorgb(t, ramp, layer, col, alpha);
  }
  return col.rgb;
}

float3 dt_shade_ramp(float light,
                     float3 base,
                     float thresh,
                     sampler1DArray ramp,
                     float layer,
                     float is_constant,
                     float &cel)
{
  float t = clamp(light + 0.5f - thresh, 0.0f, 1.0f);
  float3 tint = dt_ramp_color(ramp, layer, is_constant, t);
  float lum_dark = dt_luminance(dt_ramp_color(ramp, layer, is_constant, 0.0f));
  float lum_lit = dt_luminance(dt_ramp_color(ramp, layer, is_constant, 1.0f));
  cel = clamp((dt_luminance(tint) - lum_dark) / max(lum_lit - lum_dark, 0.0001f), 0.0f, 1.0f);
  return base * tint;
}

/* Ambient Mode (spec 3.10): 0 OVERLAY, 1 HUE, 2 HUE_SAT, 3 SAT, 4 VAL, 5 MULTIPLY, 6 MIX. */
float3 dt_ambient_mode(float3 a, float3 b, int mode)
{
  if (mode == 0) {
    return dt_overlay(a, b);
  }
  if (mode == 5) {
    return a * b;
  }
  if (mode < 1 || mode > 4) {
    return b;
  }
  float3 ha = dt_rgb_to_hsv(a);
  float3 hb = dt_rgb_to_hsv(b);
  if (mode == 1) {
    ha.x = hb.x;
  }
  else if (mode == 2) {
    ha.x = hb.x;
    ha.y = mix(ha.y, hb.y, 0.65f);
  }
  else if (mode == 3) {
    ha.y = hb.y;
  }
  else {
    ha.z = hb.z;
  }
  return dt_hsv_to_rgb(ha);
}

/* Light Mode (spec 3.10): 0 OVERLAY, 1 HUE, 2 MULTIPLY, 3 ADD, 4 PURE_CEL. */
float3 dt_light_mode(float3 c, float3 light_col, float3 light_norm, float strength, int mode)
{
  float s = clamp(strength, 0.0f, 2.0f);
  float3 ls = mix(float3(1.0f), light_norm, s);
  if (mode == 0) {
    return dt_overlay(c, ls);
  }
  if (mode == 1) {
    float3 hc = dt_rgb_to_hsv(c);
    float3 hl = dt_rgb_to_hsv(light_norm);
    float3 tinted = dt_hsv_to_rgb(float3(hl.x, hc.y, hc.z));
    return mix(c, tinted, clamp(s, 0.0f, 1.0f) * hl.y);
  }
  if (mode == 2) {
    return c * ls;
  }
  if (mode == 3) {
    return c + (light_col - min(min(light_col.r, light_col.g), light_col.b)) * s;
  }
  return c;
}
```

- [ ] **Step 5: Đăng ký file trong `source/blender/gpu/CMakeLists.txt`.** Thêm dòng sau ngay dưới `  shaders/material/gpu_shader_material_anime_character.glsl`:

```cmake
  shaders/material/gpu_shader_material_dasktoon_shading.glsl
```

- [ ] **Step 6: Refactor `gpu_shader_material_anime_character.glsl`**
  1. Thêm `#include "gpu_shader_material_dasktoon_shading.glsl"` dưới các include sẵn có. Xóa hai hàm `dasktoon_master_rgb_to_hsv/hsv_to_rgb` và đổi mọi chỗ gọi sang `dt_rgb_to_hsv/dt_hsv_to_rgb`.
  2. Phần 2: thay từ `float s_soft = ...` tới `float3 surface_color = mix(final_shadow, base_color.rgb, cel_factor);` bằng:
     ```glsl
     float cel_factor;
     float3 surface_color = dt_shade_simple(
         light_intensity, base_color.rgb, shadow_color.rgb, shadow_thresh, shadow_softness, cel_factor);
     ```
  3. Phần 3: thay chuỗi `if (a_mode == 0) ... else { ... }` bằng `amb_shaded = dt_ambient_mode(amb_shaded, amb_color, a_mode);`
  4. Phần 4: thay khối tính `l_norm` và overlay bằng:
     ```glsl
     float3 lit_shaded = dt_light_mode(surface_color, light_col, dt_light_norm(light_col), light_tint_strength, 0);
     ```
     Đồng thời xóa các biến không còn dùng (`l_strength`, `l_max`, `l_norm`, `a`, `b`).

- [ ] **Step 7: Refactor `gpu_shader_material_dask_cel.glsl`.** Thêm include. Xóa hai hàm `dask_cel_rgb_to_hsv/hsv_to_rgb` và đổi chỗ gọi sang `dt_*`. Thay phần 2–3 (từ `float s_soft` tới `float3 surface_color = mix(...)`) bằng:

```glsl
  float cel_factor;
  float3 surface_color = dt_shade_simple(
      light_intensity, base_color.rgb, shadow_color.rgb, shadow_thresh, shadow_softness, cel_factor);
```

- [ ] **Step 8: Build, rồi chạy baseline và test của Task 2**

Run: lệnh build, sau đó:
`"$DT" -b --factory-startup --python-exit-code 1 --python tests/python/dasktoon_shading_baseline.py && "$DT" -b --factory-startup --python-exit-code 1 --python tests/python/dasktoon_shading_test.py`
Expected: PASS cả hai.

- [ ] **Step 9: Commit**

```bash
git add source/blender/gpu/CMakeLists.txt source/blender/gpu/shaders/material/gpu_shader_material_dasktoon_shading.glsl source/blender/gpu/shaders/material/gpu_shader_material_anime_character.glsl source/blender/gpu/shaders/material/gpu_shader_material_dask_cel.glsl tests/python/dasktoon_shading_baseline.py tests/python/dasktoon_data/shading_baseline.json
git commit -m "refactor: share DaskToon shading core between Anime BSDF and Dask Cel"
```

---

### Task 4: Storage dải màu, RNA, giao diện và GPU (Anime BSDF và Dask Cel), cộng Light Mode cho Anime BSDF

**Files:**
- Create: `source/blender/nodes/NOD_dasktoon_shading.hh`
- Create: `source/blender/nodes/shader/node_shader_dasktoon_shading.hh`, `source/blender/nodes/shader/node_shader_dasktoon_shading.cc`
- Modify: `source/blender/nodes/shader/CMakeLists.txt` (thêm `node_shader_dasktoon_shading.cc` và `.hh` vào SRC), `source/blender/nodes/CMakeLists.txt` (thêm `NOD_dasktoon_shading.hh`)
- Modify: `source/blender/nodes/shader/nodes/node_shader_anime_character.cc`, `node_shader_dask_cel.cc`
- Modify: `source/blender/makesrna/intern/rna_nodetree.cc`
- Modify: `gpu_shader_material_anime_character.glsl`, `gpu_shader_material_dask_cel.glsl`
- Test: thêm vào `tests/python/dasktoon_shading_test.py`

**Interfaces:**
- Produces (C++, namespace `blender::nodes::dasktoon`):
  - `int shading_ramp_mode_bit(int node_type_legacy)`: trả −1 nếu node không thuộc 3 node trên
  - `bool shading_is_ramp_mode(const bNode &)`, `void shading_set_ramp_mode(bNode &, bool)` (tạo storage khi cần)
  - `ColorBand *shading_ramp_new()`
  - `int light_blend_mode_get(const bNode &)`, `void light_blend_mode_set(bNode &, int)`
  - `struct ShadingGPULinks { GPUNodeLink *ramp_tex; float ramp_layer; float ramp_mode; float ramp_constant; }`
  - `ShadingGPULinks shading_gpu_links(GPUMaterial *, const bNode &)`
  - `void draw_shading_buttons(ui::Layout &, PointerRNA *)`
- Produces (RNA): `shading_mode` (`SIMPLE`/`RAMP`) và `shading_ramp` (ColorRamp) trên cả 3 node (Anime Cel dùng ở Task 5). `light_blend_mode` của Anime BSDF chuyển sang `custom1` bit 8–11.
- Consumes (Python, có ở Task 6): menu `NODE_MT_dasktoon_shading_styles`, operator `dasktoon.shading_style_save` và `dasktoon.shading_ramp_from_simple`. Trước Task 6 các nút này chưa có tác dụng, chuyện này chấp nhận được.

- [ ] **Step 1: Viết test lỗi** (thêm vào `dasktoon_shading_test.py`, phía trên `if __name__`)

```python
SHADING_NODES = ('ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel')


class ShadingModeTest(unittest.TestCase):
    def test_rna_and_socket_visibility(self):
        tu.reset_scene()
        for node_type in SHADING_NODES:
            with self.subTest(node=node_type):
                _mat, node = tu.node_material("M", node_type)
                self.assertEqual(node.shading_mode, 'SIMPLE')
                self.assertIsNotNone(node.shading_ramp)
                self.assertTrue(node.inputs["Shadow Color"].enabled)
                node.shading_mode = 'RAMP'
                self.assertFalse(node.inputs["Shadow Color"].enabled)
                self.assertFalse(node.inputs["Shadow Softness"].enabled)
                self.assertTrue(node.inputs["Shadow Threshold"].enabled)

    def test_ramp_mode_is_base_times_ramp(self):
        for node_type in SHADING_NODES:
            with self.subTest(node=node_type):
                tu.reset_scene()
                plane = tu.add_plane()
                sun = tu.add_sun(0.3 * math.pi)  # light = 0.3 at the plane centre (world is black)
                mat, node = tu.node_material("R", node_type)
                tu.assign(plane, mat)
                node.shading_mode = 'RAMP'
                ramp = node.shading_ramp
                ramp.interpolation = 'CONSTANT'
                ramp.elements[0].position = 0.0
                ramp.elements[0].color = (0.5, 0.25, 0.25, 1.0)
                ramp.elements[1].position = 0.5
                ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
                node.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
                node.inputs["Shadow Threshold"].default_value = 0.5
                dark = tu.render_center("ramp_dark_" + node_type)  # t = 0.3 -> first stop
                self.assertAlmostEqual(dark[0], 0.5, delta=0.01)
                self.assertAlmostEqual(dark[1], 0.25, delta=0.01)
                sun.data.energy = 0.8 * math.pi  # t = 0.8 -> white
                lit = tu.render_center("ramp_lit_" + node_type)
                self.assertAlmostEqual(lit[0], 1.0, delta=0.01)
                self.assertAlmostEqual(lit[1], 1.0, delta=0.01)


class LightModeTest(unittest.TestCase):
    def test_light_blend_mode_keeps_other_settings(self):
        tu.reset_scene()
        _mat, node = tu.node_material("L", 'ShaderNodeAnimeCharacter')
        node.use_ambient = True
        node.use_rim = True
        node.ambient_mode = 'HUE'
        node.outline_tint_mode = 'LIGHT_REACTIVE'
        for mode in ('HUE', 'MULTIPLY', 'ADD', 'PURE_CEL', 'OVERLAY', 'ADD'):
            node.light_blend_mode = mode
            self.assertEqual(node.light_blend_mode, mode)
            self.assertTrue(node.use_ambient)
            self.assertTrue(node.use_rim)
            self.assertFalse(node.use_light)
            self.assertEqual(node.ambient_mode, 'HUE')
            self.assertEqual(node.outline_tint_mode, 'LIGHT_REACTIVE')
        node.outline_tint_mode = 'CUSTOM'
        node.ambient_mode = 'MIX'
        self.assertEqual(node.light_blend_mode, 'ADD')

    def test_light_modes_change_color(self):
        tu.reset_scene()
        plane = tu.add_plane()
        tu.add_sun(2.0, color=(1.0, 0.4, 0.2))
        mat, node = tu.node_material("LM", 'ShaderNodeAnimeCharacter')
        tu.assign(plane, mat)
        node.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1.0)
        node.use_light = True
        results = {}
        for mode in ('OVERLAY', 'HUE', 'MULTIPLY', 'ADD', 'PURE_CEL'):
            node.light_blend_mode = mode
            results[mode] = tu.render_center("lightmode_" + mode)[:3]
        node.use_light = False
        off = tu.render_center("lightmode_off")[:3]
        for a, b in zip(results['PURE_CEL'], off):
            self.assertAlmostEqual(a, b, delta=1e-3)
        distinct = {tuple(round(c, 2) for c in rgb) for rgb in results.values()}
        self.assertEqual(len(distinct), 5)


class LegacyNodesTest(unittest.TestCase):
    def test_legacy_nodes_without_storage(self):
        bpy.ops.wm.open_mainfile(filepath=os.path.join(tu.DATA_DIR, "dasktoon_legacy_nodes.blend"))
        tu._drop_legacy_outline_handler()
        mat = bpy.data.materials["Legacy_AnimeCharacter"]
        node = next(n for n in mat.node_tree.nodes if n.bl_idname == 'ShaderNodeAnimeCharacter')
        self.assertTrue(node.use_ambient)
        self.assertTrue(node.use_rim)
        self.assertEqual(node.ambient_mode, 'HUE')
        self.assertEqual(node.outline_tint_mode, 'LIGHT_REACTIVE')
        self.assertEqual(node.light_blend_mode, 'OVERLAY')
        self.assertEqual(node.shading_mode, 'SIMPLE')
        self.assertIsNone(node.shading_ramp)
        tu.setup_render_scene()
        plane = tu.add_plane()
        tu.add_sun(2.0)
        tu.assign(plane, mat)
        simple = tu.render_center("legacy_simple")
        self.assertGreater(max(simple[:3]), 0.05)
        node.shading_mode = 'RAMP'
        self.assertIsNotNone(node.shading_ramp)
        ramp = tu.render_center("legacy_ramp")
        self.assertGreater(max(ramp[:3]), 0.05)
```

- [ ] **Step 2: Chạy để xác nhận FAIL**

Run: lệnh chạy `dasktoon_shading_test.py`
Expected: FAIL với `AttributeError: ... has no attribute 'shading_mode'`, và test giữ cờ module fail vì `use_rim` bị tắt.

- [ ] **Step 3: Tạo `source/blender/nodes/NOD_dasktoon_shading.hh`**

```cpp
/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Storage layout of the DaskToon shading core shared by Anime BSDF, Anime Cel and Dask Cel.
 * Design: docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md, section 3.5.
 */

#pragma once

struct bNode;
struct ColorBand;

namespace blender::nodes::dasktoon {

/** Bit of bNode::custom2 that selects Ramp shading, or -1 for other node types. */
int shading_ramp_mode_bit(int node_type_legacy);
bool shading_is_ramp_mode(const bNode &node);
/** Switching to Ramp creates the ColorBand storage when a legacy node has none. */
void shading_set_ramp_mode(bNode &node, bool ramp);
/** New ColorBand initialized with the "Anime 2 tông" preset. */
ColorBand *shading_ramp_new();
/** Anime BSDF: custom1 bits 8-11. Anime Cel: custom2 bits 0-3. */
int light_blend_mode_get(const bNode &node);
void light_blend_mode_set(bNode &node, int value);

}  // namespace blender::nodes::dasktoon
```

- [ ] **Step 4: Tạo `source/blender/nodes/shader/node_shader_dasktoon_shading.hh`**

```cpp
/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#pragma once

#include "NOD_dasktoon_shading.hh"
#include "node_shader_util.hh"

namespace blender::nodes::dasktoon {

struct ShadingGPULinks {
  GPUNodeLink *ramp_tex = nullptr;
  float ramp_layer = 0.0f;
  float ramp_mode = 0.0f;
  float ramp_constant = 0.0f;
};

/** Always returns a valid ramp texture (white when not in Ramp mode or without storage). */
ShadingGPULinks shading_gpu_links(GPUMaterial *mat, const bNode &node);
/** Simple/Ramp switch, then (Ramp only) style menu, save, convert buttons and the ramp widget. */
void draw_shading_buttons(ui::Layout &layout, PointerRNA *ptr);

}  // namespace blender::nodes::dasktoon
```

- [ ] **Step 5: Tạo `source/blender/nodes/shader/node_shader_dasktoon_shading.cc`.** Trước khi viết, kiểm tra API thật của các thứ sau và chỉnh code theo đó (ghi vào báo cáo nếu khác):
  - `grep -rn "\.op(\"\|\.menu(\"" source/blender/editors/space_node/*.cc | head` để biết tên hàm thêm operator hoặc menu của `ui::Layout`.
  - `grep -n "MEM_malloc_arrayN<" source/blender/blenlib/*.hh source/blender/*/intern/*.cc | head -3` để xem cách cấp phát mảng.
  - Thân hàm `GPU_color_band` trong `source/blender/gpu/intern/gpu_material.cc`, để biết nó có giải phóng `pixels` hay không.
  - `typedef struct CBData` trong `source/blender/makesdna/DNA_texture_types.h` (hoặc `DNA_color_types.h`), để biết thứ tự các trường.

```cpp
/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include <algorithm>

#include "MEM_guardedalloc.h"

#include "BKE_colorband.hh"
#include "BKE_node_legacy_types.hh"

#include "DNA_texture_types.h"

#include "RNA_access.hh"

#include "UI_interface_layout.hh"
#include "UI_resources.hh"

#include "node_shader_dasktoon_shading.hh"

namespace blender::nodes::dasktoon {

int shading_ramp_mode_bit(const int node_type_legacy)
{
  switch (node_type_legacy) {
    case SH_NODE_ANIME_CHARACTER:
      return 6;
    case SH_NODE_ANIME_CEL:
      return 8;
    case SH_NODE_DASK_CEL:
      return 0;
    default:
      return -1;
  }
}

bool shading_is_ramp_mode(const bNode &node)
{
  const int bit = shading_ramp_mode_bit(node.type_legacy);
  return bit >= 0 && (node.custom2 & (1 << bit)) != 0;
}

void shading_set_ramp_mode(bNode &node, const bool ramp)
{
  const int bit = shading_ramp_mode_bit(node.type_legacy);
  if (bit < 0) {
    return;
  }
  if (ramp) {
    node.custom2 = short(node.custom2 | (1 << bit));
    if (node.storage == nullptr) {
      node.storage = shading_ramp_new();
    }
  }
  else {
    node.custom2 = short(node.custom2 & ~(1 << bit));
  }
}

ColorBand *shading_ramp_new()
{
  ColorBand *coba = BKE_colorband_add(true);
  coba->tot = 2;
  coba->cur = 0;
  coba->ipotype = COLBAND_INTERP_CONSTANT;
  coba->data[0].r = 0.80f;
  coba->data[0].g = 0.62f;
  coba->data[0].b = 0.66f;
  coba->data[0].a = 1.0f;
  coba->data[0].pos = 0.0f;
  coba->data[1].r = 1.0f;
  coba->data[1].g = 1.0f;
  coba->data[1].b = 1.0f;
  coba->data[1].a = 1.0f;
  coba->data[1].pos = 0.5f;
  return coba;
}

int light_blend_mode_get(const bNode &node)
{
  if (node.type_legacy == SH_NODE_ANIME_CHARACTER) {
    return (node.custom1 >> 8) & 0x0F;
  }
  return node.custom2 & 0x0F;
}

void light_blend_mode_set(bNode &node, const int value)
{
  if (node.type_legacy == SH_NODE_ANIME_CHARACTER) {
    node.custom1 = short((node.custom1 & ~0x0F00) | ((value & 0x0F) << 8));
  }
  else {
    node.custom2 = short((node.custom2 & ~0x000F) | (value & 0x0F));
  }
}

ShadingGPULinks shading_gpu_links(GPUMaterial *mat, const bNode &node)
{
  ShadingGPULinks links;
  const ColorBand *coba = static_cast<const ColorBand *>(node.storage);
  const bool ramp = shading_is_ramp_mode(node) && coba != nullptr;
  float *array = nullptr;
  int size = 0;
  if (ramp) {
    BKE_colorband_evaluate_table_rgba(coba, &array, &size);
    links.ramp_constant = (coba->ipotype == COLBAND_INTERP_CONSTANT) ? 1.0f : 0.0f;
  }
  else {
    size = 2;
    array = MEM_malloc_arrayN<float>(size_t(size) * 4, __func__);
    std::fill_n(array, size * 4, 1.0f);
  }
  links.ramp_tex = GPU_color_band(mat, size, array, &links.ramp_layer);
  links.ramp_mode = ramp ? 1.0f : 0.0f;
  return links;
}

void draw_shading_buttons(ui::Layout &layout, PointerRNA *ptr)
{
  layout.prop(ptr, "shading_mode", ui::ITEM_R_EXPAND, std::nullopt, ICON_NONE);
  if (RNA_enum_get(ptr, "shading_mode") != 1) {
    return;
  }
  ui::Layout &row = layout.row(true);
  row.menu("NODE_MT_dasktoon_shading_styles", IFACE_("Style"), ICON_NONE);
  row.op("DASKTOON_OT_shading_style_save", "", ICON_FILE_TICK);
  row.op("DASKTOON_OT_shading_ramp_from_simple", "", ICON_IMPORT);
  template_color_ramp(&layout, ptr, "shading_ramp", false);
}

}  // namespace blender::nodes::dasktoon
```

Nếu `GPU_color_band` **không** giải phóng `pixels` thì phải gọi `MEM_freeN(array)` sau lời gọi đó. Làm theo đúng cách `gpu_shader_valtorgb` đang làm.

- [ ] **Step 6: Đăng ký các file mới trong CMake.** Trong `source/blender/nodes/shader/CMakeLists.txt`, thêm `node_shader_dasktoon_shading.cc` vào danh sách SRC (cạnh `node_shader_util.cc`) và `node_shader_dasktoon_shading.hh` vào phần header. Trong `source/blender/nodes/CMakeLists.txt`, thêm `NOD_dasktoon_shading.hh` vào danh sách header.

- [ ] **Step 7: Sửa `node_shader_anime_character.cc`**
  - Include `"node_shader_dasktoon_shading.hh"`. Trong `node_declare`, thêm
    `auto simple_mode = [](const bNode &node) { return !dasktoon::shading_is_ramp_mode(node); };`
    rồi gắn `.available(simple_mode)` cho *Shadow Color* và *Shadow Softness*.
  - Thêm:
    ```cpp
    static void node_init(bNodeTree * /*ntree*/, bNode *node)
    {
      node->storage = dasktoon::shading_ramp_new();
    }
    ```
  - Trong `node_shader_buts_anime_character`, ngay sau `row2`:
    ```cpp
      if (RNA_boolean_get(ptr, "use_light")) {
        layout.prop(ptr, "light_blend_mode", ui::ITEM_R_SPLIT_EMPTY_NAME, "Light Mode", ICON_NONE);
      }
      dasktoon::draw_shading_buttons(layout, ptr);
    ```
  - Hàm GPU: thay `return GPU_stack_link(...)` bằng:
    ```cpp
      const dasktoon::ShadingGPULinks shading = dasktoon::shading_gpu_links(mat, *node);
      float modes2[4] = {float(dasktoon::light_blend_mode_get(*node)),
                         shading.ramp_mode,
                         shading.ramp_constant,
                         0.0f};
      return GPU_stack_link(mat,
                            node,
                            "node_anime_character",
                            in,
                            out,
                            GPU_constant(modes),
                            shading.ramp_tex,
                            GPU_constant(&shading.ramp_layer),
                            GPU_constant(modes2));
    ```
  - Trong `register_node_type_sh_anime_character`: thêm `ntype.initfunc = file_ns::node_init;` và
    `bke::node_type_storage(ntype, "ColorBand", node_free_standard_storage, node_copy_standard_storage);`
  - Tooltip (spec 3.1): thêm `.description("Light level where shadow begins. World lighting counts too: a bright World leaves fewer shadows")`
    cho *Shadow Threshold*. Làm giống vậy ở Dask Cel (Step 9) và Anime Cel (Task 5).

- [ ] **Step 8: Sửa GLSL `node_anime_character`.** Thêm các tham số sau `const float4 modes,`:
  `sampler1DArray ramp_tex, float ramp_layer, const float4 modes2,`. Sau đó:
  - Phần 2:
    ```glsl
      float cel_factor;
      float3 surface_color;
      if (modes2.y > 0.5f) {
        surface_color = dt_shade_ramp(light_intensity, base_color.rgb, shadow_thresh, ramp_tex, ramp_layer, modes2.z, cel_factor);
      }
      else {
        surface_color = dt_shade_simple(light_intensity, base_color.rgb, shadow_color.rgb, shadow_thresh, shadow_softness, cel_factor);
      }
    ```
  - Phần 4: `int(modes2.x + 0.5f)` thay cho `0` trong lời gọi `dt_light_mode`.

- [ ] **Step 9: Sửa `node_shader_dask_cel.cc` và GLSL của nó**
  - C++: include, `.available(simple_mode)` cho Shadow Color và Shadow Softness, `node_init` và storage giống Step 7, gọi `dasktoon::draw_shading_buttons(layout, ptr);` sau dòng outline mode. Hàm GPU:
    ```cpp
      const dasktoon::ShadingGPULinks shading = dasktoon::shading_gpu_links(mat, *node);
      float modes[4] = {float(node->custom1), shading.ramp_mode, shading.ramp_constant, 0.0f};
      return GPU_stack_link(mat, node, "node_dask_cel", in, out, GPU_constant(modes), shading.ramp_tex, GPU_constant(&shading.ramp_layer));
    ```
  - GLSL: thay tham số `float outline_tint_mode` bằng `const float4 modes, sampler1DArray ramp_tex, float ramp_layer`. Ở đầu thân hàm thêm `float outline_tint_mode = modes.x;`. Phần 2–3 rẽ nhánh `if (modes.y > 0.5f)` giống Step 8.

- [ ] **Step 10: Sửa `rna_nodetree.cc`**
  - Include `"NOD_dasktoon_shading.hh"`.
  - Trong phần `RNA_RUNTIME`:
    - Sửa `rna_ShaderNodeAnimeCharacter_outline_tint_mode_set` thành
      `node->custom1 = short((node->custom1 & ~0x00F0) | ((value & 0x0F) << 4));`
      (code cũ dùng `& 0x000F` nên xóa mất các bit 8–11).
    - Thêm các hàm:
    ```cpp
    static int rna_DaskToonShading_mode_get(PointerRNA *ptr)
    {
      return blender::nodes::dasktoon::shading_is_ramp_mode(*static_cast<const bNode *>(ptr->data)) ? 1 : 0;
    }
    static void rna_DaskToonShading_mode_set(PointerRNA *ptr, int value)
    {
      blender::nodes::dasktoon::shading_set_ramp_mode(*static_cast<bNode *>(ptr->data), value != 0);
    }
    static int rna_DaskToon_light_blend_mode_get(PointerRNA *ptr)
    {
      return blender::nodes::dasktoon::light_blend_mode_get(*static_cast<const bNode *>(ptr->data));
    }
    static void rna_DaskToon_light_blend_mode_set(PointerRNA *ptr, int value)
    {
      blender::nodes::dasktoon::light_blend_mode_set(*static_cast<bNode *>(ptr->data), value);
    }
    ```
  - Trong phần định nghĩa (trước `def_sh_anime_character`):
    ```cpp
    static const EnumPropertyItem rna_enum_dasktoon_shading_mode_items[] = {
        {0, "SIMPLE", 0, "Simple", "Shadow Color, Threshold and Softness sliders"},
        {1, "RAMP", 0, "Ramp", "Paint your own light-to-shadow transition with a color ramp"},
        {0, nullptr, 0, nullptr, nullptr},
    };

    static void def_dasktoon_shading(StructRNA *srna)
    {
      PropertyRNA *prop = RNA_def_property(srna, "shading_mode", PROP_ENUM, PROP_NONE);
      RNA_def_property_enum_funcs(prop, "rna_DaskToonShading_mode_get", "rna_DaskToonShading_mode_set", nullptr);
      RNA_def_property_enum_items(prop, rna_enum_dasktoon_shading_mode_items);
      RNA_def_property_ui_text(prop, "Shading", "How light turns into shadow");
      RNA_def_property_update(prop, NC_NODE | NA_EDITED, "rna_Node_socket_update");

      prop = RNA_def_property(srna, "shading_ramp", PROP_POINTER, PROP_NONE);
      RNA_def_property_pointer_sdna(prop, nullptr, "storage");
      RNA_def_property_struct_type(prop, "ColorRamp");
      RNA_def_property_ui_text(prop, "Shading Ramp", "Light-to-shadow tint, multiplied with Base Color");
      RNA_def_property_update(prop, NC_NODE | NA_EDITED, "rna_Node_update");
    }
    ```
  - Trong `def_sh_anime_character`: thay `RNA_def_property_enum_sdna(prop, nullptr, "custom2");` của `light_blend_mode` bằng
    `RNA_def_property_enum_funcs(prop, "rna_DaskToon_light_blend_mode_get", "rna_DaskToon_light_blend_mode_set", nullptr);`
    rồi gọi `def_dasktoon_shading(srna);` ở cuối hàm.
  - Trong `def_sh_dask_cel`: gọi `def_dasktoon_shading(srna);` ở cuối hàm.

- [ ] **Step 11: Build và chạy toàn bộ test về shading**

Run: build, sau đó chạy `dasktoon_shading_test.py` và `dasktoon_shading_baseline.py`.
Expected: PASS. Baseline vẫn PASS vì chế độ Đơn giản không đổi.

- [ ] **Step 12: Commit**

```bash
git add source/blender/nodes source/blender/makesrna/intern/rna_nodetree.cc source/blender/gpu/shaders/material tests/python/dasktoon_shading_test.py
git commit -m "feat: add Simple/Ramp shading modes and real light modes to Anime BSDF and Dask Cel"
```

---

### Task 5: Pipeline mới cho Anime Cel (cel, specular, Ambient Mode, Light Mode, Dải)

**Files:**
- Modify: `source/blender/nodes/shader/nodes/node_shader_anime_cel.cc`, `gpu_shader_material_anime_cel.glsl`, `source/blender/makesrna/intern/rna_nodetree.cc`
- Test: thêm `AnimeCelTest` vào `tests/python/dasktoon_shading_test.py`, và thêm `'ShaderNodeAnimeCel'` vào `SHADING_NODES`

**Interfaces:**
- Consumes: các API `dasktoon::*` của Task 4 và các hàm `dt_*` của Task 3.
- Produces (RNA): `ambient_mode` (`custom1`), `light_blend_mode` (`custom2` bit 0–3), `shading_mode` và `shading_ramp` trên `ShaderNodeAnimeCel`. Mặc định cho node mới: `HUE_SAT`, `OVERLAY`, `SIMPLE`.

- [ ] **Step 1: Viết test lỗi**

```python
class AnimeCelTest(unittest.TestCase):
    def _plane(self, sun_strength, sun_color=(1.0, 1.0, 1.0)):
        tu.reset_scene()
        plane = tu.add_plane()
        tu.add_sun(sun_strength, color=sun_color)
        mat, node = tu.node_material("Cel", 'ShaderNodeAnimeCel')
        tu.assign(plane, mat)
        node.inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1.0)
        node.inputs["Shadow Color"].default_value = (0.3, 0.2, 0.4, 1.0)
        node.inputs["Specular Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        return node

    def test_defaults(self):
        tu.reset_scene()
        _mat, node = tu.node_material("D", 'ShaderNodeAnimeCel')
        self.assertEqual(node.ambient_mode, 'HUE_SAT')
        self.assertEqual(node.light_blend_mode, 'OVERLAY')
        self.assertEqual(node.shading_mode, 'SIMPLE')

    def test_threshold_moves_boundary(self):
        node = self._plane(0.4 * math.pi)  # light = 0.4
        node.light_blend_mode = 'PURE_CEL'
        node.inputs["Shadow Threshold"].default_value = 0.3
        lit = tu.render_center("cel_lit")
        node.inputs["Shadow Threshold"].default_value = 0.5
        shade = tu.render_center("cel_shade")
        self.assertGreater(lit[0] - shade[0], 0.2)

    def test_specular_adds_color(self):
        node = self._plane(1.0)
        node.light_blend_mode = 'PURE_CEL'
        without = tu.render_center("spec_off")
        node.inputs["Specular Color"].default_value = (1.0, 0.0, 0.0, 1.0)
        node.inputs["Specular Size"].default_value = 0.5
        with_spec = tu.render_center("spec_on")
        self.assertGreater(with_spec[0] - without[0], 0.05)

    def test_ambient_modes_differ(self):
        node = self._plane(0.0)
        node.inputs["Ambient Color"].default_value = (0.2, 0.3, 0.9, 1.0)
        node.inputs["Ambient Blend"].default_value = 1.0
        colors = set()
        for mode in ('OVERLAY', 'HUE', 'HUE_SAT', 'SAT', 'VAL', 'MULTIPLY', 'MIX'):
            node.ambient_mode = mode
            colors.add(tuple(round(c, 2) for c in tu.render_center("cel_amb_" + mode)[:3]))
        self.assertGreaterEqual(len(colors), 6)

    def test_light_modes_differ(self):
        node = self._plane(2.0, sun_color=(1.0, 0.4, 0.2))
        colors = set()
        for mode in ('OVERLAY', 'HUE', 'MULTIPLY', 'ADD', 'PURE_CEL'):
            node.light_blend_mode = mode
            colors.add(tuple(round(c, 2) for c in tu.render_center("cel_light_" + mode)[:3]))
        self.assertEqual(len(colors), 5)
```

Riêng `test_ambient_modes_differ`: SAT và HUE_SAT có thể trùng màu khi Shadow Color gần xám. Vì vậy chỉ yêu cầu ≥ 6 màu khác nhau, và ghi rõ lý do này vào docstring của test.

- [ ] **Step 2: Chạy để xác nhận FAIL** (`AttributeError: ambient_mode`)

- [ ] **Step 3: Đọc `node_shader_anime_cel.cc` và xác định thứ tự socket.** Ghi chú lại chỉ số của socket *Normal*, vì code hiện tại gọi `GPU_link(... &in[10].link)` trong khi Normal có thể là chỉ số 11. Đây là lỗi, cần ghi vào báo cáo. Sau đó sửa:
  - `node_declare`: `.available(simple_mode)` cho Shadow Color và Shadow Softness.
  - Hàm init:
    ```cpp
    static void node_init(bNodeTree * /*ntree*/, bNode *node)
    {
      node->custom1 = 2; /* HUE_SAT */
      node->custom2 = 0; /* OVERLAY light mode, Simple shading */
      node->storage = dasktoon::shading_ramp_new();
    }
    ```
  - `draw_buttons`: giữ `ambient_mode` và `light_blend_mode` (lần này RNA đã có thật), rồi gọi `dasktoon::draw_shading_buttons(layout, ptr);`.
  - Hàm GPU:
    ```cpp
      int normal_index = 0;
      LISTBASE_FOREACH_INDEX (const bNodeSocket *, socket, &node->inputs, i) {
        if (STREQ(socket->identifier, "Normal")) {
          normal_index = i;
        }
      }
      if (!in[normal_index].link) {
        GPU_link(mat, "world_normals_get", &in[normal_index].link);
      }
      GPU_material_flag_set(mat, GPU_MATFLAG_DIFFUSE | GPU_MATFLAG_GLOSSY | GPU_MATFLAG_EMISSION | GPU_MATFLAG_SHADER_TO_RGBA);
      const dasktoon::ShadingGPULinks shading = dasktoon::shading_gpu_links(mat, *node);
      float modes[4] = {float(node->custom1), float(dasktoon::light_blend_mode_get(*node)), shading.ramp_mode, shading.ramp_constant};
      return GPU_stack_link(mat, node, "node_anime_cel", in, out, GPU_constant(modes), shading.ramp_tex, GPU_constant(&shading.ramp_layer));
    ```
  - Đăng ký `initfunc` và storage `"ColorBand"`.

- [ ] **Step 4: RNA.** Tạo `def_sh_anime_cel` gồm:
  - `ambient_mode`: `RNA_def_property_enum_sdna(prop, nullptr, "custom1")`. Danh sách item được chuyển `prop_ambient_mode_items` thành mảng cấp file `rna_enum_dasktoon_ambient_mode_items`, rồi dùng chung với `def_sh_anime_character`.
  - `light_blend_mode`: dùng các hàm get/set của Task 4, với items là mảng cấp file `rna_enum_dasktoon_light_mode_items`.
  - Gọi `def_dasktoon_shading(srna)`.

  Đổi `define("ShaderNode", "ShaderNodeAnimeCel");` thành `define("ShaderNode", "ShaderNodeAnimeCel", def_sh_anime_cel);`.

- [ ] **Step 5: Kiểm tra struct `ClosureReflection`** (`grep -rn "struct ClosureReflection" -A6 source/blender/draw/engines/eevee/shaders/`), rồi viết lại GLSL `node_anime_cel`:

```glsl
#include "gpu_shader_material_dasktoon_shading.glsl"
#include "gpu_shader_math_vector_safe_lib.glsl"
#include "gpu_shader_utildefines_lib.glsl"

[[node]]
void node_anime_cel(float4 base_color,
                    float4 shadow_color,
                    float shadow_thresh,
                    float shadow_softness,
                    float4 ambient_color,
                    float ambient_blend,
                    float ambient_shadow_only,
                    float light_tint_strength,
                    float4 spec_color,
                    float spec_size,
                    float spec_softness,
                    float3 N,
                    float weight,
                    const float4 modes,
                    sampler1DArray ramp_tex,
                    float ramp_layer,
                    Closure &result,
                    float4 &out_color)
{
  base_color = max(base_color, float4(0.0f));
  shadow_color = max(shadow_color, float4(0.0f));
  ambient_color = max(ambient_color, float4(0.0f));
  spec_color = max(spec_color, float4(0.0f));
  N = safe_normalize(N);
  int ambient_mode = int(modes.x + 0.5f);
  int light_mode = int(modes.y + 0.5f);

  /* Ambient (spec 3.10): tints the shadow tone, and the lit tone unless "shadow only". */
  float3 amb_rgb = ambient_color.rgb;
  float blend_fac = clamp(ambient_blend * ambient_color.a, 0.0f, 1.0f);
  float3 shadow_amb = mix(shadow_color.rgb, dt_ambient_mode(shadow_color.rgb, amb_rgb, ambient_mode), blend_fac);
  float3 lit_col = base_color.rgb;
  if (ambient_shadow_only < 0.5f) {
    lit_col = mix(lit_col, lit_col * amb_rgb, blend_fac * 0.5f);
  }

  /* Scene light (spec 3.1). */
  ClosureDiffuse diff_in;
  diff_in.weight = 1.0f;
  diff_in.color = float3(1.0f);
  diff_in.N = N;
  float3 light_col = closure_to_rgba(closure_eval(diff_in)).rgb;
  float light = max(max(light_col.r, light_col.g), light_col.b);

  /* Shading core (spec 3.2 / 3.3). */
  float cel;
  float3 color;
  if (modes.z > 0.5f) {
    color = dt_shade_ramp(light, lit_col, shadow_thresh, ramp_tex, ramp_layer, modes.w, cel);
  }
  else {
    color = dt_shade_simple(light, lit_col, shadow_amb, shadow_thresh, shadow_softness, cel);
  }

  /* Lamp colour on the lit side (spec 3.10). */
  color = mix(color, dt_light_mode(color, light_col, dt_light_norm(light_col), light_tint_strength, light_mode), cel);

  /* Toon specular (spec 3.6). */
  ClosureReflection refl;
  refl.weight = 1.0f;
  refl.color = float3(1.0f);
  refl.N = N;
  refl.roughness = 0.05f;
  float glossy = dt_luminance(closure_to_rgba(closure_eval(refl)).rgb);
  float spec = clamp((glossy - (1.0f - spec_size)) / max(spec_softness, 0.0001f), 0.0f, 1.0f);
  color += spec_color.rgb * spec;

  out_color = float4(color, base_color.a);
  ClosureEmission emission_data;
  emission_data.weight = weight;
  emission_data.emission = color;
  result = closure_eval(emission_data);
}
```

Xóa hai hàm `dasktoon_cel_rgb_to_hsv/hsv_to_rgb`. Kiểm tra thứ tự tham số khớp với thứ tự socket đọc được ở Step 3, rồi sửa nếu khác.

- [ ] **Step 6: Build và chạy test.** Mong đợi: PASS (kể cả `ShadingModeTest` với Anime Cel và baseline).
- [ ] **Step 7: Commit** `feat: give Anime Cel real cel shading, toon specular and working ambient/light modes`

---

### Task 6: Preset, style của người dùng và chuyển từ Đơn giản (Python)

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_shading_styles.py`
- Modify: `scripts/startup/bl_ui/__init__.py` (thêm `"dasktoon_shading_styles"` vào `_modules`, ngay sau `"dasktoon_anime_nodes"`)
- Create: `tests/python/dasktoon_shading_styles_test.py`

**Interfaces:**
- Produces:
  - `BUILTIN_STYLES: dict[str, dict]`, `user_styles_dir(create=False) -> str` (biến môi trường `DASKTOON_STYLES_DIR` ghi đè đường dẫn)
  - `list_user_styles() -> list[str]`, `get_style(name) -> dict | None`, `apply_style(ramp, style)`, `style_from_ramp(ramp) -> dict`
  - `save_user_style(name, ramp) -> str`, `delete_user_style(name) -> bool`, `ramp_from_simple(node)`
  - Operator: `dasktoon.shading_style_apply(name, material, node)`, `dasktoon.shading_style_save(name, overwrite, material, node)`, `dasktoon.shading_style_delete(name)`, `dasktoon.shading_ramp_from_simple(material, node)`
  - Menu: `NODE_MT_dasktoon_shading_styles`, `NODE_MT_dasktoon_shading_styles_delete`
  - Operator tìm node theo `context.node`, rồi `context.active_node`, rồi theo hai property `material` + `node` (để chạy từ script hoặc test).

- [ ] **Step 1: Viết test lỗi**

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import math
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

os.environ["DASKTOON_STYLES_DIR"] = tempfile.mkdtemp(prefix="dasktoon_styles_")
from bl_ui import dasktoon_shading_styles as styles  # noqa: E402


class StylesTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        self.mat, self.node = tu.node_material("S", 'ShaderNodeAnimeCharacter')
        self.node.shading_mode = 'RAMP'

    def test_builtin_style_applies_exactly(self):
        style = styles.BUILTIN_STYLES["Anime 3 tông"]
        styles.apply_style(self.node.shading_ramp, style)
        ramp = self.node.shading_ramp
        self.assertEqual(ramp.interpolation, 'CONSTANT')
        self.assertEqual(len(ramp.elements), 3)
        for element, (pos, col) in zip(ramp.elements, style["stops"]):
            self.assertAlmostEqual(element.position, pos, places=4)
            for a, b in zip(element.color, col):
                self.assertAlmostEqual(a, b, places=4)

    def test_save_load_delete_user_style(self):
        styles.apply_style(self.node.shading_ramp, styles.BUILTIN_STYLES["Manga"])
        path = styles.save_user_style("Style của tôi", self.node.shading_ramp)
        self.assertTrue(os.path.isfile(path))
        self.assertIn("Style của tôi", styles.list_user_styles())
        styles.apply_style(self.node.shading_ramp, styles.BUILTIN_STYLES["Anime 2 tông"])
        styles.apply_style(self.node.shading_ramp, styles.get_style("Style của tôi"))
        self.assertAlmostEqual(self.node.shading_ramp.elements[0].color[0], 0.10, places=4)
        self.assertTrue(styles.delete_user_style("Style của tôi"))
        self.assertNotIn("Style của tôi", styles.list_user_styles())

    def test_operator_by_material_and_node_name(self):
        result = bpy.ops.dasktoon.shading_style_apply(name="Manga", material=self.mat.name, node=self.node.name)
        self.assertEqual(result, {'FINISHED'})
        self.assertAlmostEqual(self.node.shading_ramp.elements[0].color[0], 0.10, places=4)

    def test_ramp_from_simple_keeps_boundary(self):
        plane = tu.add_plane()
        sun = tu.add_sun(1.0)
        tu.assign(plane, self.mat)
        node = self.node
        node.shading_mode = 'SIMPLE'
        node.inputs["Shadow Threshold"].default_value = 0.46
        node.inputs["Shadow Softness"].default_value = 0.05
        renders = {}
        for label, light in (("below", 0.36), ("above", 0.56)):
            sun.data.energy = light * math.pi
            renders[("simple", label)] = tu.render_center("simple_" + label)
        styles.ramp_from_simple(node)
        self.assertEqual(node.shading_mode, 'RAMP')
        for label, light in (("below", 0.36), ("above", 0.56)):
            sun.data.energy = light * math.pi
            renders[("ramp", label)] = tu.render_center("ramp_" + label)
        for label in ("below", "above"):
            for a, b in zip(renders[("simple", label)][:3], renders[("ramp", label)][:3]):
                self.assertAlmostEqual(a, b, delta=0.08)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy để xác nhận FAIL** (`ImportError: dasktoon_shading_styles`)

- [ ] **Step 3: Viết `scripts/startup/bl_ui/dasktoon_shading_styles.py`**

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Shading styles for the DaskToon shading ramp: built-in presets and the user's own styles.

Design: docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md, section 3.7.
"""

import json
import os
import re

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import Menu, Operator

SHADING_NODE_TYPES = {'ShaderNodeAnimeCharacter', 'ShaderNodeAnimeCel', 'ShaderNodeDaskCel'}

BUILTIN_STYLES = {
    "Anime 2 tông": {"interpolation": 'CONSTANT', "stops": [
        (0.0, (0.80, 0.62, 0.66, 1.0)), (0.5, (1.0, 1.0, 1.0, 1.0))]},
    "Anime 3 tông": {"interpolation": 'CONSTANT', "stops": [
        (0.0, (0.55, 0.42, 0.52, 1.0)), (0.3, (0.82, 0.66, 0.70, 1.0)), (0.55, (1.0, 1.0, 1.0, 1.0))]},
    "Mềm như vẽ": {"interpolation": 'EASE', "stops": [
        (0.2, (0.72, 0.58, 0.66, 1.0)), (0.7, (1.0, 1.0, 1.0, 1.0))]},
    "Da anime (viền ấm)": {"interpolation": 'CONSTANT', "stops": [
        (0.0, (0.82, 0.62, 0.64, 1.0)), (0.47, (1.0, 0.55, 0.50, 1.0)), (0.53, (1.0, 1.0, 1.0, 1.0))]},
    "Manga": {"interpolation": 'CONSTANT', "stops": [
        (0.0, (0.10, 0.10, 0.10, 1.0)), (0.5, (1.0, 1.0, 1.0, 1.0))]},
}


def user_styles_dir(create=False):
    override = os.environ.get("DASKTOON_STYLES_DIR")
    if override:
        if create:
            os.makedirs(override, exist_ok=True)
        return override
    return bpy.utils.user_resource('CONFIG', path=os.path.join("dasktoon", "shading_styles"), create=create)


def _file_name(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip() + ".json"


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_user_styles():
    folder = user_styles_dir()
    if not folder or not os.path.isdir(folder):
        return []
    names = []
    for entry in sorted(os.listdir(folder)):
        if entry.endswith(".json"):
            try:
                names.append(_read(os.path.join(folder, entry))["name"])
            except (OSError, ValueError, KeyError):
                continue
    return names


def get_style(name):
    if name in BUILTIN_STYLES:
        return BUILTIN_STYLES[name]
    path = os.path.join(user_styles_dir(), _file_name(name))
    if os.path.isfile(path):
        data = _read(path)
        return {"interpolation": data["interpolation"], "stops": [tuple(s) for s in data["stops"]]}
    return None


def apply_style(ramp, style):
    ramp.interpolation = style["interpolation"]
    elements = ramp.elements
    while len(elements) > 1:
        elements.remove(elements[-1])
    first_pos, first_color = style["stops"][0]
    elements[0].position = first_pos
    elements[0].color = first_color
    for pos, color in style["stops"][1:]:
        element = elements.new(pos)
        element.color = color


def style_from_ramp(ramp):
    return {"interpolation": ramp.interpolation,
            "stops": [(e.position, tuple(e.color)) for e in ramp.elements]}


def save_user_style(name, ramp):
    folder = user_styles_dir(create=True)
    path = os.path.join(folder, _file_name(name))
    data = {"version": 1, "name": name}
    data.update(style_from_ramp(ramp))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return path


def delete_user_style(name):
    path = os.path.join(user_styles_dir(), _file_name(name))
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def ramp_from_simple(node):
    """Approximate the Simple sliders with a ramp (spec 3.7). The boundary sits at t = 0.5."""
    def socket_rgb(name, fallback):
        socket = node.inputs[name]
        return fallback if socket.is_linked else tuple(socket.default_value)[:3]

    base = socket_rgb("Base Color", (0.8, 0.8, 0.8))
    shadow = socket_rgb("Shadow Color", (0.5, 0.5, 0.5))
    soft = max(node.inputs["Shadow Softness"].default_value, 0.001)
    if sum(c * c for c in shadow) ** 0.5 > 0.001:
        final = [s + (b * s * 1.25 - s) * 0.75 for s, b in zip(shadow, base)]
    else:
        final = [b * 0.5 for b in base]
    tint = [min(max(f / max(b, 0.01), 0.0), 1.0) for f, b in zip(final, base)]
    node.shading_mode = 'RAMP'
    apply_style(node.shading_ramp, {"interpolation": 'EASE', "stops": [
        (max(0.5 - soft * 0.5, 0.0), (tint[0], tint[1], tint[2], 1.0)),
        (min(0.5 + soft * 0.5, 1.0), (1.0, 1.0, 1.0, 1.0)),
    ]})


def _target_node(context, op):
    node = getattr(context, "node", None) or getattr(context, "active_node", None)
    if op.material and op.node:
        mat = bpy.data.materials.get(op.material)
        node = mat.node_tree.nodes.get(op.node) if mat and mat.node_tree else None
    if node is None or node.bl_idname not in SHADING_NODE_TYPES:
        return None
    return node


class _TargetProps:
    material: StringProperty(options={'SKIP_SAVE', 'HIDDEN'})
    node: StringProperty(options={'SKIP_SAVE', 'HIDDEN'})


class DASKTOON_OT_shading_style_apply(_TargetProps, Operator):
    """Apply a shading style to the node's ramp"""
    bl_idname = "dasktoon.shading_style_apply"
    bl_label = "Apply Shading Style"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty()

    def execute(self, context):
        node = _target_node(context, self)
        style = get_style(self.name)
        if node is None or style is None:
            self.report({'WARNING'}, "Không tìm thấy node hoặc style")
            return {'CANCELLED'}
        node.shading_mode = 'RAMP'
        apply_style(node.shading_ramp, style)
        return {'FINISHED'}


class DASKTOON_OT_shading_style_save(_TargetProps, Operator):
    """Save the current ramp as one of your own styles (shared by every file)"""
    bl_idname = "dasktoon.shading_style_save"
    bl_label = "Lưu style của tôi"

    name: StringProperty(name="Tên style", default="Style của tôi")
    overwrite: BoolProperty(name="Ghi đè nếu đã có", default=False)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        node = _target_node(context, self)
        if node is None or node.shading_ramp is None:
            self.report({'WARNING'}, "Hãy chọn một node DaskToon ở chế độ Dải đổ bóng")
            return {'CANCELLED'}
        name = self.name.strip()
        if not name or name in BUILTIN_STYLES:
            self.report({'ERROR'}, "Tên trống hoặc trùng preset có sẵn")
            return {'CANCELLED'}
        if name in list_user_styles() and not self.overwrite:
            self.report({'ERROR'}, "Style '%s' đã có. Tick 'Ghi đè nếu đã có' để thay" % name)
            return {'CANCELLED'}
        save_user_style(name, node.shading_ramp)
        self.report({'INFO'}, "Đã lưu style '%s'" % name)
        return {'FINISHED'}


class DASKTOON_OT_shading_style_delete(Operator):
    """Delete one of your own shading styles"""
    bl_idname = "dasktoon.shading_style_delete"
    bl_label = "Xóa style"

    name: StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if not delete_user_style(self.name):
            self.report({'WARNING'}, "Không tìm thấy style '%s'" % self.name)
            return {'CANCELLED'}
        return {'FINISHED'}


class DASKTOON_OT_shading_ramp_from_simple(_TargetProps, Operator):
    """Create a ramp that approximates the current Simple sliders"""
    bl_idname = "dasktoon.shading_ramp_from_simple"
    bl_label = "Chuyển từ Đơn giản"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        node = _target_node(context, self)
        if node is None:
            self.report({'WARNING'}, "Hãy chọn một node DaskToon")
            return {'CANCELLED'}
        ramp_from_simple(node)
        self.report({'INFO'}, "Đã tạo dải gần đúng với thanh trượt hiện tại")
        return {'FINISHED'}


class NODE_MT_dasktoon_shading_styles(Menu):
    bl_label = "Shading Style"

    def draw(self, context):
        layout = self.layout
        for name in BUILTIN_STYLES:
            layout.operator(DASKTOON_OT_shading_style_apply.bl_idname, text=name).name = name
        user = list_user_styles()
        if user:
            layout.separator()
            for name in user:
                layout.operator(DASKTOON_OT_shading_style_apply.bl_idname, text=name, icon='USER').name = name
            layout.menu("NODE_MT_dasktoon_shading_styles_delete", icon='TRASH')


class NODE_MT_dasktoon_shading_styles_delete(Menu):
    bl_label = "Xóa style"

    def draw(self, context):
        for name in list_user_styles():
            self.layout.operator(DASKTOON_OT_shading_style_delete.bl_idname, text=name).name = name


classes = (
    DASKTOON_OT_shading_style_apply,
    DASKTOON_OT_shading_style_save,
    DASKTOON_OT_shading_style_delete,
    DASKTOON_OT_shading_ramp_from_simple,
    NODE_MT_dasktoon_shading_styles,
    NODE_MT_dasktoon_shading_styles_delete,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

- [ ] **Step 4: Đăng ký module, đồng bộ script vào build rồi chạy test.** Mong đợi: PASS.
- [ ] **Step 5: Commit** `feat: add shading style presets and user styles for the shading ramp`

---

### Task 7: Dựng node group Geometry Nodes cho outline

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_outline_nodes.py`
- Create: `tests/python/dasktoon_outline_nodes_test.py`

**Interfaces:**
- Produces:
  - `SlotParams(enabled: bool, width: float, bleed: float, wobble: float, outline_material)` (dataclass frozen)
  - `ensure_core_group() -> GeometryNodeTree`
  - `build_object_group(obj, slots: list[SlotParams], sun, mask_name: str, uv_name: str) -> GeometryNodeTree`
  - `ensure_modifier(obj, tree) -> NodesModifier`, `remove_modifier(obj)`
  - Hằng: `MODIFIER_NAME`, `CORE_GROUP`, `OBJECT_GROUP_PREFIX`, `FALLBACK_LIGHT`, `WOBBLE_SCALE`

- [ ] **Step 1: Viết test lỗi**

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import math
import os
import sys
import unittest

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline_nodes as gn  # noqa: E402


def evaluated_mesh(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return obj.evaluated_get(depsgraph).to_mesh()


def hull_verts(obj, original_count):
    mesh = evaluated_mesh(obj)
    return [obj.matrix_world @ v.co for v in mesh.vertices[original_count:]]


class OutlineNodesTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        self.outline_mat = tu.emission_material("Skin.Outline", (0.1, 0.0, 0.0, 1.0))

    def _plane(self, scale=(1.0, 1.0, 1.0), cuts=0):
        obj = tu.add_plane(2.0)
        if cuts:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
            bm.to_mesh(obj.data)
            bm.free()
        obj.scale = scale
        obj.data.materials.append(tu.emission_material("Skin", (1.0, 1.0, 1.0, 1.0)))
        return obj

    def _apply(self, obj, width=0.05, bleed=0.0, wobble=0.0, sun=None, mask="", uv=""):
        slots = [gn.SlotParams(True, width, bleed, wobble, self.outline_mat)]
        gn.ensure_modifier(obj, gn.build_object_group(obj, slots, sun, mask, uv))
        bpy.context.view_layer.update()

    def test_only_enabled_slots_get_hull(self):
        obj = tu.add_sphere(segments=16, rings=8)
        obj.data.materials.append(tu.emission_material("A", (1, 1, 1, 1)))
        obj.data.materials.append(tu.emission_material("B", (1, 1, 1, 1)))
        for poly in obj.data.polygons:
            poly.material_index = 1 if poly.center.z < 0 else 0
        top = sum(1 for p in obj.data.polygons if p.material_index == 0)
        slots = [gn.SlotParams(True, 0.05, 0.0, 0.0, self.outline_mat), gn.SlotParams(False, 0.0, 0.0, 0.0, None)]
        gn.ensure_modifier(obj, gn.build_object_group(obj, slots, None, "", ""))
        bpy.context.view_layer.update()
        mesh = evaluated_mesh(obj)
        self.assertEqual(len(mesh.polygons), len(obj.data.polygons) + top)
        self.assertIn(self.outline_mat, list(mesh.materials))
        self.assertEqual(len(obj.material_slots), 2)
        self.assertEqual(obj.modifiers[-1].name, gn.MODIFIER_NAME)

    def test_offset_is_world_space_with_non_uniform_scale(self):
        obj = self._plane(scale=(1.0, 1.0, 2.0))
        count = len(obj.data.vertices)
        self._apply(obj, width=0.05)
        for co in hull_verts(obj, count):
            self.assertAlmostEqual(co.z, 0.05, delta=1e-4)

    def test_light_bleed_thins_lit_side(self):
        obj = self._plane()
        count = len(obj.data.vertices)
        sun = tu.add_sun(1.0)  # points down: plane normal faces the light
        self._apply(obj, width=0.05, bleed=1.0, sun=sun)
        self.assertAlmostEqual(hull_verts(obj, count)[0].z, 0.05 * 0.25, delta=1e-4)
        sun.rotation_euler = (math.pi, 0.0, 0.0)  # light from below: no thinning
        bpy.context.view_layer.update()
        self.assertAlmostEqual(hull_verts(obj, count)[0].z, 0.05, delta=1e-4)

    def test_wobble_varies_width_and_needs_uv(self):
        obj = self._plane(cuts=8)
        count = len(obj.data.vertices)
        self._apply(obj, width=0.05, wobble=1.0, uv=obj.data.uv_layers[0].name)
        zs = [co.z for co in hull_verts(obj, count)]
        self.assertGreater(max(zs) - min(zs), 0.002)
        self._apply(obj, width=0.05, wobble=1.0, uv="")  # no UV map: wobble off, still works
        zs = [co.z for co in hull_verts(obj, count)]
        self.assertLess(max(zs) - min(zs), 1e-5)

    def test_mask_vertex_group(self):
        obj = self._plane(cuts=2)
        count = len(obj.data.vertices)
        group = obj.vertex_groups.new(name="Outline_Weight")
        group.add([v.index for v in obj.data.vertices if v.co.x > 0.0], 1.0, 'REPLACE')
        self._apply(obj, width=0.05, mask="Outline_Weight")
        zs = hull_verts(obj, count)
        for v, co in zip(obj.data.vertices, zs):
            self.assertAlmostEqual(co.z, 0.05 if v.co.x > 0.0 else 0.0, delta=1e-4)

    def test_split_vertices_do_not_crack(self):
        tu.reset_scene()
        bpy.ops.mesh.primitive_cube_add(size=2.0)
        obj = bpy.context.active_object
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.split_edges(bm, edges=bm.edges[:])
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.materials.append(tu.emission_material("Skin", (1, 1, 1, 1)))
        count = len(obj.data.vertices)
        self.assertEqual(count, 24)
        self._apply(obj, width=0.1)
        by_position = {}
        for v, co in zip(obj.data.vertices, hull_verts(obj, count)):
            by_position.setdefault(tuple(round(c, 5) for c in v.co), []).append(co)
        for moved in by_position.values():
            for co in moved[1:]:
                self.assertLess((co - moved[0]).length, 1e-5)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy để xác nhận FAIL** (ImportError)

- [ ] **Step 3: Viết `scripts/startup/bl_ui/dasktoon_outline_nodes.py`.** Kiểm tra trước rằng `bpy.types.ObjectModifiers` có hàm `move(from_index, to_index)`. Nếu không có thì dùng `bpy.ops.object.modifier_move_to_index` trong `context.temp_override(object=obj)`.

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Geometry Nodes builders for the DaskToon outline (spec section 4.3). Builders only, no syncing."""

import math
from dataclasses import dataclass

import bpy

CORE_GROUP = "DaskToon_OutlineCore"
CORE_VERSION = 1
OBJECT_GROUP_PREFIX = "DT_Outline::"
MODIFIER_NAME = "DaskToon Outline"
WOBBLE_SCALE = 12.0
_FALLBACK = (0.5, 0.8, 0.6)
FALLBACK_LIGHT = tuple(c / math.sqrt(sum(x * x for x in _FALLBACK)) for c in _FALLBACK)


@dataclass(frozen=True)
class SlotParams:
    enabled: bool
    width: float
    bleed: float
    wobble: float
    outline_material: object  # bpy.types.Material or None


def _new_socket(tree, name, in_out, socket_type, default=None):
    socket = tree.interface.new_socket(name, in_out=in_out, socket_type=socket_type)
    if default is not None:
        socket.default_value = default
    return socket


def _feed(tree, socket, value):
    if isinstance(value, bpy.types.NodeSocket):
        tree.links.new(value, socket)
    elif value is not None:
        socket.default_value = value


def _math(tree, operation, a=None, b=None, c=None, clamp=False):
    node = tree.nodes.new('ShaderNodeMath')
    node.operation = operation
    node.use_clamp = clamp
    for socket, value in zip(node.inputs, (a, b, c)):
        _feed(tree, socket, value)
    return node.outputs[0]


def _vector_math(tree, operation, a=None, b=None, scale=None):
    node = tree.nodes.new('ShaderNodeVectorMath')
    node.operation = operation
    _feed(tree, node.inputs[0], a)
    _feed(tree, node.inputs[1], b)
    if scale is not None:
        _feed(tree, node.inputs["Scale"], scale)
    return node.outputs["Value"] if operation in {'DOT_PRODUCT', 'LENGTH', 'DISTANCE'} else node.outputs["Vector"]


def _on_domain(tree, value, domain, data_type):
    node = tree.nodes.new('GeometryNodeFieldOnDomain')
    node.domain = domain
    node.data_type = data_type
    tree.links.new(value, node.inputs["Value"])
    return node.outputs["Value"]


def ensure_core_group():
    tree = bpy.data.node_groups.get(CORE_GROUP)
    if tree is not None and tree.get("dasktoon_version") == CORE_VERSION:
        return tree
    if tree is None:
        tree = bpy.data.node_groups.new(CORE_GROUP, 'GeometryNodeTree')
    else:
        tree.nodes.clear()
        tree.interface.clear()
    tree["dasktoon_version"] = CORE_VERSION
    _new_socket(tree, "Geometry", 'INPUT', 'NodeSocketGeometry')
    _new_socket(tree, "Enabled", 'INPUT', 'NodeSocketBool', False)
    _new_socket(tree, "Width", 'INPUT', 'NodeSocketFloat', 0.0)
    _new_socket(tree, "Bleed", 'INPUT', 'NodeSocketFloat', 0.0)
    _new_socket(tree, "Wobble", 'INPUT', 'NodeSocketFloat', 0.0)
    _new_socket(tree, "Sun", 'INPUT', 'NodeSocketObject')
    _new_socket(tree, "Has Sun", 'INPUT', 'NodeSocketBool', False)
    _new_socket(tree, "Mask Name", 'INPUT', 'NodeSocketString', "")
    _new_socket(tree, "UV Name", 'INPUT', 'NodeSocketString', "")
    _new_socket(tree, "Original", 'OUTPUT', 'NodeSocketGeometry')
    _new_socket(tree, "Hull", 'OUTPUT', 'NodeSocketGeometry')

    nodes, links = tree.nodes, tree.links
    group_in, group_out = nodes.new('NodeGroupInput'), nodes.new('NodeGroupOutput')
    inp = group_in.outputs

    # Faces whose material has outline enabled are the hull source.
    separate = nodes.new('GeometryNodeSeparateGeometry')
    separate.domain = 'FACE'
    links.new(inp["Geometry"], separate.inputs["Geometry"])
    links.new(inp["Enabled"], separate.inputs["Selection"])

    # Smoothed normal: merge coincident vertices, then sample their normal back (no cracks on split seams).
    merge = nodes.new('GeometryNodeMergeByDistance')
    merge.inputs["Distance"].default_value = 1e-5
    links.new(inp["Geometry"], merge.inputs["Geometry"])
    nearest = nodes.new('GeometryNodeSampleNearest')
    nearest.domain = 'POINT'
    links.new(merge.outputs[0], nearest.inputs["Geometry"])
    links.new(nodes.new('GeometryNodeInputPosition').outputs[0], nearest.inputs["Sample Position"])
    smooth = nodes.new('GeometryNodeSampleIndex')
    smooth.data_type = 'FLOAT_VECTOR'
    smooth.domain = 'POINT'
    links.new(merge.outputs[0], smooth.inputs["Geometry"])
    links.new(nodes.new('GeometryNodeInputNormal').outputs[0], smooth.inputs["Value"])
    links.new(nearest.outputs["Index"], smooth.inputs["Index"])

    # World-space normal and direction towards the Sun.
    self_info = nodes.new('GeometryNodeObjectInfo')
    self_info.transform_space = 'ORIGINAL'
    links.new(nodes.new('GeometryNodeSelfObject').outputs[0], self_info.inputs["Object"])
    to_world = nodes.new('FunctionNodeTransformDirection')
    links.new(smooth.outputs[0], to_world.inputs["Direction"])
    links.new(self_info.outputs["Transform"], to_world.inputs["Transform"])
    normal_world = _vector_math(tree, 'NORMALIZE', to_world.outputs[0])
    sun_info = nodes.new('GeometryNodeObjectInfo')
    sun_info.transform_space = 'ORIGINAL'
    links.new(inp["Sun"], sun_info.inputs["Object"])
    sun_up = nodes.new('FunctionNodeRotateVector')
    sun_up.inputs["Vector"].default_value = (0.0, 0.0, 1.0)
    links.new(sun_info.outputs["Rotation"], sun_up.inputs["Rotation"])
    light_dir = nodes.new('GeometryNodeSwitch')
    light_dir.input_type = 'VECTOR'
    light_dir.inputs["False"].default_value = FALLBACK_LIGHT
    links.new(inp["Has Sun"], light_dir.inputs["Switch"])
    links.new(sun_up.outputs[0], light_dir.inputs["True"])

    # light_thin = 1 - clamp((hl - 0.55) / 0.45) * bleed * 0.75, with hl = dot(N, L) * 0.5 + 0.5
    n_dot_l = _vector_math(tree, 'DOT_PRODUCT', normal_world, light_dir.outputs[0])
    half_lambert = _math(tree, 'MULTIPLY_ADD', n_dot_l, 0.5, 0.5)
    lit_amount = _math(tree, 'DIVIDE', _math(tree, 'SUBTRACT', half_lambert, 0.55), 0.45, clamp=True)
    bleed = _on_domain(tree, inp["Bleed"], 'FACE', 'FLOAT')
    light_thin = _math(tree, 'SUBTRACT', 1.0, _math(tree, 'MULTIPLY', _math(tree, 'MULTIPLY', lit_amount, bleed), 0.75))

    # Wobble: f(u, v) = sin(2u) cos(3v) + 0.5 sin(6.28v), (u, v) = first UV map * WOBBLE_SCALE
    uv_attr = nodes.new('GeometryNodeInputNamedAttribute')
    uv_attr.data_type = 'FLOAT_VECTOR'
    links.new(inp["UV Name"], uv_attr.inputs["Name"])
    uv = _on_domain(tree, uv_attr.outputs["Attribute"], 'CORNER', 'FLOAT_VECTOR')
    split_uv = nodes.new('ShaderNodeSeparateXYZ')
    links.new(uv, split_uv.inputs[0])
    u = _math(tree, 'MULTIPLY', split_uv.outputs["X"], WOBBLE_SCALE)
    v = _math(tree, 'MULTIPLY', split_uv.outputs["Y"], WOBBLE_SCALE)
    f = _math(tree, 'ADD',
              _math(tree, 'MULTIPLY', _math(tree, 'SINE', _math(tree, 'MULTIPLY', u, 2.0)),
                    _math(tree, 'COSINE', _math(tree, 'MULTIPLY', v, 3.0))),
              _math(tree, 'MULTIPLY', _math(tree, 'SINE', _math(tree, 'MULTIPLY', v, 6.28)), 0.5))
    wobble = _on_domain(tree, inp["Wobble"], 'FACE', 'FLOAT')
    wobble_term = _math(tree, 'ADD', 1.0, _math(tree, 'MULTIPLY', _math(tree, 'MULTIPLY', wobble, 0.25), f))

    # Optional painted mask (vertex group); 1 when the attribute does not exist.
    mask_attr = nodes.new('GeometryNodeInputNamedAttribute')
    mask_attr.data_type = 'FLOAT'
    links.new(inp["Mask Name"], mask_attr.inputs["Name"])
    mask = nodes.new('GeometryNodeSwitch')
    mask.input_type = 'FLOAT'
    mask.inputs["False"].default_value = 1.0
    links.new(mask_attr.outputs["Exists"], mask.inputs["Switch"])
    links.new(mask_attr.outputs["Attribute"], mask.inputs["True"])

    width = _on_domain(tree, inp["Width"], 'FACE', 'FLOAT')
    width = _math(tree, 'MULTIPLY', _math(tree, 'MULTIPLY', _math(tree, 'MULTIPLY', width, light_thin), wobble_term),
                  mask.outputs[0])
    offset_world = _vector_math(tree, 'SCALE', normal_world, scale=width)
    invert = nodes.new('FunctionNodeInvertMatrix')
    links.new(self_info.outputs["Transform"], invert.inputs["Matrix"])
    to_local = nodes.new('FunctionNodeTransformDirection')
    links.new(offset_world, to_local.inputs["Direction"])
    links.new(invert.outputs["Matrix"], to_local.inputs["Transform"])
    set_position = nodes.new('GeometryNodeSetPosition')
    links.new(separate.outputs["Selection"], set_position.inputs["Geometry"])
    links.new(to_local.outputs[0], set_position.inputs["Offset"])
    flip = nodes.new('GeometryNodeFlipFaces')
    links.new(set_position.outputs[0], flip.inputs["Mesh"])

    links.new(inp["Geometry"], group_out.inputs["Original"])
    links.new(flip.outputs[0], group_out.inputs["Hull"])
    return tree


def build_object_group(obj, slots, sun, mask_name, uv_name):
    name = OBJECT_GROUP_PREFIX + obj.name
    tree = bpy.data.node_groups.get(name) or bpy.data.node_groups.new(name, 'GeometryNodeTree')
    tree.nodes.clear()
    tree.interface.clear()
    _new_socket(tree, "Geometry", 'INPUT', 'NodeSocketGeometry')
    _new_socket(tree, "Geometry", 'OUTPUT', 'NodeSocketGeometry')
    nodes, links = tree.nodes, tree.links
    group_in, group_out = nodes.new('NodeGroupInput'), nodes.new('NodeGroupOutput')
    material_index = nodes.new('GeometryNodeInputMaterialIndex').outputs[0]

    def table(data_type, values):
        switch = nodes.new('GeometryNodeIndexSwitch')
        switch.data_type = data_type
        switch.index_switch_items.clear()
        for _value in values:
            switch.index_switch_items.new()
        links.new(material_index, switch.inputs["Index"])
        for i, value in enumerate(values):
            switch.inputs[i + 1].default_value = value
        return switch.outputs[0]

    core = nodes.new('GeometryNodeGroup')
    core.node_tree = ensure_core_group()
    links.new(group_in.outputs[0], core.inputs["Geometry"])
    links.new(table('BOOLEAN', [s.enabled for s in slots]), core.inputs["Enabled"])
    links.new(table('FLOAT', [s.width for s in slots]), core.inputs["Width"])
    links.new(table('FLOAT', [s.bleed for s in slots]), core.inputs["Bleed"])
    links.new(table('FLOAT', [s.wobble for s in slots]), core.inputs["Wobble"])
    core.inputs["Sun"].default_value = sun
    core.inputs["Has Sun"].default_value = sun is not None
    core.inputs["Mask Name"].default_value = mask_name
    core.inputs["UV Name"].default_value = uv_name

    hull = core.outputs["Hull"]
    for i, slot in enumerate(slots):
        if not slot.enabled or slot.outline_material is None:
            continue
        compare = nodes.new('FunctionNodeCompare')
        compare.data_type = 'INT'
        compare.operation = 'EQUAL'
        links.new(material_index, compare.inputs["A"])
        compare.inputs["B"].default_value = i
        set_material = nodes.new('GeometryNodeSetMaterial')
        set_material.inputs["Material"].default_value = slot.outline_material
        links.new(hull, set_material.inputs["Geometry"])
        links.new(compare.outputs[0], set_material.inputs["Selection"])
        hull = set_material.outputs[0]
    join = nodes.new('GeometryNodeJoinGeometry')
    links.new(core.outputs["Original"], join.inputs[0])
    links.new(hull, join.inputs[0])
    links.new(join.outputs[0], group_out.inputs[0])
    return tree


def ensure_modifier(obj, tree):
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is None:
        modifier = obj.modifiers.new(MODIFIER_NAME, 'NODES')
    if modifier.node_group != tree:
        modifier.node_group = tree
    index = obj.modifiers.find(MODIFIER_NAME)
    last = len(obj.modifiers) - 1
    if index != last:
        obj.modifiers.move(index, last)
    return modifier


def remove_modifier(obj):
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is not None:
        obj.modifiers.remove(modifier)
    tree = bpy.data.node_groups.get(OBJECT_GROUP_PREFIX + obj.name)
    if tree is not None and tree.users == 0:
        bpy.data.node_groups.remove(tree)
```

- [ ] **Step 4: Đồng bộ script vào build, chạy test, sửa đến khi PASS.** Các chỗ dễ sai nhất là tên socket. Nếu tên socket khác code trên thì in `[s.name for s in node.inputs]` ra để đối chiếu, rồi ghi điểm khác vào báo cáo.
- [ ] **Step 5: Commit** `feat: add Geometry Nodes builders for the per-vertex DaskToon outline`

---

### Task 8: Đồng bộ outline, material `.Outline`, panel; gỡ handler cũ

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_outline.py`
- Modify: `scripts/startup/bl_ui/dasktoon_anime_nodes.py`: xóa `dasktoon_vrm_outline_auto_sync` và phần đăng ký của nó; viết lại nhánh `OUTLINE` của `DASKTOON_OT_setup_anime_preset` (return sớm, không chạy phần gán material ở cuối hàm)
- Modify: `scripts/startup/bl_ui/__init__.py`: thêm `"dasktoon_outline"` vào `_modules`
- Create: `tests/python/dasktoon_outline_sync_test.py`

**Interfaces:**
- Consumes: `dasktoon_outline_nodes` (Task 7). Hàm `_sync_outline_socket(src_socket, target_tree, target_socket, visited)` vẫn nằm trong `dasktoon_anime_nodes.py`, không xóa.
- Produces:
  - `find_source(mat) -> tuple[str, Node | None] | None`, với kind là `'ANIME_BSDF' | 'DASK_CEL' | 'MATERIAL'`
  - `outline_material_for(mat, create=True) -> Material | None`, `outline_node(outline_mat) -> Node | None`
  - `sync_material(mat)`, `sync_object(obj, scene)`, `sync_all(scene)`, `reset_cache()`
  - Hằng `MASK_NAMES`, `OUTLINE_PROP`, `OUTLINE_MAT_PROP`
  - Operator `dasktoon.outline_toggle_material`. Panel `MATERIAL_PT_dasktoon_outline`.

- [ ] **Step 1: Viết test lỗi** (gồm Review Focus 1, 2, 5)

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import time
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from bl_ui import dasktoon_outline_nodes as gn  # noqa: E402


def update():
    bpy.context.view_layer.update()


class OutlineSyncTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()
        self.obj = tu.add_sphere(segments=16, rings=8)
        self.mat, self.node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        tu.assign(self.obj, self.mat)
        update()

    def test_enable_creates_modifier_and_outline_material(self):
        self.assertIsNone(self.obj.modifiers.get(gn.MODIFIER_NAME))
        self.node.use_outline = True
        update()
        self.assertIsNotNone(self.obj.modifiers.get(gn.MODIFIER_NAME))
        companion = outline.outline_material_for(self.mat, create=False)
        self.assertEqual(companion.name, "Skin.Outline")
        self.assertEqual(len(self.obj.material_slots), 1)
        self.node.use_outline = False
        update()
        self.assertIsNone(self.obj.modifiers.get(gn.MODIFIER_NAME))
        self.assertIsNotNone(bpy.data.materials.get("Skin.Outline"))

    def test_reroute_between_node_and_output(self):
        nt = self.mat.node_tree
        output = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
        reroute = nt.nodes.new('NodeReroute')
        nt.links.new(self.node.outputs[0], reroute.inputs[0])
        nt.links.new(reroute.outputs[0], output.inputs["Surface"])
        self.node.use_outline = True
        update()
        self.assertIsNotNone(self.obj.modifiers.get(gn.MODIFIER_NAME))

    def test_rename_does_not_duplicate_outline_material(self):
        self.node.use_outline = True
        update()
        self.mat.name = "Face"
        self.obj.name = "Hero"
        self.node.inputs["Outline Width"].default_value = 0.01
        update()
        companions = [m for m in bpy.data.materials if m.name.endswith(".Outline")]
        self.assertEqual(len(companions), 1)
        self.assertIsNotNone(self.obj.modifiers.get(gn.MODIFIER_NAME))

    def test_empty_slots_and_non_mesh_objects(self):
        self.obj.data.materials.append(None)
        bpy.ops.object.empty_add()
        bpy.ops.mesh.primitive_cube_add()  # no material at all
        self.node.use_outline = True
        update()
        outline.sync_all(bpy.context.scene)
        self.assertIsNotNone(self.obj.modifiers.get(gn.MODIFIER_NAME))

    def test_linked_duplicates_keep_slot_count(self):
        self.node.use_outline = True
        update()
        for i in range(200):
            dup = self.obj.copy()
            bpy.context.scene.collection.objects.link(dup)
        update()
        self.assertEqual(len(self.obj.data.materials), 1)

    def test_transform_only_update_is_cheap_and_writes_nothing(self):
        self.node.use_outline = True
        update()
        calls = []
        original = gn.build_object_group
        gn.build_object_group = lambda *a, **k: calls.append(1) or original(*a, **k)
        try:
            start = time.perf_counter()
            self.obj.location.x += 1.0
            update()
            elapsed = time.perf_counter() - start
        finally:
            gn.build_object_group = original
        self.assertEqual(calls, [])
        self.assertLess(elapsed, 0.05)

    def test_mesh_data_untouched(self):
        before = [tuple(v.co) for v in self.obj.data.vertices]
        self.node.use_outline = True
        update()
        self.assertEqual(before, [tuple(v.co) for v in self.obj.data.vertices])
        self.assertEqual(len(self.obj.data.materials), 1)

    def test_material_without_main_node_uses_checkbox(self):
        plain = tu.emission_material("Plain", (1, 1, 1, 1))
        tu.assign(self.obj, plain)
        plain[outline.OUTLINE_PROP] = True
        update()
        self.assertIsNotNone(self.obj.modifiers.get(gn.MODIFIER_NAME))

    def test_quick_controls_reach_outline_material(self):
        self.node.use_outline = True
        self.node.outline_tint_mode = 'HARMONIC_KYOTO'
        self.node.inputs["Outline Color"].default_value = (0.2, 0.1, 0.05, 1.0)
        update()
        companion = outline.outline_material_for(self.mat, create=False)
        dask = outline.outline_node(companion)
        self.assertEqual(dask.bl_rna.properties["tint_mode"].enum_items[dask.tint_mode].value, 1)
        self.assertAlmostEqual(dask.inputs["Outline Color"].default_value[0], 0.2, places=4)

    def test_outline_preset_operator(self):
        bpy.context.view_layer.objects.active = self.obj
        result = bpy.ops.dasktoon.setup_anime_preset(preset_type='OUTLINE')
        self.assertEqual(result, {'FINISHED'})
        update()
        self.assertTrue(self.node.use_outline)
        self.assertFalse(any(m.type == 'SOLIDIFY' for m in self.obj.modifiers))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy để xác nhận FAIL** (ImportError)

- [ ] **Step 3: Viết `scripts/startup/bl_ui/dasktoon_outline.py`**

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon outline: per-material sources, companion `.Outline` materials and the sync handler (spec 4)."""

import bpy
from bpy.app.handlers import persistent
from bpy.types import Operator, Panel

from . import dasktoon_outline_nodes as gn

OUTLINE_PROP = "dasktoon_outline"
OUTLINE_MAT_PROP = "dasktoon_outline_material"
MASK_NAMES = ("Outline_Weight", "outline_weight", "DaskOutline_Mask", "Outline_Mask", "Outline_Width", "outline_mask")

_signatures = {}
_busy = False


def reset_cache():
    _signatures.clear()


def find_source(mat):
    """Companion `.Outline` materials never contain a source node, so they return None."""
    if mat is None or mat.node_tree is None:
        return None
    for node in mat.node_tree.nodes:
        if node.bl_idname == 'ShaderNodeAnimeCharacter' and node.use_outline:
            return ('ANIME_BSDF', node)
        if node.bl_idname == 'ShaderNodeDaskCel' and node.inputs["Use Outline"].default_value:
            return ('DASK_CEL', node)
    if mat.get(OUTLINE_PROP):
        return ('MATERIAL', None)
    return None


def outline_node(outline_mat):
    if outline_mat is None or outline_mat.node_tree is None:
        return None
    return next((n for n in outline_mat.node_tree.nodes if n.bl_idname == 'ShaderNodeDaskOutline'), None)


def outline_material_for(mat, create=True):
    companion = mat.get(OUTLINE_MAT_PROP)
    if isinstance(companion, bpy.types.Material):
        return companion
    if not create:
        return None
    companion = bpy.data.materials.new(mat.name + ".Outline")
    companion.use_backface_culling = True
    if hasattr(companion, "use_backface_culling_shadow"):
        companion.use_backface_culling_shadow = True
    nt = companion.node_tree
    nt.nodes.clear()
    output = nt.nodes.new('ShaderNodeOutputMaterial')
    output.location = (300.0, 0.0)
    dask = nt.nodes.new('ShaderNodeDaskOutline')
    nt.links.new(dask.outputs["BSDF"], output.inputs["Surface"])
    mat[OUTLINE_MAT_PROP] = companion
    return companion


def _set_value(socket, value):
    current = socket.default_value
    try:
        same = tuple(current) == tuple(value)
    except TypeError:
        same = current == value
    if not same:
        socket.default_value = value


def _sync_socket(source_socket, target_tree, target_socket):
    from .dasktoon_anime_nodes import _sync_outline_socket
    if source_socket.is_linked:
        _sync_outline_socket(source_socket, target_tree, target_socket, {})
    else:
        for link in list(target_socket.links):
            target_tree.links.remove(link)
        _set_value(target_socket, tuple(source_socket.default_value))


def sync_material(mat):
    """Quick controls of the main node -> companion material (one-way, spec 4.2)."""
    source = find_source(mat)
    if source is None or source[1] is None:
        return
    kind, node = source
    companion = outline_material_for(mat)
    dask = outline_node(companion)
    if dask is None:
        return
    tree = companion.node_tree
    for n in list(tree.nodes):
        if n.bl_idname not in {'ShaderNodeDaskOutline', 'ShaderNodeOutputMaterial'}:
            tree.nodes.remove(n)
    _sync_socket(node.inputs["Outline Color"], tree, dask.inputs["Outline Color"])
    _sync_socket(node.inputs["Base Color"], tree, dask.inputs["Base Color"])
    _set_value(dask.inputs["Outline Lighting Mix"], node.inputs["Outline Lighting Mix"].default_value)
    tint_value = node.bl_rna.properties["outline_tint_mode"].enum_items[node.outline_tint_mode].value
    for item in dask.bl_rna.properties["tint_mode"].enum_items:
        if item.value == tint_value and dask.tint_mode != item.identifier:
            dask.tint_mode = item.identifier


def find_sun(scene):
    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.data.type == 'SUN' and obj.visible_get():
            return obj
    return None


def _slot_params(obj):
    slots = []
    for slot in obj.material_slots:
        mat = slot.material
        source = find_source(mat)
        if source is None:
            slots.append(gn.SlotParams(False, 0.0, 0.0, 0.0, None))
            continue
        companion = outline_material_for(mat)
        dask = outline_node(companion)
        node = source[1]
        width_socket = node.inputs["Outline Width"] if node is not None else dask.inputs["Outline Width"]
        slots.append(gn.SlotParams(True, float(width_socket.default_value),
                                   float(dask.inputs["Light Bleed"].default_value),
                                   float(dask.inputs["Hand Wobble"].default_value), companion))
    return slots


def sync_object(obj, scene):
    if obj.type != 'MESH' or obj.library is not None:
        return
    slots = _slot_params(obj)
    if not any(s.enabled for s in slots):
        _signatures.pop(obj.as_pointer(), None)
        gn.remove_modifier(obj)
        return
    sun = find_sun(scene)
    uv_name = obj.data.uv_layers[0].name if obj.data.uv_layers else ""
    mask_name = next((name for name in MASK_NAMES if name in obj.vertex_groups), "")
    signature = (
        tuple((s.enabled, round(s.width, 6), round(s.bleed, 6), round(s.wobble, 6),
               s.outline_material.as_pointer() if s.outline_material else 0) for s in slots),
        sun.as_pointer() if sun else 0, uv_name, mask_name, obj.name,
    )
    if _signatures.get(obj.as_pointer()) == signature and obj.modifiers.get(gn.MODIFIER_NAME):
        return
    gn.ensure_modifier(obj, gn.build_object_group(obj, slots, sun, mask_name, uv_name))
    _signatures[obj.as_pointer()] = signature


def sync_all(scene):
    for mat in bpy.data.materials:
        if mat.library is None:
            sync_material(mat)
    for obj in scene.objects:
        sync_object(obj, scene)


@persistent
def outline_depsgraph_post(scene, depsgraph):
    global _busy
    if _busy:
        return
    materials, objects, everything = set(), set(), False
    for update in depsgraph.updates:
        data = update.id.original
        if isinstance(data, bpy.types.Material):
            materials.add(data)
        elif isinstance(data, bpy.types.Object):
            if data.type == 'LIGHT':
                everything = True
            elif update.is_updated_geometry or update.is_updated_shading:
                objects.add(data)
    if not (materials or objects or everything):
        return
    _busy = True
    try:
        for mat in materials:
            sync_material(mat)
        if everything:
            targets = list(scene.objects)
        else:
            targets = set(objects)
            if materials:
                targets.update(o for o in scene.objects
                               if any(slot.material in materials for slot in getattr(o, "material_slots", ())))
        for obj in targets:
            sync_object(obj, scene)
    finally:
        _busy = False


@persistent
def outline_load_post(_filepath):
    reset_cache()
    for scene in bpy.data.scenes:
        sync_all(scene)


class DASKTOON_OT_outline_toggle_material(Operator):
    """Turn the DaskToon outline on or off for a material without an Anime BSDF / Dask Cel node"""
    bl_idname = "dasktoon.outline_toggle_material"
    bl_label = "Outline"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        mat = context.material
        if mat is None:
            return {'CANCELLED'}
        mat[OUTLINE_PROP] = not bool(mat.get(OUTLINE_PROP))
        return {'FINISHED'}


class MATERIAL_PT_dasktoon_outline(Panel):
    bl_label = "DaskToon Outline"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        return context.material is not None

    def draw(self, context):
        layout = self.layout
        mat = context.material
        main = next((n for n in mat.node_tree.nodes
                     if n.bl_idname in {'ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel'}), None) if mat.node_tree else None
        if main is not None and main.bl_idname == 'ShaderNodeAnimeCharacter':
            layout.prop(main, "use_outline", text="Outline")
        elif main is not None:
            layout.prop(main.inputs["Use Outline"], "default_value", text="Outline")
        else:
            layout.operator(DASKTOON_OT_outline_toggle_material.bl_idname,
                            text="Outline", depress=bool(mat.get(OUTLINE_PROP)))
        companion = outline_material_for(mat, create=False)
        dask = outline_node(companion)
        if find_source(mat) is not None and dask is not None:
            col = layout.column(align=True)
            if main is None:
                col.prop(dask.inputs["Outline Width"], "default_value", text="Width")
            col.prop(dask.inputs["Light Bleed"], "default_value", text="Light Bleed")
            col.prop(dask.inputs["Hand Wobble"], "default_value", text="Hand Wobble")
            col.prop(dask, "tint_mode", text="")
        layout.operator("dasktoon.outline_prepare_game_data", icon='EXPORT')


classes = (DASKTOON_OT_outline_toggle_material, MATERIAL_PT_dasktoon_outline)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    if outline_depsgraph_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(outline_depsgraph_post)
    if outline_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(outline_load_post)


def unregister():
    for handler_list, handler in ((bpy.app.handlers.depsgraph_update_post, outline_depsgraph_post),
                                  (bpy.app.handlers.load_post, outline_load_post)):
        if handler in handler_list:
            handler_list.remove(handler)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

- [ ] **Step 4: Sửa `dasktoon_anime_nodes.py`.** Xóa hàm `dasktoon_vrm_outline_auto_sync` (kể cả decorator) và các dòng thêm/gỡ nó trong `register()`/`unregister()`. Giữ `_sync_outline_socket` và `_sync_outline_node_subgraph`. Thay nhánh `elif self.preset_type == 'OUTLINE':` bằng:

```python
        elif self.preset_type == 'OUTLINE':
            target = obj.active_material
            if target is None or target.node_tree is None:
                self.report({'WARNING'}, "Hãy gán một material cho object trước")
                return {'CANCELLED'}
            main = next((n for n in target.node_tree.nodes
                         if n.bl_idname in {'ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel'}), None)
            if main is not None and main.bl_idname == 'ShaderNodeAnimeCharacter':
                main.use_outline = True
            elif main is not None:
                main.inputs["Use Outline"].default_value = True
            else:
                target["dasktoon_outline"] = True
            self.report({'INFO'}, "Đã bật outline cho material '%s'" % target.name)
            return {'FINISHED'}
```

Đặt nhánh này **trước** đoạn `mat = bpy.data.materials.new(...)` ở đầu `execute`, để preset OUTLINE không tạo material thừa. Chỗ đặt nhánh là quyết định do nhóm tự chọn, ghi vào báo cáo.

- [ ] **Step 5: Đăng ký module, đồng bộ script, chạy `dasktoon_outline_sync_test.py` và `dasktoon_outline_nodes_test.py`.** Mong đợi: PASS.
- [ ] **Step 6: Commit** `feat: sync per-material DaskToon outlines with Geometry Nodes and drop the Solidify handler`

---

### Task 9: Dữ liệu outline cho game (`DT_OutlineN`, `DT_OutlineW`)

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_outline_gamedata.py`; thêm `"dasktoon_outline_gamedata"` vào `_modules`
- Create: `tests/python/dasktoon_outline_gamedata_test.py`

**Interfaces:**
- Consumes: `dasktoon_outline.MASK_NAMES`, `dasktoon_outline_nodes.MODIFIER_NAME`
- Produces:
  - `oct_encode(np.ndarray (N, 3)) -> (N, 2)`, `oct_decode((N, 2)) -> (N, 3)`
  - `smoothed_vertex_normals(mesh) -> np.ndarray (V, 3)`
  - `write_outline_uvs(obj) -> tuple[bool, str]`, `is_outline_data_stale(mesh) -> bool`
  - Operator `dasktoon.outline_prepare_game_data`

- [ ] **Step 1: Viết test lỗi**

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import unittest

import bmesh
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline_gamedata as gd  # noqa: E402


def decoded_world_normals(mesh):
    """Decode DT_OutlineN back to object space using the same MikkTSpace frame."""
    uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
    mesh.uv_layers["DT_OutlineN"].uv.foreach_get("vector", uv)
    n_ts = gd.oct_decode(uv.reshape(-1, 2).astype(np.float64))
    mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
    t = np.array([l.tangent for l in mesh.loops])
    sign = np.array([l.bitangent_sign for l in mesh.loops])
    n = np.array([cn.vector for cn in mesh.corner_normals])
    b = sign[:, None] * np.cross(n, t)
    mesh.free_tangents()
    return n_ts[:, :1] * t + n_ts[:, 1:2] * b + n_ts[:, 2:3] * n


class GameDataTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()

    def test_oct_round_trip(self):
        rng = np.random.default_rng(1)
        v = rng.normal(size=(10000, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        self.assertLess(np.abs(gd.oct_decode(gd.oct_encode(v)) - v).max(), 1e-6)

    def test_sphere_decodes_to_radial_normal(self):
        obj = tu.add_sphere(segments=24, rings=12)
        ok, msg = gd.write_outline_uvs(obj)
        self.assertTrue(ok, msg)
        mesh = obj.data
        decoded = decoded_world_normals(mesh)
        corner_vert = np.array([l.vertex_index for l in mesh.loops])
        radial = np.array([mesh.vertices[i].co.normalized() for i in corner_vert])
        self.assertLess(np.abs(decoded - radial).max(), 1e-3)

    def test_split_cube_shares_smoothed_normal(self):
        bpy.ops.mesh.primitive_cube_add(size=2.0)
        obj = bpy.context.active_object
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.split_edges(bm, edges=bm.edges[:])
        bm.to_mesh(obj.data)
        bm.free()
        ok, msg = gd.write_outline_uvs(obj)
        self.assertTrue(ok, msg)
        decoded = decoded_world_normals(obj.data)
        by_pos = {}
        for loop, normal in zip(obj.data.loops, decoded):
            key = tuple(round(c, 4) for c in obj.data.vertices[loop.vertex_index].co)
            by_pos.setdefault(key, []).append(normal)
        for normals in by_pos.values():
            self.assertLess(np.abs(np.array(normals) - normals[0]).max(), 1e-3)

    def test_mask_written_to_dt_outline_w(self):
        obj = tu.add_plane()
        group = obj.vertex_groups.new(name="Outline_Weight")
        group.add([0, 1], 0.25, 'REPLACE')
        ok, msg = gd.write_outline_uvs(obj)
        self.assertTrue(ok, msg)
        layer = obj.data.uv_layers["DT_OutlineW"]
        for loop, uv in zip(obj.data.loops, layer.uv):
            self.assertAlmostEqual(uv.vector[0], 0.25 if loop.vertex_index in (0, 1) else 0.0, places=5)

    def test_active_uv_preserved_and_signature(self):
        obj = tu.add_plane()
        mesh = obj.data
        first = mesh.uv_layers[0].name
        ok, _msg = gd.write_outline_uvs(obj)
        self.assertTrue(ok)
        self.assertEqual(mesh.uv_layers.active.name, first)
        self.assertTrue([uv for uv in mesh.uv_layers if uv.active_render][0].name == first)
        self.assertFalse(gd.is_outline_data_stale(mesh))

    def test_errors_without_uv_or_with_ngon(self):
        bpy.ops.mesh.primitive_circle_add(vertices=8, fill_type='NGON')
        ngon = bpy.context.active_object
        ok, msg = gd.write_outline_uvs(ngon)
        self.assertFalse(ok)
        self.assertNotIn("DT_OutlineN", [uv.name for uv in ngon.data.uv_layers])
        obj = tu.add_plane()
        while obj.data.uv_layers:
            obj.data.uv_layers.remove(obj.data.uv_layers[0])
        ok, msg = gd.write_outline_uvs(obj)
        self.assertFalse(ok)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy để xác nhận FAIL**

- [ ] **Step 3: Viết `scripts/startup/bl_ui/dasktoon_outline_gamedata.py`**

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Outline data for game engines: smoothed normals (tangent space, octahedral) in DT_OutlineN
and the painted width mask in DT_OutlineW (spec section 5)."""

import bpy
import numpy as np
from bpy.types import Operator

from .dasktoon_outline import MASK_NAMES
from .dasktoon_outline_nodes import MODIFIER_NAME

UV_NORMAL = "DT_OutlineN"
UV_MASK = "DT_OutlineW"
SIG_PROP = "dt_outline_sig"
QUANT = 1e-5


def oct_encode(v):
    v = v / np.abs(v).sum(axis=1, keepdims=True)
    xy = v[:, :2].copy()
    neg = v[:, 2] < 0.0
    sign = np.where(xy[neg] >= 0.0, 1.0, -1.0)
    xy[neg] = (1.0 - np.abs(v[neg][:, [1, 0]])) * sign
    return xy


def oct_decode(e):
    n = np.column_stack([e[:, 0], e[:, 1], 1.0 - np.abs(e[:, 0]) - np.abs(e[:, 1])])
    t = np.clip(-n[:, 2], 0.0, None)
    n[:, 0] += np.where(n[:, 0] >= 0.0, -t, t)
    n[:, 1] += np.where(n[:, 1] >= 0.0, -t, t)
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def _array(collection, attr, count, width, dtype=np.float64):
    out = np.empty(count * width, dtype=np.float32 if dtype == np.float64 else dtype)
    collection.foreach_get(attr, out)
    return out.reshape(count, width).astype(dtype) if width > 1 else out.astype(dtype)


def smoothed_vertex_normals(mesh):
    """Angle-weighted face normals summed over vertices that share a position (merges split seams)."""
    v_count, l_count, p_count = len(mesh.vertices), len(mesh.loops), len(mesh.polygons)
    co = _array(mesh.vertices, "co", v_count, 3)
    corner_vert = _array(mesh.loops, "vertex_index", l_count, 1, np.int64)
    loop_start = _array(mesh.polygons, "loop_start", p_count, 1, np.int64)
    loop_total = _array(mesh.polygons, "loop_total", p_count, 1, np.int64)
    poly_normal = _array(mesh.polygons, "normal", p_count, 3)
    corner_poly = np.repeat(np.arange(p_count), loop_total)
    k = np.arange(l_count) - loop_start[corner_poly]
    total = loop_total[corner_poly]
    prev_corner = loop_start[corner_poly] + (k - 1) % total
    next_corner = loop_start[corner_poly] + (k + 1) % total
    here = co[corner_vert]
    e1 = co[corner_vert[prev_corner]] - here
    e2 = co[corner_vert[next_corner]] - here
    angle = np.arctan2(np.linalg.norm(np.cross(e1, e2), axis=1), (e1 * e2).sum(axis=1))
    keys = np.round(co / QUANT).astype(np.int64)
    _unique, group = np.unique(keys, axis=0, return_inverse=True)
    group = group.reshape(-1)
    acc = np.zeros((group.max() + 1, 3))
    np.add.at(acc, group[corner_vert], poly_normal[corner_poly] * angle[:, None])
    acc /= np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
    return acc[group]


def _mask_per_vertex(obj):
    name = next((n for n in MASK_NAMES if n in obj.vertex_groups), None)
    weights = np.ones(len(obj.data.vertices))
    if name is None:
        return weights
    index = obj.vertex_groups[name].index
    weights[:] = 0.0
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == index:
                weights[v.index] = g.weight
    return weights


def _ensure_layer(mesh, name):
    layer = mesh.uv_layers.get(name)
    return layer if layer is not None else mesh.uv_layers.new(name=name, do_init=False)


def write_outline_uvs(obj):
    mesh = obj.data
    if not mesh.uv_layers:
        return False, "%s: cần ít nhất một UV map" % obj.name
    if any(p.loop_total > 4 for p in mesh.polygons):
        return False, "%s: có mặt nhiều hơn 4 cạnh (ngon); hãy Triangulate hoặc chia lại trước" % obj.name
    uv0 = mesh.uv_layers[0].name
    active_name = mesh.uv_layers.active.name
    render_name = next(uv.name for uv in mesh.uv_layers if uv.active_render)
    l_count = len(mesh.loops)
    mesh.calc_tangents(uvmap=uv0)
    tangent = _array(mesh.loops, "tangent", l_count, 3)
    sign = _array(mesh.loops, "bitangent_sign", l_count, 1)
    normal = np.array([c.vector for c in mesh.corner_normals], dtype=np.float64)
    mesh.free_tangents()
    bitangent = sign[:, None] * np.cross(normal, tangent)
    corner_vert = _array(mesh.loops, "vertex_index", l_count, 1, np.int64)
    smooth = smoothed_vertex_normals(mesh)[corner_vert]
    n_ts = np.column_stack([(smooth * tangent).sum(1), (smooth * bitangent).sum(1), (smooth * normal).sum(1)])
    n_ts /= np.maximum(np.linalg.norm(n_ts, axis=1, keepdims=True), 1e-12)
    encoded = oct_encode(n_ts).astype(np.float32)
    mask = np.zeros((l_count, 2), dtype=np.float32)
    mask[:, 0] = _mask_per_vertex(obj)[corner_vert]
    _ensure_layer(mesh, UV_NORMAL).uv.foreach_set("vector", encoded.ravel())
    _ensure_layer(mesh, UV_MASK).uv.foreach_set("vector", mask.ravel())
    mesh.uv_layers.active = mesh.uv_layers[active_name]
    mesh.uv_layers[render_name].active_render = True
    mesh[SIG_PROP] = [len(mesh.vertices), l_count, uv0]
    return True, "%s: đã ghi %s và %s" % (obj.name, UV_NORMAL, UV_MASK)


def is_outline_data_stale(mesh):
    sig = mesh.get(SIG_PROP)
    if sig is None or not mesh.uv_layers:
        return True
    return list(sig) != [len(mesh.vertices), len(mesh.loops), mesh.uv_layers[0].name]


class DASKTOON_OT_outline_prepare_game_data(Operator):
    """Write smoothed outline normals and the width mask into real UV maps for game export"""
    bl_idname = "dasktoon.outline_prepare_game_data"
    bl_label = "Chuẩn bị outline cho game"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objects = [o for o in context.selected_objects if o.type == 'MESH']
        if not objects:
            objects = [o for o in context.scene.objects if o.type == 'MESH' and o.modifiers.get(MODIFIER_NAME)]
        done, errors, seen = 0, [], set()
        for obj in objects:
            if obj.data in seen or obj.data.library is not None:
                continue
            seen.add(obj.data)
            ok, msg = write_outline_uvs(obj)
            if ok:
                done += 1
            else:
                errors.append(msg)
        for msg in errors:
            self.report({'WARNING'}, msg)
        self.report({'INFO'}, "Đã chuẩn bị %d mesh, %d lỗi" % (done, len(errors)))
        return {'FINISHED'} if done else {'CANCELLED'}


def register():
    bpy.utils.register_class(DASKTOON_OT_outline_prepare_game_data)


def unregister():
    bpy.utils.unregister_class(DASKTOON_OT_outline_prepare_game_data)
```

- [ ] **Step 4: Đăng ký module, đồng bộ script, chạy test.** Mong đợi: PASS. Ngoài ra chạy lại `dasktoon_platform_test.py`: test FBX phải vẫn PASS.
- [ ] **Step 5: Commit** `feat: write DaskToon outline game data into real UV maps`

---

### Task 10: Dấu phiên bản dữ liệu và tự động nâng cấp file cũ

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_upgrade.py`. Thêm `"dasktoon_upgrade"` vào `_modules` (sau `"dasktoon_outline_gamedata"`)
- Modify: `scripts/startup/bl_ui/dasktoon_outline.py`. **Không** tự đăng ký `outline_load_post` nữa; `dasktoon_upgrade` sẽ gọi `sync_all` sau khi nâng cấp xong
- Create: `tests/python/dasktoon_upgrade_test.py`

**Interfaces:**
- Consumes: `dasktoon_outline.{find_source, outline_material_for, outline_node, sync_all, reset_cache, OUTLINE_PROP}` và `dasktoon_anime_nodes._sync_outline_socket`
- Produces: `DATA_VERSION = 1`, `REPORT_TEXT = "DaskToon Upgrade Report"`, `needs_upgrade() -> bool`, `upgrade_nodes(lines)`, `upgrade_legacy_outline(lines)`, handler `upgrade_load_post`, `stamp_save_pre`

- [ ] **Step 1: Viết test lỗi**

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_upgrade as up  # noqa: E402
from bl_ui import dasktoon_outline_nodes as gn  # noqa: E402


def open_fixture(name):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(tu.DATA_DIR, name))


class UpgradeTest(unittest.TestCase):
    def test_legacy_outline_is_upgraded(self):
        open_fixture("dasktoon_legacy_outline.blend")
        hero = bpy.data.objects["Hero"]
        self.assertFalse(any(m.type == 'SOLIDIFY' for o in bpy.data.objects for m in o.modifiers))
        self.assertFalse(any(m and m.name.endswith("_DaskOutline") for m in hero.data.materials))
        self.assertEqual(len(hero.data.materials), 1)
        self.assertIsNone(bpy.data.materials.get("Hero_DaskOutline"))
        self.assertIsNotNone(hero.modifiers.get(gn.MODIFIER_NAME))
        skin = bpy.data.materials["Skin"]
        node = next(n for n in skin.node_tree.nodes if n.bl_idname == 'ShaderNodeAnimeCharacter')
        self.assertTrue(node.use_outline)
        self.assertAlmostEqual(node.inputs["Outline Width"].default_value, 0.004, places=6)
        self.assertIn(up.REPORT_TEXT, bpy.data.texts)
        for scene in bpy.data.scenes:
            self.assertEqual(scene.get("dasktoon_data_version"), up.DATA_VERSION)

    def test_legacy_anime_cel_modes(self):
        open_fixture("dasktoon_legacy_nodes.blend")
        cel = next(n for n in bpy.data.materials["Legacy_AnimeCel"].node_tree.nodes
                   if n.bl_idname == 'ShaderNodeAnimeCel')
        self.assertEqual(cel.ambient_mode, 'HUE_SAT')
        self.assertEqual(cel.light_blend_mode, 'MULTIPLY')
        bsdf = next(n for n in bpy.data.materials["Legacy_AnimeCharacter"].node_tree.nodes
                    if n.bl_idname == 'ShaderNodeAnimeCharacter')
        self.assertTrue(bsdf.use_ambient)
        self.assertTrue(bsdf.use_rim)
        self.assertEqual(bsdf.shading_mode, 'SIMPLE')

    def test_upgrade_runs_once(self):
        open_fixture("dasktoon_legacy_nodes.blend")
        path = os.path.join(tempfile.mkdtemp(prefix="dasktoon_up_"), "saved.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        cel = next(n for n in bpy.data.materials["Legacy_AnimeCel"].node_tree.nodes
                   if n.bl_idname == 'ShaderNodeAnimeCel')
        cel.ambient_mode = 'OVERLAY'  # the user's later choice must survive reopening
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        cel = next(n for n in bpy.data.materials["Legacy_AnimeCel"].node_tree.nodes
                   if n.bl_idname == 'ShaderNodeAnimeCel')
        self.assertEqual(cel.ambient_mode, 'OVERLAY')


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy để xác nhận FAIL**

- [ ] **Step 3: Viết `scripts/startup/bl_ui/dasktoon_upgrade.py`**

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""One-time upgrade of files saved before the shading/outline rewrite (spec section 6)."""

import bpy
from bpy.app.handlers import persistent

from . import dasktoon_outline as outline

DATA_VERSION = 1
VERSION_PROP = "dasktoon_data_version"
REPORT_TEXT = "DaskToon Upgrade Report"
LEGACY_MODIFIERS = {"DaskToon_Outline", "DaskToon_Outline_Solidify"}


def needs_upgrade():
    return any(scene.get(VERSION_PROP, 0) < DATA_VERSION for scene in bpy.data.scenes)


def _shader_trees():
    for mat in bpy.data.materials:
        if mat.node_tree is not None and mat.library is None:
            yield mat.node_tree
    for group in bpy.data.node_groups:
        if group.bl_idname == 'ShaderNodeTree' and group.library is None:
            yield group


def upgrade_nodes(lines):
    count = 0
    for tree in _shader_trees():
        for node in tree.nodes:
            if node.bl_idname == 'ShaderNodeAnimeCel':
                node.ambient_mode = 'HUE_SAT'
                node.light_blend_mode = 'MULTIPLY'
                count += 1
    if count:
        lines.append("Anime Cel: %d node chuyển sang Ambient HUE_SAT / Light MULTIPLY (gần cách cũ nhất)" % count)


def _is_legacy_outline_material(mat):
    return mat is not None and mat.name.endswith("_DaskOutline")


def _legacy_settings(legacy_mat):
    node = outline.outline_node(legacy_mat)
    if node is None:
        return None
    return {
        "tint_mode": node.tint_mode,
        "color_socket": node.inputs["Outline Color"],
        "values": {name: node.inputs[name].default_value for name in
                   ("Outline Lighting Mix", "Light Bleed", "Hand Wobble", "Tint Darkness", "Tint Saturation Boost")},
    }


def _enable_outline(mat, width):
    main = next((n for n in mat.node_tree.nodes
                 if n.bl_idname in {'ShaderNodeAnimeCharacter', 'ShaderNodeDaskCel'}), None)
    if main is not None and main.bl_idname == 'ShaderNodeAnimeCharacter':
        main.use_outline = True
    elif main is not None:
        main.inputs["Use Outline"].default_value = True
    else:
        mat[outline.OUTLINE_PROP] = True
    if width is not None:
        socket = main.inputs["Outline Width"] if main is not None else None
        if socket is not None and socket.default_value in (0.0, 0.002):
            socket.default_value = width
    return main


def upgrade_legacy_outline(lines):
    from .dasktoon_anime_nodes import _sync_outline_socket
    copied = {}
    removed_slots = 0
    for obj in list(bpy.data.objects):
        if obj.type != 'MESH':
            continue
        mods = [m for m in obj.modifiers if m.type == 'SOLIDIFY' and m.name in LEGACY_MODIFIERS]
        slots = [i for i, m in enumerate(obj.data.materials) if _is_legacy_outline_material(m)]
        if not mods and not slots:
            continue
        if obj.library is not None or obj.data.library is not None:
            lines.append("Bỏ qua %s (dữ liệu link từ thư viện)" % obj.name)
            continue
        width = mods[0].thickness if mods else None
        legacy_mat = obj.data.materials[slots[0]] if slots else bpy.data.materials.get(obj.name + "_DaskOutline")
        settings = _legacy_settings(legacy_mat) if legacy_mat is not None else None
        for mod in mods:
            obj.modifiers.remove(mod)
        for i in reversed(slots):
            obj.data.materials.pop(index=i)
            removed_slots += 1
        for mat in obj.data.materials:
            if mat is None or mat.node_tree is None or _is_legacy_outline_material(mat):
                continue
            _enable_outline(mat, width)
            if settings is None:
                continue
            if mat in copied:
                if copied[mat] != obj.name:
                    lines.append("Xung đột: %s dùng chung material %s, giữ thiết lập của %s"
                                 % (obj.name, mat.name, copied[mat]))
                continue
            companion = outline.outline_material_for(mat)
            dask = outline.outline_node(companion)
            dask.tint_mode = settings["tint_mode"]
            for name, value in settings["values"].items():
                dask.inputs[name].default_value = value
            _sync_outline_socket(settings["color_socket"], companion.node_tree, dask.inputs["Outline Color"], {})
            copied[mat] = obj.name
        lines.append("Đã nâng cấp outline của %s" % obj.name)
    orphans = [m for m in bpy.data.materials if _is_legacy_outline_material(m) and m.users == 0]
    for mat in orphans:
        bpy.data.materials.remove(mat)
    if removed_slots or orphans:
        lines.append("Đã dọn %d slot thừa và %d material _DaskOutline" % (removed_slots, len(orphans)))


def _report(lines):
    text = bpy.data.texts.get(REPORT_TEXT) or bpy.data.texts.new(REPORT_TEXT)
    text.clear()
    text.write("\n".join(lines) + "\n")
    summary = "DaskToon đã nâng cấp file: %s" % (lines[0] if lines else "không có gì")
    print(summary)
    if bpy.app.background:
        return

    def show():
        wm = bpy.context.window_manager
        if wm.windows:
            wm.popup_menu(lambda self, _ctx: [self.layout.label(text=line) for line in lines[:8]],
                          title="DaskToon", icon='INFO')
        return None

    bpy.app.timers.register(show, first_interval=0.5)


@persistent
def upgrade_load_post(_filepath):
    if needs_upgrade():
        lines = []
        upgrade_nodes(lines)
        upgrade_legacy_outline(lines)
        for scene in bpy.data.scenes:
            scene[VERSION_PROP] = DATA_VERSION
        if lines:
            _report(lines)
    outline.reset_cache()
    for scene in bpy.data.scenes:
        outline.sync_all(scene)


@persistent
def stamp_save_pre(_filepath):
    for scene in bpy.data.scenes:
        if scene.library is None and scene.get(VERSION_PROP) != DATA_VERSION:
            scene[VERSION_PROP] = DATA_VERSION


def register():
    if upgrade_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(upgrade_load_post)
    if stamp_save_pre not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(stamp_save_pre)


def unregister():
    if upgrade_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(upgrade_load_post)
    if stamp_save_pre in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(stamp_save_pre)
```

Lưu ý: file mới tạo (startup hoặc factory) cũng không có dấu phiên bản, nhưng trong đó không có Anime Cel cũ nên `upgrade_nodes` không đổi gì; sau đó dấu được ghi, coi như hợp lệ. Nếu startup file của DaskToon có sẵn Anime Cel thì các node đó sẽ bị chuyển mode một lần. Ghi vào báo cáo như một hệ quả đã chấp nhận.

- [ ] **Step 4: Gỡ phần đăng ký `outline_load_post` trong `dasktoon_outline.py`** (giữ hàm để test có thể gọi). Đồng bộ script, chạy test `upgrade` và `outline_sync`. Mong đợi: PASS.
- [ ] **Step 5: Commit** `feat: upgrade pre-rewrite DaskToon files automatically on load`

---

### Task 11: Ảnh để duyệt bằng mắt, đăng ký test với CMake, báo cáo

**Files:**
- Create: `tests/python/dasktoon_visual_review.py`
- Modify: `tests/python/CMakeLists.txt`
- Create: `docs/superpowers/reports/2026-10-03-dasktoon-progress.md`

- [ ] **Step 1: Viết `dasktoon_visual_review.py`.** Script render một quả cầu và một khối đơn giản ở độ phân giải 256×256, với từng preset (cộng chế độ Đơn giản) và ba góc Sun. Thêm một hàng outline: Light Bleed 0 và 1, Wobble 0 và 1. Ghép tất cả thành `review_sheet.png` bằng numpy (tạo `bpy.data.images.new` rồi ghi `pixels`), đặt trong `$DASKTOON_TEST_OUT/review/`. Đây không phải unittest, và in ra đường dẫn ảnh khi xong.

```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Render a contact sheet of shading styles and outlines for human review (not an automated test).

DaskToon.exe --background --factory-startup --python tests/python/dasktoon_visual_review.py
"""

import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_shading_styles as styles  # noqa: E402

SIZE = 256
OUT = os.path.join(tu.OUT_DIR, "review")
SUN_ANGLES = (0.3, 0.9, 1.4)


def render_tile(style_name, sun_angle, outline=None):
    tu.reset_scene(SIZE)
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    tu.set_world_color((0.05, 0.06, 0.08))
    tu.add_sun(3.0, rotation=(sun_angle, 0.4, 0.0))
    obj = tu.add_sphere(radius=1.2)
    mat, node = tu.node_material("Review", 'ShaderNodeAnimeCharacter')
    tu.assign(obj, mat)
    node.inputs["Base Color"].default_value = (0.95, 0.80, 0.72, 1.0)
    if style_name is not None:
        node.shading_mode = 'RAMP'
        styles.apply_style(node.shading_ramp, styles.BUILTIN_STYLES[style_name])
    if outline is not None:
        node.use_outline = True
        node.inputs["Outline Width"].default_value = 0.03
        bpy.context.view_layer.update()
        from bl_ui import dasktoon_outline
        dask = dasktoon_outline.outline_node(dasktoon_outline.outline_material_for(mat))
        dask.inputs["Light Bleed"].default_value = outline[0]
        dask.inputs["Hand Wobble"].default_value = outline[1]
        bpy.context.view_layer.update()
    path = os.path.join(OUT, "%s_%.1f_%s.png" % (style_name or "Simple", sun_angle, outline))
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    tile = np.array(img.pixels[:]).reshape(SIZE, SIZE, 4)
    bpy.data.images.remove(img)
    return tile


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for style_name in [None] + list(styles.BUILTIN_STYLES):
        rows.append(np.concatenate([render_tile(style_name, a) for a in SUN_ANGLES], axis=1))
    rows.append(np.concatenate([render_tile(None, 0.9, outline=o) for o in ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))],
                               axis=1))
    sheet = np.concatenate(rows[::-1], axis=0)
    h, w = sheet.shape[:2]
    image = bpy.data.images.new("review_sheet", w, h, alpha=True)
    image.pixels = sheet.ravel()
    image.filepath_raw = os.path.join(OUT, "review_sheet.png")
    image.file_format = 'PNG'
    image.save()
    print("REVIEW SHEET:", image.filepath_raw)


main()
```

- [ ] **Step 2: Chạy script và mở ảnh ra xem.** Chép ảnh vào `docs/superpowers/reports/` để người dùng duyệt.
- [ ] **Step 3: Đăng ký test trong `tests/python/CMakeLists.txt`** (ngay sau khối `script_load_addons`):

```cmake
foreach(dasktoon_test
    dasktoon_platform_test
    dasktoon_shading_test
    dasktoon_shading_baseline
    dasktoon_shading_styles_test
    dasktoon_outline_nodes_test
    dasktoon_outline_sync_test
    dasktoon_outline_gamedata_test
    dasktoon_upgrade_test
)
  add_blender_test(
    ${dasktoon_test}
    --python ${CMAKE_CURRENT_LIST_DIR}/${dasktoon_test}.py
  )
endforeach()
```

- [ ] **Step 4: Chạy lại toàn bộ test một lượt** (vòng lặp shell qua 8 file, in PASS/FAIL cho từng file)

```bash
for t in platform_test shading_test shading_baseline shading_styles_test outline_nodes_test outline_sync_test outline_gamedata_test upgrade_test; do
  "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_$t.py >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"
done
```

- [ ] **Step 5: Viết báo cáo** `docs/superpowers/reports/2026-10-03-dasktoon-progress.md`. Nội dung gồm:
  - Trạng thái từng task.
  - Kết quả của lượt chạy test ở Step 4.
  - Thời gian build đo được.
  - Các quyết định tự đưa ra kèm lý do.
  - Các lỗi phát hiện thêm (ví dụ chỉ số Normal của Anime Cel, `outline_tint_mode_set`).
  - Những việc người dùng cần làm: duyệt ảnh, kiểm tra giao diện node trong GUI, xem lại công thức Light Mode.

- [ ] **Step 6: Commit** `test: register DaskToon tests, add visual review sheet and progress report`
