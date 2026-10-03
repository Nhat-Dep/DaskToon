// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Renders each exported test sphere under the light set-up DaskToon used, to linear float EXR files.

using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

[Serializable]
public class DtRenderCase
{
    public string name;
    public string obj;
    public float[] camPos;
}

[Serializable]
public class DtRenderArgs
{
    public string model;
    public DtRenderCase[] cases;
    public int resolution;
    public float orthoSize;
    public float[] camForward;
    public float[] camUp;
    public float[] lightDir;
    public float lightIntensity;
    public float[] lightColor;
    public float[] ambient;
    public string outDir;
}

public static class DaskToonRenderTests
{
    static Vector3 V(float[] a) => new Vector3(a[0], a[1], a[2]);
    static Color C(float[] a) => new Color(a[0], a[1], a[2], 1f);

    public static void RenderCases() => DaskToonTests.Run(() =>
    {
        var args = JsonUtility.FromJson<DtRenderArgs>(File.ReadAllText(DaskToonTests.ArgsPath));
        AssetDatabase.Refresh();
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        // Linear values from DaskToon; Unity linearises Color settings of a Linear project, hence .gamma.
        var ambient = C(args.ambient);
        RenderSettings.skybox = null;
        RenderSettings.ambientMode = AmbientMode.Flat;
        RenderSettings.ambientLight = ambient.gamma;
        var probe = new SphericalHarmonicsL2();
        probe.AddAmbientLight(ambient);
        RenderSettings.ambientProbe = probe;
        RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom;
        RenderSettings.customReflectionTexture = null;
        RenderSettings.fog = false;

        var sun = new GameObject("DT_Sun").AddComponent<Light>();
        sun.type = LightType.Directional;
        sun.intensity = args.lightIntensity;
        sun.color = C(args.lightColor).gamma;
        sun.shadows = LightShadows.None;
        sun.transform.rotation = Quaternion.LookRotation(-V(args.lightDir));

        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(args.model);
        if (prefab == null)
            return new Dictionary<string, object> { { "ok", false }, { "error", "model not imported: " + args.model } };
        var model = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        var cam = DaskToonTests.NewCamera();
        cam.orthographic = true;
        cam.orthographicSize = args.orthoSize;
        cam.nearClipPlane = 0.01f;
        cam.farClipPlane = 100f;
        Directory.CreateDirectory(args.outDir);
        var outputs = new Dictionary<string, object>();
        // Back-to-back render requests in batchmode reuse stale per-material data with the SRP Batcher on (URP's own Lit
        // shader shows it too), so the comparison renders without it.
        var pipeline = GraphicsSettings.defaultRenderPipeline as UniversalRenderPipelineAsset;
        var batcher = pipeline != null && pipeline.useSRPBatcher;
        if (pipeline != null) pipeline.useSRPBatcher = false;
        try
        {
            foreach (var c in args.cases)
            {
                foreach (var r in model.GetComponentsInChildren<Renderer>(true)) r.enabled = r.gameObject.name == c.obj;
                cam.transform.position = V(c.camPos);
                cam.transform.rotation = Quaternion.LookRotation(V(args.camForward), V(args.camUp));
                var tex = DaskToonTests.RenderCamera(cam, args.resolution, args.resolution);
                var path = Path.Combine(args.outDir, c.name + ".exr");
                File.WriteAllBytes(path, tex.EncodeToEXR(Texture2D.EXRFlags.OutputAsFloat));
                outputs[c.name] = path;
            }
        }
        finally
        {
            if (pipeline != null) pipeline.useSRPBatcher = batcher;
        }
        return new Dictionary<string, object> { { "outputs", outputs } };
    });
}
