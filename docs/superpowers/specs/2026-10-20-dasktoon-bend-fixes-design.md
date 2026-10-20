# Bend fixes: corrective shape keys made by Build Rig (DaskToon + Unity)

Date: 2026-10-20. The user asked for automatic shape keys: "Biểu cảm mặt cơ bản, Sửa chỗ gập (corrective), tư thế
khung xương thử nghiệm trước". This spec covers the second part, chosen as "Làm, cả trong Unity". Autonomous mode
("Tự động, làm liên tục"): the rulings below were made without the user and are listed for review.

## Problem

DaskToon skins with plain linear blending (the Armature modifier without Preserve Volume; Unity skins the same way).
A vertex weighted between two bones lands on the straight line between where each bone would put it, so a bent knee or
hip loses volume at the joint: the front of the knee flattens, the seat of a sitting character caves in and its shorts
leave a gap at the hem.

Spike on the user's character tdt (copy, 2026-10-20), joint bent 90°: the knee keeps its round front, the seat stays
full and the hem closes; the elbow and the A-posed shoulder change little (their weights blend over few vertices).

## What it does

Build Rig makes, for each side, four bend fixes: Knee (lower leg bent back), Elbow (forearm bent forward), Hip (thigh
raised forward, sitting) and Shoulder (arm lowered along the body; skipped when the arm already hangs within 20° of
down). Each is a shape key `DT_Fix_<Side><Joint>` on every mesh of the character whose vertices blend across that joint.

**The shape.** At the fix's pose (the child bone turned from its rest direction d0 to the target direction d1, about
the joint, by the angle θ between them), a vertex with the share `a` of its weight on the child side (the child bone and
everything below it) goes where turning it about the joint by a·θ puts it — the rotation blend — instead of where linear
blending puts it. The key holds the rest-space offset that makes linear blending land there: with
`M = (1 - a)·I + a·R(θ)`, offset = M⁻¹ (target - linear). Vertices wholly on one side do not move. A key whose largest
offset is under 0.05% of the character's height is not made.

**When it shows.** d0 is the child bone's own direction. The child's swing from rest as seen from its parent (its turn
without the twist about itself), as the swing quaternion's vector v = sin(α/2)·n, splits into the bend along the fix's
arc, 2·asin(v·axis), and the swing off it, 2·asin(v·across) (across = d0 × axis). The key's value is
`clamp(bend/θ) · clamp(1 - |off|/θ)`: 0 at rest and for a limb swung the other way, exactly bend/θ along the arc, 1 at
the fix's pose and past it (a kneeling knee keeps its fix), fading for a limb swung elsewhere (a leg raised to the side
leaves the sitting fix at 0). A first version measured the angle to the target (a cone): past the pose the fix faded
again, so a deeper bend lost it.

In DaskToon a driver works it out without Python (no Auto Run): two Transform variables read the child's local
rotation in Swing and Y Twist mode, which gives 2·asin of v's X and Z, so sin(x/2) and sin(z/2) are v's components in
the bone's frame; the expression is arithmetic, asin, min, max, abs and clamp (under Blender's 255 characters). No
helper bone is needed. Key Pose leaves shape keys a driver sets.

**Unity.** The rig file gets `correctives`: shape key, parent, child, the angle and the target direction in the
character's frame (left, up, front from the rest skeleton: the upper legs, Hips and Head). DaskToon's importer adds one
`DaskToonCorrective` to the model; at import (the model's rest pose) it turns the target into the parent bone's frame and
takes the child's +Y (Unity keeps a Blender bone's +Y along it) as d0; in LateUpdate it sets the blend shape weight
(×100) on every SkinnedMeshRenderer that has the shape, by the same formula. Unity's frame is mirrored from Blender's,
so the front is up × left there (left × up in Blender); the swing's sign flips with the cross products on both sides,
so bend comes out the same and off only changes sign (it is used as |off|). The Unity test turns each child to the
direction a DaskToon pose gives it and finds the driver's value within 0.01, and checks against the model's own bones
that the knee's target points back, the hip's and elbow's forward and the shoulder's down.

**Setting.** Rig setting "Bend Fixes" (on by default), in Anime Rig › Joints below Shoulder Follows Arm. Off, Build Rig
removes the fixes. Building again remakes them (a key edited by hand is replaced). The rig file is written for a rig
whose only content is its fixes, so Unity gets the scripts too.

## Deeper bends, the outer side only (2026-10-20, morning)

The user then asked for more poses ("Thêm tư thế sửa chỗ gập"). Knees and elbows get a second fix on the same arc:
`DT_Fix_<Side>KneeDeep` at 150 degrees (kneeling) and `DT_Fix_<Side>ElbowDeep` at 140 degrees (a forearm folded up).
The 90 degree key rises from 0 to 1 up to 90 degrees, then falls back to 0 at the deep fix's bend while the deep key
rises; past 150 the deep key stays at 1. Each key has a start, its angle and an end (0 when it stays past its pose),
and fades off the arc over the arc's first bend:
`clamp((bend - start) / (angle - start)) * clamp((end - bend) / (end - angle)) * clamp(1 - |off| / reach)`;
the driver expression stays under 255 characters, the rig file carries start, end and reach, and Unity's script works
the same weight out (scripts version 7). On tdt (copy): the knee keeps its round front at 120, 135 and 150 degrees.

The user then asked to see it with DaskToon's shader ("thử trên có shader"): tdt, lr_shape and RG2 (copies) with Use
DaskToon Shader on every material and the anime engine. Two changes came of it:

- Only the outer side of a bend is fixed (the knee cap, the seat, the top of the shoulder), where linear blending loses
  the volume. On the inner side (the back of the knee, the groin) the turned vertices bulged into a bump at the top of
  the shin and a fold at the groin. The key fades from one side to the other over a band half the vertex's distance
  from the bone wide.
- No fix for the arm raised (`ShoulderUp`, tried that morning): with the arm up the armpit is the outer, stretched side,
  and keeping its volume bulged it out (tdt) and pushed the skin through the shirt (lr_shape). The arm-down fix stays
  (RG2, T-posed: a rounder shoulder top, nothing in the armpit).

A mesh with a Mirror modifier gets no fixes: the shape key sits under the Mirror, so a fix made on one half showed on
the other half too, whose limb was not bent (a sleeve moved 0.48 m in Wave; the deep fixes, about four times larger
in rest space at 150 degrees, showed it). lr_shape models halves so; its mirrored meshes go without fixes.

## Rulings (autonomous)

1. One fix per joint at one pose (90° for knee, elbow, hip; arm down for the shoulder) at first; deep knee and elbow
   bends were added the next morning on the user's word (section above); the arm up was tried and dropped.
2. The rotation blend is the target, not a sculpted or smoothed shape: it is exact, cannot make a rigid part move, and
   matches what the spike showed. Cost if wrong: elbows gain little on meshes with narrow weight blends.
3. Elbow bends forward (palms-down T-pose); knee bends back; hip forward. Cost if wrong: a rig with other conventions
   gets fixes that never fire (the cone falls off), never wrong shapes at rest.
4. Built by Build Rig, on by default, not a separate button: "tự shapekey" was asked as automatic.
5. Clips still bake the key values (the FBX exporter samples every shape key); the Unity component overrides them each
   frame from the pose, so Mecanim retargeted clips get the fixes too.
6. No fixes on a mesh with a Mirror modifier (above). Cost if wrong: mirrored halves keep linear blending's flat
   joints; applying the Mirror before Build Rig gives them fixes.
7. The outer side only (above). Cost if wrong: an inner side that does lose volume (a thick thigh against the calf)
   keeps linear blending's crease there.
8. No arm-up fix (above). Cost if wrong: raised arms keep linear blending's thin shoulder; the shoulders' own lift
   (Shoulder Follows Arm) still helps there.
