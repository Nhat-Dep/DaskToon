# DaskToon: rig anime R2b (lắc trong Unity) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao tự động rồi "tiếp tục" (2026-10-06 20:34); Claude chạy **inline** trên `dasktoon-anime-rig`,
> sau R1, R2. Không push, không merge.

**Goal:** Kéo model DaskToon vào Unity là tóc và váy tự lắc bằng script DaskToon, cùng thuật toán và thông số với lắc trực
tiếp trong DaskToon; phần chọn "Baked" thì Unity phát keyframe đã bake.

**Architecture:** Engine Export ghi `<Model>.rig.json` cạnh FBX (chuỗi theo tên xương, độ dài, thông số, chế độ Unity;
collider theo tên xương, bán kính, độ dài) và cài ba script C# vào `Assets/DaskToon/Scripts/` (GUID cố định, file phiên
bản như shader). `DaskToonRigImporter` (AssetPostprocessor) đọc json lúc Unity import FBX và gắn `DaskToonSpringBone`
(mỗi chuỗi một component trên gốc model) và `DaskToonSpringCollider` (trên xương thân) vào prefab của model. Trong lúc
ghi FBX, các chuỗi "Runtime" không lắc (về tư thế nghỉ) để Unity không lắc hai lần.

**Tech Stack:** Python `bpy`, C# (Unity 6000.5, URP 17.5), `tests/python/dasktoon_unity_harness.py` (Unity batchmode
trên project tạm `%TEMP%\dasktoon_unity_test`, không đụng project của người dùng).

**Spec:** `docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md` §9.1 (Sway in Unity), §9.5.

**Đã kiểm trước (thử trong Unity, 2026-10-06):** sau khi Unity import FBX của DaskToon, vị trí world của xương = tọa độ
Blender đổi `(-x, z, -y)`; trục +Y cục bộ của xương chỉ dọc xương (như Blender); xương con nằm ở `(0, độ dài xương cha,
0)`; scale 1. Nên json không cần tọa độ: độ dài và tên xương là đủ.

## Global Constraints

- Như R1, R2 (chữ tiếng Anh có bản Việt, không driver, không panel thanh bên, không push).
- Thuật toán C# là bản dịch từng dòng của `dasktoon_rig/spring.py` (spec §9.3); trọng lực `Vector3.down`.
- Script Unity cài như shader: GUID cố định, `DaskToonScripts.version`, PROJECT mode không ghi đè bản mới hơn.
- Test Unity dùng project tạm của harness; bỏ qua khi máy không có Unity 6000.5.4f1. File C# test không được tham chiếu
  thẳng tới kiểu `DaskToon.*` (project tạm chưa chắc đã có script): dùng reflection.

## Review Focus

1. **Chuỗi Runtime đã bake key**: Unity sẽ lắc hai lần → Engine Export cảnh báo. Test Task 4
   (`test_runtime_chain_with_keys_warns`).
2. **Model không có chuỗi**: không ghi json, không cài script. Test Task 4 (`test_no_chains_no_rig_files`).
3. **Xuất lại vào project đã có script mới hơn**: không ghi đè. Test Task 3 (`test_newer_scripts_are_kept`).
4. **Tư thế trong FBX**: chuỗi Runtime ở tư thế nghỉ khi ghi FBX, chuỗi Baked giữ lắc; xong thì trả lại. Test Task 1
   (`test_suppressed_chains_rest_and_come_back`) và Task 4.
5. **Unity khớp DaskToon**: cùng 20 bước, đuôi xương khớp tới 2 mm. Test Task 5.

---

### Task 1: Chế độ Unity của phần, tắt lắc theo phần

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_rig.py` (`DaskRigPart.sway_in_unity`; panel Sway hiện thêm thuộc tính này),
  `scripts/modules/dasktoon_rig/parts.py` (`Part(..., sway_in_unity='RUNTIME')`), `scripts/modules/dasktoon_rig/sway.py`
  (`world_colliders(rig)` công khai thay `_colliders`; `suppressed(rig, part_names)`), `dasktoon_translations.py`
- Test: `tests/python/dasktoon_rig_sway_test.py` (`SuppressTest`), `tests/python/dasktoon_rig_ui_test.py` (props panel
  Sway)

**Interfaces:**
- Produces: `DaskRigPart.sway_in_unity` ('RUNTIME' | 'BAKED'); `sway.world_colliders(rig) -> [(head, tail, radius)]`;
  `sway.suppressed(rig, part_names)` (context manager: xương của các phần đó về tư thế nghỉ và không lắc khi đổi khung;
  ra khỏi thì góc xoay cũ trở lại, bộ nhớ đệm của rig bị bỏ).

- [ ] **Step 1: Test** — thêm vào `dasktoon_rig_sway_test.py`:
```python
class SuppressTest(unittest.TestCase):
    def test_suppressed_chains_rest_and_come_back(self):
        rig = character()
        play(rig, 8)
        swayed = quat(rig, BONE)
        hair = quat(rig, "Hair_2")
        self.assertLess(abs(swayed[0]), 0.999)
        with sway.suppressed(rig, {"Skirt"}):
            np.testing.assert_allclose(quat(rig, BONE), (1.0, 0.0, 0.0, 0.0), atol=1e-6)
            np.testing.assert_allclose(quat(rig, "Hair_2"), hair, atol=1e-6)
            bpy.context.scene.frame_set(9)
            np.testing.assert_allclose(quat(rig, BONE), (1.0, 0.0, 0.0, 0.0), atol=1e-6)
            self.assertNotEqual(tuple(quat(rig, "Hair_2")), tuple(hair))
        np.testing.assert_allclose(quat(rig, BONE), swayed, atol=1e-6)
        self.assertFalse(sway._cache.get(rig.session_uid))

    def test_world_colliders(self):
        rig = character()
        found = sway.world_colliders(rig)
        self.assertEqual(len(found), len(build.COLLIDER_BONES))
        head, tail, radius = found[0]
        self.assertGreater(np.linalg.norm(tail - head), 0.0)
        self.assertGreater(radius, 0.0)
```
  `dasktoon_rig_ui_test.py`: trong `test_sway_panel_and_bake`, danh sách props panel Sway thành
  `["live_sway", "stiffness", "gravity", "drag", "radius", "sway_in_unity"]`.

- [ ] **Step 2: Chạy, thấy FAIL** — `AttributeError: module 'dasktoon_rig.sway' has no attribute 'suppressed'`.

- [ ] **Step 3: Code**

`sway.py`: đổi tên `_colliders` thành `world_colliders` (cả chỗ gọi trong `sway()`), thêm:
```python
_suppressed = {}  # session_uid of the rig → part names whose chains do not sway (Engine Export, spec 9.5)


@contextmanager
def suppressed(rig, part_names):
    """Meanwhile the chains of `part_names` rest and do not sway; afterwards their rotations come back."""
    names = [name for part, chain in chains(rig) if part in part_names for name in chain]
    saved = {name: tuple(getattr(rig.pose.bones[name], _rotation_path(rig.pose.bones[name]))) for name in names}
    _suppressed[rig.session_uid] = set(part_names)
    identity = Matrix.Identity(3)
    try:
        for name in names:
            _set_rotation(rig.pose.bones[name], identity)
        yield
    finally:
        _suppressed.pop(rig.session_uid, None)
        for name, value in saved.items():
            pb = rig.pose.bones[name]
            setattr(pb, _rotation_path(pb), value)
        clear_cache(rig)
```
  (`from contextlib import contextmanager`.) Trong `sway()`, ngay sau `found = chains(rig)`:
```python
    skipped = _suppressed.get(rig.session_uid, set())
    found = [(part, names) for part, names in found if part not in skipped]
```
  (`frame_pre` vẫn đưa mọi xương chuỗi về nghỉ, nên chuỗi bị tắt đứng ở tư thế nghỉ.)

`bl_ui/dasktoon_rig.py`, `DaskRigPart` thêm:
```python
    sway_in_unity: EnumProperty(
        name="Sway in Unity",
        description="How the chain sways in Unity",
        items=[
            ('RUNTIME', "Runtime", "DaskToon's spring bone script sways the chain while the game runs"),
            ('BAKED', "Baked", "Unity plays the sway baked into the exported animation"),
        ],
        default='RUNTIME',
    )
```
  panel Sway: sau `col.prop(part, "radius")` thêm `layout.prop(part, "sway_in_unity")`.
  `parts.Part`: tham số `sway_in_unity='RUNTIME'` → thuộc tính.

- [ ] **Step 4: Bản dịch**: "Sway in Unity" → "Lắc trong Unity", "How the chain sways in Unity" → "Cách chuỗi lắc trong
  Unity", "Runtime" → "Khi chạy", "DaskToon's spring bone script sways the chain while the game runs" → "Script spring bone
  của DaskToon cho chuỗi lắc khi game chạy", "Baked" → "Đã bake", "Unity plays the sway baked into the exported animation" →
  "Unity phát chuyển động lắc đã bake trong animation xuất ra".
- [ ] **Step 5: Chạy, thấy PASS** — `rt.sh dasktoon_rig_sway_test dasktoon_rig_ui_test dasktoon_translations_test`.
- [ ] **Step 6: Commit** — `feat: Sway in Unity per part, and a way to keep chains at rest while exporting`.

---

### Task 2: File mô tả rig (`rig_json.py`)

**Files:**
- Create: `scripts/modules/dasktoon_export/rig_json.py`
- Test: `tests/python/dasktoon_export_rig_test.py`
- Modify: CMake, `TRANSLATED` += `rig_json.py`

**Interfaces:**
- Consumes: `sway.chains`, `DaskRig.colliders`, `DaskRigPart` thông số.
- Produces: `rig_json.VERSION = 1`, `rig_json.rig_data(rig) -> dict | None`, `rig_json.text(data) -> str`,
  `rig_json.find_rig(objects) -> Object | None` (armature đầu tiên có chuỗi), `rig_json.runtime_parts(rig) -> set`.

- [ ] **Step 1: Test**

**File `tests/python/dasktoon_export_rig_test.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""<Model>.rig.json and the Unity scripts of the anime rig (spec 9.5), and how Engine Export writes them."""

import json
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from dasktoon_export import rig_json  # noqa: E402
from dasktoon_rig import build  # noqa: E402


def built(roles=(("Body", 'BODY'), ("Hair", 'HAIR'), ("Skirt", 'SKIRT'))):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = fx.character()
    rig = fx.rig_for()
    for name, role in roles:
        ui.add_part(rig, objs[name], role)
    build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
    return rig, objs


class RigJsonTest(unittest.TestCase):
    def test_rig_data(self):
        rig, objs = built()
        rig.data.dasktoon_rig.parts["Skirt"].sway_in_unity = 'BAKED'
        rig.data.dasktoon_rig.parts["Hair"].stiffness = 2.5
        data = rig_json.rig_data(rig)
        self.assertEqual(data["version"], 1)
        hair = next(c for c in data["chains"] if c["part"] == "Hair")
        self.assertEqual(hair["bones"], ["Hair_1", "Hair_2", "Hair_3", "Hair_4"])
        self.assertEqual(hair["unity"], "runtime")
        self.assertAlmostEqual(hair["stiffness"], 2.5, places=5)
        self.assertAlmostEqual(hair["lengths"][1], rig.data.bones["Hair_2"].length, places=5)
        skirts = [c for c in data["chains"] if c["part"] == "Skirt"]
        self.assertEqual(len(skirts), 8)
        self.assertEqual({c["unity"] for c in skirts}, {"baked"})
        self.assertEqual([c["bone"] for c in data["colliders"]], list(build.COLLIDER_BONES))
        head = next(c for c in data["colliders"] if c["bone"] == "Head")
        self.assertAlmostEqual(head["length"], rig.data.bones["Head"].length, places=5)
        self.assertEqual(json.loads(rig_json.text(data)), data)
        self.assertEqual(rig_json.runtime_parts(rig), {"Hair"})
        self.assertIs(rig_json.find_rig([objs["Body"], rig]), rig)

    def test_scaled_rig_gives_world_lengths(self):
        rig, _objs = built()
        rig.scale = (2.0, 2.0, 2.0)
        bpy.context.view_layer.update()
        hair = next(c for c in rig_json.rig_data(rig)["chains"] if c["part"] == "Hair")
        self.assertAlmostEqual(hair["lengths"][0], 2.0 * rig.data.bones["Hair_1"].length, places=5)

    def test_no_chains(self):
        rig, objs = built(roles=(("Body", 'BODY'),))
        self.assertIsNone(rig_json.rig_data(rig))
        self.assertIsNone(rig_json.find_rig([rig, objs["Body"]]))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, thấy FAIL** — `cannot import name 'rig_json'`.

- [ ] **Step 3: Code**

**File `scripts/modules/dasktoon_export/rig_json.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""<Model>.rig.json beside the FBX (anime rig spec 9.5): the chains and colliders DaskToon's Unity spring bone needs,
by bone name. Unity keeps a bone's tail along its local +Y, as Blender does, so only lengths (world, meters) travel."""

import json

VERSION = 1


def _length(rig, bone):
    world = rig.matrix_world
    return (world @ bone.tail_local - world @ bone.head_local).length


def rig_data(rig):
    """The json-ready dict of an armature whose chains Build Rig made, or None when it has none."""
    from dasktoon_rig import spring, sway
    found = sway.chains(rig)
    if not found:
        return None
    data = rig.data.dasktoon_rig
    bones = rig.data.bones
    chains = []
    for part_name, names in found:
        part = data.parts.get(part_name)
        defaults = spring.Params()
        chains.append({
            "part": part_name,
            "bones": names,
            "lengths": [round(_length(rig, bones[name]), 6) for name in names],
            "stiffness": round(part.stiffness if part else defaults.stiffness, 6),
            "gravity": round(part.gravity if part else defaults.gravity, 6),
            "drag": round(part.drag if part else defaults.drag, 6),
            "radius": round(part.radius if part else defaults.radius, 6),
            "unity": "baked" if part is not None and part.sway_in_unity == 'BAKED' else "runtime",
        })
    colliders = [{"bone": c.bone, "radius": round(c.radius, 6), "length": round(_length(rig, bones[c.bone]), 6)}
                 for c in data.colliders if bones.get(c.bone) is not None]
    return {"version": VERSION, "chains": chains, "colliders": colliders}


def text(data):
    return json.dumps(data, indent=2) + "\n"


def find_rig(objects):
    """The first armature of `objects` with chains made by Build Rig, or None."""
    from dasktoon_rig import sway
    return next((obj for obj in objects if obj.type == 'ARMATURE' and sway.chains(obj)), None)


def runtime_parts(rig):
    """Names of the parts whose chains Unity sways itself."""
    return {part.name for part in rig.data.dasktoon_rig.parts if part.sway_in_unity == 'RUNTIME'}
```

- [ ] **Step 4: Đăng ký** — CMake `dasktoon_export_rig_test` (sau `dasktoon_rig_sway_test`); `TRANSLATED` +=
  `"scripts/modules/dasktoon_export/rig_json.py"`.
- [ ] **Step 5: Chạy, thấy PASS** — `rt.sh dasktoon_export_rig_test dasktoon_translations_test`.
- [ ] **Step 6: Commit** — `feat: rig description file for Unity (chains, lengths, sway settings, colliders)`.

---

### Task 3: Script Unity và việc cài đặt (`scripts_install.py`)

**Files:**
- Create: `scripts/modules/dasktoon_export/unity_scripts/DaskToonSpringBone.cs`,
  `.../unity_scripts/DaskToonSpringCollider.cs`, `.../unity_scripts/Editor/DaskToonRigImporter.cs`,
  `scripts/modules/dasktoon_export/scripts_install.py`
- Modify: `scripts/modules/dasktoon_export/unity_yaml.py` (`script_meta(guid)`)
- Test: `tests/python/dasktoon_export_rig_test.py` (`ScriptsInstallTest`)
- Modify: `TRANSLATED` += `scripts_install.py`

**Interfaces:**
- Produces: `scripts_install.SCRIPTS_VERSION = 1`, `SCRIPT_DIR = "Scripts"`, `FILE_GUIDS`, `installed_version(root)`,
  `install_scripts(target, warnings, force=False) -> bool`; `unity_yaml.script_meta(guid)`. C#: `DaskToon.DaskToonSpringBone`
  (`bones`, `lastLength`, `stiffness`, `gravity`, `drag`, `radius`, `colliders`, `Setup()`, `Step(float dt)`,
  `Tail(int i)`), `DaskToon.DaskToonSpringCollider` (`radius`, `length`, `Head`, `Tail`, `Radius`),
  `DaskToon.Editor.DaskToonRigImporter`.

- [ ] **Step 1: Test** — thêm vào `dasktoon_export_rig_test.py`:
```python
class ScriptsInstallTest(unittest.TestCase):
    def target(self, root, mode='PROJECT'):
        from dasktoon_export import targets
        return targets.ExportTarget('UNITY_URP', mode, root, "Hero", None)

    def test_install_writes_scripts_with_fixed_guids(self):
        from dasktoon_export import scripts_install as si
        root = os.path.join(tempfile.mkdtemp(prefix="dt_scripts_"), "Assets", "DaskToon")
        warnings = []
        self.assertTrue(si.install_scripts(self.target(root), warnings))
        self.assertEqual(warnings, [])
        for rel, guid in si.FILE_GUIDS.items():
            path = os.path.join(root, si.SCRIPT_DIR, *rel.split("/"))
            self.assertTrue(os.path.isfile(path), rel)
            with open(path + ".meta", encoding="utf-8") as f:
                meta = f.read()
            self.assertIn("guid: %s" % guid, meta)
            self.assertIn("MonoImporter:", meta)
        self.assertTrue(os.path.isfile(os.path.join(root, si.SCRIPT_DIR, "Editor.meta")))
        self.assertEqual(si.installed_version(root), si.SCRIPTS_VERSION)
        with open(os.path.join(root, si.SCRIPT_DIR, "DaskToonSpringBone.cs"), encoding="utf-8") as f:
            code = f.read()
        self.assertIn("public void Step(float dt)", code)
        self.assertIn("Vector3.down", code)

    def test_newer_scripts_are_kept(self):
        from dasktoon_export import scripts_install as si
        root = os.path.join(tempfile.mkdtemp(prefix="dt_scripts_"), "Assets", "DaskToon")
        self.assertTrue(si.install_scripts(self.target(root), []))
        with open(os.path.join(root, si.SCRIPT_DIR, si.VERSION_FILE), "w", encoding="utf-8") as f:
            f.write("%d\n" % (si.SCRIPTS_VERSION + 1))
        self.assertFalse(si.install_scripts(self.target(root), []))
        self.assertTrue(si.install_scripts(self.target(root), [], force=True))
```
  (Nếu `targets.ExportTarget` có chữ ký khác: dùng `targets.make_target(<thư mục giả có Assets>, "Hero")` như test export
  khác — ruling khi chạy.)

- [ ] **Step 2: Chạy, thấy FAIL** — `cannot import name 'scripts_install'`.

- [ ] **Step 3: Code**

`unity_yaml.py`, cạnh `include_meta`:
```python
def script_meta(guid):
    return _meta(guid, ["MonoImporter:", "  externalObjects: {}", "  serializedVersion: 2", "  defaultReferences: []",
                        "  executionOrder: 0", "  icon: {instanceID: 0}"])
```

**File `scripts/modules/dasktoon_export/scripts_install.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Install DaskToon's Unity scripts for the anime rig (spring bones, colliders, the importer that reads
<Model>.rig.json) into an export root, as the shaders are: fixed GUIDs and a version file, so a project is only
rewritten by a newer DaskToon (anime rig spec 9.5)."""

import os

from . import assets, shaders_install, unity_yaml

SCRIPTS_VERSION = 1
SCRIPT_DIR = "Scripts"
VERSION_FILE = "DaskToonScripts.version"
SOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unity_scripts")
FOLDER_GUIDS = {"Scripts": "fc047532de7a491c96575985da296e3a", "Scripts/Editor": "b072af31e2654fc280b1fc5df8af8cf2"}
VERSION_GUID = "aa275e64a29745889c3af2e20285b967"
FILE_GUIDS = {
    "DaskToonSpringBone.cs": "447db0cdbda2403dbb15e084f25149cf",
    "DaskToonSpringCollider.cs": "f611202d6bd34f7fb27569a468d4789b",
    "Editor/DaskToonRigImporter.cs": "5e0acb864e5c435983c70bd57f042a01",
}


def installed_version(root):
    try:
        with open(os.path.join(root, SCRIPT_DIR, VERSION_FILE), encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def install_scripts(target, warnings, force=False):
    """Write the scripts with their fixed GUIDs, then the version file. PROJECT mode skips an install of this version
    or newer unless `force`. Returns True when the scripts were written."""
    if target.mode == 'PROJECT' and not force and installed_version(target.root) >= SCRIPTS_VERSION:
        return False
    shaders_install.ensure_root(target)
    for rel in sorted(FOLDER_GUIDS):
        parent, name = os.path.split(rel)
        assets.ensure_folder(os.path.join(target.root, parent) if parent else target.root, name, FOLDER_GUIDS[rel])
    for rel, guid in sorted(FILE_GUIDS.items()):
        with open(os.path.join(SOURCE_DIR, *rel.split("/")), "rb") as f:
            data = f.read()
        assets.write_asset(target.root, SCRIPT_DIR + "/" + rel, guid, unity_yaml.script_meta(guid), warnings,
                           data=data)
    assets.write_asset(target.root, SCRIPT_DIR + "/" + VERSION_FILE, VERSION_GUID, unity_yaml.default_meta(VERSION_GUID),
                       warnings, data=b"%d\n" % SCRIPTS_VERSION)
    return True
```
  (`assets.ensure_folder(root, relpath, guid)` tạo `<root>/<relpath>` và `.meta` — kiểm chữ ký khi chạy; ruling nếu khác.)

**File `scripts/modules/dasktoon_export/unity_scripts/DaskToonSpringCollider.cs`:**
```csharp
// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Written by DaskToon's Engine Export; exporting again replaces it.

using UnityEngine;

namespace DaskToon
{
    /// <summary>A capsule along a bone, from the bone along its local +Y for `length`, that spring bones keep out of
    /// (DaskToon anime rig).</summary>
    [AddComponentMenu("DaskToon/Spring Collider")]
    [DisallowMultipleComponent]
    public class DaskToonSpringCollider : MonoBehaviour
    {
        public float radius = 0.05f;
        public float length = 0.1f;

        float Scale => transform.lossyScale.y;
        public float Radius => radius * Scale;
        public Vector3 Head => transform.position;
        public Vector3 Tail => transform.position + transform.rotation * Vector3.up * (length * Scale);

        void OnDrawGizmosSelected()
        {
            Gizmos.color = Color.cyan;
            Gizmos.DrawWireSphere(Head, Radius);
            Gizmos.DrawWireSphere(Tail, Radius);
            Gizmos.DrawLine(Head, Tail);
        }
    }
}
```

**File `scripts/modules/dasktoon_export/unity_scripts/DaskToonSpringBone.cs`:**
```csharp
// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Written by DaskToon's Engine Export; exporting again replaces it.

using UnityEngine;

namespace DaskToon
{
    /// <summary>Sways one chain of bones the way DaskToon's Live Sway does (anime rig spec 9.3, dasktoon_rig/spring.py):
    /// every bone keeps its tail's current and previous position; a step adds the inertia, a pull towards the animated
    /// pose and gravity, keeps the bone's length and pushes the tail out of the colliders. A bone's tail is along its
    /// local +Y.</summary>
    [AddComponentMenu("DaskToon/Spring Bone")]
    public class DaskToonSpringBone : MonoBehaviour
    {
        public Transform[] bones = new Transform[0];
        public float lastLength = 0.1f;
        [Range(0f, 4f)] public float stiffness = 1f;
        [Range(0f, 2f)] public float gravity = 0.2f;
        [Range(0f, 1f)] public float drag = 0.4f;
        public float radius = 0.03f;
        public DaskToonSpringCollider[] colliders = new DaskToonSpringCollider[0];

        Vector3[] current = new Vector3[0];
        Vector3[] previous = new Vector3[0];
        Quaternion[] restLocal = new Quaternion[0];
        Quaternion[] written = new Quaternion[0];
        float[] lengths = new float[0];

        void OnEnable() => Setup();

        void LateUpdate() => Step(Time.deltaTime);

        /// <summary>Start again from the current pose, without sway.</summary>
        public void Setup()
        {
            var n = bones.Length;
            current = new Vector3[n];
            previous = new Vector3[n];
            restLocal = new Quaternion[n];
            written = new Quaternion[n];
            lengths = new float[n];
            for (var i = 0; i < n; i++)
            {
                var bone = bones[i];
                if (bone == null) continue;
                restLocal[i] = bone.localRotation;
                written[i] = bone.localRotation;
                lengths[i] = i + 1 < n && bones[i + 1] != null
                    ? Vector3.Distance(bone.position, bones[i + 1].position)
                    : lastLength * bone.lossyScale.y;
                current[i] = previous[i] = bone.position + bone.rotation * Vector3.up * lengths[i];
            }
        }

        public Vector3 Tail(int i) => current[i];

        /// <summary>One step of `dt` seconds.</summary>
        public void Step(float dt)
        {
            if (current.Length != bones.Length) Setup();
            for (var i = 0; i < bones.Length; i++)
            {
                var bone = bones[i];
                if (bone == null) continue;
                // A bone the animation did not touch still has the rotation written last step: its pose is the rest.
                var local = Quaternion.Angle(bone.localRotation, written[i]) < 1e-3f ? restLocal[i] : bone.localRotation;
                var parent = bone.parent != null ? bone.parent.rotation : Quaternion.identity;
                var posed = parent * local;
                var rest = posed * Vector3.up;
                var head = bone.position;
                var tail = current[i] + (current[i] - previous[i]) * (1f - drag) + rest * (stiffness * dt)
                           + Vector3.down * (gravity * dt);
                tail = head + (tail - head).normalized * lengths[i];
                foreach (var collider in colliders)
                {
                    if (collider == null) continue;
                    tail = PushOut(tail, collider.Head, collider.Tail, collider.Radius + radius);
                    tail = head + (tail - head).normalized * lengths[i];
                }
                previous[i] = current[i];
                current[i] = tail;
                bone.rotation = Quaternion.FromToRotation(rest, (tail - head).normalized) * posed;
                written[i] = bone.localRotation;
            }
        }

        static Vector3 PushOut(Vector3 point, Vector3 a, Vector3 b, float distance)
        {
            var axis = b - a;
            var length2 = axis.sqrMagnitude;
            var t = length2 < 1e-12f ? 0f : Mathf.Clamp01(Vector3.Dot(point - a, axis) / length2);
            var closest = a + axis * t;
            var away = point - closest;
            var gap = away.magnitude;
            if (gap >= distance || gap < 1e-9f) return point;
            return closest + away / gap * distance;
        }
    }
}
```

**File `scripts/modules/dasktoon_export/unity_scripts/Editor/DaskToonRigImporter.cs`:**
```csharp
// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Written by DaskToon's Engine Export; exporting again replaces it.

using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace DaskToon.Editor
{
    /// <summary>When Unity imports a model with a DaskToon <model>.rig.json beside it, adds a DaskToonSpringBone for
    /// each chain that sways at run time and a DaskToonSpringCollider on each collider bone (anime rig spec 9.5).</summary>
    public class DaskToonRigImporter : AssetPostprocessor
    {
        [Serializable]
        class ChainData
        {
            public string part;
            public string[] bones;
            public float[] lengths;
            public float stiffness;
            public float gravity;
            public float drag;
            public float radius;
            public string unity;
        }

        [Serializable]
        class ColliderData
        {
            public string bone;
            public float radius;
            public float length;
        }

        [Serializable]
        class RigData
        {
            public int version;
            public ChainData[] chains;
            public ColliderData[] colliders;
        }

        public static string RigPath(string modelPath) => Path.ChangeExtension(modelPath, ".rig.json");

        void OnPostprocessModel(GameObject root)
        {
            var path = RigPath(assetPath).Replace('\\', '/');
            context.DependsOnSourceAsset(path);
            if (!File.Exists(path)) return;
            var data = JsonUtility.FromJson<RigData>(File.ReadAllText(path));
            if (data == null || data.version != 1)
            {
                Debug.LogWarning("DaskToon: " + path + " is not a rig file this version understands");
                return;
            }
            var byName = new Dictionary<string, Transform>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                if (!byName.ContainsKey(t.name)) byName[t.name] = t;
            }
            var colliders = new List<DaskToonSpringCollider>();
            foreach (var c in data.colliders ?? new ColliderData[0])
            {
                if (!byName.TryGetValue(c.bone, out var bone)) continue;
                var collider = bone.gameObject.AddComponent<DaskToonSpringCollider>();
                collider.radius = c.radius;
                collider.length = c.length;
                colliders.Add(collider);
            }
            foreach (var chain in data.chains ?? new ChainData[0])
            {
                if (chain.unity == "baked" || chain.bones == null) continue;
                var bones = new List<Transform>();
                foreach (var name in chain.bones)
                {
                    if (byName.TryGetValue(name, out var bone)) bones.Add(bone);
                }
                if (bones.Count == 0) continue;
                var spring = root.AddComponent<DaskToonSpringBone>();
                spring.bones = bones.ToArray();
                spring.lastLength = chain.lengths != null && chain.lengths.Length > 0
                    ? chain.lengths[chain.lengths.Length - 1] : 0.1f;
                spring.stiffness = chain.stiffness;
                spring.gravity = chain.gravity;
                spring.drag = chain.drag;
                spring.radius = chain.radius;
                spring.colliders = colliders.ToArray();
            }
        }
    }
}
```

- [ ] **Step 4: Đăng ký** — `TRANSLATED` += `"scripts/modules/dasktoon_export/scripts_install.py"`.
- [ ] **Step 5: Chạy, thấy PASS** — `rt.sh dasktoon_export_rig_test dasktoon_export_shaders_test dasktoon_translations_test`.
  (Bản cài: `tools/dasktoon_sync_build.py` chép cả `unity_scripts/*.cs` vì nó chép cả thư mục `scripts/modules`.)
- [ ] **Step 6: Commit** — `feat: Unity spring bone, collider and rig importer scripts, installed with fixed GUIDs`.

---

### Task 4: Engine Export ghi rig cho Unity

**Files:**
- Modify: `scripts/modules/dasktoon_export/__init__.py` (`_write_model`), `scripts/modules/dasktoon_export/report.py`
  (`Report.rig`, `Report.scripts`, dòng báo cáo), `dasktoon_translations.py`
- Test: `tests/python/dasktoon_export_rig_test.py` (`ExportRigTest`)

**Interfaces:**
- Consumes: `rig_json.*`, `scripts_install.install_scripts`, `sway.suppressed`, `sway.remove_rotation_keys`... (đọc key
  qua channelbag như `sway`).
- Produces: `Report.rig` (đường dẫn json tương đối, rỗng nếu không có), `Report.scripts` ('INSTALLED' | 'UP_TO_DATE' |
  'SKIPPED'); `dasktoon_export._keyed_runtime_parts(rig) -> list[str]`.

- [ ] **Step 1: Test** — thêm vào `dasktoon_export_rig_test.py`:
```python
def export(rig, objs, folder=None):
    import dasktoon_export
    from dasktoon_export import targets
    target = targets.make_target(folder or tempfile.mkdtemp(prefix="dt_rig_export_"), "Hero")
    options = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)
    return target, dasktoon_export.export_model(bpy.context, target, [rig] + list(objs.values()), options)


class ExportRigTest(unittest.TestCase):
    def test_export_writes_rig_json_and_scripts(self):
        from dasktoon_export import scripts_install as si
        rig, objs = built()
        target, rep = export(rig, objs)
        self.assertEqual(rep.rig, "Hero/Model/Hero.rig.json")
        self.assertEqual(rep.scripts, 'INSTALLED')
        path = os.path.join(target.root, "Hero", "Model", "Hero.rig.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["chains"]), 9)
        self.assertTrue(os.path.isfile(path + ".meta"))
        self.assertTrue(os.path.isfile(os.path.join(target.root, si.SCRIPT_DIR, "DaskToonSpringBone.cs")))
        self.assertIn("Hero/Model/Hero.rig.json", "\n".join(rep.lines()))

    def test_no_chains_no_rig_files(self):
        rig, objs = built(roles=(("Body", 'BODY'),))
        target, rep = export(rig, {"Body": objs["Body"]})
        self.assertEqual(rep.rig, "")
        self.assertEqual(rep.scripts, 'SKIPPED')
        self.assertFalse(os.path.exists(os.path.join(target.root, "Hero", "Model", "Hero.rig.json")))
        self.assertFalse(os.path.exists(os.path.join(target.root, "Scripts")))

    def test_runtime_chains_rest_while_the_fbx_is_written(self):
        import dasktoon_export
        from dasktoon_export import model_fbx
        rig, objs = built()
        rig.data.dasktoon_rig.parts["Hair"].sway_in_unity = 'BAKED'
        scene = bpy.context.scene
        hips = rig.pose.bones["Hips"]
        for frame, x in ((1, 0.0), (6, 0.3)):
            hips.location = (x, 0.0, 0.0)
            hips.keyframe_insert("location", frame=frame)
        for frame in range(1, 9):
            scene.frame_set(frame)
        seen = {}
        original = model_fbx.write_fbx

        def spy(context, objects, filepath, include_animation):
            seen["skirt"] = tuple(rig.pose.bones["Skirt1_3"].rotation_quaternion)
            seen["hair"] = tuple(rig.pose.bones["Hair_4"].rotation_quaternion)
            return original(context, objects, filepath, include_animation)

        model_fbx.write_fbx = spy
        try:
            export(rig, objs)
        finally:
            model_fbx.write_fbx = original
        self.assertAlmostEqual(abs(seen["skirt"][0]), 1.0, places=6)   # Runtime: at rest in the FBX
        self.assertLess(abs(seen["hair"][0]), 0.9999)                  # Baked: keeps its sway
        self.assertLess(abs(rig.pose.bones["Skirt1_3"].rotation_quaternion[0]), 0.9999)  # back afterwards

    def test_runtime_chain_with_keys_warns(self):
        from dasktoon_rig import sway
        rig, objs = built()
        scene = bpy.context.scene
        scene.frame_start, scene.frame_end = 1, 3
        sway.bake(bpy.context, rig, 1, 3)
        _target, rep = export(rig, objs)
        self.assertTrue(any("Skirt" in w and "twice" in w for w in rep.warnings), rep.warnings)
        self.assertTrue(any("Hair" in w and "twice" in w for w in rep.warnings), rep.warnings)
```

- [ ] **Step 2: Chạy, thấy FAIL** — `AttributeError: 'Report' object has no attribute 'rig'`.

- [ ] **Step 3: Code**

`report.py`:
```python
SCRIPT_STATE = {
    'INSTALLED': n_("Scripts: installed or updated"),
    'UP_TO_DATE': n_("Scripts: the project already has a recent enough version, not written again"),
    'SKIPPED': n_("Scripts: not needed (no hair or skirt chains)"),
}
```
  `Report` thêm `rig: str = ""`, `scripts: str = 'SKIPPED'`; `lines()` sau dòng Model:
```python
        if self.rig:
            out.append(rpt_("Rig: %s (DaskToon spring bones sway the hair and skirts in Unity)") % self.rig)
            out.append(rpt_(SCRIPT_STATE[self.scripts]))
```

`dasktoon_export/__init__.py`:
```python
def _keyed_runtime_parts(rig):
    """Parts that sway at run time in Unity but whose chain bones have rotation keys (from Bake Sway): Unity would sway
    them twice."""
    from bpy_extras import anim_utils
    from dasktoon_rig import sway
    from . import rig_json
    anim = rig.animation_data
    if anim is None or anim.action is None:
        return []
    channelbag = anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot)
    if channelbag is None:
        return []
    keyed = {curve.data_path for curve in channelbag.fcurves}
    runtime = rig_json.runtime_parts(rig)
    out = []
    for part, names in sway.chains(rig):
        if part in runtime and part not in out and any(
                'pose.bones["%s"].%s' % (bpy.utils.escape_identifier(name), prop) in keyed
                for name in names for prop in sway.ROTATION_PATHS):
            out.append(part)
    return out
```
  trong `_write_model`, nhánh `if options.model_format == 'FBX':` — trước khi tạo `meta` của FBX:
```python
        rig = rig_json.find_rig(objects)
        data = rig_json.rig_data(rig) if rig is not None else None
        if data is not None:
            rig_rel = "%s/%s.rig.json" % (model_dir, safe_name(target.name))
            rig_guid = writer.guid(rig_rel)
            if assets.write_asset(target.root, rig_rel, rig_guid, unity_yaml.text_meta(rig_guid), rep.warnings,
                                  data=rig_json.text(data).encode("utf-8")):
                rep.rig = rig_rel
            rep.scripts = 'INSTALLED' if scripts_install.install_scripts(target, rep.warnings) else 'UP_TO_DATE'
            for part in _keyed_runtime_parts(rig):
                rep.warnings.append(rpt_("Part %s sways in Unity, but its bones have sway keys: Unity would sway it "
                                         "twice. Set Sway in Unity to Baked, or remove the keys") % part)
```
  và ghi FBX trong `sway.suppressed(rig, rig_json.runtime_parts(rig))` khi `data is not None` (dùng
  `contextlib.nullcontext()` khi không có): thay
```python
        if assets.write_asset(target.root, rel, guid, meta, rep.warnings, writer=write_fbx):
            rep.model = rel
```
  bằng
```python
        quiet = sway.suppressed(rig, rig_json.runtime_parts(rig)) if data is not None else contextlib.nullcontext()
        with quiet:
            if assets.write_asset(target.root, rel, guid, meta, rep.warnings, writer=write_fbx):
                rep.model = rel
```
  (import `contextlib`; `from . import rig_json, scripts_install`; `from dasktoon_rig import sway` trong hàm.)
  `write_fbx` của test gọi qua `model_fbx.write_fbx(...)` (tra lúc chạy), nên spy trong test thay được.

- [ ] **Step 4: Bản dịch**: ba câu `SCRIPT_STATE`, "Rig: %s (DaskToon spring bones sway the hair and skirts in Unity)",
  "Part %s sways in Unity, but its bones have sway keys: Unity would sway it twice. Set Sway in Unity to Baked, or remove
  the keys".
- [ ] **Step 5: Chạy, thấy PASS** — `rt.sh dasktoon_export_rig_test dasktoon_export_fbx_test dasktoon_export_layout_test dasktoon_engine_export_ui_test dasktoon_rig_build_test dasktoon_translations_test`.
- [ ] **Step 6: Commit** — `feat: Engine Export writes the rig file and the Unity scripts; runtime chains rest in the FBX`.

---

### Task 5: Kiểm trong Unity thật

**Files:**
- Create: `tests/unity/Editor/DaskToonRigTests.cs`, `tests/python/dasktoon_unity_rig_test.py` (không vào CMake, như các
  test Unity khác)

- [ ] **Step 1: Test C#**

**File `tests/unity/Editor/DaskToonRigTests.cs`:**
```csharp
// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Checks the anime rig in Unity: the importer added DaskToon spring bones and colliders from <model>.rig.json, chain
// bones sit along their parent's +Y, and 20 steps of the C# spring bone land where DaskToon's spring.py does.
// The DaskToon scripts are reached by reflection, so this file compiles before any export installed them.

using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

[Serializable]
public class DtRigArgs
{
    public string model;
    public string chainRoot;
    public int steps;
    public float dt;
    public float[] expected;
}

public static class DaskToonRigTests
{
    public static void CheckRig() => DaskToonTests.Run(() =>
    {
        var args = JsonUtility.FromJson<DtRigArgs>(File.ReadAllText(DaskToonTests.ArgsPath));
        AssetDatabase.Refresh();
        var result = new Dictionary<string, object>();
        var springType = Type.GetType("DaskToon.DaskToonSpringBone, Assembly-CSharp");
        var colliderType = Type.GetType("DaskToon.DaskToonSpringCollider, Assembly-CSharp");
        result["scripts"] = springType != null && colliderType != null;
        if (springType == null || colliderType == null) return result;
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(args.model);
        result["imported"] = prefab != null;
        if (prefab == null) return result;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        var springs = go.GetComponents(springType);
        result["springs"] = springs.Length;
        result["colliders"] = go.GetComponentsInChildren(colliderType, true).Length;
        var bonesField = springType.GetField("bones");
        Component chain = null;
        foreach (var s in springs)
        {
            var bones = (Transform[])bonesField.GetValue(s);
            if (bones.Length > 0 && bones[0].name == args.chainRoot) chain = s;
        }
        result["chainFound"] = chain != null;
        if (chain == null) return result;
        var chainBones = (Transform[])bonesField.GetValue(chain);
        var offAxis = 0f;
        for (var i = 0; i + 1 < chainBones.Length; i++)
        {
            var local = chainBones[i + 1].localPosition;
            offAxis = Mathf.Max(offAxis, new Vector2(local.x, local.z).magnitude);
        }
        result["offAxis"] = offAxis;
        springType.GetMethod("Setup").Invoke(chain, null);
        var step = springType.GetMethod("Step");
        for (var k = 0; k < args.steps; k++) step.Invoke(chain, new object[] { args.dt });
        var tail = springType.GetMethod("Tail");
        var maxError = 0f;
        for (var i = 0; i < chainBones.Length; i++)
        {
            var expected = new Vector3(args.expected[3 * i], args.expected[3 * i + 1], args.expected[3 * i + 2]);
            var actual = (Vector3)tail.Invoke(chain, new object[] { i });
            maxError = Mathf.Max(maxError, (actual - expected).magnitude);
        }
        result["maxError"] = maxError;
        UnityEngine.Object.DestroyImmediate(go);
        return result;
    });
}
```

- [ ] **Step 2: Test Python**

**File `tests/python/dasktoon_unity_rig_test.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The anime rig in Unity 6000.5 (spec 9.5): the importer adds the spring bones and colliders from <model>.rig.json, and
20 steps of the C# spring bone match dasktoon_rig/spring.py. Runs Unity in batchmode on the harness's throwaway project."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402
import dasktoon_export  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from dasktoon_export import targets  # noqa: E402
from dasktoon_rig import build, spring, sway  # noqa: E402

STEPS = 20
DT = 1.0 / 30.0


def to_unity(v):
    return [-float(v[0]), float(v[2]), -float(v[1])]


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnityRigTest(unittest.TestCase):
    def test_spring_bones_match_dasktoon(self):
        root = harness.ensure_project()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        rig = fx.rig_for()
        for name, role in (("Body", 'BODY'), ("Hair", 'HAIR'), ("Skirt", 'SKIRT')):
            ui.add_part(rig, objs[name], role)
        build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
        target = targets.make_target(root, "DTRig")
        options = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [rig, objs["Body"], objs["Hair"], objs["Skirt"]],
                                           options)
        self.assertEqual(rep.rig, "DTRig/Model/DTRig.rig.json")
        names = dict(sway.chains(rig))["Hair"]
        pose = sway.chain_pose(rig, names)
        part = rig.data.dasktoon_rig.parts["Hair"]
        params = spring.Params(part.stiffness, part.gravity, part.drag, part.radius)
        state = spring.reset(pose)
        colliders = sway.world_colliders(rig)
        for _ in range(STEPS):
            spring.step(state, pose, params, colliders, DT)
        expected = [c for tail in state.current for c in to_unity(tail)]
        result = harness.run_method("DaskToonRigTests.CheckRig", {
            "model": "Assets/DaskToon/DTRig/Model/DTRig.fbx", "chainRoot": names[0], "steps": STEPS, "dt": DT,
            "expected": expected})
        self.assertTrue(result["ok"], result.get("error"))
        self.assertTrue(result["scripts"])
        self.assertTrue(result["imported"])
        self.assertEqual(result["springs"], 9)
        self.assertEqual(result["colliders"], len(build.COLLIDER_BONES))
        self.assertTrue(result["chainFound"])
        self.assertLess(result["offAxis"], 1e-3)
        self.assertLess(result["maxError"], 2e-3)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 3: Chạy** — `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_unity_rig_test.py`
  (vài phút). Lỗi biên dịch C# hay sai lệch số: sửa theo systematic-debugging, ghi ruling.
- [ ] **Step 4: Commit** — `test: the anime rig's spring bones in Unity match DaskToon's`.

---

### Task 6: Kiểm tra, báo cáo

- [ ] Toàn bộ suite CMake; test Unity rig.
- [ ] Báo cáo: thêm mục R2b (Unity) vào `docs/superpowers/reports/2026-10-06-dasktoon-anime-rig-r1-report.md`.
