# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""
DaskToon 1-Click Anime FX Suite:
  - 💥 Anime Action & Impact FX (Shockwave Ring, Hit Spark Burst, Debris Blast, Slash Arc)
  - 🫧 Floating Anime Bubbles (Up / Down / Slow Chill)
  - 🌸 Sakura Petals Drift (Cánh hoa anh đào rơi)
  - ✨ Magic Sparkles & Stardust (Bụi ma thuật phát sáng)
  - 🍃 Wind Gust Leaves (Lá cây bay theo gió)
  - 🌧️ Anime Cel Rain (Mưa hoạt hình)
  - 🔥 Magic Fire Embers (Tàn lửa ma thuật)
"""

import bpy
import math
from bpy.types import Operator, Panel
from bpy.props import EnumProperty, FloatProperty, IntProperty, BoolProperty, FloatVectorProperty


def get_or_create_collection(col_name="[FX] DaskToon_Anime_Effects"):
    """Find or create dedicated FX collection to keep Outliner clean"""
    col = bpy.data.collections.get(col_name)
    if not col:
        col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(col)
    return col


def create_bubble_material():
    """Create clean rainbow iridescence anime bubble material without noise"""
    name = "DaskToon_Anime_Bubble_Rainbow"
    mat = bpy.data.materials.get(name)
    if mat:
        return mat

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    
    if hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'BLENDED'
    elif hasattr(mat, 'blend_method'):
        mat.blend_method = 'BLEND'
    if hasattr(mat, 'use_backface_culling'):
        mat.use_backface_culling = False

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out_node = nodes.new('ShaderNodeOutputMaterial')
    out_node.location = (600, 0)

    try:
        glass_node = nodes.new(type='ShaderNodeAnimeGlass')
        glass_node.location = (200, 0)
        glass_node.inputs['Crystal Tint'].default_value = (0.4, 0.9, 1.0, 1.0)
        glass_node.inputs['Internal Glow Color'].default_value = (0.9, 0.4, 0.95, 0.6)
        glass_node.inputs['Sparkle Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        glass_node.inputs['Dispersion Power'].default_value = 1.5
        glass_node.inputs['Fresnel Power'].default_value = 2.0
        glass_node.inputs['Opacity'].default_value = 0.25
        links.new(glass_node.outputs['BSDF'], out_node.inputs['Surface'])
    except Exception:
        fresnel = nodes.new('ShaderNodeFresnel')
        fresnel.location = (-200, 100)
        fresnel.inputs['IOR'].default_value = 1.15

        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.location = (0, 100)
        ramp.color_ramp.elements[0].color = (0.2, 0.8, 1.0, 1.0)
        ramp.color_ramp.elements[1].color = (0.9, 0.4, 0.85, 1.0)
        links.new(fresnel.outputs['Fac'], ramp.inputs['Fac'])

        trans = nodes.new('ShaderNodeBsdfTransparent')
        trans.location = (0, -100)

        mix = nodes.new('ShaderNodeMixShader')
        mix.location = (300, 0)
        links.new(fresnel.outputs['Fac'], mix.inputs['Fac'])
        links.new(trans.outputs['BSDF'], mix.inputs[1])
        links.new(ramp.outputs['Color'], mix.inputs[2])
        links.new(mix.outputs['Shader'], out_node.inputs['Surface'])

    return mat


def create_impact_energy_material(mat_name, base_col=(1.0, 0.9, 0.3, 1.0), emission_power=8.0):
    """Create a stylized glowing Anime Impact Energy material"""
    mat = bpy.data.materials.get(mat_name)
    if mat:
        return mat

    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    if hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'BLENDED'
    elif hasattr(mat, 'blend_method'):
        mat.blend_method = 'BLEND'

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    emiss = nodes.new('ShaderNodeEmission')
    emiss.inputs['Color'].default_value = base_col
    emiss.inputs['Strength'].default_value = emission_power
    links.new(emiss.outputs['Emission'], out.inputs['Surface'])
    return mat


def create_sakura_petal_mesh(col):
    """Create a stylized curved sakura petal mesh"""
    name = "FX_Sakura_Petal_Mesh"
    obj = bpy.data.objects.get(name)
    if obj:
        return obj

    mesh = bpy.data.meshes.new(name)
    verts = [
        (0.0, -0.25, 0.0),
        (-0.15, 0.0, 0.05),
        (0.15, 0.0, 0.05),
        (0.0, 0.35, 0.1),
        (0.0, 0.42, 0.08),
    ]
    faces = [
        (0, 1, 3),
        (0, 3, 2),
        (1, 4, 3),
        (2, 3, 4),
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj.hide_viewport = True
    obj.hide_render = True

    mat = bpy.data.materials.new("DaskToon_Sakura_Petal")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.98, 0.72, 0.82, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.5
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    obj.data.materials.append(mat)
    return obj


def create_star_sparkle_mesh(col):
    """Create a stylized 4-point anime star sparkle mesh"""
    name = "FX_Star_Sparkle_Mesh"
    obj = bpy.data.objects.get(name)
    if obj:
        return obj

    mesh = bpy.data.meshes.new(name)
    verts = [
        (0.0, 0.0, 0.0),
        (0.0, 0.4, 0.0),
        (0.08, 0.08, 0.0),
        (0.4, 0.0, 0.0),
        (0.08, -0.08, 0.0),
        (0.0, -0.4, 0.0),
        (-0.08, -0.08, 0.0),
        (-0.4, 0.0, 0.0),
        (-0.08, 0.08, 0.0),
    ]
    faces = [
        (0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5),
        (0, 5, 6), (0, 6, 7), (0, 7, 8), (0, 8, 1)
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj.hide_viewport = True
    obj.hide_render = True

    mat = create_impact_energy_material("DaskToon_Magic_Sparkle", (1.0, 0.90, 0.45, 1.0), 3.0)
    obj.data.materials.append(mat)
    return obj


# =============================================================================
# Main Operator: 1-Click Anime FX (Atmospheric + Action Impact)
# =============================================================================

class DASKTOON_OT_add_anime_fx(Operator):
    """Add 1-Click Anime Atmospheric FX & Action Impact Effects"""
    bl_idname = "dasktoon.add_anime_fx"
    bl_label = "Add Anime Effect"
    bl_options = {'REGISTER', 'UNDO'}

    fx_type: EnumProperty(
        name="Effect Type",
        description="Choose the Anime effect to generate",
        items=[
            # Impact FX
            ('IMPACT_SHOCKWAVE', "💥 Impact Shockwave Ring", "Expanding 3D Anime shockwave ring with sharp energy teeth"),
            ('IMPACT_HIT_SPARK', "⚡ Impact Hit Spark Burst", "8-point stylized Anime hit spark explosion with sharp rays"),
            ('IMPACT_SLASH_ARC', "🗡️ Impact Slash Arc", "Curved glowing Anime energy crescent slash blade"),
            ('IMPACT_DEBRIS', "🪨 Ground Debris Blast", "Stylized rock fragments blasting outward from impact point"),
            # Atmospheric FX
            ('BUBBLES_UP', "🫧 Floating Bubbles (Up)", "Anime bubbles gently floating upwards with rainbow iridescence"),
            ('BUBBLES_DOWN', "🫧 Sinking Bubbles (Down / Reverse)", "Anime bubbles floating downwards slowly"),
            ('SAKURA', "🌸 Sakura Petals Fall", "Anime cherry blossom petals drifting and tumbling in the wind"),
            ('SPARKLES', "✨ Magic Sparkles & Stars", "Glowing 4-point anime stars and floating magic stardust"),
            ('LEAVES', "🍃 Wind Gust Leaves", "Anime autumn momiji / green leaves swirling in a breeze"),
            ('RAIN', "🌧️ Anime Cel Rain", "Stylized straight rain streaks falling from above"),
            ('EMBERS', "🔥 Fire Embers & Sparks", "Glowing anime flame sparks rising into the air"),
        ],
        default='IMPACT_SHOCKWAVE'
    )

    particle_count: IntProperty(
        name="Count",
        description="Number of particles / debris count",
        default=120,
        min=5,
        max=5000
    )

    flow_speed: FloatProperty(
        name="Speed / Power",
        description="Speed of floating movement or shockwave burst expansion",
        default=1.0,
        min=0.01,
        max=20.0
    )

    wobble_strength: FloatProperty(
        name="Wobble / Turbulence",
        description="Strength of chaotic gentle swaying in wind/water",
        default=0.8,
        min=0.0,
        max=5.0
    )

    size_scale: FloatProperty(
        name="Size Scale",
        description="Scale of the effect",
        default=1.0,
        min=0.05,
        max=10.0
    )

    def execute(self, context):
        col = get_or_create_collection()
        cur_frame = context.scene.frame_current

        # ---------------------------------------------------------------------
        # 1. 💥 IMPACT SHOCKWAVE RING
        # ---------------------------------------------------------------------
        if self.fx_type == 'IMPACT_SHOCKWAVE':
            ring_name = "FX_Anime_Shockwave_Ring"
            bpy.ops.mesh.primitive_torus_add(
                major_radius=0.1,
                minor_radius=0.03,
                major_segments=48,
                minor_segments=12,
                location=(0, 0, 0.1)
            )
            ring = context.active_object
            ring.name = ring_name
            bpy.ops.object.shade_smooth()
            
            for c in ring.users_collection: c.objects.unlink(ring)
            col.objects.link(ring)

            # Assign glowing gold/white impact energy material
            mat = create_impact_energy_material("DaskToon_Shockwave_Energy", (1.0, 0.95, 0.6, 1.0), 10.0)
            ring.data.materials.append(mat)

            # Animate snappy Anime Impact Scale (Frame 1 -> Frame 8)
            ring.scale = (0.1, 0.1, 0.1)
            ring.keyframe_insert(data_path="scale", frame=cur_frame)
            
            ring.scale = (4.0 * self.size_scale, 4.0 * self.size_scale, 0.8 * self.size_scale)
            ring.keyframe_insert(data_path="scale", frame=cur_frame + int(8 / max(0.1, self.flow_speed)))

            self.report({'INFO'}, "💥 Created Anime Impact Shockwave Ring with Snappy Timing!")
            return {'FINISHED'}

        # ---------------------------------------------------------------------
        # 2. ⚡ IMPACT HIT SPARK BURST
        # ---------------------------------------------------------------------
        elif self.fx_type == 'IMPACT_HIT_SPARK':
            spark_name = "FX_Anime_Hit_Spark_Burst"
            mesh = bpy.data.meshes.new(spark_name)
            
            # 8-ray diamond sharp star burst
            r_long = 1.5 * self.size_scale
            r_short = 0.8 * self.size_scale
            r_core = 0.12 * self.size_scale
            verts = [
                (0, 0, 0),
                (0, r_long, 0), (r_core, r_core, 0), (r_short, r_short, 0), (r_core, 0, 0),
                (r_long, 0, 0), (r_core, -r_core, 0), (r_short, -r_short, 0), (0, -r_core, 0),
                (0, -r_long, 0), (-r_core, -r_core, 0), (-r_short, -r_short, 0), (-r_core, 0, 0),
                (-r_long, 0, 0), (-r_core, r_core, 0), (-r_short, r_short, 0), (0, r_core, 0)
            ]
            faces = []
            for i in range(1, 16):
                faces.append((0, i, i + 1))
            faces.append((0, 16, 1))

            mesh.from_pydata(verts, [], faces)
            mesh.update()

            spark_obj = bpy.data.objects.new(spark_name, mesh)
            col.objects.link(spark_obj)
            spark_obj.location = (0, 0, 1.0)

            mat = create_impact_energy_material("DaskToon_Hit_Spark_Energy", (1.0, 0.98, 0.85, 1.0), 12.0)
            spark_obj.data.materials.append(mat)

            # Animate snappy flash burst (Frames 1 -> 3 -> 7)
            spark_obj.scale = (0.2, 0.2, 0.2)
            spark_obj.keyframe_insert(data_path="scale", frame=cur_frame)
            spark_obj.scale = (1.5, 1.5, 1.5)
            spark_obj.keyframe_insert(data_path="scale", frame=cur_frame + 2)
            spark_obj.scale = (0.01, 0.01, 0.01)
            spark_obj.keyframe_insert(data_path="scale", frame=cur_frame + 6)

            self.report({'INFO'}, "⚡ Created Anime Hit Spark Burst!")
            return {'FINISHED'}

        # ---------------------------------------------------------------------
        # 3. 🗡️ IMPACT SLASH ARC
        # ---------------------------------------------------------------------
        elif self.fx_type == 'IMPACT_SLASH_ARC':
            arc_name = "FX_Anime_Slash_Arc"
            mesh = bpy.data.meshes.new(arc_name)
            
            # Curved crescent arc geometry
            verts = []
            faces = []
            segs = 16
            r_outer = 2.0 * self.size_scale
            r_inner = 1.6 * self.size_scale
            arc_angle = math.pi * 0.75 # 135 degrees crescent

            for s in range(segs + 1):
                t = s / segs
                ang = -arc_angle * 0.5 + t * arc_angle
                # Taper tips
                thick_factor = math.sin(t * math.pi)
                r_in = r_inner + (r_outer - r_inner) * (1.0 - thick_factor) * 0.4
                
                xo = math.cos(ang) * r_outer
                yo = math.sin(ang) * r_outer
                xi = math.cos(ang) * r_in
                yi = math.sin(ang) * r_in
                verts.extend([(xo, yo, 0.0), (xi, yi, 0.0)])

            for s in range(segs):
                idx = s * 2
                faces.append((idx, idx + 1, idx + 3, idx + 2))

            mesh.from_pydata(verts, [], faces)
            mesh.update()

            arc_obj = bpy.data.objects.new(arc_name, mesh)
            col.objects.link(arc_obj)
            arc_obj.location = (0, 0, 1.2)

            mat = create_impact_energy_material("DaskToon_Slash_Energy", (0.3, 0.9, 1.0, 1.0), 10.0) # Cyan blade
            arc_obj.data.materials.append(mat)

            # Animate slash swipe rotation & scale
            arc_obj.scale = (0.3, 0.3, 0.3)
            arc_obj.rotation_euler = (0, 0, -0.5)
            arc_obj.keyframe_insert(data_path="scale", frame=cur_frame)
            arc_obj.keyframe_insert(data_path="rotation_euler", frame=cur_frame)

            arc_obj.scale = (1.2, 1.2, 1.2)
            arc_obj.rotation_euler = (0, 0, 0.8)
            arc_obj.keyframe_insert(data_path="scale", frame=cur_frame + 3)
            arc_obj.keyframe_insert(data_path="rotation_euler", frame=cur_frame + 3)

            arc_obj.scale = (0.01, 0.01, 0.01)
            arc_obj.keyframe_insert(data_path="scale", frame=cur_frame + 6)

            self.report({'INFO'}, "🗡️ Created Anime Slash Arc FX!")
            return {'FINISHED'}

        # ---------------------------------------------------------------------
        # 4. 🪨 IMPACT GROUND DEBRIS / ATMOSPHERIC PARTICLE SYSTEMS
        # ---------------------------------------------------------------------
        emitter_name = f"FX_{self.fx_type}_Emitter"
        is_falling = self.fx_type in {'BUBBLES_DOWN', 'SAKURA', 'LEAVES', 'RAIN'}
        emitter_z = 5.0 if is_falling else (0.0 if self.fx_type == 'IMPACT_DEBRIS' else -1.0)
        
        bpy.ops.mesh.primitive_plane_add(size=3.0 if self.fx_type == 'IMPACT_DEBRIS' else 8.0, location=(0.0, 0.0, emitter_z))
        emitter = context.active_object
        emitter.name = emitter_name
        
        for c in emitter.users_collection: c.objects.unlink(emitter)
        col.objects.link(emitter)
        emitter.hide_render = True

        ps_mod = emitter.modifiers.new(name=f"PS_{self.fx_type}", type='PARTICLE_SYSTEM')
        ps = ps_mod.particle_system
        pset = ps.settings

        pset.count = self.particle_count
        pset.frame_start = cur_frame
        pset.frame_end = cur_frame + 2 if self.fx_type == 'IMPACT_DEBRIS' else (cur_frame + 250)
        pset.lifetime = 60 if self.fx_type == 'IMPACT_DEBRIS' else 180
        pset.lifetime_random = 0.4

        pset.physics_type = 'NEWTON'
        pset.damping = 0.05 if self.fx_type == 'IMPACT_DEBRIS' else 0.15
        
        if self.fx_type == 'IMPACT_DEBRIS':
            pset.normal_factor = self.flow_speed * 6.0 # Blast UPWARDS
            pset.factor_random = 2.0
            pset.effector_weights.gravity = 1.5 # Gravity pulls debris down
            pset.use_rotations = True
            pset.rotation_mode = 'NOR_TAN'
            pset.rotation_factor_random = 1.0
            pset.angular_velocity_mode = 'RAND'
            pset.angular_velocity_factor = 10.0
        elif self.fx_type == 'BUBBLES_UP':
            pset.normal_factor = self.flow_speed * 0.5
            pset.effector_weights.gravity = -0.15
        elif self.fx_type == 'BUBBLES_DOWN':
            pset.normal_factor = -self.flow_speed * 0.5
            pset.effector_weights.gravity = 0.2
        elif self.fx_type == 'SAKURA':
            pset.normal_factor = -self.flow_speed * 0.3
            pset.effector_weights.gravity = 0.25
            pset.factor_random = 0.2
            pset.use_rotations = True
            pset.rotation_mode = 'NOR_TAN'
            pset.rotation_factor_random = 1.0
            pset.angular_velocity_mode = 'RAND'
            pset.angular_velocity_factor = 2.0
        elif self.fx_type == 'SPARKLES':
            pset.normal_factor = self.flow_speed * 0.2
            pset.factor_random = 0.5
            pset.effector_weights.gravity = -0.05
        elif self.fx_type == 'LEAVES':
            pset.normal_factor = -self.flow_speed * 0.4
            pset.effector_weights.gravity = 0.3
            pset.use_rotations = True
            pset.rotation_mode = 'NOR_TAN'
            pset.rotation_factor_random = 1.0
            pset.angular_velocity_mode = 'RAND'
            pset.angular_velocity_factor = 3.0
        elif self.fx_type == 'RAIN':
            pset.normal_factor = -self.flow_speed * 4.0
            pset.effector_weights.gravity = 1.0
            pset.damping = 0.0
        elif self.fx_type == 'EMBERS':
            pset.normal_factor = self.flow_speed * 0.8
            pset.effector_weights.gravity = -0.4
            pset.factor_random = 0.4

        pset.render_type = 'OBJECT'
        pset.particle_size = self.size_scale * 0.4
        pset.size_random = 0.6

        if self.fx_type in {'BUBBLES_UP', 'BUBBLES_DOWN'}:
            bubble_mesh_name = "FX_Bubble_Instance_Sphere"
            bubble_obj = bpy.data.objects.get(bubble_mesh_name)
            if not bubble_obj:
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.5, location=(0, 0, -20))
                bubble_obj = context.active_object
                bubble_obj.name = bubble_mesh_name
                bubble_obj.hide_viewport = True
                bubble_obj.hide_render = True
                for c in bubble_obj.users_collection: c.objects.unlink(bubble_obj)
                col.objects.link(bubble_obj)
                bubble_obj.data.materials.append(create_bubble_material())
            pset.instance_object = bubble_obj

        elif self.fx_type == 'SAKURA':
            sakura_obj = create_sakura_petal_mesh(col)
            pset.instance_object = sakura_obj

        elif self.fx_type in {'SPARKLES', 'EMBERS'}:
            star_obj = create_star_sparkle_mesh(col)
            pset.instance_object = star_obj

        elif self.fx_type == 'IMPACT_DEBRIS':
            # Create low-poly anime rock chunk
            rock_name = "FX_Debris_Rock_Chunk"
            rock_obj = bpy.data.objects.get(rock_name)
            if not rock_obj:
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.25, location=(0, 0, -20))
                rock_obj = context.active_object
                rock_obj.name = rock_name
                rock_obj.hide_viewport = True
                rock_obj.hide_render = True
                for c in rock_obj.users_collection: c.objects.unlink(rock_obj)
                col.objects.link(rock_obj)
                
                rock_mat = bpy.data.materials.new("DaskToon_Debris_Rock")
                rock_mat.use_nodes = True
                bsdf = rock_mat.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    bsdf.inputs['Base Color'].default_value = (0.25, 0.22, 0.20, 1.0)
                    bsdf.inputs['Roughness'].default_value = 0.9
                rock_obj.data.materials.append(rock_mat)
            pset.instance_object = rock_obj

        if self.wobble_strength > 0.001 and self.fx_type != 'IMPACT_DEBRIS':
            turb_name = f"FX_{self.fx_type}_Turbulence"
            turb_obj = bpy.data.objects.get(turb_name)
            if not turb_obj:
                bpy.ops.object.effector_add(type='TURBULENCE', location=(0, 0, 2.0))
                turb_obj = context.active_object
                turb_obj.name = turb_name
                turb_obj.field.strength = self.wobble_strength * 1.5
                turb_obj.field.size = 2.0
                turb_obj.field.flow = 0.5
                for c in turb_obj.users_collection: c.objects.unlink(turb_obj)
                col.objects.link(turb_obj)

        self.report({'INFO'}, f"✨ Created 1-Click Anime Effect: {self.fx_type}!")
        return {'FINISHED'}


# =============================================================================
# UI Panel in DaskToon Sidebar
# =============================================================================

class VIEW3D_PT_dasktoon_anime_fx(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"
    bl_label = "Anime Visual Effects (Impact & Atmosphere)"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # 1. Action & Impact FX Box
        box_impact = layout.box()
        box_impact.label(text="💥 Anime Action & Impact FX:", icon='PHYSICS')
        col_imp = box_impact.column(align=True)
        
        r_imp1 = col_imp.row(align=True)
        op_shock = r_imp1.operator("dasktoon.add_anime_fx", text="💥 Shockwave Ring", icon='SPHERE')
        op_shock.fx_type = 'IMPACT_SHOCKWAVE'
        op_spark = r_imp1.operator("dasktoon.add_anime_fx", text="⚡ Hit Spark", icon='LIGHT_SUN')
        op_spark.fx_type = 'IMPACT_HIT_SPARK'

        r_imp2 = col_imp.row(align=True)
        op_slash = r_imp2.operator("dasktoon.add_anime_fx", text="🗡️ Slash Arc", icon='CURVE_DATA')
        op_slash.fx_type = 'IMPACT_SLASH_ARC'
        op_debris = r_imp2.operator("dasktoon.add_anime_fx", text="🪨 Debris Blast", icon='MOD_EXPLODE')
        op_debris.fx_type = 'IMPACT_DEBRIS'

        layout.separator()

        # 2. Atmospheric & Particle FX Box
        box_atmo = layout.box()
        box_atmo.label(text="🫧 Atmospheric & Weather Particles:", icon='PARTICLES')
        col_atmo = box_atmo.column(align=True)

        r1 = col_atmo.row(align=True)
        op = r1.operator("dasktoon.add_anime_fx", text="🫧 Bubbles (Up)", icon='META_BALL')
        op.fx_type = 'BUBBLES_UP'
        op_down = r1.operator("dasktoon.add_anime_fx", text="🫧 Sinking (Down)", icon='MOD_FLUID')
        op_down.fx_type = 'BUBBLES_DOWN'

        r2 = col_atmo.row(align=True)
        op_sakura = r2.operator("dasktoon.add_anime_fx", text="🌸 Sakura Fall", icon='COMMUNITY')
        op_sakura.fx_type = 'SAKURA'
        op_leaves = r2.operator("dasktoon.add_anime_fx", text="🍃 Wind Leaves", icon='FORCE_WIND')
        op_leaves.fx_type = 'LEAVES'

        r3 = col_atmo.row(align=True)
        op_sparkle = r3.operator("dasktoon.add_anime_fx", text="✨ Magic Sparkles", icon='LIGHT_SUN')
        op_sparkle.fx_type = 'SPARKLES'
        op_embers = r3.operator("dasktoon.add_anime_fx", text="🔥 Fire Sparks", icon='FIRE')
        op_embers.fx_type = 'EMBERS'

        col_atmo.separator()
        op_rain = col_atmo.operator("dasktoon.add_anime_fx", text="🌧️ Anime Cel Rain", icon='MOD_WAVE')
        op_rain.fx_type = 'RAIN'


classes = (
    DASKTOON_OT_add_anime_fx,
    VIEW3D_PT_dasktoon_anime_fx,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
