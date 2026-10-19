# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime rig, R1 (docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md, section 7): Add › Armature › Anime
Humanoid; the Anime Rig panel in Properties › Object Data of an armature (Joints, Parts, Regions, Build) and of a mesh
(its parts, Add Part from Selection, Lock from Selection, the region colors while painting). The regions and locks:
docs/superpowers/specs/2026-10-13-dasktoon-rig-regions-design.md, section 6. The auto rig (Anime Humanoid on selected
meshes) and the Check panel: docs/superpowers/specs/2026-10-14-dasktoon-auto-rig-design.md. The work is done by the
dasktoon_rig module."""

import math

import bpy
from bpy.app.handlers import persistent
from bpy.app.translations import pgettext_iface as iface_, pgettext_rpt as rpt_
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, Panel, PropertyGroup, UIList

ROLE_ITEMS = (
    ('BODY', "Body", "Skin and face: automatic weights from the body bones", 'USER', 0),
    ('CLOTHING', "Clothing", "Follows the body: weights copied from the nearest Body surface", 'MATCLOTH', 1),
    ('ACCESSORY', "Accessory", "Rigid on one bone", 'PINNED', 2),
    ('HAIR', "Hair", "A chain of bones for each long lock", 'STRANDS', 3),
    ('SKIRT', "Skirt", "Chains of bones around the hips", 'MOD_CLOTH', 4),
    ('JAW', "Jaw", "The lower jaw and chin: follows the Jaw bone, blended into the face", 'MESH_CAPSULE', 5),
    ('FLAT_EYE', "Flat Eye", "An iris drawn on the face: slides on its UVs as the eye looks around", 'HIDE_OFF', 6),
    ('MOUTH_2D', "2D Mouth", "A drawn mouth: shows one cell of its texture atlas, chosen by the dt_mouth property",
     'IMAGE_DATA', 7),
)
ROLE_ICONS = {item[0]: item[3] for item in ROLE_ITEMS}
# The body regions (rig regions spec 3.1), each with the strip color icon nearest its paint color.
REGION_ITEMS = (
    ('HEAD', "Head", "The head, and the locks hanging from it", 'STRIP_COLOR_03', 0),
    ('TORSO', "Torso", "The body from the hips to the neck", 'STRIP_COLOR_05', 1),
    ('ARM_L', "Left Arm", "The character's left arm and hand", 'STRIP_COLOR_01', 2),
    ('ARM_R', "Right Arm", "The character's right arm and hand", 'STRIP_COLOR_02', 3),
    ('LEG_L', "Left Leg", "The character's left leg and foot", 'STRIP_COLOR_04', 4),
    ('LEG_R', "Right Leg", "The character's right leg and foot", 'STRIP_COLOR_06', 5),
)
PALETTE = "DaskToon Regions"
# The test poses of the Check (auto rig spec 3), in the order of check.POSES. Their names have the "DaskToon"
# translation context: Blender's Vietnamese for "Wave" is the modifier.
POSE_ITEMS = (
    ('ARMS_UP', "Arms Up", "Raise both arms"),
    ('SIT', "Sit", "Bend the thighs forward and the knees down, as if sitting"),
    ('TURN_HEAD', "Turn Head", "Turn the head to the left"),
    ('WAVE', "Wave", "Raise the right arm and wave the forearm"),
    ('REST', "Rest", "Every bone back at rest"),
)
# The joint at the head of each bone the Check looks at (auto rig spec 4.1), as its sentences name it.
JOINT_NAMES = {
    "LeftUpperArm": "Left shoulder", "RightUpperArm": "Right shoulder",
    "LeftLowerArm": "Left elbow", "RightLowerArm": "Right elbow",
    "LeftHand": "Left wrist", "RightHand": "Right wrist",
    "LeftUpperLeg": "Left hip", "RightUpperLeg": "Right hip",
    "LeftLowerLeg": "Left knee", "RightLowerLeg": "Right knee",
    "LeftFoot": "Left ankle", "RightFoot": "Right ankle",
    "Neck": "Base of the neck", "Head": "Head joint",
}
ISSUE_ICONS = {'JOINT': 'BONE_DATA', 'STRETCH': 'MOD_SIMPLEDEFORM', 'FACING': 'ORIENTATION_GLOBAL'}


def _is_mesh(_self, obj):
    return obj.type == 'MESH'


def _sway_changed(self, _context):
    from dasktoon_rig import sway
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj.data == self.id_data:
            sway.sync(obj)


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
    # Its own translation context: Blender's Vietnamese for "Chains" means jewellery chains.
    chain_count: IntProperty(name="Chains", description="Number of chains around the skirt", default=8, min=3, max=24,
                             translation_context="DaskToon")
    stiffness: FloatProperty(name="Stiffness", description="How strongly the chain springs back to its pose",
                             default=1.0, min=0.0, max=4.0, update=_sway_changed)
    gravity: FloatProperty(name="Gravity", description="How strongly the chain is pulled down", default=0.2, min=0.0,
                           max=2.0, update=_sway_changed)
    drag: FloatProperty(name="Drag", description="How quickly the swing dies down: 0 keeps swinging, 1 stops at once",
                        default=0.4, min=0.0, max=1.0, update=_sway_changed)
    radius: FloatProperty(name="Radius", description="How far each joint keeps from the colliders", default=0.03,
                          min=0.0, max=1.0, unit='LENGTH', update=_sway_changed)
    eye_side: EnumProperty(
        name="Side", description="Which eye the iris belongs to",
        items=[('AUTO', "Automatic", "The side the part lies on"),
               ('LEFT', "Left", "The character's left eye"),
               ('RIGHT', "Right", "The character's right eye")],
        default='AUTO')
    eye_range: FloatProperty(
        name="Range", description="How far the iris slides on its UVs when the eye turns all the way; negative turns "
        "it the other way", default=0.1, min=-1.0, max=1.0)
    mouth_rows: IntProperty(name="Rows", description="Rows of mouth cells in the atlas texture", default=2, min=1,
                            max=8)
    mouth_columns: IntProperty(name="Columns", description="Columns of mouth cells in the atlas texture", default=4,
                               min=1, max=8)
    sway_in_unity: EnumProperty(
        name="Sway in Unity",
        description="How the chain sways in Unity",
        items=[
            ('RUNTIME', "Runtime", "DaskToon's spring bone script sways the chain while the game runs"),
            ('BAKED', "Baked", "Unity plays the sway baked into the exported animation"),
        ],
        default='RUNTIME',
    )
    made_by_recognize: BoolProperty(
        name="Made by Recognize", description="A lock Recognize made from pieces hanging from the head; Recognize makes "
        "it again (keeping its role and settings)")


class DaskRigCollider(PropertyGroup):
    """A capsule along a bone that hair and skirts do not go through"""
    bone: StringProperty(name="Bone", description="Bone the capsule runs along, from its head to its tail")
    radius: FloatProperty(name="Radius", description="Radius of the capsule, in armature units", default=0.05,
                          min=0.0, unit='LENGTH', update=_sway_changed)


def _shoulder_changed(self, _context):
    from dasktoon_rig import shoulders
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj.data == self.id_data:
            shoulders.sync(obj)


def _look_changed(self, _context):
    from dasktoon_rig import look
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj.data == self.id_data:
            look.sync_limits(obj)


# A spot the Check found (auto rig spec 4); its message is written when the panel draws. A stretched spot keeps its
# vertices in the item's "vertices" property.
class DaskRigIssue(PropertyGroup):
    """A spot the Check of the auto rig found"""
    kind: EnumProperty(items=[('JOINT', "", ""), ('STRETCH', "", ""), ('ROLE', "", ""), ('FACING', "", "")],
                       default='JOINT')
    bone: StringProperty()
    part: StringProperty()
    object: PointerProperty(type=bpy.types.Object)
    pose: StringProperty()
    region: StringProperty()
    role: StringProperty()
    below_waist: BoolProperty()  # a ROLE spot: only the part below the waist looks like it


class DaskRig(PropertyGroup):
    """The parts of an anime rig"""
    parts: CollectionProperty(type=DaskRigPart, name="Parts", description="Parts of the character")
    active_part_index: IntProperty(name="Active Part", description="Part shown below the list", default=0)
    colliders: CollectionProperty(type=DaskRigCollider, name="Colliders",
                                  description="Capsules that hair and skirts do not go through; Build Rig makes them")
    live_sway: BoolProperty(name="Live Sway", description="Sway hair and skirts while the animation plays",
                            default=True, update=_sway_changed)
    look_yaw_limit: FloatProperty(name="Side Limit", description="How far the eyes turn to the side to follow "
                                  "LookTarget", subtype='ANGLE', default=0.5235988, min=0.0, max=1.5707963,
                                  update=_look_changed)
    look_pitch_limit: FloatProperty(name="Up and Down Limit", description="How far the eyes turn up and down to "
                                    "follow LookTarget", subtype='ANGLE', default=0.3490659, min=0.0, max=1.5707963,
                                    update=_look_changed)
    highlight_part: BoolProperty(name="Highlight Part", default=True,
                                 description="Draw the faces of the part chosen in the list in the 3D view, at rest")
    issues: CollectionProperty(type=DaskRigIssue, name="Spots to Look At",
                               description="What the Check found: joints outside the body, stretched spots, roles that "
                               "look wrong")
    checked: BoolProperty(name="Checked", description="The Check has run since the rig was built")
    shoulder_follow: FloatProperty(name="Shoulder Follows Arm", default=1.0, min=0.0, max=1.0, subtype='FACTOR',
                                   description="How much the shoulders lift when the arms rise above them: 1 as a "
                                   "person's, 0 not at all", update=_shoulder_changed)
    bend_fixes: BoolProperty(name="Bend Fixes", default=True,
                             description="Build Rig makes a shape key for each knee, elbow, hip and shoulder that keeps "
                             "the joint round as it bends, in DaskToon and in Unity")


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


def fit_to_parts(context, rig):
    """Fit the skeleton of `rig` to the meshes of its parts, reading the body's shape from the Body and Clothing parts
    (hair, a skirt or a held staff is no limb). A character whose feet face another way than the skeleton's front (-Y)
    is turned round on the spot first. Returns that turn (radians about +Z, 0 when none)."""
    from dasktoon_rig import facing, parts as rig_parts, skeleton
    parts = [part for part in rig.data.dasktoon_rig.parts if part.object is not None and part.object.type == 'MESH']
    meshes = list(dict.fromkeys(part.object for part in parts))
    body = list(dict.fromkeys(part.object for part in parts if part.role in {'BODY', 'CLOTHING'}))
    skin = list(dict.fromkeys(part.object for part in parts if part.role == 'BODY'))
    turn = facing.face_front(context, meshes, body=body or None)
    eyes = []  # the eyeballs (Accessories named as eyes) and flat eyes: the eye joints go to their middles
    for part in parts:
        if part.role == 'FLAT_EYE' or (part.role == 'ACCESSORY' and rig_parts.is_eye(part.name)):
            try:
                world, _edges = rig_parts.mesh_arrays(part.object)
                eyes.append(world[rig_parts.part_vertices(part)])
            except rig_parts.PartError:
                continue
    skeleton.fit(context, rig, meshes, body=body or None, skin=skin or None, eyes=eyes or None)
    return turn


def skirt_below_waist(rig, part):
    """Make the part of `part`'s mesh below the waist a Skirt part of its own (the vertex group "<part> Skirt"); returns
    the new part, or None when nothing of it is below the waist."""
    from dasktoon_rig import check
    obj = part.object
    vertices = [int(v) for v in check.below_waist(rig, obj)]
    if not vertices:
        return None
    name = "%s Skirt" % part.name
    group = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
    group.remove(list(range(len(obj.data.vertices))))
    group.add(vertices, 1.0, 'REPLACE')
    return add_part(rig, obj, 'SKIRT', name=name, scope='VERTEX_GROUP', vertex_group=group.name)


def skirts_below_waist(rig):
    """The auto rig makes a skirt of the part below the waist of each Clothing mesh whose lower part looks like one
    (the user chose this, 2026-10-19, over the Check asking). Returns the names of those parts."""
    from dasktoon_rig import check
    parts = [part for part in rig.data.dasktoon_rig.parts if part.object is not None]
    names = [name for name, role, lower in check.role_issues(rig, parts) if role == 'SKIRT' and lower]
    made = []
    for name in names:  # looked up again: adding a part may move the parts in memory
        part = next(part for part in rig.data.dasktoon_rig.parts if part.name == name)
        if skirt_below_waist(rig, part) is not None:
            made.append(name)
    return made


def eyes_off_the_head(rig):
    """An Accessory that only "mat" (Vietnamese eyes, unaccented) says is eyes, and which is not on the head in small
    pieces, is Clothing (the user's choice, 2026-10-19). Returns the names of those parts."""
    from dasktoon_rig import parts as rig_parts
    out = []
    for part in rig.data.dasktoon_rig.parts:
        if (part.role == 'ACCESSORY' and part.scope == 'OBJECT' and part.object is not None
                and part.object.type == 'MESH' and rig_parts.eye_by_mat_only(part.name)
                and not rig_parts.on_head_in_small_pieces(rig, part.object)):
            part.role = 'CLOTHING'
            out.append(part.name)
    return out


def report_turn(operator, turn):
    if turn:
        operator.report({'WARNING'}, rpt_("The character did not face the front (-Y): it was turned %d° on the spot, "
                                          "as the skeleton and Unity need") % abs(round(math.degrees(turn))))


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


def show_rig_tab(context):
    """Every Properties editor of the windows shows the object data tab, where Anime Rig is."""
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'PROPERTIES':
                try:
                    area.spaces.active.context = 'DATA'
                except TypeError:  # not a tab of what the editor shows
                    pass


def build_rig(context, rig):
    """Build `rig` as Build Rig does: the regions and locks are recognized first when they never were (rig regions spec
    5). Returns (the build result, the Analysis when it recognized or None); raises build.BuildError."""
    from dasktoon_rig import build, parts as rig_parts, regions
    build.check(rig, list(rig.data.dasktoon_rig.parts))  # its message, before recognizing anything
    recognized = None
    if not regions.has_layers(rig):
        try:
            recognized = regions.recognize(context, rig)
        except rig_parts.PartError:
            pass  # Build reports the part
    hide_spot()  # its weights change
    return build.build(context, rig, list(rig.data.dasktoon_rig.parts)), recognized


def run_check(context, rig):
    """The Check (auto rig spec 4): a new list on the rig, nothing of the old one lit up. Returns how many spots."""
    from dasktoon_rig import check
    hide_spot()
    return check.run(context, rig)


def check_summary(count):
    return rpt_("Spots to look at: %d") % count if count else rpt_("Nothing to fix found")


class DASKTOON_OT_rig_add_humanoid(Operator):
    """Add the DaskToon standard skeleton; with meshes selected, rig them in one go and check the rig"""
    bl_idname = "dasktoon.rig_add_humanoid"
    bl_label = "Anime Humanoid"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        from dasktoon_rig import build, skeleton
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        height, location = skeleton.placement(meshes, context.scene.cursor.location)
        rig = skeleton.create_humanoid(context, height, location)
        if not meshes:
            for obj in context.view_layer.objects:
                obj.select_set(obj == rig)
            context.view_layer.objects.active = rig
            self.report({'INFO'}, rpt_("Select the character's meshes, add them in Anime Rig › Parts, then press Fit "
                                       "to Parts and Build Rig"))
            return {'FINISHED'}
        # The auto rig (auto rig spec 2): parts, fitted, regions and locks, built, checked.
        progress = context.window_manager
        progress.progress_begin(0, 3)
        try:
            add_meshes(rig, meshes)
            report_turn(self, fit_to_parts(context, rig))
            for name in eyes_off_the_head(rig):
                self.report({'INFO'}, rpt_("%s is not on the head: Clothing, not eyes") % name)
            made = skirts_below_waist(rig)
            if made:
                self.report({'INFO'}, rpt_("The part below the waist became a skirt: %s") % ", ".join(made))
            for obj in context.view_layer.objects:
                obj.select_set(obj == rig)
            context.view_layer.objects.active = rig
            show_rig_tab(context)
            progress.progress_update(1)
            try:
                result, _recognized = build_rig(context, rig)
            except build.BuildError as ex:  # the skeleton stays, fitted: fix what it says, then Build Rig
                self.report({'ERROR'}, rpt_("The skeleton is added and fitted, but the rig could not be built: %s")
                            % ex)
                return {'FINISHED'}
            progress.progress_update(2)
            for warning in result.warnings:
                self.report({'WARNING'}, warning)
            count = run_check(context, rig)
        finally:
            progress.progress_end()
        if count:
            self.report({'INFO'}, rpt_("Rig built. The Check found spots to look at (%d): see Anime Rig › Check")
                        % count)
        else:
            self.report({'INFO'}, rpt_("Rig built. The Check found nothing to fix; try the test poses in Anime Rig › "
                                       "Check"))
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
        report_turn(self, fit_to_parts(context, rig_of(context)))
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
            result, recognized = build_rig(context, rig)
        except build.BuildError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        for warning in result.warnings:
            self.report({'WARNING'}, warning)
        if recognized is not None:
            self.report({'INFO'}, rpt_("Recognized the regions and %d locks first") % len(recognized.locks))
        self.report({'INFO'}, result.summary())
        if rig.data.dasktoon_rig.checked:  # the list showing was for the rig before this build
            self.report({'INFO'}, check_summary(run_check(context, rig)))
        return {'FINISHED'}


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
        group_name = "DT_%s" % name
        group = obj.vertex_groups.new(name=group_name)
        group.add(selected, 1.0, 'REPLACE')
        bpy.ops.object.mode_set(mode='EDIT')
        add_part(rig, obj, self.role, name=name, scope='VERTEX_GROUP', vertex_group=group.name)
        self.report({'INFO'}, rpt_("Added part %s to %s") % (name, rig.name))
        return {'FINISHED'}


class DASKTOON_OT_rig_lock_from_selection(Operator):
    """Make the pieces under the selected vertices one lock, rigid on the head (with the role Hair it sways)"""
    bl_idname = "dasktoon.rig_lock_from_selection"
    bl_label = "Lock from Selection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT' and bool(humanoid_rigs(context.scene))

    def execute(self, context):
        from dasktoon_rig import parts as rig_parts, regions
        obj = context.object
        rig = find_rig(context, obj)
        if rig is None:
            self.report({'ERROR'}, rpt_("No standard skeleton to add the part to"))
            return {'CANCELLED'}
        obj.update_from_editmode()
        selected = [v.index for v in obj.data.vertices if v.select]
        bpy.ops.object.mode_set(mode='OBJECT')
        try:
            part = regions.lock_from_selection(rig, obj, selected)
        except rig_parts.PartError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        finally:
            bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, rpt_("Made lock %s") % part.name)
        return {'FINISHED'}


def _region_parts(rig):
    return [part for part in rig.data.dasktoon_rig.parts
            if part.object is not None and part.object.type == 'MESH' and part.role in ('BODY', 'CLOTHING')]


class DASKTOON_OT_rig_recognize(Operator):
    """Paint the head, torso, arms and legs on the Body and Clothing meshes and make locks of the pieces on the head"""
    bl_idname = "dasktoon.rig_recognize"
    bl_label = "Recognize"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        rig = rig_of(context)
        return rig is not None and bool(_region_parts(rig))

    def invoke(self, context, event):
        from dasktoon_rig import regions
        if regions.has_layers(rig_of(context)):
            return context.window_manager.invoke_confirm(
                self, event, message=rpt_("Paint the regions again and remake the locks? What you painted is replaced"))
        return self.execute(context)

    def execute(self, context):
        from dasktoon_rig import build, parts as rig_parts, regions
        rig = rig_of(context)
        try:
            build.check(rig, list(rig.data.dasktoon_rig.parts))  # a rig Build cannot use cannot be recognized either
            found = regions.recognize(context, rig)
        except (build.BuildError, rig_parts.PartError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        self.report({'INFO'}, rpt_("Recognized the regions and %d locks") % len(found.locks))
        return {'FINISHED'}


def regions_palette():
    """The palette of the six region colors, made when missing."""
    from dasktoon_rig import regions
    palette = bpy.data.palettes.get(PALETTE) or bpy.data.palettes.new(PALETTE)
    if len(palette.colors) != len(regions.REGIONS):
        palette.colors.clear()
        for region in regions.REGIONS:
            palette.colors.new().color = regions.COLORS[region]
    return palette


class DASKTOON_OT_rig_paint_regions(Operator):
    """Paint the body regions in Vertex Paint with this region's color"""
    bl_idname = "dasktoon.rig_paint_regions"
    bl_label = "Paint Regions"
    bl_options = {'REGISTER', 'UNDO'}

    region: EnumProperty(name="Region", description="Region to paint", items=REGION_ITEMS, default='TORSO')

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is None:
            return False
        if obj.type == 'ARMATURE':
            return bool(_region_parts(obj))
        return obj.type == 'MESH'

    def execute(self, context):
        from dasktoon_rig import build, parts as rig_parts, regions
        obj = context.object
        if obj.type == 'ARMATURE':
            rig = obj
            if not regions.has_layers(rig):  # start from what Recognize finds
                try:
                    build.check(rig, list(rig.data.dasktoon_rig.parts))
                    regions.recognize(context, rig)
                except (build.BuildError, rig_parts.PartError) as ex:
                    self.report({'ERROR'}, str(ex))
                    return {'CANCELLED'}
            part = _active_part(rig)
            obj = part.object if part is not None and part in _region_parts(rig) else _region_parts(rig)[0].object
        paint_regions(context, obj, self.region)
        return {'FINISHED'}


def paint_regions(context, target, region):
    """Vertex Paint on the region layer of `target` (selected and active now) with the color of `region`, the region
    palette at hand and Show Regions on."""
    from dasktoon_rig import regions
    obj = context.object
    if obj != target:
        if obj is not None and obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for other in context.view_layer.objects:
            other.select_set(other == target)
        context.view_layer.objects.active = target
    regions.ensure_layer(target)
    target.data.color_attributes.active_color_name = regions.LAYER
    if target.mode != 'VERTEX_PAINT':
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')
    paint = context.tool_settings.vertex_paint
    paint.palette = regions_palette()
    settings = paint.unified_paint_settings
    settings.use_unified_color = True
    settings.color = regions.COLORS[region]
    context.window_manager.dasktoon_show_regions = True


class DASKTOON_OT_rig_paint_done(Operator):
    """Leave Vertex Paint and select the rig again"""
    bl_idname = "dasktoon.rig_paint_done"
    bl_label = "Done Painting"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'VERTEX_PAINT'

    def execute(self, context):
        obj = context.object
        rig = find_rig(context, obj)
        bpy.ops.object.mode_set(mode='OBJECT')
        if rig is not None:
            for other in context.view_layer.objects:
                other.select_set(other == rig)
            context.view_layer.objects.active = rig
        return {'FINISHED'}


# Show Regions: the 3D views and meshes as they were before, to put back.
_shown = {}


def show_regions(show):
    """Every 3D view in Solid shading colored by the active color layer, the region layer active on every mesh that
    has one; or, `show` off, everything as it was."""
    from dasktoon_rig import regions
    spaces = [space for screen in bpy.data.screens for area in screen.areas for space in area.spaces
              if space.type == 'VIEW_3D']
    if show:  # what is saved is overwritten: after another file opens, a new view can get an old one's address
        for space in spaces:
            if (space.shading.type, space.shading.color_type) != ('SOLID', 'VERTEX'):
                _shown[("space", space.as_pointer())] = (space.shading.type, space.shading.color_type)
                space.shading.type, space.shading.color_type = 'SOLID', 'VERTEX'
        for mesh in bpy.data.meshes:
            layers = mesh.color_attributes
            if layers.get(regions.LAYER) is not None and layers.active_color_name != regions.LAYER:
                _shown[("mesh", mesh.name)] = layers.active_color_name
                layers.active_color_name = regions.LAYER
                mesh.update()  # the 3D views draw the new active color only after this
        return
    for space in spaces:
        saved = _shown.pop(("space", space.as_pointer()), None)
        if saved is not None:
            space.shading.type, space.shading.color_type = saved
    for key in [key for key in _shown if key[0] == "mesh"]:
        mesh = bpy.data.meshes.get(key[1])
        name = _shown.pop(key)
        if mesh is not None:
            mesh.color_attributes.active_color_name = name
            mesh.update()


def _show_regions_changed(self, _context):
    show_regions(self.dasktoon_show_regions)


# Highlight Part: the triangles of the part chosen in the list, drawn in the 3D view while the rig is active.
_highlight = {"handle": None, "key": None, "batch": None, "shader": None, "generation": 0}
HIGHLIGHT_COLOR = (0.2, 0.9, 1.0, 0.35)
HIGHLIGHT_PULL = 0.999  # drawn as if 0.1% nearer: on its own faces it shows over the mesh (onion ghosts go behind)


def part_triangles(part):
    """World corners (3 rows a triangle) of the faces of `part` (every corner in the part), at rest."""
    import numpy as np
    from dasktoon_rig import parts as rig_parts
    obj = part.object
    try:
        vertices = rig_parts.part_vertices(part)
    except rig_parts.PartError:
        return np.zeros((0, 3), np.float32)
    world, _edges = rig_parts.mesh_arrays(obj)
    mesh = obj.data
    mesh.calc_loop_triangles()
    corners = np.empty(len(mesh.loop_triangles) * 3, np.int32)
    mesh.loop_triangles.foreach_get("vertices", corners)
    corners = corners.reshape(-1, 3)
    inside = np.zeros(len(world), bool)
    inside[vertices] = True
    return world[corners[inside[corners].all(axis=1)].ravel()].astype(np.float32)


def _highlight_shader():
    import gpu
    from bl_ui import dasktoon_animation
    if _highlight["shader"] is None:
        info = gpu.types.GPUShaderCreateInfo()
        info.push_constant('MAT4', "perspective")
        info.push_constant('VEC4', "depth")
        info.push_constant('VEC4', "color")
        info.vertex_in(0, 'VEC3', "pos")
        info.fragment_out(0, 'VEC4', "fragColor")
        info.vertex_source(dasktoon_animation.ONION_VERTEX)
        info.fragment_source("void main()\n{\n  fragColor = color;\n}\n")
        _highlight["shader"] = gpu.shader.create_from_info(info)
    return _highlight["shader"]


def _draw_batch(context, batch, color, pull, depth_test):
    import gpu
    shader = _highlight_shader()
    view = context.region_data
    shader.bind()
    shader.uniform_float("perspective", view.perspective_matrix)
    shader.uniform_float("depth", (view.window_matrix[2][2], view.window_matrix[2][3], pull,
                                   1.0 if view.is_perspective else 0.0))
    shader.uniform_float("color", color)
    state = gpu.state.blend_get(), gpu.state.depth_test_get(), gpu.state.depth_mask_get()
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set(depth_test)
    gpu.state.depth_mask_set(False)
    batch.draw(shader)
    gpu.state.blend_set(state[0])
    gpu.state.depth_test_set(state[1])
    gpu.state.depth_mask_set(state[2])


def at_rest(rig):
    """True when no bone of `rig` is moved from its rest position (the part highlight is drawn at rest)."""
    from mathutils import Matrix
    identity = Matrix.Identity(4)
    return all(bone.matrix_basis == identity for bone in rig.pose.bones)


# Show: the stretched spot the Check found, lit up where its pose moves it (auto rig spec 4.2) while the rig stays in
# that pose.
_spot = {"rig": None, "index": -1, "signature": None, "triangles": None, "batch": None}
SPOT_COLOR = (1.0, 0.3, 0.1, 0.5)


def _pose_signature(rig):
    return tuple(round(value, 5) for bone in rig.pose.bones for row in bone.matrix_basis for value in row)


def spot_triangles(rig, issue):
    """World corners (3 rows a triangle) of the faces of a stretched spot (every corner in it; those touching it when
    none is), where the rig's pose moves them through their weights."""
    import numpy as np
    from dasktoon_rig import check
    obj = issue.object
    if obj is None or obj.type != 'MESH':
        return np.zeros((0, 3), np.float32)
    moved = check.deformed(rig, obj)
    mesh = obj.data
    mesh.calc_loop_triangles()
    corners = np.empty(len(mesh.loop_triangles) * 3, np.int32)
    mesh.loop_triangles.foreach_get("vertices", corners)
    corners = corners.reshape(-1, 3)
    inside = np.zeros(len(moved), bool)
    inside[[v for v in issue.get("vertices", ()) if 0 <= v < len(moved)]] = True
    chosen = corners[inside[corners].all(axis=1)]
    if not len(chosen):
        chosen = corners[inside[corners].any(axis=1)]
    return moved[chosen.ravel()].astype(np.float32)


def show_spot(context, rig, index):
    """Put `rig` in the pose of its stretched spot `index` and light the spot up there."""
    from dasktoon_rig import check
    issue = rig.data.dasktoon_rig.issues[index]
    check.apply_pose(context, rig, issue.pose)
    _spot.update(rig=rig.name, index=index, signature=_pose_signature(rig), triangles=spot_triangles(rig, issue),
                 batch=None)
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def hide_spot():
    _spot.update(rig=None, index=-1, signature=None, triangles=None, batch=None)


def spot_shown():
    """The rig whose stretched spot is lit up now (it is still in the pose of the spot), or None."""
    rig = bpy.data.objects.get(_spot["rig"]) if _spot["rig"] else None
    if rig is None or rig.type != 'ARMATURE' or _pose_signature(rig) != _spot["signature"]:
        return None
    return rig


@persistent
def _forget_spot(_dummy):
    hide_spot()


def _spot_draw(context):
    """Draw the spot shown, through everything (it may be inside the body); True when it is drawn."""
    if spot_shown() is None or _spot["triangles"] is None or not len(_spot["triangles"]):
        return False
    if _spot["batch"] is None:
        from gpu_extras.batch import batch_for_shader
        _spot["batch"] = batch_for_shader(_highlight_shader(), 'TRIS', {"pos": _spot["triangles"]})
    _draw_batch(context, _spot["batch"], SPOT_COLOR, 1.0, 'NONE')
    return True


def _highlight_draw():
    context = bpy.context
    if context.region_data is None or context.screen.is_animation_playing:  # not while the character moves
        return
    if _spot_draw(context):  # the spot the Check shows, in place of the part
        return
    rig = context.object
    if rig is None or rig.type != 'ARMATURE' or not at_rest(rig):  # the part is drawn at rest
        return
    data = rig.data.dasktoon_rig
    part = _active_part(rig)
    if not data.highlight_part or part is None or part.object is None or part.object.type != 'MESH':
        return
    from gpu_extras.batch import batch_for_shader
    key = (rig.name, data.active_part_index, part.object.name, part.scope, part.material, part.vertex_group,
           len(part.object.data.vertices), _highlight["generation"])
    if key != _highlight["key"]:
        triangles = part_triangles(part)
        _highlight["batch"] = (batch_for_shader(_highlight_shader(), 'TRIS', {"pos": triangles}) if len(triangles)
                               else None)
        _highlight["key"] = key
    if _highlight["batch"] is not None:
        _draw_batch(context, _highlight["batch"], HIGHLIGHT_COLOR, HIGHLIGHT_PULL, 'LESS_EQUAL')


def _highlight_depsgraph(_scene, depsgraph):
    """A mesh's data changed (an edit, not the armature deforming it on a frame): make the highlight again."""
    if any(isinstance(update.id, bpy.types.Mesh) for update in depsgraph.updates):
        _highlight["generation"] += 1


def draw_region_buttons(layout):
    grid = layout.grid_flow(columns=2, even_columns=True, align=True)
    for identifier, name, _description, icon, _number in REGION_ITEMS:
        grid.operator("dasktoon.rig_paint_regions", text=name, icon=icon).region = identifier


def _check_poll(context):
    rig = rig_of(context)
    return rig is not None and rig.mode != 'EDIT'


def _stretch_issue(rig, index):
    issues = rig.data.dasktoon_rig.issues
    return issues[index] if 0 <= index < len(issues) and issues[index].kind == 'STRETCH' else None


class DASKTOON_OT_rig_test_pose(Operator):
    """Put the character in a test pose to see how the rig bends; nothing is keyed"""
    bl_idname = "dasktoon.rig_test_pose"
    bl_label = "Test Pose"
    bl_options = {'REGISTER', 'UNDO'}

    pose: EnumProperty(name="Pose", description="The test pose", items=POSE_ITEMS, default='REST',
                       translation_context="DaskToon")

    @classmethod
    def poll(cls, context):
        return _check_poll(context)

    def execute(self, context):
        from dasktoon_rig import check
        check.apply_pose(context, rig_of(context), self.pose)
        return {'FINISHED'}


class DASKTOON_OT_rig_check(Operator):
    """Look for joints outside the body, spots torn in the test poses and parts whose role looks wrong"""
    bl_idname = "dasktoon.rig_check"
    bl_label = "Check"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _check_poll(context)

    def execute(self, context):
        from dasktoon_rig import build
        rig = rig_of(context)
        try:
            build.check(rig, list(rig.data.dasktoon_rig.parts))  # what Build needs, the Check needs
        except build.BuildError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        self.report({'INFO'}, check_summary(run_check(context, rig)))
        return {'FINISHED'}


class DASKTOON_OT_rig_check_done(Operator):
    """Clear the list of spots to look at and stop lighting up the spot shown"""
    bl_idname = "dasktoon.rig_check_done"
    bl_label = "Done Checking"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        rig = rig_of(context)
        return rig is not None and rig.data.dasktoon_rig.checked

    def execute(self, context):
        data = rig_of(context).data.dasktoon_rig
        data.issues.clear()
        data.checked = False
        hide_spot()
        return {'FINISHED'}


class DASKTOON_OT_rig_fix_joint(Operator):
    """Edit the joints with this one selected: move it into the body, then press Build Rig"""
    bl_idname = "dasktoon.rig_fix_joint"
    bl_label = "Fix Joint"
    bl_options = {'REGISTER', 'UNDO'}

    bone: StringProperty(name="Bone", description="The bone whose joint, its head, is selected")

    @classmethod
    def poll(cls, context):
        rig = rig_of(context)
        return rig is not None and context.view_layer.objects.active == rig

    def execute(self, context):
        rig = rig_of(context)
        if rig.data.bones.get(self.bone) is None:
            self.report({'ERROR'}, rpt_("There is no bone %s") % self.bone)
            return {'CANCELLED'}
        rig.data.use_mirror_x = True  # as Edit Joints: both sides move together
        if rig.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bones = rig.data.edit_bones
        bones.active = bones[self.bone]  # first: making a bone active selects all of it
        for bone in bones:
            bone.select = bone.select_head = bone.select_tail = False
        bone = bones[self.bone]
        bone.select_head = True
        if bone.parent is not None and bone.use_connect:
            bone.parent.select_tail = True  # the same joint
        return {'FINISHED'}


class DASKTOON_OT_rig_show_spot(Operator):
    """Put the character in the pose that tears this spot and light the spot up"""
    bl_idname = "dasktoon.rig_show_spot"
    bl_label = "Show Spot"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Spot", description="Which spot of the list", min=0)

    @classmethod
    def poll(cls, context):
        return _check_poll(context)

    def execute(self, context):
        rig = rig_of(context)
        if _stretch_issue(rig, self.index) is None:
            self.report({'ERROR'}, rpt_("That spot is not in the list"))
            return {'CANCELLED'}
        show_spot(context, rig, self.index)
        return {'FINISHED'}


class DASKTOON_OT_rig_paint_spot(Operator):
    """Light up the spot in its pose and paint the regions on its mesh: the torn faces take their region's color"""
    bl_idname = "dasktoon.rig_paint_spot"
    bl_label = "Paint Regions at Spot"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Spot", description="Which spot of the list", min=0)

    @classmethod
    def poll(cls, context):
        return _check_poll(context)

    def execute(self, context):
        rig = rig_of(context)
        issue = _stretch_issue(rig, self.index)
        if issue is None:
            self.report({'ERROR'}, rpt_("That spot is not in the list"))
            return {'CANCELLED'}
        target, region = issue.object, issue.region
        if target not in [part.object for part in _region_parts(rig)]:
            self.report({'ERROR'}, rpt_("That spot is not on a Body or Clothing part"))
            return {'CANCELLED'}
        show_spot(context, rig, self.index)
        paint_regions(context, target, region)
        return {'FINISHED'}


class DASKTOON_OT_rig_change_role(Operator):
    """Give the part this role, then build the rig and check it again"""
    bl_idname = "dasktoon.rig_change_role"
    bl_label = "Change Role"
    bl_options = {'REGISTER', 'UNDO'}

    part: StringProperty(name="Part", description="The part to change")
    role: EnumProperty(name="Role", description="The new role", items=ROLE_ITEMS, default='HAIR')

    @classmethod
    def poll(cls, context):
        return _check_poll(context)

    def execute(self, context):
        from dasktoon_rig import build, parts as rig_parts, regions
        rig = rig_of(context)
        parts = rig.data.dasktoon_rig.parts
        part = next((part for part in parts if part.name == self.part), None)
        if part is None:
            self.report({'ERROR'}, rpt_("There is no part %s") % self.part)
            return {'CANCELLED'}
        part.role = self.role
        part.bone_count = rig_parts.DEFAULT_BONE_COUNT.get(self.role, rig_parts.BONE_COUNT)
        obj = part.object
        if obj is not None and self.role not in regions.BODY_ROLES and not any(
                other.object == obj and other.role in regions.BODY_ROLES and not other.made_by_recognize
                for other in parts):
            regions.remove_locks(rig, obj)  # its pieces are locks of a Body or Clothing mesh no more
        try:
            result, _recognized = build_rig(context, rig)
        except build.BuildError as ex:
            self.report({'ERROR'}, str(ex))
            return {'FINISHED'}  # the role is changed
        for warning in result.warnings:
            self.report({'WARNING'}, warning)
        self.report({'INFO'}, check_summary(run_check(context, rig)))
        return {'FINISHED'}


class DASKTOON_OT_rig_skirt_below_waist(Operator):
    """Make the part of this mesh below the waist a skirt of its own, then build the rig and check it again"""
    bl_idname = "dasktoon.rig_skirt_below_waist"
    bl_label = "Make the Part Below the Waist a Skirt"
    bl_options = {'REGISTER', 'UNDO'}

    part: StringProperty(name="Part", description="The part whose lower part becomes a skirt")

    @classmethod
    def poll(cls, context):
        return _check_poll(context)

    def execute(self, context):
        from dasktoon_rig import build, check
        rig = rig_of(context)
        part = next((part for part in rig.data.dasktoon_rig.parts if part.name == self.part), None)
        if part is None or part.object is None or part.object.type != 'MESH':
            self.report({'ERROR'}, rpt_("There is no part %s") % self.part)
            return {'CANCELLED'}
        if skirt_below_waist(rig, part) is None:
            self.report({'ERROR'}, rpt_("Nothing of %s is below the waist") % part.name)
            return {'CANCELLED'}
        try:
            result, _recognized = build_rig(context, rig)
        except build.BuildError as ex:
            self.report({'ERROR'}, str(ex))
            return {'FINISHED'}  # the skirt part is added
        for warning in result.warnings:
            self.report({'WARNING'}, warning)
        self.report({'INFO'}, check_summary(run_check(context, rig)))
        return {'FINISHED'}


class DASKTOON_OT_rig_turn_character(Operator):
    """Turn the character on the spot by a quarter, then fit the skeleton, build the rig and check it again"""
    bl_idname = "dasktoon.rig_turn_character"
    bl_label = "Turn the Character"
    bl_options = {'REGISTER', 'UNDO'}

    degrees: IntProperty(name="Degrees", description="How far to turn, to the left (positive) or the right",
                         default=90, min=-180, max=180)

    @classmethod
    def poll(cls, context):
        return _check_poll(context)

    def execute(self, context):
        from dasktoon_rig import build, facing, regions
        rig = rig_of(context)
        parts = [part for part in rig.data.dasktoon_rig.parts if part.object is not None]
        meshes = list(dict.fromkeys(part.object for part in parts if part.object.type == 'MESH'))
        body = list(dict.fromkeys(part.object for part in parts
                                  if part.object.type == 'MESH' and part.role in regions.BODY_ROLES))
        facing.turn(context, meshes, math.radians(self.degrees), body=body or None)
        report_turn(self, fit_to_parts(context, rig))
        try:
            result, _recognized = build_rig(context, rig)
        except build.BuildError as ex:
            self.report({'ERROR'}, str(ex))
            return {'FINISHED'}  # it is turned and fitted
        for warning in result.warnings:
            self.report({'WARNING'}, warning)
        self.report({'INFO'}, check_summary(run_check(context, rig)))
        return {'FINISHED'}


def issue_sentence(issue):
    """What a spot of the Check's list says, in the interface's language."""
    if issue.kind == 'FACING':
        return rpt_("The character faces a side, not the front (-Y)")
    if issue.kind == 'JOINT':
        return rpt_("%s is outside the body") % iface_(JOINT_NAMES.get(issue.bone, issue.bone))
    if issue.kind == 'STRETCH':
        region = next((name for identifier, name, *_rest in REGION_ITEMS if identifier == issue.region), issue.region)
        pose = next((name for identifier, name, _tip in POSE_ITEMS if identifier == issue.pose), issue.pose)
        return rpt_("%s stretched in the %s pose (%s)") % (iface_(region), iface_(pose, "DaskToon"), issue.part)
    if issue.role == 'SKIRT' and issue.below_waist:
        return rpt_("The part of %s below the waist looks like a skirt") % issue.part
    if issue.role == 'SKIRT':
        return rpt_("%s looks like a skirt") % issue.part
    return rpt_("%s looks like hair") % issue.part


def wrapped_label(layout, text, icon='NONE', width=None):
    """`text` (translated already) as labels broken to fit `width` pixels (default: the region's), the icon on the first
    line: a real window cut the Check's longer sentences off at the panel's edge. One label where nothing tells the
    width (the background)."""
    import textwrap
    context = bpy.context
    scale = context.preferences.system.ui_scale or 1.0  # 0 without a window
    if width is None:
        width = context.region.width if context.region is not None else 0
    chars = int((width - 40 * scale) / (7 * scale))
    lines = textwrap.wrap(text, chars) if chars >= 16 else []
    column = layout.column(align=True)
    for k, line in enumerate(lines or [text]):
        column.label(text=line, icon=icon if k == 0 else 'BLANK1', translate=False)


def draw_issue(layout, rig, index, issue):
    box = layout.box()
    wrapped_label(box, issue_sentence(issue), icon=ISSUE_ICONS.get(issue.kind) or ROLE_ICONS.get(issue.role, 'ERROR'))
    row = box.row(align=True)
    if issue.kind == 'FACING':
        row.operator("dasktoon.rig_turn_character", text="Turn 90° Left", icon='LOOP_BACK').degrees = 90
        row.operator("dasktoon.rig_turn_character", text="Turn 90° Right", icon='LOOP_FORWARDS').degrees = -90
    elif issue.kind == 'JOINT':
        row.operator("dasktoon.rig_fix_joint", text="Fix", icon='EDITMODE_HLT').bone = issue.bone
    elif issue.kind == 'STRETCH':
        shown = _spot["rig"] == rig.name and _spot["index"] == index and spot_shown() is not None
        row.operator("dasktoon.rig_show_spot", text="Show", text_ctxt="DaskToon", icon='HIDE_OFF',
                     depress=shown).index = index
        if issue.object in [part.object for part in _region_parts(rig)]:
            row.operator("dasktoon.rig_paint_spot", text="Paint Regions", icon='BRUSH_DATA').index = index
    elif issue.below_waist:
        row.operator("dasktoon.rig_skirt_below_waist", text="Make That Part a Skirt",
                     icon=ROLE_ICONS.get(issue.role, 'NONE')).part = issue.part
    else:
        op = row.operator("dasktoon.rig_change_role", icon=ROLE_ICONS.get(issue.role, 'NONE'),
                          text="Make it a Skirt" if issue.role == 'SKIRT' else "Make it Hair")
        op.part, op.role = issue.part, issue.role


class DASKTOON_UL_rig_parts(UIList):
    """Parts of the anime rig"""

    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon=ROLE_ICONS[item.role])
        if item.object is not None and item.object.name != item.name:
            row.label(text=item.object.name, translate=False)


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


class DATA_PT_dasktoon_rig_check(DaskRigPanel, Panel):
    bl_label = "Check"
    bl_parent_id = "DATA_PT_dasktoon_rig"

    def draw(self, context):
        from dasktoon_rig import skeleton
        layout = self.layout
        rig = rig_of(context)
        data = rig.data.dasktoon_rig
        if skeleton.missing_bones(rig.data):
            layout.label(text="The Check needs a standard skeleton", icon='INFO')
            return
        layout.label(text="Test poses:")
        grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
        for identifier, name, _tip in POSE_ITEMS[:-1]:
            grid.operator("dasktoon.rig_test_pose", text=name, text_ctxt="DaskToon").pose = identifier
        layout.operator("dasktoon.rig_test_pose", text="Rest", text_ctxt="DaskToon", icon='LOOP_BACK').pose = 'REST'
        if not data.checked:
            layout.label(text="Not checked yet")
            layout.operator("dasktoon.rig_check", text="Check", icon='VIEWZOOM')
            return
        if not len(data.issues):
            layout.label(text="Nothing to fix found", icon='CHECKMARK')
        else:
            column = layout.column()
            for index, issue in enumerate(data.issues):
                draw_issue(column, rig, index, issue)
            layout.label(text="After a fix, press Build Rig to check again", icon='INFO')
        row = layout.row(align=True)
        row.operator("dasktoon.rig_check", text="Check Again", icon='FILE_REFRESH')
        row.operator("dasktoon.rig_check_done", text="Done", icon='CHECKMARK')


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
        layout.prop(rig_of(context).data.dasktoon_rig, "shoulder_follow", slider=True)
        layout.prop(rig_of(context).data.dasktoon_rig, "bend_fixes")


class DATA_PT_dasktoon_rig_parts(DaskRigPanel, Panel):
    bl_label = "Parts"
    bl_parent_id = "DATA_PT_dasktoon_rig"

    def draw(self, context):
        layout = self.layout
        rig = rig_of(context)
        data = rig.data.dasktoon_rig
        row = layout.row()
        row.template_list("DASKTOON_UL_rig_parts", "", data, "parts", data, "active_part_index", rows=4)
        layout.prop(data, "highlight_part")
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
        if part.role == 'FLAT_EYE':
            layout.prop(part, "eye_side")
            layout.prop(part, "eye_range")
        if part.role == 'MOUTH_2D':
            layout.prop(part, "mouth_rows")
            layout.prop(part, "mouth_columns")
            col = layout.column(align=True)
            col.label(text="Cells from the top left: closed, A, I, U, E, O", icon='INFO')
            col.label(text="The object's dt_mouth picks the cell; lip sync keys it")


class DATA_PT_dasktoon_rig_regions(DaskRigPanel, Panel):
    bl_label = "Regions"
    bl_parent_id = "DATA_PT_dasktoon_rig"

    def draw(self, _context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("dasktoon.rig_recognize", icon='VIEWZOOM')
        row.prop(bpy.context.window_manager, "dasktoon_show_regions", toggle=True, icon='COLOR')
        layout.label(text="Paint regions:")
        draw_region_buttons(layout)
        layout.label(text="In Vertex Paint, select faces and press Shift+K to fill them", icon='INFO')


class DATA_PT_dasktoon_rig_look(DaskRigPanel, Panel):
    # Not "Look": Blender's Vietnamese for that word is the Color Management look.
    bl_label = "Gaze"
    bl_parent_id = "DATA_PT_dasktoon_rig"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        data = rig_of(context).data.dasktoon_rig
        col = layout.column(align=True)
        col.prop(data, "look_yaw_limit")
        col.prop(data, "look_pitch_limit")


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
            layout.prop(part, "sway_in_unity")
        else:
            layout.label(text="Select a hair or skirt part to set how it sways")
        layout.operator("dasktoon.rig_bake_sway", icon='REC')


class DATA_PT_dasktoon_rig_colliders(DaskRigPanel, Panel):
    bl_label = "Colliders"
    bl_parent_id = "DATA_PT_dasktoon_rig_sway"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        rig = rig_of(context)
        return rig is not None and len(rig.data.dasktoon_rig.colliders) > 0

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        for collider in rig_of(context).data.dasktoon_rig.colliders:
            layout.prop(collider, "radius", text=collider.bone, translate=False)


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
        from dasktoon_rig import regions
        if obj.mode == 'VERTEX_PAINT' and obj.data.color_attributes.get(regions.LAYER) is not None:
            layout.label(text="Paint regions:")
            draw_region_buttons(layout)
            layout.operator("dasktoon.rig_paint_done", icon='CHECKMARK')
        layout.operator("dasktoon.rig_part_from_selection", icon='ADD')
        layout.operator("dasktoon.rig_lock_from_selection", icon='GROUP_VERTEX')
        if obj.mode != 'EDIT':
            layout.label(text="Select the vertices of a part in Edit Mode", icon='INFO')


def menu_func(self, _context):
    self.layout.operator(DASKTOON_OT_rig_add_humanoid.bl_idname, text="Anime Humanoid", icon='OUTLINER_OB_ARMATURE')


classes = (
    DaskRigPart,
    DaskRigCollider,
    DaskRigIssue,
    DaskRig,
    DASKTOON_OT_rig_add_humanoid,
    DASKTOON_OT_rig_edit_joints,
    DASKTOON_OT_rig_fit,
    DASKTOON_OT_rig_add_selected,
    DASKTOON_OT_rig_add_material_part,
    DASKTOON_OT_rig_remove_part,
    DASKTOON_OT_rig_build,
    DASKTOON_OT_rig_bake_sway,
    DASKTOON_OT_rig_part_from_selection,
    DASKTOON_OT_rig_lock_from_selection,
    DASKTOON_OT_rig_recognize,
    DASKTOON_OT_rig_paint_regions,
    DASKTOON_OT_rig_paint_done,
    DASKTOON_OT_rig_test_pose,
    DASKTOON_OT_rig_check,
    DASKTOON_OT_rig_check_done,
    DASKTOON_OT_rig_fix_joint,
    DASKTOON_OT_rig_show_spot,
    DASKTOON_OT_rig_paint_spot,
    DASKTOON_OT_rig_change_role,
    DASKTOON_OT_rig_skirt_below_waist,
    DASKTOON_OT_rig_turn_character,
    DASKTOON_UL_rig_parts,
    DATA_PT_dasktoon_rig,
    DATA_PT_dasktoon_rig_check,
    DATA_PT_dasktoon_rig_joints,
    DATA_PT_dasktoon_rig_parts,
    DATA_PT_dasktoon_rig_regions,
    DATA_PT_dasktoon_rig_look,
    DATA_PT_dasktoon_rig_sway,
    DATA_PT_dasktoon_rig_colliders,
    DATA_PT_dasktoon_rig_build,
    DATA_PT_dasktoon_rig_mesh,
)


# bl_ui registers `classes`; register() adds the rig data to armatures and the Add › Armature entry. The chains sway
# with Spring constraints, which the depsgraph evaluates: there are no frame handlers.
def register():
    from .space_view3d import VIEW3D_MT_armature_add
    bpy.types.Armature.dasktoon_rig = PointerProperty(type=DaskRig)
    bpy.types.WindowManager.dasktoon_show_regions = BoolProperty(
        name="Show Regions", update=_show_regions_changed,
        description="Show the body regions in the 3D views: Solid shading colored by the region layer")
    VIEW3D_MT_armature_add.append(menu_func)
    if _highlight["handle"] is None:
        _highlight["handle"] = bpy.types.SpaceView3D.draw_handler_add(_highlight_draw, (), 'WINDOW', 'POST_VIEW')
    if _highlight_depsgraph not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_highlight_depsgraph)
    if _forget_spot not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_forget_spot)


def unregister():
    from .space_view3d import VIEW3D_MT_armature_add
    VIEW3D_MT_armature_add.remove(menu_func)
    if _highlight["handle"] is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_highlight["handle"], 'WINDOW')
        _highlight["handle"] = None
    if _highlight_depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_highlight_depsgraph)
    if _forget_spot in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_forget_spot)
    del bpy.types.WindowManager.dasktoon_show_regions
    del bpy.types.Armature.dasktoon_rig
