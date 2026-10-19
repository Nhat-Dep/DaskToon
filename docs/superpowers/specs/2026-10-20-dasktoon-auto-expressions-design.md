# Automatic expression shape keys: filling the gaps and sculpting the eyes

Date: 2026-10-20. The user asked for automatic shape keys ("Biểu cảm mặt cơ bản") and chose "Lấp chỗ trống + tự nặn
cho model chưa có", autonomous ("Tự động, làm liên tục"). The rulings below were made without the user. The bend fixes
are their own spec (2026-10-20-dasktoon-bend-fixes-design.md).

## What the user's characters have

- tdt and lr_shape: 31 expression keys (VRM 0.x and ARKit-like). "e" barely moves (34 vertices, 0.9 mm, where "a"
  moves 8.4 mm), "mouthUpperUp" and "neutral" move nothing.
- pl1, RGforGame, filie: no shape keys. Their eyes are loose pieces in front of the face (eye white, iris, upper and
  lower lashes; in the body mesh for pl1 and RGforGame, in the meshes "mat" and "mi" for filie), not eye sockets in the
  face mesh. pl1 draws its mouth on the skin; filie's mouth is loose pieces in the middle of the face.

## Part A: Fill Empty Expressions

A button in Shape Keys › Expression Sets. On the active mesh, an expression key that moves nothing, or less than 15% of
the median largest move of the mesh's expressions, is built from keys that move:

- the same expression under another usual name: VRM 0.x / VRM 1.0 / VRoid / ARKit ("happy" from "joy", "a" from
  "aa" or "jawOpen");
- "e" = 0.5 "a" + 0.5 "i";
- a blink side from the blink (its half, blended across the middle as Split Left / Right does); the blink from both
  sides;
- the upper lip ("mouthUpperUp") from the vertices "i" moves up (else "e", else "a"); the lower lip from the vertices
  "a" moves down; their Left/Right from them.

"neutral" stays empty (VRM's rest face). Keys that move are never changed. The report names each key filled and how.
On tdt: "e" becomes a half-open mouth between "a" and "i"; "mouthUpperUp" comes out small (tdt's "i" barely lifts the
lip).

## Part B: Sculpt Eye Expressions

A button in Shape Keys › Expression Sets, for a character with a DaskToon rig (Head bone). It finds each eye as the
loose pieces in front of the head: in the head's frame (centre of the Head bone, its length as the unit, the character
facing -Y), a piece whose centre is in front (y < -0.15), to the side (0.06 < |x| < 0.5), at eye height
(-0.5 < z < 0.2), smaller than 0.45 across and of 3 vertices or more; the pieces on one side make that eye. Both
eyes are needed. Hair parts are left out (a lock of filie's hair hangs in front of an eye). A face with an eye socket
(open edges of another piece all around an eye, leaving no gap wider than 1.5 radians) is left alone: closing a
socket needs its lids moved, which this does not do. The edge of the hair along the forehead crosses the eyes (pl1)
but does not go around them, so it is no socket.

For each eye, the close line is a third of the way up from its lowest point. Eye whites painted on the face (pl1) or
a face layer behind an eye (RGforGame) would stay open, so the skin under each eye moves with it: the vertices of the
Body parts' meshes in front of the head inside the eye's outline move as the eye does, fading back to rest 30% of the
eye's size out of it. Hair and clothes never move. Keys, on each mesh holding eye pieces or skin under them:

- blink: every vertex of the eye goes to the close line, keeping 4% of its height (the lashes meet in a line);
- blink_L, blink_R: one eye (the character's left at +X);
- joy: closed as an arc, its middle raised by 35% of the eye's height (the "^^" of a smiling anime face);
- surprised: the eye 12% bigger about its centre.

A mouth drawn on the face makes joy smile: the Body's face texture is read through its UVs below the eyes, on the
mesh as shown with the rig at rest (pl1's Subdivision moves the drawing away from where its cage puts it), keeping only
what shows from the front (pl1 has a pink inside of the mouth behind its face); the largest patch unlike the skin near
the middle that is a wide line is the mouth, and the skin at its corners lifts by 18% of its width (nothing in the
middle). On pl1 it finds the 0.13-wide line and smiles; filie's materials have no image, so no mouth is read. An open
mouth ("a") is not made: stretching a drawn line hides it rather than opening it (tried on pl1).

A key of the same expression that already moves is left alone; an empty one is filled; a missing one is added under its
VRM 0.x name. The report names the keys made and the meshes.

## On the user's characters (copies, 2026-10-20)

- filie: both eyes found (eye "mat" and lashes "mi"); closed, the eyes leave the lash line on her skin; joy arcs;
  surprised widens. Works.
- pl1: both eyes found (three pieces each in the body mesh). With the pieces alone, the eye whites painted on the face
  stayed open; with the skin under the eyes moving too, both eyes close to clean lines, joy shows "^^".
- RGforGame: both eyes found; with the pieces alone one eye showed a white face layer behind; with the skin moving it
  closes to a line too.

## Rulings (autonomous)

1. Eyes, plus a smile for joy when the mouth is drawn on the face: the user's three characters without keys show no
   mouth geometry to open (pl1 draws it, filie's is small cards), and stretching a drawn line hid it. DaskToon's 2D
   mouth (atlas) covers A I U E O for drawn mouths. Cost if wrong: mouth shapes still to make by hand.
2. Squashing the eye pieces and the skin under them to a line, not moving lids: these characters have no lids to
   move. Cost if wrong: the face around a closed eye is slightly flattened (seen in plain studio light, not in toon
   shading); a model whose iris shows above the lash line keeps a sliver of it.
3. Fill treats "barely moves" (under 15% of the usual) as empty, because tdt's "e" is not zero but useless. Cost if
   wrong: a deliberately subtle key gets replaced; the button is undoable and the report says which.
4. Both parts are buttons, not run by the auto rig: they change the user's expression keys, which should be asked for.
