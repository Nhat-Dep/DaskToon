// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Checks the bend fixes in Unity (docs/superpowers/specs/2026-10-20-dasktoon-bend-fixes-design.md): the model gets a
// DaskToonCorrective from its rig file, each fix's target points where it does in DaskToon (measured against the
// model's own bones), and a pose given as the child bone's direction gives the blend shape weight DaskToon's driver
// gives. DaskToon's scripts are reached by reflection, so this file compiles before an export has installed them.

using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

[Serializable]
public class DtFixPose
{
    public string shape;
    public string child;
    public float[] direction;  // in the character's frame: left, up, front
}

[Serializable]
public class DtFixArgs
{
    public string model;
    public DtFixPose[] poses;
}

public static class DaskToonCorrectiveTests
{
    static object Field(object obj, string name) => obj.GetType().GetField(name).GetValue(obj);

    public static void Check() => DaskToonTests.Run(() =>
    {
        var args = JsonUtility.FromJson<DtFixArgs>(File.ReadAllText(DaskToonTests.ArgsPath));
        AssetDatabase.Refresh();
        EditorUtility.UnloadUnusedAssetsImmediate();
        var result = new Dictionary<string, object>();
        var type = Type.GetType("DaskToon.DaskToonCorrective, Assembly-CSharp");
        var root = Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(args.model));
        var component = type != null ? root.GetComponent(type) : null;
        result["component"] = component != null;
        if (component == null)
        {
            Object.DestroyImmediate(root);
            return result;
        }
        var bones = new Dictionary<string, Transform>();
        foreach (var t in root.GetComponentsInChildren<Transform>(true))
        {
            if (!bones.ContainsKey(t.name)) bones[t.name] = t;
        }
        var up = (bones["Head"].position - bones["Hips"].position).normalized;
        var left = Vector3.ProjectOnPlane(bones["LeftUpperLeg"].position - bones["RightUpperLeg"].position, up).normalized;
        var front = Vector3.Cross(up, left);
        // The model's own front, from its foot: where the toes point.
        var toes = Vector3.ProjectOnPlane(bones["LeftToes"].position - bones["LeftFoot"].position, up).normalized;
        result["frontAlongToes"] = Vector3.Dot(front, toes);
        var weightNow = type.GetMethod("WeightNow");
        var byShape = new Dictionary<string, object>();
        var shapes = new List<string>();
        foreach (var fix in (Array)Field(component, "fixes"))
        {
            var shape = (string)Field(fix, "shape");
            shapes.Add(shape);
            byShape[shape] = fix;
            var parent = (Transform)Field(fix, "parent");
            var rest = (Vector3)Field(fix, "rest");
            var along = (Vector3)Field(fix, "along");
            var angle = (float)Field(fix, "angle");
            var target = parent.TransformDirection(Quaternion.AngleAxis(angle * Mathf.Rad2Deg, along) * rest);
            result[shape + ".angle"] = angle;
            result[shape + ".down"] = Vector3.Dot(target, -up);
            result[shape + ".front"] = Vector3.Dot(target, toes);
            result[shape + ".atRest"] = (float)weightNow.Invoke(null, new[] { fix });
            var names = new List<string>();
            foreach (var renderer in (SkinnedMeshRenderer[])Field(fix, "renderers")) names.Add(renderer.name);
            result[shape + ".renderers"] = string.Join(",", names);
        }
        result["shapes"] = shapes.ToArray();
        var apply = type.GetMethod("Apply");
        var weights = new List<float>();
        foreach (var pose in args.poses)
        {
            var child = bones[pose.child];
            var restRotation = child.rotation;
            var direction = (pose.direction[0] * left + pose.direction[1] * up + pose.direction[2] * front).normalized;
            child.rotation = Quaternion.FromToRotation(child.up, direction) * restRotation;
            apply.Invoke(component, null);
            var fix = byShape[pose.shape];
            var renderer = ((SkinnedMeshRenderer[])Field(fix, "renderers"))[0];
            weights.Add(renderer.GetBlendShapeWeight(((int[])Field(fix, "indices"))[0]) / 100f);
            child.rotation = restRotation;
        }
        result["weights"] = weights.ToArray();
        Object.DestroyImmediate(root);
        return result;
    });
}
