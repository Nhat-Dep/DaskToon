// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Checks an exported FBX after Unity imported it: material remap, blend shapes, axes, and that DT_OutlineN decodes
// with Unity's own tangent frame into the smoothed normal DaskToon computed (spec 8, Unity step 3).

using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

[Serializable]
public class DtExpectedNormal
{
    public float[] p;
    public float[] n;
}

[Serializable]
public class DtModelArgs
{
    public string model;
    public string mesh;
    public int outlineUV;
    public DtExpectedNormal[] normals;
}

public static class DaskToonModelTests
{
    static Vector3 V(float[] a) => new Vector3(a[0], a[1], a[2]);

    static DtExpectedNormal Nearest(DtExpectedNormal[] list, Vector3 p)
    {
        DtExpectedNormal best = null;
        var bestDistance = 1e-6f;
        foreach (var e in list)
        {
            var d = (V(e.p) - p).sqrMagnitude;
            if (d < bestDistance)
            {
                bestDistance = d;
                best = e;
            }
        }
        return best;
    }

    static Vector3 OctDecode(Vector2 e)
    {
        var n = new Vector3(e.x, e.y, 1f - Mathf.Abs(e.x) - Mathf.Abs(e.y));
        var t = Mathf.Max(-n.z, 0f);
        n.x += n.x >= 0f ? -t : t;
        n.y += n.y >= 0f ? -t : t;
        return n.normalized;
    }

    public static void CheckModel() => DaskToonTests.Run(() =>
    {
        var args = JsonUtility.FromJson<DtModelArgs>(File.ReadAllText(DaskToonTests.ArgsPath));
        AssetDatabase.Refresh();
        var result = new Dictionary<string, object>();
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(args.model);
        result["imported"] = prefab != null;
        if (prefab == null) return result;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        var materials = new Dictionary<string, object>();
        foreach (var r in go.GetComponentsInChildren<Renderer>(true))
        foreach (var m in r.sharedMaterials)
        {
            if (m != null) materials[m.name] = AssetDatabase.GetAssetPath(m);
        }
        result["materials"] = materials;

        Mesh mesh = null;
        Transform owner = null;
        foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>(true))
        {
            if (smr.name == args.mesh) { mesh = smr.sharedMesh; owner = smr.transform; }
        }
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>(true))
        {
            if (mesh == null && mf.name == args.mesh) { mesh = mf.sharedMesh; owner = mf.transform; }
        }
        // An FBX with a single object is collapsed onto the prefab root, which is named after the file.
        var renderers = go.GetComponentsInChildren<Renderer>(true);
        if (mesh == null && renderers.Length == 1)
        {
            owner = renderers[0].transform;
            var skinned = renderers[0] as SkinnedMeshRenderer;
            mesh = skinned != null ? skinned.sharedMesh : renderers[0].GetComponent<MeshFilter>()?.sharedMesh;
        }
        result["meshFound"] = mesh != null;
        if (mesh == null) return result;
        result["blendShapes"] = mesh.blendShapeCount;
        var channels = new List<object>();
        for (var i = 0; i < 8; i++)
        {
            if (mesh.HasVertexAttribute(VertexAttribute.TexCoord0 + i)) channels.Add(i);
        }
        result["uvChannels"] = channels;

        var toWorld = owner.localToWorldMatrix;
        var mirror = toWorld.determinant < 0f ? -1f : 1f;
        var vertices = mesh.vertices;
        var normals = mesh.normals;
        var tangents = mesh.tangents;
        var uvs = new List<Vector2>();
        mesh.GetUVs(args.outlineUV, uvs);
        var maxAngle = 0f;
        var matched = 0;
        var top = float.MinValue;
        for (var i = 0; i < vertices.Length; i++)
        {
            var p = toWorld.MultiplyPoint3x4(vertices[i]);
            top = Mathf.Max(top, p.y);
            var expected = Nearest(args.normals, p);
            if (expected == null || uvs.Count != vertices.Length || tangents.Length != vertices.Length) continue;
            var n = toWorld.MultiplyVector(normals[i]).normalized;
            var t = toWorld.MultiplyVector(new Vector3(tangents[i].x, tangents[i].y, tangents[i].z)).normalized;
            var b = Vector3.Cross(n, t) * tangents[i].w * mirror;
            var e = OctDecode(uvs[i]);
            var decoded = (t * e.x + b * e.y + n * e.z).normalized;
            maxAngle = Mathf.Max(maxAngle, Vector3.Angle(decoded, V(expected.n)));
            matched++;
        }
        result["matched"] = matched;
        result["vertices"] = vertices.Length;
        result["maxNormalAngle"] = maxAngle;
        result["top"] = top;
        return result;
    });
}
