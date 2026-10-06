// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Written by DaskToon's Engine Export; exporting again replaces it.

using UnityEngine;

namespace DaskToon
{
    /// <summary>Sways one chain of bones the way DaskToon's Live Sway does (anime rig spec 9.3, dasktoon_rig/spring.py):
    /// every bone keeps its tail's current and previous position; a step adds the inertia, a pull towards the animated
    /// pose and gravity, keeps the bone's length and pushes the tail out of the colliders. A bone's tail is along its
    /// local +Y.</summary>
    [AddComponentMenu("DaskToon/Spring Bone")]
    public class DaskToonSpringBone : MonoBehaviour
    {
        public Transform[] bones = new Transform[0];
        public float lastLength = 0.1f;
        [Range(0f, 4f)] public float stiffness = 1f;
        [Range(0f, 2f)] public float gravity = 0.2f;
        [Range(0f, 1f)] public float drag = 0.4f;
        public float radius = 0.03f;
        public DaskToonSpringCollider[] colliders = new DaskToonSpringCollider[0];

        Vector3[] current = new Vector3[0];
        Vector3[] previous = new Vector3[0];
        Quaternion[] restLocal = new Quaternion[0];
        Quaternion[] written = new Quaternion[0];
        float[] lengths = new float[0];

        void OnEnable() => Setup();

        void LateUpdate() => Step(Time.deltaTime);

        /// <summary>Start again from the current pose, without sway.</summary>
        public void Setup()
        {
            var n = bones.Length;
            current = new Vector3[n];
            previous = new Vector3[n];
            restLocal = new Quaternion[n];
            written = new Quaternion[n];
            lengths = new float[n];
            for (var i = 0; i < n; i++)
            {
                var bone = bones[i];
                if (bone == null) continue;
                restLocal[i] = bone.localRotation;
                written[i] = bone.localRotation;
                lengths[i] = i + 1 < n && bones[i + 1] != null
                    ? Vector3.Distance(bone.position, bones[i + 1].position)
                    : lastLength * bone.lossyScale.y;
                current[i] = previous[i] = bone.position + bone.rotation * Vector3.up * lengths[i];
            }
        }

        public Vector3 Tail(int i) => current[i];

        /// <summary>One step of `dt` seconds.</summary>
        public void Step(float dt)
        {
            if (current.Length != bones.Length) Setup();
            for (var i = 0; i < bones.Length; i++)
            {
                var bone = bones[i];
                if (bone == null) continue;
                // A bone the animation did not touch still has the rotation written last step: its pose is the rest.
                var local = Quaternion.Angle(bone.localRotation, written[i]) < 1e-3f ? restLocal[i] : bone.localRotation;
                var parent = bone.parent != null ? bone.parent.rotation : Quaternion.identity;
                var posed = parent * local;
                var rest = posed * Vector3.up;
                var head = bone.position;
                var tail = current[i] + (current[i] - previous[i]) * (1f - drag) + rest * (stiffness * dt)
                           + Vector3.down * (gravity * dt);
                tail = head + (tail - head).normalized * lengths[i];
                foreach (var collider in colliders)
                {
                    if (collider == null) continue;
                    tail = PushOut(tail, collider.Head, collider.Tail, collider.Radius + radius);
                    tail = head + (tail - head).normalized * lengths[i];
                }
                previous[i] = current[i];
                current[i] = tail;
                bone.rotation = Quaternion.FromToRotation(rest, (tail - head).normalized) * posed;
                written[i] = bone.localRotation;
            }
        }

        static Vector3 PushOut(Vector3 point, Vector3 a, Vector3 b, float distance)
        {
            var axis = b - a;
            var length2 = axis.sqrMagnitude;
            var t = length2 < 1e-12f ? 0f : Mathf.Clamp01(Vector3.Dot(point - a, axis) / length2);
            var closest = a + axis * t;
            var away = point - closest;
            var gap = away.magnitude;
            if (gap >= distance || gap < 1e-9f) return point;
            return closest + away / gap * distance;
        }
    }
}
