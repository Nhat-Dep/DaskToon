# Model Guide: a newcomer makes an anime model DaskToon can take all the way

Date: 2026-10-20. The user asked: "có thể tạo cơ chế hướng dẫn để 1 người mới cũng có thể làm model anime đúng?" and
chose: a model check, step-by-step steps and reading pages (no template model); "right" meaning DaskToon's automatic
tools (auto rig, bend fixes, expressions, shader, Unity export) work on it without hand fixes; in the 3D viewport's
sidebar; design approved, then autonomous ("Duyệt, làm tự động").

## Where

A tab **Guide** ("Hướng dẫn") in the 3D Viewport's sidebar (N), two panels: **Model Check** and **Steps**. The UI spec
of 2026-10-04 removed every DaskToon panel from the viewport sidebar; the user's choice of 2026-10-20 makes the Guide the
one exception (the sidebar stays in view while modelling). The reading pages open in the web browser, shipped with
DaskToon (no network needed), English and Vietnamese, the one matching the interface language.

## The character checked

The character of the selection: a selected DaskToon rig or a mesh it deforms means that rig's meshes; otherwise the
selected meshes; nothing selected, every visible mesh of the scene.

## Model Check

**Check** runs every check and lists the results; **Check Again** after a change. Each result: ✓ fine, ⚠ should be
fixed, ✗ must be fixed (the automatic tools fail on it), one sentence why, **Fix** when DaskToon can fix it, **?** that
opens the page at that check. Results live in the window (not saved in the file). The checks reuse what the automatic
tools use, so they agree with them.

| Group | Check | Rule | Fix |
|---|---|---|---|
| Standing | Size | height 0.5 to 3.5 m, else ⚠ | scale the character to 1.6 m about its feet |
| | On the floor | lowest point within 2% of the height of 0, else ⚠ | move it onto the floor |
| | In the middle | across the middle of its lower legs within 5% of the height of x = 0 and y = 0, else ⚠ | move it there |
| | Facing the front | its feet (facing.py) reach -Y within 30°: ✓; another way: ✗; the feet do not tell: ⚠ | turn it to the front |
| | T or A pose | width / height ≥ 0.55 ✓, 0.45 to 0.55 ⚠ (arms low), below ✗ (arms down) | — |
| Mesh | Even scale | no mesh stretched by an uneven scale ⚠; a negative scale (mirrored) ✗ | Apply Scale on them |
| | Normals outside | the Body's faces point outward (Build's test) | recalculate them outside |
| | Mirror applied | no Mirror modifier (bend fixes skip such meshes) ⚠ | apply it (meshes without shape keys) |
| | No n-gons | no face with more than 4 sides (Unity export warns) ⚠ | split those faces into triangles |
| | Separate parts | at least two meshes, or one with three loose pieces or more ⚠ | — |
| Materials | UV map | every mesh has one (textures, export bakes) ⚠ | Smart UV Project |
| | DaskToon shader | every material a face uses has the Anime BSDF ⚠ | Use DaskToon Shader on them |
| | No unused materials | no slot that no face uses ⚠ | remove those slots |
| After the rig | Rig | a DaskToon humanoid rig deforms the meshes ✗ | the auto rig (Add › Armature › Anime Humanoid) |
| | Rig Check | the rig's Check has run and found nothing ⚠ | run the Check |
| | Joint loops | each knee and elbow blends over enough vertices of the Body (the bend fixes need them) ⚠ | — |
| | Eyes | loose eye pieces in front of the face (Sculpt Eye Expressions), or an expression key that closes the eyes ⚠ | — |
| | Mouth | a drawn mouth or mouth plates (joy smiles), or mouth keys ⚠ | — |
| | Expressions | a blink key that moves ✓; empty expression keys ⚠ | Sculpt Eye Expressions / Fill Empty Expressions |

## Steps

Nine steps, each with a few lines of advice, its checks, its main buttons and a link to its page; the first step that
is not done opens, a done step shows a tick:

1. New model (any mesh); 2. Body (Size, On the floor, In the middle, Facing, T or A pose, Even scale, Normals);
3. Head and face (Separate parts, Mirror); 4. Hair (Separate parts); 5. Clothes (No n-gons); 6. Materials (UV map,
DaskToon shader, No unused materials); 7. Rig (Rig, Rig Check, Joint loops); 8. Expressions (Eyes, Mouth,
Expressions); 9. Unity (done once Engine Export has written this file's character, marked on the scene).

## Pages

One HTML page a step, a section a check, short, with pictures made from the test characters (never the user's),
under `scripts/modules/dasktoon_guide/pages/<en|vi>/`. Written for a newcomer: what to do, why DaskToon needs it, how to
see it in Blender.

## Rulings (autonomous)

1. Eyes and mouth are checked after the rig: they need the head's frame, which only the rig gives. Cost if wrong: a
   newcomer learns about their eyes at step 8, not step 3 (the page of step 3 explains them first).
2. Arms are judged by the width over the height, not by fitting a skeleton: quick, and the chibi and adult models pass
   the same way. Cost if wrong: a wide skirt or big hair could hide arms that hang down.
3. The joint loops check reads the rig's weights (blended vertices), not edge loops: it measures what the bend fixes use.
4. No live checking: a check runs on the button (some take a second on big meshes).
5. The Guide tab is the one DaskToon panel in the viewport sidebar (user's choice over the UI spec of 2026-10-04).
6. Even scale, not "applied transforms": a rotated or evenly scaled object is fine for every DaskToon tool (the real
   models had both); only an uneven or negative scale breaks the weights and the export. Cost if wrong: none known.
7. Joints: at least 8 vertices blending across each knee and elbow (a thin tube of the test chibi blends over 6 or 7 at
   its elbow, the regions chibi's limbs pass). Cost if wrong: a low-poly limb that still bends fine gets a warning.
