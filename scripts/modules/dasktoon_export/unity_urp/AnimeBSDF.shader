// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// DaskToon Anime BSDF for URP 17.5. Written by DaskToon Engine Export; edit the material in DaskToon and re-export.

Shader "DaskToon/AnimeBSDF"
{
    Properties
    {
        [MainColor] _BaseColor ("Base Color", Color) = (0.991, 0.945, 0.916, 1)
        [MainTexture] _BaseMap ("Base Color Map", 2D) = "white" {}
        [HideInInspector] _DT_BaseMapOn ("Base Color Map On", Float) = 0
        _DT_ShadowColor ("Shadow Color", Color) = (0.945, 0.827, 0.832, 1)
        [NoScaleOffset] _DT_ShadowColorMap ("Shadow Color Map", 2D) = "white" {}
        [HideInInspector] _DT_ShadowColorMapOn ("Shadow Color Map On", Float) = 0
        _DT_ShadowThreshold ("Shadow Threshold", Range(0, 1)) = 0.46
        [NoScaleOffset] _DT_ShadowThresholdMap ("Shadow Threshold Map", 2D) = "white" {}
        [HideInInspector] _DT_ShadowThresholdMapOn ("Shadow Threshold Map On", Float) = 0
        _DT_ShadowSoftness ("Shadow Softness", Range(0.001, 0.5)) = 0.035
        [Toggle(_DT_RAMP)] _DT_UseRamp ("Shading Ramp", Float) = 0
        [NoScaleOffset] _DT_RampMap ("Ramp", 2D) = "white" {}
        [HideInInspector] _DT_RampConstant ("Ramp Constant", Float) = 1

        [Header(Ambient)][Toggle(_DT_AMBIENT)] _DT_UseAmbient ("Ambient", Float) = 0
        [Enum(Overlay,0,Hue,1,HueSat,2,Sat,3,Val,4,Multiply,5,Mix,6)] _DT_AmbientMode ("Ambient Mode", Float) = 0
        _DT_AmbientColor ("Ambient Color", Color) = (0.931, 0.955, 1, 1)
        [NoScaleOffset] _DT_AmbientColorMap ("Ambient Color Map", 2D) = "white" {}
        [HideInInspector] _DT_AmbientColorMapOn ("Ambient Color Map On", Float) = 0
        [Toggle] _DT_AmbientUseCustom ("Use Custom Color", Float) = 1
        [Toggle] _DT_AmbientShadowOnly ("Ambient Shadow Only", Float) = 1
        _DT_AmbientFactor ("Ambient Factor", Range(0, 1)) = 0.3

        [Header(Light)][Toggle(_DT_LIGHT)] _DT_UseLight ("Light", Float) = 0
        [Enum(Overlay,0,Hue,1,Multiply,2,Add,3,PureCel,4)] _DT_LightMode ("Light Mode", Float) = 0
        _DT_LightTintStrength ("Light Tint Strength", Range(0, 2)) = 1
        _DT_LightFactor ("Light Factor", Range(0, 1)) = 1

        [Header(AO)][Toggle(_DT_AO)] _DT_UseAO ("AO", Float) = 0
        _DT_AOColor ("AO Color", Color) = (0, 0, 0, 1)
        [NoScaleOffset] _DT_AOColorMap ("AO Color Map", 2D) = "white" {}
        [HideInInspector] _DT_AOColorMapOn ("AO Color Map On", Float) = 0
        _DT_AODistance ("AO Distance (SSAO radius is global in URP)", Float) = 0.5
        _DT_AODarkness ("AO Darkness", Range(0, 10)) = 1.5
        _DT_AOFactor ("AO Factor", Range(0, 1)) = 1
        _DT_AOMask ("AO Mask", Range(0, 1)) = 1
        [NoScaleOffset] _DT_AOMaskMap ("AO Mask Map", 2D) = "white" {}
        [HideInInspector] _DT_AOMaskMapOn ("AO Mask Map On", Float) = 0

        [Header(Rim)][Toggle(_DT_RIM)] _DT_UseRim ("Rim", Float) = 0
        _DT_RimColor ("Rim Color", Color) = (1, 0.991, 0.955, 1)
        [NoScaleOffset] _DT_RimColorMap ("Rim Color Map", 2D) = "white" {}
        [HideInInspector] _DT_RimColorMapOn ("Rim Color Map On", Float) = 0
        _DT_RimPower ("Rim Fresnel Power", Range(0.1, 10)) = 4
        _DT_RimLift ("Rim Lift", Range(-1, 1)) = 0
        _DT_RimLightingMix ("Rim Lighting Mix", Range(0, 1)) = 0.6
        _DT_RimFactor ("Rim Factor", Range(0, 1)) = 0.5

        [Header(Grade)][Toggle(_DT_GRADE)] _DT_UseGrade ("Grade", Float) = 0
        _DT_ColorFilter ("Color Filter", Color) = (1, 1, 1, 1)
        [NoScaleOffset] _DT_ColorFilterMap ("Color Filter Map", 2D) = "white" {}
        [HideInInspector] _DT_ColorFilterMapOn ("Color Filter Map On", Float) = 0
        _DT_ShadowTint ("Shadow Tint", Color) = (0.786, 0.798, 0.891, 1)
        [NoScaleOffset] _DT_ShadowTintMap ("Shadow Tint Map", 2D) = "white" {}
        [HideInInspector] _DT_ShadowTintMapOn ("Shadow Tint Map On", Float) = 0
        _DT_HighlightTint ("Highlight Tint", Color) = (1, 0.982, 0.955, 1)
        [NoScaleOffset] _DT_HighlightTintMap ("Highlight Tint Map", 2D) = "white" {}
        [HideInInspector] _DT_HighlightTintMapOn ("Highlight Tint Map On", Float) = 0
        _DT_Saturation ("Saturation", Range(0, 3)) = 1
        _DT_Brightness ("Brightness", Range(-1, 1)) = 0
        _DT_Contrast ("Contrast", Range(-1, 1)) = 0
        _DT_GradeFactor ("Grade Factor", Range(0, 1)) = 1

        [Header(Master)]
        _DT_Strength ("Strength", Range(0, 10)) = 1
        _DT_Alpha ("Alpha", Range(0, 1)) = 1
        [NoScaleOffset] _DT_AlphaMap ("Alpha Map", 2D) = "white" {}
        [HideInInspector] _DT_AlphaMapOn ("Alpha Map On", Float) = 0
        [Toggle(_DT_NORMALMAP)] _DT_UseNormalMap ("Normal Map", Float) = 0
        [Normal][NoScaleOffset] _DT_NormalMap ("Normal Map", 2D) = "bump" {}
        _DT_NormalStrength ("Normal Strength", Range(0, 10)) = 1

        [Header(Outline)][Toggle(_DT_OUTLINE)] _DT_UseOutline ("Outline (re-export from DaskToon to turn on)", Float) = 0
        _DT_OutlineWidth ("Outline Width (m)", Range(0, 0.05)) = 0.002
        _DT_OutlineColor ("Outline Color", Color) = (0.506, 0.313, 0.272, 1)
        [NoScaleOffset] _DT_OutlineColorMap ("Outline Color Map", 2D) = "white" {}
        [HideInInspector] _DT_OutlineColorMapOn ("Outline Color Map On", Float) = 0
        _DT_OutlineBaseColor ("Outline Base Color", Color) = (0.991, 0.945, 0.916, 1)
        [NoScaleOffset] _DT_OutlineBaseColorMap ("Outline Base Color Map", 2D) = "white" {}
        [HideInInspector] _DT_OutlineBaseColorMapOn ("Outline Base Color Map On", Float) = 0
        _DT_OutlineLightBleed ("Light Bleed", Range(0, 1)) = 0.7
        _DT_OutlineWobble ("Hand Wobble", Range(0, 1)) = 0.15
        [Enum(Custom,0,Harmonic,1,LightReactive,2)] _DT_OutlineTintMode ("Tint Mode", Float) = 0
        _DT_OutlineTintDarkness ("Tint Darkness", Range(0.05, 1)) = 0.35
        _DT_OutlineTintSatBoost ("Tint Saturation Boost", Range(0.5, 3)) = 1.4
        _DT_OutlineLightingMix ("Outline Lighting Mix", Range(0, 1)) = 0.1
        [HideInInspector] _DT_OutlineUV ("Outline Normal UV Channel", Float) = -1
        [HideInInspector] _DT_OutlineWUV ("Outline Mask UV Channel", Float) = -1

        [Header(Render)][Toggle(_DT_ALPHATEST_ON)] _AlphaClip ("Alpha Clip", Float) = 0
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
            float4 _DT_AOColor;
            float4 _DT_RimColor;
            float4 _DT_ColorFilter;
            float4 _DT_ShadowTint;
            float4 _DT_HighlightTint;
            float _DT_BaseMapOn;
            float _DT_ShadowColorMapOn;
            float _DT_ShadowThreshold;
            float _DT_ShadowThresholdMapOn;
            float _DT_ShadowSoftness;
            float _DT_RampConstant;
            float _DT_AmbientColorMapOn;
            float _DT_AmbientUseCustom;
            float _DT_AmbientShadowOnly;
            float _DT_AmbientFactor;
            float _DT_AmbientMode;
            float _DT_LightTintStrength;
            float _DT_LightFactor;
            float _DT_LightMode;
            float _DT_AOColorMapOn;
            float _DT_AODistance;
            float _DT_AODarkness;
            float _DT_AOFactor;
            float _DT_AOMask;
            float _DT_AOMaskMapOn;
            float _DT_RimColorMapOn;
            float _DT_RimPower;
            float _DT_RimLift;
            float _DT_RimLightingMix;
            float _DT_RimFactor;
            float _DT_ColorFilterMapOn;
            float _DT_ShadowTintMapOn;
            float _DT_HighlightTintMapOn;
            float _DT_Saturation;
            float _DT_Brightness;
            float _DT_Contrast;
            float _DT_GradeFactor;
            float _DT_Strength;
            float _DT_Alpha;
            float _DT_AlphaMapOn;
            float _DT_NormalStrength;
            DT_SHARED_MATERIAL_FIELDS
        CBUFFER_END

        TEXTURE2D(_BaseMap);
        TEXTURE2D(_DT_ShadowColorMap);
        TEXTURE2D(_DT_ShadowThresholdMap);
        TEXTURE2D(_DT_RampMap);
        TEXTURE2D(_DT_AmbientColorMap);
        TEXTURE2D(_DT_AOColorMap);
        TEXTURE2D(_DT_AOMaskMap);
        TEXTURE2D(_DT_RimColorMap);
        TEXTURE2D(_DT_ColorFilterMap);
        TEXTURE2D(_DT_ShadowTintMap);
        TEXTURE2D(_DT_HighlightTintMap);
        TEXTURE2D(_DT_AlphaMap);
        TEXTURE2D(_DT_NormalMap);
        DT_SHARED_TEXTURES

        float DT_SurfaceAlpha(float2 uv)
        {
            return clamp(DT_FloatInput(_DT_Alpha, TEXTURE2D_ARGS(_DT_AlphaMap, sampler_linear_repeat), _DT_AlphaMapOn, uv),
                         0.0, 1.0);
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
            #pragma fragment DT_AnimeBSDFFragment
            #pragma shader_feature_local_fragment _DT_RAMP
            #pragma shader_feature_local_fragment _DT_AMBIENT
            #pragma shader_feature_local_fragment _DT_LIGHT
            #pragma shader_feature_local_fragment _DT_AO
            #pragma shader_feature_local_fragment _DT_RIM
            #pragma shader_feature_local_fragment _DT_GRADE
            #pragma shader_feature_local_fragment _DT_ALPHATEST_ON
            #pragma shader_feature_local_fragment _DT_NORMALMAP
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fragment _ _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ProbeVolumeVariants.hlsl"
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "DaskToonURP.hlsl"

            half4 DT_AnimeBSDFFragment(DTVaryings input, FRONT_FACE_TYPE face : FRONT_FACE_SEMANTIC) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                float2 uv = input.uv0;
                float alpha = DT_SurfaceAlpha(uv);
                DT_ClipAlpha(uv);
                float3 N = DT_ShadingNormal(input, IS_FRONT_VFACE(face, true, false),
                                            TEXTURE2D_ARGS(_DT_NormalMap, sampler_linear_repeat), _DT_NormalStrength);
                InputData inputData = DT_MakeInputData(input.positionWS, N, input.positionCS, input.fogFactor);
                bool needUp = false;
#if defined(_DT_AMBIENT)
                needUp = _DT_AmbientUseCustom < 0.5;
#endif
                DTLighting l = DT_GatherLighting(inputData, N, needUp, false);

                DTAnimeBSDFInput s;
                s.baseColor = DT_ColorInput(_BaseColor, TEXTURE2D_ARGS(_BaseMap, sampler_linear_repeat), _DT_BaseMapOn, uv).rgb;
                s.shadowColor = DT_ColorInput(_DT_ShadowColor, TEXTURE2D_ARGS(_DT_ShadowColorMap, sampler_linear_repeat),
                                              _DT_ShadowColorMapOn, uv).rgb;
                s.shadowThreshold = DT_FloatInput(_DT_ShadowThreshold,
                                                  TEXTURE2D_ARGS(_DT_ShadowThresholdMap, sampler_linear_repeat),
                                                  _DT_ShadowThresholdMapOn, uv);
                s.shadowSoftness = _DT_ShadowSoftness;
                s.ambientColor = DT_ColorInput(_DT_AmbientColor, TEXTURE2D_ARGS(_DT_AmbientColorMap, sampler_linear_repeat),
                                               _DT_AmbientColorMapOn, uv).rgb;
                s.ambientUseCustom = _DT_AmbientUseCustom;
                s.ambientShadowOnly = _DT_AmbientShadowOnly;
                s.ambientFactor = _DT_AmbientFactor;
                s.ambientMode = (int)round(_DT_AmbientMode);
                s.lightTintStrength = _DT_LightTintStrength;
                s.lightFactor = _DT_LightFactor;
                s.lightMode = (int)round(_DT_LightMode);
                s.aoColor = DT_ColorInput(_DT_AOColor, TEXTURE2D_ARGS(_DT_AOColorMap, sampler_linear_repeat),
                                          _DT_AOColorMapOn, uv).rgb;
                s.aoDarkness = _DT_AODarkness;
                s.aoFactor = _DT_AOFactor;
                s.aoMask = DT_FloatInput(_DT_AOMask, TEXTURE2D_ARGS(_DT_AOMaskMap, sampler_linear_repeat), _DT_AOMaskMapOn, uv);
                s.rimColor = DT_ColorInput(_DT_RimColor, TEXTURE2D_ARGS(_DT_RimColorMap, sampler_linear_repeat),
                                           _DT_RimColorMapOn, uv).rgb;
                s.rimPower = _DT_RimPower;
                s.rimLift = _DT_RimLift;
                s.rimLightingMix = _DT_RimLightingMix;
                s.rimFactor = _DT_RimFactor;
                s.colorFilter = DT_ColorInput(_DT_ColorFilter, TEXTURE2D_ARGS(_DT_ColorFilterMap, sampler_linear_repeat),
                                              _DT_ColorFilterMapOn, uv).rgb;
                s.shadowTint = DT_ColorInput(_DT_ShadowTint, TEXTURE2D_ARGS(_DT_ShadowTintMap, sampler_linear_repeat),
                                             _DT_ShadowTintMapOn, uv).rgb;
                s.highlightTint = DT_ColorInput(_DT_HighlightTint, TEXTURE2D_ARGS(_DT_HighlightTintMap, sampler_linear_repeat),
                                                _DT_HighlightTintMapOn, uv).rgb;
                s.saturation = _DT_Saturation;
                s.brightness = _DT_Brightness;
                s.contrast = _DT_Contrast;
                s.gradeFactor = _DT_GradeFactor;
                s.strength = _DT_Strength;

                float3 c = dt_anime_bsdf(s, l, TEXTURE2D_ARGS(_DT_RampMap, sampler_linear_clamp), _DT_RampConstant);
                c = MixFog(c, inputData.fogCoord);
                return half4(c, alpha);
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
            #pragma shader_feature_local_fragment _DT_ALPHATEST_ON
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
            #pragma shader_feature_local_fragment _DT_ALPHATEST_ON
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
            #pragma shader_feature_local_fragment _DT_ALPHATEST_ON
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
            #pragma shader_feature_local_fragment _DT_ALPHATEST_ON
            #pragma multi_compile_instancing
            #include "DaskToonURP.hlsl"
            ENDHLSL
        }
    }
}
