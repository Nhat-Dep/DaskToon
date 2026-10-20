# Model Guide Implementation Plan

**Goal:** the Guide tab of docs/superpowers/specs/2026-10-20-dasktoon-model-guide-design.md: Model Check, Steps, pages.

**Architecture:** `scripts/modules/dasktoon_guide/` holds the logic (checks.py: one function a check returning a Result;
fixes.py: one function a fixable check; steps.py: the nine steps; pages/: HTML); `scripts/startup/bl_ui/dasktoon_guide.py`
holds the sidebar panels, the window's result list and the operators (check, fix, open page). Checks reuse
dasktoon_rig (facing, build's normal test, eye_shapes, correctives) and dasktoon_export (materials faces use).

**Spec:** docs/superpowers/specs/2026-10-20-dasktoon-model-guide-design.md

## Global Constraints

- Every visible string goes through translations (Vietnamese in dasktoon_translations.py); no "\\u" escapes in source.
- Lines at most 120 columns; tests registered in tests/python/CMakeLists.txt; new modules listed in the translations test.
- The test runner is the VS 2026 build (rt.sh); real models only on copies, their pictures out of git.

## Tasks

1. checks.py and fixes.py for Standing, Mesh and Materials; tests `dasktoon_guide_checks_test` (a good chibi passes
   every check; each bad variant fails its check and its fix makes it pass).
2. After-the-rig checks (Rig, Rig Check, Joint loops, Eyes, Mouth, Expressions); tests in the same file.
3. steps.py, the sidebar tab (panels, result list, operators), the Unity step's mark from Engine Export,
   translations; tests `dasktoon_guide_ui_test` (panels draw, Check fills the list, Fix runs, the sidebar test allows
   the Guide tab only).
4. Pages (en, vi) with an anchor a check, the page operator, pictures by `tools/dasktoon_guide_pictures.py`; tests
   (every step and check has its page and anchor in both languages, every picture a page uses exists).
5. Real-window shots of the tab, the Model Check on the six real models (copies), report.
