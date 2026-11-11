# DaskToon: the .dlive export and import (DaskToon side)

Format: `D:/DaskLive/docs/dlive-format.md` (authoritative). App design: `D:/DaskLive/docs/specs/2026-11-10-dasklive-design.md`,
section 3. This note says how DaskToon writes and reads the file. A `.dlive` is the Godot export
(`2026-10-20-dasktoon-godot-export-design.md`) packed into one ZIP.

## Export: `dasktoon_dlive.export(context, filepath, objects, options) -> Report`

File > Export > DaskLive (.dlive). Options: Make Expressions (on), Max Texture Size (2048), Thumbnail (on), Selected
Objects Only.

1. With Make Expressions on, `copies.temporary` swaps each mesh for a copy (the original waits under another name, the
   copy takes its name, same collections, same armature). The rig's parts point at the copies meanwhile, because Auto
   Expressions finds eyes, hair and body by those pointers. Afterwards copies, meshes and shape keys are removed, names
   and pointers restored: the file has the same data-block counts and no new shape keys.
2. On the copies: `auto_expressions.run` (sculpts blink/eye/mouth keys, fills empty ones), then
   `synthesize_arkit52` (the ARKit 52 from VRM; now a numpy function in `bl_ui/dasktoon_shape_key_manager.py`, the
   operator calls it).
3. `dasktoon_export.godot.export_model` runs into a temporary folder (so the model, face-shading rest normals, mesh merge,
   outline data, `.dasktoon.json` and textures are exactly the Godot export's). Its material writer takes an optional
   `collect(spec, entry, textures)`: the same uniform values it puts in the `.tres` come out as JSON
   (`godot/materials.py`: `param_items`, `value_json`, `params_json`); the `.tres` output is unchanged (Godot test green).
4. Packing: `manifest.json`, `model.glb` (STORED), `rig.json` (= `<name>.dasktoon.json`), `materials.json`,
   `expressions.json`, `finish.json` (`godot/finish.py: layers_json`), `textures/*`, `thumbnail.png`.

## What is in the files

- `materials.json` entry: `name`, `shader`, `cull`, `alpha`, `params` (Godot uniform values; texture = archive path),
  optional `outline` (`shader`, `alpha`, `params`), and `dasktoon`: `node` (bl_idname), `settings` (node properties),
  `inputs` (default value by socket identifier), `textures` (`socket`, `kind`, `color`, `path`, `strength` for a normal
  map), `ramp`. DaskLive ignores `dasktoon`.
- `finish.json`: `{"amount", "layers": {grade|gradient|color|vignette: {uniform: value}}}`; only layers that are on. The
  gradient layer also holds `light_direction`, `gradient_auto`, `gradient_angle`.
- `expressions.json`: `keys` by ARKit name (case of the ARKit spelling) and VRM 1.0 preset (aa ih ou ee oh blink
  blinkLeft blinkRight happy angry sad relaxed surprised, and lookUp/lookDown/lookLeft/lookRight/neutral when a key of that
  name exists), only keys that really move, weight 1.0, `mesh` is the name in the model (merged meshes take the Body's
  name). `bones`: VRM role -> bone name for the standard skeleton's deform bones. `made`: `sculpted`, `filled`,
  `missing` (ARKit names nothing plays).
- Textures: PNG/JPG up to the size option are copied as they are; larger ones are scaled down, other formats (EXR) become PNG.

## Import: `dasktoon_dlive.import_dlive(context, filepath)`

File > Import > DaskLive (.dlive). Refuses a file whose `format` is not `dlive` or whose `version` is above 1 (message names
both versions, nothing is imported). Then: glTF import of `model.glb`; each material with a `dasktoon` block is rebuilt (node,
settings, inputs, textures packed into the .blend, normal map, ramp); sway chains and colliders of `rig.json` go back as a
Hair part (chain bones marked as Build Rig marks them), colliders; shape key values of `rig.json.shapes`.

## Rulings

- R1 One mapping, two outputs: the material writer is refactored (not copied); the Godot export stays byte-identical.
- R2 Expressions on temporary copies, with the parts' pointers moved to the copies for the duration.
- R3 The model for DaskLive is the Godot export run in a temp folder; shaders and README written there are thrown away.
- R4 `finish.json` layout as above (the format doc was loose about where `gradient_auto/angle` go).
- R5 Thumbnail: EEVEE render of a temp scene, 256 px, orthographic from the front (characters face -Y). Any failure is a
  warning, the file is written without it.
- R6 Names of keys follow the VRM presets only through the alias slots in `dasktoon_rig/expressions.py`; one key per slot
  per mesh (the first that moves), as Auto Expressions does.
- R7 The glTF skin needs meshes parented to the armature with vertex groups (as every real DaskToon character has);
  test fixtures set both.
- R8 Import restores sway chains as role Hair; the real role of each part is not in `rig.json`.

## Known gaps

Flat eyes, 2D mouths and bend fixes (`rig.json` `flatEyes`, `mouths`, `correctives`) are not restored on import.
Animation clips are not exported (format v1). `look*` VRM presets need keys with those names.
