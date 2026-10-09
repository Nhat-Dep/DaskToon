# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Chains of the anime rig as plain maths: geodesic distance, hair lock joints and weights, skirt strips (spec 6.3,
6.4)."""

import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_rig import chains  # noqa: E402


def ribbon(path, width=0.04):
    """Points and edges of a ribbon two vertices wide along `path` (list of xyz), offset along X."""
    points, edges = [], []
    for i, (x, y, z) in enumerate(path):
        points += [(x - width / 2, y, z), (x + width / 2, y, z)]
        edges.append((2 * i, 2 * i + 1))
        if i:
            edges += [(2 * i - 2, 2 * i), (2 * i - 1, 2 * i + 1), (2 * i - 2, 2 * i + 1)]
    return np.array(points, float), np.array(edges, np.int64)


def straight(rings=20, top=1.0, bottom=0.5):
    return ribbon([(0.0, 0.0, top + (bottom - top) * r / rings) for r in range(rings + 1)])


def cone(rings=6, segments=16, top=0.5, bottom=0.2, r_top=0.1, r_bottom=0.2, start=0.0, sweep=2 * math.pi):
    points = []
    for r in range(rings + 1):
        t = r / rings
        radius = r_top + (r_bottom - r_top) * t
        for s in range(segments):
            a = start + sweep * s / segments
            points.append((radius * math.cos(a), radius * math.sin(a), top + (bottom - top) * t))
    return np.array(points, float)


class BasicsTest(unittest.TestCase):
    def test_segment_distance(self):
        points = np.array([(0.0, 0.0, 0.5), (1.0, 0.0, 0.5), (0.0, 0.0, 2.0)])
        d = chains.segment_distance(points, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        np.testing.assert_allclose(d, [0.0, 1.0, 1.0])

    def test_components(self):
        found = chains.components(5, np.array([(0, 1), (3, 4)]))
        self.assertEqual([c.tolist() for c in found], [[0, 1], [2], [3, 4]])

    def test_geodesic_walks_the_edges(self):
        points = np.array([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (5.0, 5.0, 0.0)])
        d = chains.geodesic(points, np.array([(0, 1), (1, 2)]), [0])
        np.testing.assert_allclose(d[:3], [0.0, 1.0, 2.0])
        self.assertTrue(math.isinf(d[3]))

    def test_tent_rows_sum_to_one_and_peak_at_their_bone(self):
        w = chains.tent(np.array([0.0, 0.5, 1.0, 2.5, 4.0, 5.0]), 4)
        np.testing.assert_allclose(w.sum(axis=1), 1.0)
        np.testing.assert_allclose(w[0], [1, 0, 0, 0, 0])
        np.testing.assert_allclose(w[1], [0.5, 0.5, 0, 0, 0])
        np.testing.assert_allclose(w[3], [0, 0, 0.5, 0.5, 0])
        np.testing.assert_allclose(w[4], [0, 0, 0, 0, 1])
        np.testing.assert_allclose(w[5], [0, 0, 0, 0, 1])


class HairTest(unittest.TestCase):
    HEAD = ((0.0, 0.0, 1.0), (0.0, 0.0, 1.3))

    def test_straight_lock(self):
        points, edges = straight()
        chain = chains.hair_chain(points, edges, *self.HEAD, 4)
        self.assertEqual(chain.joints.shape, (5, 3))
        self.assertTrue(np.all(np.diff(chain.joints[:, 2]) < 0.0))
        self.assertTrue(0.9 <= chain.joints[0, 2] <= 1.0, chain.joints[0])
        self.assertLess(chain.joints[4, 2], 0.53)
        np.testing.assert_allclose(chain.joints[:, 0], 0.0, atol=1e-9)
        np.testing.assert_allclose(chain.weights.sum(axis=1), 1.0)
        np.testing.assert_allclose(chain.weights[0], [1, 0, 0, 0, 0])
        self.assertEqual(int(np.argmax(chain.weights[-1])), 4)

    def test_curved_lock_follows_the_curve(self):
        arc = [(0.0, 0.3 * math.sin(a), 1.0 - 0.3 + 0.3 * math.cos(a))
               for a in np.linspace(0.0, math.pi / 2, 21)]
        points, edges = ribbon(arc, width=0.02)
        chain = chains.hair_chain(points, edges, *self.HEAD, 4)
        centre = np.array([0.0, 0.0, 0.7])
        radii = np.linalg.norm(chain.joints[:, 1:] - centre[1:], axis=1)
        np.testing.assert_allclose(radii, 0.3, atol=0.01)
        self.assertGreater(chain.joints[4, 1], 0.29)

    def test_short_wide_piece_is_rigid(self):
        grid = [(x, 0.0, z) for z in np.linspace(1.0, 0.9, 5) for x in np.linspace(-0.05, 0.05, 5)]
        points = np.array(grid, float)
        edges = [(r * 5 + c, r * 5 + c + 1) for r in range(5) for c in range(4)]
        edges += [(r * 5 + c, (r + 1) * 5 + c) for r in range(4) for c in range(5)]
        self.assertIsNone(chains.hair_chain(points, np.array(edges), *self.HEAD, 4))

    def test_too_few_vertices(self):
        points = np.array([(0.0, 0.0, 1.0), (0.0, 0.0, 0.5), (0.0, 0.0, 0.2)])
        self.assertIsNone(chains.hair_chain(points, np.array([(0, 1), (1, 2)]), *self.HEAD, 4))


class SkirtTest(unittest.TestCase):
    def test_full_skirt(self):
        points = cone()
        skirt = chains.skirt_chains(points, 3, 8)
        self.assertEqual(len(skirt.strips), 8)
        self.assertTrue(all(s is not None for s in skirt.strips))
        front = skirt.strips[0]
        self.assertAlmostEqual(front[0, 0], 0.0, places=6)
        self.assertLess(front[0, 1], 0.0)
        self.assertAlmostEqual(front[0, 2], 0.5, places=6)
        self.assertAlmostEqual(front[3, 2], 0.2, places=6)
        radii = np.linalg.norm(front[:, :2], axis=1)
        self.assertTrue(np.all(np.diff(radii) > 0.0))
        self.assertAlmostEqual(radii[0], 0.1, delta=0.01)
        self.assertAlmostEqual(radii[3], 0.2, delta=0.01)
        left = skirt.strips[2]  # strip 2 of 8 is 90 degrees counter-clockwise from the front: +X, the left side
        self.assertGreater(left[1, 0], 0.1)
        self.assertEqual(skirt.weights.shape, (len(points), 1 + 8 * 3))
        np.testing.assert_allclose(skirt.weights.sum(axis=1), 1.0)
        bottom_left = int(np.argmin(np.linalg.norm(points - (0.2, 0.0, 0.2), axis=1)))
        self.assertAlmostEqual(skirt.weights[bottom_left, 1 + 2 * 3 + 2], 1.0, places=6)
        top = int(np.argmin(np.linalg.norm(points - (0.1, 0.0, 0.5), axis=1)))
        self.assertAlmostEqual(skirt.weights[top, 0], 1.0, places=6)

    def test_front_panel_only(self):
        points = cone(start=-math.pi, sweep=math.pi * 15 / 16)
        skirt = chains.skirt_chains(points, 3, 8)
        self.assertIsNotNone(skirt.strips[0])
        self.assertIsNone(skirt.strips[4])  # the back
        np.testing.assert_allclose(skirt.weights[:, 1 + 4 * 3:1 + 5 * 3], 0.0)
        np.testing.assert_allclose(skirt.weights.sum(axis=1), 1.0)


if __name__ == "__main__":
    tu.run_tests()
