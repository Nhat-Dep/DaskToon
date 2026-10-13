// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Written by DaskToon's Engine Export; exporting again replaces it.

using UnityEngine;

namespace DaskToon
{
    /// <summary>A 2D mouth (anime rig spec 10.3): the material shows one cell of its atlas, rows x columns from the
    /// top left. The cell comes from the bone MouthCell, whose Y scale is the cell + 1 in the exported animation (FBX
    /// carries no custom property animation). The UVs move through the "UV Transform" of DaskToon's shaders, set per
    /// material slot with a MaterialPropertyBlock. DaskToon's importer fills the fields from the rig file.</summary>
    public class DaskToonMouthAtlas : MonoBehaviour
    {
        static readonly int UVTransformId = Shader.PropertyToID("_DT_UVTransform");

        public Transform cellBone;
        public Renderer target;
        public int materialIndex;
        public int rows = 2;
        public int columns = 4;

        MaterialPropertyBlock block;

        /// <summary>The cell shown now.</summary>
        public int Cell()
        {
            if (cellBone == null) return 0;
            return Mathf.Clamp(Mathf.RoundToInt(cellBone.localScale.y - 1f), 0, Mathf.Max(rows * columns - 1, 0));
        }

        /// <summary>(scale u, scale v, offset u, offset v) placing the mouth's 0 to 1 UVs in the cell.</summary>
        public Vector4 UVTransform()
        {
            int cell = Cell(), col = cell % columns, row = cell / columns;
            return new Vector4(1f / columns, 1f / rows, (float)col / columns, (float)(rows - 1 - row) / rows);
        }

        void LateUpdate()
        {
            if (target == null || rows < 1 || columns < 1) return;
            if (block == null) block = new MaterialPropertyBlock();
            target.GetPropertyBlock(block, materialIndex);
            block.SetVector(UVTransformId, UVTransform());
            target.SetPropertyBlock(block, materialIndex);
        }
    }
}
