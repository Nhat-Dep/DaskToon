# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Spring bones as plain maths (anime rig spec 9.3): inertia, stiffness, gravity, length, capsule colliders."""

import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import spring  # noqa: E402

# A bone's tail is along its local +Y. This rotation points +Y at +X (a horizontal bone).
TO_X = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])


def chain(count=1, length=0.1, direction=TO_X):
    return spring.Pose(np.zeros(3), direction, [np.eye(3)] * count, [length] * count)


def tail_of(rotation, head, length):
    return head + rotation[:, 1] * length


class SpringTest(unittest.TestCase):
    def test_from_to(self):
        for a, b in [((1, 0, 0), (0, 1, 0)), ((0, 0, 1), (0, 0, -1)), ((1, 0, 0), (1, 0, 0)), ((0.6, 0.8, 0), (0, 0, 1))]:
            a, b = np.array(a, float), np.array(b, float)
            r = spring.from_to(a, b)
            np.testing.assert_allclose(r @ a, b, atol=1e-9)
            np.testing.assert_allclose(r @ r.T, np.eye(3), atol=1e-9)
            self.assertAlmostEqual(np.linalg.det(r), 1.0, places=9)

    def test_reset_hangs_in_the_pose(self):
        pose = chain(2)
        state = spring.reset(pose)
        np.testing.assert_allclose(state.current, [(0.1, 0, 0), (0.2, 0, 0)], atol=1e-12)
        np.testing.assert_allclose(state.previous, state.current)
        rotations = spring.rotations(state, pose)
        np.testing.assert_allclose(rotations[1], TO_X, atol=1e-12)

    def test_gravity_pulls_down_and_keeps_the_length(self):
        pose = chain(2)
        state = spring.reset(pose)
        params = spring.Params(stiffness=0.0, gravity=1.0, drag=0.0, radius=0.0)
        for _ in range(10):
            rotations = spring.step(state, pose, params, [], 1.0 / 24.0)
        self.assertLess(state.current[0][2], -0.01)
        self.assertLess(state.current[1][2], state.current[0][2])
        self.assertAlmostEqual(np.linalg.norm(state.current[0]), 0.1, places=9)
        self.assertAlmostEqual(np.linalg.norm(state.current[1] - state.current[0]), 0.1, places=9)
        np.testing.assert_allclose(tail_of(rotations[0], np.zeros(3), 0.1), state.current[0], atol=1e-9)
        np.testing.assert_allclose(tail_of(rotations[1], state.current[0], 0.1), state.current[1], atol=1e-9)

    def test_stiffness_brings_it_back(self):
        pose = chain(1)
        state = spring.State([(0.0, 0.0, 0.1)])  # pushed up, straight above the head
        params = spring.Params(stiffness=4.0, gravity=0.0, drag=1.0, radius=0.0)
        start = math.acos(state.current[0][0] / 0.1)
        for _ in range(30):
            spring.step(state, pose, params, [], 1.0 / 24.0)
        self.assertLess(math.acos(min(1.0, state.current[0][0] / 0.1)), start / 4)

    def test_drag_one_keeps_no_inertia(self):
        pose = chain(1)
        state = spring.State([(0.1, 0.0, 0.0)], [(0.1, 0.0, -0.05)])  # was moving up fast
        spring.step(state, pose, spring.Params(stiffness=0.0, gravity=0.0, drag=1.0, radius=0.0), [], 1.0 / 24.0)
        np.testing.assert_allclose(state.current[0], (0.1, 0.0, 0.0), atol=1e-12)
        spring.step(state, pose, spring.Params(stiffness=0.0, gravity=0.0, drag=0.0, radius=0.0), [], 1.0 / 24.0)
        np.testing.assert_allclose(state.current[0], (0.1, 0.0, 0.0), atol=1e-12)

    def test_capsule_pushes_the_tail_out(self):
        pose = chain(1)
        state = spring.reset(pose)
        capsule = (np.array((0.1, -1.0, -0.02)), np.array((0.1, 1.0, -0.02)), 0.03)  # under the tail, along Y
        params = spring.Params(stiffness=0.0, gravity=2.0, drag=0.0, radius=0.01)
        for _ in range(20):
            spring.step(state, pose, params, [capsule], 1.0 / 24.0)
        tail = state.current[0]
        distance = math.hypot(tail[0] - 0.1, tail[2] + 0.02)
        self.assertGreaterEqual(distance, 0.04 - 1e-6)
        self.assertAlmostEqual(np.linalg.norm(tail), 0.1, places=9)

    def test_same_input_same_output(self):
        def run():
            pose = chain(3, direction=np.eye(3))
            state = spring.reset(pose)
            moving = spring.Pose(np.array((0.05, 0.0, 0.0)), np.eye(3), [np.eye(3)] * 3, [0.1] * 3)
            out = None
            for _ in range(12):
                out = spring.step(state, moving, spring.Params(), [], 1.0 / 30.0)
            return state.current, out
        a, b = run(), run()
        np.testing.assert_array_equal(a[0], b[0])
        for x, y in zip(a[1], b[1]):
            np.testing.assert_array_equal(x, y)

    def test_copy_is_independent(self):
        state = spring.reset(chain(1))
        other = state.copy()
        other.current[0][2] = 5.0
        self.assertEqual(state.current[0][2], 0.0)


if __name__ == "__main__":
    tu.run_tests()
