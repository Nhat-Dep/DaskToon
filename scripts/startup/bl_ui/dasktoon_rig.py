# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime rig, R1 (docs/superpowers/specs/2026-10-06-dasktoon-anime-rig-design.md, section 7): Add › Armature › Anime
Humanoid; the Anime Rig panel in Properties › Object Data of an armature (Joints, Parts, Build) and of a mesh (its
parts, Add Part from Selection). The work is done by the dasktoon_rig module."""

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
)
ROLE_ICONS = {item[0]: item[3] for item in ROLE_ITEMS}


def _is_mesh(_self, obj):
    return obj.type == 'MESH'


def _sway_changed(_self, _context):
    from dasktoon_rig import sway
    sway.clear_cache()


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
    stiffness: FloatProperty(name="Stiffness", description="How strongly the chain springs back to its pose",
                             default=1.0, min=0.0, max=4.0, update=_sway_changed)
    gravity: FloatProperty(name="Gravity", description="How strongly the chain is pulled down", default=0.2, min=0.0,
                           max=2.0, update=_sway_changed)
    drag: FloatProperty(name="Drag", description="How quickly the swing dies down: 0 keeps swinging, 1 stops at once",
                        default=0.4, min=0.0, max=1.0, update=_sway_changed)
    radius: FloatProperty(name="Radius", description="How far each joint keeps from the colliders", default=0.03,
                          min=0.0, max=1.0, unit='LENGTH', update=_sway_changed)


class DaskRigCollider(PropertyGroup):
    """A capsule along a bone that hair and skirts do not go through"""
    bone: StringProperty(name="Bone", description="Bone the capsule runs along, from its head to its tail")
    radius: FloatProperty(name="Radius", description="Radius of the capsule", default=0.05, min=0.0, unit='LENGTH',
                          update=_sway_changed)


class DaskRig(PropertyGroup):
    """The parts of an anime rig"""
    parts: CollectionProperty(type=DaskRigPart, name="Parts", description="Parts of the character")
    active_part_index: IntProperty(name="Active Part", description="Part shown below the list", default=0)
    colliders: CollectionProperty(type=DaskRigCollider, name="Colliders",
                                  description="Capsules that hair and skirts do not go through; Build Rig makes them")
    live_sway: BoolProperty(name="Live Sway", description="Sway hair and skirts while the animation plays",
                            default=True, update=_sway_changed)


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
    DASKTOON_UL_rig_parts,
    DATA_PT_dasktoon_rig,
    DATA_PT_dasktoon_rig_joints,
    DATA_PT_dasktoon_rig_parts,
    DATA_PT_dasktoon_rig_sway,
    DATA_PT_dasktoon_rig_build,
    DATA_PT_dasktoon_rig_mesh,
)


def _sway_handlers():
    from dasktoon_rig import sway
    return ((bpy.app.handlers.frame_change_pre, sway.frame_pre),
            (bpy.app.handlers.frame_change_post, sway.frame_post),
            (bpy.app.handlers.depsgraph_update_post, sway.depsgraph_post))


# bl_ui registers `classes`; register() adds the rig data to armatures, the Add › Armature entry and the sway handlers.
def register():
    from .space_view3d import VIEW3D_MT_armature_add
    bpy.types.Armature.dasktoon_rig = PointerProperty(type=DaskRig)
    VIEW3D_MT_armature_add.append(menu_func)
    for handlers, function in _sway_handlers():
        if function not in handlers:
            handlers.append(function)


def unregister():
    from .space_view3d import VIEW3D_MT_armature_add
    for handlers, function in _sway_handlers():
        if function in handlers:
            handlers.remove(function)
    VIEW3D_MT_armature_add.remove(menu_func)
    del bpy.types.Armature.dasktoon_rig
