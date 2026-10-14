// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Checks the eyes and mouth of a character in Unity (anime rig spec 10, R3): the model gets a DaskToonFlatEye and a
// DaskToonMouthAtlas from its rig file; turning the eye slides the iris by the same offset as in DaskToon; the
// MouthCell bone's Y scale picks the atlas cell; the clip carries MouthCell's scale. DaskToon's scripts are reached by
// reflection, so this file compiles before an export has installed them.

using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

[Serializable]
public class DtFaceArgs
{
    public string model;
    public string clip;
    public float cellTime;
}

public static class DaskToonFaceTests
{
    static Transform Find(Transform root, string name)
    {
        foreach (var t in root.GetComponentsInChildren<Transform>(true))
        {
            if (t.name == name) return t;
        }
        return null;
    }

    static object Field(object obj, string name) => obj.GetType().GetField(name).GetValue(obj);
    static object Call(object obj, string name) => obj.GetType().GetMethod(name).Invoke(obj, null);
    static string NameOf(object value) => value is Object o && o != null ? o.name : "";

    public static void CheckFace() => DaskToonTests.Run(() =>
    {
        var args = JsonUtility.FromJson<DtFaceArgs>(File.ReadAllText(DaskToonTests.ArgsPath));
        AssetDatabase.Refresh();
        EditorUtility.UnloadUnusedAssetsImmediate();
        var result = new Dictionary<string, object>();
        var eyeType = Type.GetType("DaskToon.DaskToonFlatEye, Assembly-CSharp");
        var mouthType = Type.GetType("DaskToon.DaskToonMouthAtlas, Assembly-CSharp");
        var root = Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(args.model));
        var eye = eyeType != null ? root.GetComponentInChildren(eyeType, true) : null;
        result["flatEye"] = eye != null;
        if (eye != null)
        {
            var bone = (Transform)Field(eye, "eye");
            result["flatEye.eye"] = NameOf(bone);
            result["flatEye.target"] = NameOf(Field(eye, "target"));
            result["flatEye.range"] = (float)Field(eye, "range");
            // Turn the eye toward the character's left (from its right eye to its left eye), then up.
            var left = (Find(root.transform, "LeftEye").position - Find(root.transform, "RightEye").position).normalized;
            var restRotation = bone.rotation;
            var gaze = restRotation * Vector3.up;  // Unity keeps a Blender bone's +Y along the bone
            Vector2 Turned(Vector3 toward, float degrees)
            {
                var turned = Vector3.RotateTowards(gaze, toward, degrees * Mathf.Deg2Rad, 0f);
                bone.rotation = Quaternion.FromToRotation(gaze, turned) * restRotation;
                return (Vector2)Call(eye, "Offset");
            }
            var toLeft = Turned(left, 20f);
            result["flatEye.left"] = toLeft.x;
            result["flatEye.leftY"] = toLeft.y;
            var up = Turned(Vector3.up, 10f);
            result["flatEye.up"] = up.y;
            result["flatEye.upX"] = up.x;
            result["flatEye.rest"] = Turned(gaze, 0f).magnitude;
        }
        var mouth = mouthType != null ? root.GetComponentInChildren(mouthType, true) : null;
        result["mouth"] = mouth != null;
        if (mouth != null)
        {
            var cellBone = (Transform)Field(mouth, "cellBone");
            result["mouth.bone"] = NameOf(cellBone);
            result["mouth.target"] = NameOf(Field(mouth, "target"));
            result["mouth.rows"] = (int)Field(mouth, "rows");
            result["mouth.columns"] = (int)Field(mouth, "columns");
            result["mouth.rest"] = (int)Call(mouth, "Cell");
            cellBone.localScale = new Vector3(1f, 4f, 1f);
            result["mouth.cell"] = (int)Call(mouth, "Cell");
            var uv = (Vector4)Call(mouth, "UVTransform");
            result["mouth.uv"] = new float[] { uv.x, uv.y, uv.z, uv.w };
        }
        Object.DestroyImmediate(root);
        AnimationClip clip = null;
        foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(args.clip))
        {
            if (asset is AnimationClip found && !found.name.StartsWith("__preview__")) clip = found;
        }
        result["clip"] = clip != null;
        if (clip != null)
        {
            foreach (var binding in AnimationUtility.GetCurveBindings(clip))
            {
                if (!binding.path.EndsWith("MouthCell") || binding.propertyName != "m_LocalScale.y") continue;
                result["clip.cellCurve"] = true;
                result["clip.cellValue"] = AnimationUtility.GetEditorCurve(clip, binding).Evaluate(args.cellTime);
            }
        }
        return result;
    });
}
