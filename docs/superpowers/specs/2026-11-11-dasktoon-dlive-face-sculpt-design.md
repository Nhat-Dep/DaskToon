# Face keys sculpted from nothing (.dlive export)

Date: 2026-11-11. Part of the .dlive design (2026-11-10-dasktoon-dlive-design.md); builds on the auto expressions design
(2026-10-20).

## Goal

A character with no face shape keys, with or without a DaskToon rig, leaves the .dlive export with every ARKit key a face's own
shape can make, and the VRM presets (a i u e o, angry, sorrow, fun, with blink, joy and surprised from the eye sculpting).
`expressions.json` `made` says how each was made (`how`) and lists what could not be (`missing`).

## Order of making

1. Mirror modifiers of copies without shape keys are applied (a character modelled in half): a key of one side needs a real side.
2. Auto Expressions (eyes, vowels of a mouth that opens), then fill from keys that move (existing).
3. The ARKit 52 from the VRM keys (existing `synthesize_arkit52`, now told which way the character's left is in each mesh:
   a character facing +Y has its left at the mesh's -X).
4. Keys made from whole-face keys are confined to the place they belong (a smile that closed an eye loses that).
5. For each ARKit face key that no key moves where it should (`face_shapes.Face.does_work`): sculpt it.
6. VRM presets nothing moves yet are added up from the ARKit fields.

A key that already moves where it belongs is never touched.

## Finding the face without a DaskToon rig (`dasktoon_rig/face_frame.py`)

`located` gives the existing eye, mouth and expression code a temporary armature (a Head bone a unit long, centred on the
origin; the object's transform maps the head's frame onto the scene, any size, facing any of four ways), the parts the names and
shapes of the meshes suggest and an Armature modifier on each mesh that moves nothing. The head is where eye_shapes finds eyes:
small twin pieces, one each side of a middle, in front of the head's centre; every size from a seventh to the whole of the
character's height and every facing is tried, a cheap prefilter first, `find_eyes` last. A humanoid armature of any naming
(dasktoon_import.bones.classify) narrows the sizes by its head bone. No eyes, no frame, nothing sculpted.

## Sizes

Everything is the face's own: W the eyes' width, A the distance between them, H half the mouth's width (a slit, a drawn line,
pieces, else where a mouth lies below the eyes, no lower than half way to the chin). No number is in metres. Fields fade
smoothly to nothing; only the loose pieces that make the face's skin move (a hair lock of the same mesh in front of the cheek
is another piece); of other meshes only small pieces lying in the mouth's place (teeth, a tongue).

- brows: loose pieces over the eyes (a mesh of their own, or lying on the skin of the head's mesh) move as they are; else the
  skin from the lid up to 1.3 W over it. Inner up, outer up, down differ in how the move fades from the middle outward.
- eyes: wide and squint scale each eye about its middle (pieces and the skin round them).
- cheeks, nose: lift under the eye; swell along the surface; the nose's wings rise and spread.
- mouth: pucker, funnel, left/right, rolls, shrugs, press, stretch, dimple, smile, frown, lower down, upper up, close:
  fields round the mouth tapering by H.
- jaw: the lower face turns about the ear (forward, left, right, open), fading out past the ears, the chin and the back of the head.

## Not made

tongueOut (no tongue mesh), eyeLook* (an eyeball turning inside a face's hole: the game turns the eye bones).

## Tests

dasktoon_face_sculpt_test.py: a head with eye pieces and no armature; brows as pieces of the head's mesh; brows as meshes of
their own; no brows; Japanese bone names; facing +Y; modelled in half; displacement limits; pairs mirror; hair never moves.

## Rulings from the real characters (2026-11-11)

- filie (no rig, no keys, modelled in half, faces +Y): 55 of 56 keys ARKit-or-VRM; the head is found from her eye pieces, the Mirror
  modifiers applied on the export's copies. Her hair covers her brows and her face is flat shaded: the keys are small, not
  broken.
- tdt (an armature object not in the file): the same way; brows and eyeWide are no longer missing. A hair lock of the Body mesh
  in front of the cheek once zigzagged with a jaw key: only the skin's own pieces move.
- lr (faces +Y, no rig): all but look and tongue.
- A key the export made from a whole-face key (joy) and that moved what lies outside its place (a smile that closed an eye) is
  confined to the place; a cheek key leaves a margin of 0.3 of an eye's width under the eye, or the eye's own pieces warp.
- The eye bones of a skeleton are the eyes of a face with no eye pieces (sockets and lids); no blink is made there (closing
  skin onto a line is no lid).
- The look keys are not made: an iris wider than the hole of the face it is seen through comes out in front of the skin when
  it moves.
