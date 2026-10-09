// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Written by DaskToon's Engine Export; exporting again replaces it.

using UnityEngine;

namespace DaskToon
{
    /// <summary>A capsule along a bone, from the bone along its local +Y for `length`, that spring bones keep out of
    /// (DaskToon anime rig).</summary>
    [AddComponentMenu("DaskToon/Spring Collider")]
    [DisallowMultipleComponent]
    public class DaskToonSpringCollider : MonoBehaviour
    {
        public float radius = 0.05f;
        public float length = 0.1f;

        float Scale => transform.lossyScale.y;
        public float Radius => radius * Scale;
        public Vector3 Head => transform.position;
        public Vector3 Tail => transform.position + transform.rotation * Vector3.up * (length * Scale);

        void OnDrawGizmosSelected()
        {
            Gizmos.color = Color.cyan;
            Gizmos.DrawWireSphere(Head, Radius);
            Gizmos.DrawWireSphere(Tail, Radius);
            Gizmos.DrawLine(Head, Tail);
        }
    }
}
