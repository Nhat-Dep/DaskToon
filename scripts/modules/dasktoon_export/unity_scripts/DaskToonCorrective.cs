// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Written by DaskToon's Engine Export; exporting again replaces it.

using System;
using UnityEngine;

namespace DaskToon
{
    /// <summary>Bend fixes (DaskToon's docs/superpowers/specs/2026-10-20-dasktoon-bend-fixes-design.md): knees,
    /// elbows, hips and shoulders have blend shapes that keep the joint round as it bends; this sets their weights from
    /// the pose every frame, after the animation, as DaskToon's drivers do. The child bone's swing from rest, seen from
    /// its parent, splits into the bend along the fix's arc and the swing off it; the weight rises from start to angle,
    /// falls back to 0 at end when a deeper fix follows (end 0: it stays), and fades over reach off the arc.
    /// DaskToon's importer fills the fixes from the rig file.</summary>
    public class DaskToonCorrective : MonoBehaviour
    {
        [Serializable]
        public class Fix
        {
            public string shape;
            public Transform parent;
            public Transform child;
            /// <summary>The child's direction at rest (along the bone), in the parent's frame.</summary>
            public Vector3 rest = Vector3.up;
            /// <summary>The axis the fix turns the child about (rest x target), in the parent's frame.</summary>
            public Vector3 along = Vector3.right;
            /// <summary>rest x along: the swing off the fix's arc.</summary>
            public Vector3 across = Vector3.forward;
            public float angle = Mathf.PI / 2f;
            /// <summary>The bend where the weight starts to rise (0, or the fix before on the same arc).</summary>
            public float start;
            /// <summary>The bend where it is back to 0 (the next fix on the arc); 0: it stays at full past angle.</summary>
            public float end;
            /// <summary>The swing off the arc over which it fades (0: angle).</summary>
            public float reach;
            public SkinnedMeshRenderer[] renderers = new SkinnedMeshRenderer[0];
            public int[] indices = new int[0];
        }

        public Fix[] fixes = new Fix[0];

        /// <summary>The weight (0 to 1) for the child's direction `now` (the parent's frame).</summary>
        public static float Weight(Fix fix, Vector3 now)
        {
            var normal = Vector3.Cross(fix.rest, now);
            if (normal.sqrMagnitude < 1e-12f || fix.angle <= 0f) return 0f;
            var turn = Vector3.Angle(fix.rest, now) * Mathf.Deg2Rad;
            var swing = Mathf.Sin(turn / 2f) * normal.normalized;  // the swing quaternion's vector part
            var bend = 2f * Mathf.Asin(Mathf.Clamp(Vector3.Dot(swing, fix.along), -1f, 1f));
            var off = 2f * Mathf.Asin(Mathf.Clamp(Vector3.Dot(swing, fix.across), -1f, 1f));
            var rise = fix.angle > fix.start ? Mathf.Clamp01((bend - fix.start) / (fix.angle - fix.start)) : 1f;
            var fall = fix.end > fix.angle ? Mathf.Clamp01((fix.end - bend) / (fix.end - fix.angle)) : 1f;
            var reach = fix.reach > 0f ? fix.reach : fix.angle;
            return rise * fall * Mathf.Clamp01(1f - Mathf.Abs(off) / reach);
        }

        /// <summary>The weight of `fix` in the pose now.</summary>
        public static float WeightNow(Fix fix)
        {
            if (fix.parent == null || fix.child == null) return 0f;
            return Weight(fix, fix.parent.InverseTransformDirection(fix.child.up));  // Unity keeps a bone's +Y along it
        }

        /// <summary>Sets every fix's blend shape weight from the pose.</summary>
        public void Apply()
        {
            foreach (var fix in fixes)
            {
                var weight = WeightNow(fix) * 100f;
                for (var i = 0; i < fix.renderers.Length && i < fix.indices.Length; i++)
                {
                    if (fix.renderers[i] != null) fix.renderers[i].SetBlendShapeWeight(fix.indices[i], weight);
                }
            }
        }

        void LateUpdate() => Apply();
    }
}
