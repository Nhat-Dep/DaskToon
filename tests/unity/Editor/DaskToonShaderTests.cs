// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Compiles every pass of the DaskToon shaders for several keyword sets (D3D11 and Vulkan).

using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Rendering;
using UnityEngine;
using UnityEngine.Rendering;

public static class DaskToonShaderTests
{
    static readonly string[] Shaders = { "AnimeBSDF", "AnimeCel", "AnimeEye", "DaskCel" };

    static readonly string[][] KeywordSets =
    {
        new string[0],
        new[] { "_DT_RAMP", "_DT_AMBIENT", "_DT_LIGHT", "_DT_AO", "_DT_RIM", "_DT_GRADE", "_DT_OUTLINE", "_DT_ANGEL_RING",
                "_DT_ALPHATEST_ON", "_DT_NORMALMAP" },
        new[] { "_MAIN_LIGHT_SHADOWS_CASCADE", "_ADDITIONAL_LIGHTS", "_ADDITIONAL_LIGHT_SHADOWS", "_SHADOWS_SOFT",
                "_SCREEN_SPACE_OCCLUSION", "_DT_RAMP", "_DT_AMBIENT", "_DT_AO" },
        new[] { "_CLUSTER_LIGHT_LOOP", "_ADDITIONAL_LIGHTS", "_DT_AMBIENT", "_DT_OUTLINE" },
        new[] { "_MAIN_LIGHT_SHADOWS_SCREEN", "PROBE_VOLUMES_L1", "FOG_LINEAR" },
        new[] { "PROBE_VOLUMES_L2", "_DT_ALPHATEST_ON", "_CASTING_PUNCTUAL_LIGHT_SHADOW" },
    };

    public static void CompileShaders() => DaskToonTests.Run(() =>
    {
        AssetDatabase.Refresh();
        var errors = new List<object>();
        var compiled = 0;
        foreach (var name in Shaders)
        {
            var path = "Assets/DaskToon/Shaders/" + name + ".shader";
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(path);
            if (shader == null)
            {
                errors.Add(path + ": not imported");
                continue;
            }
            foreach (var m in ShaderUtil.GetShaderMessages(shader))
            {
                if (m.severity == ShaderCompilerMessageSeverity.Error)
                    errors.Add(name + ": " + m.message + " (" + m.file + ":" + m.line + ")");
            }
            var sub = ShaderUtil.GetShaderData(shader).GetSubshader(0);
            for (var p = 0; p < sub.PassCount; p++)
            {
                var pass = sub.GetPass(p);
                foreach (var keywords in KeywordSets)
                foreach (var platform in new[] { ShaderCompilerPlatform.D3D, ShaderCompilerPlatform.Vulkan })
                foreach (var stage in new[] { ShaderType.Vertex, ShaderType.Fragment })
                {
                    var info = pass.CompileVariant(stage, keywords, platform, BuildTarget.StandaloneWindows64);
                    compiled++;
                    if (info.Success) continue;
                    foreach (var m in info.Messages)
                    {
                        if (m.severity == ShaderCompilerMessageSeverity.Error)
                            errors.Add(name + "/" + pass.Name + "/" + platform + "/" + stage + " [" +
                                       string.Join(" ", keywords) + "]: " + m.message + " (" + m.file + ":" + m.line + ")");
                    }
                }
            }
        }
        return new Dictionary<string, object> { { "ok", errors.Count == 0 }, { "errors", errors }, { "compiled", compiled } };
    });
}
