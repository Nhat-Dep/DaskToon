# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Controls (docs/superpowers/specs/2026-11-06-dasktoon-rig-controls-design.md, section 6): a Rigify control rig fitted
on the DaskToon joints and joined into the same armature. Each DaskToon bone of the table below copies a helper
DTH-<bone> that sits on Rigify's ORG bone with the DaskToon bone's own rest, so the DaskToon skeleton (what Unity and
Godot get) is unchanged and only its bones deform. Remove takes the layer off again, as it was before; Build Rig and
Edit Joints remove it first (it is built on the joints) and Build Rig adds it back."""

import json
import math

import bpy
import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_
from mathutils import Vector

RECORD = "dt_controls"  # on the armature data: what was there before the controls, for Remove
FOLLOW = "DT Follow Rigify"
HELPER = "DTH-"
SIDES = (("L", "Left"), ("R", "Right"))
SPINE = {"spine": "Hips", "spine.001": "Spine", "spine.002": "Chest", "spine.003": "UpperChest", "spine.006": "Head"}
LIMB = {"shoulder": "Shoulder", "upper_arm": "UpperArm", "forearm": "LowerArm", "hand": "Hand",
        "thigh": "UpperLeg", "shin": "LowerLeg", "foot": "Foot", "toe": "Toes"}
FINGERS = {"thumb": "Thumb", "f_index": "Index", "f_middle": "Middle", "f_ring": "Ring", "f_pinky": "Little"}
SEGMENTS = ("Proximal", "Intermediate", "Distal")
HEEL_HALF_WIDTH = 0.01375  # of the height: the heel pivot is 2.75% of it wide
HEEL_BEHIND = 0.02  # of the height behind the ankle when no body is found around it
DEFORM_COLLECTION = "DaskToon Deform"
HELPER_COLLECTION = "DaskToon Helpers"
# Rigify's limb switches: the bone holding IK_FK, and how the panel names the limb.
LIMB_SWITCHES = (("upper_arm_parent.L", "Left Arm"), ("upper_arm_parent.R", "Right Arm"),
                 ("thigh_parent.L", "Left Leg"), ("thigh_parent.R", "Right Leg"))


class ControlsError(Exception):
    pass


def metarig_map():
    """{metarig bone: DaskToon bone} of the whole bones; Neck is split into spine.004 and spine.005."""
    out = dict(SPINE)
    for s, side in SIDES:
        for m, d in LIMB.items():
            out["%s.%s" % (m, s)] = side + d
        for m, d in FINGERS.items():
            for k in range(3):
                out["%s.0%d.%s" % (m, k + 1, s)] = side + d + SEGMENTS[k]
    return out


def follows():
    """{DaskToon bone: the Rigify ORG bone it follows}."""
    out = {d: "ORG-" + m for m, d in metarig_map().items()}
    out["Neck"] = "ORG-spine.004"
    return out


def has_controls(rig):
    return rig is not None and rig.type == 'ARMATURE' and RECORD in rig.data


def missing_joints(rig):
    return [name for name in list(metarig_map().values()) + ["Neck"] if rig.data.bones.get(name) is None]


def limb_switches(rig):
    """[(pose bone, limb name)] of the IK/FK switches the controls have."""
    return [(rig.pose.bones[name], label) for name, label in LIMB_SWITCHES
            if rig.pose.bones.get(name) is not None and "IK_FK" in rig.pose.bones[name]]


def _set_mode(context, obj, mode):
    if context.view_layer.objects.active is not None and context.view_layer.objects.active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in context.view_layer.objects:
        o.select_set(o == obj)
    context.view_layer.objects.active = obj
    if mode != 'OBJECT':
        bpy.ops.object.mode_set(mode=mode)


def _body_points(rig):
    """World positions of the Body parts' vertices (every mesh the rig moves when it has no parts)."""
    data = getattr(rig.data, "dasktoon_rig", None)
    meshes = []
    if data is not None:
        meshes = [p.object for p in data.parts if p.role == 'BODY' and p.object is not None]
    if not meshes:
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and any(
            m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
    points = []
    for obj in dict.fromkeys(meshes):
        co = np.empty(len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get("co", co)
        mw = np.array(obj.matrix_world)
        points.append(co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3])
    return np.concatenate(points) if points else np.zeros((0, 3))


def _rigify_on():
    """Rigify enabled for this session; returns whether it was off (to switch it off again)."""
    import addon_utils
    loaded, enabled = addon_utils.check("rigify")
    if enabled:
        return False
    addon_utils.enable("rigify", default_set=True, persistent=False)
    if not hasattr(bpy.ops.pose, "rigify_generate"):
        raise ControlsError(rpt_("Rigify is missing from this build"))
    return True


def _rigify_off():
    import addon_utils
    addon_utils.disable("rigify", default_set=True)


def add(context, rig):
    """The control layer on `rig`; returns the number of control bones. ControlsError when a joint is missing."""
    if rig.data.get(RECORD) is not None:
        remove(context, rig)
    missing = missing_joints(rig)
    if missing:
        raise ControlsError(rpt_("These joints are missing: %s") % ", ".join(missing))
    active = context.view_layer.objects.active
    switched_on = _rigify_on()
    try:
        return _add(context, rig)
    finally:
        if switched_on:
            _rigify_off()
        if active is not None and active.name in context.view_layer.objects:
            _set_mode(context, active, 'OBJECT')


def _add(context, rig):
    arm = rig.data
    bones = arm.bones
    look = bones.get("LookTarget")
    record = {
        "bones": [b.name for b in bones],
        "collections": [c.name for c in arm.collections_all],
        "visible": [c.name for c in arm.collections_all if c.is_visible],
        "look_parent": look.parent.name if look is not None and look.parent is not None else "",
        "texts": [t.name for t in bpy.data.texts],
        "collections_data": [c.name for c in bpy.data.collections],
        "objects": [o.name for o in bpy.data.objects],
    }
    deform = {b.name for b in bones if b.use_deform}
    mapping = metarig_map()
    world = rig.matrix_world
    height = max(b.head_local.z for b in bones) - min(b.head_local.z for b in bones)

    def head(name):
        return world @ bones[name].head_local

    def tail(name):
        return world @ bones[name].tail_local

    def z_axis(name):
        return (world.to_3x3() @ bones[name].matrix_local.to_3x3().col[2]).normalized()

    # 1. Rigify's human metarig on the DaskToon joints.
    _set_mode(context, None, 'OBJECT')
    cursor = context.scene.cursor.location.copy()
    bpy.ops.object.armature_human_metarig_add()
    context.scene.cursor.location = cursor
    meta = context.view_layer.objects.active
    meta.location = (0.0, 0.0, 0.0)
    _set_mode(context, meta, 'EDIT')
    eb = meta.data.edit_bones
    keep = set(mapping) | {"spine.004", "spine.005"} | {"palm.0%d.%s" % (k, s) for k in range(1, 5) for s in "LR"} | \
        {"heel.02.%s" % s for s in "LR"}
    for b in list(eb):
        if b.name not in keep:
            eb.remove(b)
    connected = {b.name: b.use_connect for b in eb}
    for m in mapping:
        eb[m].use_connect = False
    for m, d in mapping.items():
        b = eb[m]
        b.head, b.tail = head(d), tail(d)
        b.align_roll(z_axis(d))
    neck_head, neck_tail = head("Neck"), tail("Neck")
    middle = (neck_head + neck_tail) / 2
    eb["spine.004"].head, eb["spine.004"].tail = neck_head, middle
    eb["spine.005"].head, eb["spine.005"].tail = middle, neck_tail
    for name in ("spine.004", "spine.005"):
        eb[name].align_roll(z_axis("Neck"))
    body = _body_points(rig)
    feet = [tail(side + "Toes").z for _s, side in SIDES] + [head(side + "Foot").z for _s, side in SIDES]
    floor = float(body[:, 2].min()) if len(body) else min(feet)
    for s, side in SIDES:
        sign = 1.0 if s == "L" else -1.0
        hand = eb["hand.%s" % s]
        for k, f in enumerate(("f_index", "f_middle", "f_ring", "f_pinky")):
            knuckle = eb["%s.01.%s" % (f, s)].head.copy()
            palm = eb["palm.0%d.%s" % (k + 1, s)]
            palm.use_connect = False
            palm.head = hand.head + (knuckle - hand.head) * 0.3
            palm.tail = knuckle
            palm.align_roll(z_axis(side + "Hand"))
        ankle = head(side + "Foot")
        near = body[(np.abs(body[:, 0] - ankle.x) < 0.035 * height / 1.6) & (body[:, 2] < ankle.z) &
                    (np.abs(body[:, 1] - ankle.y) < 0.08 * height / 1.6)] if len(body) else body
        back = float(near[:, 1].max()) if len(near) else ankle.y + HEEL_BEHIND * height
        heel = eb["heel.02.%s" % s]
        heel.use_connect = False
        heel.head = Vector((ankle.x - sign * HEEL_HALF_WIDTH * height, back, floor))
        heel.tail = Vector((ankle.x + sign * HEEL_HALF_WIDTH * height, back, floor))
        heel.roll = 0.0
    # Where Rigify's metarig joins two bones, each starts where its parent ends (the DaskToon bones follow through
    # helpers, so a few millimetres here change nothing).
    for name in [b.name for b in eb]:
        b = eb[name]
        if connected.get(name) and b.parent is not None:
            b.head = b.parent.tail.copy()
            b.use_connect = True
    _set_mode(context, meta, 'OBJECT')

    # 2. Generate.
    bpy.ops.pose.rigify_generate()
    generated = meta.data.rigify_target_rig
    if generated is None:
        raise ControlsError(rpt_("Rigify could not make the controls"))
    rig_id = generated.data.get("rig_id")
    generated_name = generated.name
    for text in [t for t in bpy.data.texts if t.name not in record["texts"]]:
        bpy.data.texts.remove(text)  # Rigify's panel script: the Controls section does its work (spec 6.4)

    # 3. Joined into the DaskToon armature.
    if rig_id is not None:
        arm["rig_id"] = rig_id
    for o in context.view_layer.objects:
        o.select_set(o in (rig, generated))
    context.view_layer.objects.active = rig
    bpy.ops.object.join()
    leftover = bpy.data.objects.get(generated_name)
    if leftover is not None and leftover != rig:
        bpy.data.objects.remove(leftover)

    # 4. The DaskToon bones follow Rigify through helpers with their own rest.
    follow = follows()
    _set_mode(context, rig, 'EDIT')
    eb = arm.edit_bones
    for d, org in follow.items():
        source = eb[d]
        helper = eb.new(HELPER + d)
        helper.head, helper.tail, helper.roll = source.head.copy(), source.tail.copy(), source.roll
        helper.parent = eb[org]
        helper.use_deform = False
    if look is not None and "root" in eb:
        eb["LookTarget"].parent = eb["root"]
    _set_mode(context, rig, 'POSE')
    for d in follow:
        pb = rig.pose.bones[d]
        pb.matrix_basis.identity()
        con = pb.constraints.new('COPY_TRANSFORMS')
        con.name = FOLLOW
        con.target, con.subtarget = rig, HELPER + d
    _set_mode(context, rig, 'OBJECT')

    # 5. Only the DaskToon bones deform; their collections hidden, Rigify's shown; the metarig's face collections,
    # left empty without its face, go.
    while True:  # children first, then the parent they leave empty
        empty = [c for c in arm.collections_all if c.name not in record["collections"] and not c.bones
                 and not c.children]
        if not empty:
            break
        for collection in empty:
            arm.collections.remove(collection)
    for b in arm.bones:
        if b.name not in deform:
            b.use_deform = False
    from . import face_board
    for name in record["collections"]:
        collection = arm.collections_all.get(name)
        if collection is not None and name != face_board.COLLECTION:  # the face board stays in sight
            collection.is_visible = False
    hidden = arm.collections.new(DEFORM_COLLECTION)
    helpers = arm.collections.new(HELPER_COLLECTION)
    for b in arm.bones:
        if b.name.startswith(HELPER):
            helpers.assign(b)
        elif b.name in follow:
            hidden.assign(b)
    hidden.is_visible = helpers.is_visible = False
    # Shown at first: the body, the IK limbs (Rigify's limbs start in IK), the fingers and the root; the FK, tweak and
    # finger detail controls wait (all at once they hid the character).
    for collection in arm.collections_all:
        if collection.name in HIDDEN_AT_FIRST:
            collection.is_visible = False
    for collection in [c for c in bpy.data.collections if c.name not in record["collections_data"]
                       and c.name.startswith("WGT")]:  # Rigify's control shapes, kept with the character
        home = rig.users_collection[0] if rig.users_collection else None
        if home is not None and collection.name not in home.children:
            for parent in [p for p in bpy.data.collections if collection.name in p.children] + [
                    context.scene.collection]:
                if collection.name in parent.children:
                    parent.children.unlink(collection)
            home.children.link(collection)
            layer = _layer_collection(context.view_layer.layer_collection, collection.name)
            if layer is not None:
                layer.exclude = True
    rig.show_in_front = True
    arm[RECORD] = json.dumps(record)
    bpy.data.objects.remove(meta)
    count = sum(1 for b in arm.bones if b.name not in record["bones"] and not b.name.startswith(HELPER))
    return count


HIDDEN_AT_FIRST = {"Torso (Tweak)", "Fingers (Detail)", "Arm.L (FK)", "Arm.R (FK)", "Leg.L (FK)", "Leg.R (FK)",
                   "Arm.L (Tweak)", "Arm.R (Tweak)", "Leg.L (Tweak)", "Leg.R (Tweak)"}


def _layer_collection(layer, name):
    if layer.collection.name == name:
        return layer
    for child in layer.children:
        found = _layer_collection(child, name)
        if found is not None:
            return found
    return None


def _show_side(rig, label, side):
    """Show the limb's `side` ('IK' / 'FK') controls and hide its other ones."""
    kind, s = next((kind, s) for name, kind, s in LIMBS if name == label)
    for which in ("IK", "FK"):
        collection = rig.data.collections_all.get("%s.%s (%s)" % (kind, s, which))
        if collection is not None:
            collection.is_visible = which == side


def remove(context, rig):
    """Take the control layer off `rig` as it was before Add; False when it has none."""
    arm = rig.data
    if arm.get(RECORD) is None:
        return False
    record = json.loads(arm[RECORD])
    keep = set(record["bones"])
    from . import face_board  # the face board stays: it hangs from the DaskToon head, not from the controls
    gone = {b.name for b in arm.bones if b.name not in keep
            and not b.name.startswith((face_board.PREFIX, face_board.FRAME_PREFIX))}
    active = context.view_layer.objects.active
    for pb in rig.pose.bones:
        for con in [c for c in pb.constraints if c.name == FOLLOW]:
            pb.constraints.remove(con)
    for owner in (rig, arm):
        if owner.animation_data is None:
            continue
        for fcurve in list(owner.animation_data.drivers):
            path = fcurve.data_path
            refers = any('"%s"' % name in path for name in gone)
            if not refers:
                for var in fcurve.driver.variables:
                    for target in var.targets:
                        if any('"%s"' % name in (target.data_path or "") or target.bone_target == name
                               for name in gone if name):
                            refers = True
            if refers:
                owner.animation_data.drivers.remove(fcurve)
    _set_mode(context, rig, 'EDIT')
    eb = arm.edit_bones
    for name in gone:
        bone = eb.get(name)
        if bone is not None:
            eb.remove(bone)
    look = eb.get("LookTarget")
    if look is not None:
        look.parent = eb.get(record["look_parent"]) if record["look_parent"] else None
    _set_mode(context, rig, 'OBJECT')
    for collection in [c for c in arm.collections_all if c.name not in record["collections"]
                       and c.name != face_board.COLLECTION]:
        if collection.name in arm.collections_all:
            arm.collections.remove(collection)
    for name in record["collections"]:
        collection = arm.collections_all.get(name)
        if collection is not None:
            collection.is_visible = name in record["visible"]
    for obj in [o for o in bpy.data.objects if o.name not in record["objects"] and o.name.startswith("WGT")]:
        bpy.data.objects.remove(obj)
    for collection in [c for c in bpy.data.collections if c.name not in record["collections_data"] and
                       c.name.startswith("WGT") and not c.objects]:
        bpy.data.collections.remove(collection)
    if "rig_id" in arm:
        del arm["rig_id"]
    del arm[RECORD]
    if active is not None and active.name in context.view_layer.objects:
        _set_mode(context, active, 'OBJECT')
    return True


# --- IK and FK snapping (spec 6.5): the controls of one side put where the other side shows the limb ---

LIMB_KINDS = {
    "Arm": dict(switch="upper_arm_parent.{s}", org=("ORG-upper_arm.{s}", "ORG-forearm.{s}", "ORG-hand.{s}"),
                fk=("upper_arm_fk.{s}", "forearm_fk.{s}", "hand_fk.{s}"), base="upper_arm_ik.{s}", end="hand_ik.{s}",
                pole="upper_arm_ik_target.{s}", reset=(), extra=()),
    "Leg": dict(switch="thigh_parent.{s}", org=("ORG-thigh.{s}", "ORG-shin.{s}", "ORG-foot.{s}", "ORG-toe.{s}"),
                fk=("thigh_fk.{s}", "shin_fk.{s}", "foot_fk.{s}", "toe_fk.{s}"), base="thigh_ik.{s}", end="foot_ik.{s}",
                pole="thigh_ik_target.{s}", reset=("foot_heel_ik.{s}", "foot_spin_ik.{s}"),
                extra=(("toe_ik.{s}", "ORG-toe.{s}"),)),
}
LIMBS = tuple((side + " " + kind, kind, s) for kind in ("Arm", "Leg") for s, side in SIDES)


def limb(rig, label):
    """The bone names of the limb called `label` ("Left Arm"); None when the rig has no controls for it."""
    for name, kind, s in LIMBS:
        if name != label:
            continue
        spec = LIMB_KINDS[kind]

        def f(value):
            return value.format(s=s)
        out = {"switch": f(spec["switch"]), "org": tuple(map(f, spec["org"])), "fk": tuple(map(f, spec["fk"])),
               "base": f(spec["base"]), "end": f(spec["end"]), "pole": f(spec["pole"]),
               "reset": tuple(map(f, spec["reset"])), "extra": tuple((f(a), f(b)) for a, b in spec["extra"])}
        return out if rig.pose.bones.get(out["switch"]) is not None else None
    return None


def _follow_matrix(rig, control, org, now):
    """Where `control` goes to show the limb as `org` is now (armature space): their rest offset kept."""
    bones = rig.data.bones
    return now @ bones[org].matrix_local.inverted() @ bones[control].matrix_local


def _set(context, rig, name, matrix):
    """Pose bone `name` at `matrix` (armature space), its own scale kept: a control in a stretching IK chain would
    otherwise take the stretch as its scale and shrink the limb."""
    pb = rig.pose.bones[name]
    scale = pb.scale.copy()
    pb.matrix = matrix
    pb.scale = scale
    context.view_layer.update()


def _shown(rig, names):
    return {n: rig.pose.bones[n].matrix.copy() for n in names}


def snap(context, rig, label, to):
    """Put the FK controls (`to` 'FK') or the IK controls ('IK') of the limb `label` where the limb is shown now, and
    switch the limb to them: the limb does not move."""
    bones = limb(rig, label)
    if bones is None:
        raise ControlsError(rpt_("This rig has no controls for %s") % label)
    switch = rig.pose.bones[bones["switch"]]
    shown = _shown(rig, bones["org"])
    if to == 'FK':
        for control, org in zip(bones["fk"], bones["org"]):
            _set(context, rig, control, _follow_matrix(rig, control, org, shown[org]))
        switch["IK_FK"] = 1.0
        _show_side(rig, label, 'FK')
    else:
        for name in bones["reset"]:
            rig.pose.bones[name].matrix_basis.identity()
        for _round in range(2):  # the end hangs from the base's parent chain: a second round settles it
            if switch.get("pole_vector"):
                rig.pose.bones[bones["pole"]].matrix = _pole(rig, bones, shown)
            else:
                _set(context, rig, bones["base"], _follow_matrix(rig, bones["base"], bones["org"][0],
                                                                 shown[bones["org"][0]]))
            _set(context, rig, bones["end"], _follow_matrix(rig, bones["end"], bones["org"][2], shown[bones["org"][2]]))
            for control, org in bones["extra"]:
                _set(context, rig, control, _follow_matrix(rig, control, org, shown[org]))
        switch["IK_FK"] = 0.0
        _show_side(rig, label, 'IK')
        rig.update_tag()
        context.view_layer.update()
        if not switch.get("pole_vector"):
            _turn_bend(context, rig, bones, shown)
        _correct_length(context, rig, bones, shown)
    rig.update_tag()
    context.view_layer.update()


def _bend_direction(a, b, c):
    """The way the middle joint b sticks out of the line a-c (unit), or None when the limb is straight."""
    along = c - a
    t = (b - a).dot(along) / max(along.length_squared, 1e-12)
    out = b - (a + along * t)
    return out.normalized() if out.length > 1e-6 else None


def _turn_bend(context, rig, bones, shown):
    """Without a pole, the IK limb bends in the plane its base control's twist gives (Rigify lets that control turn
    about its own Y only): twist it until the middle joint is where it was shown (a few rounds, as the solver
    follows)."""
    want = _bend_direction(*(shown[n].to_translation() for n in bones["org"][:3]))
    if want is None:
        return
    base = rig.pose.bones[bones["base"]]
    mode = base.rotation_mode
    base.rotation_mode = 'QUATERNION'
    from mathutils import Quaternion
    try:
        for _round in range(8):
            a, b, c = (rig.pose.bones[n].matrix.to_translation() for n in bones["org"][:3])
            now = _bend_direction(a, b, c)
            if now is None:
                return
            axis = (c - a).normalized()
            angle = math.atan2(now.cross(want).dot(axis), now.dot(want))
            if abs(angle) < 1e-5:
                return
            y_axis = base.matrix.to_3x3().col[1].normalized()  # the twist turns the limb about the base's own Y
            sign = 1.0 if y_axis.dot(axis) >= 0.0 else -1.0
            base.rotation_quaternion = base.rotation_quaternion @ Quaternion((0.0, 1.0, 0.0), angle * sign)
            context.view_layer.update()
            _set(context, rig, bones["end"], _follow_matrix(rig, bones["end"], bones["org"][2],
                                                            shown[bones["org"][2]]))
    finally:
        if mode != 'QUATERNION':
            q = base.rotation_quaternion.copy()
            base.rotation_mode = mode
            if mode == 'AXIS_ANGLE':
                axis_angle = q.to_axis_angle()
                base.rotation_axis_angle = (axis_angle[1],) + tuple(axis_angle[0])
            else:
                base.rotation_euler = q.to_euler(mode)
        context.view_layer.update()


def _correct_length(context, rig, bones, shown):
    """Rigify's IK chain may stretch: bent, its solver squashes the limb a little. Scale the IK base control until the
    upper bone is as long as it was shown (as Rigify's own snapping does), the end target put back each round."""
    base = rig.pose.bones[bones["base"]]
    upper = bones["org"][0]
    want = (shown[upper].to_3x3().col[1]).length * rig.data.bones[upper].length
    for _round in range(6):
        pb = rig.pose.bones[upper]
        now = (pb.tail - pb.head).length
        if now <= 1e-9 or abs(now - want) < 1e-5:
            return
        base.scale = base.scale * (want / now)
        context.view_layer.update()
        _set(context, rig, bones["end"], _follow_matrix(rig, bones["end"], bones["org"][2], shown[bones["org"][2]]))


def _pole(rig, bones, shown):
    """The pole target in the plane of the limb's bend, in front of the middle joint, one upper bone's length away."""
    from mathutils import Matrix as _Matrix
    a, b, c = (shown[n].to_translation() for n in bones["org"][:3])
    along = c - a
    t = (b - a).dot(along) / max(along.length_squared, 1e-12)
    out = b - (a + along * t)
    if out.length < 1e-6:
        out = shown[bones["org"][0]].to_3x3() @ Vector((0.0, 0.0, 1.0))
    place = b + out.normalized() * (b - a).length
    current = rig.pose.bones[bones["pole"]].matrix
    return _Matrix.Translation(place) @ current.to_3x3().to_4x4()


# Control collections shown in the Controls section: (Rigify's collection, label)
COLLECTIONS = (("Torso", "Torso"), ("Torso (Tweak)", "Torso (Tweak)"), ("Arm.L (IK)", "Left Arm IK"),
               ("Arm.L (FK)", "Left Arm FK"), ("Arm.R (IK)", "Right Arm IK"), ("Arm.R (FK)", "Right Arm FK"),
               ("Leg.L (IK)", "Left Leg IK"), ("Leg.L (FK)", "Left Leg FK"), ("Leg.R (IK)", "Right Leg IK"),
               ("Leg.R (FK)", "Right Leg FK"), ("Fingers", "Fingers"), ("Fingers (Detail)", "Fingers (Detail)"),
               ("Arm.L (Tweak)", "Left Arm (Tweak)"), ("Arm.R (Tweak)", "Right Arm (Tweak)"),
               ("Leg.L (Tweak)", "Left Leg (Tweak)"), ("Leg.R (Tweak)", "Right Leg (Tweak)"), ("Root", "Root"))


def key_limb(rig, label, frame):
    """Keys on the limb's controls and its IK/FK switch at `frame` (after a snap, with auto keying on)."""
    bones = limb(rig, label)
    if bones is None:
        return
    names = list(bones["fk"]) + [bones["base"], bones["end"], bones["pole"]] + list(bones["reset"]) + [
        c for c, _o in bones["extra"]]
    for name in names:
        pb = rig.pose.bones[name]
        for path in ("location", "rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler",
                     "scale"):
            pb.keyframe_insert(path, frame=frame, group=name)
    rig.pose.bones[bones["switch"]].keyframe_insert('["IK_FK"]', frame=frame, group=bones["switch"])
