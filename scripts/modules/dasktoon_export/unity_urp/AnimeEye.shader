// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// DaskToon Anime Eye for URP 17.5 (unlit, like the node: pure emission).

Shader "DaskToon/AnimeEye"
{
    Properties
    {
        [MainColor] _BaseColor ("Iris Color", Color) = (0.424, 0.701, 0.931, 1)
        [MainTexture] _BaseMap ("Iris Color Map", 2D) = "white" {}
        [HideInInspector] _DT_BaseMapOn ("Iris Color Map On", Float) = 0
        _DT_PupilColor ("Pupil Color", Color) = (0.152, 0.248, 0.381, 1)
        [NoScaleOffset] _DT_PupilColorMap ("Pupil Color Map", 2D) = "white" {}
        [HideInInspector] _DT_PupilColorMapOn ("Pupil Color Map On", Float) = 0
        _DT_GlowColor ("Bottom Glow Color", Color) = (0.626, 0.931, 1, 1)
        [NoScaleOffset] _DT_GlowColorMap ("Bottom Glow Color Map", 2D) = "white" {}
        [HideInInspector] _DT_GlowColorMapOn ("Bottom Glow Color Map On", Float) = 0
        _DT_GlowPower ("Bottom Glow Power", Float) = 1.5
        _DT_TopShadowTint ("Top Shadow Tint", Color) = (0.313, 0.381, 0.537, 1)
        [NoScaleOffset] _DT_TopShadowTintMap ("Top Shadow Tint Map", 2D) = "white" {}
        [HideInInspector] _DT_TopShadowTintMapOn ("Top Shadow Tint Map On", Float) = 0
        _DT_SparkleColor ("Sparkle Color", Color) = (1, 1, 1, 1)
        [NoScaleOffset] _DT_SparkleColorMap ("Sparkle Color Map", 2D) = "white" {}
        [HideInInspector] _DT_SparkleColorMapOn ("Sparkle Color Map On", Float) = 0
        [Toggle] _DT_EyeUseUV ("Use UV (off: Blender world XY)", Float) = 1

        [Header(Outline)][Toggle(_DT_OUTLINE)] _DT_UseOutline ("Outline (re-export from DaskToon to turn on)", Float) = 0
        _DT_OutlineWidth ("Outline Width (m)", Range(0, 0.05)) = 0.002
        _DT_OutlineColor ("Outline Color", Color) = (0.437, 0.313, 0.313, 1)
        [NoScaleOffset] _DT_OutlineColorMap ("Outline Color Map", 2D) = "white" {}
        [HideInInspector] _DT_OutlineColorMapOn ("Outline Color Map On", Float) = 0
        _DT_OutlineBaseColor ("Outline Base Color", Color) = (0.978, 0.931, 0.906, 1)
        [NoScaleOffset] _DT_OutlineBaseColorMap ("Outline Base Color Map", 2D) = "white" {}
        [HideInInspector] _DT_OutlineBaseColorMapOn ("Outline Base Color Map On", Float) = 0
        _DT_OutlineLightBleed ("Light Bleed", Range(0, 1)) = 0.7
        _DT_OutlineWobble ("Hand Wobble", Range(0, 1)) = 0.15
        [Enum(Custom,0,Harmonic,1,LightReactive,2)] _DT_OutlineTintMode ("Tint Mode", Float) = 0
        _DT_OutlineTintDarkness ("Tint Darkness", Range(0.05, 1)) = 0.35
        _DT_OutlineTintSatBoost ("Tint Saturation Boost", Range(0.5, 3)) = 1.4
        _DT_OutlineLightingMix ("Outline Lighting Mix", Range(0, 1)) = 0
        [HideInInspector] _DT_OutlineUV ("Outline Normal UV Channel", Float) = -1
        [HideInInspector] _DT_OutlineWUV ("Outline Mask UV Channel", Float) = -1

        [Header(Render)]
        [HideInInspector] _AlphaClip ("Alpha Clip", Float) = 0
        _Cutoff ("Alpha Cutoff", Range(0, 1)) = 0.5
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src Blend", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst Blend", Float) = 0
        [Enum(Off,0,On,1)] _ZWrite ("ZWrite", Float) = 1
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
        [HideInInspector] _Surface ("Surface", Float) = 0
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" "IgnoreProjector" = "True" }

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "DaskToonCore.hlsl"

        CBUFFER_START(UnityPerMaterial)
            float4 _BaseColor;
            float4 _DT_PupilColor;
            float4 _DT_GlowColor;
            float4 _DT_TopShadowTint;
            float4 _DT_SparkleColor;
            float _DT_BaseMapOn;
            float _DT_PupilColorMapOn;
            float _DT_GlowColorMapOn;
            float _DT_GlowPower;
            float _DT_TopShadowTintMapOn;
            float _DT_SparkleColorMapOn;
            float _DT_EyeUseUV;
            DT_SHARED_MATERIAL_FIELDS
        CBUFFER_END

        TEXTURE2D(_BaseMap);
        TEXTURE2D(_DT_PupilColorMap);
        TEXTURE2D(_DT_GlowColorMap);
        TEXTURE2D(_DT_TopShadowTintMap);
        TEXTURE2D(_DT_SparkleColorMap);
        DT_SHARED_TEXTURES

        float DT_SurfaceAlpha(float2 uv)
        {
            return 1.0;
        }
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Blend [_SrcBlend] [_DstBlend]
            ZWrite [_ZWrite]
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex DT_ForwardVertex
            #pragma fragment DT_AnimeEyeFragment
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "DaskToonURP.hlsl"

            half4 DT_AnimeEyeFragment(DTVaryings input) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                float2 uv = input.uv0;
                // The node falls back to the Blender world position when its UV input is unlinked or zero.
                float3 pb = DT_UnityToBlenderPos(input.positionWS);
                float2 eye_uv = (_DT_EyeUseUV > 0.5 && dot(uv, uv) > 1e-6) ? uv : pb.xy * 0.5 + 0.5;
                DTAnimeEyeInput s;
                s.irisColor = DT_ColorInput(_BaseColor, TEXTURE2D_ARGS(_BaseMap, sampler_linear_repeat), _DT_BaseMapOn, uv).rgb;
                s.pupilColor = DT_ColorInput(_DT_PupilColor, TEXTURE2D_ARGS(_DT_PupilColorMap, sampler_linear_repeat),
                                             _DT_PupilColorMapOn, uv).rgb;
                s.glowColor = DT_ColorInput(_DT_GlowColor, TEXTURE2D_ARGS(_DT_GlowColorMap, sampler_linear_repeat),
                                            _DT_GlowColorMapOn, uv).rgb;
                s.glowPower = _DT_GlowPower;
                s.topShadowTint = DT_ColorInput(_DT_TopShadowTint, TEXTURE2D_ARGS(_DT_TopShadowTintMap, sampler_linear_repeat),
                                                _DT_TopShadowTintMapOn, uv).rgb;
                s.sparkleColor = DT_ColorInput(_DT_SparkleColor, TEXTURE2D_ARGS(_DT_SparkleColorMap, sampler_linear_repeat),
                                               _DT_SparkleColorMapOn, uv).rgb;
                float3 c = dt_anime_eye(s, eye_uv);
                float fogFactor = input.fogFactor;
                c = MixFog(c, InitializeInputDataFog(float4(input.positionWS, 1.0), fogFactor));
                return half4(c, 1.0);
            }
            ENDHLSL
        }

        Pass
        {
            Name "Outline"
            Tags { "LightMode" = "SRPDefaultUnlit" }
            Cull Front
            ZWrite On

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex DT_OutlineVertex
            #pragma fragment DT_OutlineFragment
            #pragma shader_feature_local_vertex _DT_OUTLINE
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ProbeVolumeVariants.hlsl"
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "DaskToonOutline.hlsl"
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex DT_ShadowVertex
            #pragma fragment DT_ShadowFragment
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #pragma multi_compile_instancing
            #include "DaskToonURP.hlsl"
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            ZWrite On
            ColorMask R
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex DT_DepthVertex
            #pragma fragment DT_DepthOnlyFragment
            #pragma multi_compile_instancing
            #include "DaskToonURP.hlsl"
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode" = "DepthNormals" }
            ZWrite On
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex DT_DepthVertex
            #pragma fragment DT_DepthNormalsFragment
            #pragma multi_compile_instancing
            #include "DaskToonURP.hlsl"
            ENDHLSL
        }
    }
}
