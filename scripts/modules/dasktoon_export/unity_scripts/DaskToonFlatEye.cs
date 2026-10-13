// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Written by DaskToon's Engine Export; exporting again replaces it.

using UnityEngine;

namespace DaskToon
{
    /// <summary>A flat eye (anime rig spec 10.2): the iris drawn on the face slides on its UVs as its eye bone turns,
    /// by the same offset as in DaskToon: (-range * f.left, -range * f.up) for the eye looking along f. The UVs move
    /// through the "UV Transform" of DaskToon's shaders, set per material slot with a MaterialPropertyBlock.
    /// DaskToon's importer fills the fields from the rig file.</summary>
    public class DaskToonFlatEye : MonoBehaviour
    {
        static readonly int UVTransform = Shader.PropertyToID("_DT_UVTransform");

        public Transform eye;
        public Renderer target;
        public int materialIndex;
        public float range = 0.1f;
        /// <summary>The eye's rest rotation, relative to its parent.</summary>
        public Quaternion restLocalRotation = Quaternion.identity;
        /// <summary>The character's left and up, in the eye's rest frame.</summary>
        public Vector3 left = Vector3.right;
        public Vector3 up = Vector3.forward;

        MaterialPropertyBlock block;

        /// <summary>The UV offset for the eye's turn now.</summary>
        public Vector2 Offset()
        {
            var turn = Quaternion.Inverse(restLocalRotation) * eye.localRotation;
            var gaze = turn * Vector3.up;  // Unity keeps a Blender bone's +Y along the bone
            return new Vector2(-range * Vector3.Dot(gaze, left), -range * Vector3.Dot(gaze, up));
        }

        void LateUpdate()
        {
            if (eye == null || target == null) return;
            if (block == null) block = new MaterialPropertyBlock();
            target.GetPropertyBlock(block, materialIndex);
            var offset = Offset();
            block.SetVector(UVTransform, new Vector4(1f, 1f, offset.x, offset.y));
            target.SetPropertyBlock(block, materialIndex);
        }
    }
}
