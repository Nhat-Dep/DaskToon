// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Written by DaskToon's Engine Export; exporting again replaces it.

using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace DaskToon.Editor
{
    /// <summary>Makes the Humanoid avatar of a DaskToon model (anime rig spec 8, clips spec 6). Unity's own bone
    /// mapping leaves out bones of the DaskToon skeleton, so DaskToon writes such a model as Generic, marked
    /// "DaskToonHumanoid"; once it is imported, its human description is made from the imported hierarchy (the bones
    /// carry Unity's HumanBodyBones names) and it is imported again as Humanoid. Its clip files (model@clip.fbx, marked
    /// "DaskToonHumanoidClip") then copy that avatar.</summary>
    public class DaskToonAvatarImporter : AssetPostprocessor
    {
        public const string ModelMark = "DaskToonHumanoid";
        public const string ClipMark = "DaskToonHumanoidClip";
        static readonly Dictionary<string, HumanDescription> pending = new Dictionary<string, HumanDescription>();

        void OnPostprocessModel(GameObject root)
        {
            var importer = (ModelImporter)assetImporter;
            if (importer.userData != ModelMark || importer.animationType == ModelImporterAnimationType.Human) return;
            pending[assetPath] = Describe(root, importer.humanDescription);
        }

        /// <summary>`description` with the skeleton of `root` as imported (its rest pose) and every bone named after
        /// a HumanBodyBones value mapped to that human bone.</summary>
        public static HumanDescription Describe(GameObject root, HumanDescription description)
        {
            var skeleton = new List<SkeletonBone>();
            var names = new HashSet<string>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                skeleton.Add(new SkeletonBone
                {
                    name = t.name, position = t.localPosition, rotation = t.localRotation, scale = t.localScale
                });
                names.Add(t.name);
            }
            var human = new List<HumanBone>();
            for (var i = 0; i < HumanTrait.BoneCount; i++)
            {
                var bone = ((HumanBodyBones)i).ToString();
                if (!names.Contains(bone)) continue;
                var mapped = new HumanBone { boneName = bone, humanName = HumanTrait.BoneName[i] };
                mapped.limit.useDefaultValues = true;
                human.Add(mapped);
            }
            description.skeleton = skeleton.ToArray();
            description.human = human.ToArray();
            return description;
        }

        static void OnPostprocessAllAssets(string[] importedAssets, string[] deletedAssets, string[] movedAssets,
                                           string[] movedFromAssetPaths)
        {
            if (pending.Count == 0) return;
            foreach (var path in new List<string>(pending.Keys))
            {
                var description = pending[path];
                pending.Remove(path);
                if (!(AssetImporter.GetAtPath(path) is ModelImporter importer)) continue;
                importer.humanDescription = description;
                importer.animationType = ModelImporterAnimationType.Human;
                importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
                importer.autoGenerateAvatarMappingIfUnspecified = false;
                importer.SaveAndReimport();
                UseAvatarInClips(path);
            }
        }

        /// <summary>The clip files beside `modelPath` (model@clip.fbx, marked) copy its Humanoid avatar.</summary>
        static void UseAvatarInClips(string modelPath)
        {
            Avatar avatar = null;
            foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(modelPath))
            {
                if (asset is Avatar found) avatar = found;
            }
            if (avatar == null || !avatar.isHuman) return;
            var folder = Path.GetDirectoryName(modelPath);
            var prefix = Path.GetFileNameWithoutExtension(modelPath) + "@";
            foreach (var file in Directory.GetFiles(folder, prefix + "*.fbx"))
            {
                var path = file.Replace('\\', '/');
                if (!(AssetImporter.GetAtPath(path) is ModelImporter clip) || clip.userData != ClipMark) continue;
                clip.animationType = ModelImporterAnimationType.Human;
                clip.avatarSetup = ModelImporterAvatarSetup.CopyFromOther;
                clip.sourceAvatar = avatar;
                clip.SaveAndReimport();
            }
        }
    }
}
