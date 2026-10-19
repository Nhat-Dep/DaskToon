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
    /// each chain that sways at run time and a DaskToonSpringCollider on each collider bone (anime rig spec 9.5), a
    /// DaskToonFlatEye for each flat eye and a DaskToonMouthAtlas for each 2D mouth (spec 10, rig file version 2), and
    /// one DaskToonCorrective with the bend fixes (docs/superpowers/specs/2026-10-20-dasktoon-bend-fixes-design.md).
    /// </summary>
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
        class FlatEyeData
        {
            public string @object;
            public string material;
            public int slot;
            public string side;
            public float range;
        }

        [Serializable]
        class MouthData
        {
            public string @object;
            public string material;
            public int slot;
            public int rows;
            public int columns;
            public string bone;
        }

        [Serializable]
        class CorrectiveData
        {
            public string shape;
            public string parent;
            public string child;
            public float[] target;  // in the character's frame: left, up, front
            public float angle;
        }

        [Serializable]
        class RigData
        {
            public int version;
            public ChainData[] chains;
            public ColliderData[] colliders;
            public FlatEyeData[] flatEyes;
            public MouthData[] mouths;
            public CorrectiveData[] correctives;
        }

        /// <summary>The slot of `renderer` whose material is named `material`, else `slot` (kept within the slots).
        /// </summary>
        static int MaterialIndex(Renderer renderer, string material, int slot)
        {
            var materials = renderer.sharedMaterials;
            for (var i = 0; i < materials.Length; i++)
            {
                if (materials[i] != null && materials[i].name == material) return i;
            }
            return Mathf.Clamp(slot, 0, Mathf.Max(materials.Length - 1, 0));
        }

        public static string RigPath(string modelPath) => Path.ChangeExtension(modelPath, ".rig.json");

        /// <summary>A rig file that arrives after its model (exported later, copied in) imports the model again, so the
        /// model gets its spring bones; a model imported in the same pass reads the file itself.</summary>
        static void OnPostprocessAllAssets(string[] importedAssets, string[] deletedAssets, string[] movedAssets,
                                           string[] movedFromAssetPaths)
        {
            var imported = new HashSet<string>(importedAssets);
            foreach (var path in importedAssets)
            {
                if (!path.EndsWith(".rig.json", StringComparison.OrdinalIgnoreCase)) continue;
                var model = path.Substring(0, path.Length - ".rig.json".Length) + ".fbx";
                if (File.Exists(model) && !imported.Contains(model)) AssetDatabase.ImportAsset(model);
            }
        }

        void OnPostprocessModel(GameObject root)
        {
            var path = RigPath(assetPath).Replace('\\', '/');
            if (!File.Exists(path)) return;
            context.DependsOnSourceAsset(path);  // a new rig file imports the model again
            var data = JsonUtility.FromJson<RigData>(File.ReadAllText(path));
            if (data == null || data.version < 1 || data.version > 2)
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
            AddFace(root, data, byName);
            AddCorrectives(root, data, byName);
        }

        /// <summary>One DaskToonCorrective with the fixes whose blend shape a SkinnedMeshRenderer of the model has. The
        /// target comes in the character's frame, built from the same bones as in DaskToon; Unity's axes are mirrored
        /// from Blender's, so the front is up x left here (left x up there).</summary>
        static void AddCorrectives(GameObject root, RigData data, Dictionary<string, Transform> byName)
        {
            if (data.correctives == null || data.correctives.Length == 0) return;
            if (!byName.TryGetValue("Hips", out var hips) || !byName.TryGetValue("Head", out var head)
                || !byName.TryGetValue("LeftUpperLeg", out var leftLeg)
                || !byName.TryGetValue("RightUpperLeg", out var rightLeg))
                return;
            var up = (head.position - hips.position).normalized;
            var left = Vector3.ProjectOnPlane(leftLeg.position - rightLeg.position, up).normalized;
            var front = Vector3.Cross(up, left);
            var renderers = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            var fixes = new List<DaskToonCorrective.Fix>();
            foreach (var c in data.correctives)
            {
                if (c.target == null || c.target.Length != 3) continue;
                if (!byName.TryGetValue(c.parent ?? "", out var parent) || !byName.TryGetValue(c.child ?? "", out var child))
                    continue;
                var world = (c.target[0] * left + c.target[1] * up + c.target[2] * front).normalized;
                var target = parent.InverseTransformDirection(world);
                var rest = parent.InverseTransformDirection(child.up).normalized;  // the model imports at rest
                var along = Vector3.Cross(rest, target);
                if (along.sqrMagnitude < 1e-12f) continue;
                along.Normalize();
                var found = new List<SkinnedMeshRenderer>();
                var indices = new List<int>();
                foreach (var renderer in renderers)
                {
                    var index = renderer.sharedMesh != null ? renderer.sharedMesh.GetBlendShapeIndex(c.shape) : -1;
                    if (index < 0) continue;
                    found.Add(renderer);
                    indices.Add(index);
                }
                if (found.Count == 0) continue;
                fixes.Add(new DaskToonCorrective.Fix
                {
                    shape = c.shape, parent = parent, child = child, rest = rest, along = along,
                    across = Vector3.Cross(rest, along), angle = Vector3.Angle(rest, target) * Mathf.Deg2Rad,
                    renderers = found.ToArray(), indices = indices.ToArray(),
                });
            }
            if (fixes.Count == 0) return;
            root.AddComponent<DaskToonCorrective>().fixes = fixes.ToArray();
        }

        static void AddFace(GameObject root, RigData data, Dictionary<string, Transform> byName)
        {
            foreach (var e in data.flatEyes ?? new FlatEyeData[0])
            {
                if (!byName.TryGetValue(e.@object, out var mesh) || !(mesh.GetComponent<Renderer>() is Renderer renderer))
                    continue;
                if (!byName.TryGetValue("LeftEye", out var leftEye) || !byName.TryGetValue("RightEye", out var rightEye))
                    continue;
                var bone = e.side == "RIGHT" ? rightEye : leftEye;
                var eye = mesh.gameObject.AddComponent<DaskToonFlatEye>();
                eye.eye = bone;
                eye.target = renderer;
                eye.materialIndex = MaterialIndex(renderer, e.material, e.slot);
                eye.range = e.range;
                eye.restLocalRotation = bone.localRotation;
                // The character's left (from its right eye to its left) and up, in the eye's rest frame: the same
                // directions DaskToon's drivers use, whatever axes the FBX import gave the bone.
                var rest = Quaternion.Inverse(bone.rotation);
                eye.left = (rest * (leftEye.position - rightEye.position)).normalized;
                eye.up = (rest * root.transform.up).normalized;
            }
            foreach (var m in data.mouths ?? new MouthData[0])
            {
                if (!byName.TryGetValue(m.@object, out var mesh) || !(mesh.GetComponent<Renderer>() is Renderer renderer))
                    continue;
                if (!byName.TryGetValue(m.bone ?? "", out var cellBone)) continue;
                var mouth = mesh.gameObject.AddComponent<DaskToonMouthAtlas>();
                mouth.cellBone = cellBone;
                mouth.target = renderer;
                mouth.materialIndex = MaterialIndex(renderer, m.material, m.slot);
                mouth.rows = Mathf.Max(m.rows, 1);
                mouth.columns = Mathf.Max(m.columns, 1);
            }
        }
    }
}
