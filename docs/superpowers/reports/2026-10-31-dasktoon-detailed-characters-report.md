# Detailed characters: the auto rig, accessories and Auto Expressions

Date: 2026-10-31. Specs: 2026-10-30-dasktoon-accessories-design.md, 2026-10-20-dasktoon-auto-expressions-design.md part C.

The user tried detailed models from games and found the auto roles and shoulders poor, wanted a group for accessories, found
Auto Expressions hard to follow, and saw a blink go the wrong way. Their ruling on method: a model only shows what is wrong
with a feature, so each finding below names the general kind of input, says why the old tests passed, and has a harder
test on a synthetic character with no name or number of the model. The fixes were then checked on eight characters that
had no part in finding them.

## What was wrong, and why the tests passed

| What showed | The kind of input | Why the tests passed | The harder test |
|---|---|---|---|
| Blink went the wrong way | Eyes set behind the face in holes, brows above them | Fixtures had four clean pieces in front, no brows, no holes | `EyesInHolesTest`, `OffCentreTest` |
| Blink turned the eye upside down in the previews | An expression with several keys (blink and its sides, joy and happy, joy and the ARKit shapes) adds up when all are on | The previews were tested with one key at a time | `ShownOnceTest` |
| A face changed by itself | New keys start at 1 in Blender | Only Sculpt and Fill were checked for it | `KeysStartOffTest`, over every tool |
| An expression showed nothing, or half | Eyes, skin and mouth are meshes of their own; the tools worked on the active mesh | Fixtures keep one mesh's keys | `WholeCharacterTest` |
| Keys of an older version stayed wrong | Keys that move are kept | No test asked for them to be replaced | `RedoTest` |
| One surface read as many pieces, arms came away at the shoulder | Vertices doubled along texture seams | No fixture had coincident vertices | `SeamTest`, `SeamsChangeNothingTest` |
| Crystals became the arms, shoulders level with the eyes | Big ornaments far from the body | No wide ornaments in any fixture | `FarOrnamentTest` |
| Arms hidden under a cloak | A wide cloak hides the arms in the silhouette | No fixture hid the arms | `HiddenArmsTest` |
| Most meshes Clothing, each loose bit a lock | Names in Chinese, brows and blush as meshes of their own | Latin names, few locks | `NameTest`, `HeadPartsTest`, `HairTest` |
| Legs stopped at the knee (found by the held-out run) | Skin only where it shows: socks and shoes below it | Every fixture had skin down to the floor, under its boots | `SkinOnlyWhereItShowsTest` |
| Shoulders rose to the temple (held-out run) | A Body mesh of head and hair, with no arm in it | Every Body had arms | `test_a_lock_of_hair_in_the_skin_is_no_arm` |
| Arms raised met over the head (seen in a render) | A trunk as narrow as a wide sleeve: the walk from the hand went on through it | Every fixture's trunk was too wide for this | `test_a_slim_trunk_keeps_its_shoulders_at_its_sides` |
| Arms left behind, stretched from hip to hand (seen in a render of the skin alone) | A wide cloak widens the trunk as the front view reads it, and the trunk takes in the arms | Every fixture's clothes followed the body's width | `WideClothesTest` |
| A bust squeezed (held-out run, by the rule above) | No arm to read: the shoulders are only the template's | No fixture without arms | `NoArmsTest` |
| A strap rose with the arm (old test, once the shoulders widened) | The shoulder bone's zone went by plain distance, past pieces apart | The old shoulders were short enough | `test_lifting_an_arm_leaves_the_ears_locks_and_straps`, kept as it was |
| The neck sank and the whole body leaned 8 degrees (Unity bend fix test, by the shoulder rule) | A shoulder moved out along a sloping arm comes lower, and the neck goes by that height | No test looked at the body's frame | `test_the_body_stands_straight` |
| The top of the thigh stayed behind, a flap of skin below the hip (a render, once the user asked about the legs) | Hips wide next to the thigh: the trunk's round end hung over it | Fixture hips were narrow | `WideHipsTest` |
| Shorts followed a skirt and not the thighs (leg weights, measured then) | Two parts named in Chinese both came to bones named "Part", and the first's passed for bones of the body | Only one part with a name not in Latin letters | `NamesInOtherScriptsTest` |
| The outfit taken for the Body (seen in a real window's log) | Plain names, an outfit taller than skin that stops at the knee | Skin down to the floor again | `test_with_plain_names_the_body_reaches_the_head` |
| A head of its own taken for the Body (held-out run, by the rule above) | The Body stops at the neck, under a head mesh | Skin in one piece, head included | `test_with_plain_names_a_head_of_its_own_is_not_the_body` |
| Expressions were not looked at on the real faces until the user asked: a whole strip of an eye, a closed eye still open at its ends | Lashes in many small bits; a strand or an ear beside the eye; whites reaching far past a hole | Every fixture had four clean pieces and nothing beside them | `ManyLittlePiecesTest`, `WhatLiesBesideTheEyeTest`, `SeenThroughAHoleTest` |
| A wink closed both eyes, or one key undid the other | A mesh modelled in half with a Mirror modifier | Every fixture modelled both sides | `HalfModelledTest`, `HalfModelledAutoTest` |
| A character stayed backwards and rigged wrong (held-out run) | A wide round stand under the feet: its edge read as the floor | Every fixture stood on its own feet | `test_a_stand_under_the_feet_is_no_floor` |
| A face stayed in an expression after the button | Keys left on, from the user's trying them | Every fixture started at rest | `LeftOnTest` |
| "lông mi đâu": closed eyes had no lash | Every piece was squashed to 4% of its height, a thin lash with them | The test measured how flat the eye was, nothing about what stayed | `ClosedEyeTest` |
| A band of iris along the closed eye (close-up renders) | The white and the iris kept as thick as the line, round any thinner lash; which piece is a lash cannot be told by its outline | Same | `test_the_white_and_the_iris_come_to_nothing`, `ALashOfAnyShapeTest` |
| Painted whites open at both ends (close-up renders) | Lashes wider than the iris, the white painted past it | The eye was the band of most pieces, and the fixture's white was a piece | `test_the_eye_is_as_wide_as_its_lashes` |
| The eye twice too tall, the close line below it | A ball in a dent, most of it under the skin | No fixture had skin in front of any piece | `BehindTheSkinTest` |
| Joy lifted the chest round a brooch (a render) | A Head bone long against the face: how far below the eyes a mouth may be went by that bone | Fixture bones are all of a length with the face | `WhereAMouthLiesTest` |
| Joy dented the jaw (a close-up of the mouth) | Every loose piece near the middle made one mouth, the collar with the teeth | No fixture had pieces in two rows, or lips at all | `test_joy_smiles_at_the_slit_whatever_lies_below`, `PiecesOfAMouthTest` |
| No A I U E O on a mouth that opens | A slit in the skin with teeth, tongue and the inside of a mouth behind | The spec ruled no key can open a mouth, on the characters of that day | `dasktoon_expressions_mouth_test.py` |
| Lip Sync moved the lips and not the teeth | Teeth a mesh of their own | The test character was one mesh | `test_every_mesh_of_the_character_talks` |
| A crash on one character | Adding a part moves the list in memory; a part held from before it is gone | One part added at a time | `test_many_meshes_each_with_something_standing_off`. This test did not fail on the old code: where the list lands is luck. The proof is the crash gone |

All of it together: `tests/python/dasktoon_detailed_character_test.py`, one character with everything above under names that
say nothing, through Anime Humanoid and Auto Expressions, and a check that cutting its surfaces along seams changes neither
the skeleton nor the parts.

## Results

Auto rig on copies, old code (the last commit before this work) against new. "Spots" is what the Check lists. "Torn" counts
edges torn open, by tools/dasktoon_rig_accuracy.py. Fewer parts is not better in itself: the accessories are grouped.

The three characters that showed the bugs:

| | Parts | Bones | Spots | Torn: arms up | sit | wave |
|---|---|---|---|---|---|---|
| Encore | 59 > 38 | 126 > 119 | 9 > 1 | 64 > 4 | 185 > 36 | 10 > 32 |
| Evita | 8 > 15 | 546 > 206 | 16 > 12 | 310 > 1805 | 531 > 351 | 155 > 862 |
| Violet | 16 > 13 | 170 > 114 | 32 > 11 | 672 > 548 | 1063 > 152 | 0 > 200 |

Old and new tear counts of Evita and Violet do not compare in the poses that move the arms. Their old rigs had 10 and 13
joints outside the body, and in the old renders the arms did not follow; an arm that stays where it is tears nothing. New
joint spots: Evita 2, Violet 5. Encore's one spot is a suggestion that a mesh may be Hair. Encore's sitting pose stretches
more edges than before (483 > 1074) and tears fewer; its worst opening is 4 cm on a character 1.5 tall.

The eight that had no part in finding the bugs:

| | Spots | Torn: arms up | wave | sit | Joints outside the body |
|---|---|---|---|---|---|
| tdt | 0 > 0 | 7 > 6 | 1 > 2 | 0 > 6 | 0 > 0 |
| lr_shape | 2 > 1 | 30 > 30 | 11 > 11 | 25 > 3 | 1 > 1 |
| pl1 | 8 > 5 | 367 > 100 | 145 > 37 | 68 > 40 | 0 > 0 |
| RGforGame | 5 > 3 | 72 > 13 | 30 > 8 | 0 > 0 | 0 > 0 |
| RG2 | 4 > 6 | 159 > 90 | 77 > 46 | 0 > 0 | 0 > 0 |
| adl | 13 > 5 | 1 > 30 | 0 > 15 | 96 > 11 | 1 > 4 |
| filie | 3 > 1 | 226 > 89 | 108 > 43 | 106 > 48 | 2 > 0 |
| Luna | 5 > 3 | 279 > 255 | 124 > 125 | 62 > 26 | 0 > 0 |

Two rules did most of it. An arm starting at the side of the trunk cut tears with the arms up by 12% to 82% on the five
characters whose shoulders lay inside the chest. The trunk no longer hanging below the hips cut tears sitting on every
character that had any but tdt (0 > 6). All eleven were looked at sitting and three with the arms up: Encore's arms, which met
over the head with the rule missing, rise beside it; Evita's, which stretched from hip to hand, rise whole; Violet's flap of
skin below the hip is gone. The legs were looked at only after the user asked: the counts had looked mixed, and the tests had
no leg like these.

Measuring old against new on held-out characters, and looking at renders, is what found most of the late bugs, all of them
in rules of this work or brought to light by them: socks and shoes taken for accessories, hair taken for an arm, a Body rule
that lost a character its skirt, a trunk rule that hurt a bust, a shoulder rule that sank the neck. The counts alone hid the
worst: arms left behind on Evita, shoulders inside the chest on Encore, thighs left behind on Violet. Originals are unchanged
(md5 of all ten files compared).

The panels were looked at in a real window (tools/dasktoon_auto_expressions_screenshots.py): that found a hint cut short and
a car for an icon, and its log showed the outfit taken for the Body.

Auto Expressions on the ten characters with eyes, up close, open, blink and joy. Three (tdt, lr_shape, Violet) have keys of
their own and are left to them. Encore needs Redo Eye Expressions, its keys being old. Every closed eye keeps its lash and
shows no white. adl is a bust with no loose eyes: blink, joy and surprised from its keys, nothing sculpted.

One rule was tried and dropped: an eye with a white of its own leaves the skin alone. It looked right on the piece tables and
left Evita's eye open and a grey patch on filie, whose eyes are drawn on the skin behind what looked like a white. Tapering
the skin toward the corners of the eye was dropped too: the whites came back at both ends on pl1, RG2 and Luna.

A I U E O (spec part D): Encore, Evita and Violet have a slit and get all five; looked at up close, each vowel. The other
eight have none: pl1, RGforGame, RG2, filie and Luna have nothing to open, tdt, lr_shape and adl were not changed.
Joy on Evita no longer touches the jaw; its smile is slight, its lips thick.

## What the checks do not settle

- The vowels were seen only on the three characters that showed the need: no held-out character has a slit, so this rule has
  not been shown on one that played no part in it. The numbers in spec part D were set by eye on those three, in a plain
  render, not in motion or through Lip Sync on a real voice.
- Pursed lips (U, O) leave a small lump at each end on Encore and a thin line past the lips on Violet.
- Evita's open mouth shows pale teeth at each corner, what the model holds there (rays through the corners hit its own
  pieces, not what lies behind the head).
- Closing an eye drawn on the skin stretches what is drawn round it. On Evita the shadow painted round the eyes spreads to a
  darker band from the brows to the lashes, cut off by the hair at the sides. The lash line and the place of the close are
  right; a clean lid would take a painted one. RGforGame and RG2 smear their brows the same way on a coarse mesh.
- filie keeps a thin grey line above the closed eye, the top of what her skin paints behind the iris: the iris goes under
  the skin there, so the eye counts up to where it shows.
- Encore shows two small dark bits on the closed lash: pieces as thin as the lash, that lie inside the eye at rest. Whatever
  is thin and off the eye's middle stays.
- Luna's stand (the mesh Cube.001) is still a Clothing part.
- Evita's cloak tears when her arms go up (worst edge 4.7 units on a character 11.65 tall), and her body at the shoulder 0.39.
  The cloak is one Clothing part hanging across arms and trunk. The tear counts in the table are mostly this. Her two
  remaining joint spots are at the shins, under the cloak.
- Violet's two long coat tails are in one piece with its arms, in its Body mesh, so raising the arms pulls them up (worst
  edge 6.6 units on a character 14.5 tall), and sitting drags them (4.1). The Check lists it, and painting them as trunk is a
  way out now; cloth like this wants chains of its own.
- Violet's five joint spots (upper arms, forearms, head) were not looked into.
- RG2 lists more spots (4 > 6) though it tears less; they were not looked at one by one. The Check counts spots, not how far
  they open.
- adl is a bust with no arm to read, so the shoulder rules play no part in it. It tears more with the arms up and far less
  sitting; its accessories went from 55 to 94 parts.
- tdt sitting tears a little more (0 > 6), with far fewer stretched edges (262 > 114).
- `_run_half` reads one row: on very coarse meshes the silhouette has holes and a trunk can read too thin (seen on a test bust,
  not on a real character).
- Encore's Head bone is 1.2 cm off the middle of her face: the eyes are found across it, the bone itself is not moved.
- A I U E O are not made on a mouth without a slit: the list says so and points to the 2D Mouth.
- Clothing across two objects (a sleeve mesh and a shirt mesh) has no shoulder carry between the objects; whether it matters
  was not measured.
- `test_many_meshes_each_with_something_standing_off` did not fail on the old code (see the table).
- `test_the_rig_fix_is_the_auto_rig` no longer asks for a warning on the test character's elbows: it stood on an elbow falling
  on one ring of vertices, and the elbow moved with the shoulder. `test_joints_without_blended_vertices` holds the warning.
