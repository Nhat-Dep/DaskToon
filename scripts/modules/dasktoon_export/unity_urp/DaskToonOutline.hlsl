// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Outline pass (LightMode SRPDefaultUnlit, Cull Front): pushes every vertex along DaskToon's smoothed outline normal
// (DT_OutlineN, octahedral, tangent space) by the width of project 1's Geometry Nodes hull, then colours the line
// with the Dask Outline formula. _DT_OutlineUV / _DT_OutlineWUV < 0 means the mesh has no outline data: the vertex
// normal and a mask of 1 are used instead.

#ifndef DASKTOON_OUTLINE_INCLUDED
#define DASKTOON_OUTLINE_INCLUDED

#include "DaskToonURP.hlsl"

struct DTOutlineAttributes
{
    float4 positionOS : POSITION;
    float3 normalOS : NORMAL;
    float4 tangentOS : TANGENT;
    float2 uv0 : TEXCOORD0;
    float2 uv1 : TEXCOORD1;
    float2 uv2 : TEXCOORD2;
    float2 uv3 : TEXCOORD3;
    float2 uv4 : TEXCOORD4;
    float2 uv5 : TEXCOORD5;
    float2 uv6 : TEXCOORD6;
    float2 uv7 : TEXCOORD7;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct DTOutlineVaryings
{
    float4 positionCS : SV_POSITION;
    float2 uv0 : TEXCOORD0;
    float3 positionWS : TEXCOORD1;
    float3 normalWS : TEXCOORD2;
    float fogFactor : TEXCOORD3;
    UNITY_VERTEX_INPUT_INSTANCE_ID
    UNITY_VERTEX_OUTPUT_STEREO
};

float2 DT_OutlineChannel(DTOutlineAttributes v, float index)
{
    int i = (int)round(index);
    float2 uv = v.uv0;
    uv = (i == 1) ? v.uv1 : uv;
    uv = (i == 2) ? v.uv2 : uv;
    uv = (i == 3) ? v.uv3 : uv;
    uv = (i == 4) ? v.uv4 : uv;
    uv = (i == 5) ? v.uv5 : uv;
    uv = (i == 6) ? v.uv6 : uv;
    uv = (i == 7) ? v.uv7 : uv;
    return uv;
}

DTOutlineVaryings DT_OutlineVertex(DTOutlineAttributes input)
{
    DTOutlineVaryings output = (DTOutlineVaryings)0;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_TRANSFER_INSTANCE_ID(input, output);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
    VertexPositionInputs vp = GetVertexPositionInputs(input.positionOS.xyz);
    VertexNormalInputs vn = GetVertexNormalInputs(input.normalOS, input.tangentOS);
    float3 N = normalize(vn.normalWS);
    float3 dir = N;
    if (_DT_OutlineUV > -0.5)
    {
        float3 nts = dt_oct_decode(DT_OutlineChannel(input, _DT_OutlineUV));
        dir = normalize(vn.tangentWS * nts.x + vn.bitangentWS * nts.y + N * nts.z);
    }
    float mask = (_DT_OutlineWUV > -0.5) ? DT_OutlineChannel(input, _DT_OutlineWUV).x : 1.0;
    Light mainLight = GetMainLight();
    // No Sun in Blender: the hull uses normalize(0.5, 0.8, 0.6).
    float3 L = (dot(mainLight.color, mainLight.color) > 1e-8) ? mainLight.direction
                                                               : normalize(DT_BlenderToUnityDir(float3(0.5, 0.8, 0.6)));
    float width = dt_outline_width(_DT_OutlineWidth, _DT_OutlineLightBleed, _DT_OutlineWobble, dot(dir, L), input.uv0,
                                   mask);
#if !defined(_DT_OUTLINE)
    width = 0.0;
#endif
    float3 positionWS = vp.positionWS + dir * width;
    output.positionCS = TransformWorldToHClip(positionWS);
    output.positionWS = positionWS;
    output.normalWS = N;
    output.uv0 = input.uv0;
    output.fogFactor = ComputeFogFactor(output.positionCS.z);
    return output;
}

half4 DT_OutlineFragment(DTOutlineVaryings input) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
    float2 uv = input.uv0;
    DT_ClipAlpha(uv);
    DTOutlineInput s;
    s.baseColor = DT_ColorInput(_DT_OutlineBaseColor, TEXTURE2D_ARGS(_DT_OutlineBaseColorMap, sampler_linear_repeat),
                                _DT_OutlineBaseColorMapOn, uv).rgb;
    s.outlineColor = DT_ColorInput(_DT_OutlineColor, TEXTURE2D_ARGS(_DT_OutlineColorMap, sampler_linear_repeat),
                                   _DT_OutlineColorMapOn, uv).rgb;
    s.lightBleed = _DT_OutlineLightBleed;
    s.tintDarkness = _DT_OutlineTintDarkness;
    s.tintSatBoost = _DT_OutlineTintSatBoost;
    s.lightingMix = _DT_OutlineLightingMix;
    s.tintMode = (int)round(_DT_OutlineTintMode);
    // EEVEE draws a flipped hull, so the line is shaded with the inverted normal.
    float3 N = -normalize(input.normalWS);
    InputData inputData = DT_MakeInputData(input.positionWS, N, input.positionCS, input.fogFactor);
    float3 diffuse = float3(0.0, 0.0, 0.0);
    if (s.lightingMix > 0.001)
    {
        diffuse = DT_DiffuseLight(inputData, N);
    }
    float3 c = dt_outline_color(s, DT_UnityToBlenderDir(N), diffuse);
    c = MixFog(c, inputData.fogCoord);
    return half4(c, 1.0);
}

#endif // DASKTOON_OUTLINE_INCLUDED
