# Paint Layers Implementation Plan

**Goal:** docs/superpowers/specs/2026-10-20-dasktoon-paint-layers-design.md: layers inside the image, Start Painting,
anime brushes and Fill Part.

**Architecture:** Python owns the layer data (`Image.dasktoon_layers`, `Image.dasktoon_layer_index` in system
properties) and the UI (`scripts/modules/dasktoon_paint/`, `scripts/startup/bl_ui/dasktoon_paint.py`); C++
(`editors/sculpt_paint/mesh/paint_image_layers.cc`) reads it to send strokes to the active layer, composites the painted
region after each step and after undo, and offers `paint.dasktoon_layers_composite` so there is one compositing code.

**Spec:** docs/superpowers/specs/2026-10-20-dasktoon-paint-layers-design.md

## Global Constraints

- Every visible string translated (Vietnamese in dasktoon_translations.py, the "DaskToon" context where Blender's own
  Vietnamese has the word); no "\\u" escapes; lines at most 120 columns.
- No DaskToon panel class in a sidebar (the UI layout test); layer UI is drawn into Blender's Texture Slots and Image
  panels.
- Build with the VS 2026 tree (`cmake --build D:/build_windows_x64_vc18_Release --config Release --target install`);
  tests with rt.sh; new modules listed in the translations test; tests registered in tests/python/CMakeLists.txt.

## Tasks

1. C++ core: `paint_image_layers.cc` (read layers, paint target, composite region/full, owners of a layer, refresh all,
   the composite operator), hooks in the four places that pick the pixels, `imapaint_image_update`, image undo;
   Add Texture Paint Slot connects to the anime shader. Build.
2. Python layers: property groups, `dasktoon_paint.layers` (add, duplicate, remove, move, merge down, flatten),
   property updates composite, the layer list drawn into Texture Slots and the Image panel; tests
   `dasktoon_paint_layers_test` (compositing per blend mode, opacity, hidden, first layer keeps the picture, merge,
   flatten, Add Texture Paint Slot on the anime shader).
3. Start Painting, saving painted images with the file, the anime brushes, Fill Part tool; tests in the same file.
4. Window test (strokes in 3D and 2D go to the active layer, undo), real-window screenshots (vi), Guide page mention,
   report, full suite, push.
