// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Written by DaskToon's Engine Export; exporting again replaces it.

using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace DaskToon.Editor
{
    /// <summary>When Unity imports a model with a DaskToon <model>.rig.json beside it, adds a DaskToonSpringBone for
    /// each chain that sways at run time and a DaskToonSpringCollider on each collider bone (anime rig spec 9.5).</summary>
    public class DaskToonRigImporter : AssetPostprocessor
    {
        [Serializable]
        class ChainData
        {
            public string part;
            public string[] bones;
            public float[] lengths;
            public float stiffness;
            public float gravity;
            public float drag;
            public float radius;
            public string unity;
        }

        [Serializable]
        class ColliderData
        {
            public string bone;
            public float radius;
            public float length;
        }

        [Serializable]
        class RigData
        {
            public int version;
            public ChainData[] chains;
            public ColliderData[] colliders;
        }

        public static string RigPath(string modelPath) => Path.ChangeExtension(modelPath, ".rig.json");

        void OnPostprocessModel(GameObject root)
        {
            var path = RigPath(assetPath).Replace('\\', '/');
            if (!File.Exists(path)) return;
            context.DependsOnSourceAsset(path);  // a new rig file imports the model again
            var data = JsonUtility.FromJson<RigData>(File.ReadAllText(path));
            if (data == null || data.version != 1)
            {
                Debug.LogWarning("DaskToon: " + path + " is not a rig file this version understands");
                return;
            }
            var byName = new Dictionary<string, Transform>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                if (!byName.ContainsKey(t.name)) byName[t.name] = t;
            }
            var colliders = new List<DaskToonSpringCollider>();
            foreach (var c in data.colliders ?? new ColliderData[0])
            {
                if (!byName.TryGetValue(c.bone, out var bone)) continue;
                var collider = bone.gameObject.AddComponent<DaskToonSpringCollider>();
                collider.radius = c.radius;
                collider.length = c.length;
                colliders.Add(collider);
            }
            foreach (var chain in data.chains ?? new ChainData[0])
            {
                if (chain.unity == "baked" || chain.bones == null) continue;
                var bones = new List<Transform>();
                foreach (var name in chain.bones)
                {
                    if (byName.TryGetValue(name, out var bone)) bones.Add(bone);
                }
                if (bones.Count == 0) continue;
                var spring = root.AddComponent<DaskToonSpringBone>();
                spring.bones = bones.ToArray();
                spring.lastLength = chain.lengths != null && chain.lengths.Length > 0
                    ? chain.lengths[chain.lengths.Length - 1] : 0.1f;
                spring.stiffness = chain.stiffness;
                spring.gravity = chain.gravity;
                spring.drag = chain.drag;
                spring.radius = chain.radius;
                spring.colliders = colliders.ToArray();
            }
        }
    }
}
