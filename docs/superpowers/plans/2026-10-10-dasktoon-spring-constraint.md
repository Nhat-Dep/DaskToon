# DaskToon: constraint Spring (C++) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng giao **tự động** (2026-10-10); Claude chạy **inline** trên nhánh `dasktoon-spring-constraint` (từ
> `dasktoon-master` sau khi merge rig). Không push, không merge.

**Goal:** Lắc của tóc và váy trong DaskToon được tính bằng một loại constraint C++ mới, `SPRING`, ngay lúc Blender tính
khung hình: kéo timeline, render và xuất đều đúng mà không cần handler hay Bake; kết quả khớp `dasktoon_rig/spring.py`.

**Architecture:** DNA `bSpringConstraint` (thông số + danh sách collider dạng `bConstraintTarget`, bán kính ở `weight`).
`constraint.cc` thêm `CTI_SPRING`: tính một bước spring bone mỗi khung, trạng thái lưu trong bộ nhớ đệm toàn cục có khóa
(session UID của object + tên xương → khung → đuôi hiện tại, đuôi trước, đầu vào đã dùng). RNA `SpringConstraint`,
`SpringConstraintCollider`. Python: Build Rig gắn constraint vào xương chuỗi (`sway.sync`), Live Sway = mute, Bake đọc tư
thế đã có lắc; handler Python cũ bị bỏ.

**Tech Stack:** C++ (Blender 5.2: DNA, BKE, RNA, editors), MSBuild/VS 2022, Python `bpy`.

**Spec:** `docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md` §9.2–§9.4 (bản đã sửa 2026-10-10).

## Global Constraints

- Thuật toán đúng spec §9.3, như `spring.py`; trọng lực −Z world; bước `frs_sec_base / frs_sec`.
- Bán kính (khớp và collider) tính theo đơn vị của armature: nhân scale world của object khi tính (sửa lỗi nhỏ "collider
  không theo scale"). `rig.json` ghi bán kính world (nhân scale) cho Unity.
- Đầu vào của một khung đã tính đổi (sửa animation, dời rig) → bỏ lịch sử của xương, bắt đầu lại ở khung đó (sửa lỗi nhỏ
  "dời rig thì giật").
- Không phá file cũ: DaskToon cũ mở file có constraint Spring thì constraint thành loại NULL (đường có sẵn trong đọc file).
- Chữ hiển thị mới (RNA, panel) có bản Việt; không panel ở thanh bên.
- Build: `MSYS_NO_PATHCONV=1 "$MSBUILD" "D:/build_windows_x64_vc17_Release/INSTALL.vcxproj" -p:Configuration=Release -m -v:m -nologo`
  rồi `"$PY" tools/dasktoon_sync_build.py "$INSTALL"`.

## Review Focus

1. **Đọc/ghi file**: constraint và collider còn nguyên sau khi lưu và mở lại; nhân bản xương/object chép cả collider. Test
   Task 1 (`test_save_and_reload_keeps_colliders`, `test_copy_keeps_colliders`).
2. **Khớp bản Python**: chơi tuần tự từng khung, đuôi xương khớp `spring.py` tới 1e-4. Test Task 2 (`test_matches_python`).
3. **Kéo timeline lui/tới, tính lại cùng khung**: kết quả không đổi; về khung đầu là hết lắc. Test Task 2.
4. **Sửa animation sau khi đã chơi**: khung đó bắt đầu lại, không dùng trạng thái cũ. Test Task 2
   (`test_changed_input_starts_again`).
5. **Xuất Unity khi constraint đang chạy**: chuỗi Runtime bị mute trong lúc ghi FBX, chuỗi Baked giữ lắc. Test Task 3.

---

### Task 1: Loại constraint SPRING (dữ liệu, RNA, giao diện), chưa tính

**Files:**
- Modify: `source/blender/makesdna/DNA_constraint_types.h` (enum `CONSTRAINT_TYPE_SPRING = 32`, struct `bSpringConstraint`)
- Modify: `source/blender/blenkernel/intern/constraint.cc` (`CTI_SPRING` với new/free/copy/targets/id_looper, evaluate
  rỗng; bảng type; ghi/đọc target trong blend; `constraint_list_find_from_target`)
- Modify: `source/blender/makesrna/intern/rna_constraint.cc` (mục enum, refine, `SpringConstraint`,
  `SpringConstraintCollider`, `SpringConstraintColliders.new/clear`, đường dẫn collider)
- Modify: `source/blender/editors/object/object_constraint.cc` (không tự thêm target), `source/blender/editors/space_outliner/outliner_draw.cc`
  (icon), `source/blender/animrig/intern/visualkey.cc` (visual keying xoay)
- Modify: `scripts/startup/bl_ui/properties_constraint.py` (panel `OBJECT_PT_bSpringConstraint`, `BONE_PT_bSpringConstraint`
  và panel con collider), `scripts/startup/bl_ui/dasktoon_translations.py`, `tests/python/dasktoon_translations_test.py`
  (`TRANSLATED_CLASSES` thêm các panel mới)
- Test: `tests/python/dasktoon_spring_constraint_test.py` (đăng ký CMake)

**Interfaces:**
- Produces: `pose_bone.constraints.new('SPRING')` → `SpringConstraint` (`stiffness`, `gravity`, `drag`, `radius`,
  `colliders` với `new()`, `clear()`; mỗi collider `target`, `subtarget`, `radius`; `clear_cache()` có ở Task 2).

- [ ] **Step 1: Test**

**File `tests/python/dasktoon_spring_constraint_test.py`:**
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon's Spring constraint (anime rig spec 9.4): the constraint type, its colliders and settings, and how it sways
a bone like dasktoon_rig/spring.py."""

import math
import os
import sys
import tempfile
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_i18n_utils as iu  # noqa: E402
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_translations as dt  # noqa: E402


def chain_rig(count=3):
    """An armature with a body bone "Spine" (up) and a horizontal chain "Tail_1".."Tail_<count>" along +Y from its top."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = bpy.data.armatures.new("Rig")
    rig = bpy.data.objects.new("Rig", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    spine = data.edit_bones.new("Spine")
    spine.head, spine.tail = (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)
    parent = spine
    for k in range(1, count + 1):
        bone = data.edit_bones.new("Tail_%d" % k)
        bone.head = (0.0, 0.1 * (k - 1), 1.0)
        bone.tail = (0.0, 0.1 * k, 1.0)
        bone.parent = parent
        bone.use_connect = k > 1
        parent = bone
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def add_springs(rig, count=3, colliders=()):
    for k in range(1, count + 1):
        con = rig.pose.bones["Tail_%d" % k].constraints.new('SPRING')
        for bone, radius in colliders:
            item = con.colliders.new()
            item.target = rig
            item.subtarget = bone
            item.radius = radius
    return [rig.pose.bones["Tail_%d" % k].constraints[0] for k in range(1, count + 1)]


class TypeTest(unittest.TestCase):
    def test_new_spring_constraint(self):
        rig = chain_rig()
        con = rig.pose.bones["Tail_1"].constraints.new('SPRING')
        self.assertEqual(con.type, 'SPRING')
        self.assertEqual(con.bl_rna.identifier, "SpringConstraint")
        self.assertEqual((con.stiffness, con.gravity, con.drag), (1.0, 0.2, 0.4))
        self.assertAlmostEqual(con.radius, 0.03, places=6)
        self.assertEqual(len(con.colliders), 0)
        item = con.colliders.new()
        self.assertEqual(item.target, rig)
        item.subtarget = "Spine"
        item.radius = 0.25
        self.assertEqual((con.colliders[0].subtarget, round(con.colliders[0].radius, 6)), ("Spine", 0.25))
        self.assertEqual(con.colliders[0].path_from_id(), 'pose.bones["Tail_1"].constraints["Spring"].colliders[0]')
        con.colliders.clear()
        self.assertEqual(len(con.colliders), 0)

    def test_save_and_reload_keeps_colliders(self):
        rig = chain_rig()
        add_springs(rig, 1, [("Spine", 0.2)])
        rig.pose.bones["Tail_1"].constraints[0].stiffness = 2.5
        path = os.path.join(tempfile.mkdtemp(prefix="dt_spring_"), "spring.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        con = bpy.data.objects["Rig"].pose.bones["Tail_1"].constraints[0]
        self.assertEqual(con.type, 'SPRING')
        self.assertAlmostEqual(con.stiffness, 2.5, places=6)
        self.assertEqual([(c.target.name, c.subtarget) for c in con.colliders], [("Rig", "Spine")])
        self.assertAlmostEqual(con.colliders[0].radius, 0.2, places=6)

    def test_copy_keeps_colliders(self):
        rig = chain_rig()
        add_springs(rig, 1, [("Spine", 0.2)])
        copy = rig.copy()
        bpy.context.scene.collection.objects.link(copy)
        con = copy.pose.bones["Tail_1"].constraints[0]
        self.assertEqual([c.subtarget for c in con.colliders], ["Spine"])

    def test_panels_and_texts(self):
        from bl_ui import properties_constraint as pc
        self.assertTrue(hasattr(pc, "BONE_PT_bSpringConstraint"))
        self.assertTrue(hasattr(pc, "BONE_PT_bSpringConstraint_colliders"))
        item = next(i for i in bpy.types.Constraint.bl_rna.properties["type"].enum_items if i.identifier == 'SPRING')
        strings = {item.name, item.description, bpy.types.SpringConstraint.bl_rna.description}
        for struct in (bpy.types.SpringConstraint, bpy.types.SpringConstraintCollider):
            for prop in struct.bl_rna.properties:
                if prop.identifier in bpy.types.Constraint.bl_rna.properties or prop.identifier == "rna_type":
                    continue
                strings.update((prop.name, prop.description))
        strings.discard("")
        with iu.language('vi_VN'):
            self.assertEqual(iu.untranslated(strings, dt.KEEP), [])


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy, thấy FAIL** — `TypeError: ... enum "SPRING" not found` (chưa build).

- [ ] **Step 3: Code C++**

`DNA_constraint_types.h`: trong `eBConstraint_Types`, sau `CONSTRAINT_TYPE_GEOMETRY_ATTRIBUTE = 31,`:
```cpp
  /** DaskToon: spring bone sway of the anime rig. */
  CONSTRAINT_TYPE_SPRING = 32,
```
  và sau `struct bArmatureConstraint {...};`:
```cpp
/** DaskToon anime rig: sways a bone like a spring bone (docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md
 * section 9). The colliders are capsules along bones: the targets, with the capsule radius in `weight` (armature units,
 * like `radius`). */
struct bSpringConstraint {
  /** Collider bones (bConstraintTarget-s); `weight` is the capsule radius. */
  ListBaseT<bConstraintTarget> targets = {nullptr, nullptr};
  /** Pull back towards the posed direction. */
  float stiffness = 1.0f;
  /** Pull down (world -Z). */
  float gravity = 0.2f;
  /** 0 keeps all the swing, 1 none. */
  float drag = 0.4f;
  /** Radius of the bone's tail against the colliders, in armature units. */
  float radius = 0.03f;
};
```

`constraint.cc`, trước `/* -------- Action Constraint ----------- */`:
```cpp
/* -------- Spring Constraint (DaskToon) ----------- */

static void spring_new_data(void *cdata)
{
  bSpringConstraint *data = static_cast<bSpringConstraint *>(cdata);
  data->stiffness = 1.0f;
  data->gravity = 0.2f;
  data->drag = 0.4f;
  data->radius = 0.03f;
}

static void spring_free(bConstraint *con)
{
  bSpringConstraint *data = static_cast<bSpringConstraint *>(con->data);
  data->targets.free_no_destruct();
}

static void spring_copy(bConstraint *con, bConstraint *srccon)
{
  bSpringConstraint *pcon = static_cast<bSpringConstraint *>(con->data);
  bSpringConstraint *opcon = static_cast<bSpringConstraint *>(srccon->data);
  BLI_duplicatelist(&pcon->targets, &opcon->targets);
}

static int spring_get_tars(bConstraint *con, ListBaseT<bConstraintTarget> *list)
{
  if (con && list) {
    bSpringConstraint *data = static_cast<bSpringConstraint *>(con->data);
    *list = data->targets;
    return data->targets.count();
  }
  return 0;
}

static void spring_id_looper(bConstraint *con, ConstraintIDFunc func, void *userdata)
{
  bSpringConstraint *data = static_cast<bSpringConstraint *>(con->data);
  for (bConstraintTarget &ct : data->targets) {
    func(con, reinterpret_cast<ID **>(&ct.tar), false, userdata);
  }
}

static void spring_evaluate(bConstraint * /*con*/,
                            bConstraintOb * /*cob*/,
                            ListBaseT<bConstraintTarget> * /*targets*/)
{
}

static bConstraintTypeInfo CTI_SPRING = {
    /*type*/ CONSTRAINT_TYPE_SPRING,
    /*size*/ sizeof(bSpringConstraint),
    /*name*/ N_("Spring"),
    /*struct_name*/ "bSpringConstraint",
    /*free_data*/ spring_free,
    /*id_looper*/ spring_id_looper,
    /*copy_data*/ spring_copy,
    /*new_data*/ spring_new_data,
    /*get_constraint_targets*/ spring_get_tars,
    /*flush_constraint_targets*/ nullptr,
    /*get_target_matrix*/ nullptr,
    /*evaluate_constraint*/ spring_evaluate,
};
```
  bảng: `constraintsTypeInfo[32] = &CTI_SPRING; /* Spring Constraint (DaskToon) */`;
  `BKE_constraint_blend_write` thêm (giống ARMATURE):
```cpp
        case CONSTRAINT_TYPE_SPRING: {
          bSpringConstraint *data = static_cast<bSpringConstraint *>(con.data);
          for (bConstraintTarget &ct : data->targets) {
            writer->write_struct(&ct);
          }
          break;
        }
```
  `BKE_constraint_blend_read_data`:
```cpp
      case CONSTRAINT_TYPE_SPRING: {
        bSpringConstraint *data = static_cast<bSpringConstraint *>(con.data);
        BLO_read_struct_list(reader, bConstraintTarget, &data->targets);
        break;
      }
```
  `constraint_list_find_from_target`:
```cpp
    else if (con.type == CONSTRAINT_TYPE_SPRING) {
      targets = &(static_cast<bSpringConstraint *>(con.data))->targets;
    }
```
  `BKE_constraint_targets_for_solving_get`: `ELEM(cti->type, CONSTRAINT_TYPE_ARMATURE, CONSTRAINT_TYPE_SPRING)` (Spring đọc
  thẳng pose channel của collider, không cần `ct->matrix`).

`rna_constraint.cc`:
- mục enum sau `SHRINKWRAP`:
```cpp
    {CONSTRAINT_TYPE_SPRING,
     "SPRING",
     ICON_FORCE_HARMONIC,
     "Spring",
     "Sway the bone like a spring: it swings with the motion, hangs down and keeps out of collider bones "
     "(DaskToon)"},
```
- refine: `case CONSTRAINT_TYPE_SPRING: return RNA_SpringConstraint;`
- `rna_ConstraintTarget_path`: nhánh `else if (con->type == CONSTRAINT_TYPE_SPRING)` không dùng (collider có đường dẫn
  riêng); thêm hàm:
```cpp
static std::optional<std::string> rna_SpringConstraintCollider_path(const PointerRNA *ptr)
{
  Object *ob = id_cast<Object *>(ptr->owner_id);
  bConstraintTarget *tgt = static_cast<bConstraintTarget *>(ptr->data);
  bConstraint *con = rna_constraint_from_target(ptr);
  if (con != nullptr && con->type == CONSTRAINT_TYPE_SPRING) {
    const int index = BLI_findindex(&static_cast<bSpringConstraint *>(con->data)->targets, tgt);
    if (index >= 0) {
      return fmt::format(
          "{}.colliders[{}]", rna_Constraint_do_compute_path(ob, con).value_or(""), index);
    }
  }
  return std::nullopt;
}

static bConstraintTarget *rna_SpringConstraint_collider_new(ID *id, bConstraint *con, Main *bmain)
{
  bSpringConstraint *scon = static_cast<bSpringConstraint *>(con->data);
  bConstraintTarget *tgt = MEM_new<bConstraintTarget>("Spring Collider");
  tgt->tar = id_cast<Object *>(id);
  tgt->weight = 0.05f;
  BLI_addtail(&scon->targets, tgt);
  ed::object::constraint_dependency_tag_update(bmain, id_cast<Object *>(id), con);
  return tgt;
}

static void rna_SpringConstraint_collider_clear(ID *id, bConstraint *con, Main *bmain)
{
  bSpringConstraint *scon = static_cast<bSpringConstraint *>(con->data);
  scon->targets.free_no_destruct();
  ed::object::constraint_dependency_tag_update(bmain, id_cast<Object *>(id), con);
}
```
- định nghĩa struct (gọi trong `RNA_def_constraint` sau `rna_def_constraint_armature_deform(brna);`):
```cpp
static void rna_def_constraint_spring_collider(BlenderRNA *brna)
{
  StructRNA *srna = RNA_def_struct(brna, "SpringConstraintCollider", nullptr);
  RNA_def_struct_ui_text(
      srna, "Spring Collider", "A capsule along a bone that the spring keeps out of");
  RNA_def_struct_path_func(srna, "rna_SpringConstraintCollider_path");
  RNA_def_struct_sdna(srna, "bConstraintTarget");

  RNA_define_lib_overridable(true);

  PropertyRNA *prop = RNA_def_property(srna, "target", PROP_POINTER, PROP_NONE);
  RNA_def_property_pointer_sdna(prop, nullptr, "tar");
  RNA_def_property_ui_text(prop, "Armature", "Armature of the collider bone");
  RNA_def_property_pointer_funcs(
      prop, nullptr, "rna_ConstraintTargetBone_target_set", nullptr, "rna_Armature_object_poll");
  RNA_def_property_flag(prop, PROP_EDITABLE);
  RNA_def_property_update(prop, NC_OBJECT | ND_CONSTRAINT, "rna_ConstraintTarget_dependency_update");

  prop = RNA_def_property(srna, "subtarget", PROP_STRING, PROP_NONE);
  RNA_def_property_string_sdna(prop, nullptr, "subtarget");
  RNA_def_property_ui_text(prop, "Bone", "Bone the capsule runs along, from its head to its tail");
  RNA_def_property_update(prop, NC_OBJECT | ND_CONSTRAINT, "rna_ConstraintTarget_dependency_update");

  prop = RNA_def_property(srna, "radius", PROP_FLOAT, PROP_DISTANCE);
  RNA_def_property_float_sdna(prop, nullptr, "weight");
  RNA_def_property_range(prop, 0.0f, FLT_MAX);
  RNA_def_property_ui_range(prop, 0.0f, 1.0f, 1, 3);
  RNA_def_property_ui_text(prop, "Radius", "Radius of the capsule, in armature units");
  RNA_def_property_update(prop, NC_OBJECT | ND_CONSTRAINT, "rna_ConstraintTarget_update");

  RNA_define_lib_overridable(false);
}

static void rna_def_constraint_spring_colliders(BlenderRNA *brna, PropertyRNA *cprop)
{
  RNA_def_property_srna(cprop, "SpringConstraintColliders");
  StructRNA *srna = RNA_def_struct(brna, "SpringConstraintColliders", nullptr);
  RNA_def_struct_sdna(srna, "bConstraint");
  RNA_def_struct_ui_text(srna, "Spring Colliders", "Collider bones of a Spring constraint");

  FunctionRNA *func = RNA_def_function(srna, "new", "rna_SpringConstraint_collider_new");
  RNA_def_function_flag(func, FUNC_USE_SELF_ID | FUNC_USE_MAIN);
  RNA_def_function_ui_description(func, "Add a collider; its armature is the constraint's owner");
  PropertyRNA *parm = RNA_def_pointer(func, "collider", "SpringConstraintCollider", "", "New collider");
  RNA_def_function_return(func, parm);

  func = RNA_def_function(srna, "clear", "rna_SpringConstraint_collider_clear");
  RNA_def_function_flag(func, FUNC_USE_SELF_ID | FUNC_USE_MAIN);
  RNA_def_function_ui_description(func, "Remove all colliders");
}

static void rna_def_constraint_spring(BlenderRNA *brna)
{
  rna_def_constraint_spring_collider(brna);

  StructRNA *srna = RNA_def_struct(brna, "SpringConstraint", "Constraint");
  RNA_def_struct_ui_text(
      srna,
      "Spring Constraint",
      "Sway a bone like a spring bone: it swings with the motion, hangs down and keeps out of collider bones");
  RNA_def_struct_sdna_from(srna, "bSpringConstraint", "data");
  RNA_def_struct_ui_icon(srna, ICON_FORCE_HARMONIC);

  RNA_define_lib_overridable(true);

  PropertyRNA *prop = RNA_def_property(srna, "colliders", PROP_COLLECTION, PROP_NONE);
  RNA_def_property_collection_sdna(prop, nullptr, "targets", nullptr);
  RNA_def_property_struct_type(prop, "SpringConstraintCollider");
  RNA_def_property_ui_text(prop, "Colliders", "Capsules along bones that the spring keeps out of");
  rna_def_constraint_spring_colliders(brna, prop);

  prop = RNA_def_property(srna, "stiffness", PROP_FLOAT, PROP_NONE);
  RNA_def_property_float_sdna(prop, nullptr, "stiffness");
  RNA_def_property_range(prop, 0.0f, 4.0f);
  RNA_def_property_ui_text(prop, "Stiffness", "How strongly the bone springs back to its pose");
  RNA_def_property_update(prop, NC_OBJECT | ND_CONSTRAINT, "rna_Constraint_update");

  prop = RNA_def_property(srna, "gravity", PROP_FLOAT, PROP_NONE);
  RNA_def_property_float_sdna(prop, nullptr, "gravity");
  RNA_def_property_range(prop, 0.0f, 2.0f);
  RNA_def_property_ui_text(prop, "Gravity", "How strongly the bone is pulled down");
  RNA_def_property_update(prop, NC_OBJECT | ND_CONSTRAINT, "rna_Constraint_update");

  prop = RNA_def_property(srna, "drag", PROP_FLOAT, PROP_FACTOR);
  RNA_def_property_float_sdna(prop, nullptr, "drag");
  RNA_def_property_range(prop, 0.0f, 1.0f);
  RNA_def_property_ui_text(
      prop, "Drag", "How quickly the swing dies down: 0 keeps swinging, 1 stops at once");
  RNA_def_property_update(prop, NC_OBJECT | ND_CONSTRAINT, "rna_Constraint_update");

  prop = RNA_def_property(srna, "radius", PROP_FLOAT, PROP_DISTANCE);
  RNA_def_property_float_sdna(prop, nullptr, "radius");
  RNA_def_property_range(prop, 0.0f, FLT_MAX);
  RNA_def_property_ui_range(prop, 0.0f, 1.0f, 1, 3);
  RNA_def_property_ui_text(
      prop, "Radius", "How far the bone's tail keeps from the colliders, in armature units");
  RNA_def_property_update(prop, NC_OBJECT | ND_CONSTRAINT, "rna_Constraint_update");

  RNA_define_lib_overridable(false);
}
```
  (Task 2 đổi các update thành `rna_SpringConstraint_update` để xóa bộ nhớ đệm.)

`object_constraint.cc` (`get_new_constraint_target`): thêm `case CONSTRAINT_TYPE_SPRING:` vào nhóm `return false;`
  (collider do DaskToon quản lý). `outliner_draw.cc`: `case CONSTRAINT_TYPE_SPRING: data.icon = ICON_FORCE_HARMONIC; break;`
  `visualkey.cc`: `case CONSTRAINT_TYPE_SPRING: if (searchtype == VISUALKEY_ROT) { return true; } break;`

- [ ] **Step 4: Panel Python** — `properties_constraint.py`, trước `classes = (`:
```python
# Spring Constraint (DaskToon anime rig)

class SpringConstraintPanel(ConstraintButtonsPanel):
    def draw(self, context):
        layout = self.layout
        con = self.get_constraint(context)
        layout.use_property_split = True
        layout.use_property_decorate = True
        col = layout.column()
        col.prop(con, "stiffness")
        col.prop(con, "gravity")
        col.prop(con, "drag")
        col.prop(con, "radius")
        self.draw_influence(layout, con)


class SpringConstraintCollidersPanel(ConstraintButtonsSubPanel):
    bl_label = "Colliders"

    def draw(self, context):
        layout = self.layout
        con = self.get_constraint(context)
        layout.use_property_split = True
        layout.use_property_decorate = False
        if not con.colliders:
            layout.label(text="No colliders: Build Rig adds the body bones", icon='INFO')
        for collider in con.colliders:
            layout.prop(collider, "radius", text=collider.subtarget, translate=False)


class OBJECT_PT_bSpringConstraint(ObjectConstraintPanel, SpringConstraintPanel, Panel):
    pass


class BONE_PT_bSpringConstraint(BoneConstraintPanel, SpringConstraintPanel, Panel):
    pass


class OBJECT_PT_bSpringConstraint_colliders(ObjectConstraintPanel, SpringConstraintCollidersPanel, Panel):
    bl_parent_id = "OBJECT_PT_bSpringConstraint"


class BONE_PT_bSpringConstraint_colliders(BoneConstraintPanel, SpringConstraintCollidersPanel, Panel):
    bl_parent_id = "BONE_PT_bSpringConstraint"
```
  và thêm bốn lớp vào `classes` (OBJECT_ trước BONE_, panel con sau panel cha).
  `dasktoon_translations_test.py`: `TRANSLATED_CLASSES["scripts/startup/bl_ui/properties_constraint.py"] =
  ("SpringConstraintPanel", "SpringConstraintCollidersPanel")`.

- [ ] **Step 5: Bản dịch** — VI: "Spring" → "Lò xo"; mô tả enum; "Spring Constraint"; mô tả struct; "Spring Collider" →
  "Collider của lò xo"; "A capsule along a bone that the spring keeps out of"; "Armature of the collider bone"; "Bone the
  capsule runs along, from its head to its tail" (đã có); "Radius of the capsule, in armature units"; "Colliders" (đã
  có); "Capsules along bones that the spring keeps out of"; "How strongly the bone springs back to its pose"; "How
  strongly the bone is pulled down"; "How quickly the swing dies down: 0 keeps swinging, 1 stops at once" (đã có); "How
  far the bone's tail keeps from the colliders, in armature units"; "Collider bones of a Spring constraint"; "Add a
  collider; its armature is the constraint's owner"; "Remove all colliders"; "No colliders: Build Rig adds the body
  bones"; "Spring Colliders".

- [ ] **Step 6: Build, đồng bộ, chạy** — build INSTALL, `sync`, `run dasktoon_spring_constraint_test` → PASS; thêm
  `run dasktoon_translations_test dasktoon_ui_layout_test`.
- [ ] **Step 7: Commit** — `feat: a Spring constraint type with collider bones (C++, DNA, RNA, panels)`.

---

### Task 2: Tính lắc trong constraint, bộ nhớ đệm theo khung

**Files:**
- Modify: `source/blender/blenkernel/intern/constraint.cc` (`spring_evaluate` thật, bộ nhớ đệm,
  `BKE_constraint_spring_cache_clear`), `source/blender/blenkernel/BKE_constraint.h` (khai báo),
  `source/blender/makesrna/intern/rna_constraint.cc` (`rna_SpringConstraint_update`, hàm `clear_cache`)
- Test: `tests/python/dasktoon_spring_constraint_test.py` (`EvaluateTest`)

**Interfaces:**
- Produces: `SpringConstraint.clear_cache()` (xóa bộ nhớ đệm của object chủ); `BKE_constraint_spring_cache_clear(const
  Object *ob)`.

- [ ] **Step 1: Test** — thêm vào file test:
```python
def tails(rig, count=3):
    world = rig.matrix_world
    return [np.array(world @ rig.pose.bones["Tail_%d" % k].tail) for k in range(1, count + 1)]


def python_tails(rig, frames, params, colliders, count=3):
    """Tails from dasktoon_rig/spring.py for the same chain, frame by frame, with the springs muted for the poses."""
    from dasktoon_rig import spring, sway
    cons = [rig.pose.bones["Tail_%d" % k].constraints[0] for k in range(1, count + 1)]
    for con in cons:
        con.mute = True
    names = ["Tail_%d" % k for k in range(1, count + 1)]
    out, state = {}, None
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        pose = sway.chain_pose(rig, names)
        caps = [(np.array(rig.matrix_world @ rig.pose.bones[b].head), np.array(rig.matrix_world @ rig.pose.bones[b].tail), r)
                for b, r in colliders]
        if state is None or frame == bpy.context.scene.frame_start:
            state = spring.reset(pose)
        else:
            spring.step(state, pose, params, caps, 1.0 / bpy.context.scene.render.fps)
        out[frame] = [t.copy() for t in state.current]
    for con in cons:
        con.mute = False
    return out


def animate_spine(rig):
    spine = rig.pose.bones["Spine"]
    for frame, x in ((1, 0.0), (5, 0.4), (10, 0.4)):
        spine.location = (x, 0.0, 0.0)
        spine.keyframe_insert("location", frame=frame)
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 20


class EvaluateTest(unittest.TestCase):
    def setUp(self):
        self.rig = chain_rig()
        animate_spine(self.rig)
        self.cons = add_springs(self.rig, 3, [("Spine", 0.05)])

    def play(self, last):
        out = {}
        for frame in range(1, last + 1):
            bpy.context.scene.frame_set(frame)
            out[frame] = tails(self.rig)
        return out

    def test_matches_python(self):
        from dasktoon_rig import spring
        expected = python_tails(self.rig, range(1, 13), spring.Params(), [("Spine", 0.05)])
        self.cons[0].clear_cache()
        played = self.play(12)
        for frame in (1, 4, 8, 12):
            np.testing.assert_allclose(np.array(played[frame]), np.array(expected[frame]), atol=1e-4, err_msg=str(frame))
        self.assertGreater(np.linalg.norm(played[8][2] - played[1][2] - np.array((0.4, 0.0, 0.0))), 0.01)

    def test_start_frame_has_no_sway(self):
        self.play(8)
        bpy.context.scene.frame_set(1)
        np.testing.assert_allclose(np.array(tails(self.rig)),
                                   [(0.0, 0.1, 1.0), (0.0, 0.2, 1.0), (0.0, 0.3, 1.0)], atol=1e-5)

    def test_same_frame_twice_and_scrubbing(self):
        played = self.play(12)
        bpy.context.scene.frame_set(7)
        np.testing.assert_allclose(np.array(tails(self.rig)), np.array(played[7]), atol=1e-6)
        bpy.context.view_layer.update()
        np.testing.assert_allclose(np.array(tails(self.rig)), np.array(played[7]), atol=1e-6)
        again = self.play(12)
        np.testing.assert_allclose(np.array(again[12]), np.array(played[12]), atol=1e-6)

    def test_changed_input_starts_again(self):
        self.play(8)
        spine = self.rig.pose.bones["Spine"]
        spine.location = (0.4, 0.0, 0.3)
        spine.keyframe_insert("location", frame=8)
        bpy.context.scene.frame_set(8)
        head = np.array(self.rig.matrix_world @ self.rig.pose.bones["Tail_1"].head)
        np.testing.assert_allclose(tails(self.rig)[0], head + (0.0, 0.1, 0.0), atol=1e-5)  # at rest again

    def test_mute_and_settings(self):
        self.play(8)
        for con in self.cons:
            con.mute = True
        bpy.context.scene.frame_set(8)
        rest = tails(self.rig)
        for con in self.cons:
            con.mute = False
        bpy.context.scene.frame_set(8)
        swayed = tails(self.rig)
        self.assertGreater(np.linalg.norm(swayed[2] - rest[2]), 1e-3)
        self.cons[2].drag = 1.0   # clears the cache: frame 8 starts again
        bpy.context.scene.frame_set(8)
        np.testing.assert_allclose(tails(self.rig)[2], rest[2], atol=1e-5)

    def test_collider_pushes_out_and_follows_scale(self):
        self.rig.pose.bones["Spine"].constraints.clear()
        for con in self.cons:
            con.stiffness, con.gravity = 0.0, 2.0
        self.play(15)
        tip = tails(self.rig)[2]
        head = np.array(self.rig.matrix_world @ self.rig.pose.bones["Spine"].head)
        tail = np.array(self.rig.matrix_world @ self.rig.pose.bones["Spine"].tail)
        t = np.clip((tip - head) @ (tail - head) / ((tail - head) @ (tail - head)), 0.0, 1.0)
        self.assertGreaterEqual(np.linalg.norm(tip - (head + t * (tail - head))), 0.05 + 0.03 - 1e-4)

    def test_python_handlers_are_gone(self):
        names = [h.__name__ for h in bpy.app.handlers.frame_change_post + bpy.app.handlers.frame_change_pre]
        self.assertNotIn("frame_post", names)
        self.assertNotIn("frame_pre", names)
```
  (`test_python_handlers_are_gone` qua được ở Task 3; Task 2 chỉ chạy các test còn lại.)

- [ ] **Step 2: Chạy, thấy FAIL** — `AttributeError: 'SpringConstraint' object has no attribute 'clear_cache'`.

- [ ] **Step 3: Code** — `constraint.cc`, đầu file thêm `#include <map>`, `#include <mutex>`, `#include <string>`,
  `#include <unordered_map>`; thay `spring_evaluate` rỗng bằng:
```cpp
/* Sways a bone like the anime rig's spring bones (docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md 9.3,
 * 9.4), the same maths as scripts/modules/dasktoon_rig/spring.py and Unity's DaskToonSpringBone: the tail keeps its
 * current and previous world position; a step adds the inertia, a pull towards the posed direction and gravity, keeps
 * the bone's length and pushes the tail out of the collider capsules. The state of every frame is cached, keyed by the
 * object's session UID and the bone, with the inputs it was solved from: the same frame again gives the same pose, the
 * scene's start frame and changed inputs start again, a new frame steps on from the closest earlier one. */

struct SpringFrame {
  float3 current;
  float3 previous;
  float3 head;
  float3 rest;
};

struct SpringCapsule {
  float3 a;
  float3 b;
  float radius;
};

constexpr int SPRING_MAX_CATCH_UP = 300;

static std::mutex &spring_mutex()
{
  static std::mutex mutex;
  return mutex;
}

/* Plain std containers: the cache lives until exit, outside guarded memory. */
static std::unordered_map<std::string, std::map<int, SpringFrame>> &spring_cache()
{
  static std::unordered_map<std::string, std::map<int, SpringFrame>> cache;
  return cache;
}

static std::string spring_prefix(const Object *ob)
{
  return std::to_string(ob->id.session_uid) + ":";
}

void BKE_constraint_spring_cache_clear(const Object *ob)
{
  const std::string prefix = spring_prefix(ob);
  std::scoped_lock lock(spring_mutex());
  auto &cache = spring_cache();
  for (auto it = cache.begin(); it != cache.end();) {
    if (it->first.compare(0, prefix.size(), prefix) == 0) {
      it = cache.erase(it);
    }
    else {
      ++it;
    }
  }
}

static float3 spring_unit(const float3 &v)
{
  const float length = math::length(v);
  return length > 1e-12f ? v / length : v;
}

static float3 spring_push_out(const float3 &point, const float3 &a, const float3 &b, const float distance)
{
  const float3 axis = b - a;
  const float length2 = math::dot(axis, axis);
  const float t = length2 < 1e-18f ? 0.0f :
                                     std::clamp(math::dot(point - a, axis) / length2, 0.0f, 1.0f);
  const float3 closest = a + axis * t;
  const float3 away = point - closest;
  const float gap = math::length(away);
  if (gap >= distance || gap < 1e-12f) {
    return point;
  }
  return closest + away / gap * distance;
}

static void spring_step(SpringFrame &state,
                        const float3 &head,
                        const float3 &rest,
                        const float length,
                        const bSpringConstraint &data,
                        const Span<SpringCapsule> capsules,
                        const float joint_radius,
                        const float dt)
{
  const float3 current = state.current;
  float3 tail = current + (current - state.previous) * (1.0f - data.drag) +
                rest * (data.stiffness * dt) + float3(0.0f, 0.0f, -1.0f) * (data.gravity * dt);
  tail = head + spring_unit(tail - head) * length;
  for (const SpringCapsule &capsule : capsules) {
    tail = spring_push_out(tail, capsule.a, capsule.b, capsule.radius + joint_radius);
    tail = head + spring_unit(tail - head) * length;
  }
  state.previous = current;
  state.current = tail;
}

static bool spring_same(const float3 &a, const float3 &b)
{
  return math::length(a - b) < 1e-6f;
}

static void spring_evaluate(bConstraint *con,
                            bConstraintOb *cob,
                            ListBaseT<bConstraintTarget> *targets)
{
  const bSpringConstraint *data = static_cast<const bSpringConstraint *>(con->data);
  if (cob->type != CONSTRAINT_OBTYPE_BONE || cob->pchan == nullptr ||
      cob->pchan_armbone == nullptr || cob->scene == nullptr || cob->depsgraph == nullptr)
  {
    return;
  }
  const float3 head(cob->matrix[3]);
  const float3 axis(cob->matrix[1]);
  const float scale = math::length(axis);
  const float length = cob->pchan_armbone->length * scale;
  if (scale < 1e-8f || length < 1e-8f) {
    return;
  }
  const float3 rest = axis / scale;
  const float object_scale = mat4_to_scale(cob->ob->object_to_world().ptr());

  Vector<SpringCapsule> capsules;
  for (const bConstraintTarget &ct : *targets) {
    if (!VALID_CONS_TARGET(&ct) || ct.tar->type != OB_ARMATURE || ct.tar->pose == nullptr) {
      continue;
    }
    const bPoseChannel *pchan = BKE_pose_channel_find_name(ct.tar->pose, ct.subtarget);
    if (pchan == nullptr) {
      continue;
    }
    const float(*world)[4] = ct.tar->object_to_world().ptr();
    float3 a, b;
    mul_v3_m4v3(a, world, pchan->pose_head);
    mul_v3_m4v3(b, world, pchan->pose_tail);
    capsules.append({a, b, ct.weight * mat4_to_scale(world)});
  }

  const Scene *scene = cob->scene;
  const int frame = int(std::lround(DEG_get_ctime(cob->depsgraph)));
  const float dt = scene->r.frs_sec > 0 ? scene->r.frs_sec_base / float(scene->r.frs_sec) :
                                          1.0f / 24.0f;
  const std::string key = spring_prefix(cob->ob) + cob->pchan->name;
  float3 tail;
  {
    std::scoped_lock lock(spring_mutex());
    std::map<int, SpringFrame> &history = spring_cache()[key];
    auto found = history.find(frame);
    if (found != history.end() && spring_same(found->second.head, head) &&
        spring_same(found->second.rest, rest))
    {
      tail = found->second.current;
    }
    else {
      if (found != history.end()) {
        history.clear(); /* The animation or the rig changed: start again from here. */
      }
      SpringFrame state;
      auto after = history.lower_bound(frame);
      if (frame != scene->r.sfra && after != history.begin() &&
          frame - std::prev(after)->first <= SPRING_MAX_CATCH_UP)
      {
        const auto earlier = std::prev(after);
        state = earlier->second;
        for (int step = earlier->first; step < frame; step++) {
          spring_step(state, head, rest, length, *data, capsules, data->radius * object_scale, dt);
        }
      }
      else {
        history.clear();
        state.current = state.previous = head + rest * length;
      }
      state.head = head;
      state.rest = rest;
      history.insert_or_assign(frame, state);
      tail = state.current;
    }
  }

  /* Turn the bone from its posed direction to its tail, keeping the head and the scale. */
  float rotation[3][3], basis[3][3], result[3][3];
  const float3 direction = spring_unit(tail - head);
  rotation_between_vecs_to_mat3(rotation, rest, direction);
  copy_m3_m4(basis, cob->matrix);
  mul_m3_m3m3(result, rotation, basis);
  copy_m4_m3(cob->matrix, result);
  copy_v3_v3(cob->matrix[3], head);
  cob->matrix[3][3] = 1.0f;
}
```
  `BKE_constraint.h` (trong namespace): `/** DaskToon: forget the cached sway of every Spring constraint on `ob`. */
  void BKE_constraint_spring_cache_clear(const struct Object *ob);`

`rna_constraint.cc` (RNA_RUNTIME):
```cpp
static void rna_SpringConstraint_update(Main *bmain, Scene *scene, PointerRNA *ptr)
{
  BKE_constraint_spring_cache_clear(id_cast<Object *>(ptr->owner_id));
  rna_Constraint_update(bmain, scene, ptr);
}

static void rna_SpringConstraintCollider_update(Main *bmain, Scene *scene, PointerRNA *ptr)
{
  BKE_constraint_spring_cache_clear(id_cast<Object *>(ptr->owner_id));
  rna_ConstraintTarget_update(bmain, scene, ptr);
}

static void rna_SpringConstraint_clear_cache(ID *id, bConstraint * /*con*/)
{
  BKE_constraint_spring_cache_clear(id_cast<Object *>(id));
}
```
  bốn thuộc tính của `SpringConstraint` dùng `rna_SpringConstraint_update`; `radius` của collider dùng
  `rna_SpringConstraintCollider_update`; collider `new`/`clear` gọi thêm `BKE_constraint_spring_cache_clear`. Hàm:
```cpp
  FunctionRNA *func = RNA_def_function(srna, "clear_cache", "rna_SpringConstraint_clear_cache");
  RNA_def_function_flag(func, FUNC_USE_SELF_ID);
  RNA_def_function_ui_description(
      func, "Forget the cached sway of every Spring constraint of the object, so it starts again");
```

- [ ] **Step 4: Bản dịch** — "Forget the cached sway of every Spring constraint of the object, so it starts again".
- [ ] **Step 5: Build, chạy** — PASS trừ `test_python_handlers_are_gone`.
- [ ] **Step 6: Commit** — `feat: the Spring constraint sways bones like spring.py, with a per-frame cache`.

---

### Task 3: Rig dùng constraint Spring

**Files:**
- Modify: `scripts/modules/dasktoon_rig/sway.py` (bỏ handler, `_cache`, `sway()`, `apply()`; thêm `CONSTRAINT_NAME`,
  `spring_constraint(pb)`, `sync(rig)`, `set_live(rig, on)`, `clear_cache(rig)`; `suppressed()` mute; `bake()` đọc tư thế
  đã có lắc; `world_colliders()` nhân scale), `scripts/modules/dasktoon_rig/build.py` (bán kính collider theo đơn vị
  armature; gọi `sway.sync` cuối Build), `scripts/startup/bl_ui/dasktoon_rig.py` (bỏ đăng ký handler; cập nhật thuộc
  tính gọi `sway.sync`), `scripts/modules/dasktoon_export/rig_json.py` (bán kính world)
- Test: viết lại `tests/python/dasktoon_rig_sway_test.py`; sửa `tests/python/dasktoon_export_rig_test.py`
  (`test_runtime_chains_rest_while_the_fbx_is_written` theo mute và hướng xương), `tests/python/dasktoon_rig_build_test.py`
  (collider theo đơn vị armature)

**Interfaces:**
- Produces: `sway.CONSTRAINT_NAME = "DaskToon Spring"`, `sway.spring_constraint(pb)`, `sway.sync(rig)`,
  `sway.set_live(rig, on)`, `sway.clear_cache(rig)`, `sway.direction(rig, name)`; giữ `chains`, `chain_pose`,
  `world_colliders`, `suppressed`, `bake`, `remove_rotation_keys`, `ROTATION_PATHS`.

- [ ] **Step 1: Test** — `dasktoon_rig_sway_test.py` viết lại với nhân vật thử như cũ (`character()`, hông lướt khung
  1→6), đo bằng **hướng xương** (`sway.direction`, tính từ `pose_bone.head/tail`, có cả constraint):
  `test_build_adds_spring_constraints` (mọi xương chuỗi có một constraint `SPRING` tên `DaskToon Spring`, 14 collider,
  thông số của phần), `test_moving_hips_sway_the_skirt`, `test_back_to_start_resets`,
  `test_revisiting_a_frame_gives_the_same_pose`, `test_live_sway_off_mutes`, `test_settings_reach_the_constraints`
  (đổi Stiffness của phần → constraint đổi), `test_bake_matches_live`, `test_bake_twice_does_not_stack`,
  `SuppressTest.test_suppressed_chains_rest_and_come_back` (mute rồi trả trạng thái), `test_world_colliders`. Test export:
  spy kiểm `pb.constraints[0].mute` của Skirt (Runtime) là True và Hair (Baked) là False lúc ghi FBX; sau khi xuất mute
  trở lại như trước.

- [ ] **Step 2: Chạy, thấy FAIL** — `AttributeError: module 'dasktoon_rig.sway' has no attribute 'sync'`.

- [ ] **Step 3: Code** — `sway.py` mới:
```python
"""Sway of the generated chains (anime rig spec 9.4): every chain bone has DaskToon's C++ Spring constraint, which the
depsgraph evaluates with the rest of the pose (scrubbing, rendering and exporting are right without baking). This module
keeps the constraints in step with the rig's parts and colliders, turns Live Sway on and off (mute), bakes the sway into
keys and keeps runtime chains still while Engine Export writes the FBX."""

from contextlib import contextmanager

import bpy
import numpy as np
from mathutils import Matrix

from . import build, spring

CONSTRAINT_NAME = "DaskToon Spring"
ROTATION_PATHS = ("rotation_quaternion", "rotation_euler", "rotation_axis_angle")


def chains(rig): ...            # unchanged


def chain_pose(rig, names): ... # unchanged


def spring_constraint(pb):
    return next((c for c in pb.constraints if c.type == 'SPRING'), None)


def _scale(rig):
    return max(rig.matrix_world.to_scale())


def world_colliders(rig):
    """[(head, tail, world radius)] capsules of the rig's colliders in its current pose."""
    world, scale = rig.matrix_world, _scale(rig)
    out = []
    for collider in rig.data.dasktoon_rig.colliders:
        pb = rig.pose.bones.get(collider.bone)
        if pb is not None:
            out.append((np.array(world @ pb.head), np.array(world @ pb.tail), collider.radius * scale))
    return out


def sync(rig):
    """A Spring constraint on every chain bone with its part's settings, the rig's colliders and Live Sway."""
    data = rig.data.dasktoon_rig
    for part_name, names in chains(rig):
        part = data.parts.get(part_name)
        params = part if part is not None else spring.Params()
        for name in names:
            pb = rig.pose.bones[name]
            con = spring_constraint(pb)
            if con is None:
                con = pb.constraints.new('SPRING')
                con.name = CONSTRAINT_NAME
            con.stiffness, con.gravity, con.drag, con.radius = (params.stiffness, params.gravity, params.drag,
                                                                params.radius)
            con.colliders.clear()
            for collider in data.colliders:
                item = con.colliders.new()
                item.target = rig
                item.subtarget = collider.bone
                item.radius = collider.radius
            con.mute = not data.live_sway


def set_live(rig, on): ...      # mute = not on on every spring constraint of the chains
def clear_cache(rig): ...       # clear_cache() on the first spring constraint found
def direction(rig, name): ...   # unit (tail - head) of the pose bone, world


@contextmanager
def suppressed(rig, part_names):
    """Meanwhile the Spring constraints of `part_names` are muted (Engine Export writes the FBX); then as before."""


def _basis_rotation(rig, pb):
    """The local rotation (3x3) that gives pb its current pose rotation with the parent as it is now."""


def bake(context, rig, frame_start, frame_end): ...  # remove rotation curves, live on, clear cache, frame by frame read
                                                   # _basis_rotation, live off, insert keys
```
  (Thân các hàm viết khi thực hiện; `bake` giữ hành vi: thay cả đường cong xoay, Live Sway tắt sau đó.)
  `build.py`: `collider_radii` chia cho scale của rig (đơn vị armature), `build()` gọi `sway.sync(rig)` sau khi ghi
  collider. `dasktoon_rig.py`: `_sway_changed` tìm các rig dùng armature đó và gọi `sway.sync`; `register()` không thêm
  handler. `rig_json.py`: `radius` của chuỗi và collider nhân scale của rig.

- [ ] **Step 4: Chạy, thấy PASS** — `rt.sh dasktoon_rig_sway_test dasktoon_spring_constraint_test dasktoon_rig_build_test dasktoon_rig_ui_test dasktoon_export_rig_test dasktoon_translations_test`; test Unity rig.
- [ ] **Step 5: Commit** — `feat: the anime rig sways with Spring constraints instead of frame handlers`.

---

### Task 4: Kiểm tra, ảnh, báo cáo

- [ ] Toàn bộ suite CMake; test Unity (rig, model, shader).
- [ ] Công cụ chụp ảnh: ảnh `25_sway` vẫn ra như cũ (constraint thay handler); thêm `27_spring_constraint` (tab Bone
  Constraints của một xương tóc).
- [ ] Báo cáo: mục "Constraint Spring (C++)" trong `docs/superpowers/reports/2026-10-06-dasktoon-anime-rig-r1-report.md`.
