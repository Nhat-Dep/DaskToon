# Godot Export Implementation Plan

**Goal:** docs/superpowers/specs/2026-10-20-dasktoon-godot-export-design.md.

**Architecture:** `scripts/modules/dasktoon_export/godot/` (target, glb, materials as .tres, shader and script files
copied from `godot/files/`), dispatched from `export_model` when the engine is GODOT_4; tests drive a temporary Godot
project with the installed Godot (headless import + a GDScript check), like the Unity harness.

## Tasks

1. Wave 1: target (project.godot), glb, textures, Anime BSDF + outline shaders, materials, import script; harness and
   tests `dasktoon_godot_export_test`; a window shot in Godot.
2. Wave 2: Anime Cel, eye, Dask Cel shaders; rig, clips (stepped), expressions.
3. Wave 3: springs, bend fixes, eyes (look at, flat eye), 2D mouth.
4. Wave 4: real models, shots, report.
