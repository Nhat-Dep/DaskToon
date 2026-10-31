# Accessories: a group of their own, and characters with many details

Date: 2026-10-30. The user tried the auto rig on three detailed models from games and found the roles and the shoulders
poor, and asked for a separate group for accessories. Their ruling on method (saved as a rule): a model only shows what is
wrong with a feature. The fix is general, the old tests are asked why they missed it, a harder test goes in, and the
result is checked on models that had no part in the fix (see the report of 2026-10-31).

## What an accessory is

What a character wears or carries that does not bend with the skin under it: a bow, a bag, a brow, crystals round a cloak.
An accessory is rigid on one bone. It is listed in the **Accessories** panel under Anime Rig, apart from Parts, which
shows everything else. The panel has **Find Accessories**, which finds them again, then builds the rig and checks it.

## What makes a detailed character hard

1. **Seams.** A model from a game has its vertices doubled along the texture seams: one surface in pieces that only touch.
   Reading them as loose pieces breaks every test built on "one piece". `parts.welded_arrays` gives the vertices and the
   edges with coincident vertices (within `WELD` = 0.2 mm) joined, for the piece tests, for the regions and for the hair
   chains. `build._seams` averages the weights of coincident vertices of a part, so a seam never opens when posed.
2. **Skin only where it shows.** Under socks, shoes and sleeves there is often no skin at all. Being far from the skin
   therefore says nothing by itself.
3. **Parts as pieces of one mesh.** A cloak holds crystals, a shirt holds studs. What a mesh keeps of its Clothing stays;
   the rest becomes a part of its own on the vertex group `DT_Accessories`, or the whole part an Accessory when nothing
   stays.
4. **Names that say nothing**, or in Chinese or Japanese. `parts.MARKS` adds the usual words of both to the word list; the
   shape tests below do not use names at all. No word is added for one model: a word goes in only if it is the ordinary
   word for the thing. Among plain names the tallest mesh is the Body, of two about as tall (`ABOUT_AS_TALL`, 10%) the one
   reaching higher: skin may stop at the knee above an outfit down to the floor. Asking the Body to reach the head instead
   took a head of its own for the Body, on two characters.

## How they are found

**Before the fit** (`accessories.find_far`): a piece of Clothing is off the body when all of these hold:

- it reaches more than `FAR_REACH` (0.12 x height) out of the skin **seen from above**. Shoes and socks are far from any
  skin but lie under the legs, so only the sideways reach counts;
- it goes less than `ROUND_THE_BODY` (1.5 pi) round the body: a wide skirt goes round it;
- no vertex of it lies within `TOUCHES` (0.01 x height) of the skin: a sleeve touches its hand, a cloak its neck.

Size is no test: a crystal may be as long as the character is tall (Evita's are). These pieces are kept out of the
skeleton's fit: read as part of the body's shape they become its arms.

**After the fit** (`accessories.find`): a mesh lying wholly on the head goes with the head, if it is Clothing or a small
Body in small pieces. A piece of Clothing no longer than `COMPACT` (0.22 x height) whose vertices stand off the surfaces
round it by `STANDS_OFF` (0.012 x height), and which does not go `ROUND_A_BONE` (1.3 pi) round its nearest bone (a cuff, a
belt, a shoe), is an accessory.

## Which bone

The part's **Bone** if you set one. Otherwise each group of touching pieces takes (`accessories.bone_for`) the limb on whose
surface it sits, a ring taking the hand and not a finger; the Head when it sits on the head; else the nearest bone of the
trunk and shoulders. A crystal floating by the shoulder does not swing with the arm.

## The shoulders

Two rules joined the fit of the arms (`body_shape._arms`):

- What is worn hides an arm, it does not move it: where the arm of the silhouette and the arm of the skin disagree by more
  than 20 degrees, the skin is right. But only if the skin's arm is `ARM_SKIN` (0.2 x height) long or more: real arms were
  0.27 to 0.33 on eleven characters, the false one (a lock of hair at the temple, in a Body mesh with no arm in it) 0.09.
- An arm starts at the side of the trunk at least (`_off_the_trunk`). Walking in from the hand, a trunk as narrow as a wide
  sleeve was passed through as if it were one, which left the shoulder inside the chest, and arms raised met over the
  head. Going down the `ARM_TRUNK` (0.15 x height) of rows below the shoulder, the silhouette widens along the arm, then
  falls back to the trunk at the armpit: the trunk is the lower quartile of the rows after the widest (a stray hole in the
  silhouette narrows a row, the hips widen the last), if it is at most `ARM_FALLS` (0.7) of the widest. A shoulder inside it
  moves out along the arm, by `ARM_SLIDE` (0.3 of the arm) at most. On the ten characters with arms to read the fall was 0.34 to 0.65.

And one to the regions (`regions.half_widths`): a trunk read more than `TRUNK_WIDE` (1.5) times the shoulders' distance from
the middle is what is worn on it. A wide cloak read as trunk took in the arms: the arm bones rose and the arms stayed behind,
stretched from hip to hand. Such a trunk is read from the Body meshes where they have it, else held at that width. With no
arm found anywhere the shoulders are only the template's and say nothing, so the rule stands aside (a bust in a coat).

The height of the shoulders is read before a shoulder moves out: along a sloping arm it comes lower, and the neck, which goes
by that height, sank with it and leaned the whole body's frame by 8 degrees.

With wider shoulders the shoulder bone's zone, which goes by its length, reached a strap on the chest. It now leaves a piece
apart alone, as the limbs always did.

## The legs

The same fault as a cloak's, at the other end of the trunk (`regions.trunk_distance`): the round end of the trunk hung below
the hips. Hips wide next to the thigh (0.19 of the height across a thigh of 0.26) took the top of the thigh and what is worn on
it, which stayed behind when the leg rose: a flap of skin below the hip, and shorts with no leg bone at all. The trunk now
narrows below the root of the Hips to nothing one half width down, as the head does below its root.

Bone names are ASCII, and a name in Chinese or Japanese has none: every such part came to "Part". Two skirts so named made
bones of one name, and the first's then passed for bones of the body. Each part now has a start of its own (`_Plan.base`).

## Other changes it brought

- A hair piece shorter than `SHORT_LOCK` (0.05 x height) gets no chain: rigid on the Head. The bones of one character fell
  from 546 to 206.
- The Check reads hair as reaching mid-Head, not only past the head joint: a shirt whose collar stands just past the neck
  was offered to become Hair.

## Rulings (autonomous)

1. Accessories found by shape are marked by Anime Humanoid, not only by the button: without them the skeleton is wrong
   before anyone can look. Cost if wrong: a piece is rigid that should bend; change its role in the list.
2. `TOUCHES` makes a cloak resting on the neck stay Clothing, however wide. Its arms come from the skin by the first rule
   of the shoulders. Cost if wrong: a wide cloak over a character with no arm skin still misleads the fit.
3. Pieces marked by shape go on the vertex group `DT_Accessories`, so a mesh is not split. Cost if wrong: a hand-made group
   of that name is replaced.
