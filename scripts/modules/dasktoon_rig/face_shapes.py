# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Sculpt the ARKit face keys nothing else makes (docs/superpowers/specs/2026-11-11-dasktoon-dlive-face-sculpt-design.md).

Every size is the face's own, read from the eyes eye_shapes.find_eyes finds (their width W, the distance between them A)
and the mouth (a slit that opens, a drawn line, pieces; else where a mouth lies below the eyes, half its width H): no number
here is in metres. A key is a smooth offset field over the vertices of the face region: it fades to nothing with the
distance from what it moves, so no vertex outside the face region moves and no seam tears.

Brows: a loose pair of pieces above the eyes (a mesh of its own, or pieces of the face's) moves as they are; with none, the
skin above the eyes does, from the lid's height up to about W over it. Inner up, outer up and down differ in how the move
fades from the middle of the face outward. Cheeks: a lift under each eye (squint) and a push out along the surface (puff).
Nose: the wings rise and spread. Mouth: a field round the mouth's middle, tapering at HALF its width from the corners
and a bit more above and below; pucker and funnel pull it to the middle and forward, left and right slide it, the rolls,
shrugs and press move the lips up or down by the band of the upper lip or the lower one, stretch and dimple are the corners.
Jaw: the lower face turns about the ear, a hinge estimated from the eyes, and fades out past the ears and the chin.
Eyes: wide scales each eye up about its middle (eye_shapes WIDEN), squint down to SQUINT of its height. The look keys
are not made: the pieces of an eye lie behind holes in the face and out of them when they move (filie's iris is wider than
what shows), so the game turns the eye bones. A key that already moves where it belongs is left alone."""

import numpy as np

from . import eye_shapes, expressions
from .eye_shapes import _rest, _is_mesh_of

BROW_UP = 0.35  # (of the eye's width) how far brows rise
BROW_DOWN = 0.3
LID_HEIGHT = 0.45  # (of the eye's width) the lid lies at most this far above the eye's middle
LID = 0.05  # (of the eye's width) the skin above the lid that does not move
BROW_REACH = 1.3  # (of the eye's width) how far above the lid the skin of a brow key moves
CHEEK_LIFT = 0.14  # (of the eye's width)
PUFF = 0.14  # (of the distance between the eyes) how far a cheek swells
SNEER = 0.07
SQUINT = 0.7  # of the eye's height
JAW_TURN = 0.09  # radians
JAW_OPEN = 0.11
WORKS = 0.03  # (of the eye's width) a key moves its region at least this far
JAW_FORWARD = 0.12  # (of the distance between the eyes)
JAW_BELOW = 0.8  # (of the distance between the eyes) from the mouth to the chin
MOUTH_SPREAD = (1.7, 1.3)  # of the mouth's half width: how far across and up and down the mouth's field reaches
FIND = "found"

ARKIT_FACE = (
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "eyeWideLeft", "eyeWideRight",
    "eyeSquintLeft", "eyeSquintRight", "cheekPuff", "cheekSquintLeft", "cheekSquintRight", "noseSneerLeft",
    "noseSneerRight", "mouthPucker", "mouthFunnel", "mouthLeft", "mouthRight", "mouthRollLower", "mouthRollUpper",
    "mouthShrugLower", "mouthShrugUpper", "mouthPressLeft", "mouthPressRight", "mouthStretchLeft", "mouthStretchRight",
    "mouthDimpleLeft", "mouthDimpleRight", "mouthClose", "jawForward", "jawLeft", "jawRight", "jawOpen",
    "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight", "mouthLowerDownLeft",
    "mouthLowerDownRight", "mouthUpperUpLeft", "mouthUpperUpRight")
# the VRM presets: (slot, its VRM 0.x name, [(ARKit key, weight)])
PRESETS = (("A", "a", (("jawOpen", 1.0),)), ("I", "i", (("mouthStretchLeft", 0.9), ("mouthStretchRight", 0.9))),
           ("U", "u", (("mouthPucker", 1.0),)),
           ("E", "e", (("mouthStretchLeft", 0.5), ("mouthStretchRight", 0.5), ("jawOpen", 0.35))),
           ("O", "o", (("mouthFunnel", 1.0), ("jawOpen", 0.5))),
           ("ANGRY", "angry", (("browDownLeft", 1.0), ("browDownRight", 1.0), ("eyeSquintLeft", 0.4),
                               ("eyeSquintRight", 0.4), ("mouthFrownLeft", 0.3), ("mouthFrownRight", 0.3))),
           ("SORROW", "sorrow", (("browInnerUp", 0.9), ("mouthFrownLeft", 0.8), ("mouthFrownRight", 0.8))),
           ("FUN", "fun", (("eyeSquintLeft", 0.5), ("eyeSquintRight", 0.5), ("mouthSmileLeft", 0.4),
                           ("mouthSmileRight", 0.4), ("cheekSquintLeft", 0.5), ("cheekSquintRight", 0.5))))


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _band(x, low_a, low_b, high_a, high_b):
    """0 under low_a, rising to 1 at low_b, flat to high_a, falling to 0 at high_b."""
    return _smooth((x - low_a) / max(low_b - low_a, 1e-9)) * (1.0 - _smooth((x - high_a) / max(high_b - high_a, 1e-9)))


class Face:
    """What the keys are sized by: all in armature space (the head's frame)."""

    def __init__(self, rig, meshes, eyes):
        self.rig, self.eyes = rig, eyes
        left, right = eyes["LEFT"], eyes["RIGHT"]
        self.width = float(np.mean([e.high[0] - e.low[0] for e in eyes.values()]))
        self.tall = float(np.mean([e.high[2] - e.low[2] for e in eyes.values()]))
        self.mid = (left.low[0] + left.high[0] + right.low[0] + right.high[0]) / 4.0
        self.apart = abs((left.low[0] + left.high[0]) - (right.low[0] + right.high[0])) / 2.0
        self.eye_low = min(e.low[2] for e in eyes.values())
        self.eye_top = max(e.high[2] for e in eyes.values())
        self.eye_z = (self.eye_low + self.eye_top) / 2.0
        # the upper lid: a band of eye pieces that took a brow or a tall lash in is no taller than this above its middle
        self.lid = min(self.eye_top, self.eye_z + LID_HEIGHT * self.width)
        centre, self.size = eye_shapes._head(rig)
        self.head_y = float(centre[1])
        mouth = (eye_shapes.slit_mouth(rig, meshes, eyes) or eye_shapes.drawn_mouth(rig, meshes, eyes)
                 or eye_shapes.piece_mouth(rig, meshes, eyes))
        self.mouth_found = mouth is not None
        if mouth is not None:
            self.x0, self.z0, self.half = float(mouth[0][0]), float(mouth[0][2]), float(mouth[1])
        else:  # where a mouth lies below the eyes of an anime face
            self.x0, self.z0, self.half = self.mid, self.eye_low - 0.55 * self.apart, 0.3 * self.apart
        self.half = max(self.half, 0.02 * self.apart)
        hair = {p.object for p in rig.data.dasktoon_rig.parts if p.role == 'HAIR'}
        roles = {p.object: p.role for p in rig.data.dasktoon_rig.parts}
        self.meshes = [o for o in meshes if _is_mesh_of(rig, o) and len(o.data.vertices) and o not in hair]
        self.roles = roles
        self.rests = {o: _rest(rig, o) for o in self.meshes}
        self._movable = {}
        if not self.mouth_found:  # a face that ends sooner than the usual distance below the eyes: the mouth is half way
            lowest = [r[(np.abs(r[:, 0] - self.mid) < 0.3 * self.apart) & (r[:, 1] < self.head_y)
                        & (r[:, 2] < self.eye_low), 2].min(initial=self.eye_low)
                      for o, r in self.rests.items() if roles.get(o) == 'BODY']
            if lowest and min(lowest) < self.eye_low:
                self.z0 = max(self.z0, self.eye_low - 0.5 * (self.eye_low - min(lowest)))

    # -- where the vertices a key may move are -------------------------------------------------------------------------
    def movable(self, obj):
        """Mask of the vertices of `obj` a key may move: of the Body, the loose pieces that make the face's skin (a hair
        lock of the same mesh in front of the cheek is another piece and stays), in the face box; of other meshes only
        the small loose pieces lying wholly in the mouth's place (teeth, a tongue)."""
        if obj in self._movable:
            return self._movable[obj]
        rest = self.rests[obj]
        box = self.in_box(rest)
        out = np.zeros(len(rest), bool)
        pieces = eye_shapes._pieces(obj.data)
        if self.roles.get(obj) == 'BODY':
            a = self.apart
            middle = ((np.abs(rest[:, 0] - self.mid) < a) & (rest[:, 2] > self.eye_z - 2.0 * a)
                      & (rest[:, 2] < self.eye_z + 0.5 * a) & (rest[:, 1] < self.head_y))
            counts = [int(middle[piece].sum()) for piece in pieces]
            most = max(counts) if counts else 0
            for piece, count in zip(pieces, counts):
                if most and count >= 0.25 * most:
                    out[piece] = True
            out &= box
        else:  # teeth, a tongue, the inside of a mouth: small loose pieces that lie in the mouth's own place
            h = self.half
            inside = ((np.abs(rest[:, 0] - self.x0) < 2.5 * h) & (np.abs(rest[:, 2] - self.z0) < 2.0 * h)
                      & (rest[:, 1] < self.head_y + 0.15 * self.size))
            for piece in pieces:
                if len(piece) >= eye_shapes.FEWEST and inside[piece].all() and np.ptp(rest[piece], axis=0).max() <                         eye_shapes.WIDEST * self.size:
                    out[piece] = True
        self._movable[obj] = out
        return out

    def in_box(self, rest):
        a = self.apart
        return ((np.abs(rest[:, 0] - self.mid) < 3.2 * a) & (rest[:, 2] > self.eye_z - 4.5 * a)
                & (rest[:, 2] < self.eye_z + 3.0 * a) & (rest[:, 1] < self.head_y + 0.15 * self.size))

    def side(self, rest, which):
        """How much of the character's left (+X) or right each vertex takes: a smooth step across the middle."""
        blend = 0.08 * self.apart  # the blend across the middle
        t = _smooth(((rest[:, 0] - self.mid) + blend) / (2.0 * blend))
        return t if which == 'LEFT' else 1.0 - t

    def lean(self, rest, middle=None):
        """-1 on the right of the face's middle, +1 on the left, through 0 at the middle (a smooth sign: a vertex on
        the middle line moves nothing sideways, whichever side the rounding puts it)."""
        return np.clip((rest[:, 0] - (self.mid if middle is None else middle)) / (0.1 * self.apart), -1.0, 1.0)

    def normals(self, obj):
        """Unit vertex normals of `obj` at rest, armature space."""
        mesh = obj.data
        n = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("normal", n)
        n = n.reshape(-1, 3)
        to_arm = np.array((self.rig.matrix_world.inverted() @ obj.matrix_world).to_3x3())
        n = n @ np.linalg.inv(to_arm)  # inverse transpose
        return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)

    # -- brows ------------------------------------------------------------------------------------------------------
    def brow_pieces(self):
        """{object: [vertex indices]} of the loose pieces over the eyes, a pair twin across the middle (brows of a mesh
        of their own, or loose pieces of the face's), not part of an eye; {} without a pair."""
        eye_pieces = {(o, int(p[0])) for e in self.eyes.values() for o, p in e.pieces if len(p)}
        found = {"LEFT": [], "RIGHT": []}
        for obj in self.meshes:
            rest = self.rests[obj]
            for piece in eye_shapes._pieces(obj.data):
                if len(piece) < eye_shapes.FEWEST or (obj, int(piece[0])) in eye_pieces:
                    continue
                p = rest[piece]
                low, high = p.min(axis=0), p.max(axis=0)
                middle, size = (low + high) / 2.0, high - low
                if (low[2] > self.lid - 0.05 * self.tall and middle[2] < self.lid + 1.6 * self.width
                        and abs(abs(middle[0] - self.mid) - self.apart / 2.0) < 0.7 * self.apart
                        and size[0] < 1.8 * self.width and size[2] < 0.9 * self.width
                        and middle[1] < self.head_y and size[0] > 0.2 * self.width):
                    if self.roles.get(obj) == 'BODY' and not self._on_skin(obj, piece):
                        continue  # a hair lock of the face's own mesh hangs in front of the skin; a brow lies on it
                    found["LEFT" if middle[0] > self.mid else "RIGHT"].append((obj, piece))
        if not found["LEFT"] or not found["RIGHT"]:
            return {}
        out = {}
        for pieces in found.values():
            for obj, piece in pieces:
                out.setdefault(obj, []).append(piece)
        return {obj: np.concatenate(pieces) for obj, pieces in out.items()}

    def _on_skin(self, obj, piece):
        """True when the loose `piece` of the Body mesh `obj` lies on the face's skin (no further in front of it than a
        tenth of the eyes' distance)."""
        rest, skin = self.rests[obj], self.movable(obj)
        p = rest[piece]
        centre = (p.min(axis=0) + p.max(axis=0)) / 2.0
        a = self.apart
        near = skin & ~np.isin(np.arange(len(rest)), piece) & (np.abs(rest[:, 0] - centre[0]) < 0.2 * a)             & (np.abs(rest[:, 2] - centre[2]) < 0.2 * a)
        return bool(near.any()) and abs(float(rest[near, 1].mean()) - float(p[:, 1].mean())) < 0.1 * a

    def brow(self, key):
        """{object: offsets} of the brow key `key` (Down, InnerUp, OuterUp, with its side)."""
        which = "LEFT" if key.endswith("Left") else "RIGHT" if key.endswith("Right") else None
        pieces = self.brow_pieces()
        out = {}
        for obj in self.meshes:
            rest = self.rests[obj]
            reach = np.zeros(len(rest))
            if pieces:
                if obj in pieces:
                    reach[pieces[obj]] = 1.0
            else:
                reach = self.movable(obj).astype(float)
                above = (rest[:, 2] - self.lid) / self.width
                reach *= _band(above, LID, 0.35, 0.75, BROW_REACH)
            if not reach.any():
                continue
            offsets = np.zeros_like(rest)
            u = np.abs(rest[:, 0] - self.mid)
            inner = max(self.apart / 2.0 - self.width / 2.0, 0.0)
            outer = self.apart / 2.0 + self.width / 2.0
            t = np.clip((u - inner) / max(outer - inner, 1e-9), 0.0, 1.0)
            across = 1.0 - _smooth((u - outer) / (0.25 * self.width))
            share = self.side(rest, which) if which else 1.0
            if key == "browInnerUp":
                offsets[:, 2] = BROW_UP * self.width * (1.0 - t)
            elif key.startswith("browOuterUp"):
                offsets[:, 2] = BROW_UP * self.width * t
            else:
                offsets[:, 2] = -BROW_DOWN * self.width * (1.0 - 0.5 * t)
                offsets[:, 0] = -self.lean(rest) * 0.08 * self.width * (1.0 - t)
            out[obj] = offsets * (reach * across * share)[:, None]
        return out

    # -- eyes -------------------------------------------------------------------------------------------------------
    def eye_move(self, how, side):
        """{object: offsets} of both pieces and skin of the eye on `side` for `how` ('WIDEN', 'SQUINT')."""
        eye = self.eyes[side]
        skin = eye_shapes._skin(self.rig, {side: eye}, self.meshes)
        out = {}
        holders = list(dict.fromkeys([o for o, _p in eye.pieces] + list(skin)))
        for obj in holders:
            rest = self.rests[obj]
            moved = np.zeros_like(rest)
            for i, (owner, piece) in enumerate(eye.pieces):
                if owner != obj:
                    continue
                if how in ('WIDEN', 'SQUINT'):
                    moved[piece] = self._scale(eye, rest[piece], how) - rest[piece]
            near, fade = skin.get(obj, {}).get(side, ((), None))
            if len(near) and how in ('WIDEN', 'SQUINT'):
                moved[near] = (self._scale(eye, rest[near], how) - rest[near]) * fade[:, None]
            if moved.any():
                out[obj] = moved
        return out

    @staticmethod
    def _scale(eye, points, how):
        out = points.copy()
        middle = (eye.low + eye.high) / 2.0
        if how == 'WIDEN':
            for axis in (0, 2):
                out[:, axis] = middle[axis] + (points[:, axis] - middle[axis]) * eye_shapes.WIDEN
        else:
            out[:, 2] = middle[2] + (points[:, 2] - middle[2]) * SQUINT
        return out

    # -- cheeks, nose ------------------------------------------------------------------------------------------------
    def spot(self, rest, centre, across, up):
        """A smooth bump 1 at `centre` (x, z), gone `across` and `up` from it."""
        r = np.sqrt(((rest[:, 0] - centre[0]) / across) ** 2 + ((rest[:, 2] - centre[1]) / up) ** 2)
        return _smooth(1.0 - r)

    def cheek(self, key):
        out = {}
        for obj in self.meshes:
            if self.roles.get(obj) != 'BODY':
                continue
            rest, box = self.rests[obj], self.movable(obj)
            offsets = np.zeros_like(rest)
            if key == "cheekPuff":
                z = (self.eye_low + self.z0) / 2.0 - 0.05 * self.apart
                tall = max((self.eye_low - self.z0) / 2.0 + 0.3 * self.apart, 0.4 * self.apart)
                bump = sum(self.spot(rest, (self.mid + s * 0.95 * self.apart, z), 0.6 * self.apart, tall)
                           for s in (1.0, -1.0))
                n = self.normals(obj)
                n[:, 1] = np.minimum(n[:, 1], 0.0)  # forward or sideways, never backwards
                offsets = n * (PUFF * self.apart * bump)[:, None]
            else:
                side = "LEFT" if key.endswith("Left") else "RIGHT"
                eye = self.eyes[side]
                centre = ((eye.low[0] + eye.high[0]) / 2.0, self.eye_low - 0.45 * self.width)
                bump = self.spot(rest, centre, 0.9 * self.width, 0.65 * self.width)
                offsets[:, 2] = CHEEK_LIFT * self.width * bump
                offsets[:, 1] = -0.05 * self.width * bump
            out[obj] = offsets * (box * 1.0)[:, None]
        return out

    def nose(self, key):
        out = {}
        s = 1.0 if key.endswith("Left") else -1.0
        for obj in self.meshes:
            if self.roles.get(obj) != 'BODY':
                continue
            rest = self.rests[obj]
            z = self.eye_low - 0.3 * (self.eye_low - self.z0)
            bump = self.spot(rest, (self.mid + s * 0.22 * self.apart, z), 0.28 * self.apart, 0.25 * self.apart)
            offsets = np.zeros_like(rest)
            offsets[:, 2] = SNEER * self.apart * bump
            offsets[:, 0] = s * 0.5 * SNEER * self.apart * bump
            out[obj] = offsets * self.movable(obj)[:, None]
        return out

    # -- mouth, jaw --------------------------------------------------------------------------------------------------
    def mouth_field(self, rest):
        """(field 1 at the mouth's middle and gone MOUTH_SPREAD of its half width off it, vertical position in half
        widths from the lip line, across in half widths, the corners' bump)."""
        h = self.half
        across, up = (rest[:, 0] - self.x0) / h, (rest[:, 2] - self.z0) / h
        w = _smooth(1.0 - np.sqrt((across / MOUTH_SPREAD[0]) ** 2 + (up / MOUTH_SPREAD[1]) ** 2))
        corner = np.exp(-(((np.abs(across) - 1.0) / 0.55) ** 2) - (up / 0.6) ** 2)
        return w, up, across, corner

    def mouth(self, key):
        h = self.half
        out = {}
        which = "LEFT" if key.endswith("Left") else "RIGHT" if key.endswith("Right") else None
        for obj in self.meshes:
            mask = self.movable(obj)
            if not mask.any():
                continue
            rest = self.rests[obj]
            w, up, across, corner = self.mouth_field(rest)
            lower = 1.0 - _smooth((up + 0.1) / 0.3)
            upper = _smooth(up / 0.3)
            d = np.zeros_like(rest)
            share = self.side(rest, which)[:] if which else np.ones(len(rest))
            if key == "mouthPucker":
                d[:, 0] = -(rest[:, 0] - self.x0) * 0.4 * w
                d[:, 1] = -0.35 * h * w
            elif key == "mouthFunnel":
                d[:, 0] = -(rest[:, 0] - self.x0) * 0.25 * w
                d[:, 1] = -0.4 * h * w
                d[:, 2] = 0.15 * h * w * np.tanh(up / 0.3)
            elif key in ("mouthLeft", "mouthRight"):
                d[:, 0] = (0.45 if key == "mouthLeft" else -0.45) * h * w
            elif key == "mouthRollLower":
                d[:, 2], d[:, 1] = 0.22 * h * w * lower, 0.15 * h * w * lower
            elif key == "mouthRollUpper":
                d[:, 2], d[:, 1] = -0.18 * h * w * upper, 0.15 * h * w * upper
            elif key == "mouthShrugLower":
                d[:, 2], d[:, 1] = 0.28 * h * w * lower, -0.1 * h * w * lower
            elif key == "mouthShrugUpper":
                d[:, 2], d[:, 1] = 0.2 * h * w * upper, -0.08 * h * w * upper
            elif key.startswith("mouthPress"):
                d[:, 2] = 0.12 * h * w * (lower - upper) * share
            elif key == "mouthClose":
                d[:, 2] = 0.1 * h * w * (lower - upper)
            elif key.startswith("mouthStretch"):
                d[:, 0] = self.lean(rest, self.x0) * 0.35 * h * corner * share
                d[:, 2] = -0.12 * h * corner * share
            elif key.startswith("mouthSmile"):
                d[:, 2] = 0.3 * h * corner * share
                d[:, 0] = self.lean(rest, self.x0) * 0.15 * h * corner * share
            elif key.startswith("mouthFrown"):
                d[:, 2] = -0.25 * h * corner * share
            elif key.startswith("mouthLowerDown"):
                d[:, 2] = -0.35 * h * w * lower * share
            elif key.startswith("mouthUpperUp"):
                d[:, 2] = 0.2 * h * w * upper * share
            elif key.startswith("mouthDimple"):
                d[:, 1] = 0.25 * h * corner * share
                d[:, 0] = self.lean(rest, self.x0) * 0.12 * h * corner * share
            out[obj] = d * mask[:, None]
        return out

    def chin(self):
        """Height of the chin: the lowest place under the mouth where the face's skin still lies as far forward as the
        mouth (below it the neck falls back); a face of its own height when no skin shows it."""
        if getattr(self, "_chin", None) is None:
            a = self.apart
            fronts = []
            for obj in self.meshes:
                if self.roles.get(obj) != 'BODY':
                    continue
                rest = self.rests[obj]
                near = rest[(np.abs(rest[:, 0] - self.mid) < 0.3 * a) & (rest[:, 1] < self.head_y)
                            & (rest[:, 2] < self.z0) & (rest[:, 2] > self.z0 - 2.5 * a)]
                fronts.append(near)
            near = np.concatenate(fronts) if fronts else np.zeros((0, 3))
            chin = self.z0 - 1.0 * a
            if len(near) > 8:
                front = near[:, 1].min()
                forward = near[near[:, 1] < front + 0.35 * a]
                chin = float(forward[:, 2].min())
            self._chin = float(np.clip(chin, self.z0 - 2.2 * a, self.z0 - 0.35 * a))
        return self._chin

    def jaw(self, key):
        a = self.apart
        out = {}
        pivot = np.array((self.mid, self.head_y + 0.15 * self.size, self.eye_low - 0.2 * a))
        chin = self.chin()
        for obj in self.meshes:
            mask = self.movable(obj)
            if not mask.any():
                continue
            rest = self.rests[obj]
            weight = (_smooth((self.z0 + 0.1 * self.half - rest[:, 2]) / (0.9 * self.half + 0.15 * a))
                      * (1.0 - _smooth((chin - rest[:, 2]) / (0.15 * a)))
                      * (1.0 - _smooth((np.abs(rest[:, 0] - self.mid) - 1.3 * a) / (0.5 * a)))
                      * _smooth((self.head_y - rest[:, 1]) / (0.3 * self.size)))
            d = np.zeros_like(rest)
            v = rest - pivot
            if key == "jawForward":
                d[:, 1] = -JAW_FORWARD * a
            elif key == "jawOpen":  # about the ear's axis: the chin goes down and back
                d[:, 1] = (np.cos(JAW_OPEN) - 1.0) * v[:, 1] - np.sin(JAW_OPEN) * v[:, 2]
                d[:, 2] = np.sin(JAW_OPEN) * v[:, 1] + (np.cos(JAW_OPEN) - 1.0) * v[:, 2]
            else:
                theta = JAW_TURN if key == "jawLeft" else -JAW_TURN
                d[:, 0] = (np.cos(theta) - 1.0) * v[:, 0] - np.sin(theta) * v[:, 1]
                d[:, 1] = np.sin(theta) * v[:, 0] + (np.cos(theta) - 1.0) * v[:, 1]
            out[obj] = d * (weight * mask)[:, None]
        return out

    # -- where a key does its work -----------------------------------------------------------------------------------
    def boxes(self, name):
        """[(x low, x high, z low, z high)] where the key `name` should move something, armature space."""
        w, a, m = self.width, self.apart, self.mid
        if name.startswith("brow"):
            return [(m - a / 2.0 - w, m + a / 2.0 + w, self.lid + 0.15 * w, self.lid + 1.6 * w)]
        if name.startswith(("eyeWide", "eyeSquint", "cheekSquint")):
            eye = self.eyes["LEFT" if name.endswith("Left") else "RIGHT"]
            low = self.eye_low - 1.0 * w if name.startswith("cheek") else eye.low[2] - 0.3 * w
            top = eye.low[2] if name.startswith("cheek") else eye.high[2] + 0.3 * w
            return [(eye.low[0] - 0.4 * w, eye.high[0] + 0.4 * w, low, top)]
        if name == "cheekPuff":
            return [(m + s * 0.3 * a, m + s * 1.6 * a, self.z0 - 0.2 * a, self.eye_low) if s > 0
                    else (m - 1.6 * a, m - 0.3 * a, self.z0 - 0.2 * a, self.eye_low) for s in (1.0, -1.0)]
        if name.startswith("nose"):
            return [(m - 0.6 * a, m + 0.6 * a, self.z0, self.eye_low)]
        if name.startswith("jaw"):
            return [(m - 1.6 * a, m + 1.6 * a, self.chin() - 0.5 * a, self.z0 + 0.2 * self.half)]
        h = self.half
        return [(self.x0 - MOUTH_SPREAD[0] * h, self.x0 + MOUTH_SPREAD[0] * h, self.z0 - MOUTH_SPREAD[1] * h,
                 self.z0 + MOUTH_SPREAD[1] * h)]

    def reach(self, name, rest, fade=0.0):
        """Per vertex of `rest` 1 inside the places the key `name` works (boxes), falling to 0 `fade` of the eyes' distance
        outside them."""
        out = np.zeros(len(rest))
        m = max(fade * self.apart, 1e-9)
        for x0, x1, z0, z1 in self.boxes(name):
            inside = (_smooth((rest[:, 0] - (x0 - m)) / m) * _smooth(((x1 + m) - rest[:, 0]) / m)
                      * _smooth((rest[:, 2] - (z0 - m)) / m) * _smooth(((z1 + m) - rest[:, 2]) / m))
            if fade <= 0.0:
                inside = ((rest[:, 0] > x0) & (rest[:, 0] < x1) & (rest[:, 2] > z0) & (rest[:, 2] < z1)).astype(float)
            out = np.maximum(out, inside)
        return out

    def does_work(self, name, objs):
        """True when the key `name` of one of `objs` moves a vertex of its region by at least a share of an eye's width."""
        for obj, _block, moved, _base, _co in self._blocks(name, objs):
            if (moved * self.reach(name, self.rests[obj])).max() > WORKS * self.width:
                return True
        return False

    def _blocks(self, name, objs):
        """[(object, key block, how far each vertex moves, armature space)] of the keys of `objs` called `name`."""
        out = []
        for obj in objs:
            key = obj.data.shape_keys
            if key is None or obj not in self.rests:
                continue
            base = np.empty(len(key.reference_key.data) * 3)
            key.reference_key.data.foreach_get("co", base)
            to_arm = np.array((self.rig.matrix_world.inverted() @ obj.matrix_world).to_3x3())
            for block in key.key_blocks:
                if block == key.reference_key or block.name.lower() != name.lower():
                    continue
                co = np.empty_like(base)
                block.data.foreach_get("co", co)
                out.append((obj, block, np.linalg.norm((co - base).reshape(-1, 3) @ to_arm.T, axis=1), base, co))
        return out

    def confine(self, name):
        """The key `name` made from others (a whole-face key) moves what lies outside its region (a smile that closes an
        eye): take that out, fading over a quarter of the eyes' distance. Returns True when it changed."""
        changed = False
        for obj, block, moved, base, co in [(o, b, m, bs, c) for o, b, m, bs, c in self._blocks(name, self.meshes)]:
            weight = self.reach(name, self.rests[obj], 0.25)
            if (moved * (1.0 - weight)).max() > 0.2 * WORKS * self.width:
                block.data.foreach_set("co", (base + (co - base) * np.repeat(weight, 3)))
                changed = True
        return changed


def bone_eyes(rig):
    """{"LEFT": Eye, "RIGHT": Eye} sized by the eye bones of `rig` (LeftEye, RightEye): a face with sockets and lids has
    no pieces to find, its eyes are where the skeleton puts them, as wide as a share of the distance between them; {}
    without both bones."""
    left, right = rig.data.bones.get("LeftEye"), rig.data.bones.get("RightEye")
    if left is None or right is None:
        return {}
    apart = abs(left.head_local[0] - right.head_local[0])
    if apart <= 1e-9:
        return {}
    half = np.array((0.21 * apart, 0.02 * apart, 0.15 * apart))
    return {side: eye_shapes.Eye(side, [], np.array(bone.head_local) - half, np.array(bone.head_local) + half)
            for side, bone in (("LEFT", left), ("RIGHT", right))}


def _moving(obj):
    key = obj.data.shape_keys
    if key is None:
        return set()
    base = np.empty(len(key.reference_key.data) * 3, np.float32)
    key.reference_key.data.foreach_get("co", base)
    return {b.name.lower() for b in key.key_blocks if b != key.reference_key and expressions.key_moves(b, base)}


def _put(rig, obj, name, moved):
    """`moved` (offsets of `obj` in armature space) as the key `name` of `obj`, off."""
    key = obj.data.shape_keys
    if key is None:
        obj.shape_key_add(name="Basis", from_mix=False)
        key = obj.data.shape_keys
    block = key.key_blocks.get(name) or obj.shape_key_add(name=name, from_mix=False)
    base = np.empty(len(key.reference_key.data) * 3)
    key.reference_key.data.foreach_get("co", base)
    to_arm = np.array((rig.matrix_world.inverted() @ obj.matrix_world).to_3x3())
    block.data.foreach_set("co", (base.reshape(-1, 3) + moved @ np.linalg.inv(to_arm).T).ravel())
    block.value = 0.0


HOW = {
    "brow": "brows: the loose pieces above the eyes, else the skin above them, moved up, down or inward",
    "eyeWide": "the eye grown about its middle", "eyeSquint": "the eye shrunk to {} of its height".format(SQUINT),
"cheekPuff": "the cheeks pushed out along the surface",
    "cheekSquint": "the skin under the eye lifted", "noseSneer": "the nose's wings raised and spread",
    "mouth": "the skin round the mouth moved", "jaw": "the lower face turned about the ear",
}


def how_of(name):
    for prefix in ("eyeWide", "eyeSquint", "cheekPuff", "cheekSquint", "noseSneer", "brow", "mouth", "jaw"):
        if name.startswith(prefix):
            return HOW[prefix]
    return "sculpted from the face"


def _fields(face, name):
    if name.startswith("brow"):
        return face.brow(name)
    if name.startswith(("eyeWide", "eyeSquint")):
        return face.eye_move('WIDEN' if "Wide" in name else 'SQUINT', "LEFT" if name.endswith("Left") else "RIGHT")
    if name.startswith("cheek"):
        return face.cheek(name)
    if name.startswith("nose"):
        return face.nose(name)
    if name.startswith("jaw"):
        return face.jaw(name)
    return face.mouth(name)


def _one_sided(name):
    return name.endswith(("Left", "Right"))


def _stand_in(obj, name):
    """The key of `obj` named `name`, whatever its case, goes back to moving nothing."""
    key = obj.data.shape_keys
    if key is None:
        return
    base = np.empty(len(key.reference_key.data) * 3)
    key.reference_key.data.foreach_get("co", base)
    for block in key.key_blocks:
        if block != key.reference_key and block.name.lower() == name.lower():
            block.data.foreach_set("co", base)
            block.value = 0.0


def sculpt(rig, meshes, wanted=None, confined=()):
    """Make the ARKit face keys of ARKIT_FACE (those of `wanted` if given) that no mesh of `meshes` moves where it should;
    returns [(key name, how, [mesh names])]; nothing without both eyes found. `confined`: names of keys made from
    others, which lose what they move outside their region. A key under the name that moves only
    elsewhere is a stand-in (a "browInnerUp" made from a whole-face key that only widens the eyes): it is cleared and
    made again."""
    if rig is None:
        return []
    eyes = eye_shapes.find_eyes(rig, meshes) or bone_eyes(rig)
    if not eyes:
        return []
    face = Face(rig, meshes, eyes)
    made = []
    for name in confined:  # keys the export made from whole-face keys move only where they belong
        if name in ARKIT_FACE:
            face.confine(name)
    for name in ARKIT_FACE:
        if (wanted is not None and name not in wanted) or face.does_work(name, face.meshes):
            continue
        usable = {obj: offsets for obj, offsets in _fields(face, name).items()
                  if offsets.any() and not (_one_sided(name) and eye_shapes.has_mirror(obj))}
        if not usable:
            continue
        for obj in face.meshes:
            _stand_in(obj, name)
        for obj, offsets in usable.items():
            _put(rig, obj, name, offsets)
        made.append((name, how_of(name), [obj.name for obj in usable]))
    return made


def sculpt_presets(rig, meshes):
    """The VRM expressions nothing moves yet (PRESETS), made of the ARKit fields, under their VRM 0.x names; returns
    [(key name, how, [mesh names])]."""
    from . import auto_expressions
    if rig is None:
        return []
    eyes = eye_shapes.find_eyes(rig, meshes) or bone_eyes(rig)
    if not eyes:
        return []
    face = Face(rig, meshes, eyes)
    states = auto_expressions.states(face.meshes)
    made = []
    for slot, name, parts in PRESETS:
        if states.get(slot) == 'READY':
            continue
        total = {}
        for part, weight in parts:
            for obj, offsets in _fields(face, part).items():
                total[obj] = total.get(obj, 0.0) + weight * offsets
        usable = {obj: o for obj, o in total.items() if np.any(o) and not eye_shapes.has_mirror(obj)}
        if not usable:
            continue
        for obj, offsets in usable.items():
            key = obj.data.shape_keys
            existing = [b.name for b in (key.key_blocks if key is not None else ())
                        if b != key.reference_key and expressions.slot_of(b.name) == slot]
            _put(rig, obj, existing[0] if existing else name, offsets)
        made.append((name, "the ARKit shapes added up: " + ", ".join(p for p, _w in parts), [o.name for o in usable]))
    return made
