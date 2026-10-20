# Anime Unwrap Implementation Plan

**Goal:** docs/superpowers/specs/2026-10-20-dasktoon-anime-unwrap-design.md.

**Architecture:** `scripts/modules/dasktoon_uv/` (seams.py: face labels from the rig's regions and loose parts, seams
between labels and hidden-side cut paths; unwrap.py: SLIM unwrap, island scale by importance, mirrored limbs, packing
per material; transfer.py: old pictures to the new UV map), the operator in `scripts/startup/bl_ui/dasktoon_uv.py`.

## Tasks

1. seams.py + unwrap.py (labels, seams, unwrap, head ×1.5, mirror, pack); tests `dasktoon_uv_unwrap_test` on the
   regions chibi.
2. transfer.py (pictures and their layers to the new UV map); tests.
3. Operator, menus, Start Painting and the Guide's UV fix use it; translations; real models; real-window shots;
   report; suite; push.
