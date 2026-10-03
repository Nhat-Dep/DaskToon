# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unity YAML text for materials and .meta files (spec 4). Pure functions: no bpy, no file access."""

import hashlib
import re

MATERIAL_FILE_ID = 2100000
TEXTURE_FILE_ID = 2800000
SHADER_FILE_ID = 4800000

_PLAIN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_ .()\-]*$")
_RESERVED = {"true", "false", "yes", "no", "on", "off", "null", "~"}
_TAIL = ["  userData: ", "  assetBundleName: ", "  assetBundleVariant: "]

# kind: (sRGBTexture, textureType, wrap, mipmaps, platform textureCompression) - spec 4, texture table.
TEXTURE_KINDS = {
    'COLOR': (1, 0, 0, 1, 2),
    'DATA': (0, 0, 0, 1, 0),
    'NORMAL': (0, 1, 0, 1, 2),
    'RAMP': (1, 0, 1, 0, 0),
}


def guid_for(name, relpath):
    """GUID of a model, material or texture: md5("dasktoon:<name>:<relative path>")."""
    key = "dasktoon:%s:%s" % (name, relpath.replace("\\", "/"))
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def linear_to_srgb(c):
    """Standard piecewise sRGB encoding; values above 1 follow the same curve (HDR colours)."""
    if c <= 0.0:
        return 0.0
    if c <= 0.0031308:
        return c * 12.92
    return 1.055 * c ** (1.0 / 2.4) - 0.055


def scalar(text):
    """A YAML scalar the way Unity writes it: plain when safe, single-quoted otherwise."""
    text = str(text)
    if _PLAIN.match(text) and not text.endswith(" ") and text.lower() not in _RESERVED:
        return text
    return "'" + text.replace("'", "''") + "'"


def number(value):
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    value = float(value)
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return "%.7g" % value


def _list(indent, key, items):
    if not items:
        return ["%s%s: []" % (indent, key)]
    return ["%s%s:" % (indent, key)] + ["%s- %s" % (indent, item) for item in items]


def _meta(guid, lines):
    return "\n".join(["fileFormatVersion: 2", "guid: " + guid] + lines + _TAIL) + "\n"


def material_yaml(name, shader_guid, keywords, queue, render_type, disabled_passes, floats, colors, textures):
    """A Material asset (serializedVersion 8). `colors` are linear RGBA and are written sRGB-encoded, the way
    Unity stores Color properties; `textures` maps a texture property to a texture GUID or None."""
    lines = [
        "%YAML 1.1",
        "%TAG !u! tag:unity3d.com,2011:",
        "--- !u!21 &2100000",
        "Material:",
        "  serializedVersion: 8",
        "  m_ObjectHideFlags: 0",
        "  m_CorrespondingSourceObject: {fileID: 0}",
        "  m_PrefabInstance: {fileID: 0}",
        "  m_PrefabAsset: {fileID: 0}",
        "  m_Name: " + scalar(name),
        "  m_Shader: {fileID: %d, guid: %s, type: 3}" % (SHADER_FILE_ID, shader_guid),
        "  m_Parent: {fileID: 0}",
        "  m_ModifiedSerializedProperties: 0",
    ]
    lines += _list("  ", "m_ValidKeywords", sorted(keywords))
    lines += [
        "  m_InvalidKeywords: []",
        "  m_LightmapFlags: 4",
        "  m_EnableInstancingVariants: 0",
        "  m_DoubleSidedGI: 0",
        "  m_CustomRenderQueue: %d" % queue,
        "  stringTagMap:",
        "    RenderType: " + render_type,
    ]
    lines += _list("  ", "disabledShaderPasses", list(disabled_passes))
    lines += ["  m_LockedProperties: ", "  m_SavedProperties:", "    serializedVersion: 3"]
    tex_lines = []
    for prop in sorted(textures):
        guid = textures[prop]
        ref = "{fileID: %d, guid: %s, type: 3}" % (TEXTURE_FILE_ID, guid) if guid else "{fileID: 0}"
        tex_lines += ["    - %s:" % prop, "        m_Texture: " + ref,
                      "        m_Scale: {x: 1, y: 1}", "        m_Offset: {x: 0, y: 0}"]
    lines += (["    m_TexEnvs:"] + tex_lines) if tex_lines else ["    m_TexEnvs: []"]
    lines.append("    m_Ints: []")
    lines += _list("    ", "m_Floats", ["%s: %s" % (k, number(v)) for k, v in sorted(floats.items())])
    lines += _list("    ", "m_Colors", [
        "%s: {r: %s, g: %s, b: %s, a: %s}" % (
            k, number(linear_to_srgb(v[0])), number(linear_to_srgb(v[1])), number(linear_to_srgb(v[2])),
            number(v[3]))
        for k, v in sorted(colors.items())])
    lines += ["  m_BuildTextureStacks: []", "  m_AllowLocking: 1"]
    return "\n".join(lines) + "\n"


def material_meta(guid):
    return _meta(guid, ["NativeFormatImporter:", "  externalObjects: {}", "  mainObjectFileID: %d" % MATERIAL_FILE_ID])


def folder_meta(guid):
    return _meta(guid, ["folderAsset: yes", "DefaultImporter:", "  externalObjects: {}"])


def default_meta(guid):
    return _meta(guid, ["DefaultImporter:", "  externalObjects: {}"])


def text_meta(guid):
    return _meta(guid, ["TextScriptImporter:", "  externalObjects: {}"])


def shader_meta(guid):
    return _meta(guid, ["ShaderImporter:", "  externalObjects: {}", "  defaultTextures: []",
                        "  nonModifiableTextures: []", "  preprocessorOverride: 0"])


def include_meta(guid):
    return _meta(guid, ["ShaderIncludeImporter:", "  externalObjects: {}"])


def texture_meta(guid, kind, size=(1024, 1024), point_filter=False):
    srgb, tex_type, wrap, mips, compression = TEXTURE_KINDS[kind]
    max_size = 2048
    while max_size < max(size) and max_size < 16384:
        max_size *= 2
    lines = [
        "TextureImporter:",
        "  internalIDToNameTable: []",
        "  externalObjects: {}",
        "  serializedVersion: 13",
        "  mipmaps:",
        "    mipMapMode: 0",
        "    enableMipMap: %d" % mips,
        "    sRGBTexture: %d" % srgb,
        "    linearTexture: 0",
        "    fadeOut: 0",
        "    borderMipMap: 0",
        "    mipMapsPreserveCoverage: 0",
        "    alphaTestReferenceValue: 0.5",
        "    mipMapFadeDistanceStart: 1",
        "    mipMapFadeDistanceEnd: 3",
        "  bumpmap:",
        "    convertToNormalMap: 0",
        "    externalNormalMap: 0",
        "    heightScale: 0.25",
        "    normalMapFilter: 0",
        "    flipGreenChannel: 0",
        "  isReadable: 0",
        "  streamingMipmaps: 0",
        "  streamingMipmapsPriority: 0",
        "  vTOnly: 0",
        "  ignoreMipmapLimit: 0",
        "  grayScaleToAlpha: 0",
        "  generateCubemap: 6",
        "  cubemapConvolution: 0",
        "  seamlessCubemap: 0",
        "  textureFormat: 1",
        "  maxTextureSize: %d" % max_size,
        "  textureSettings:",
        "    serializedVersion: 2",
        "    filterMode: %d" % (0 if point_filter else 1),
        "    aniso: 1",
        "    mipBias: 0",
        "    wrapU: %d" % wrap,
        "    wrapV: %d" % wrap,
        "    wrapW: %d" % wrap,
        "  nPOTScale: %d" % (0 if kind == 'RAMP' else 1),
        "  lightmap: 0",
        "  compressionQuality: 50",
        "  spriteMode: 0",
        "  alphaUsage: 1",
        "  alphaIsTransparency: 0",
        "  textureType: %d" % tex_type,
        "  textureShape: 1",
        "  platformSettings:",
        "  - serializedVersion: 4",
        "    buildTarget: DefaultTexturePlatform",
        "    maxTextureSize: %d" % max_size,
        "    resizeAlgorithm: 0",
        "    textureFormat: -1",
        "    textureCompression: %d" % compression,
        "    compressionQuality: 50",
        "    crunchedCompression: 0",
        "    allowsAlphaSplitting: 0",
        "    overridden: 0",
        "    ignorePlatformSupport: 0",
        "    androidETC2FallbackOverride: 0",
        "    forceMaximumCompressionQuality_BC6H_BC7: 0",
    ]
    return _meta(guid, lines)


def model_meta(guid, materials, import_animation):
    """ModelImporter of an exported FBX. `materials` maps an FBX material name to the GUID of its .mat, so Unity
    uses the exported materials without Search and Remap (spec 4)."""
    remap = []
    for name in sorted(materials):
        remap += ["  - first:", "      type: UnityEngine:Material", "      assembly: UnityEngine.CoreModule",
                  "      name: " + scalar(name),
                  "    second: {fileID: %d, guid: %s, type: 2}" % (MATERIAL_FILE_ID, materials[name])]
    lines = ["ModelImporter:", "  serializedVersion: 22200", "  internalIDToNameTable: []"]
    lines += (["  externalObjects:"] + remap) if remap else ["  externalObjects: {}"]
    lines += [
        "  materials:",
        "    materialImportMode: 2",
        "    materialName: 0",
        "    materialSearch: 1",
        "    materialLocation: 1",
        "  animations:",
        "    legacyGenerateAnimations: 4",
        "    bakeSimulation: 0",
        "    resampleCurves: 1",
        "    optimizeGameObjects: 0",
        "    removeConstantScaleCurves: 0",
        "    motionNodeName: ",
        "    animationImportErrors: ",
        "    animationImportWarnings: ",
        "    animationRetargetingWarnings: ",
        "    animationDoRetargetingWarnings: 0",
        "    importAnimatedCustomProperties: 0",
        "    importConstraints: 0",
        "    animationCompression: 1",
        "    animationRotationError: 0.5",
        "    animationPositionError: 0.5",
        "    animationScaleError: 0.5",
        "    animationWrapMode: 0",
        "    extraExposedTransformPaths: []",
        "    extraUserProperties: []",
        "    clipAnimations: []",
        "    isReadable: 0",
        "  meshes:",
        "    lODScreenPercentages: []",
        "    globalScale: 1",
        "    meshCompression: 0",
        "    addColliders: 0",
        "    useSRGBMaterialColor: 1",
        "    sortHierarchyByName: 1",
        "    importPhysicalCameras: 0",
        "    importVisibility: 1",
        "    importBlendShapes: 1",
        "    importCameras: 0",
        "    importLights: 0",
        "    nodeNameCollisionStrategy: 1",
        "    fileIdsGeneration: 2",
        "    swapUVChannels: 0",
        "    generateSecondaryUV: 0",
        "    useFileUnits: 1",
        "    keepQuads: 0",
        "    weldVertices: 1",
        "    bakeAxisConversion: 0",
        "    preserveHierarchy: 0",
        "    skinWeightsMode: 0",
        "    maxBonesPerVertex: 4",
        "    minBoneWeight: 0.001",
        "    optimizeBones: 1",
        "    meshOptimizationFlags: -1",
        "    indexFormat: 0",
        "    secondaryUVAngleDistortion: 8",
        "    secondaryUVAreaDistortion: 15.000001",
        "    secondaryUVHardAngle: 88",
        "    secondaryUVMarginMethod: 1",
        "    secondaryUVMinLightmapResolution: 40",
        "    secondaryUVMinObjectScale: 1",
        "    secondaryUVPackMargin: 4",
        "    useFileScale: 1",
        "    strictVertexDataChecks: 0",
        "  tangentSpace:",
        "    normalSmoothAngle: 60",
        "    normalImportMode: 0",
        "    tangentImportMode: 3",
        "    normalCalculationMode: 4",
        "    legacyComputeAllNormalsFromSmoothingGroupsWhenMeshHasBlendShapes: 0",
        "    blendShapeNormalImportMode: 0",
        "    normalSmoothingSource: 0",
        "  referencedClips: []",
        "  importAnimation: %d" % (1 if import_animation else 0),
        "  humanDescription:",
        "    serializedVersion: 3",
        "    human: []",
        "    skeleton: []",
        "    armTwist: 0.5",
        "    foreArmTwist: 0.5",
        "    upperLegTwist: 0.5",
        "    legTwist: 0.5",
        "    armStretch: 0.05",
        "    legStretch: 0.05",
        "    feetSpacing: 0",
        "    globalScale: 1",
        "    rootMotionBoneName: ",
        "    hasTranslationDoF: 0",
        "    hasExtraRoot: 0",
        "    skeletonHasParents: 1",
        "  lastHumanDescriptionAvatarSource: {instanceID: 0}",
        "  autoGenerateAvatarMappingIfUnspecified: 1",
        "  animationType: 2",
        "  humanoidOversampling: 1",
        "  avatarSetup: 1",
        "  addHumanoidExtraRootOnlyWhenUsingAvatar: 1",
        "  importBlendShapeDeformPercent: 1",
        "  remapMaterialsIfMaterialImportModeIsNone: 0",
        "  additionalBone: 0",
    ]
    return _meta(guid, lines)
