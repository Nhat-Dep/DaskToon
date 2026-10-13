# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime rig, R1 (docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md, section 7): Add › Armature › Anime
Humanoid; the Anime Rig panel in Properties › Object Data of an armature (Joints, Parts, Regions, Build) and of a mesh
(its parts, Add Part from Selection, Lock from Selection, the region colors while painting). The regions and locks:
docs/superpowers/specs/2026-10-13-dasktoon-rig-regions-design.md, section 6. The work is done by the dasktoon_rig
module."""

import bpy
from bpy.app.translations import pgettext_rpt as rpt_
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
    ('HEAD', "Head", "The head, and the locks hanging from it", 'SEQUENCE_COLOR_03', 0),
    ('TORSO', "Torso", "The body from the hips to the neck", 'SEQUENCE_COLOR_05', 1),
    ('ARM_L', "Left Arm", "The character's left arm and hand", 'SEQUENCE_COLOR_01', 2),
    ('ARM_R', "Right Arm", "The character's right arm and hand", 'SEQUENCE_COLOR_02', 3),
    ('LEG_L', "Left Leg", "The character's left leg and foot", 'SEQUENCE_COLOR_04', 4),
    ('LEG_R', "Right Leg", "The character's right leg and foot", 'SEQUENCE_COLOR_06', 5),
)
PALETTE = "DaskToon Regions"


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


def _look_changed(self, _context):
    from dasktoon_rig import look
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj.data == self.id_data:
            look.sync_limits(obj)


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
        parts = [part for part in rig.data.dasktoon_rig.parts if part.object is not None and part.object.type == 'MESH']
        meshes = list(dict.fromkeys(part.object for part in parts))
        # The shape of the body is read from the Body and Clothing parts: hair, a skirt or a held staff is no limb.
        body = list(dict.fromkeys(part.object for part in parts if part.role in {'BODY', 'CLOTHING'}))
        skeleton.fit(context, rig, meshes, body=body or None)
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
        from dasktoon_rig import build, parts as rig_parts, regions
        rig = rig_of(context)
        recognized = None
        if rig.data.dasktoon_rig.parts and not regions.has_layers(rig):
            # Never recognized: do it first, so the one-button way still gets regions and locks (rig regions spec 5).
            try:
                recognized = regions.recognize(context, rig)
            except rig_parts.PartError:
                pass  # Build reports the part
        try:
            result = build.build(context, rig, list(rig.data.dasktoon_rig.parts))
        except build.BuildError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        for warning in result.warnings:
            self.report({'WARNING'}, warning)
        if recognized is not None:
            self.report({'INFO'}, rpt_("Recognized the regions and %d locks first") % len(recognized.locks))
        self.report({'INFO'}, result.summary())
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
        from dasktoon_rig import parts as rig_parts, regions
        try:
            found = regions.recognize(context, rig_of(context))
        except rig_parts.PartError as ex:
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
        from dasktoon_rig import regions
        obj = context.object
        if obj.type == 'ARMATURE':
            rig = obj
            if not regions.has_layers(rig):
                regions.recognize(context, rig)
            part = _active_part(rig)
            target = part.object if part is not None and part in _region_parts(rig) else _region_parts(rig)[0].object
            if obj.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            for other in context.view_layer.objects:
                other.select_set(other == target)
            context.view_layer.objects.active = target
            obj = target
        regions.ensure_layer(obj)
        obj.data.color_attributes.active_color_name = regions.LAYER
        if obj.mode != 'VERTEX_PAINT':
            bpy.ops.object.mode_set(mode='VERTEX_PAINT')
        paint = context.tool_settings.vertex_paint
        paint.palette = regions_palette()
        settings = paint.unified_paint_settings
        settings.use_unified_color = True
        settings.color = regions.COLORS[self.region]
        context.window_manager.dasktoon_show_regions = True
        return {'FINISHED'}


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


def _show_regions_changed(self, _context):
    show_regions(self.dasktoon_show_regions)


# Highlight Part: the triangles of the part chosen in the list, drawn in the 3D view while the rig is active.
_highlight = {"handle": None, "key": None, "batch": None, "shader": None, "generation": 0}
HIGHLIGHT_COLOR = (0.2, 0.9, 1.0, 0.35)


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


def _highlight_draw():
    context = bpy.context
    rig = context.object
    if (rig is None or rig.type != 'ARMATURE' or context.region_data is None
            or context.screen.is_animation_playing):  # drawn at rest: not while the character moves
        return
    data = rig.data.dasktoon_rig
    part = _active_part(rig)
    if not data.highlight_part or part is None or part.object is None or part.object.type != 'MESH':
        return
    import gpu
    from bl_ui import dasktoon_animation
    from gpu_extras.batch import batch_for_shader
    shader = _highlight_shader()
    key = (rig.name, data.active_part_index, part.object.name, part.scope, part.material, part.vertex_group,
           len(part.object.data.vertices), _highlight["generation"])
    if key != _highlight["key"]:
        triangles = part_triangles(part)
        _highlight["batch"] = batch_for_shader(shader, 'TRIS', {"pos": triangles}) if len(triangles) else None
        _highlight["key"] = key
    if _highlight["batch"] is None:
        return
    view = context.region_data
    shader.bind()
    shader.uniform_float("perspective", view.perspective_matrix)
    shader.uniform_float("depth", (view.window_matrix[2][2], view.window_matrix[2][3], dasktoon_animation.ONION_PUSH,
                                   1.0 if view.is_perspective else 0.0))
    shader.uniform_float("color", HIGHLIGHT_COLOR)
    state = gpu.state.blend_get(), gpu.state.depth_test_get(), gpu.state.depth_mask_get()
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.depth_mask_set(False)
    _highlight["batch"].draw(shader)
    gpu.state.blend_set(state[0])
    gpu.state.depth_test_set(state[1])
    gpu.state.depth_mask_set(state[2])


def _highlight_depsgraph(_scene, depsgraph):
    """A mesh's data changed (an edit, not the armature deforming it on a frame): make the highlight again."""
    if any(isinstance(update.id, bpy.types.Mesh) for update in depsgraph.updates):
        _highlight["generation"] += 1


def draw_region_buttons(layout):
    grid = layout.grid_flow(columns=2, even_columns=True, align=True)
    for identifier, name, _description, icon, _number in REGION_ITEMS:
        grid.operator("dasktoon.rig_paint_regions", text=name, icon=icon).region = identifier


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
    DASKTOON_UL_rig_parts,
    DATA_PT_dasktoon_rig,
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


def unregister():
    from .space_view3d import VIEW3D_MT_armature_add
    VIEW3D_MT_armature_add.remove(menu_func)
    if _highlight["handle"] is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_highlight["handle"], 'WINDOW')
        _highlight["handle"] = None
    if _highlight_depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_highlight_depsgraph)
    del bpy.types.WindowManager.dasktoon_show_regions
    del bpy.types.Armature.dasktoon_rig
