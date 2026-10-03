// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// DaskToon Anime Cel (Classic Cel) for URP 17.5, with the hair pattern's Angel Ring layer (_DT_ANGEL_RING).

Shader "DaskToon/AnimeCel"
{
    Properties
    {
        [MainColor] _BaseColor ("Base Color", Color) = (0.955, 0.916, 0.896, 1)
        [MainTexture] _BaseMap ("Base Color Map", 2D) = "white" {}
        [HideInInspector] _DT_BaseMapOn ("Base Color Map On", Float) = 0
        _DT_ShadowColor ("Shadow Color", Color) = (0.798, 0.735, 0.767, 1)
        [NoScaleOffset] _DT_ShadowColorMap ("Shadow Color Map", 2D) = "white" {}
        [HideInInspector] _DT_ShadowColorMapOn ("Shadow Color Map On", Float) = 0
        _DT_ShadowThreshold ("Shadow Threshold", Range(0, 1)) = 0.48
        [NoScaleOffset] _DT_ShadowThresholdMap ("Shadow Threshold Map", 2D) = "white" {}
        [HideInInspector] _DT_ShadowThresholdMapOn ("Shadow Threshold Map On", Float) = 0
        _DT_ShadowSoftness ("Shadow Softness", Range(0.001, 0.5)) = 0.02
        [Toggle(_DT_RAMP)] _DT_UseRamp ("Shading Ramp", Float) = 0
        [NoScaleOffset] _DT_RampMap ("Ramp", 2D) = "white" {}
        [HideInInspector] _DT_RampConstant ("Ramp Constant", Float) = 1
        [Enum(Overlay,0,Hue,1,HueSat,2,Sat,3,Val,4,Multiply,5,Mix,6)] _DT_AmbientMode ("Ambient Mode", Float) = 2
        _DT_AmbientColor ("Ambient Color", Color) = (0.906, 0.931, 0.978, 1)
        [NoScaleOffset] _DT_AmbientColorMap ("Ambient Color Map", 2D) = "white" {}
        [HideInInspector] _DT_AmbientColorMapOn ("Ambient Color Map On", Float) = 0
        _DT_AmbientBlend ("Ambient Blend", Range(0, 1)) = 0.5
        [Toggle] _DT_AmbientShadowOnly ("Ambient Shadow Only", Float) = 1
        [Enum(Overlay,0,Hue,1,Multiply,2,Add,3,PureCel,4)] _DT_LightMode ("Light Mode", Float) = 0
        _DT_LightTintStrength ("Light Tint Strength", Range(0, 2)) = 1
        _DT_SpecularColor ("Specular Color", Color) = (1, 1, 1, 1)
        [NoScaleOffset] _DT_SpecularColorMap ("Specular Color Map", 2D) = "white" {}
        [HideInInspector] _DT_SpecularColorMapOn ("Specular Color Map On", Float) = 0
        _DT_SpecularSize ("Specular Size", Range(0, 1)) = 0.08
        _DT_SpecularSoftness ("Specular Softness", Range(0, 1)) = 0.02
        [Toggle(_DT_NORMALMAP)] _DT_UseNormalMap ("Normal Map", Float) = 0
        [Normal][NoScaleOffset] _DT_NormalMap ("Normal Map", 2D) = "bump" {}
        _DT_NormalStrength ("Normal Strength", Range(0, 10)) = 1
        _DT_EmissionStrength ("Emission Strength", Float) = 1

        [Header(Angel Ring)][Toggle(_DT_ANGEL_RING)] _DT_UseAngelRing ("Angel Ring", Float) = 0
        _DT_RingColor ("Highlight Color", Color) = (1, 0.982, 0.945, 1)
        _DT_RingPosition ("Band Position", Range(0, 1)) = 0.5
        _DT_RingWidth ("Band Width", Range(0, 1)) = 0.08
        _DT_RingSoftness ("Band Softness", Range(0, 1)) = 0.02
        _DT_RingJitter ("Strand Jitter", Range(0, 1)) = 0.12
        _DT_RingNoiseScale ("Noise Scale", Float) = 35
        _DT_RingIntensity ("Intensity", Float) = 1.5
        [Toggle] _DT_RingClampFactor ("Clamp Factor", Float) = 1
        [Toggle] _DT_RingClampResult ("Clamp Result", Float) = 0
        _DT_CelSelfEmission ("Cel Own Emission (DaskToon hidden Weight)", Float) = 0
        _DT_RingSelfEmission ("Ring Own Emission (DaskToon hidden Weight)", Float) = 0

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
            float4 _DT_ShadowColor;
            float4 _DT_AmbientColor;
            float4 _DT_SpecularColor;
            float4 _DT_RingColor;
            float _DT_BaseMapOn;
            float _DT_ShadowColorMapOn;
            float _DT_ShadowThreshold;
            float _DT_ShadowThresholdMapOn;
            float _DT_ShadowSoftness;
            float _DT_RampConstant;
            float _DT_AmbientMode;
            float _DT_AmbientColorMapOn;
            float _DT_AmbientBlend;
            float _DT_AmbientShadowOnly;
            float _DT_LightMode;
            float _DT_LightTintStrength;
            float _DT_SpecularColorMapOn;
            float _DT_SpecularSize;
            float _DT_SpecularSoftness;
            float _DT_NormalStrength;
            float _DT_EmissionStrength;
            float _DT_RingPosition;
            float _DT_RingWidth;
            float _DT_RingSoftness;
            float _DT_RingJitter;
            float _DT_RingNoiseScale;
            float _DT_RingIntensity;
            float _DT_RingClampFactor;
            float _DT_RingClampResult;
            float _DT_CelSelfEmission;
            float _DT_RingSelfEmission;
            DT_SHARED_MATERIAL_FIELDS
        CBUFFER_END

        TEXTURE2D(_BaseMap);
        TEXTURE2D(_DT_ShadowColorMap);
        TEXTURE2D(_DT_ShadowThresholdMap);
        TEXTURE2D(_DT_RampMap);
        TEXTURE2D(_DT_AmbientColorMap);
        TEXTURE2D(_DT_SpecularColorMap);
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
            #pragma fragment DT_AnimeCelFragment
            #pragma shader_feature_local_fragment _DT_RAMP
            #pragma shader_feature_local_fragment _DT_ANGEL_RING
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

            half4 DT_AnimeCelFragment(DTVaryings input, FRONT_FACE_TYPE face : FRONT_FACE_SEMANTIC) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                float2 uv = input.uv0;
                float3 N = DT_ShadingNormal(input, IS_FRONT_VFACE(face, true, false),
                                            TEXTURE2D_ARGS(_DT_NormalMap, sampler_linear_repeat), _DT_NormalStrength);
                InputData inputData = DT_MakeInputData(input.positionWS, N, input.positionCS, input.fogFactor);
                DTLighting l = DT_GatherLighting(inputData, N, false, true);

                DTAnimeCelInput s;
                s.baseColor = DT_ColorInput(_BaseColor, TEXTURE2D_ARGS(_BaseMap, sampler_linear_repeat), _DT_BaseMapOn, uv).rgb;
                s.shadowColor = DT_ColorInput(_DT_ShadowColor, TEXTURE2D_ARGS(_DT_ShadowColorMap, sampler_linear_repeat),
                                              _DT_ShadowColorMapOn, uv).rgb;
                s.shadowThreshold = DT_FloatInput(_DT_ShadowThreshold,
                                                  TEXTURE2D_ARGS(_DT_ShadowThresholdMap, sampler_linear_repeat),
                                                  _DT_ShadowThresholdMapOn, uv);
                s.shadowSoftness = _DT_ShadowSoftness;
                s.ambientColor = DT_ColorInput(_DT_AmbientColor, TEXTURE2D_ARGS(_DT_AmbientColorMap, sampler_linear_repeat),
                                               _DT_AmbientColorMapOn, uv);
                s.ambientBlend = _DT_AmbientBlend;
                s.ambientShadowOnly = _DT_AmbientShadowOnly;
                s.ambientMode = (int)round(_DT_AmbientMode);
                s.lightTintStrength = _DT_LightTintStrength;
                s.lightMode = (int)round(_DT_LightMode);
                s.specColor = DT_ColorInput(_DT_SpecularColor, TEXTURE2D_ARGS(_DT_SpecularColorMap, sampler_linear_repeat),
                                            _DT_SpecularColorMapOn, uv).rgb;
                s.specSize = _DT_SpecularSize;
                s.specSoftness = _DT_SpecularSoftness;

                float3 c = dt_anime_cel(s, l, TEXTURE2D_ARGS(_DT_RampMap, sampler_linear_clamp), _DT_RampConstant);
#if defined(_DT_ANGEL_RING)
                DTAngelRingInput r;
                r.highlightColor = _DT_RingColor.rgb;
                r.bandPosition = _DT_RingPosition;
                r.bandWidth = _DT_RingWidth;
                r.bandSoftness = _DT_RingSoftness;
                r.strandJitter = _DT_RingJitter;
                r.noiseScale = _DT_RingNoiseScale;
                r.intensity = _DT_RingIntensity;
                float ring_fac;
                float3 ring = dt_angel_ring(r, DT_UnityToBlenderPos(input.positionWS), DT_UnityToBlenderDir(N), ring_fac);
                // Emission(Mix) plus each node's own emission, which EEVEE adds with the node's hidden Weight.
                c = dt_hair(c, ring, ring_fac, _DT_RingClampFactor, _DT_RingClampResult) * _DT_EmissionStrength
                    + c * _DT_CelSelfEmission + ring * _DT_RingSelfEmission;
#endif
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
