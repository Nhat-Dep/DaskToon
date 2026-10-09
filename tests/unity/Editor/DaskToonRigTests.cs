// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Checks the anime rig in Unity: the importer added DaskToon spring bones and colliders from <model>.rig.json, chain
// bones sit along their parent's +Y, 20 steps of the C# spring bone land where DaskToon's spring.py does, a paused step
// (dt 0) moves nothing, and a rig file added after its model imports the model again.
// The DaskToon scripts are reached by reflection, so this file compiles before any export installed them.

using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

[Serializable]
public class DtRigArgs
{
    public string model;
    public string chainRoot;
    public int steps;
    public float dt;
    public float[] expected;
}

public static class DaskToonRigTests
{
    public static void CheckRig() => DaskToonTests.Run(() =>
    {
        var args = JsonUtility.FromJson<DtRigArgs>(File.ReadAllText(DaskToonTests.ArgsPath));
        AssetDatabase.Refresh();
        var result = new Dictionary<string, object>();
        var springType = Type.GetType("DaskToon.DaskToonSpringBone, Assembly-CSharp");
        var colliderType = Type.GetType("DaskToon.DaskToonSpringCollider, Assembly-CSharp");
        result["scripts"] = springType != null && colliderType != null;
        if (springType == null || colliderType == null) return result;
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(args.model);
        result["imported"] = prefab != null;
        if (prefab == null) return result;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        var springs = go.GetComponents(springType);
        result["springs"] = springs.Length;
        result["colliders"] = go.GetComponentsInChildren(colliderType, true).Length;
        var bonesField = springType.GetField("bones");
        Component chain = null;
        foreach (var s in springs)
        {
            var bones = (Transform[])bonesField.GetValue(s);
            if (bones.Length > 0 && bones[0].name == args.chainRoot) chain = s;
        }
        result["chainFound"] = chain != null;
        if (chain == null) return result;
        var chainBones = (Transform[])bonesField.GetValue(chain);
        var offAxis = 0f;
        for (var i = 0; i + 1 < chainBones.Length; i++)
        {
            var local = chainBones[i + 1].localPosition;
            offAxis = Mathf.Max(offAxis, new Vector2(local.x, local.z).magnitude);
        }
        result["offAxis"] = offAxis;
        springType.GetMethod("Setup").Invoke(chain, null);
        var step = springType.GetMethod("Step");
        for (var k = 0; k < args.steps; k++) step.Invoke(chain, new object[] { args.dt });
        var tail = springType.GetMethod("Tail");
        var maxError = 0f;
        for (var i = 0; i < chainBones.Length; i++)
        {
            var expected = new Vector3(args.expected[3 * i], args.expected[3 * i + 1], args.expected[3 * i + 2]);
            var actual = (Vector3)tail.Invoke(chain, new object[] { i });
            maxError = Mathf.Max(maxError, (actual - expected).magnitude);
        }
        result["maxError"] = maxError;
        var before = new Vector3[chainBones.Length];
        for (var i = 0; i < chainBones.Length; i++) before[i] = (Vector3)tail.Invoke(chain, new object[] { i });
        step.Invoke(chain, new object[] { 0f });
        var drift = 0f;
        for (var i = 0; i < chainBones.Length; i++)
        {
            drift = Mathf.Max(drift, ((Vector3)tail.Invoke(chain, new object[] { i }) - before[i]).magnitude);
        }
        result["pausedDrift"] = drift;
        UnityEngine.Object.DestroyImmediate(go);
        return result;
    });

    public static void CheckLateRig() => DaskToonTests.Run(() =>
    {
        var args = JsonUtility.FromJson<DtRigArgs>(File.ReadAllText(DaskToonTests.ArgsPath));
        AssetDatabase.Refresh();
        var result = new Dictionary<string, object>();
        var springType = Type.GetType("DaskToon.DaskToonSpringBone, Assembly-CSharp");
        result["scripts"] = springType != null;
        if (springType == null) return result;
        var rig = Path.ChangeExtension(args.model, ".rig.json");
        var text = File.ReadAllText(rig);
        AssetDatabase.DeleteAsset(rig);
        AssetDatabase.ImportAsset(args.model, ImportAssetOptions.ForceUpdate);
        result["withoutRig"] = Springs(args.model, springType);
        File.WriteAllText(rig, text);
        AssetDatabase.ImportAsset(rig);
        result["withRig"] = Springs(args.model, springType);
        return result;
    });

    static int Springs(string model, Type springType)
    {
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(model);
        return prefab == null ? -1 : prefab.GetComponents(springType).Length;
    }
}
