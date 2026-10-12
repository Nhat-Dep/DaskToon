# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Anime timing of a clip (docs/superpowers/specs/2026-10-13-dasktoon-anime-timing-design.md, sections 3 and 4): its
timing table Action.dasktoon_timing lists (frame, step), sorted by frame; from a row's frame to the next row the clip runs
on that step: 1 is every frame, 2 to 4 are twos to fours, 0 holds the row's frame. Blender evaluates the table itself
(anim_sys.cc), so the keys are never changed."""

HOLD = 0
LABELS = {1: "1s", 2: "2s", 3: "3s", 4: "4s", HOLD: "Hold"}


def _row(action, frame):
    """The row in effect at `frame`, or None before the first row."""
    found = None
    for row in action.dasktoon_timing:
        if row.frame <= frame:
            found = row
    return found


def step_at(action, frame):
    """The step of `action` at `frame` (1 without a row)."""
    row = _row(action, frame) if action is not None else None
    return row.step if row is not None else 1


def drawn_frame(action, frame):
    """The frame whose pose `action` shows at `frame`: the start of the step that holds it."""
    row = _row(action, frame) if action is not None else None
    if row is None or row.step == 1:
        return frame
    if row.step == HOLD:
        return row.frame
    return row.frame + (frame - row.frame) // row.step * row.step


def has_steps(action):
    """True when the table makes `action` anything but 1s somewhere."""
    return action is not None and any(row.step != 1 for row in action.dasktoon_timing)


def set_step(action, frame, step):
    """The clip runs on `step` from `frame` (a row at that frame is changed); the table stays sorted."""
    rows = {row.frame: row.step for row in action.dasktoon_timing}
    rows[frame] = step
    _write(action, rows)


def remove(action, frame):
    rows = {row.frame: row.step for row in action.dasktoon_timing if row.frame != frame}
    _write(action, rows)


def _write(action, rows):
    action.dasktoon_timing.clear()
    for frame in sorted(rows):
        row = action.dasktoon_timing.add()
        row.frame, row.step = frame, rows[frame]
    action.update_tag()
