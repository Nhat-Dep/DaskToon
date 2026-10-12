// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Checks the clips of a character in Unity (clips spec 6): the model's avatar is Humanoid (DaskToon's importer makes it),
// and each <Model>@<Clip>.fbx imports as one AnimationClip with the clip's name, Loop and length, a Humanoid motion,
// and its blend shape curves.

using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

[System.Serializable]
public class DtClipArgs
{
    public string model;
    public string[] files;
}

public static class DaskToonClipTests
{
    public static void CheckClips() => DaskToonTests.Run(() =>
    {
        var args = JsonUtility.FromJson<DtClipArgs>(File.ReadAllText(DaskToonTests.ArgsPath));
        AssetDatabase.Refresh();
        EditorUtility.UnloadUnusedAssetsImmediate();  // the avatar as reimported, not an object loaded before
        var result = new Dictionary<string, object>();
        Avatar avatar = null;
        foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(args.model))
        {
            if (asset is Avatar found) avatar = found;
        }
        result["modelHuman"] = avatar != null && avatar.isValid && avatar.isHuman;
        result["modelAvatar"] = avatar == null ? "none" : avatar.name + " valid=" + avatar.isValid + " human=" + avatar.isHuman;
        result["modelType"] = ((ModelImporter)AssetImporter.GetAtPath(args.model)).animationType.ToString();
        foreach (var file in args.files)
        {
            var key = Path.GetFileNameWithoutExtension(file);
            var found = new List<AnimationClip>();
            foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(file))
            {
                if (asset is AnimationClip clip && !clip.name.StartsWith("__preview__")) found.Add(clip);
            }
            result[key + ".count"] = found.Count;
            if (found.Count == 0) continue;
            var first = found[0];
            result[key + ".name"] = first.name;
            result[key + ".loop"] = first.isLooping;
            result[key + ".length"] = first.length;
            result[key + ".human"] = first.humanMotion;
            var blendShape = false;
            var constant = true;
            var hold = -1f;
            foreach (var binding in AnimationUtility.GetCurveBindings(first))
            {
                var curve = AnimationUtility.GetEditorCurve(first, binding);
                for (var i = 0; i < curve.length; i++)
                {
                    constant &= AnimationUtility.GetKeyLeftTangentMode(curve, i) == AnimationUtility.TangentMode.Constant
                                && AnimationUtility.GetKeyRightTangentMode(curve, i) == AnimationUtility.TangentMode.Constant;
                }
                if (!binding.propertyName.StartsWith("blendShape.")) continue;
                blendShape = true;
                // Anime timing (spec 5): halfway between the 2nd and 3rd frame the value is still the 2nd frame's.
                var frame = 1f / first.frameRate;
                hold = Mathf.Abs(curve.Evaluate(1.5f * frame) - curve.Evaluate(frame));
            }
            result[key + ".blendShape"] = blendShape;
            result[key + ".constant"] = constant;
            result[key + ".hold"] = hold;
        }
        return result;
    });
}
