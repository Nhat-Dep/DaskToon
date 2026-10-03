// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Batchmode entry points for the DaskToon export tests. Results go to <project>/dt_result.json.

using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public static class DtJson
{
    public static string Write(object value)
    {
        var sb = new StringBuilder();
        Append(sb, value);
        return sb.ToString();
    }

    static void Append(StringBuilder sb, object value)
    {
        switch (value)
        {
            case null: sb.Append("null"); break;
            case string s: AppendString(sb, s); break;
            case bool b: sb.Append(b ? "true" : "false"); break;
            case float f: sb.Append(f.ToString("R", CultureInfo.InvariantCulture)); break;
            case double d: sb.Append(d.ToString("R", CultureInfo.InvariantCulture)); break;
            case int i: sb.Append(i.ToString(CultureInfo.InvariantCulture)); break;
            case IDictionary dict:
                sb.Append('{');
                var first = true;
                foreach (DictionaryEntry e in dict)
                {
                    if (!first) sb.Append(',');
                    first = false;
                    AppendString(sb, e.Key.ToString());
                    sb.Append(':');
                    Append(sb, e.Value);
                }
                sb.Append('}');
                break;
            case IEnumerable list:
                sb.Append('[');
                var firstItem = true;
                foreach (var item in list)
                {
                    if (!firstItem) sb.Append(',');
                    firstItem = false;
                    Append(sb, item);
                }
                sb.Append(']');
                break;
            default: AppendString(sb, value.ToString()); break;
        }
    }

    static void AppendString(StringBuilder sb, string s)
    {
        sb.Append('"');
        foreach (var c in s)
        {
            if (c == '"' || c == '\\') sb.Append('\\').Append(c);
            else if (c < ' ') sb.Append("\\u").Append(((int)c).ToString("x4"));
            else sb.Append(c);
        }
        sb.Append('"');
    }
}

public static class DaskToonTests
{
    public static string ProjectDir => Directory.GetCurrentDirectory();
    public static string ArgsPath => Path.Combine(ProjectDir, "dt_args.json");

    public static void Run(Func<Dictionary<string, object>> body)
    {
        Dictionary<string, object> result;
        int code = 0;
        try
        {
            result = body();
            if (!result.ContainsKey("ok")) result["ok"] = true;
        }
        catch (Exception e)
        {
            result = new Dictionary<string, object> { { "ok", false }, { "error", e.ToString() } };
            code = 1;
        }
        File.WriteAllText(Path.Combine(ProjectDir, "dt_result.json"), DtJson.Write(result));
        EditorApplication.Exit(code);
    }

    public static Texture2D RenderCamera(Camera cam, int width, int height)
    {
        var rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGBFloat, RenderTextureReadWrite.Linear);
        rt.antiAliasing = 1;
        rt.Create();
        var request = new UniversalRenderPipeline.SingleCameraRequest { destination = rt };
        if (RenderPipeline.SupportsRenderRequest(cam, request))
        {
            RenderPipeline.SubmitRenderRequest(cam, request);
        }
        else
        {
            cam.targetTexture = rt;
            cam.Render();
            cam.targetTexture = null;
        }
        var previous = RenderTexture.active;
        RenderTexture.active = rt;
        var tex = new Texture2D(width, height, TextureFormat.RGBAFloat, false, true);
        tex.ReadPixels(new Rect(0, 0, width, height), 0, 0);
        tex.Apply();
        RenderTexture.active = previous;
        rt.Release();
        return tex;
    }

    public static Camera NewCamera()
    {
        var cam = new GameObject("DT_Camera").AddComponent<Camera>();
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = Color.black;
        cam.allowMSAA = false;
        cam.allowHDR = true;
        var data = cam.GetUniversalAdditionalCameraData();
        data.renderPostProcessing = false;
        data.antialiasing = AntialiasingMode.None;
        return cam;
    }

    public static void Setup() => Run(() =>
    {
        PlayerSettings.colorSpace = ColorSpace.Linear;
        var rendererData = ScriptableObject.CreateInstance<UniversalRendererData>();
        AssetDatabase.CreateAsset(rendererData, "Assets/DaskToonTestRenderer.asset");
        var asset = UniversalRenderPipelineAsset.Create(rendererData);
        asset.supportsHDR = true;
        AssetDatabase.CreateAsset(asset, "Assets/DaskToonTestURP.asset");
        GraphicsSettings.defaultRenderPipeline = asset;
        var current = QualitySettings.GetQualityLevel();
        for (var i = 0; i < QualitySettings.names.Length; i++)
        {
            QualitySettings.SetQualityLevel(i, false);
            QualitySettings.renderPipeline = asset;
        }
        QualitySettings.SetQualityLevel(current, false);
        AssetDatabase.SaveAssets();
        return new Dictionary<string, object> { { "colorSpace", PlayerSettings.colorSpace.ToString() } };
    });

    public static void Smoke() => Run(() =>
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        var mat = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
        mat.SetColor("_BaseColor", new Color(0.25f, 0.5f, 0.75f, 1f));
        sphere.GetComponent<MeshRenderer>().sharedMaterial = mat;
        var cam = NewCamera();
        cam.orthographic = true;
        cam.orthographicSize = 1.5f;
        cam.transform.position = new Vector3(0f, 0f, -5f);
        var tex = RenderCamera(cam, 64, 64);
        var c = tex.GetPixel(32, 32);
        return new Dictionary<string, object>
        {
            { "colorSpace", PlayerSettings.colorSpace.ToString() },
            { "urp", GraphicsSettings.defaultRenderPipeline is UniversalRenderPipelineAsset },
            { "center", new List<object> { c.r, c.g, c.b } },
        };
    });
}
