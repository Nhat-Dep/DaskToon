// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// DaskToon Dask Cel (Cel Shading) for URP 17.5. _DT_OUTLINE also turns on the node's in-surface edge line.

Shader "DaskToon/DaskCel"
{
    Properties
    {
        [MainColor] _BaseColor ("Base Color", Color) = (0.978, 0.931, 0.906, 1)
        [MainTexture] _BaseMap ("Base Color Map", 2D) = "white" {}
        [HideInInspector] _DT_BaseMapOn ("Base Color Map On", Float) = 0
        _DT_ShadowColor ("Shadow Color", Color) = (0.827, 0.735, 0.767, 1)
        [NoScaleOffset] _DT_ShadowColorMap ("Shadow Color Map", 2D) = "white" {}
        [HideInInspector] _DT_ShadowColorMapOn ("Shadow Color Map On", Float) = 0
        _DT_ShadowThreshold ("Shadow Threshold", Range(0, 1)) = 0.48
        [NoScaleOffset] _DT_ShadowThresholdMap ("Shadow Threshold Map", 2D) = "white" {}
        [HideInInspector] _DT_ShadowThresholdMapOn ("Shadow Threshold Map On", Float) = 0
        _DT_ShadowSoftness ("Shadow Softness", Range(0.001, 0.5)) = 0.02
        [Toggle(_DT_RAMP)] _DT_UseRamp ("Shading Ramp", Float) = 0
        [NoScaleOffset] _DT_RampMap ("Ramp", 2D) = "white" {}
        [HideInInspector] _DT_RampConstant ("Ramp Constant", Float) = 1
        _DT_Strength ("Strength", Range(0, 10)) = 1
        [Toggle(_DT_NORMALMAP)] _DT_UseNormalMap ("Normal Map", Float) = 0
        [Normal][NoScaleOffset] _DT_NormalMap ("Normal Map", 2D) = "bump" {}
        _DT_NormalStrength ("Normal Strength", Range(0, 10)) = 1

        [Header(Outline)][Toggle(_DT_OUTLINE)] _DT_UseOutline ("Outline (re-export from DaskToon to turn on)", Float) = 0
        _DT_OutlineWidth ("Outline Width (m)", Range(0, 0.05)) = 0.0015
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
            float4 _DT_ShadowColor;
            float _DT_BaseMapOn;
            float _DT_ShadowColorMapOn;
            float _DT_ShadowThreshold;
            float _DT_ShadowThresholdMapOn;
            float _DT_ShadowSoftness;
            float _DT_RampConstant;
            float _DT_Strength;
            float _DT_NormalStrength;
            DT_SHARED_MATERIAL_FIELDS
        CBUFFER_END

        TEXTURE2D(_BaseMap);
        TEXTURE2D(_DT_ShadowColorMap);
        TEXTURE2D(_DT_ShadowThresholdMap);
        TEXTURE2D(_DT_RampMap);
        TEXTURE2D(_DT_NormalMap);
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
            #pragma fragment DT_DaskCelFragment
            #pragma shader_feature_local_fragment _DT_RAMP
            #pragma shader_feature_local_fragment _DT_OUTLINE
            #pragma shader_feature_local_fragment _DT_NORMALMAP
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fragment _ _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ProbeVolumeVariants.hlsl"
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "DaskToonURP.hlsl"

            half4 DT_DaskCelFragment(DTVaryings input, FRONT_FACE_TYPE face : FRONT_FACE_SEMANTIC) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                float2 uv = input.uv0;
                float3 N = DT_ShadingNormal(input, IS_FRONT_VFACE(face, true, false),
                                            TEXTURE2D_ARGS(_DT_NormalMap, sampler_linear_repeat), _DT_NormalStrength);
                InputData inputData = DT_MakeInputData(input.positionWS, N, input.positionCS, input.fogFactor);
                DTLighting l = DT_GatherLighting(inputData, N, false, false);

                DTDaskCelInput s;
                s.baseColor = DT_ColorInput(_BaseColor, TEXTURE2D_ARGS(_BaseMap, sampler_linear_repeat), _DT_BaseMapOn, uv).rgb;
                s.shadowColor = DT_ColorInput(_DT_ShadowColor, TEXTURE2D_ARGS(_DT_ShadowColorMap, sampler_linear_repeat),
                                              _DT_ShadowColorMapOn, uv).rgb;
                s.shadowThreshold = DT_FloatInput(_DT_ShadowThreshold,
                                                  TEXTURE2D_ARGS(_DT_ShadowThresholdMap, sampler_linear_repeat),
                                                  _DT_ShadowThresholdMapOn, uv);
                s.shadowSoftness = _DT_ShadowSoftness;
                s.outlineWidth = _DT_OutlineWidth;
                s.outlineColor = DT_ColorInput(_DT_OutlineColor, TEXTURE2D_ARGS(_DT_OutlineColorMap, sampler_linear_repeat),
                                               _DT_OutlineColorMapOn, uv).rgb;
                s.outlineLightingMix = _DT_OutlineLightingMix;
                s.outlineTintMode = (int)round(_DT_OutlineTintMode);
                s.strength = _DT_Strength;

                float cel;
                float3 c = dt_dask_cel(s, l, TEXTURE2D_ARGS(_DT_RampMap, sampler_linear_clamp), _DT_RampConstant, cel);
                c = MixFog(c, inputData.fogCoord);
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
