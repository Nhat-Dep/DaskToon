# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon's Animation tab (docs/superpowers/specs/2026-10-10-dasktoon-animation-tab-design.md, sections 5 to 7): the
"DaskToon Character" keying set, Key Pose, the part of the Dope Sheet header that shows when Whole Character is on, and
the file-load handler that puts DaskToon's tab in place of Blender's. The header also holds the character's clips
(docs/superpowers/specs/2026-10-10-dasktoon-clips-design.md, section 4), their anime timing and the onion skin
(docs/superpowers/specs/2026-10-13-dasktoon-anime-timing-design.md, sections 4 and 6)."""

import types

import bpy
import _keyingsets_utils as keyingsets_utils
from bpy.app.handlers import persistent
from bpy.app.translations import pgettext_iface as iface_, pgettext_rpt as rpt_
from bpy.props import BoolProperty, CollectionProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import KeyingSetInfo, Menu, Operator, Panel, PropertyGroup
from keyingsets_builtins import WholeCharacterMixin


class CharacterKeying(WholeCharacterMixin):
    """What the "DaskToon Character" keying set keys (spec 5). Key Pose keys the same paths itself, so it works from any
    editor."""

    def iterator(self, context, ks):
        from dasktoon_animation import character
        objects = list(context.view_layer.objects)
        for armature in character.selected_characters(context):
            for bone in armature.pose.bones:
                self.generate(context, ks, bone)
            for obj in character.members(armature, objects):
                self.generate_face(ks, obj)
        for obj in context.selected_objects:
            if not character.armatures_of(obj):
                keyingsets_utils.RKS_GEN_location(self, context, ks, obj)
                keyingsets_utils.RKS_GEN_rotation(self, context, ks, obj)
                keyingsets_utils.RKS_GEN_scaling(self, context, ks, obj)

    def generate_face(self, ks, obj):
        """The shape keys (but the Basis) and the expression controllers of a mesh of the character."""
        key = obj.data.shape_keys if obj.type == 'MESH' else None
        if key is not None:
            for block in key.key_blocks:
                if block != key.reference_key:
                    ks.paths.add(key, 'key_blocks["%s"].value' % bpy.utils.escape_identifier(block.name),
                                 group_method='NAMED', group_name=obj.name)
        root = getattr(obj, "dask_shape_controllers", None)
        for i in range(len(root.groups) if root is not None else 0):
            for axis in ("handle_x", "handle_y"):
                ks.paths.add(obj, "dask_shape_controllers.groups[%d].%s" % (i, axis), group_method='NAMED',
                             group_name="Controllers")


class DASKTOON_KS_character(CharacterKeying, KeyingSetInfo):
    """Key the whole pose of the selected characters: every bone, every shape key of their meshes and every expression
    controller; other selected objects get location, rotation and scale"""
    bl_idname = "DASKTOON_KS_character"
    bl_label = "DaskToon Character"

    def poll(self, context):
        from dasktoon_animation import character
        return bool(context.selected_objects) or bool(character.selected_characters(context))


class _Paths(list):
    """Collects what a keying set iterator adds: (ID, data path, index, group)."""

    def add(self, id_block, path, index=-1, group_method='NAMED', group_name=""):
        self.append((id_block, path, index, group_name if group_method == 'NAMED' else ""))


def key_pose(context, frame=None):
    """Key what the "DaskToon Character" keying set keys, on `frame` (the current frame by default). Returns the number
    of paths keyed."""
    ks = types.SimpleNamespace(paths=_Paths())
    CharacterKeying().iterator(context, ks)
    frame = context.scene.frame_current if frame is None else frame
    for id_block, path, index, group in ks.paths:
        id_block.keyframe_insert(data_path=path, index=index, frame=frame, group=group)
    return len(ks.paths)


class DASKTOON_OT_key_pose(Operator):
    """Key the whole pose of the selected characters at the current frame: every bone, shape key and controller"""
    bl_idname = "dasktoon.key_pose"
    bl_label = "Key Pose"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from dasktoon_animation import character, timing
        characters = character.selected_characters(context)
        if not characters and not context.selected_objects:
            self.report({'ERROR'}, rpt_("Select a part of a character to key its pose"))
            return {'CANCELLED'}
        # With anime timing the pose seen is the one of the step's drawn frame: that is where it is keyed.
        armature = header_armature(context)
        frame = timing.drawn_frame(_action(armature), context.scene.frame_current)
        key_pose(context, frame)
        names = [armature.name for armature in characters] or [obj.name for obj in context.selected_objects]
        self.report({'INFO'}, rpt_("Keyed the pose of %s at frame %d") % (", ".join(names), frame))
        return {'FINISHED'}


def header_armature(context):
    """The armature whose clips the header shows: the active object's character, else the first character with a
    selected part; None without one."""
    from dasktoon_animation import character
    obj = context.active_object
    found = character.armatures_of(obj) if obj is not None else []
    if not found:
        found = character.selected_characters(context)
    return found[0] if found else None


class DASKTOON_MT_character_clips(Menu):
    bl_label = "Clips"

    def draw(self, context):
        from dasktoon_animation import clips
        layout = self.layout
        armature = header_armature(context)
        if armature is None:
            layout.label(text="Select a part of a character")
            return
        for clip in clips.clips_of(armature):
            props = layout.operator(DASKTOON_OT_clip_use.bl_idname, text=clip.name, icon='ACTION', translate=False)
            props.clip = clip.name
        layout.separator()
        layout.operator(DASKTOON_OT_clip_new.bl_idname, icon='ADD')
        layout.operator(DASKTOON_OT_clip_delete.bl_idname, icon='X')


def _clip_context(op, context):
    """(armature, objects) of the header's character, or None after reporting why."""
    armature = header_armature(context)
    if armature is None:
        op.report({'ERROR'}, rpt_("Select a part of a character"))
        return None
    return armature, list(context.view_layer.objects)


class DASKTOON_OT_clip_new(Operator):
    """Make a new, empty clip of the character and play it; its animation so far becomes a clip first"""
    bl_idname = "dasktoon.clip_new"
    bl_label = "New Clip"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from dasktoon_animation import clips
        found = _clip_context(self, context)
        if found is None:
            return {'CANCELLED'}
        clip = clips.new(*found, scene=context.scene)
        self.report({'INFO'}, rpt_("New clip %s") % clip.name)
        return {'FINISHED'}


class DASKTOON_OT_clip_use(Operator):
    """Play this clip on the whole character: body and face"""
    bl_idname = "dasktoon.clip_use"
    bl_label = "Use Clip"
    bl_options = {'REGISTER', 'UNDO'}

    clip: StringProperty(name="Clip")

    def execute(self, context):
        from dasktoon_animation import clips
        found = _clip_context(self, context)
        if found is None:
            return {'CANCELLED'}
        clip = next((c for c in clips.clips_of(found[0]) if c.name == self.clip), None)
        if clip is None:
            self.report({'ERROR'}, rpt_("No clip %s") % self.clip)
            return {'CANCELLED'}
        clips.use(*found, clip, context.scene)
        return {'FINISHED'}


class DASKTOON_OT_clip_delete(Operator):
    """Delete the clip the character plays; it plays the first clip left"""
    bl_idname = "dasktoon.clip_delete"
    bl_label = "Delete Clip"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        from dasktoon_animation import clips
        armature = header_armature(context)
        return armature is not None and clips.current(armature) is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        from dasktoon_animation import clips
        armature, objects = header_armature(context), list(context.view_layer.objects)
        clip = clips.current(armature)
        name = clip.name
        clips.delete(armature, objects, clip, context.scene)
        self.report({'INFO'}, rpt_("Deleted clip %s") % name)
        return {'FINISHED'}


def _action(armature):
    """The action the character plays (its clip), or None."""
    anim = armature.animation_data if armature is not None else None
    return anim.action if anim is not None else None


def timing_label(context):
    """The header's Timing button text: the step at the current frame ("2s", "Hold")."""
    from dasktoon_animation import timing
    action = _action(header_armature(context))
    return iface_(timing.LABELS[timing.step_at(action, context.scene.frame_current)])


class DASKTOON_OT_timing_set(Operator):
    """From the current frame the clip runs on this step, until the next timing row"""
    bl_idname = "dasktoon.timing_set"
    bl_label = "Set Timing Here"
    bl_options = {'REGISTER', 'UNDO'}

    step: IntProperty(name="Step", description="1 to 4 frames per drawing, or 0 to hold", default=2, min=0, max=4)

    def execute(self, context):
        from dasktoon_animation import timing
        action = _action(header_armature(context))
        if action is None:
            self.report({'ERROR'}, rpt_("Key a pose first"))
            return {'CANCELLED'}
        timing.set_step(action, context.scene.frame_current, self.step)
        return {'FINISHED'}


class DASKTOON_OT_timing_remove(Operator):
    """Remove this timing row: the timing before it goes on"""
    bl_idname = "dasktoon.timing_remove"
    bl_label = "Remove Timing"
    bl_options = {'REGISTER', 'UNDO'}

    frame: IntProperty(name="Frame")

    def execute(self, context):
        from dasktoon_animation import timing
        action = _action(header_armature(context))
        if action is not None:
            timing.remove(action, self.frame)
        return {'FINISHED'}


class DASKTOON_PT_character_timing(Panel):
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'HEADER'
    bl_label = "Timing"

    def draw(self, context):
        from dasktoon_animation import timing
        layout = self.layout
        action = _action(header_armature(context))
        if action is None:
            layout.label(text="Key a pose first")
            return
        layout.label(text="Set timing from this frame:")
        row = layout.row(align=True)
        for step in (1, 2, 3, 4, timing.HOLD):
            row.operator(DASKTOON_OT_timing_set.bl_idname, text=iface_(timing.LABELS[step]),
                         translate=False).step = step
        if not len(action.dasktoon_timing):
            layout.label(text="The clip runs on 1s")
        for item in action.dasktoon_timing:
            row = layout.row(align=True)
            row.label(text=iface_("From frame %d: %s") % (item.frame, iface_(timing.LABELS.get(item.step, "?"))),
                      translate=False)
            row.operator(DASKTOON_OT_timing_remove.bl_idname, text="", icon='X').frame = item.frame
        layout.label(text="Key on the drawn frames: a key between them shows from the next one", icon='INFO')


# Onion skin (anime timing spec 6). A timer copies the ghosts once the frame, the clip and the settings have stayed the
# same for a tick and nothing plays; a draw handler shows them in every 3D Viewport.
ONION_TICK = 0.2
ONION_CACHE = 16  # ghost frames kept while the animation does not change
ONION_COLORS = {'BEFORE': (1.0, 0.25, 0.2), 'AFTER': (0.2, 0.55, 1.0)}
_onion = {"ghosts": [], "frame": None, "batches": None, "seen": None, "drawn": None, "edits": 0, "cache": {},
          "cache_key": None, "capturing": False, "handle": None}


def onion_ghosts():
    """[(side 'BEFORE' or 'AFTER', rank (0 nearest), frame, [(object name, triangles)])] the onion skin shows."""
    return _onion["ghosts"]


def _onion_redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def _set_ghosts(ghosts, frame):
    _onion["ghosts"], _onion["frame"], _onion["batches"] = ghosts, frame, None
    _onion_redraw()


def onion_refresh(context):
    """Copy the ghosts of the header's character at the scene's frame. While a pose in the scene has changes that are
    not keyed, jumping to other frames would lose them: then nothing is copied, the old ghosts stay, and it returns
    False."""
    from dasktoon_animation import character, onion
    scene = context.scene
    settings = scene.dasktoon_onion
    armature = header_armature(context)
    action = _action(armature)
    if not settings.show or action is None:
        _set_ghosts([], None)
        return True
    objects = list(context.view_layer.objects)
    if onion.unkeyed_changes(onion.animated_ids(objects), scene.frame_current):
        return False
    before, after = onion.ghost_frames(action, scene.frame_current, settings.before, settings.after)
    meshes = [obj for obj in character.members(armature, objects) if obj.type == 'MESH' and obj.visible_get()]
    cache_key = (scene.name, action.name, _onion["edits"], tuple(obj.name for obj in meshes))
    if _onion["cache_key"] != cache_key:
        _onion["cache"], _onion["cache_key"] = {}, cache_key
    cache = _onion["cache"]
    missing = [frame for frame in before + after if frame not in cache]
    if missing:
        _onion["capturing"] = True
        try:
            cache.update(onion.capture(context, meshes, missing))
        finally:
            _onion["capturing"] = False
    ghosts = ([('BEFORE', rank, frame, cache[frame]) for rank, frame in enumerate(before)] +
              [('AFTER', rank, frame, cache[frame]) for rank, frame in enumerate(after)])
    for frame in list(cache)[:max(0, len(cache) - ONION_CACHE)]:
        del cache[frame]
    _set_ghosts(ghosts, (scene.name, scene.frame_current))
    return True


def _onion_signature(context):
    scene = context.scene
    settings = scene.dasktoon_onion
    armature = header_armature(context)
    action = _action(armature)
    return (scene.name, scene.frame_current, settings.show, settings.before, settings.after,
            armature.name if armature is not None else "", action.name if action is not None else "", _onion["edits"])


def _onion_tick():
    windows = list(bpy.context.window_manager.windows)
    if not windows or not any(scene.dasktoon_onion.show for scene in bpy.data.scenes):
        _onion["seen"] = _onion["drawn"] = None
        _set_ghosts([], None)
        return None
    if any(window.screen.is_animation_playing or len(getattr(window, "modal_operators", ())) for window in windows):
        _onion["seen"] = None
        return ONION_TICK
    with bpy.context.temp_override(window=windows[0]):
        signature = _onion_signature(bpy.context)
        if signature == _onion["drawn"]:
            return ONION_TICK
        if signature != _onion["seen"]:
            _onion["seen"] = signature  # still changing: copy once it stays for a tick
            return ONION_TICK
        if onion_refresh(bpy.context):
            _onion["drawn"] = signature
    return ONION_TICK


def _onion_start():
    if not bpy.app.timers.is_registered(_onion_tick):
        bpy.app.timers.register(_onion_tick, first_interval=ONION_TICK, persistent=True)


@persistent
def _onion_depsgraph(_scene, depsgraph):
    """Keys or meshes changed: the copied ghosts are old."""
    if not _onion["capturing"] and any(isinstance(update.id, (bpy.types.Action, bpy.types.Mesh))
                                       for update in depsgraph.updates):
        _onion["edits"] += 1


ONION_PUSH = 1.001  # ghosts are drawn as if 0.1% farther away: where one lies on the mesh, the mesh shows
ONION_VERTEX = """
void main()
{
  vec4 clip = perspective * vec4(pos, 1.0);
  /* depth.x, depth.y: the window matrix's z row; depth.z: the push; depth.w: 1 for a perspective view. */
  float z = depth.w > 0.5 ? -clip.w : (clip.z - depth.y) / depth.x;
  float pushed = z * depth.z;
  float ndc = depth.w > 0.5 ? (depth.x * pushed + depth.y) / -pushed : depth.x * pushed + depth.y;
  gl_Position = vec4(clip.xy, ndc * clip.w, clip.w);
}
"""


def _onion_shader():
    import gpu
    if _onion.get("shader") is None:
        info = gpu.types.GPUShaderCreateInfo()
        info.push_constant('MAT4', "perspective")
        info.push_constant('VEC4', "depth")
        info.push_constant('VEC4', "color")
        info.vertex_in(0, 'VEC3', "pos")
        info.fragment_out(0, 'VEC4', "fragColor")
        info.vertex_source(ONION_VERTEX)
        info.fragment_source("void main()\n{\n  fragColor = color;\n}\n")
        _onion["shader"] = gpu.shader.create_from_info(info)
    return _onion["shader"]


def _onion_draw():
    context = bpy.context
    scene = context.scene
    settings = scene.dasktoon_onion
    if (not settings.show or not _onion["ghosts"] or _onion["frame"] != (scene.name, scene.frame_current)
            or context.screen.is_animation_playing or context.region_data is None):
        return
    import gpu
    from gpu_extras.batch import batch_for_shader
    shader = _onion_shader()
    view = context.region_data
    shader.bind()
    shader.uniform_float("perspective", view.perspective_matrix)
    shader.uniform_float("depth", (view.window_matrix[2][2], view.window_matrix[2][3], ONION_PUSH,
                                   1.0 if view.is_perspective else 0.0))
    if _onion["batches"] is None:
        _onion["batches"] = [(side, rank, batch_for_shader(shader, 'TRIS', {"pos": triangles}))
                             for side, rank, _frame, shapes in _onion["ghosts"]
                             for _name, triangles in shapes if len(triangles)]
    counts = {'BEFORE': max(settings.before, 1), 'AFTER': max(settings.after, 1)}
    state = gpu.state.blend_get(), gpu.state.depth_test_get(), gpu.state.depth_mask_get()
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.depth_mask_set(False)
    for side, rank, batch in _onion["batches"]:
        # The nearest ghost has the set opacity; farther ones fade.
        shader.uniform_float("color", (*ONION_COLORS[side], settings.opacity * (counts[side] - rank) / counts[side]))
        batch.draw(shader)
    gpu.state.blend_set(state[0])
    gpu.state.depth_test_set(state[1])
    gpu.state.depth_mask_set(state[2])


def _onion_show_changed(self, _context):
    if self.show:
        _onion_start()


class DaskOnionSkin(PropertyGroup):
    """Onion skin of the character being animated (anime timing spec 6)"""
    show: BoolProperty(
        name="Onion Skin", update=_onion_show_changed,
        description="Show faintly, in the 3D Viewports, the character's poses at the keys before and after this frame")
    before: IntProperty(name="Before", description="How many keyed poses before this frame to show", default=1,
                        min=0, max=8)
    after: IntProperty(name="After", description="How many keyed poses after this frame to show", default=1, min=0,
                       max=8)
    opacity: FloatProperty(name="Opacity", description="How visible the nearest ghost is; farther ones fade",
                           default=0.3, min=0.0, max=1.0, subtype='FACTOR')


class DASKTOON_PT_onion_skin(Panel):
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'HEADER'
    bl_label = "Onion Skin"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.dasktoon_onion
        layout.prop(settings, "before")
        layout.prop(settings, "after")
        layout.prop(settings, "opacity", slider=True)
        layout.label(text="Ghosts are the keyed poses; they update when you stop for a moment", icon='INFO')


def draw_character_header(layout, context):
    """DaskToon's part of the Dope Sheet header while Whole Character is on: Key Pose and the character's clips (clips
    spec 4); timing comes here too (spec 7)."""
    from dasktoon_animation import clips
    layout.operator(DASKTOON_OT_key_pose.bl_idname, icon='KEY_HLT')
    armature = header_armature(context)
    if armature is None:
        return
    clip = clips.current(armature)
    row = layout.row(align=True)
    label = clip.name if clip is not None else iface_("No Clip")
    row.menu(DASKTOON_MT_character_clips.__name__, text=label, icon='ACTION', translate=False)
    if clip is not None:
        row.prop(clip, "name", text="")
        row.prop(clip, "use_cyclic", text="Loop", toggle=True)
    row.operator(DASKTOON_OT_clip_new.bl_idname, text="", icon='ADD')
    layout.popover(DASKTOON_PT_character_timing.__name__, text=timing_label(context), translate=False)
    onion_skin = context.scene.dasktoon_onion
    row = layout.row(align=True)
    row.prop(onion_skin, "show", toggle=True, icon='ONIONSKIN_ON' if onion_skin.show else 'ONIONSKIN_OFF')
    row.popover(DASKTOON_PT_onion_skin.__name__, text="")


def use_character_keying_set(scene):
    """A scene without an active keying set keys whole characters with I (spec 5). True when it was set."""
    from dasktoon_animation import KEYING_SET
    keying_sets = scene.keying_sets_all
    if keying_sets.active is not None:
        return False
    found = next((ks for ks in keying_sets if ks.bl_idname == KEYING_SET), None)
    if found is None:
        return False
    keying_sets.active = found
    return True


@persistent
def load_post(_filepath):
    """A file was opened (the startup file and New too): DaskToon's Animation tab, and the character keying set for I
    in scenes without one (spec 5, 6)."""
    from dasktoon_animation import tab
    tab.ensure_animation_tab()
    tab.show_render_in_camera_view()
    for scene in bpy.data.scenes:
        use_character_keying_set(scene)
    _onion.update(ghosts=[], frame=None, batches=None, seen=None, drawn=None, cache={}, cache_key=None)
    if any(scene.dasktoon_onion.show for scene in bpy.data.scenes):
        _onion_start()


class DaskTimingStep(PropertyGroup):
    """From this frame the clip runs on this step, until the next row"""
    frame: IntProperty(name="Frame", description="Frame the step starts at")
    step: IntProperty(name="Step", description="Frames each drawing is held: 1 to 4, or 0 to hold this frame",
                      default=2, min=0, max=4)


classes = (
    DaskTimingStep,
    DaskOnionSkin,
    DASKTOON_PT_onion_skin,
    DASKTOON_KS_character,
    DASKTOON_OT_key_pose,
    DASKTOON_MT_character_clips,
    DASKTOON_OT_clip_new,
    DASKTOON_OT_clip_use,
    DASKTOON_OT_clip_delete,
    DASKTOON_OT_timing_set,
    DASKTOON_OT_timing_remove,
    DASKTOON_PT_character_timing,
)


def _is_armature(_action, obj):
    return obj.type == 'ARMATURE'


# bl_ui registers `classes`; register() adds the file-load handler and the clip's character.
def register():
    bpy.types.Action.dasktoon_character = PointerProperty(
        name="Character", description="Armature of the character this action is a clip of (DaskToon)",
        type=bpy.types.Object, poll=_is_armature)
    bpy.types.Action.dasktoon_timing = CollectionProperty(
        name="Timing", type=DaskTimingStep,
        description="Anime timing of the clip: from each row's frame it runs on that row's step (DaskToon)")
    bpy.types.Scene.dasktoon_onion = PointerProperty(
        name="Onion Skin", type=DaskOnionSkin, description="Onion skin of the character being animated (DaskToon)")
    if load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post)
    if _onion_depsgraph not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_onion_depsgraph)
    if _onion["handle"] is None:
        _onion["handle"] = bpy.types.SpaceView3D.draw_handler_add(_onion_draw, (), 'WINDOW', 'POST_VIEW')


def unregister():
    if load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post)
    if _onion_depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_onion_depsgraph)
    if _onion["handle"] is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_onion["handle"], 'WINDOW')
        _onion["handle"] = None
    if bpy.app.timers.is_registered(_onion_tick):
        bpy.app.timers.unregister(_onion_tick)
    del bpy.types.Action.dasktoon_character
    del bpy.types.Action.dasktoon_timing
    del bpy.types.Scene.dasktoon_onion
