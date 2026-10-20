# Game Texture Sets (part 1) Implementation Plan

**Goal:** docs/superpowers/specs/2026-10-20-dasktoon-game-texture-sets-design.md.

**Architecture:** `dasktoon_uv/sets.py` (the set of every face, the face material split, upright islands, sizes by
density, the colour atlas of each set); `unwrap.unwrap(..., sets=True)` packs per set instead of per material;
`dasktoon_uv` operator gets the Pictures choice.

## Tasks

1. sets.py: face sets, upright rotation, density sizes; unwrap packs per set; tests on the regions chibi with a hair lock.
2. Colour atlas per set and the Base Color links, the face material split; transfer skips the set images; tests.
3. Operator choice, translations, real models looked at, report, suite, push.
