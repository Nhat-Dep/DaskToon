# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""What the Add Joint tool does with each click and key (machine rig spec 2), without the mouse: the modal operator in
bl_ui/dasktoon_machine.py turns events into these calls.

States: CHILD (click a piece), PARENT (click its parent, or empty space for the root), ADJUST (the guessed joint is
shown: move the pivot, change the axis or the kind, Enter makes the joint). A click on a piece that has a joint already
opens that joint for changes."""

import numpy as np
from bpy.app.translations import pgettext_rpt as rpt_

from . import MachineError, joints, pieces

CHILD, PARENT, ADJUST = 'CHILD', 'PARENT', 'ADJUST'


class ToolState:
    def __init__(self, context, rig):
        self.context, self.rig = context, rig
        self.binding = pieces.Binding(rig)
        self.root = self.binding.root
        self.state = CHILD
        self.child, self.parent, self.joint, self.editing = [], None, None, None
        self.default_parent = None
        self.history = []
        self.message = ""

    # Reading

    def bone_of(self, piece):
        bone = self.binding.bone_of(piece)
        return None if bone in (None, self.root) else bone

    def unbound(self):
        return self.binding.unbound()

    def status(self):
        """The line the header shows (an English source string, translated by the caller)."""
        if self.state == CHILD:
            return "Click a piece to give it a joint, or a piece with a joint to change it"
        if self.state == PARENT:
            return "Click the piece it hangs from, or empty space for the root. Shift+click: more pieces"
        return ("Enter: make the joint · drag G: move the pivot · X Y Z: axis · A: guessed axis · T: kind · "
                "P: another parent · Backspace: undo the last joint")

    # Clicks

    def _reset(self):
        self.state = CHILD
        self.child, self.parent, self.joint, self.editing = [], None, None, None

    def click(self, piece, shift=False):
        self.message = ""
        if self.state == CHILD:
            if piece is None:
                return
            bone = self.bone_of(piece)
            if bone is not None:
                self._edit(bone)
                return
            self.child = [piece]
            if self.default_parent is not None and self.default_parent in self.rig.data.bones:
                self._set_parent(self.default_parent)
            else:
                self.state = PARENT
            return
        if shift and piece is not None:
            self._toggle(piece)
            return
        if piece is None:
            self._set_parent(self.root)
            return
        if piece in self.child:
            return
        bone = self.bone_of(piece)
        if bone is None:
            bone = joints.add(self.context, self.binding, [piece], None, joints.guess(self.binding, [piece], []))
            self.history.append(bone)
            self.message = rpt_("The parent piece got a free joint of its own: %s") % bone
        self._set_parent(bone)

    def _toggle(self, piece):
        owner = self.bone_of(piece)
        if owner is not None and owner != self.editing:
            self.message = rpt_("This piece has a joint already: %s") % owner
            return
        if piece in self.child:
            self.child.remove(piece)
        else:
            self.child.append(piece)
        if not self.child:
            self._reset()
        elif self.parent is not None:
            self._guess()

    def _edit(self, bone):
        self.editing = bone
        self.child = self.binding.pieces_of(bone)
        parent = self.rig.data.bones[bone].parent
        self.parent = parent.name if parent is not None else self.root
        self.joint = joints.joint_of(self.rig, bone)
        self.state = ADJUST

    def _guess(self):
        parent = [] if self.parent == self.root else self.binding.pieces_of(self.parent)
        self.joint = joints.guess(self.binding, self.child, parent)

    def _set_parent(self, bone):
        if self.editing is not None and (bone == self.editing or bone in joints.descendants(self.rig, self.editing)):
            self.message = rpt_("A joint cannot hang from itself or from a joint below it")
            return
        self.parent = bone
        self._guess()
        self.state = ADJUST

    # Keys

    def pick_parent(self):
        if self.state == ADJUST:
            self.state = PARENT

    def set_axis(self, axis):
        """A world axis, or None for the guessed one."""
        if self.joint is None:
            return
        if axis is None:
            pivot = self.joint.pivot
            self._guess()
            self.joint.pivot = pivot
        else:
            self.joint.axis = np.asarray(axis, dtype=float)

    def cycle_kind(self):
        if self.joint is not None:
            kinds = joints.KINDS
            self.joint.kind = kinds[(kinds.index(self.joint.kind) + 1) % len(kinds)]

    def move_pivot(self, point):
        if self.joint is not None:
            self.joint.pivot = np.asarray(point, dtype=float)

    def confirm(self):
        """Make (or change) the joint; returns its name, or None when there is nothing to make yet."""
        if self.state != ADJUST or not self.child:
            return None
        if self.editing is not None:
            name = self.editing
            old = self.rig.data.bones[name].parent
            if (old.name if old is not None else self.root) != self.parent:
                joints.set_parent(self.context, self.binding, name, self.parent)
            current = self.binding.pieces_of(name)
            added = [p for p in self.child if p not in current]
            dropped = [p for p in current if p not in self.child]
            if added:
                self.binding.bind(added, name)
            if dropped:
                self.binding.bind(dropped, self.root)
            joints.move(self.context, self.binding, name, self.joint)
        else:
            name = joints.add(self.context, self.binding, self.child, self.parent, self.joint)
            self.history.append(name)
        self.default_parent = name
        self._reset()
        return name

    def undo_last(self):
        if not self.history:
            return None
        name = self.history.pop()
        if name not in self.rig.data.bones:
            return None
        try:
            parent = joints.remove(self.context, self.binding, name)
        except MachineError:
            return None
        self.default_parent = None if parent == self.root else parent
        self._reset()
        return name
