# DaskToon: rig anime R2 (lắc trong DaskToon) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao **tự động 3 tiếng** (2026-10-06 16:44); Claude chạy **inline** trên nhánh
> `dasktoon-anime-rig`, sau R1. Không push, không merge.

**Goal:** Tóc và váy do Build Rig sinh ra tự lắc khi phát animation trong DaskToon (spring bone kiểu VRM), không xuyên
qua thân, và bake được thành keyframe.

**Architecture:** `dasktoon_rig/spring.py` là toán numpy thuần (một bước mô phỏng, đặt lại, xoay xương theo đuôi) để
sau này viết lại y hệt bằng C# cho Unity. `dasktoon_rig/sway.py` nối vào Blender: handler `frame_change_pre` đưa xương
chuỗi về tư thế nghỉ trước khi animation chạy, handler `frame_change_post` đọc tư thế đã animate, bước mô phỏng, ghi
góc xoay vào xương; bộ nhớ đệm theo khung; Bake Sway. Build Rig sinh collider dạng capsule dọc các xương thân.
Panel con **Sway** trong Anime Rig.

**Tech Stack:** Python `bpy`, `numpy`, `mathutils`, `bpy_extras.anim_utils` (channelbag của action có slot, Blender 5).

**Spec:** `docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md` §9.1–§9.4

## Global Constraints

- Như R1: chữ tiếng Anh kiểu Blender, có bản Việt; không f-string/cộng chuỗi trong chữ hiển thị; không driver; không
  panel ở thanh bên viewport.
- Thuật toán đúng spec §9.3, bước thời gian cố định `fps_base / fps`.
- Thông số mặc định: Stiffness **1**, Gravity **0,2**, Drag **0,4**, Radius **0,03 m** (spec ghi 2% chiều cao khung;
  ruling: hằng số 0,03 m, gần 2% của nhân vật 1,6 m).
- Không thêm điều khiển chưa có tác dụng: **Sway in Unity** (spec §9.1) và phần Unity (§9.5) để kế hoạch R2b.

## Review Focus

1. **Tua lại, nhảy khung**: về khung đầu thì hết lắc; quay lại khung đã qua thì ra đúng như lần trước. Test Task 3
   (`test_back_to_start_resets`, `test_revisiting_a_frame_gives_the_same_pose`).
2. **Xương chuỗi có keyframe của người dùng**: lắc cộng thêm vào động tác, không chồng lên chính kết quả lắc của khung
   trước. Test Task 3 (`test_keyed_chain_bone_is_the_rest_direction`).
3. **Bake rồi phát lại**: keyframe khớp với lúc xem trực tiếp; Live Sway tắt để không lắc hai lần. Test Task 3
   (`test_bake_matches_live`).
4. **Tắt Live Sway**: xương chuỗi đứng yên, không bị đặt lại. Test Task 3 (`test_live_sway_off_leaves_bones`).
5. **Collider**: đuôi xương không vào sâu hơn bán kính capsule. Test Task 1 (`test_capsule_pushes_the_tail_out`).

---

Môi trường như R1 (`rt.sh` đồng bộ bản cài rồi chạy test).

### Task 1: Bộ giải spring bone (`spring.py`)

**Files:**
- Create: `scripts/modules/dasktoon_rig/spring.py`
- Test: `tests/python/dasktoon_rig_spring_test.py`
- Modify: `tests/python/CMakeLists.txt`, `tests/python/dasktoon_translations_test.py` (`TRANSLATED` += `spring.py`)

**Interfaces:**
- Produces: `GRAVITY_DIR`, `Params(stiffness=1.0, gravity=0.2, drag=0.4, radius=0.03)`, `Pose(root_head, parent_rotation,
  local_rotations, lengths)`, `State(current, previous=None)` (`.copy()`), `from_to(a, b) -> 3x3`, `reset(pose) ->
  State`, `rotations(state, pose) -> [3x3]`, `step(state, pose, params, colliders, dt) -> [3x3]` với `colliders =
  [(head, tail, radius)]` (world).

- [ ] **Step 1: Viết test**

**File `tests/python/dasktoon_rig_spring_test.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Spring bones as plain maths (anime rig spec 9.3): inertia, stiffness, gravity, length, capsule colliders."""

import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import spring  # noqa: E402

# A bone's tail is along its local +Y. This rotation points +Y at +X (a horizontal bone).
TO_X = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])


def chain(count=1, length=0.1, direction=TO_X):
    return spring.Pose(np.zeros(3), direction, [np.eye(3)] * count, [length] * count)


def tail_of(rotation, head, length):
    return head + rotation[:, 1] * length


class SpringTest(unittest.TestCase):
    def test_from_to(self):
        for a, b in [((1, 0, 0), (0, 1, 0)), ((0, 0, 1), (0, 0, -1)), ((1, 0, 0), (1, 0, 0)), ((0.6, 0.8, 0), (0, 0, 1))]:
            a, b = np.array(a, float), np.array(b, float)
            r = spring.from_to(a, b)
            np.testing.assert_allclose(r @ a, b, atol=1e-9)
            np.testing.assert_allclose(r @ r.T, np.eye(3), atol=1e-9)
            self.assertAlmostEqual(np.linalg.det(r), 1.0, places=9)

    def test_reset_hangs_in_the_pose(self):
        pose = chain(2)
        state = spring.reset(pose)
        np.testing.assert_allclose(state.current, [(0.1, 0, 0), (0.2, 0, 0)], atol=1e-12)
        np.testing.assert_allclose(state.previous, state.current)
        rotations = spring.rotations(state, pose)
        np.testing.assert_allclose(rotations[1], TO_X, atol=1e-12)

    def test_gravity_pulls_down_and_keeps_the_length(self):
        pose = chain(2)
        state = spring.reset(pose)
        params = spring.Params(stiffness=0.0, gravity=1.0, drag=0.0, radius=0.0)
        for _ in range(10):
            rotations = spring.step(state, pose, params, [], 1.0 / 24.0)
        self.assertLess(state.current[0][2], -0.01)
        self.assertLess(state.current[1][2], state.current[0][2])
        self.assertAlmostEqual(np.linalg.norm(state.current[0]), 0.1, places=9)
        self.assertAlmostEqual(np.linalg.norm(state.current[1] - state.current[0]), 0.1, places=9)
        np.testing.assert_allclose(tail_of(rotations[0], np.zeros(3), 0.1), state.current[0], atol=1e-9)
        np.testing.assert_allclose(tail_of(rotations[1], state.current[0], 0.1), state.current[1], atol=1e-9)

    def test_stiffness_brings_it_back(self):
        pose = chain(1)
        state = spring.State([(0.0, 0.0, 0.1)])  # pushed up, straight above the head
        params = spring.Params(stiffness=4.0, gravity=0.0, drag=1.0, radius=0.0)
        start = math.acos(state.current[0][0] / 0.1)
        for _ in range(30):
            spring.step(state, pose, params, [], 1.0 / 24.0)
        self.assertLess(math.acos(min(1.0, state.current[0][0] / 0.1)), start / 4)

    def test_drag_one_keeps_no_inertia(self):
        pose = chain(1)
        state = spring.State([(0.1, 0.0, 0.0)], [(0.1, 0.0, -0.05)])  # was moving up fast
        spring.step(state, pose, spring.Params(stiffness=0.0, gravity=0.0, drag=1.0, radius=0.0), [], 1.0 / 24.0)
        np.testing.assert_allclose(state.current[0], (0.1, 0.0, 0.0), atol=1e-12)
        spring.step(state, pose, spring.Params(stiffness=0.0, gravity=0.0, drag=0.0, radius=0.0), [], 1.0 / 24.0)
        np.testing.assert_allclose(state.current[0], (0.1, 0.0, 0.0), atol=1e-12)

    def test_capsule_pushes_the_tail_out(self):
        pose = chain(1)
        state = spring.reset(pose)
        capsule = (np.array((0.1, -1.0, -0.02)), np.array((0.1, 1.0, -0.02)), 0.03)  # under the tail, along Y
        params = spring.Params(stiffness=0.0, gravity=2.0, drag=0.0, radius=0.01)
        for _ in range(20):
            spring.step(state, pose, params, [capsule], 1.0 / 24.0)
        tail = state.current[0]
        distance = math.hypot(tail[0] - 0.1, tail[2] + 0.02)
        self.assertGreaterEqual(distance, 0.04 - 1e-6)
        self.assertAlmostEqual(np.linalg.norm(tail), 0.1, places=9)

    def test_same_input_same_output(self):
        def run():
            pose = chain(3, direction=np.eye(3))
            state = spring.reset(pose)
            moving = spring.Pose(np.array((0.05, 0.0, 0.0)), np.eye(3), [np.eye(3)] * 3, [0.1] * 3)
            out = None
            for _ in range(12):
                out = spring.step(state, moving, spring.Params(), [], 1.0 / 30.0)
            return state.current, out
        a, b = run(), run()
        np.testing.assert_array_equal(a[0], b[0])
        for x, y in zip(a[1], b[1]):
            np.testing.assert_array_equal(x, y)

    def test_copy_is_independent(self):
        state = spring.reset(chain(1))
        other = state.copy()
        other.current[0][2] = 5.0
        self.assertEqual(state.current[0][2], 0.0)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, thấy FAIL** — `cannot import name 'spring'`.

- [ ] **Step 3: Viết code**

**File `scripts/modules/dasktoon_rig/spring.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Spring bones of the anime rig (spec 9.3) as plain numpy maths, so DaskToon and the Unity script share one algorithm
(VRM's spring bone): every bone keeps its tail's current and previous world position; a step adds the inertia, a pull
towards the posed direction and gravity, keeps the bone's length and pushes the tail out of capsule colliders. A bone's
tail is along its local +Y, as in Blender."""

import numpy as np

GRAVITY_DIR = np.array((0.0, 0.0, -1.0))


class Params:
    """How a chain sways: stiffness (pull back to the pose), gravity, drag (1 keeps no inertia) and the radius of each
    tail against colliders."""

    def __init__(self, stiffness=1.0, gravity=0.2, drag=0.4, radius=0.03):
        self.stiffness = stiffness
        self.gravity = gravity
        self.drag = drag
        self.radius = radius


class Pose:
    """A chain as animated, without sway: world head of its first bone, world rotation (3x3) of the bone it hangs from,
    each bone's rotation relative to the one before (3x3) and each bone's length."""

    def __init__(self, root_head, parent_rotation, local_rotations, lengths):
        self.root_head = np.asarray(root_head, float)
        self.parent_rotation = np.asarray(parent_rotation, float)
        self.local_rotations = [np.asarray(r, float) for r in local_rotations]
        self.lengths = [float(length) for length in lengths]


class State:
    """Current and previous world position of every tail of a chain."""

    def __init__(self, current, previous=None):
        self.current = np.array(current, float)
        self.previous = np.array(current if previous is None else previous, float)

    def copy(self):
        return State(self.current.copy(), self.previous.copy())


def _unit(vector):
    length = float(np.linalg.norm(vector))
    return vector / length if length > 1e-12 else vector


def from_to(a, b):
    """The rotation (3x3) taking unit vector a to unit vector b along the shortest arc."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    cross = np.cross(a, b)
    cosine = float(a @ b)
    if cosine < -1.0 + 1e-9:
        axis = _unit(np.cross(a, (1.0, 0.0, 0.0)) if abs(a[0]) < 0.9 else np.cross(a, (0.0, 1.0, 0.0)))
        return 2.0 * np.outer(axis, axis) - np.eye(3)
    k = np.array([[0.0, -cross[2], cross[1]], [cross[2], 0.0, -cross[0]], [-cross[1], cross[0], 0.0]])
    return np.eye(3) + k + k @ k / (1.0 + cosine)


def reset(pose):
    """The state of a chain hanging in its pose, without sway."""
    tails = []
    head, parent = pose.root_head, pose.parent_rotation
    for local, length in zip(pose.local_rotations, pose.lengths):
        rotation = parent @ local
        head = head + rotation[:, 1] * length
        tails.append(head)
        parent = rotation
    return State(tails)


def rotations(state, pose):
    """World rotations (3x3) that point every bone of the chain at its tail in `state`, without a step."""
    out = []
    head, parent = pose.root_head, pose.parent_rotation
    for i, (local, length) in enumerate(zip(pose.local_rotations, pose.lengths)):
        posed = parent @ local
        rotation = from_to(posed[:, 1], _unit(state.current[i] - head)) @ posed
        out.append(rotation)
        head, parent = head + rotation[:, 1] * length, rotation
    return out


def _push_out(point, a, b, distance):
    """`point` moved out of the capsule of radius `distance` around the segment a-b, if it is inside."""
    axis = b - a
    length2 = float(axis @ axis)
    t = 0.0 if length2 < 1e-18 else min(1.0, max(0.0, float((point - a) @ axis) / length2))
    closest = a + axis * t
    away = point - closest
    gap = float(np.linalg.norm(away))
    if gap >= distance or gap < 1e-12:
        return point
    return closest + away / gap * distance


def step(state, pose, params, colliders, dt):
    """One step of `dt` seconds (spec 9.3): updates `state` and returns the bones' world rotations (3x3).
    `colliders` is a list of (head, tail, radius) capsules in world space."""
    out = []
    head, parent = pose.root_head, pose.parent_rotation
    for i, (local, length) in enumerate(zip(pose.local_rotations, pose.lengths)):
        posed = parent @ local
        rest = posed[:, 1]
        current = state.current[i].copy()
        tail = (current + (current - state.previous[i]) * (1.0 - params.drag) + rest * (params.stiffness * dt)
                + GRAVITY_DIR * (params.gravity * dt))
        tail = head + _unit(tail - head) * length
        for a, b, radius in colliders:
            tail = _push_out(tail, np.asarray(a, float), np.asarray(b, float), radius + params.radius)
            tail = head + _unit(tail - head) * length
        state.previous[i] = current
        state.current[i] = tail
        rotation = from_to(rest, _unit(tail - head)) @ posed
        out.append(rotation)
        head, parent = tail, rotation
    return out
```

- [ ] **Step 4: Đăng ký** — CMake `dasktoon_rig_spring_test`; `TRANSLATED` += `"scripts/modules/dasktoon_rig/spring.py"`.
- [ ] **Step 5: Chạy, thấy PASS** — `rt.sh dasktoon_rig_spring_test dasktoon_translations_test`.
- [ ] **Step 6: Commit** — `feat: spring bone solver for the anime rig`.

---

### Task 2: Thông số lắc, collider khi Build

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_rig.py` (thông số lắc trên `DaskRigPart`; `DaskRigCollider`; `DaskRig.colliders`,
  `active_collider_index`, `live_sway`), `scripts/modules/dasktoon_rig/parts.py` (`Part` có thông số lắc),
  `scripts/modules/dasktoon_rig/build.py` (`COLLIDER_BONES`, `colliders()` ghi vào `rig.data.dasktoon_rig.colliders`),
  `scripts/startup/bl_ui/dasktoon_translations.py`
- Test: `tests/python/dasktoon_rig_build_test.py` (`ColliderTest`)

**Interfaces:**
- Consumes: `weights.read`, `parts.bone_segment`, `chains.segment_distance`.
- Produces: `DaskRigPart.stiffness/gravity/drag/radius`, `DaskRigCollider.bone/radius`, `DaskRig.colliders`,
  `DaskRig.live_sway`; `parts.Part(..., stiffness=1.0, gravity=0.2, drag=0.4, radius=0.03)`;
  `build.COLLIDER_BONES`, `build.collider_radii(rig, parts, owners) -> [(bone, radius)]`; `Result.colliders`.
  Sửa thông số lắc hoặc collider gọi `sway.clear_cache()` (Task 3) — ở Task 2 hàm cập nhật gọi qua
  `_sway_changed`, Task 3 điền thân hàm.

- [ ] **Step 1: Viết test** — thêm vào `dasktoon_rig_build_test.py`:
```python
class ColliderTest(unittest.TestCase):
    def test_build_makes_body_colliders(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        rig = fx.rig_for()
        result = build.build(bpy.context, rig, separate_parts(objs))
        colliders = {c.bone: c.radius for c in rig.data.dasktoon_rig.colliders}
        self.assertEqual(set(colliders), set(build.COLLIDER_BONES))
        self.assertEqual([name for name, _radius in result.colliders], list(colliders))
        np.testing.assert_allclose([radius for _name, radius in result.colliders], list(colliders.values()), rtol=1e-6)
        body_radius = 0.07 * fx.HEIGHT
        self.assertTrue(0.3 * body_radius < colliders["Chest"] < body_radius, colliders["Chest"])
        self.assertTrue(all(r > 0.0 for r in colliders.values()))
        build.build(bpy.context, rig, separate_parts(objs))
        self.assertEqual(len(rig.data.dasktoon_rig.colliders), len(build.COLLIDER_BONES))

    def test_part_sway_defaults(self):
        part = parts.Part("Hair", None, 'HAIR')
        self.assertEqual((part.stiffness, part.gravity, part.drag, part.radius), (1.0, 0.2, 0.4, 0.03))
```

- [ ] **Step 2: Chạy, thấy FAIL** — `AttributeError: ... 'colliders'`.

- [ ] **Step 3: Viết code**

`parts.Part.__init__`: thêm tham số `stiffness=1.0, gravity=0.2, drag=0.4, radius=0.03` và gán thành thuộc tính.

`bl_ui/dasktoon_rig.py`, trước `class DaskRigPart`:
```python
def _sway_changed(_self, _context):
    from dasktoon_rig import sway
    sway.clear_cache()
```
thêm vào `DaskRigPart`:
```python
    stiffness: FloatProperty(name="Stiffness", description="How strongly the chain springs back to its pose",
                             default=1.0, min=0.0, max=4.0, update=_sway_changed)
    gravity: FloatProperty(name="Gravity", description="How strongly the chain is pulled down", default=0.2, min=0.0,
                           max=2.0, update=_sway_changed)
    drag: FloatProperty(name="Drag", description="How quickly the swing dies down: 0 keeps swinging, 1 stops at once",
                        default=0.4, min=0.0, max=1.0, update=_sway_changed)
    radius: FloatProperty(name="Radius", description="How far each joint keeps from the colliders", default=0.03,
                          min=0.0, max=1.0, unit='LENGTH', update=_sway_changed)
```
lớp mới trước `DaskRig`:
```python
class DaskRigCollider(PropertyGroup):
    """A capsule along a bone that hair and skirts do not go through"""
    bone: StringProperty(name="Bone", description="Bone the capsule runs along, from its head to its tail")
    radius: FloatProperty(name="Radius", description="Radius of the capsule", default=0.05, min=0.0, unit='LENGTH',
                          update=_sway_changed)
```
thêm vào `DaskRig`:
```python
    colliders: CollectionProperty(type=DaskRigCollider, name="Colliders",
                                  description="Capsules that hair and skirts do not go through; Build Rig makes them")
    live_sway: BoolProperty(name="Live Sway", description="Sway hair and skirts while the animation plays",
                            default=True, update=_sway_changed)
```
(`BoolProperty`, `FloatProperty` thêm vào import; `DaskRigCollider` vào `classes` trước `DaskRig`.)

`build.py`:
```python
COLLIDER_BONES = ("Head", "Neck", "UpperChest", "Chest", "Spine", "Hips", "LeftUpperArm", "RightUpperArm",
                  "LeftLowerArm", "RightLowerArm", "LeftUpperLeg", "RightUpperLeg", "LeftLowerLeg", "RightLowerLeg")
COLLIDER_SHARE = 0.9
COLLIDER_FALLBACK = 0.03  # of the skeleton's height, for a bone no Body vertex follows


def collider_radii(rig, parts, owners):
    """[(bone, world radius)] of a capsule along each COLLIDER_BONES bone of the rig (spec 9.2): COLLIDER_SHARE of the
    mean distance from the bone to the Body vertices whose largest weight is that bone."""
    names = [n for n in COLLIDER_BONES if rig.data.bones.get(n) is not None]
    body_ids = [i for i, part in enumerate(parts) if part.role == 'BODY']
    distances = {name: [] for name in names}
    for obj, owner in owners.items():
        vertices = np.nonzero(np.isin(owner, body_ids))[0]
        if len(vertices) == 0:
            continue
        world, _edges = rig_parts.mesh_arrays(obj)
        deform = [b.name for b in rig.data.bones if b.use_deform]
        matrix = weights.read(obj, deform)[vertices]
        dominant = np.array(deform)[matrix.argmax(axis=1)]
        has = matrix.max(axis=1) > 0.0
        for name in names:
            mine = vertices[(dominant == name) & has]
            if len(mine):
                distances[name].append(chains.segment_distance(world[mine], *rig_parts.bone_segment(rig, name)))
    heads = [rig.matrix_world @ b.head_local for b in rig.data.bones]
    tails = [rig.matrix_world @ b.tail_local for b in rig.data.bones]
    height = max(p.z for p in heads + tails) - min(p.z for p in heads + tails)
    out = []
    for name in names:
        found = np.concatenate(distances[name]) if distances[name] else np.zeros(0)
        out.append((name, float(found.mean()) * COLLIDER_SHARE if len(found) else COLLIDER_FALLBACK * height))
    return out


def _write_colliders(rig, radii):
    data = getattr(rig.data, "dasktoon_rig", None)
    if data is None:
        return
    data.colliders.clear()
    for name, radius in radii:
        item = data.colliders.add()
        item.bone = name
        item.radius = radius
```
`Result.__init__` thêm `self.colliders = []`; trong `build()` sau `_tidy(rig, owners)`:
```python
        result.colliders = collider_radii(rig, parts, owners)
        _write_colliders(rig, result.colliders)
```

- [ ] **Step 4: Bản dịch** (VI): "Stiffness" (Blender có), "How strongly the chain springs back to its pose", "Gravity"
  (Blender có), "How strongly the chain is pulled down", "Drag" (Blender có), "How quickly the swing dies down: 0 keeps
  swinging, 1 stops at once", "How far each joint keeps from the colliders", "A capsule along a bone that hair and skirts
  do not go through", "Bone the capsule runs along, from its head to its tail", "Radius of the capsule", "Colliders",
  "Capsules that hair and skirts do not go through; Build Rig makes them", "Live Sway", "Sway hair and skirts while the
  animation plays".
- [ ] **Step 5: `sway.py` tối thiểu** (Task 3 viết đầy đủ), để `_sway_changed` có chỗ gọi:
```python
"""Live sway of the generated chains (anime rig spec 9.4); Task 3 fills it in."""

_cache = {}


def clear_cache(rig=None):
    if rig is None:
        _cache.clear()
    else:
        _cache.pop(rig.session_uid, None)
```
- [ ] **Step 6: Chạy, thấy PASS** — `rt.sh dasktoon_rig_build_test dasktoon_rig_ui_test dasktoon_translations_test`.
- [ ] **Step 7: Commit** — `feat: sway settings on rig parts and body colliders from Build Rig`.

---

### Task 3: Lắc trực tiếp và Bake (`sway.py`)

**Files:**
- Create: `scripts/modules/dasktoon_rig/sway.py`
- Modify: `scripts/startup/bl_ui/dasktoon_rig.py` (`register()` thêm handler, `unregister()` gỡ), `build.py`
  (`build()` gọi `sway.clear_cache(rig)` ở cuối)
- Test: `tests/python/dasktoon_rig_sway_test.py`
- Modify: CMake, `TRANSLATED` += `sway.py`

**Interfaces:**
- Consumes: `spring.*`, `build.MARK`, `DaskRig.live_sway/colliders`, `DaskRigPart.stiffness/...`.
- Produces: `sway.chains(rig) -> [(part name, [bone names])]`, `sway.chain_pose(rig, names) -> spring.Pose`,
  `sway.apply(rig, names, world_rotations)`, `sway.clear_cache(rig=None)`, `sway.sway(rig, scene)`, handlers
  `sway.frame_pre(scene, depsgraph=None)`, `sway.frame_post(scene, depsgraph=None)`, `sway.depsgraph_post(scene,
  depsgraph)`, `sway.remove_rotation_keys(rig, names)`, `sway.bake(context, rig, frame_start, frame_end) -> (frames,
  bones)`.

- [ ] **Step 1: Viết test**

**File `tests/python/dasktoon_rig_sway_test.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Live sway and Bake Sway on the test character (anime rig spec 9.4)."""

import os
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_rig_fixtures as fx  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_rig as ui  # noqa: E402
from dasktoon_rig import build, parts, sway  # noqa: E402

BONE = "Skirt1_3"


def character():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = fx.character()
    rig = fx.rig_for()
    for obj, role in (("Body", 'BODY'), ("Shirt", 'CLOTHING'), ("Hair", 'HAIR'), ("Skirt", 'SKIRT')):
        ui.add_part(rig, objs[obj], role)
    build.build(bpy.context, rig, list(rig.data.dasktoon_rig.parts))
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 20
    hips = rig.pose.bones["Hips"]
    for frame, x in ((1, 0.0), (6, 0.3), (12, 0.3)):  # the hips dash sideways, then stop
        hips.location = (x, 0.0, 0.0)
        hips.keyframe_insert("location", frame=frame)
    scene.frame_set(1)
    return rig


def quat(rig, name):
    return np.array(rig.pose.bones[name].rotation_quaternion)


def play(rig, last):
    out = {}
    for frame in range(1, last + 1):
        bpy.context.scene.frame_set(frame)
        out[frame] = quat(rig, BONE)
    return out


class SwayTest(unittest.TestCase):
    def setUp(self):
        self.rig = character()

    def test_chains(self):
        found = dict((names[0], (part, names)) for part, names in sway.chains(self.rig))
        self.assertEqual(found["Hair_1"], ("Hair", ["Hair_1", "Hair_2", "Hair_3", "Hair_4"]))
        self.assertEqual(found["Skirt1_1"], ("Skirt", ["Skirt1_1", "Skirt1_2", "Skirt1_3"]))
        self.assertEqual(len(found), 9)

    def test_moving_hips_sway_the_skirt(self):
        played = play(self.rig, 12)
        self.assertAlmostEqual(abs(played[1][0]), 1.0, places=6)  # no sway on the first frame
        self.assertLess(abs(played[8][0]), 0.999)

    def test_back_to_start_resets(self):
        play(self.rig, 8)
        bpy.context.scene.frame_set(1)
        self.assertAlmostEqual(abs(quat(self.rig, BONE)[0]), 1.0, places=6)

    def test_revisiting_a_frame_gives_the_same_pose(self):
        played = play(self.rig, 12)
        bpy.context.scene.frame_set(7)
        np.testing.assert_allclose(quat(self.rig, BONE), played[7], atol=1e-9)
        again = play(self.rig, 12)
        np.testing.assert_allclose(again[12], played[12], atol=1e-9)

    def test_tails_follow_the_simulation(self):
        play(self.rig, 9)
        bpy.context.view_layer.update()
        state = sway._cache[self.rig.session_uid][9]
        names = dict(sway.chains(self.rig))["Skirt"]
        index = [n for _p, n in sway.chains(self.rig)].index(names)
        world = self.rig.matrix_world
        for i, name in enumerate(names):
            tail = np.array(world @ self.rig.pose.bones[name].tail)
            np.testing.assert_allclose(tail, state[index].current[i], atol=1e-4)

    def test_live_sway_off_leaves_bones(self):
        self.rig.data.dasktoon_rig.live_sway = False
        pb = self.rig.pose.bones[BONE]
        pb.rotation_quaternion = (0.9, 0.1, 0.0, 0.0)
        play(self.rig, 6)
        np.testing.assert_allclose(quat(self.rig, BONE), (0.9, 0.1, 0.0, 0.0), atol=1e-6)

    def test_keyed_chain_bone_is_the_rest_direction(self):
        pb = self.rig.pose.bones["Hair_1"]
        pb.rotation_quaternion = (0.96592583, 0.25881905, 0.0, 0.0)  # 30 degrees, keyed on every frame
        pb.keyframe_insert("rotation_quaternion", frame=1)
        still = dict(sway.chains(self.rig))
        self.rig.data.dasktoon_rig.parts["Hair"].stiffness = 4.0
        self.rig.data.dasktoon_rig.parts["Hair"].gravity = 0.0
        played = {}
        for frame in range(1, 30):
            bpy.context.scene.frame_set(frame)
            played[frame] = quat(self.rig, "Hair_1")
        # With strong stiffness and no gravity the lock settles on its keyed pose instead of drifting each frame.
        np.testing.assert_allclose(played[29], (0.96592583, 0.25881905, 0.0, 0.0), atol=0.05)
        self.assertIn("Hair", still)

    def test_parameter_change_clears_the_cache(self):
        play(self.rig, 4)
        self.assertTrue(sway._cache.get(self.rig.session_uid))
        self.rig.data.dasktoon_rig.parts["Skirt"].drag = 0.9
        self.assertFalse(sway._cache.get(self.rig.session_uid))

    def test_bake_matches_live(self):
        live = play(self.rig, 12)
        frames, bones = sway.bake(bpy.context, self.rig, 1, 12)
        self.assertEqual((frames, bones), (12, 4 + 8 * 3))
        self.assertFalse(self.rig.data.dasktoon_rig.live_sway)
        for frame in (5, 9, 12):
            bpy.context.scene.frame_set(frame)
            np.testing.assert_allclose(quat(self.rig, BONE), live[frame], atol=1e-5)

    def test_bake_twice_does_not_stack(self):
        sway.bake(bpy.context, self.rig, 1, 12)
        first = {}
        for frame in (6, 12):
            bpy.context.scene.frame_set(frame)
            first[frame] = quat(self.rig, BONE)
        sway.bake(bpy.context, self.rig, 1, 12)
        for frame in (6, 12):
            bpy.context.scene.frame_set(frame)
            np.testing.assert_allclose(quat(self.rig, BONE), first[frame], atol=1e-5)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, thấy FAIL** — `cannot import name 'sway'` (hoặc thiếu hàm nếu Task 2 đã tạo file rỗng).

- [ ] **Step 3: Viết code**

**File `scripts/modules/dasktoon_rig/sway.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Live sway of the generated chains (anime rig spec 9.4). Before the animation of a frame is evaluated, the chain
bones go back to their rest rotation (frame_change_pre), so a key the user set is the chain's pose and an unkeyed bone
is at rest; after it (frame_change_post) the spring solver steps from the previous frame and the bones get the swayed
rotations. States are cached per frame, so going back to a frame shows it again; the first frame of the scene starts
over. Bake Sway keys the result. No drivers: these are DaskToon's own handlers."""

import bpy
import numpy as np
from bpy.app.handlers import persistent
from mathutils import Matrix

from . import build, spring

MAX_CATCH_UP = 300
ROTATION_PATHS = ("rotation_quaternion", "rotation_euler", "rotation_axis_angle")
_cache = {}  # session_uid of the rig → {frame: [spring.State per chain]}


def clear_cache(rig=None):
    if rig is None:
        _cache.clear()
    else:
        _cache.pop(rig.session_uid, None)


def chains(rig):
    """[(part name, [bone names from root to tip])] of the chains Build Rig generated in `rig`."""
    out = []
    for bone in rig.data.bones:
        part = bone.get(build.MARK)
        if part is None or (bone.parent is not None and bone.parent.get(build.MARK) == part):
            continue
        names, current = [bone.name], bone
        while True:
            children = [c for c in current.children if c.get(build.MARK) == part]
            if not children:
                break
            current = children[0]
            names.append(current.name)
        out.append((part, names))
    return out


def _rotation(matrix):
    return np.array(matrix.to_3x3().normalized())


def chain_pose(rig, names):
    """The chain as animated, without sway (spring.Pose), from the current pose of `rig`."""
    world = rig.matrix_world
    bones = [rig.pose.bones[name] for name in names]
    parent = bones[0].parent
    parent_rotation = _rotation(world @ parent.matrix) if parent is not None else _rotation(world)
    rotations = [_rotation(world @ pb.matrix) for pb in bones]
    local, previous = [], parent_rotation
    for rotation in rotations:
        local.append(previous.T @ rotation)
        previous = rotation
    lengths = [(world @ pb.tail - world @ pb.head).length for pb in bones]
    return spring.Pose(np.array(world @ bones[0].head), parent_rotation, local, lengths)


def _set_rotation(pb, matrix):
    q = matrix.to_quaternion()
    if pb.rotation_mode == 'QUATERNION':
        pb.rotation_quaternion = q
    elif pb.rotation_mode == 'AXIS_ANGLE':
        axis, angle = q.to_axis_angle()
        pb.rotation_axis_angle = (angle, axis.x, axis.y, axis.z)
    else:
        pb.rotation_euler = q.to_euler(pb.rotation_mode)


def apply(rig, names, world_rotations):
    """Give the chain bones the rotations that make their world rotations `world_rotations` (3x3 each)."""
    to_rig = _rotation(rig.matrix_world).T
    bones = [rig.pose.bones[name] for name in names]
    parent = bones[0].parent
    parent_pose = _rotation(parent.matrix) if parent is not None else np.eye(3)
    for pb, world_rotation in zip(bones, world_rotations):
        pose = to_rig @ world_rotation
        rest = np.array(pb.bone.matrix_local.to_3x3())
        parent_rest = np.array(pb.parent.bone.matrix_local.to_3x3()) if pb.parent is not None else np.eye(3)
        basis = rest.T @ parent_rest @ parent_pose.T @ pose
        _set_rotation(pb, Matrix(basis.tolist()))
        parent_pose = pose


def _colliders(rig):
    world = rig.matrix_world
    out = []
    for collider in rig.data.dasktoon_rig.colliders:
        pb = rig.pose.bones.get(collider.bone)
        if pb is not None:
            out.append((np.array(world @ pb.head), np.array(world @ pb.tail), collider.radius))
    return out


def _params(rig, part_name):
    part = rig.data.dasktoon_rig.parts.get(part_name)
    if part is None:
        return spring.Params()
    return spring.Params(part.stiffness, part.gravity, part.drag, part.radius)


def _live(rig):
    data = getattr(rig.data, "dasktoon_rig", None)
    return data is not None and data.live_sway


def sway(rig, scene):
    """Sway the chains of `rig` for the scene's current frame."""
    found = chains(rig)
    if not found:
        return
    frame = scene.frame_current
    dt = scene.render.fps_base / scene.render.fps
    store = _cache.setdefault(rig.session_uid, {})
    poses = [chain_pose(rig, names) for _part, names in found]
    shape = [len(names) for _part, names in found]
    if store and [len(s.current) for s in next(iter(store.values()))] != shape:
        store.clear()
    colliders = _colliders(rig)
    if frame in store and frame != scene.frame_start:
        states = [s.copy() for s in store[frame]]
        results = [spring.rotations(state, pose) for state, pose in zip(states, poses)]
    else:
        earlier = [f for f in store if f < frame]
        if frame == scene.frame_start or not earlier or frame - max(earlier) > MAX_CATCH_UP:
            store.clear()
            states = [spring.reset(pose) for pose in poses]
            results = [spring.rotations(state, pose) for state, pose in zip(states, poses)]
        else:
            start = max(earlier)
            states = [s.copy() for s in store[start]]
            for _ in range(frame - start):
                results = [spring.step(state, pose, _params(rig, part), colliders, dt)
                           for state, pose, (part, _names) in zip(states, poses, found)]
        store[frame] = [s.copy() for s in states]
    for (_part, names), rotations in zip(found, results):
        apply(rig, names, rotations)


def _live_rigs(scene):
    return [obj for obj in scene.objects if obj.type == 'ARMATURE' and _live(obj)]


@persistent
def frame_pre(scene, _depsgraph=None):
    identity = Matrix.Identity(3)
    for rig in _live_rigs(scene):
        for _part, names in chains(rig):
            for name in names:
                _set_rotation(rig.pose.bones[name], identity)


@persistent
def frame_post(scene, _depsgraph=None):
    for rig in _live_rigs(scene):
        sway(rig, scene)


@persistent
def depsgraph_post(_scene, depsgraph):
    """Keys edited (an Action updated): the cached sway no longer matches the animation."""
    if any(isinstance(update.id, bpy.types.Action) for update in depsgraph.updates):
        clear_cache()


def remove_rotation_keys(rig, names):
    """Delete the rotation curves of `names` from the action of `rig` (its slot's channels)."""
    from bpy_extras import anim_utils
    anim = rig.animation_data
    if anim is None or anim.action is None:
        return
    channelbag = anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot)
    if channelbag is None:
        return
    paths = {'pose.bones["%s"].%s' % (bpy.utils.escape_identifier(name), prop) for name in names
             for prop in ROTATION_PATHS}
    for curve in list(channelbag.fcurves):
        if curve.data_path in paths:
            channelbag.fcurves.remove(curve)


def _rotation_path(pb):
    if pb.rotation_mode == 'QUATERNION':
        return "rotation_quaternion"
    if pb.rotation_mode == 'AXIS_ANGLE':
        return "rotation_axis_angle"
    return "rotation_euler"


def bake(context, rig, frame_start, frame_end):
    """Key the sway of every chain bone on every frame of the range (spec 9.4): their rotation curves are replaced and
    Live Sway turns off, so the keys play as they are. Returns (frames, bones)."""
    scene = context.scene
    names = [name for _part, chain in chains(rig) for name in chain]
    data = rig.data.dasktoon_rig
    saved = scene.frame_current
    remove_rotation_keys(rig, names)
    data.live_sway = True
    clear_cache(rig)
    values = {}
    for frame in range(frame_start, frame_end + 1):
        scene.frame_set(frame)
        values[frame] = {name: tuple(getattr(rig.pose.bones[name], _rotation_path(rig.pose.bones[name])))
                         for name in names}
    data.live_sway = False
    for frame, rotations in values.items():
        for name, value in rotations.items():
            pb = rig.pose.bones[name]
            path = _rotation_path(pb)
            setattr(pb, path, value)
            pb.keyframe_insert(path, frame=frame, group=name)
    scene.frame_set(saved)
    return frame_end - frame_start + 1, len(names)
```

`bl_ui/dasktoon_rig.py` `register()` thêm (và `unregister()` gỡ tương ứng):
```python
    from dasktoon_rig import sway
    for handlers, function in ((bpy.app.handlers.frame_change_pre, sway.frame_pre),
                               (bpy.app.handlers.frame_change_post, sway.frame_post),
                               (bpy.app.handlers.depsgraph_update_post, sway.depsgraph_post)):
        if function not in handlers:
            handlers.append(function)
```
`build.build()` cuối khối `try`, trước `return result`: `sway.clear_cache(rig)` (import `sway` trong hàm, tránh vòng
import vì `sway` import `build`).

- [ ] **Step 4: Đăng ký** — CMake `dasktoon_rig_sway_test`; `TRANSLATED` += `sway.py`.
- [ ] **Step 5: Chạy, thấy PASS** — `rt.sh dasktoon_rig_sway_test dasktoon_rig_build_test dasktoon_rig_ui_test dasktoon_translations_test`.
- [ ] **Step 6: Commit** — `feat: live sway and Bake Sway for hair and skirt chains`.

---

### Task 4: Panel Sway

**Files:**
- Modify: `scripts/startup/bl_ui/dasktoon_rig.py` (operator `DASKTOON_OT_rig_bake_sway`, panel
  `DATA_PT_dasktoon_rig_sway`), `scripts/startup/bl_ui/dasktoon_translations.py`
- Test: `tests/python/dasktoon_rig_ui_test.py` (`SwayPanelTest`; số operator trong `TextTest` thành 9)

**Interfaces:**
- Consumes: `sway.chains`, `sway.bake`.
- Produces: `dasktoon.rig_bake_sway`, `DATA_PT_dasktoon_rig_sway`.

- [ ] **Step 1: Viết test** — thêm vào `dasktoon_rig_ui_test.py`:
```python
class SwayPanelTest(unittest.TestCase):
    def test_sway_panel_and_bake(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = fx.character()
        rig = fx.rig_for()
        select_only([rig, objs["Body"], objs["Hair"]], rig)
        bpy.ops.dasktoon.rig_add_selected()
        log = tu.draw(ui.DATA_PT_dasktoon_rig_sway, panel_context(rig))
        self.assertIn("Build Rig first to make the hair and skirt chains", tu.labels(log))
        bpy.ops.dasktoon.rig_build()
        rig.data.dasktoon_rig.active_part_index = 1  # Hair
        log = tu.draw(ui.DATA_PT_dasktoon_rig_sway, panel_context(rig))
        props = [entry[1] for entry in log if entry[0] == "prop"]
        self.assertEqual(props[:5], ["live_sway", "stiffness", "gravity", "drag", "radius"])
        self.assertIn("radius", props[5:])
        self.assertIn("dasktoon.rig_bake_sway", [name for name, _text in tu.operators(log)])
        bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 5
        bpy.ops.dasktoon.rig_bake_sway()
        self.assertFalse(rig.data.dasktoon_rig.live_sway)
```
  và trong `TextTest.test_properties_and_enums_are_translated`: `self.assertEqual(len(operators), 9)`; thêm
  `ui.DaskRigCollider` vào danh sách struct.

- [ ] **Step 2: Chạy, thấy FAIL** — `AttributeError: ... DATA_PT_dasktoon_rig_sway`.

- [ ] **Step 3: Viết code** — trong `bl_ui/dasktoon_rig.py`:
```python
class DASKTOON_OT_rig_bake_sway(Operator):
    """Key the sway of hair and skirts on every frame of the scene; Live Sway turns off so the keys play as they are"""
    bl_idname = "dasktoon.rig_bake_sway"
    bl_label = "Bake Sway"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        from dasktoon_rig import sway
        rig = rig_of(context)
        return rig is not None and bool(sway.chains(rig))

    def execute(self, context):
        from dasktoon_rig import sway
        scene = context.scene
        frames, bones = sway.bake(context, rig_of(context), scene.frame_start, scene.frame_end)
        self.report({'INFO'}, rpt_("Baked %d frames of %d bones") % (frames, bones))
        return {'FINISHED'}
```
```python
class DATA_PT_dasktoon_rig_sway(DaskRigPanel, Panel):
    bl_label = "Sway"
    bl_parent_id = "DATA_PT_dasktoon_rig"

    def draw(self, context):
        from dasktoon_rig import sway
        layout = self.layout
        rig = rig_of(context)
        data = rig.data.dasktoon_rig
        if not sway.chains(rig):
            layout.label(text="Build Rig first to make the hair and skirt chains", icon='INFO')
            return
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(data, "live_sway")
        part = _active_part(rig)
        if part is not None and part.role in ('HAIR', 'SKIRT'):
            col = layout.column(align=True)
            col.prop(part, "stiffness")
            col.prop(part, "gravity")
            col.prop(part, "drag")
            col.prop(part, "radius")
        else:
            layout.label(text="Select a hair or skirt part to set how it sways")
        layout.label(text="Colliders")
        for collider in data.colliders:
            row = layout.row()
            row.prop(collider, "radius", text=collider.bone, translate=False)
        layout.operator("dasktoon.rig_bake_sway", icon='REC')
```
  (đăng ký `DASKTOON_OT_rig_bake_sway` trong `classes` cạnh các operator, `DATA_PT_dasktoon_rig_sway` sau
  `DATA_PT_dasktoon_rig_parts`.) Panel Build giữ nguyên.

- [ ] **Step 4: Bản dịch**: "Bake Sway", docstring operator, "Baked %d frames of %d bones", "Sway", "Build Rig first to
  make the hair and skirt chains", "Select a hair or skirt part to set how it sways", "Colliders".
- [ ] **Step 5: Chạy, thấy PASS** — `rt.sh dasktoon_rig_ui_test dasktoon_translations_test dasktoon_ui_layout_test`.
- [ ] **Step 6: Commit** — `feat: Sway panel with Live Sway, chain settings, colliders and Bake Sway`.

---

### Task 5: Kiểm tra, ảnh, báo cáo

- [ ] Chạy toàn bộ suite CMake.
- [ ] Công cụ chụp ảnh: thêm `25_sway` (hông lướt sang, khung giữa: váy và tóc trễ lại) và `26_sway_panel`.
- [ ] Bổ sung báo cáo R1 thành báo cáo R1 + R2 (mục R2), commit.
