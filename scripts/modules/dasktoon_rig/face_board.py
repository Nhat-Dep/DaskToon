# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The face board (docs/superpowers/specs/2026-11-06-dasktoon-rig-controls-design.md, section 8): knobs on a board
beside the head that drive the character's expression shape keys, so a face is posed and keyed like the body.

A joystick moves in the board's plane, each of its four ways driving one shape key; a slider only moves up. A knob
goes REACH (x the character's height) at most; its driver is clamp(v / reach), a simple expression that runs without
scripts. Only the knobs whose shape keys the character has are made; several meshes with one key name (face, brows
and lashes apart) share the knob. What the board drives is recorded on the armature (RECORD), so the tools that set
or key expressions (set_value, knob_path) go through the knobs: a driven key ignores its own value."""

import json

import bpy
from bpy.app.translations import pgettext_iface as iface_
from mathutils import Matrix, Vector

RECORD = "dt_face_board"
PREFIX, FRAME_PREFIX = "FB_", "FBF_"
BOARD = "FB_Board"
COLLECTION = "Face Board"
TEXT_PREFIX = "FB Label "
REACH = 0.012 / 1.6  # of the height: how far a knob goes
# Where the board stands from the head, in the character's height (temp_2_1, 1.6 tall: at least 0.27 to the side, 0.10
# in front, its top 0.06 above the head joint plus its height; further out when the hair or a hat reaches further).
SIDE, FRONT, UP = 0.27 / 1.6, 0.10 / 1.6, 0.06 / 1.6

# (knob, label, {way: names of the shape keys it drives, most telling first}); ways: UP DOWN OUT IN (out: away from
# the face's middle, the character's left being +X), or LEFT RIGHT for the gaze.
JOYSTICKS = (
    ("Brows", "Brows", {"UP": ("brow_up", "browinnerup", "上", "b_up_add", "brows_up"),
                        "DOWN": ("brow_down", "browdown", "下", "b_down_add", "brows_down"),
                        "OUT": ("brow_angry", "怒り", "b_anger", "angry_brows"),
                        "IN": ("brow_sad", "困る", "b_sad", "sad_brows")}),
    ("Eyes", "Eyes", {"UP": ("eye_wide", "eyewide", "びっくり", "e_stare", "eyes_wide"),
                      "DOWN": ("blink", "eyeblink", "まばたき", "e_close", "fcl_eye_close"),
                      "OUT": ("eye_sharp", "ｷﾘｯ", "キリッ", "e_anger"),
                      "IN": ("eye_sleepy", "じと目", "e_insipid", "なごみ")}),
    ("Wink", "Wink", {"OUT": ("blink_l", "blinkleft", "eyeblinkleft", "fcl_eye_close_l"),
                      "IN": ("blink_r", "blinkright", "eyeblinkright", "fcl_eye_close_r")}),
    ("Gaze", "Gaze", {"UP": ("lookup", "look_up", "pupil_up", "eyelookupleft"),
                      "DOWN": ("lookdown", "look_down", "pupil_down", "eyelookdownleft"),
                      "LEFT": ("lookleft", "look_left", "pupil_l"), "RIGHT": ("lookright", "look_right", "pupil_r")}),
    ("Mouth", "Mouth", {"UP": ("mouthsmile", "mouth_smile", "口角上げ", "m_smile"),
                        "DOWN": ("mouthfrown", "mouth_frown", "口角下げ", "∧", "m_anger"),
                        "OUT": ("mouthstretch", "mouth_wide", "口横広げ"),
                        "IN": ("mouthpucker", "mouth_pucker", "口横缩げ")}),
)
SLIDERS = (
    ("A", "A", ("a", "aa", "あ", "fcl_mth_a", "jawopen")), ("I", "I", ("i", "ih", "い", "fcl_mth_i")),
    ("U", "U", ("u", "ou", "う", "fcl_mth_u")), ("E", "E", ("e", "ee", "え", "fcl_mth_e")),
    ("O", "O", ("o", "oh", "お", "fcl_mth_o")),
    ("Joy", "Joy", ("joy", "happy", "fcl_all_joy")), ("Angry", "Angry", ("angry", "fcl_all_angry")),
    ("Sorrow", "Sorrow", ("sorrow", "sad", "fcl_all_sorrow")), ("Fun", "Fun", ("fun", "relaxed", "fcl_all_fun")),
    ("Surprised", "Surprised", ("surprised", "fcl_all_surprised")),
    ("Blush", "Blush", ("blush", "照れ", "cheek_blush")), ("Tongue", "Tongue", ("tongue", "tongueout", "てへぺろ")),
    ("HeartEyes", "Heart Eyes", ("heart_eyes", "はぁと", "eye_heart")),
    ("StarEyes", "Star Eyes", ("star_eyes", "星目", "eye_star")), ("Grin", "Grin", ("grin", "にやり", "m_laugh")),
)
SLIDER_ROWS = (("A", "I", "U", "E", "O"), ("Joy", "Angry", "Sorrow", "Fun", "Surprised"),
               ("Blush", "Tongue", "HeartEyes", "StarEyes", "Grin"))
# A way: (local axis of the knob, sign). Knobs stand upright on the board: local X is the character's left (+X),
# local Y up.
WAYS = {"UP": (1, 1.0), "DOWN": (1, -1.0), "OUT": (0, 1.0), "IN": (0, -1.0), "LEFT": (0, 1.0), "RIGHT": (0, -1.0)}


def meshes_of(rig):
    return [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.data.shape_keys is not None
            and any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers)]


def _find(meshes, names):
    """[(mesh, key name)] of the first of `names` (any case) some mesh has; a name used by several meshes gives all."""
    for name in names:
        found = []
        for obj in meshes:
            for block in obj.data.shape_keys.key_blocks[1:]:
                if block.name.lower() == name.lower():
                    found.append((obj, block.name))
        if found:
            return found
    return []


def plan(rig):
    """[(knob, label, kind 'STICK' / 'SLIDER', {way: [(mesh, key)]})] of the knobs the character's keys allow; a key
    is driven by one knob only (the first that takes it)."""
    meshes = meshes_of(rig)
    taken = set()
    out = []

    def take(found):
        keep = [(obj, key) for obj, key in found if (obj.name, key) not in taken]
        taken.update((obj.name, key) for obj, key in keep)
        return keep
    for knob, label, ways in JOYSTICKS:
        got = {way: take(_find(meshes, names)) for way, names in ways.items()}
        got = {way: found for way, found in got.items() if found}
        if got:
            out.append((knob, label, 'STICK', got))
    for knob, label, names in SLIDERS:
        found = take(_find(meshes, names))
        if found:
            out.append((knob, label, 'SLIDER', {"UP": found}))
    return out


def has_board(rig):
    return rig is not None and rig.type == 'ARMATURE' and RECORD in rig.data


def _height(rig):
    zs = [v for b in rig.data.bones if b.use_deform for v in (b.head_local.z, b.tail_local.z)]
    return (max(zs) - min(zs)) if zs else 1.6


# The grid, in the character's height: joysticks two a row, sliders five a row with smaller labels under them.
STICK_X, STICK_Y = 0.05, 0.055
SLIDER_X, SLIDER_Y = 0.036, 0.042
STICK_TEXT, SLIDER_TEXT, TITLE_TEXT = 0.011, 0.0075, 0.014
MARGIN = 0.03  # from the outermost point of the character beside the head to the board


def _layout(found, height):
    """{knob: (x, y)} on the board for the knobs `found`, from the board's top middle (y down is negative), and the
    board's (width, height)."""
    names = [knob for knob, _l, _k, _w in found]
    sticks = [n for n in ("Brows", "Eyes", "Wink", "Gaze", "Mouth") if n in names]
    out = {}
    y = -STICK_Y * 0.6 * height
    for i, name in enumerate(sticks):
        out[name] = ((-0.5 if i % 2 == 0 else 0.5) * STICK_X * height, y - (i // 2) * STICK_Y * height)
    if sticks:
        y -= ((len(sticks) + 1) // 2) * STICK_Y * height
    for row in SLIDER_ROWS:
        present = [n for n in row if n in names]
        if not present:
            continue
        for j, name in enumerate(present):
            out[name] = ((j - (len(present) - 1) / 2.0) * SLIDER_X * height, y)
        y -= SLIDER_Y * height
    width = max([abs(x) for x, _y in out.values()] + [0.0]) * 2.0 + SLIDER_X * height
    return out, (width, -y)


def _beside_head(rig, height):
    """How far out (+X, the character's left) the character reaches round the head: the board goes beyond it."""
    head = rig.matrix_world @ rig.data.bones["Head"].head_local
    out = head.x
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers):
            continue
        import numpy as np
        co = np.empty(len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get("co", co)
        mw = np.array(obj.matrix_world)
        world = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        near = world[(world[:, 2] > head.z - 0.05 * height) & (world[:, 2] < head.z + 0.25 * height)]
        if len(near):
            out = max(out, float(near[:, 0].max()))
    return rig.matrix_world.inverted() @ (head.__class__((out, head.y, head.z)))


def build(context, rig):
    """The board on `rig` for the keys its meshes have; returns the number of knobs (0: no key to drive, no board)."""
    if has_board(rig):
        remove(context, rig)
    found = plan(rig)
    if not found:
        return 0
    height = _height(rig)
    reach = REACH * height
    head = rig.data.bones["Head"]  # with the controls on, it follows Rigify's head control
    places, (board_width, board_height) = _layout(found, height)
    reach_out = _beside_head(rig, height).x
    top = head.head_local + Vector((0.0, -FRONT * height, UP * height + board_height / 2.0))
    top.x = max(head.head_local.x + SIDE * height, reach_out + MARGIN * height + board_width / 2.0)
    middle = top  # places are from the board's top middle
    knob_length = reach * 1.2
    view_layer = context.view_layer
    previous = view_layer.objects.active
    if previous is not None and previous.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        eb = rig.data.edit_bones
        board = eb.new(BOARD)
        board.head = top - Vector((0.0, 0.0, board_height))
        board.tail = top.copy()
        board.align_roll(Vector((0.0, -1.0, 0.0)))
        board.parent = eb[head.name]
        board.use_deform = False
        for knob, _text, kind, _ways in found:
            x, y = places[knob]
            at = middle + Vector((x, 0.0, y))
            frame = eb.new(FRAME_PREFIX + knob)
            frame.head, frame.tail = at, at + Vector((0.0, 0.0, knob_length))
            frame.align_roll(Vector((0.0, -1.0, 0.0)))
            frame.parent, frame.use_deform = board, False
            bone = eb.new(PREFIX + knob)
            bone.head, bone.tail = at, at + Vector((0.0, 0.0, knob_length * 0.6))
            bone.align_roll(Vector((0.0, -1.0, 0.0)))
            bone.parent, bone.use_deform = frame, False
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        view_layer.objects.active = previous
    collection = rig.data.collections.get(COLLECTION) or rig.data.collections.new(COLLECTION)
    collection.is_visible = True
    record = {"reach": reach, "keys": [], "texts": []}
    for knob, label, kind, ways in found:
        frame, bone = rig.data.bones[FRAME_PREFIX + knob], rig.data.bones[PREFIX + knob]
        for b in (frame, bone, rig.data.bones[BOARD]):
            collection.assign(b)
        frame.hide_select = True
        frame.color.palette, bone.color.palette = 'THEME03', 'THEME09'
        pb = rig.pose.bones[PREFIX + knob]
        pb.lock_rotation = pb.lock_scale = (True, True, True)
        pb.lock_rotation_w = True
        pb.lock_location = (kind == 'SLIDER', False, True)
        limit = pb.constraints.new('LIMIT_LOCATION')
        limit.owner_space = 'LOCAL'
        limit.use_transform_limit = True
        for axis in "xyz":
            setattr(limit, "use_min_" + axis, True)
            setattr(limit, "use_max_" + axis, True)
        limit.min_x, limit.max_x = (0.0, 0.0) if kind == 'SLIDER' else (-reach, reach)
        limit.min_y, limit.max_y = (0.0 if kind == 'SLIDER' else -reach), reach
        for way, keys in ways.items():
            axis, sign = WAYS[way]
            for obj, key in keys:
                _drive(obj, key, rig, PREFIX + knob, axis, sign, reach)
                record["keys"].append([obj.name, key, PREFIX + knob, axis, sign])
        record["texts"].append(_label(context, rig, knob, label, places[knob], height, top,
                                      SLIDER_TEXT if kind == 'SLIDER' else STICK_TEXT))
    record["texts"].append(_label(context, rig, None, "EXPRESSIONS", (0.0, reach), height, top, TITLE_TEXT))
    rig.data[RECORD] = json.dumps(record)
    return len(found)


def _drive(obj, key, rig, bone, axis, sign, reach):
    shape = obj.data.shape_keys
    path = 'key_blocks["%s"].value' % key.replace('"', '\\"')
    shape.driver_remove(path)
    fcurve = shape.driver_add(path)
    driver = fcurve.driver
    driver.type = 'SCRIPTED'
    var = driver.variables.new()
    var.name = "v"
    var.type = 'TRANSFORMS'
    target = var.targets[0]
    target.id = rig
    target.bone_target = bone
    target.transform_type = 'LOC_X' if axis == 0 else 'LOC_Y'
    target.transform_space = 'LOCAL_SPACE'
    driver.expression = "clamp(%sv / %.6f, 0.0, 1.0)" % ("" if sign > 0 else "-", reach)
    for modifier in list(fcurve.modifiers):
        fcurve.modifiers.remove(modifier)


def _label(context, rig, knob, text, place, height, top, size):
    """A line of 3D text on the board under the knob (or the title), in the interface language; not rendered."""
    curve = bpy.data.curves.new(TEXT_PREFIX + (knob or "Title"), 'FONT')
    curve.body = iface_(text, "DaskToon")
    curve.size = height * size
    curve.align_x = 'CENTER'
    obj = bpy.data.objects.new(curve.name, curve)
    for collection in rig.users_collection:
        collection.objects.link(obj)
    obj.parent = rig
    obj.parent_type = 'BONE'
    obj.parent_bone = BOARD
    # Bone parenting places the child at the bone's tail: put it back at its place on the board, upright, facing front,
    # a label under its knob, out of the knob's way.
    below = 0.0 if knob is None else size * height * 1.6 + REACH * height
    world = rig.matrix_world @ Matrix.Translation(top + Vector((place[0], -0.002, place[1] - below)))
    world = world @ Matrix.Rotation(1.5707963, 4, 'X')
    context.view_layer.update()
    obj.matrix_world = world
    obj.hide_render = True
    obj.hide_select = True
    obj.show_in_front = True
    return obj.name


def remove(context, rig):
    """Take the board off: its bones, the drivers it put on shape keys, its labels. False when there is none."""
    if not has_board(rig):
        return False
    record = json.loads(rig.data[RECORD])
    for mesh_name, key, _bone, _axis, _sign in record["keys"]:
        obj = bpy.data.objects.get(mesh_name)
        shape = obj.data.shape_keys if obj is not None and obj.type == 'MESH' else None
        if shape is not None and shape.key_blocks.get(key) is not None:
            shape.driver_remove('key_blocks["%s"].value' % key.replace('"', '\\"'))
    for name in record["texts"]:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            curve = obj.data
            bpy.data.objects.remove(obj)
            if curve.users == 0:
                bpy.data.curves.remove(curve)
    view_layer = context.view_layer
    previous = view_layer.objects.active
    if previous is not None and previous.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        eb = rig.data.edit_bones
        for bone in [b for b in eb if b.name.startswith((PREFIX, FRAME_PREFIX))]:
            eb.remove(bone)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        view_layer.objects.active = previous
    collection = rig.data.collections.get(COLLECTION)
    if collection is not None:
        rig.data.collections.remove(collection)
    del rig.data[RECORD]
    return True


def _rigs():
    return [obj for obj in bpy.data.objects if obj.type == 'ARMATURE' and RECORD in obj.data]


def knob_of(obj, key):
    """(rig, knob bone, local axis, sign, reach) of the knob driving shape key `key` of mesh `obj`, or None."""
    for rig in _rigs():
        record = json.loads(rig.data[RECORD])
        for mesh_name, name, bone, axis, sign in record["keys"]:
            if mesh_name == obj.name and name == key and rig.pose.bones.get(bone) is not None:
                return rig, bone, axis, sign, record["reach"]
    return None


def set_value(obj, block, value):
    """Show shape key `block` of mesh `obj` at `value`: through its knob when the board drives it, else its value."""
    found = knob_of(obj, block.name)
    if found is None:
        block.value = value
        return
    rig, bone, axis, sign, reach = found
    location = rig.pose.bones[bone].location
    location[axis] = sign * max(0.0, min(1.0, value)) * reach


def knob_path(obj, key):
    """(id to key, data path, index, scale) to key shape key `key` of `obj` at a value: its knob's location when the
    board drives it (value x scale), else the key's own value."""
    found = knob_of(obj, key)
    if found is None:
        return obj.data.shape_keys, 'key_blocks["%s"].value' % key, -1, 1.0
    rig, bone, axis, sign, reach = found
    return rig, 'pose.bones["%s"].location' % bone, axis, sign * reach
