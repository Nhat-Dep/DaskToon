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

- blink: a closed eye is its lash. A lash comes whole to the close line, no thicker than `LINE` (15% of the eye's height).
  What lies over the eye's middle, up, at its own middle across (the white, the iris) comes to `KEEP` (4%) behind it. Where
  every piece lies over the middle, the front one stays `LINE` thick: the lash is drawn on it. The skin goes to the line,
  keeping 4% of its height;
- blink_L, blink_R: one eye (the character's left at +X);
- joy: closed as an arc, its middle raised by 35% of the eye's height (the "^^" of a smiling anime face);
- surprised: the eye 12% bigger about its centre.

A mouth drawn on the face makes joy smile: the Body's face texture is read through its UVs below the eyes, on the
mesh as shown with the rig at rest (pl1's Subdivision moves the drawing away from where its cage puts it), keeping only
what shows from the front (pl1 has a pink inside of the mouth behind its face); the largest patch unlike the skin near
the middle that is a wide line is the mouth, and the skin at its corners lifts by 18% of its width (nothing in the
middle). On pl1 it finds the 0.13-wide line and smiles; filie's materials have no image, so no mouth is read. An open
mouth ("a") is not made: stretching a drawn line hides it rather than opening it (tried on pl1).

A face without a drawing may hold its mouth as loose pieces in the middle below the eyes: filie's face is closed, its
mouth a crease, with plates inside it (two loose pieces of the body, and a cavity). No shape key can open a closed face,
so there is no "a" there either; the plates' outline gives the mouth for the smile (2026-10-20, morning: the user asked
for A I U E O on "a model with mouth pieces", and none of the user's characters has an openable one).

A key of the same expression that already moves is left alone; an empty one is filled; a missing one is added under its
VRM 0.x name. The report names the keys made and the meshes.

## Part C: Auto Expressions (2026-10-31)

The user found the two buttons hard to follow, and on a detailed character a blink that did the opposite. One button now
does the work, for the whole character:

- **Auto Expressions** (`auto_expressions.run`): fill, sculpt what is still missing, fill again. A blink made by hand stays
  and gets its two sides from it; a key under another name (happy) comes from what was sculpted (joy). An expression moving
  on any mesh of the character is left to that key: the skin closing over the eyes by a key of its own would close them
  twice. Every mesh of the rig is included; a mesh without a rig is on its own and can only be filled.
- **A list** of 13 expressions (blink, its sides, joy, angry, sorrow, relaxed, surprised, A I U E O): ticked if a key moves
  on some mesh, greyed if not. Pressing one shows it on every mesh with the other expressions off. **Back to Rest Face**
  turns them off. Keys that are no expression (a slimmer waist) keep their value; the two previews and their Clear Values
  now work the same way, on the whole character, since the eyes are often a mesh of their own.
- **Redo Eye Expressions** writes the eye keys again from the eyes found now, after asking. Keys that move are kept by
  everything else, so a key from an older version stays until this button is pressed.

The panel comes first under Shape Keys, open, without needing a shape key, and the same buttons are in **Expressions** in
the Anime Rig panel, since after Anime Humanoid the rig is the active object. Sculpt and Fill stay as tools of their own
under Expression Tools. The Model Guide's fix and its checks use Auto Expressions.

Every new shape key starts off: Blender starts one at 1, and VRM Set, ARKit Placeholders, Split, Bake and Synthesize left
theirs on (only Sculpt and Fill were tested for it).

Eyes set in holes (Part B's socket rule, changed 2026-10-30): the eye was looked for no deeper than a fixed distance from
the head's centre, which dropped the real eye pieces of a character with eyes set behind the face and kept the brows and a
few lashes, so that the line a blink closes onto fell between them, and the blink went the wrong way. Now the front of the
face is found first and the eye may lie `DEEP` (0.25 head) behind it. Each eye is the band of height most pieces share, a
piece counting when at least half inside it (brows are left out), and mirror twins find the middle of a face off the Head
bone. Open edges of a **Body** part all round an eye are the eye's own outline, and the skin round them closes with it; open
edges in any other mesh still mean a socket, left alone.

Finding the eye, as changed 2026-10-31 on ten characters. Where most pieces lie is found first, and only pieces as deep as
that place (`AS_DEEP`) count: an ear joined to the face lies behind. Then the band up, wide enough at each height whatever
number of pieces makes the width (many bits of lash are no wider than one), then across among those in that band: a strand
beside the eye runs up past it. A ring of open edges of a Body round that place, as deep, is a hole, and the hole is the
eye: whites may reach far past it under the skin. The eye goes as far across as its pieces, not the band: the white painted
past an iris stayed open at both ends. A piece counts up as far as it shows (`SPOTS`, `UNDER`): a ball in a dent, most of it
under the skin, made the eye twice as tall as the opening. A Mirror modifier makes the other eye: its pieces are their own
twins, and that mesh gets no key of one side (the modifier would copy it).

A mouth, drawn or of pieces, lies at most `MOUTH` (one distance between the eyes) below them. Every real mouth lay 0.23 to
0.86 of that below; a brooch and necklaces 1.01 and more. The limit went by the Head bone's length before, and that bone
may be anything against the face.

## Part D: A I U E O for a mouth that opens (2026-11-02)

Part B said no key can open a mouth: true of a drawn line and a closed face. Three of the user's characters from games have
a mouth that opens all the same: a thin ring of open edges in the skin, teeth, tongue and the inside of the mouth behind it.

- **The slit** (`eye_shapes.lips`): a ring of open edges on the main piece of a Body, where a mouth lies, at least 0.05 head
  wide and no taller than `THIN` (a quarter) of its width. A ring round a loose piece is not it: teeth have rings too. It is
  the surest mouth there is, so joy reads it first, before a drawing or pieces.
- **The vowels** (`mouth_shapes.sculpt`, from Auto Expressions): keys a, i, u, e, o on the skin and on what moves behind it.

| | Upper lip rises | Lower lip falls | Width |
|---|---|---|---|
| a | 0.2 | 1.1 | 1 |
| i | 0.06 | 0.18 | 1.12 |
| u | 0.15 | 0.26 | 0.72 |
| e | 0.12 | 0.45 | 1.06 |
| o | 0.3 | 0.7 | 0.78 |

in half widths of the mouth. The lips part as an ellipse, not at all at the corners. The skin goes with them, fading out
0.7 half widths above and 1.4 below; narrowing or widening fades the same way, and out to 1.6 half widths to the side.

- **What lies behind**: pieces within `NEAR` (six half widths) behind the lips, and no bigger. The tallest (half as tall as
  the tallest or more) are the inside of the mouth and stay. The lips part no further than 90% of the way to its edge, up and
  down, and no wider than it reaches across: past that an open mouth looks through the head. Nothing behind the slit, no
  vowels. Other pieces narrow with the lips (never widen): a line of the mouth may be a piece of its own. Those below the slit
  go down 70% as far as the lower lip and never past it.
- A vowel that moves is kept, an empty one filled, a missing one added under its VRM 0.x name. Redo Eye Expressions leaves
  them: its name says eyes.
- Lip Sync keys the vowels on every mesh of the character: teeth may be a mesh of their own.
- **No darkening inside** (2026-11-03): the anime shader darkens what is closed in (AO), and the inside of a mouth is the most
  closed-in place of a character. Encore's, red in its picture, opened black. What lies behind the lips gets a copy of its
  material named `<material>.Mouth` with AO off, in a slot of its own where it shares a mesh with the skin; the skin keeps
  its material. Only where AO is on, and only on the anime shader; a second press changes nothing. It comes with a slit,
  whoever made the vowels. Shortening AO Distance does not do: at 0.03 on a character 1.5 tall the mouth is still black.

A mouth without a slit gets none: a 2D Mouth, or keys by hand.

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
