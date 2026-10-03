// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// DaskToon URP 17.5 layer: the only file that calls URP. It gathers lighting with the meaning of EEVEE's
// closure_eval(ClosureDiffuse): every lamp as Lambert without 1/pi (a Unity intensity is Blender's strength / pi)
// plus the ambient probe. It also holds the vertex stage and the shadow / depth passes of every DaskToon shader.
// Every shader defines DT_SurfaceAlpha(uv) before including this file.

#ifndef DASKTOON_URP_INCLUDED
#define DASKTOON_URP_INCLUDED

#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

// Blender world (Z up) <-> Unity world (Y up) for an FBX written with axis_forward='-Z', axis_up='Y'.
float3 DT_BlenderToUnityDir(float3 b)
{
    return float3(-b.x, b.z, -b.y);
}

float3 DT_UnityToBlenderDir(float3 u)
{
    return float3(-u.x, -u.z, u.y);
}

float3 DT_UnityToBlenderPos(float3 u)
{
    return DT_UnityToBlenderDir(u);
}

struct DTAttributes
{
    float4 positionOS : POSITION;
    float3 normalOS : NORMAL;
    float4 tangentOS : TANGENT;
    float2 uv0 : TEXCOORD0;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct DTVaryings
{
    float4 positionCS : SV_POSITION;
    float2 uv0 : TEXCOORD0;
    float3 positionWS : TEXCOORD1;
    float3 normalWS : TEXCOORD2;
    float4 tangentWS : TEXCOORD3;
    float fogFactor : TEXCOORD4;
    UNITY_VERTEX_INPUT_INSTANCE_ID
    UNITY_VERTEX_OUTPUT_STEREO
};

DTVaryings DT_ForwardVertex(DTAttributes input)
{
    DTVaryings output = (DTVaryings)0;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_TRANSFER_INSTANCE_ID(input, output);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
    VertexPositionInputs vp = GetVertexPositionInputs(input.positionOS.xyz);
    VertexNormalInputs vn = GetVertexNormalInputs(input.normalOS, input.tangentOS);
    output.positionCS = vp.positionCS;
    output.positionWS = vp.positionWS;
    output.normalWS = vn.normalWS;
    output.tangentWS = float4(vn.tangentWS, input.tangentOS.w * GetOddNegativeScale());
    output.uv0 = input.uv0;
    output.fogFactor = ComputeFogFactor(vp.positionCS.z);
    return output;
}

float4 DT_ShadowCoord(float3 positionWS)
{
#if defined(_MAIN_LIGHT_SHADOWS_SCREEN) && !defined(_SURFACE_TYPE_TRANSPARENT)
    float4 positionCS = TransformWorldToHClip(positionWS);
    float4 ndc = positionCS * 0.5;
    ndc.xy = float2(ndc.x, ndc.y * _ProjectionParams.x) + ndc.w;
    ndc.zw = positionCS.zw;
    return ndc;
#elif defined(MAIN_LIGHT_CALCULATE_SHADOWS)
    return TransformWorldToShadowCoord(positionWS);
#else
    return float4(0.0, 0.0, 0.0, 0.0);
#endif
}

// positionCS is the fragment's SV_POSITION.
InputData DT_MakeInputData(float3 positionWS, float3 normalWS, float4 positionCS, float fogFactor)
{
    InputData inputData = (InputData)0;
    inputData.positionWS = positionWS;
    inputData.normalWS = normalWS;
    inputData.viewDirectionWS = GetWorldSpaceNormalizeViewDir(positionWS);
    inputData.shadowCoord = DT_ShadowCoord(positionWS);
    inputData.fogCoord = InitializeInputDataFog(float4(positionWS, 1.0), fogFactor);
    inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(positionCS);
    inputData.shadowMask = half4(1.0, 1.0, 1.0, 1.0);
    return inputData;
}

// The geometry normal, flipped on back faces like EEVEE, optionally bent by a tangent-space normal map the way
// Blender's Normal Map node does it: normalize(mix(N, mapped, strength)).
float3 DT_ShadingNormal(DTVaryings input, bool isFrontFace, TEXTURE2D_PARAM(normalMap, normalSampler), float strength)
{
    float3 N = normalize(input.normalWS);
    if (!isFrontFace)
    {
        N = -N;
    }
#if defined(_DT_NORMALMAP)
    float3 T = normalize(input.tangentWS.xyz);
    float3 B = cross(N, T) * input.tangentWS.w;
    float3 nts = UnpackNormal(SAMPLE_TEXTURE2D(normalMap, normalSampler, input.uv0));
    float3 mapped = normalize(nts.x * T + nts.y * B + nts.z * N);
    N = normalize(lerp(N, mapped, max(strength, 0.0)));
#endif
    return N;
}

float3 DT_Lambert(Light light, float3 N)
{
    return light.color * (light.distanceAttenuation * light.shadowAttenuation) * saturate(dot(N, light.direction));
}

float3 DT_Ambient(InputData inputData, float3 N)
{
#if defined(PROBE_VOLUMES_L1) || defined(PROBE_VOLUMES_L2)
    return SampleProbeVolumePixel(half3(0.0, 0.0, 0.0), GetAbsolutePositionWS(inputData.positionWS), N,
                                  inputData.viewDirectionWS, inputData.normalizedScreenSpaceUV * _ScreenParams.xy);
#else
    return SampleSH(N);
#endif
}

// closure_eval(ClosureDiffuse) at normal N: main light + additional lights (Lambert) + ambient.
float3 DT_DiffuseLight(InputData inputData, float3 N)
{
    half4 shadowMask = inputData.shadowMask;
    Light mainLight = GetMainLight(inputData.shadowCoord, inputData.positionWS, shadowMask);
    float3 c = DT_Lambert(mainLight, N);
#if defined(_ADDITIONAL_LIGHTS)
    uint pixelLightCount = GetAdditionalLightsCount();
#if USE_CLUSTER_LIGHT_LOOP
    [loop] for (uint lightIndex = 0; lightIndex < min(URP_FP_DIRECTIONAL_LIGHTS_COUNT, MAX_VISIBLE_LIGHTS); lightIndex++)
    {
        CLUSTER_LIGHT_LOOP_SUBTRACTIVE_LIGHT_CHECK
        c += DT_Lambert(GetAdditionalLight(lightIndex, inputData.positionWS, shadowMask), N);
    }
#endif
    LIGHT_LOOP_BEGIN(pixelLightCount)
        c += DT_Lambert(GetAdditionalLight(lightIndex, inputData.positionWS, shadowMask), N);
    LIGHT_LOOP_END
#endif
    c += DT_Ambient(inputData, N);
    return c;
}

float DT_GGX(Light light, float3 N, float3 V, float alpha)
{
    float3 H = SafeNormalize(light.direction + V);
    float NdotH = saturate(dot(N, H));
    float NdotL = saturate(dot(N, light.direction));
    float NdotV = max(saturate(dot(N, V)), 0.0001);
    float a2 = alpha * alpha;
    float d = NdotH * NdotH * (a2 - 1.0) + 1.0;
    float D = a2 / (PI * d * d + 1e-7);
    float k = alpha * 0.5;
    float vis = 1.0 / (4.0 * (NdotL * (1.0 - k) + k) * (NdotV * (1.0 - k) + k));
    return D * vis * NdotL;
}

float3 DT_GGXLight(Light light, float3 N, float3 V, float alpha)
{
    return light.color * (light.distanceAttenuation * light.shadowAttenuation) * DT_GGX(light, N, V, alpha);
}

// Luminance of closure_eval(ClosureReflection) with roughness 0.05: lamps through GGX plus the reflection probe.
float DT_Glossy(InputData inputData, float3 N)
{
    const float roughness = 0.05;
    float alpha = roughness * roughness;
    float3 V = inputData.viewDirectionWS;
    half4 shadowMask = inputData.shadowMask;
    float3 c = DT_GGXLight(GetMainLight(inputData.shadowCoord, inputData.positionWS, shadowMask), N, V, alpha);
#if defined(_ADDITIONAL_LIGHTS)
    uint pixelLightCount = GetAdditionalLightsCount();
#if USE_CLUSTER_LIGHT_LOOP
    [loop] for (uint lightIndex = 0; lightIndex < min(URP_FP_DIRECTIONAL_LIGHTS_COUNT, MAX_VISIBLE_LIGHTS); lightIndex++)
    {
        CLUSTER_LIGHT_LOOP_SUBTRACTIVE_LIGHT_CHECK
        c += DT_GGXLight(GetAdditionalLight(lightIndex, inputData.positionWS, shadowMask), N, V, alpha);
    }
#endif
    LIGHT_LOOP_BEGIN(pixelLightCount)
        c += DT_GGXLight(GetAdditionalLight(lightIndex, inputData.positionWS, shadowMask), N, V, alpha);
    LIGHT_LOOP_END
#endif
    c += GlossyEnvironmentReflection(reflect(-V, N), inputData.positionWS, roughness, 1.0,
                                     inputData.normalizedScreenSpaceUV);
    return dt_luminance(c);
}

float DT_AmbientOcclusion(InputData inputData)
{
#if defined(_SCREEN_SPACE_OCCLUSION)
    return GetScreenSpaceAmbientOcclusion(inputData.normalizedScreenSpaceUV).indirectAmbientOcclusion;
#else
    return 1.0;
#endif
}

// HLSL's ?: evaluates both sides, so the optional light loops stay behind if statements.
DTLighting DT_GatherLighting(InputData inputData, float3 N, bool needUp, bool needGlossy)
{
    DTLighting l;
    l.diffuse = DT_DiffuseLight(inputData, N);
    l.diffuseUp = l.diffuse;
    if (needUp)
    {
        l.diffuseUp = DT_DiffuseLight(inputData, float3(0.0, 1.0, 0.0));
    }
    l.glossy = 0.0;
    if (needGlossy)
    {
        l.glossy = DT_Glossy(inputData, N);
    }
    l.ao = DT_AmbientOcclusion(inputData);
    l.NdotV = dot(N, inputData.viewDirectionWS);
    return l;
}

// ---------------------------------------------------------------------------------------------------------------
// ShadowCaster, DepthOnly and DepthNormals (DepthNormals feeds SSAO).

float3 _LightDirection;
float3 _LightPosition;

struct DTDepthVaryings
{
    float4 positionCS : SV_POSITION;
    float2 uv0 : TEXCOORD0;
    float3 normalWS : TEXCOORD1;
    UNITY_VERTEX_INPUT_INSTANCE_ID
    UNITY_VERTEX_OUTPUT_STEREO
};

DTDepthVaryings DT_ShadowVertex(DTAttributes input)
{
    DTDepthVaryings output = (DTDepthVaryings)0;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_TRANSFER_INSTANCE_ID(input, output);
    float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
    float3 normalWS = TransformObjectToWorldNormal(input.normalOS);
#if _CASTING_PUNCTUAL_LIGHT_SHADOW
    float3 lightDirectionWS = normalize(_LightPosition - positionWS);
#else
    float3 lightDirectionWS = _LightDirection;
#endif
    output.positionCS = ApplyShadowClamping(TransformWorldToHClip(ApplyShadowBias(positionWS, normalWS, lightDirectionWS)));
    output.uv0 = input.uv0;
    output.normalWS = normalWS;
    return output;
}

DTDepthVaryings DT_DepthVertex(DTAttributes input)
{
    DTDepthVaryings output = (DTDepthVaryings)0;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_TRANSFER_INSTANCE_ID(input, output);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
    output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
    output.uv0 = input.uv0;
    output.normalWS = NormalizeNormalPerVertex(TransformObjectToWorldNormal(input.normalOS));
    return output;
}

void DT_ClipAlpha(float2 uv)
{
#if defined(_DT_ALPHATEST_ON)
    clip(DT_SurfaceAlpha(uv) - _Cutoff);
#endif
}

half4 DT_ShadowFragment(DTDepthVaryings input) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(input);
    DT_ClipAlpha(input.uv0);
    return 0;
}

half DT_DepthOnlyFragment(DTDepthVaryings input) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
    DT_ClipAlpha(input.uv0);
    return input.positionCS.z;
}

half4 DT_DepthNormalsFragment(DTDepthVaryings input) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
    DT_ClipAlpha(input.uv0);
    return half4(NormalizeNormalPerPixel(input.normalWS), 0.0);
}

#endif // DASKTOON_URP_INCLUDED
