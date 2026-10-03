# DaskToon: Engine Export sang Unity 6 URP và Dự án DaskToon (Dự án 2) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Phiên này: người dùng đã chọn chạy **tự động, inline** (superpowers:executing-plans) trên nhánh `dasktoon-unity-export`, commit từng task, tự quyết các điểm mơ hồ và ghi vào báo cáo.

**Goal:** Một lệnh *File › Export › Engine Export…* xuất model FBX, material và shader của DaskToon thành một thư mục (hoặc ghi thẳng vào project Unity) để Unity 6 URP 17.5 hiển thị nhân vật giống render EEVEE nhất có thể; sau đó thêm hệ thống *Dự án DaskToon* gắn một thư mục `.blend` với một project Unity.

**Architecture:**
- Thư viện thuần Python `scripts/modules/dasktoon_export/` (đọc graph node → `MaterialSpec`, bake, ghi texture/`.mat`/`.meta`/FBX, cài shader) và `scripts/modules/dasktoon_project/` (file `dasktoon_project.json`, danh sách gần đây).
- Shader Unity viết tay trong `scripts/modules/dasktoon_export/unity_urp/`: `DaskToonCore.hlsl` (port công thức GLSL, không gọi URP), `DaskToonURP.hlsl` (gom ánh sáng theo nghĩa `closure_eval` của EEVEE), `DaskToonOutline.hlsl` (pass outline đẩy đỉnh theo `DT_OutlineN/W`), và một `.shader` cho mỗi node.
- Giao diện ở `scripts/startup/bl_ui/dasktoon_engine_export.py` và `scripts/startup/bl_ui/dasktoon_project.py`.
- Kiểm chứng: test headless trong `DaskToon.exe --background`, và test Unity 6000.5.4f1 batchmode trên một project tạm (`%TEMP%/dasktoon_unity_test`).

**Tech Stack:** Python `bpy` + `numpy`, HLSL/ShaderLab cho URP 17.5, C# editor script cho Unity batchmode, `unittest` chạy trong DaskToon.

**Spec:** `docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md` (hợp đồng với Dự án 1: `docs/superpowers/specs/2026-10-03-dasktoon-shading-outline-design.md`, mục 8).

---

## Môi trường và các lệnh dùng chung

Mọi lệnh chạy trong Git Bash, thư mục gốc là `d:/DaskToon`.

```bash
DT=/d/build_windows_x64_vc17_Release/bin/Release/DaskToon.exe
BUILD=/d/build_windows_x64_vc17_Release
UNITY="/c/Program Files/Unity/Hub/Editor/6000.5.4f1/Editor/Unity.exe"
```

- **Đồng bộ script** (dự án này không sửa C++ hay GLSL, nên không cần build). Chạy trước mỗi lần test:
  ```bash
  cp -r scripts/startup/. "$BUILD/bin/Release/5.2/scripts/startup/" && cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"
  ```
- **Chạy một file test** (exit code 0 là PASS):
  ```bash
  "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/<file>.py 2>&1 | tail -30
  ```
- **Test Unity** cũng chạy qua DaskToon (nó export rồi gọi Unity bằng `subprocess`). Project tạm nằm ở `%TEMP%/dasktoon_unity_test`
  (ghi đè bằng biến môi trường `DASKTOON_UNITY_PROJECT`; đường dẫn Unity ghi đè bằng `DASKTOON_UNITY`). Lần đầu tạo project mất
  khoảng 3–5 phút. Unity 6000.5 có thể crash **sau khi** đã chạy xong lúc tắt máy ảo (đã thấy segfault khi thoát), nên kết quả
  được đọc từ file `dt_result.json`, không dựa vào exit code của Unity.
- **Trích code từ kế hoạch:** mỗi khối code tạo file mới có dòng ``File: `đường/dẫn` `` ngay phía trên. Script trong scratchpad
  `plan_extract.py <plan> <task> <step>` ghi đúng các khối của bước đó ra file.

## Global Constraints

- Unity đích: **Unity 6000.5.4f1, URP 17.5.0, Linear color space**. Không hỗ trợ Built-in RP, HDRP, Unity 7, Unreal, Godot
  (Unreal 5 và Godot 4 hiện trong danh sách với chữ "sắp có").
- **Không bao giờ ghi vào project Unity của người dùng trong `D:\Unity\`.** Test chỉ dùng project tạm.
- Không push. Commit từng task trên nhánh `dasktoon-unity-export`.
- Không sửa C++/GLSL của DaskToon. Shader Unity phải port **đúng** công thức trong
  `source/blender/gpu/shaders/material/gpu_shader_material_{dasktoon_shading,anime_character,anime_cel,anime_eye,dask_cel,anime_angel_ring,dask_outline}.glsl`.
- Tên cố định (spec 4, 6):
  - Menu *File › Export › Engine Export…*, operator `export_scene.dasktoon_engine`.
  - Chế độ PROJECT ghi vào `<Project Unity>/Assets/DaskToon/`; chế độ FOLDER ghi vào `<thư mục chọn>/<Tên>_Unity/` kèm `README.txt`.
  - Bố cục: `Shaders/` (`DaskToonCore.hlsl`, `DaskToonURP.hlsl`, `DaskToonOutline.hlsl`, `AnimeBSDF.shader`, `AnimeCel.shader`,
    `AnimeEye.shader`, `DaskCel.shader`, `DaskToonShaders.version`), `<Tên>/Model/<Tên>.fbx`, `<Tên>/Materials/<material>.mat`,
    `<Tên>/Textures/<material>_<input>.png|.exr`, `<material>_Ramp.png`.
  - `<Tên>` = tên file `.blend` không đuôi, hoặc `Untitled`.
  - GUID model/material/texture = `md5("dasktoon:<Tên>:<đường dẫn tương đối>")`; shader và thư mục `Shaders` có GUID cố định.
  - Phiên bản shader `SHADER_VERSION = 1` trong `DaskToonShaders.version`.
  - Property Unity: `_BaseColor`/`_BaseMap`, còn lại tiền tố `_DT_`; bộ ba `_DT_<X>`, `_DT_<X>Map`, `_DT_<X>MapOn`.
  - Keyword (`shader_feature_local`): `_DT_RAMP`, `_DT_AMBIENT`, `_DT_LIGHT`, `_DT_AO`, `_DT_RIM`, `_DT_GRADE`, `_DT_OUTLINE`,
    `_DT_ANGEL_RING`, `_DT_ALPHATEST_ON`, `_DT_NORMALMAP`.
  - Pass outline: `LightMode = SRPDefaultUnlit`, tắt bằng `disabledShaderPasses` khi material không có outline.
  - FBX: `use_mesh_modifiers=False`, `axis_forward='-Z'`, `axis_up='Y'`, `apply_scale_options='FBX_SCALE_ALL'`,
    `add_leaf_bones=False`, `use_armature_deform_only=True`, `mesh_smooth_type='FACE'`, `object_types={'ARMATURE','MESH','EMPTY'}`.
  - Đơn vị: Directional của Unity = Sun ÷ π; ambient 1:1. Đổi trục: Blender `(x, y, z)` → Unity `(-x, z, -y)`.
- Màu trong `.mat` ghi sRGB (linear → sRGB piecewise, dùng được với giá trị > 1). Texture màu là PNG sRGB, số là PNG Non-Color,
  giá trị ngoài 0–1 là EXR.
- DaskToon chỉ ghi đè file do chính nó tạo (nhận ra nhờ GUID trong `.meta`), không bao giờ xóa file của người dùng.
- Dự án: file `dasktoon_project.json` = `{"version": 1, "name": ..., "engines": [{"engine": "UNITY_URP", "path": ...}]}`;
  danh sách gần đây tối đa 8, lưu ở `bpy.utils.user_resource('CONFIG', path="dasktoon/recent_projects.json")`, ghi đè bằng
  biến môi trường `DASKTOON_CONFIG_DIR`.
- Sai số so với EEVEE trong test Unity: cel và diffuse ≤ 0.03 (so trên giá trị sRGB 0–1). Specular và AO chỉ báo con số.

## Review Focus

1. **Tên material có ký tự đặc biệt** (`:`, `#`, `'`, dấu tiếng Việt, ký tự cấm trong tên file Windows). Người dùng mong file
   `.mat` hợp lệ, YAML đọc được, và FBX vẫn gán đúng material theo tên gốc. Test ở Task 2 (YAML) và Task 8 (bố cục).
2. **Export lại khi trong thư mục đích đã có file của người dùng trùng tên.** Người dùng mong file của họ không bị ghi đè.
   Test ở Task 3.
3. **File chưa lưu, slot material rỗng, một material dùng trên nhiều mesh có thứ tự UV khác nhau.** Người dùng mong export vẫn
   chạy, có cảnh báo rõ ràng. Test ở Task 5 và Task 8.
4. **Mesh có outline nhưng không có UV map hoặc có mặt nhiều hơn 4 cạnh.** Người dùng mong export vẫn xong, báo cáo nói rõ,
   và Unity dùng normal của mesh cho outline (`_DT_OutlineUV = -1`) thay vì đẩy đỉnh sai hướng. Test ở Task 7 và Task 8.
5. **Bake trên mesh dùng chung (linked duplicate).** Người dùng mong selection, object đang active, render engine và số sample
   của họ được trả lại nguyên vẹn, không còn đồ tạm trong file. Test ở Task 6.

## Cấu trúc file

| File | Trách nhiệm |
|---|---|
| `scripts/modules/dasktoon_export/__init__.py` | `ExportOptions`, `export_model(context, target, objects, options) -> Report` |
| `scripts/modules/dasktoon_export/unity_yaml.py` | Văn bản `.mat` và mọi loại `.meta`; `guid_for`, `linear_to_srgb` |
| `scripts/modules/dasktoon_export/assets.py` | Ghi file kèm `.meta`, chỉ ghi đè file của DaskToon; tạo thư mục kèm `.meta` |
| `scripts/modules/dasktoon_export/targets.py` | `ExportTarget`, nhận diện project Unity, chế độ PROJECT/FOLDER, nhớ đích theo file |
| `scripts/modules/dasktoon_export/shaders_install.py` | GUID cố định, `install_shaders`, `installed_version` |
| `scripts/modules/dasktoon_export/unity_urp/*` | Nguồn shader Unity |
| `scripts/modules/dasktoon_export/node_maps.py` | Bảng input → property Unity, enum → float, module → keyword |
| `scripts/modules/dasktoon_export/graph.py` | `analyze_material(mat, meshes) -> (MaterialSpec | None, lý do)` |
| `scripts/modules/dasktoon_export/textures.py` | PNG writer, texture dải màu, đọc file ảnh, EXR |
| `scripts/modules/dasktoon_export/bake.py` | `bake_input(...)` bằng Cycles Emit trên đồ tạm |
| `scripts/modules/dasktoon_export/model_fbx.py` | Chuẩn bị `DT_OutlineN/W`, chọn object, gọi FBX exporter, ghi chú modifier |
| `scripts/modules/dasktoon_export/report.py` | `Report`, gợi ý đèn, README, Text datablock, popup |
| `scripts/startup/bl_ui/dasktoon_engine_export.py` | Operator và mục menu Engine Export |
| `scripts/modules/dasktoon_project/project.py` | Đọc/ghi/nhận diện dự án, danh sách model, danh sách gần đây |
| `scripts/startup/bl_ui/dasktoon_project.py` | Menu *File › Dự án DaskToon*, panel *DaskToon › Dự án*, các operator |
| `tests/python/dasktoon_export_*_test.py`, `dasktoon_project_test.py` | Test headless |
| `tests/python/dasktoon_unity_harness.py` | Tạo/tái dùng project Unity tạm, chạy batchmode, đọc kết quả |
| `tests/python/dasktoon_unity_*_test.py` | Test trong Unity (bỏ qua nếu máy không có Unity 6000.5) |
| `tests/unity/Editor/*.cs` | Script C# được chép vào `Assets/Editor/` của project tạm |

---

### Task 1: Chạy được Unity batchmode trên project tạm (kiểm chứng sớm, spec mục 9)

**Files:**
- Create: `tests/python/dasktoon_unity_harness.py`
- Create: `tests/unity/Editor/DaskToonTests.cs`
- Test: `tests/python/dasktoon_unity_smoke_test.py`

**Interfaces:**
- Produces (Python, `dasktoon_unity_harness`): `unity_exe() -> str | None`, `project_dir() -> str`,
  `ensure_project() -> str` (tạo một lần, chép lại script C# mỗi lần, chạy `DaskToonTests.Setup` khi chưa có dấu
  `ProjectSettings/dt_setup_done`), `run_method(method: str, args: dict | None = None, timeout=1800) -> dict`
  (ghi `dt_args.json`, đọc `dt_result.json`), `SKIP_REASON: str`.
- Produces (C#): `DaskToonTests.Run(Func<Dictionary<string, object>>)`, `DaskToonTests.ArgsPath`,
  `DaskToonTests.RenderCamera(Camera, int, int) -> Texture2D` (float, linear), `DtJson.Write(object)`, các method
  `DaskToonTests.Setup` và `DaskToonTests.Smoke`.

- [ ] **Step 1: Viết test smoke (chưa có harness nên phải lỗi import)**

File: `tests/python/dasktoon_unity_smoke_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unity 6000.5 batchmode works on a throwaway URP project: license, URP 17.5, Linear, render read-back (spec 8, 9)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnitySmokeTest(unittest.TestCase):
    def test_batchmode_renders_with_urp_in_linear(self):
        harness.ensure_project()
        result = harness.run_method("DaskToonTests.Smoke")
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["colorSpace"], "Linear")
        self.assertTrue(result["urp"])
        # _BaseColor (0.25, 0.5, 0.75) is an sRGB value; the linear render target holds its linear form.
        for got, want in zip(result["center"], (0.0508, 0.2140, 0.5225)):
            self.assertAlmostEqual(got, want, delta=0.005)

    def test_project_is_outside_user_unity_folder(self):
        self.assertFalse(os.path.abspath(harness.project_dir()).lower().startswith("d:\\unity"))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, phải FAIL vì chưa có `dasktoon_unity_harness`**

Run: `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_unity_smoke_test.py 2>&1 | tail -5`
Expected: `ModuleNotFoundError: No module named 'dasktoon_unity_harness'`, exit code khác 0.

- [ ] **Step 3: Viết harness và script C#**

File: `tests/python/dasktoon_unity_harness.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Runs Unity 6000.5 in batchmode on a throwaway URP project (spec 8). Never touches the user's own projects."""

import glob
import json
import os
import shutil
import subprocess
import tempfile

UNITY_VERSION = "6000.5.4f1"
DEFAULT_UNITY = r"C:\Program Files\Unity\Hub\Editor\6000.5.4f1\Editor\Unity.exe"
SKIP_REASON = "Unity %s not installed (set DASKTOON_UNITY)" % UNITY_VERSION
TESTS_UNITY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "unity")
SETUP_MARKER = os.path.join("ProjectSettings", "dt_setup_done")
MANIFEST = {"dependencies": {
    "com.unity.render-pipelines.universal": "17.5.0",
    "com.unity.modules.animation": "1.0.0",
    "com.unity.modules.imageconversion": "1.0.0",
    "com.unity.modules.jsonserialize": "1.0.0",
}}


def unity_exe():
    path = os.environ.get("DASKTOON_UNITY", DEFAULT_UNITY)
    return path if os.path.isfile(path) else None


def project_dir():
    return os.environ.get("DASKTOON_UNITY_PROJECT") or os.path.join(tempfile.gettempdir(), "dasktoon_unity_test")


def _write_if_missing(path, text):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def ensure_project():
    """Create the test project once; the C# test scripts are refreshed on every call."""
    root = project_dir()
    # A ProjectVersion.txt written up front stops Unity from treating the folder as a new project and
    # replacing the manifest with its default template.
    _write_if_missing(os.path.join(root, "Packages", "manifest.json"), json.dumps(MANIFEST, indent=2))
    _write_if_missing(os.path.join(root, "ProjectSettings", "ProjectVersion.txt"),
                      "m_EditorVersion: %s\n" % UNITY_VERSION)
    editor_dir = os.path.join(root, "Assets", "Editor")
    os.makedirs(editor_dir, exist_ok=True)
    for source in glob.glob(os.path.join(TESTS_UNITY_DIR, "Editor", "*.cs")):
        shutil.copyfile(source, os.path.join(editor_dir, os.path.basename(source)))
    if not os.path.exists(os.path.join(root, SETUP_MARKER)):
        result = run_method("DaskToonTests.Setup")
        if not result.get("ok"):
            raise RuntimeError("Unity setup failed: %s" % result.get("error"))
        _write_if_missing(os.path.join(root, SETUP_MARKER), "ok\n")
    return root


def run_method(method, args=None, timeout=1800):
    """Run a static C# method in batchmode. It writes dt_result.json; that file is the verdict
    (Unity 6000.5 can crash while shutting down after a successful run)."""
    root = project_dir()
    result_path = os.path.join(root, "dt_result.json")
    args_path = os.path.join(root, "dt_args.json")
    for path in (result_path, args_path):
        if os.path.exists(path):
            os.remove(path)
    if args is not None:
        with open(args_path, "w", encoding="utf-8") as f:
            json.dump(args, f)
    log = os.path.join(root, "dt_unity_%s.log" % method.rsplit(".", 1)[-1])
    cmd = [unity_exe(), "-batchmode", "-projectPath", root, "-executeMethod", method, "-logFile", log]
    subprocess.run(cmd, timeout=timeout, check=False)
    if not os.path.exists(result_path):
        raise RuntimeError("Unity wrote no result for %s; see %s" % (method, log))
    with open(result_path, encoding="utf-8") as f:
        return json.load(f)
```

File: `tests/unity/Editor/DaskToonTests.cs`
```csharp
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
```

- [ ] **Step 4: Chạy test smoke (lần đầu tạo project mất vài phút, chạy nền)**

Run: `"$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_unity_smoke_test.py 2>&1 | tail -8`
Expected: `Ran 2 tests ... OK`. Nếu Unity không chạy được vì license hoặc GPU: ghi `Ruling:` vào ledger, đổi các test Unity thành
hướng dẫn chạy tay trong báo cáo, rồi tiếp tục các task headless.

- [ ] **Step 5: Commit**

```bash
git add tests/python/dasktoon_unity_harness.py tests/python/dasktoon_unity_smoke_test.py tests/unity/Editor/DaskToonTests.cs
git commit -m "test: run Unity 6000.5 batchmode on a throwaway URP project for the DaskToon export tests"
```

### Task 2: Văn bản YAML của Unity (`.mat` và mọi loại `.meta`)

**Files:**
- Create: `scripts/modules/dasktoon_export/__init__.py` (tạm thời chỉ có docstring; Task 8 viết phần còn lại)
- Create: `scripts/modules/dasktoon_export/unity_yaml.py`
- Test: `tests/python/dasktoon_export_yaml_test.py`

**Interfaces:**
- Produces: `guid_for(name: str, relpath: str) -> str`, `linear_to_srgb(c: float) -> float`, `scalar(text) -> str`,
  `number(value) -> str`, `material_yaml(name, shader_guid, keywords, queue, render_type, disabled_passes, floats, colors, textures) -> str`
  (`colors` là RGBA linear, `textures` là `{property: guid | None}`), `material_meta(guid)`, `texture_meta(guid, kind, size=(1024, 1024), point_filter=False)`
  với `kind ∈ {'COLOR', 'DATA', 'NORMAL', 'RAMP'}`, `model_meta(guid, materials: {tên FBX: guid}, import_animation: bool)`,
  `folder_meta(guid)`, `shader_meta(guid)`, `include_meta(guid)`, `default_meta(guid)`, `text_meta(guid)`.

- [ ] **Step 1: Viết test golden**

File: `tests/python/dasktoon_export_yaml_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unity YAML written by the exporter matches Unity's own format (spec 4)."""

import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_export import unity_yaml as uy  # noqa: E402

SHADER = "651389b857c37954216341111b253e67"
TEX = "0123456789abcdef0123456789abcdef"

GOLDEN_MAT = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  m_Name: Skin
  m_Shader: {fileID: 4800000, guid: 651389b857c37954216341111b253e67, type: 3}
  m_Parent: {fileID: 0}
  m_ModifiedSerializedProperties: 0
  m_ValidKeywords:
  - _DT_AMBIENT
  - _DT_RIM
  m_InvalidKeywords: []
  m_LightmapFlags: 4
  m_EnableInstancingVariants: 0
  m_DoubleSidedGI: 0
  m_CustomRenderQueue: -1
  stringTagMap:
    RenderType: Opaque
  disabledShaderPasses:
  - SRPDefaultUnlit
  m_LockedProperties: 
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
    - _BaseMap:
        m_Texture: {fileID: 2800000, guid: 0123456789abcdef0123456789abcdef, type: 3}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    - _DT_ShadowColorMap:
        m_Texture: {fileID: 0}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    m_Ints: []
    m_Floats:
    - _Cull: 2
    - _DT_ShadowThreshold: 0.46
    m_Colors:
    - _BaseColor: {r: 1, g: 0.735357, b: 0, a: 1}
  m_BuildTextureStacks: []
  m_AllowLocking: 1
"""


def golden_material(**overrides):
    args = dict(name="Skin", shader_guid=SHADER, keywords={"_DT_RIM", "_DT_AMBIENT"}, queue=-1,
                render_type="Opaque", disabled_passes=["SRPDefaultUnlit"],
                floats={"_DT_ShadowThreshold": 0.46, "_Cull": 2.0},
                colors={"_BaseColor": (1.0, 0.5, 0.0, 1.0)},
                textures={"_BaseMap": TEX, "_DT_ShadowColorMap": None})
    args.update(overrides)
    return uy.material_yaml(**args)


class YamlTest(unittest.TestCase):
    def test_guid_is_md5_of_model_name_and_relative_path(self):
        want = hashlib.md5(b"dasktoon:Hero:Hero/Materials/Skin.mat").hexdigest()
        self.assertEqual(uy.guid_for("Hero", "Hero/Materials/Skin.mat"), want)
        self.assertEqual(uy.guid_for("Hero", "Hero\\Materials\\Skin.mat"), want)

    def test_linear_to_srgb_piecewise_and_above_one(self):
        self.assertEqual(uy.linear_to_srgb(0.0), 0.0)
        self.assertEqual(uy.linear_to_srgb(-0.5), 0.0)
        self.assertAlmostEqual(uy.linear_to_srgb(0.002), 0.02584, places=5)
        self.assertAlmostEqual(uy.linear_to_srgb(0.5), 0.735357, places=6)
        self.assertAlmostEqual(uy.linear_to_srgb(2.0), 1.353256, places=6)

    def test_material_matches_golden(self):
        self.assertEqual(golden_material(), GOLDEN_MAT)

    def test_material_name_with_special_characters_is_quoted(self):
        text = golden_material(name="Áo: đỏ #1")
        self.assertIn("  m_Name: 'Áo: đỏ #1'\n", text)
        self.assertIn("  m_Name: 'It''s'\n", golden_material(name="It's"))

    def test_empty_lists_are_inline(self):
        text = golden_material(keywords=set(), disabled_passes=[], textures={}, floats={}, colors={})
        self.assertIn("  m_ValidKeywords: []\n", text)
        self.assertIn("  disabledShaderPasses: []\n", text)
        self.assertIn("    m_TexEnvs: []\n", text)
        self.assertIn("    m_Floats: []\n", text)
        self.assertIn("    m_Colors: []\n", text)

    def test_texture_meta_follows_spec_table(self):
        color = uy.texture_meta(TEX, 'COLOR')
        self.assertIn("    sRGBTexture: 1\n", color)
        self.assertIn("    textureCompression: 2\n", color)
        self.assertIn("    wrapU: 0\n", color)
        self.assertIn("    enableMipMap: 1\n", color)
        data = uy.texture_meta(TEX, 'DATA')
        self.assertIn("    sRGBTexture: 0\n", data)
        self.assertIn("    textureCompression: 0\n", data)
        self.assertIn("  textureType: 1\n", uy.texture_meta(TEX, 'NORMAL'))
        ramp = uy.texture_meta(TEX, 'RAMP', size=(256, 1), point_filter=True)
        self.assertIn("    wrapU: 1\n", ramp)
        self.assertIn("    enableMipMap: 0\n", ramp)
        self.assertIn("    filterMode: 0\n", ramp)
        self.assertIn("  nPOTScale: 0\n", ramp)
        self.assertIn("  maxTextureSize: 4096\n", uy.texture_meta(TEX, 'COLOR', size=(4096, 2048)))
        self.assertTrue(color.startswith("fileFormatVersion: 2\nguid: %s\nTextureImporter:\n" % TEX))

    def test_model_meta_remaps_materials_by_fbx_name(self):
        text = uy.model_meta(TEX, {"Skin": "a" * 32, "Áo": "b" * 32}, True)
        self.assertIn("ModelImporter:\n", text)
        self.assertIn("  externalObjects:\n  - first:\n      type: UnityEngine:Material\n"
                      "      assembly: UnityEngine.CoreModule\n      name: Skin\n"
                      "    second: {fileID: 2100000, guid: %s, type: 2}\n" % ("a" * 32), text)
        self.assertIn("      name: 'Áo'\n", text)
        for line in ("    importBlendShapes: 1\n", "    normalImportMode: 0\n", "    tangentImportMode: 3\n",
                     "    blendShapeNormalImportMode: 0\n", "  importAnimation: 1\n"):
            self.assertIn(line, text)
        bare = uy.model_meta(TEX, {}, False)
        self.assertIn("  externalObjects: {}\n", bare)
        self.assertIn("  importAnimation: 0\n", bare)

    def test_simple_metas(self):
        head = "fileFormatVersion: 2\nguid: %s\n" % TEX
        cases = {
            uy.folder_meta: "folderAsset: yes\nDefaultImporter:\n",
            uy.default_meta: "DefaultImporter:\n",
            uy.text_meta: "TextScriptImporter:\n",
            uy.shader_meta: "ShaderImporter:\n",
            uy.include_meta: "ShaderIncludeImporter:\n",
            uy.material_meta: "NativeFormatImporter:\n",
        }
        for func, body in cases.items():
            text = func(TEX)
            self.assertTrue(text.startswith(head + body), func.__name__)
            self.assertTrue(text.endswith("  assetBundleVariant: \n"), func.__name__)
        self.assertIn("  mainObjectFileID: 2100000\n", uy.material_meta(TEX))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Đồng bộ script, chạy test, phải FAIL**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_yaml_test.py 2>&1 | tail -5`
Expected: `ModuleNotFoundError: No module named 'dasktoon_export'`.

- [ ] **Step 3: Viết module**

File: `scripts/modules/dasktoon_export/__init__.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon Engine Export: model, materials and shaders for game engines.
Design: docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md"""
```

File: `scripts/modules/dasktoon_export/unity_yaml.py`
```python
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
```

- [ ] **Step 4: Đồng bộ và chạy lại test, phải PASS**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_yaml_test.py 2>&1 | tail -5`
Expected: `Ran 8 tests ... OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/modules/dasktoon_export/__init__.py scripts/modules/dasktoon_export/unity_yaml.py tests/python/dasktoon_export_yaml_test.py
git commit -m "feat: write Unity material and meta YAML for DaskToon Engine Export"
```

---

### Task 3: Đích export và ghi file an toàn (`targets.py`, `assets.py`)

**Files:**
- Create: `scripts/modules/dasktoon_export/targets.py`
- Create: `scripts/modules/dasktoon_export/assets.py`
- Test: `tests/python/dasktoon_export_targets_test.py`

**Interfaces:**
- Consumes: `unity_yaml.folder_meta(guid)`.
- Produces (`targets`): `ENGINES` (items cho EnumProperty), `SUPPORTED_ENGINES = {'UNITY_URP'}`, `TARGET_PROP = "dasktoon_engine_target"`,
  `ExportTarget(engine, mode, root, name, project="")` (frozen dataclass; `mode ∈ {'PROJECT', 'FOLDER'}`),
  `find_unity_project(path) -> str | None`, `is_unity_project(path) -> bool`, `blend_name(filepath) -> str`,
  `make_target(directory, name, engine='UNITY_URP') -> ExportTarget`, `remember_target(scene, directory, engine)`,
  `remembered_target(scene) -> (directory, engine) | None`.
- Produces (`assets`): `read_meta_guid(meta_path) -> str | None`, `is_ours(path, guid) -> bool`,
  `write_asset(root, relpath, guid, meta, warnings, data=None, writer=None) -> bool` (`writer(tmp_path)` ghi file khi không
  truyền `data`), `ensure_folder(root, relpath, guid)`.

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_export_targets_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Export destinations (PROJECT / FOLDER) and safe writing next to .meta files (spec 4)."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_export import assets, targets, unity_yaml  # noqa: E402


def fake_unity_project(parent, name="Game"):
    root = os.path.join(parent, name)
    os.makedirs(os.path.join(root, "Assets", "Characters"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


class TargetsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dt_targets_")

    def test_unity_project_is_found_from_a_subfolder(self):
        project = fake_unity_project(self.tmp)
        self.assertEqual(targets.find_unity_project(os.path.join(project, "Assets", "Characters")), project)
        self.assertTrue(targets.is_unity_project(project))
        self.assertIsNone(targets.find_unity_project(self.tmp))

    def test_project_mode_writes_into_assets_dasktoon(self):
        project = fake_unity_project(self.tmp)
        target = targets.make_target(os.path.join(project, "Assets", "Characters"), "Hero")
        self.assertEqual(target.mode, 'PROJECT')
        self.assertEqual(target.root, os.path.join(project, "Assets", "DaskToon"))
        self.assertEqual(target.project, project)
        self.assertEqual(target.name, "Hero")

    def test_folder_mode_makes_name_unity_folder(self):
        target = targets.make_target(self.tmp, "Hero")
        self.assertEqual(target.mode, 'FOLDER')
        self.assertEqual(target.root, os.path.join(self.tmp, "Hero_Unity"))

    def test_blend_name(self):
        self.assertEqual(targets.blend_name(""), "Untitled")
        self.assertEqual(targets.blend_name("C:/work/Hero.blend"), "Hero")

    def test_target_is_remembered_per_blend_file(self):
        tu.reset_scene()
        scene = bpy.context.scene
        self.assertIsNone(targets.remembered_target(scene))
        targets.remember_target(scene, self.tmp, 'UNITY_URP')
        self.assertEqual(targets.remembered_target(scene), (self.tmp, 'UNITY_URP'))


class AssetsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="dt_assets_")
        self.guid = unity_yaml.guid_for("Hero", "Hero/Materials/Skin.mat")

    def read(self, relpath):
        with open(os.path.join(self.root, relpath), "rb") as f:
            return f.read()

    def test_writes_file_and_meta_and_overwrites_its_own_file(self):
        warnings = []
        meta = unity_yaml.material_meta(self.guid)
        self.assertTrue(assets.write_asset(self.root, "Hero/Materials/Skin.mat", self.guid, meta, warnings, data=b"one"))
        self.assertTrue(assets.write_asset(self.root, "Hero/Materials/Skin.mat", self.guid, meta, warnings, data=b"two"))
        self.assertEqual(self.read("Hero/Materials/Skin.mat"), b"two")
        self.assertEqual(assets.read_meta_guid(os.path.join(self.root, "Hero/Materials/Skin.mat.meta")), self.guid)
        self.assertEqual(warnings, [])
        self.assertFalse(any(name.endswith(".tmp") for name in os.listdir(os.path.join(self.root, "Hero/Materials"))))

    def test_never_overwrites_a_user_file(self):
        os.makedirs(os.path.join(self.root, "Hero/Materials"))
        with open(os.path.join(self.root, "Hero/Materials/Skin.mat"), "wb") as f:
            f.write(b"user")
        warnings = []
        ok = assets.write_asset(self.root, "Hero/Materials/Skin.mat", self.guid, unity_yaml.material_meta(self.guid),
                                warnings, data=b"dasktoon")
        self.assertFalse(ok)
        self.assertEqual(self.read("Hero/Materials/Skin.mat"), b"user")
        self.assertFalse(os.path.exists(os.path.join(self.root, "Hero/Materials/Skin.mat.meta")))
        self.assertEqual(len(warnings), 1)
        other = unity_yaml.material_meta("f" * 32)
        with open(os.path.join(self.root, "Hero/Materials/Skin.mat.meta"), "w", encoding="utf-8") as f:
            f.write(other)
        self.assertFalse(assets.write_asset(self.root, "Hero/Materials/Skin.mat", self.guid,
                                            unity_yaml.material_meta(self.guid), warnings, data=b"dasktoon"))
        self.assertEqual(self.read("Hero/Materials/Skin.mat"), b"user")

    def test_writer_callback(self):
        def writer(path):
            with open(path, "wb") as f:
                f.write(b"fbx")
        self.assertTrue(assets.write_asset(self.root, "Hero/Model/Hero.fbx", self.guid, unity_yaml.default_meta(self.guid),
                                           [], writer=writer))
        self.assertEqual(self.read("Hero/Model/Hero.fbx"), b"fbx")

    def test_folder_meta_is_written_once(self):
        assets.ensure_folder(self.root, "Hero", "a" * 32)
        self.assertEqual(assets.read_meta_guid(os.path.join(self.root, "Hero.meta")), "a" * 32)
        assets.ensure_folder(self.root, "Hero", "b" * 32)
        self.assertEqual(assets.read_meta_guid(os.path.join(self.root, "Hero.meta")), "a" * 32)
        self.assertIn("folderAsset: yes", self.read("Hero.meta").decode("utf-8"))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, phải FAIL**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_targets_test.py 2>&1 | tail -5`
Expected: `ImportError: cannot import name 'assets'`.

- [ ] **Step 3: Viết hai module**

File: `scripts/modules/dasktoon_export/targets.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Where an export goes: straight into a Unity project (PROJECT) or into a folder to drag into Unity (FOLDER). Spec 4."""

import os
from dataclasses import dataclass

ENGINES = (
    ('UNITY_URP', "Unity 6 (URP)", "Unity 6, Universal Render Pipeline 17.5"),
    ('UNREAL_5', "Unreal 5 (sắp có)", "Chưa hỗ trợ"),
    ('GODOT_4', "Godot 4 (sắp có)", "Chưa hỗ trợ"),
)
SUPPORTED_ENGINES = {'UNITY_URP'}
TARGET_PROP = "dasktoon_engine_target"
UNTITLED = "Untitled"


@dataclass(frozen=True)
class ExportTarget:
    engine: str
    mode: str      # 'PROJECT' or 'FOLDER'
    root: str      # folder that receives Shaders/ and <name>/
    name: str      # model name: the .blend file name without extension
    project: str = ""


def is_unity_project(path):
    return os.path.isdir(os.path.join(path, "Assets")) and os.path.isdir(os.path.join(path, "ProjectSettings"))


def find_unity_project(path):
    """Walk up from `path`; the first folder holding both Assets/ and ProjectSettings/ is a Unity project."""
    current = os.path.abspath(path)
    while True:
        if is_unity_project(current):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def blend_name(filepath):
    if not filepath:
        return UNTITLED
    return os.path.splitext(os.path.basename(filepath))[0] or UNTITLED


def make_target(directory, name, engine='UNITY_URP'):
    project = find_unity_project(directory)
    if project:
        return ExportTarget(engine, 'PROJECT', os.path.join(project, "Assets", "DaskToon"), name, project)
    return ExportTarget(engine, 'FOLDER', os.path.join(os.path.abspath(directory), name + "_Unity"), name)


def remember_target(scene, directory, engine):
    scene[TARGET_PROP] = {"directory": directory, "engine": engine}


def remembered_target(scene):
    data = scene.get(TARGET_PROP)
    if data is None:
        return None
    data = data.to_dict() if hasattr(data, "to_dict") else dict(data)
    if not data.get("directory"):
        return None
    return data["directory"], data.get("engine", 'UNITY_URP')
```

File: `scripts/modules/dasktoon_export/assets.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Exported files and their .meta. DaskToon only overwrites what it wrote itself (same GUID) and never deletes
anything (spec 4, 9)."""

import os

from . import unity_yaml


def read_meta_guid(meta_path):
    try:
        with open(meta_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("guid:"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return None


def is_ours(path, guid):
    """True when `path` is free or holds a file DaskToon wrote earlier (its .meta carries `guid`)."""
    if not os.path.exists(path) and not os.path.exists(path + ".meta"):
        return True
    return read_meta_guid(path + ".meta") == guid


def _replace(path, writer):
    # Unity ignores *.tmp files, so a half-written file is never imported.
    tmp = path + ".tmp"
    writer(tmp)
    os.replace(tmp, path)


def _write_bytes(path, data):
    def writer(tmp):
        with open(tmp, "wb") as f:
            f.write(data)
    _replace(path, writer)


def write_asset(root, relpath, guid, meta, warnings, data=None, writer=None):
    """Write <root>/<relpath> and its .meta (meta first, so a file is never left without its GUID)."""
    path = os.path.join(root, relpath)
    if not is_ours(path, guid):
        warnings.append("Bỏ qua %s: file đã có sẵn và không do DaskToon tạo" % relpath.replace("\\", "/"))
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _write_bytes(path + ".meta", meta.encode("utf-8"))
    if writer is None:
        _write_bytes(path, data)
    else:
        _replace(path, writer)
    return True


def ensure_folder(root, relpath, guid):
    """Create a folder with its folder .meta; an existing .meta is left alone."""
    path = os.path.join(root, relpath)
    os.makedirs(path, exist_ok=True)
    if not os.path.exists(path + ".meta"):
        _write_bytes(path + ".meta", unity_yaml.folder_meta(guid).encode("utf-8"))
```

- [ ] **Step 4: Chạy lại test, phải PASS**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_targets_test.py 2>&1 | tail -5`
Expected: `Ran 9 tests ... OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/modules/dasktoon_export/targets.py scripts/modules/dasktoon_export/assets.py tests/python/dasktoon_export_targets_test.py
git commit -m "feat: detect Unity projects for Engine Export and write assets without touching user files"
```

### Task 4: Shader Unity URP và bộ cài shader

**Files:**
- Create: `scripts/modules/dasktoon_export/unity_urp/DaskToonCore.hlsl`
- Create: `scripts/modules/dasktoon_export/unity_urp/DaskToonURP.hlsl`
- Create: `scripts/modules/dasktoon_export/unity_urp/DaskToonOutline.hlsl`
- Create: `scripts/modules/dasktoon_export/unity_urp/AnimeBSDF.shader`, `AnimeCel.shader`, `AnimeEye.shader`, `DaskCel.shader`
- Create: `scripts/modules/dasktoon_export/shaders_install.py`
- Create: `tests/unity/Editor/DaskToonShaderTests.cs`
- Test: `tests/python/dasktoon_export_shaders_test.py`, `tests/python/dasktoon_unity_shaders_test.py`

**Interfaces:**
- Consumes: `assets.write_asset`, `assets.ensure_folder`, `unity_yaml.{shader_meta, include_meta, default_meta}`, `targets.ExportTarget`.
- Produces (`shaders_install`): `SHADER_VERSION = 1`, `SHADER_DIR = "Shaders"`, `VERSION_FILE`, `FILE_GUIDS`, `ROOT_FOLDER_GUID`,
  `SHADERS_FOLDER_GUID`, `SHADER_NAMES`, `shader_guid(shader) -> str`, `installed_version(root) -> int`, `ensure_root(target)`,
  `install_shaders(target, warnings, force=False) -> bool`.
- Produces (shader, dùng ở Task 5 và 8): tên property và keyword đúng như bảng ở Task 5. Mọi shader có các property chung
  `_DT_Outline*`, `_DT_OutlineUV`, `_DT_OutlineWUV` (−1 = không có dữ liệu, dùng normal của mesh), `_Cutoff`, `_AlphaClip`,
  `_SrcBlend`, `_DstBlend`, `_ZWrite`, `_Cull`, `_Surface`, và cờ hiện thị cho mỗi keyword (`_DT_UseRamp`, `_DT_UseAmbient`,
  `_DT_UseLight`, `_DT_UseAO`, `_DT_UseRim`, `_DT_UseGrade`, `_DT_UseOutline`, `_DT_UseAngelRing`, `_DT_UseNormalMap`).
- Produces (C#): `DaskToonShaderTests.CompileShaders` → `{"ok", "errors": [...], "compiled": int}`.

- [ ] **Step 1: Viết test headless cho bộ cài và cho phần port**

File: `tests/python/dasktoon_export_shaders_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Shader install (fixed GUIDs, version file) and static checks of the Unity shader sources (spec 4, 6)."""

import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_export import assets, shaders_install as si, targets  # noqa: E402

GLSL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "source", "blender", "gpu", "shaders", "material")
KEYWORDS = {"_DT_RAMP", "_DT_AMBIENT", "_DT_LIGHT", "_DT_AO", "_DT_RIM", "_DT_GRADE", "_DT_OUTLINE",
            "_DT_ANGEL_RING", "_DT_ALPHATEST_ON", "_DT_NORMALMAP"}


def fake_project():
    root = os.path.join(tempfile.mkdtemp(prefix="dt_shaders_"), "Game")
    os.makedirs(os.path.join(root, "Assets"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.project = fake_project()
        self.target = targets.make_target(self.project, "Hero")
        self.shaders = os.path.join(self.target.root, si.SHADER_DIR)

    def test_first_install_writes_every_file_with_fixed_guid(self):
        self.assertTrue(si.install_shaders(self.target, []))
        for name, guid in si.FILE_GUIDS.items():
            self.assertTrue(os.path.isfile(os.path.join(self.shaders, name)), name)
            self.assertEqual(assets.read_meta_guid(os.path.join(self.shaders, name + ".meta")), guid)
        self.assertEqual(si.installed_version(self.target.root), si.SHADER_VERSION)
        self.assertEqual(assets.read_meta_guid(self.shaders + ".meta"), si.SHADERS_FOLDER_GUID)
        self.assertEqual(assets.read_meta_guid(self.target.root + ".meta"), si.ROOT_FOLDER_GUID)
        self.assertIn("ShaderImporter:", read(os.path.join(self.shaders, "AnimeBSDF.shader.meta")))
        self.assertIn("ShaderIncludeImporter:", read(os.path.join(self.shaders, "DaskToonCore.hlsl.meta")))

    def test_up_to_date_project_install_is_skipped(self):
        si.install_shaders(self.target, [])
        edited = os.path.join(self.shaders, "AnimeBSDF.shader")
        with open(edited, "w", encoding="utf-8") as f:
            f.write("edited")
        self.assertFalse(si.install_shaders(self.target, []))
        self.assertEqual(read(edited), "edited")
        self.assertTrue(si.install_shaders(self.target, [], force=True))
        self.assertNotEqual(read(edited), "edited")

    def test_newer_version_overwrites(self):
        si.install_shaders(self.target, [])
        edited = os.path.join(self.shaders, "AnimeBSDF.shader")
        with open(edited, "w", encoding="utf-8") as f:
            f.write("edited")
        old = si.SHADER_VERSION
        si.SHADER_VERSION = old + 1
        try:
            self.assertTrue(si.install_shaders(self.target, []))
            self.assertEqual(si.installed_version(self.target.root), old + 1)
        finally:
            si.SHADER_VERSION = old
        self.assertNotEqual(read(edited), "edited")

    def test_folder_mode_always_writes(self):
        target = targets.make_target(tempfile.mkdtemp(prefix="dt_folder_"), "Hero")
        self.assertTrue(si.install_shaders(target, []))
        self.assertTrue(si.install_shaders(target, []))


class SourceTest(unittest.TestCase):
    def test_every_shader_has_the_passes_and_name(self):
        for name in si.SHADER_NAMES:
            text = read(os.path.join(si.SOURCE_DIR, name + ".shader"))
            self.assertIn('Shader "DaskToon/%s"' % name, text)
            for light_mode in ("UniversalForward", "SRPDefaultUnlit", "ShadowCaster", "DepthOnly", "DepthNormals"):
                self.assertIn('"LightMode" = "%s"' % light_mode, text, name)
            self.assertIn("DT_SHARED_MATERIAL_FIELDS", text, name)
            self.assertIn("float DT_SurfaceAlpha(float2 uv)", text, name)

    def test_every_keyword_is_declared(self):
        declared = set()
        for name in si.SHADER_NAMES:
            declared |= set(re.findall(r"shader_feature_local\w*\s+(_DT_\w+)",
                                       read(os.path.join(si.SOURCE_DIR, name + ".shader"))))
        self.assertEqual(declared, KEYWORDS)

    def test_core_ports_every_shared_glsl_function(self):
        glsl = read(os.path.join(GLSL_DIR, "gpu_shader_material_dasktoon_shading.glsl"))
        core = read(os.path.join(si.SOURCE_DIR, "DaskToonCore.hlsl"))
        for func in re.findall(r"^\w+\s+(dt_\w+)\(", glsl, re.MULTILINE):
            self.assertRegex(core, r"\b%s\(" % func)
        # Constants of the node formulas that must survive the port unchanged.
        for constant in ("0.0001", "1.25", "0.75", "0.65", "0.299, 0.587, 0.114", "0.2126, 0.7152, 0.0722",
                         "0.16, 0.22", "2.2", "0.45, 0.85", "0.035, 0.055", "0.018, 0.032", "0.55", "0.45",
                         "6.28", "0.5, 0.8, 0.6", "3.33", "0.03", "1.4", "0.35", "50.0"):
            self.assertIn(constant, core, constant)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, phải FAIL**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_shaders_test.py 2>&1 | tail -5`
Expected: `ImportError: cannot import name 'shaders_install'`.

- [ ] **Step 3: Viết lõi port `DaskToonCore.hlsl`**

File: `scripts/modules/dasktoon_export/unity_urp/DaskToonCore.hlsl`
```hlsl
// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// DaskToon shading core for Unity: a line-by-line port of DaskToon's GLSL node functions in
// source/blender/gpu/shaders/material/gpu_shader_material_*.glsl. This file calls no URP function: lighting
// arrives in DTLighting, gathered by DaskToonURP.hlsl with the meaning of EEVEE's closure_eval(). It only needs
// the SRP Core macros (TEXTURE2D, SAMPLER, ...), which every DaskToon shader includes first.

#ifndef DASKTOON_CORE_INCLUDED
#define DASKTOON_CORE_INCLUDED

#define DT_PI 3.14159265

// Material fields every DaskToon shader has (outline pass, alpha clip). Each .shader puts this macro inside its
// UnityPerMaterial CBUFFER, so all passes share one layout (SRP Batcher).
#define DT_SHARED_MATERIAL_FIELDS \
    float4 _DT_OutlineColor; \
    float4 _DT_OutlineBaseColor; \
    float _DT_OutlineColorMapOn; \
    float _DT_OutlineBaseColorMapOn; \
    float _DT_OutlineWidth; \
    float _DT_OutlineLightBleed; \
    float _DT_OutlineWobble; \
    float _DT_OutlineTintDarkness; \
    float _DT_OutlineTintSatBoost; \
    float _DT_OutlineLightingMix; \
    float _DT_OutlineTintMode; \
    float _DT_OutlineUV; \
    float _DT_OutlineWUV; \
    float _Cutoff;

#define DT_SHARED_TEXTURES \
    TEXTURE2D(_DT_OutlineColorMap); \
    TEXTURE2D(_DT_OutlineBaseColorMap);

// Every material texture goes through these inline samplers, so no pass gets near the 16-sampler limit.
SAMPLER(sampler_linear_repeat);
SAMPLER(sampler_linear_clamp);

struct DTLighting
{
    float3 diffuse;    // closure_eval(ClosureDiffuse) at N: every lamp (Lambert) plus the ambient
    float3 diffuseUp;  // the same for the world up direction (Blender +Z)
    float glossy;      // luminance of the sharp reflection used by the Anime Cel toon specular
    float ao;          // ambient occlusion visibility, 1 = open
    float NdotV;       // dot(N, V), signed
};

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_dasktoon_shading.glsl

float3 dt_rgb_to_hsv(float3 c)
{
    float4 K = float4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
    float4 p = lerp(float4(c.bg, K.wz), float4(c.gb, K.xy), step(c.b, c.g));
    float4 q = lerp(float4(p.xyw, c.r), float4(c.r, p.yzx), step(p.x, c.r));
    float d = q.x - min(q.w, q.y);
    float e = 1.0e-10;
    return float3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

float3 dt_hsv_to_rgb(float3 c)
{
    float4 K = float4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    float3 p = abs(frac(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * lerp(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// Rec.709 luminance, identical to Blender's default OCIO luminance coefficients.
float dt_luminance(float3 c)
{
    return dot(c, float3(0.2126, 0.7152, 0.0722));
}

float3 dt_overlay(float3 a, float3 b)
{
    return lerp(2.0 * a * b, 1.0 - 2.0 * (1.0 - a) * (1.0 - b), step(0.5, a));
}

float3 dt_light_norm(float3 light_col)
{
    float l_max = max(max(light_col.r, light_col.g), light_col.b);
    return (l_max > 0.001) ? (light_col / l_max) : float3(1.0, 1.0, 1.0);
}

float3 dt_shade_simple(float light, float3 base, float3 shadow, float thresh, float softness, out float cel)
{
    float s_soft = max(softness, 0.001);
    float s_min = clamp(thresh - s_soft * 0.5, 0.0, 1.0);
    float s_max = clamp(thresh + s_soft * 0.5, s_min + 0.0001, 1.0);
    cel = smoothstep(s_min, s_max, light);
    float3 auto_shadow = base * shadow * 1.25;
    float3 final_shadow = (length(shadow) > 0.001) ? lerp(shadow, auto_shadow, 0.75) : base * 0.5;
    return lerp(final_shadow, base, cel);
}

// The ramp texture is 256x1 with pixel i = ColorRamp.evaluate((i + 0.5) / 256). A CONSTANT ramp snaps t to a
// texel centre, which turns the bilinear clamp sampler into nearest sampling (Blender's valtorgb_nearest).
float3 dt_ramp_color(TEXTURE2D_PARAM(ramp, rampSampler), float is_constant, float t)
{
    if (is_constant > 0.5)
    {
        t = (min(floor(t * 256.0), 255.0) + 0.5) / 256.0;
    }
    return SAMPLE_TEXTURE2D_LOD(ramp, rampSampler, float2(t, 0.5), 0).rgb;
}

float3 dt_shade_ramp(float light, float3 base, float thresh, TEXTURE2D_PARAM(ramp, rampSampler), float is_constant,
                     out float cel)
{
    float t = clamp(light + 0.5 - thresh, 0.0, 1.0);
    float3 tint = dt_ramp_color(TEXTURE2D_ARGS(ramp, rampSampler), is_constant, t);
    float lum_dark = dt_luminance(dt_ramp_color(TEXTURE2D_ARGS(ramp, rampSampler), is_constant, 0.0));
    float lum_lit = dt_luminance(dt_ramp_color(TEXTURE2D_ARGS(ramp, rampSampler), is_constant, 1.0));
    cel = clamp((dt_luminance(tint) - lum_dark) / max(lum_lit - lum_dark, 0.0001), 0.0, 1.0);
    return base * tint;
}

// Ambient Mode: 0 OVERLAY, 1 HUE, 2 HUE_SAT, 3 SAT, 4 VAL, 5 MULTIPLY, 6 MIX.
float3 dt_ambient_mode(float3 a, float3 b, int mode)
{
    if (mode == 0)
    {
        return dt_overlay(a, b);
    }
    if (mode == 5)
    {
        return a * b;
    }
    if (mode < 1 || mode > 4)
    {
        return b;
    }
    float3 ha = dt_rgb_to_hsv(a);
    float3 hb = dt_rgb_to_hsv(b);
    if (mode == 1)
    {
        ha.x = hb.x;
    }
    else if (mode == 2)
    {
        ha.x = hb.x;
        ha.y = lerp(ha.y, hb.y, 0.65);
    }
    else if (mode == 3)
    {
        ha.y = hb.y;
    }
    else
    {
        ha.z = hb.z;
    }
    return dt_hsv_to_rgb(ha);
}

// Light Mode: 0 OVERLAY, 1 HUE, 2 MULTIPLY, 3 ADD, 4 PURE_CEL.
float3 dt_light_mode(float3 c, float3 light_col, float3 light_norm, float strength, int mode)
{
    float s = clamp(strength, 0.0, 2.0);
    float3 ls = lerp(float3(1.0, 1.0, 1.0), light_norm, s);
    if (mode == 0)
    {
        return dt_overlay(c, ls);
    }
    if (mode == 1)
    {
        float3 hc = dt_rgb_to_hsv(c);
        float3 hl = dt_rgb_to_hsv(light_norm);
        float3 tinted = dt_hsv_to_rgb(float3(hl.x, hc.y, hc.z));
        return lerp(c, tinted, clamp(s, 0.0, 1.0) * hl.y);
    }
    if (mode == 2)
    {
        return c * ls;
    }
    if (mode == 3)
    {
        return c + (light_col - min(min(light_col.r, light_col.g), light_col.b)) * s;
    }
    return c;
}

// value x texture when the map flag is on. Float inputs read the texture's luminance, like Blender's implicit
// colour-to-float conversion.
float4 DT_ColorInput(float4 value, TEXTURE2D_PARAM(tex, smp), float mapOn, float2 uv)
{
    UNITY_BRANCH
    if (mapOn > 0.5)
    {
        value *= SAMPLE_TEXTURE2D(tex, smp, uv);
    }
    return value;
}

float DT_FloatInput(float value, TEXTURE2D_PARAM(tex, smp), float mapOn, float2 uv)
{
    UNITY_BRANCH
    if (mapOn > 0.5)
    {
        value *= dt_luminance(SAMPLE_TEXTURE2D(tex, smp, uv).rgb);
    }
    return value;
}

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_anime_character.glsl (Anime BSDF). Modules are material keywords.

struct DTAnimeBSDFInput
{
    float3 baseColor;
    float3 shadowColor;
    float shadowThreshold;
    float shadowSoftness;
    float3 ambientColor;
    float ambientUseCustom;
    float ambientShadowOnly;
    float ambientFactor;
    int ambientMode;
    float lightTintStrength;
    float lightFactor;
    int lightMode;
    float3 aoColor;
    float aoDarkness;
    float aoFactor;
    float aoMask;
    float3 rimColor;
    float rimPower;
    float rimLift;
    float rimLightingMix;
    float rimFactor;
    float3 colorFilter;
    float3 shadowTint;
    float3 highlightTint;
    float saturation;
    float brightness;
    float contrast;
    float gradeFactor;
    float strength;
};

float3 dt_grade(float3 c, float3 filter, float3 shadow_tint, float3 highlight_tint, float saturation,
                float brightness, float contrast)
{
    float3 graded = c * filter;
    float lum = dot(graded, float3(0.299, 0.587, 0.114));
    graded = lerp(graded * shadow_tint, graded * highlight_tint, clamp(lum, 0.0, 1.0));
    if (abs(saturation - 1.0) > 0.001)
    {
        float3 hsv = dt_rgb_to_hsv(graded);
        hsv.y = clamp(hsv.y * max(saturation, 0.0), 0.0, 1.0);
        graded = dt_hsv_to_rgb(hsv);
    }
    graded += brightness;
    graded = (graded - 0.5) * (1.0 + contrast) + 0.5;
    return max(graded, float3(0.0, 0.0, 0.0));
}

float3 dt_anime_bsdf(DTAnimeBSDFInput s, DTLighting l, TEXTURE2D_PARAM(ramp, rampSampler), float rampConstant)
{
    float3 base = max(s.baseColor, 0.0);
    float3 shadow = max(s.shadowColor, 0.0);
    float3 light_col = l.diffuse;
    float light_intensity = max(max(light_col.r, light_col.g), light_col.b);

    float cel;
    float3 c;
#if defined(_DT_RAMP)
    c = dt_shade_ramp(light_intensity, base, s.shadowThreshold, TEXTURE2D_ARGS(ramp, rampSampler), rampConstant, cel);
#else
    c = dt_shade_simple(light_intensity, base, shadow, s.shadowThreshold, s.shadowSoftness, cel);
#endif

#if defined(_DT_AMBIENT)
    float amb_fac = clamp(s.ambientFactor, 0.0, 1.0);
    if (amb_fac > 0.0001)
    {
        float3 amb_color = (s.ambientUseCustom > 0.5) ? s.ambientColor : l.diffuseUp;
        float3 amb_shaded = dt_ambient_mode(c, amb_color, s.ambientMode);
        float apply_mask = (s.ambientShadowOnly > 0.5) ? (1.0 - cel) : 1.0;
        c = lerp(c, amb_shaded, amb_fac * apply_mask);
    }
#endif

#if defined(_DT_LIGHT)
    float lit_fac = clamp(s.lightFactor, 0.0, 1.0);
    if (lit_fac > 0.0001)
    {
        float3 lit_shaded = dt_light_mode(c, light_col, dt_light_norm(light_col), s.lightTintStrength, s.lightMode);
        c = lerp(c, lit_shaded, lit_fac * cel);
    }
#endif

#if defined(_DT_AO)
    float ao_f = clamp(s.aoFactor, 0.0, 1.0) * clamp(s.aoMask, 0.0, 1.0);
    if (ao_f > 0.0001)
    {
        float darkness = max(s.aoDarkness, 0.0);
        float occlusion = clamp(1.0 - l.ao, 0.0, 1.0);
        float deep_occlusion = clamp(pow(occlusion, 1.0 / max(darkness, 0.01)) * min(darkness, 3.0), 0.0, 1.0);
        float3 ao_multiplier = lerp(float3(1.0, 1.0, 1.0), s.aoColor, deep_occlusion);
        c = lerp(c, c * ao_multiplier, ao_f);
    }
#endif

#if defined(_DT_RIM)
    float rim_f = clamp(s.rimFactor, 0.0, 1.0);
    if (rim_f > 0.0001)
    {
        float fresnel = 1.0 - clamp(l.NdotV, 0.0, 1.0);
        float rim_term = clamp(pow(fresnel, max(s.rimPower, 0.5)) + s.rimLift, 0.0, 1.0);
        float3 rim_col = s.rimColor;
        float rim_l_mix = clamp(s.rimLightingMix, 0.0, 1.0);
        if (rim_l_mix > 0.001)
        {
            rim_col = lerp(rim_col, rim_col * light_col, rim_l_mix);
        }
        float light_visibility = lerp(1.0, clamp(light_intensity * 1.5, 0.0, 1.0), rim_l_mix);
        c += rim_col * (rim_term * rim_f * light_visibility);
    }
#endif

#if defined(_DT_GRADE)
    float grd_fac = clamp(s.gradeFactor, 0.0, 1.0);
    if (grd_fac > 0.0001)
    {
        float3 graded = dt_grade(c, s.colorFilter, s.shadowTint, s.highlightTint, s.saturation, s.brightness,
                                 s.contrast);
        c = lerp(c, graded, grd_fac);
    }
#endif

    return max(c * max(s.strength, 0.0), float3(0.0, 0.0, 0.0));
}

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_anime_cel.glsl (Anime Cel / Classic Cel)

struct DTAnimeCelInput
{
    float3 baseColor;
    float3 shadowColor;
    float shadowThreshold;
    float shadowSoftness;
    float4 ambientColor;
    float ambientBlend;
    float ambientShadowOnly;
    int ambientMode;
    float lightTintStrength;
    int lightMode;
    float3 specColor;
    float specSize;
    float specSoftness;
};

float3 dt_anime_cel(DTAnimeCelInput s, DTLighting l, TEXTURE2D_PARAM(ramp, rampSampler), float rampConstant)
{
    float3 base = max(s.baseColor, 0.0);
    float3 shadow = max(s.shadowColor, 0.0);
    float4 ambient = max(s.ambientColor, 0.0);
    float3 spec_color = max(s.specColor, 0.0);

    // Ambient: tints the shadow tone, and the lit tone unless "shadow only".
    float blend_fac = clamp(s.ambientBlend * ambient.a, 0.0, 1.0);
    float3 shadow_amb = lerp(shadow, dt_ambient_mode(shadow, ambient.rgb, s.ambientMode), blend_fac);
    float3 lit_col = base;
    if (s.ambientShadowOnly < 0.5)
    {
        lit_col = lerp(lit_col, lit_col * ambient.rgb, blend_fac * 0.5);
    }

    float3 light_col = l.diffuse;
    float light = max(max(light_col.r, light_col.g), light_col.b);

    float cel;
    float3 color;
#if defined(_DT_RAMP)
    color = dt_shade_ramp(light, lit_col, s.shadowThreshold, TEXTURE2D_ARGS(ramp, rampSampler), rampConstant, cel);
#else
    color = dt_shade_simple(light, lit_col, shadow_amb, s.shadowThreshold, s.shadowSoftness, cel);
#endif

    // Lamp colour on the lit side.
    color = lerp(color, dt_light_mode(color, light_col, dt_light_norm(light_col), s.lightTintStrength, s.lightMode), cel);

    // Toon specular: glossy light level cut at (1 - size).
    float spec = clamp((l.glossy - (1.0 - s.specSize)) / max(s.specSoftness, 0.0001), 0.0, 1.0);
    color += spec_color * spec;
    return color;
}

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_anime_angel_ring.glsl, and the hair pattern Mix[ADD](AnimeCel.Color, Ring.Color, Ring.Fac).

struct DTAngelRingInput
{
    float3 highlightColor;
    float bandPosition;
    float bandWidth;
    float bandSoftness;
    float strandJitter;
    float noiseScale;
    float intensity;
};

// positionB / normalB are in Blender world space (EEVEE's g_data.P and the world normal). Returns the ring Color
// output; `fac` is the Fac output.
float3 dt_angel_ring(DTAngelRingInput s, float3 positionB, float3 normalB, out float fac)
{
    float3 highlight = max(s.highlightColor, 0.0);
    float3 N = normalize(normalB);
    float jitter = sin(dot(positionB.xy, float2(s.noiseScale * 0.7, s.noiseScale * 1.3))) * s.strandJitter * 0.1;
    float ring_dist = abs(N.z + jitter - clamp(s.bandPosition, 0.0, 1.0));
    float r_fw = max(fwidth(ring_dist), 0.0005);
    float r_soft = max(s.bandSoftness, r_fw);
    float r_width = max(s.bandWidth, 0.001);
    float ring_min = max(r_width - r_soft * 0.5, 0.0);
    float ring_max = r_width + r_soft * 0.5 + 0.0001;
    float ring_fac = 1.0 - smoothstep(ring_min, ring_max, ring_dist);
    fac = ring_fac * max(s.intensity, 0.0);
    return highlight * fac;
}

// Mix node, data type Color, blend ADD: mix(A, A + B, factor) = A + factor * B.
float3 dt_hair(float3 cel, float3 ring, float ring_fac, float clamp_factor, float clamp_result)
{
    float f = (clamp_factor > 0.5) ? clamp(ring_fac, 0.0, 1.0) : ring_fac;
    float3 c = cel + f * ring;
    return (clamp_result > 0.5) ? clamp(c, 0.0, 1.0) : c;
}

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_anime_eye.glsl (unlit)

struct DTAnimeEyeInput
{
    float3 irisColor;
    float3 pupilColor;
    float3 glowColor;
    float glowPower;
    float3 topShadowTint;
    float3 sparkleColor;
};

float3 dt_anime_eye(DTAnimeEyeInput s, float2 uv)
{
    float3 iris = max(s.irisColor, 0.0);
    float3 pupil = max(s.pupilColor, 0.0);
    float3 glow = max(s.glowColor, 0.0);
    float3 top_shadow = max(s.topShadowTint, 0.0);
    float3 sparkle = max(s.sparkleColor, 0.0);

    float dist_center = length(uv - float2(0.5, 0.5));
    float pupil_fac = 1.0 - smoothstep(0.16, 0.22, dist_center);
    float3 base_iris = lerp(iris, pupil, pupil_fac);

    float bottom_curve = pow(clamp(1.0 - uv.y, 0.0, 1.0), 2.2) * max(s.glowPower, 0.0);
    float3 with_glow = base_iris + glow * bottom_curve;

    float top_shadow_fac = smoothstep(0.45, 0.85, uv.y);
    float3 with_shadow = lerp(with_glow, with_glow * top_shadow, top_shadow_fac);

    float sp1 = 1.0 - smoothstep(0.035, 0.055, length(uv - float2(0.38, 0.65)));
    float sp2 = 1.0 - smoothstep(0.018, 0.032, length(uv - float2(0.62, 0.40)));
    float sparkle_fac = clamp(sp1 + sp2, 0.0, 1.0);
    return lerp(with_shadow, sparkle, sparkle_fac);
}

// ---------------------------------------------------------------------------------------------------------------
// gpu_shader_material_dask_cel.glsl. Its in-surface outline is on when the material keyword _DT_OUTLINE is set.

struct DTDaskCelInput
{
    float3 baseColor;
    float3 shadowColor;
    float shadowThreshold;
    float shadowSoftness;
    float outlineWidth;
    float3 outlineColor;
    float outlineLightingMix;
    int outlineTintMode;
    float strength;
};

float3 dt_dask_cel(DTDaskCelInput s, DTLighting l, TEXTURE2D_PARAM(ramp, rampSampler), float rampConstant, out float cel)
{
    float3 base = max(s.baseColor, 0.0);
    float3 shadow = max(s.shadowColor, 0.0);
    float light_intensity = max(max(l.diffuse.r, l.diffuse.g), l.diffuse.b);

    float3 c;
#if defined(_DT_RAMP)
    c = dt_shade_ramp(light_intensity, base, s.shadowThreshold, TEXTURE2D_ARGS(ramp, rampSampler), rampConstant, cel);
#else
    c = dt_shade_simple(light_intensity, base, shadow, s.shadowThreshold, s.shadowSoftness, cel);
#endif

#if defined(_DT_OUTLINE)
    float edge_factor = 1.0 - abs(l.NdotV);
    float outline_thresh = 1.0 - clamp(s.outlineWidth * 50.0, 0.005, 0.99);
    if (edge_factor > outline_thresh)
    {
        float3 line_col = s.outlineColor;
        float3 base_hsv = dt_rgb_to_hsv(base);
        if (s.outlineTintMode == 1)
        {
            float o_h = frac(base_hsv.x - 0.03 + 1.0);
            float o_s = clamp(base_hsv.y * 1.40 + 0.10, 0.0, 1.0);
            float o_v = base_hsv.z * 0.35;
            line_col = dt_hsv_to_rgb(float3(o_h, o_s, o_v));
        }
        else if (s.outlineTintMode >= 2)
        {
            float3 dark_tint = dt_hsv_to_rgb(float3(base_hsv.x, clamp(base_hsv.y * 1.3, 0.0, 1.0), base_hsv.z * 0.35));
            line_col = lerp(dark_tint, dark_tint * l.diffuse * DT_PI, 0.6);
        }
        if (s.outlineLightingMix > 0.01)
        {
            line_col = lerp(line_col, line_col * l.diffuse * DT_PI, s.outlineLightingMix);
        }
        c = line_col;
    }
#endif

    return max(c * max(s.strength, 0.0), float3(0.0, 0.0, 0.0));
}

// ---------------------------------------------------------------------------------------------------------------
// Outline: gpu_shader_material_dask_outline.glsl (line colour) and the Geometry Nodes width of project 1, spec 4.3.

struct DTOutlineInput
{
    float3 baseColor;
    float3 outlineColor;
    float lightBleed;
    float tintDarkness;
    float tintSatBoost;
    float lightingMix;
    int tintMode;
};

// normalB: the hull's shading normal in Blender world space. diffuse: closure_eval(ClosureDiffuse) at that normal.
float3 dt_outline_color(DTOutlineInput s, float3 normalB, float3 diffuse)
{
    float3 base_rgb = max(s.baseColor, 0.0);
    float3 outline_rgb = max(s.outlineColor, 0.0);
    float3 N = normalize(normalB);
    float3 L = normalize(float3(0.5, 0.8, 0.6));
    float half_lambert = dot(N, L) * 0.5 + 0.5;

    float3 base_hsv = dt_rgb_to_hsv(base_rgb);
    float target_v = clamp(base_hsv.z * clamp(s.tintDarkness, 0.05, 1.0), 0.02, 0.95);
    float target_s = clamp(base_hsv.y * clamp(s.tintSatBoost, 0.5, 3.0), 0.10, 1.0);
    float3 harmonic_rgb = dt_hsv_to_rgb(float3(base_hsv.x, target_s, target_v));

    float3 line_rgb = outline_rgb;
    if (s.tintMode == 1)
    {
        line_rgb = harmonic_rgb;
        if (half_lambert > 0.7 && s.lightBleed > 0.2)
        {
            float glow_fac = (half_lambert - 0.7) * 3.33 * s.lightBleed;
            line_rgb = lerp(line_rgb, base_rgb, clamp(glow_fac, 0.0, 0.6));
        }
    }
    else if (s.tintMode >= 2)
    {
        line_rgb = lerp(harmonic_rgb, harmonic_rgb * (half_lambert * 0.8 + 0.2), 0.8);
    }

    float mix_fac = clamp(s.lightingMix, 0.0, 1.0);
    if (mix_fac > 0.001)
    {
        line_rgb = lerp(line_rgb, line_rgb * diffuse * DT_PI, mix_fac);
    }
    return line_rgb;
}

// Width of the Geometry Nodes hull (project 1, spec 4.3):
// light_thin = 1 - clamp((hl - 0.55) / 0.45) * bleed * 0.75, hl = dot(N, L) * 0.5 + 0.5,
// f(u, v) = sin(2u) cos(3v) + 0.5 sin(6.28v) with (u, v) = uv0 * 12.
float dt_outline_width(float width, float bleed, float wobble, float NdotL, float2 uv0, float mask)
{
    float hl = NdotL * 0.5 + 0.5;
    float light_thin = 1.0 - clamp((hl - 0.55) / 0.45, 0.0, 1.0) * bleed * 0.75;
    float u = uv0.x * 12.0;
    float v = uv0.y * 12.0;
    float f = sin(2.0 * u) * cos(3.0 * v) + 0.5 * sin(6.28 * v);
    return width * light_thin * (1.0 + 0.25 * wobble * f) * mask;
}

// Octahedral decode of DT_OutlineN (scripts/startup/bl_ui/dasktoon_outline_gamedata.py: oct_decode).
float3 dt_oct_decode(float2 e)
{
    float3 n = float3(e.x, e.y, 1.0 - abs(e.x) - abs(e.y));
    float t = max(-n.z, 0.0);
    n.x += (n.x >= 0.0) ? -t : t;
    n.y += (n.y >= 0.0) ? -t : t;
    return normalize(n);
}

#endif // DASKTOON_CORE_INCLUDED
```

- [ ] **Step 4: Viết lớp URP và pass outline**

File: `scripts/modules/dasktoon_export/unity_urp/DaskToonURP.hlsl`
```hlsl
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
```

File: `scripts/modules/dasktoon_export/unity_urp/DaskToonOutline.hlsl`
```hlsl
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
```

- [ ] **Step 5: Viết bốn file `.shader`**

Mọi shader có cùng năm pass; chỉ khác Properties, CBUFFER, texture, keyword và hàm fragment.

File: `scripts/modules/dasktoon_export/unity_urp/AnimeBSDF.shader`
```shaderlab
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
```

File: `scripts/modules/dasktoon_export/unity_urp/AnimeCel.shader`
```shaderlab
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
                c = dt_hair(c, ring, ring_fac, _DT_RingClampFactor, _DT_RingClampResult);
#endif
                c *= _DT_EmissionStrength;
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
```

File: `scripts/modules/dasktoon_export/unity_urp/AnimeEye.shader`
```shaderlab
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
```

File: `scripts/modules/dasktoon_export/unity_urp/DaskCel.shader`
```shaderlab
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
```

- [ ] **Step 6: Viết bộ cài shader**

File: `scripts/modules/dasktoon_export/shaders_install.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Install the DaskToon Unity shaders into an export root: fixed GUIDs, so every export points at the same shader
assets, and a version file, so a project is only rewritten by a newer DaskToon (spec 4)."""

import os

from . import assets, unity_yaml

SHADER_VERSION = 1
SHADER_DIR = "Shaders"
VERSION_FILE = "DaskToonShaders.version"
SOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unity_urp")
SHADER_NAMES = ("AnimeBSDF", "AnimeCel", "AnimeEye", "DaskCel")
SHADERS_FOLDER_GUID = "44377c95f9c3c9c9d028aff6a66c6477"
ROOT_FOLDER_GUID = "3694ef82df330a6381e838d2da364f48"  # Assets/DaskToon in PROJECT mode
VERSION_GUID = "d5a71714275166c4ace3f09ff18fa067"
FILE_GUIDS = {
    "DaskToonCore.hlsl": "712e19c1031f534b059dd5ae3c069025",
    "DaskToonURP.hlsl": "f86e64c85feac9699df227c399051118",
    "DaskToonOutline.hlsl": "76ca2d70894695203cf8567f47ecafed",
    "AnimeBSDF.shader": "651389b857c37954216341111b253e67",
    "AnimeCel.shader": "ef4936d27bf797490dd8a472a561f02e",
    "AnimeEye.shader": "970c613c54e57029168ffc98ac73c832",
    "DaskCel.shader": "050189cde98f1c513deb3503682f01a1",
}


def shader_guid(shader):
    return FILE_GUIDS[shader + ".shader"]


def installed_version(root):
    try:
        with open(os.path.join(root, SHADER_DIR, VERSION_FILE), encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def _meta_for(file_name, guid):
    if file_name.endswith(".shader"):
        return unity_yaml.shader_meta(guid)
    if file_name.endswith(".hlsl"):
        return unity_yaml.include_meta(guid)
    return unity_yaml.default_meta(guid)


def ensure_root(target):
    """The export root; in PROJECT mode also the .meta of Assets/DaskToon."""
    if target.mode == 'PROJECT':
        assets.ensure_folder(os.path.dirname(target.root), os.path.basename(target.root), ROOT_FOLDER_GUID)
    else:
        os.makedirs(target.root, exist_ok=True)


def install_shaders(target, warnings, force=False):
    """Write the shader sources with their fixed GUIDs, then the version file. PROJECT mode skips an install of
    this version or newer unless `force`. Returns True when the shaders were written."""
    if target.mode == 'PROJECT' and not force and installed_version(target.root) >= SHADER_VERSION:
        return False
    ensure_root(target)
    assets.ensure_folder(target.root, SHADER_DIR, SHADERS_FOLDER_GUID)
    for file_name, guid in sorted(FILE_GUIDS.items()):
        with open(os.path.join(SOURCE_DIR, file_name), "rb") as f:
            data = f.read()
        assets.write_asset(target.root, SHADER_DIR + "/" + file_name, guid, _meta_for(file_name, guid), warnings,
                           data=data)
    assets.write_asset(target.root, SHADER_DIR + "/" + VERSION_FILE, VERSION_GUID,
                       unity_yaml.default_meta(VERSION_GUID), warnings, data=b"%d\n" % SHADER_VERSION)
    return True
```

- [ ] **Step 7: Chạy test headless, phải PASS**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_shaders_test.py 2>&1 | tail -5`
Expected: `Ran 7 tests ... OK`.

- [ ] **Step 8: Viết test biên dịch trong Unity**

File: `tests/unity/Editor/DaskToonShaderTests.cs`
```csharp
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
```

File: `tests/python/dasktoon_unity_shaders_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Every DaskToon shader pass compiles in Unity 6000.5 / URP 17.5 (spec 8, Unity step 1)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402
from dasktoon_export import shaders_install, targets  # noqa: E402


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnityShaderTest(unittest.TestCase):
    def test_every_shader_variant_compiles(self):
        root = harness.ensure_project()
        target = targets.make_target(root, "ShaderTest")
        self.assertEqual(target.mode, 'PROJECT')
        shaders_install.install_shaders(target, [], force=True)
        result = harness.run_method("DaskToonShaderTests.CompileShaders")
        self.assertTrue(result["ok"], "\n".join(result.get("errors") or []) or result.get("error"))
        self.assertGreater(result["compiled"], 100)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 9: Chạy test Unity, sửa shader cho tới khi PASS**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_unity_shaders_test.py 2>&1 | tail -30`
Expected: `Ran 1 test ... OK`. Lỗi biên dịch được liệt kê theo `shader/pass/platform/stage [keyword]: thông điệp (file:dòng)`;
sửa trong `unity_urp/`, đồng bộ rồi chạy lại. Mỗi API URP phải sửa so với kế hoạch thì ghi một dòng `Ruling:`.

- [ ] **Step 10: Commit**

```bash
git add scripts/modules/dasktoon_export/unity_urp scripts/modules/dasktoon_export/shaders_install.py tests/unity/Editor/DaskToonShaderTests.cs tests/python/dasktoon_export_shaders_test.py tests/python/dasktoon_unity_shaders_test.py
git commit -m "feat: add the DaskToon URP 17.5 shaders and their installer for Engine Export"
```

### Task 5: Bảng map node và bộ đọc graph (`node_maps.py`, `graph.py`)

**Files:**
- Create: `scripts/modules/dasktoon_export/node_maps.py`
- Create: `scripts/modules/dasktoon_export/graph.py`
- Test: `tests/python/dasktoon_export_graph_test.py`

**Interfaces:**
- Consumes: `bl_ui.dasktoon_outline.{find_source, sync_material, outline_material_for, outline_node}` (Dự án 1),
  tên property của Task 4.
- Produces (`node_maps`): `InputMap(socket, prop, kind, map_prop="", flag_prop="")`, `NodeMap(shader, inputs, enums=(), modules=(), normal=False, ramp=False)`,
  `NODE_MAPS: {bl_idname: NodeMap}`, `ANGEL_RING_INPUTS`, `OUTLINE_INPUTS`, `SHADER_KEYWORDS: {shader: tuple}`, `KEYWORD_TOGGLES: {keyword: float property}`.
- Produces (`graph`): `TexSource(kind, color, tree_owner, node, socket, value=None, value_prop="", flag_prop="", image=None)`
  với `kind ∈ {'IMAGE', 'NORMAL', 'BAKE'}` (`value`/`value_prop`/`flag_prop` cho phép trả input về giá trị khi không ghi được texture),
  `MaterialSpec(material, shader, floats, colors, textures: {map property: TexSource}, keywords, queue, render_type, disabled_passes, ramp, outline, warnings)`,
  `follow(socket) -> NodeSocket | None`, `light_dependency(output_socket) -> str | None`,
  `analyze_material(mat, meshes) -> (MaterialSpec | None, reason: str)`, `is_outline_companion(mat) -> bool`,
  `UV_NORMAL = "DT_OutlineN"`, `UV_MASK = "DT_OutlineW"`.

Bảng property (giá trị → map → cờ). Input không có cột map thì không nhận texture trong Unity; nếu input đó có link thì ghi
cảnh báo và dùng giá trị đang đặt (`Ruling` đã chốt khi lập kế hoạch: giới hạn số texture mỗi pass để vừa 16 texture unit của
GLES/Metal đời cũ).

| Node | Input → property (★ = nhận texture) |
|---|---|
| Anime BSDF | Base Color → `_BaseColor`★(`_BaseMap`, `_DT_BaseMapOn`); Shadow Color → `_DT_ShadowColor`★; Shadow Threshold → `_DT_ShadowThreshold`★; Shadow Softness → `_DT_ShadowSoftness`; Ambient Color → `_DT_AmbientColor`★; Use Custom Color → `_DT_AmbientUseCustom`; Ambient Shadow Only → `_DT_AmbientShadowOnly`; Ambient Factor → `_DT_AmbientFactor`; Light Tint Strength → `_DT_LightTintStrength`; Light Factor → `_DT_LightFactor`; AO Color → `_DT_AOColor`★; AO Distance → `_DT_AODistance`; AO Darkness → `_DT_AODarkness`; AO Factor → `_DT_AOFactor`; AO Mask → `_DT_AOMask`★; Rim Color → `_DT_RimColor`★; Rim Fresnel Power → `_DT_RimPower`; Rim Lift → `_DT_RimLift`; Rim Lighting Mix → `_DT_RimLightingMix`; Rim Factor → `_DT_RimFactor`; Color Filter → `_DT_ColorFilter`★; Shadow Tint → `_DT_ShadowTint`★; Highlight Tint → `_DT_HighlightTint`★; Saturation, Brightness, Contrast, Grade Factor → `_DT_<tên>`; Strength → `_DT_Strength`; Alpha → `_DT_Alpha`★ |
| Anime Cel | Base Color★, Shadow Color★, Shadow Threshold★, Shadow Softness, Ambient Color★, Ambient Blend → `_DT_AmbientBlend`, Ambient Shadow Only, Light Tint Strength, Specular Color → `_DT_SpecularColor`★, Specular Size → `_DT_SpecularSize`, Specular Softness → `_DT_SpecularSoftness` |
| Angel Ring (mẫu tóc) | Highlight Color → `_DT_RingColor`, Band Position → `_DT_RingPosition`, Band Width → `_DT_RingWidth`, Band Softness → `_DT_RingSoftness`, Strand Jitter → `_DT_RingJitter`, Noise Scale → `_DT_RingNoiseScale`, Intensity → `_DT_RingIntensity` |
| Anime Eye | Iris Color → `_BaseColor`★, Pupil Color → `_DT_PupilColor`★, Bottom Glow Color → `_DT_GlowColor`★, Bottom Glow Power → `_DT_GlowPower`, Top Shadow Tint → `_DT_TopShadowTint`★, Sparkle Color → `_DT_SparkleColor`★; UV Vector → `_DT_EyeUseUV` |
| Dask Cel | Base Color★, Shadow Color★, Shadow Threshold★, Shadow Softness, Strength |
| Dask Outline (material `.Outline`) | Base Color → `_DT_OutlineBaseColor`★, Outline Color → `_DT_OutlineColor`★, Outline Width → `_DT_OutlineWidth`, Light Bleed → `_DT_OutlineLightBleed`, Hand Wobble → `_DT_OutlineWobble`, Tint Darkness → `_DT_OutlineTintDarkness`, Tint Saturation Boost → `_DT_OutlineTintSatBoost`, Outline Lighting Mix → `_DT_OutlineLightingMix` |

Enum: `ambient_mode` → `_DT_AmbientMode`, `light_blend_mode` → `_DT_LightMode`, `outline_tint_mode`/`tint_mode` → `_DT_OutlineTintMode`
(giá trị số của enum). Module của Anime BSDF: `use_ambient/use_light/use_ao/use_rim/use_grade` → `_DT_AMBIENT/_DT_LIGHT/_DT_AO/_DT_RIM/_DT_GRADE`.
`shading_mode == 'RAMP'` → `_DT_RAMP`, `_DT_RampConstant`. Các input Outline của Anime BSDF và Dask Cel không nằm trong bảng
node: chúng đi qua material `.Outline` (đã được `sync_material` đồng bộ), riêng Width lấy từ node chính.

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_export_graph_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Reading DaskToon materials into MaterialSpec (spec 5): nodes, hair pattern, Reroute, texture sources, render
state, outline and its UV channels."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from bl_ui import dasktoon_outline_gamedata as gamedata  # noqa: E402
from dasktoon_export import graph  # noqa: E402

TMP = tempfile.mkdtemp(prefix="dt_graph_")


def png_image(name, rgba=(0.5, 0.25, 0.75, 1.0), non_color=False):
    img = bpy.data.images.new(name, 4, 4)
    img.pixels = list(rgba) * 16
    path = os.path.join(TMP, name + ".png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    loaded = bpy.data.images.load(path)
    if non_color:
        loaded.colorspace_settings.name = 'Non-Color'
    return loaded


def sphere_with(mat):
    obj = tu.add_sphere(segments=12, rings=6)
    tu.assign(obj, mat)
    return obj


def analyze(mat, obj):
    return graph.analyze_material(mat, [obj.data])


class NodeTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()

    def test_anime_bsdf_values_enums_and_modules(self):
        mat, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        node.use_ambient = True
        node.use_rim = True
        node.ambient_mode = 'HUE'
        node.light_blend_mode = 'MULTIPLY'
        node.inputs["Base Color"].default_value = (0.5, 0.2, 0.1, 1.0)
        node.inputs["Shadow Threshold"].default_value = 0.3
        spec, reason = analyze(mat, sphere_with(mat))
        self.assertEqual(reason, "")
        self.assertEqual(spec.shader, "AnimeBSDF")
        for got, want in zip(spec.colors["_BaseColor"], (0.5, 0.2, 0.1, 1.0)):
            self.assertAlmostEqual(got, want, places=5)
        self.assertAlmostEqual(spec.floats["_DT_ShadowThreshold"], 0.3, places=5)
        self.assertEqual(spec.floats["_DT_AmbientMode"], 1.0)
        self.assertEqual(spec.floats["_DT_LightMode"], 2.0)
        self.assertTrue({"_DT_AMBIENT", "_DT_RIM"} <= spec.keywords)
        self.assertNotIn("_DT_LIGHT", spec.keywords)
        self.assertEqual(spec.floats["_DT_UseAmbient"], 1.0)
        self.assertEqual(spec.floats["_DT_UseLight"], 0.0)
        self.assertNotIn("_DT_UseAngelRing", spec.floats)

    def test_ramp_mode(self):
        mat, node = tu.node_material("Ramp", 'ShaderNodeDaskCel')
        node.shading_mode = 'RAMP'
        node.shading_ramp.interpolation = 'CONSTANT'
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertIn("_DT_RAMP", spec.keywords)
        self.assertEqual(spec.ramp, node.shading_ramp)
        self.assertEqual(spec.floats["_DT_RampConstant"], 1.0)
        self.assertEqual(spec.floats["_DT_UseRamp"], 1.0)

    def test_each_node_has_its_shader(self):
        for idname, shader in (('ShaderNodeAnimeCel', "AnimeCel"), ('ShaderNodeAnimeEye', "AnimeEye"),
                               ('ShaderNodeDaskCel', "DaskCel")):
            mat, _node = tu.node_material(idname, idname)
            spec, _ = analyze(mat, sphere_with(mat))
            self.assertEqual(spec.shader, shader)
        cel_mat, _ = tu.node_material("Cel", 'ShaderNodeAnimeCel')
        spec, _ = analyze(cel_mat, sphere_with(cel_mat))
        self.assertEqual(spec.floats["_DT_EmissionStrength"], 1.0)

    def test_eye_uv_input(self):
        mat, node = tu.node_material("Eye", 'ShaderNodeAnimeEye')
        obj = sphere_with(mat)
        spec, _ = analyze(mat, obj)
        self.assertEqual(spec.floats["_DT_EyeUseUV"], 0.0)
        coords = mat.node_tree.nodes.new('ShaderNodeTexCoord')
        mat.node_tree.links.new(coords.outputs["UV"], node.inputs["UV Vector"])
        spec, _ = analyze(mat, obj)
        self.assertEqual(spec.floats["_DT_EyeUseUV"], 1.0)
        self.assertEqual(spec.warnings, [])

    def test_hair_pattern(self):
        mat = tu.new_material("Hair")
        nt = mat.node_tree
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        emission = nt.nodes.new('ShaderNodeEmission')
        emission.inputs["Strength"].default_value = 2.0
        cel = nt.nodes.new('ShaderNodeAnimeCel')
        ring = nt.nodes.new('ShaderNodeAnimeAngelRing')
        ring.inputs["Intensity"].default_value = 0.8
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'ADD'
        sockets = {s.identifier: s for s in mix.inputs}
        nt.links.new(cel.outputs["Color"], sockets["A_Color"])
        nt.links.new(ring.outputs["Color"], sockets["B_Color"])
        nt.links.new(ring.outputs["Fac"], sockets["Factor_Float"])
        nt.links.new(next(s for s in mix.outputs if s.identifier == "Result_Color"), emission.inputs["Color"])
        nt.links.new(emission.outputs["Emission"], out.inputs["Surface"])
        spec, reason = analyze(mat, sphere_with(mat))
        self.assertEqual(reason, "")
        self.assertEqual(spec.shader, "AnimeCel")
        self.assertIn("_DT_ANGEL_RING", spec.keywords)
        self.assertEqual(spec.floats["_DT_EmissionStrength"], 2.0)
        self.assertAlmostEqual(spec.floats["_DT_RingIntensity"], 0.8, places=5)
        self.assertEqual(spec.floats["_DT_RingClampFactor"], 1.0)
        self.assertEqual(spec.floats["_DT_UseAngelRing"], 1.0)

    def test_reroutes_are_followed(self):
        mat, node = tu.node_material("Rerouted", 'ShaderNodeAnimeCharacter')
        nt = mat.node_tree
        out = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
        r1, r2 = nt.nodes.new('NodeReroute'), nt.nodes.new('NodeReroute')
        nt.links.new(node.outputs["BSDF"], r1.inputs[0])
        nt.links.new(r1.outputs[0], r2.inputs[0])
        nt.links.new(r2.outputs[0], out.inputs["Surface"])
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = png_image("reroute_tex")
        r3 = nt.nodes.new('NodeReroute')
        nt.links.new(tex.outputs["Color"], r3.inputs[0])
        nt.links.new(r3.outputs[0], node.inputs["Base Color"])
        spec, reason = analyze(mat, sphere_with(mat))
        self.assertEqual(reason, "")
        self.assertEqual(spec.textures["_BaseMap"].kind, 'IMAGE')

    def test_unsupported_material(self):
        mat = bpy.data.materials.new("Principled")
        spec, reason = analyze(mat, sphere_with(mat))
        self.assertIsNone(spec)
        self.assertIn("ShaderNodeBsdfPrincipled", reason)
        self.assertEqual(graph.analyze_material(None, []), (None, "slot trống"))


class SourceTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()
        self.mat, self.node = tu.node_material("Src", 'ShaderNodeAnimeCharacter')
        self.nt = self.mat.node_tree
        self.obj = sphere_with(self.mat)

    def test_direct_image_is_copied(self):
        tex = self.nt.nodes.new('ShaderNodeTexImage')
        tex.image = png_image("direct")
        self.nt.links.new(tex.outputs["Color"], self.node.inputs["Base Color"])
        spec, _ = analyze(self.mat, self.obj)
        src = spec.textures["_BaseMap"]
        self.assertEqual(src.kind, 'IMAGE')
        self.assertTrue(src.color)
        self.assertEqual(src.image, tex.image)
        self.assertEqual(spec.floats["_DT_BaseMapOn"], 1.0)
        self.assertEqual(spec.colors["_BaseColor"], (1.0, 1.0, 1.0, 1.0))

    def test_non_color_image_is_data(self):
        tex = self.nt.nodes.new('ShaderNodeTexImage')
        tex.image = png_image("mask", non_color=True)
        self.nt.links.new(tex.outputs["Color"], self.node.inputs["Shadow Threshold"])
        spec, _ = analyze(self.mat, self.obj)
        self.assertFalse(spec.textures["_DT_ShadowThresholdMap"].color)
        self.assertEqual(spec.floats["_DT_ShadowThreshold"], 1.0)

    def test_mapping_branch_is_baked(self):
        tex = self.nt.nodes.new('ShaderNodeTexImage')
        tex.image = png_image("mapped")
        mapping = self.nt.nodes.new('ShaderNodeMapping')
        coords = self.nt.nodes.new('ShaderNodeTexCoord')
        self.nt.links.new(coords.outputs["UV"], mapping.inputs["Vector"])
        self.nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        self.nt.links.new(tex.outputs["Color"], self.node.inputs["Base Color"])
        spec, _ = analyze(self.mat, self.obj)
        src = spec.textures["_BaseMap"]
        self.assertEqual(src.kind, 'BAKE')
        self.assertEqual((src.node, src.socket, src.tree_owner), (self.node.name, "Base Color", self.mat))

    def test_light_dependent_branch_warns_and_keeps_value(self):
        self.node.inputs["Shadow Color"].default_value = (0.3, 0.2, 0.1, 1.0)
        mix = self.nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        fresnel = self.nt.nodes.new('ShaderNodeFresnel')
        self.nt.links.new(fresnel.outputs["Fac"], next(s for s in mix.inputs if s.identifier == "Factor_Float"))
        self.nt.links.new(next(s for s in mix.outputs if s.identifier == "Result_Color"), self.node.inputs["Shadow Color"])
        spec, _ = analyze(self.mat, self.obj)
        self.assertNotIn("_DT_ShadowColorMap", spec.textures)
        self.assertAlmostEqual(spec.colors["_DT_ShadowColor"][0], 0.3, places=5)
        self.assertTrue(any("Shadow Color" in w and "Fresnel" in w for w in spec.warnings), spec.warnings)

    def test_linked_input_without_texture_slot_warns(self):
        self.node.use_rim = True
        self.node.inputs["Rim Fresnel Power"].default_value = 3.0
        value = self.nt.nodes.new('ShaderNodeValue')
        self.nt.links.new(value.outputs[0], self.node.inputs["Rim Fresnel Power"])
        spec, _ = analyze(self.mat, self.obj)
        self.assertEqual(spec.floats["_DT_RimPower"], 3.0)
        self.assertTrue(any("Rim Fresnel Power" in w for w in spec.warnings))

    def test_hidden_module_inputs_are_not_read_for_links(self):
        value = self.nt.nodes.new('ShaderNodeValue')
        self.nt.links.new(value.outputs[0], self.node.inputs["Rim Fresnel Power"])
        spec, _ = analyze(self.mat, self.obj)
        self.assertFalse(any("Rim Fresnel Power" in w for w in spec.warnings))

    def test_normal_map(self):
        tex = self.nt.nodes.new('ShaderNodeTexImage')
        tex.image = png_image("normal", (0.5, 0.5, 1.0, 1.0), non_color=True)
        normal_map = self.nt.nodes.new('ShaderNodeNormalMap')
        normal_map.inputs["Strength"].default_value = 0.6
        self.nt.links.new(tex.outputs["Color"], normal_map.inputs["Color"])
        self.nt.links.new(normal_map.outputs["Normal"], self.node.inputs["Normal"])
        spec, _ = analyze(self.mat, self.obj)
        self.assertEqual(spec.textures["_DT_NormalMap"].kind, 'NORMAL')
        self.assertIn("_DT_NORMALMAP", spec.keywords)
        self.assertAlmostEqual(spec.floats["_DT_NormalStrength"], 0.6, places=5)
        self.assertEqual(spec.floats["_DT_UseNormalMap"], 1.0)


class RenderStateTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()

    def test_blended_is_transparent(self):
        mat, _node = tu.node_material("Glass", 'ShaderNodeAnimeCharacter')
        mat.surface_render_method = 'BLENDED'
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertEqual((spec.queue, spec.render_type), (3000, "Transparent"))
        self.assertEqual((spec.floats["_SrcBlend"], spec.floats["_DstBlend"], spec.floats["_ZWrite"]), (5.0, 10.0, 0.0))

    def test_dithered_alpha_below_one_clips(self):
        mat, node = tu.node_material("Lash", 'ShaderNodeAnimeCharacter')
        mat.surface_render_method = 'DITHERED'
        node.inputs["Alpha"].default_value = 0.5
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertIn("_DT_ALPHATEST_ON", spec.keywords)
        self.assertEqual(spec.floats["_AlphaClip"], 1.0)
        self.assertEqual(spec.queue, -1)
        opaque, _ = analyze(*(lambda m: (m, sphere_with(m)))(tu.node_material("Opaque", 'ShaderNodeAnimeCharacter')[0]))
        self.assertNotIn("_DT_ALPHATEST_ON", opaque.keywords)
        self.assertEqual(opaque.floats["_SrcBlend"], 1.0)

    def test_backface_culling_sets_cull(self):
        mat, _node = tu.node_material("Cull", 'ShaderNodeDaskCel')
        mat.use_backface_culling = True
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertEqual(spec.floats["_Cull"], 2.0)
        mat.use_backface_culling = False
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertEqual(spec.floats["_Cull"], 0.0)


class OutlineTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        outline.reset_cache()

    def test_no_outline_disables_the_pass(self):
        mat, _node = tu.node_material("Plain", 'ShaderNodeAnimeCharacter')
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertEqual(spec.disabled_passes, ["SRPDefaultUnlit"])
        self.assertEqual(spec.floats["_DT_UseOutline"], 0.0)
        self.assertFalse(spec.outline)

    def test_outline_parameters_and_uv_channels(self):
        mat, node = tu.node_material("Lined", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        node.inputs["Outline Width"].default_value = 0.004
        node.outline_tint_mode = 'HARMONIC_KYOTO'
        obj = sphere_with(mat)
        outline.sync_material(mat)
        companion = outline.outline_material_for(mat)
        outline.outline_node(companion).inputs["Light Bleed"].default_value = 0.3
        ok, _msg = gamedata.write_outline_uvs(obj)
        self.assertTrue(ok)
        spec, _ = analyze(mat, obj)
        self.assertIn("_DT_OUTLINE", spec.keywords)
        self.assertEqual(spec.disabled_passes, [])
        self.assertAlmostEqual(spec.floats["_DT_OutlineWidth"], 0.004, places=6)
        self.assertAlmostEqual(spec.floats["_DT_OutlineLightBleed"], 0.3, places=5)
        self.assertEqual(spec.floats["_DT_OutlineTintMode"], 1.0)
        self.assertEqual(spec.floats["_DT_OutlineUV"], float(obj.data.uv_layers.find("DT_OutlineN")))
        self.assertEqual(spec.floats["_DT_OutlineWUV"], float(obj.data.uv_layers.find("DT_OutlineW")))
        self.assertEqual(spec.floats["_DT_OutlineUV"], 1.0)

    def test_missing_outline_data_falls_back_to_mesh_normal(self):
        mat, node = tu.node_material("NoData", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        spec, _ = analyze(mat, sphere_with(mat))
        self.assertEqual(spec.floats["_DT_OutlineUV"], -1.0)
        self.assertTrue(any("DT_OutlineN" in w for w in spec.warnings))

    def test_meshes_with_different_uv_order_warn(self):
        mat, node = tu.node_material("Shared", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        a = sphere_with(mat)
        b = sphere_with(mat)
        b.data.uv_layers.new(name="Extra")
        for obj in (a, b):
            gamedata.write_outline_uvs(obj)
        spec, _ = graph.analyze_material(mat, [a.data, b.data])
        self.assertTrue(any("thứ tự UV" in w for w in spec.warnings), spec.warnings)

    def test_companion_is_recognised(self):
        mat, node = tu.node_material("Owner", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        outline.sync_material(mat)
        self.assertTrue(graph.is_outline_companion(outline.outline_material_for(mat)))
        self.assertFalse(graph.is_outline_companion(mat))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, phải FAIL**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_graph_test.py 2>&1 | tail -5`
Expected: `ImportError: cannot import name 'graph'`.

- [ ] **Step 3: Viết `node_maps.py`**

File: `scripts/modules/dasktoon_export/node_maps.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon node inputs -> Unity material properties, enums -> floats, module flags -> keywords (spec 5, 6)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InputMap:
    socket: str          # input name on the DaskToon node
    prop: str            # Unity property holding the value
    kind: str            # 'COLOR', 'FLOAT' or 'BOOL'
    map_prop: str = ""   # texture property; "" when Unity takes no texture for this input
    flag_prop: str = ""  # float that switches the texture on


@dataclass(frozen=True)
class NodeMap:
    shader: str
    inputs: tuple
    enums: tuple = ()     # (node property, Unity float)
    modules: tuple = ()   # (node property, keyword)
    normal: bool = False  # has a Normal input (tangent-space normal map)
    ramp: bool = False    # has the Simple / Ramp shading switch


def _in(socket, prop, kind, mapped=False):
    if not mapped:
        return InputMap(socket, prop, kind)
    if prop == "_BaseColor":
        return InputMap(socket, prop, kind, "_BaseMap", "_DT_BaseMapOn")
    return InputMap(socket, prop, kind, prop + "Map", prop + "MapOn")


ANIME_BSDF = NodeMap("AnimeBSDF", (
    _in("Base Color", "_BaseColor", 'COLOR', True),
    _in("Shadow Color", "_DT_ShadowColor", 'COLOR', True),
    _in("Shadow Threshold", "_DT_ShadowThreshold", 'FLOAT', True),
    _in("Shadow Softness", "_DT_ShadowSoftness", 'FLOAT'),
    _in("Ambient Color", "_DT_AmbientColor", 'COLOR', True),
    _in("Use Custom Color", "_DT_AmbientUseCustom", 'BOOL'),
    _in("Ambient Shadow Only", "_DT_AmbientShadowOnly", 'BOOL'),
    _in("Ambient Factor", "_DT_AmbientFactor", 'FLOAT'),
    _in("Light Tint Strength", "_DT_LightTintStrength", 'FLOAT'),
    _in("Light Factor", "_DT_LightFactor", 'FLOAT'),
    _in("AO Color", "_DT_AOColor", 'COLOR', True),
    _in("AO Distance", "_DT_AODistance", 'FLOAT'),
    _in("AO Darkness", "_DT_AODarkness", 'FLOAT'),
    _in("AO Factor", "_DT_AOFactor", 'FLOAT'),
    _in("AO Mask", "_DT_AOMask", 'FLOAT', True),
    _in("Rim Color", "_DT_RimColor", 'COLOR', True),
    _in("Rim Fresnel Power", "_DT_RimPower", 'FLOAT'),
    _in("Rim Lift", "_DT_RimLift", 'FLOAT'),
    _in("Rim Lighting Mix", "_DT_RimLightingMix", 'FLOAT'),
    _in("Rim Factor", "_DT_RimFactor", 'FLOAT'),
    _in("Color Filter", "_DT_ColorFilter", 'COLOR', True),
    _in("Shadow Tint", "_DT_ShadowTint", 'COLOR', True),
    _in("Highlight Tint", "_DT_HighlightTint", 'COLOR', True),
    _in("Saturation", "_DT_Saturation", 'FLOAT'),
    _in("Brightness", "_DT_Brightness", 'FLOAT'),
    _in("Contrast", "_DT_Contrast", 'FLOAT'),
    _in("Grade Factor", "_DT_GradeFactor", 'FLOAT'),
    _in("Strength", "_DT_Strength", 'FLOAT'),
    _in("Alpha", "_DT_Alpha", 'FLOAT', True),
), enums=(("ambient_mode", "_DT_AmbientMode"), ("light_blend_mode", "_DT_LightMode"),
          ("outline_tint_mode", "_DT_OutlineTintMode")),
   modules=(("use_ambient", "_DT_AMBIENT"), ("use_light", "_DT_LIGHT"), ("use_ao", "_DT_AO"),
            ("use_rim", "_DT_RIM"), ("use_grade", "_DT_GRADE")),
   normal=True, ramp=True)

ANIME_CEL = NodeMap("AnimeCel", (
    _in("Base Color", "_BaseColor", 'COLOR', True),
    _in("Shadow Color", "_DT_ShadowColor", 'COLOR', True),
    _in("Shadow Threshold", "_DT_ShadowThreshold", 'FLOAT', True),
    _in("Shadow Softness", "_DT_ShadowSoftness", 'FLOAT'),
    _in("Ambient Color", "_DT_AmbientColor", 'COLOR', True),
    _in("Ambient Blend", "_DT_AmbientBlend", 'FLOAT'),
    _in("Ambient Shadow Only", "_DT_AmbientShadowOnly", 'BOOL'),
    _in("Light Tint Strength", "_DT_LightTintStrength", 'FLOAT'),
    _in("Specular Color", "_DT_SpecularColor", 'COLOR', True),
    _in("Specular Size", "_DT_SpecularSize", 'FLOAT'),
    _in("Specular Softness", "_DT_SpecularSoftness", 'FLOAT'),
), enums=(("ambient_mode", "_DT_AmbientMode"), ("light_blend_mode", "_DT_LightMode")), normal=True, ramp=True)

ANIME_EYE = NodeMap("AnimeEye", (
    _in("Iris Color", "_BaseColor", 'COLOR', True),
    _in("Pupil Color", "_DT_PupilColor", 'COLOR', True),
    _in("Bottom Glow Color", "_DT_GlowColor", 'COLOR', True),
    _in("Bottom Glow Power", "_DT_GlowPower", 'FLOAT'),
    _in("Top Shadow Tint", "_DT_TopShadowTint", 'COLOR', True),
    _in("Sparkle Color", "_DT_SparkleColor", 'COLOR', True),
))

DASK_CEL = NodeMap("DaskCel", (
    _in("Base Color", "_BaseColor", 'COLOR', True),
    _in("Shadow Color", "_DT_ShadowColor", 'COLOR', True),
    _in("Shadow Threshold", "_DT_ShadowThreshold", 'FLOAT', True),
    _in("Shadow Softness", "_DT_ShadowSoftness", 'FLOAT'),
    _in("Strength", "_DT_Strength", 'FLOAT'),
), enums=(("outline_tint_mode", "_DT_OutlineTintMode"),), normal=True, ramp=True)

NODE_MAPS = {
    'ShaderNodeAnimeCharacter': ANIME_BSDF,
    'ShaderNodeAnimeCel': ANIME_CEL,
    'ShaderNodeAnimeEye': ANIME_EYE,
    'ShaderNodeDaskCel': DASK_CEL,
}

ANGEL_RING_INPUTS = (
    _in("Highlight Color", "_DT_RingColor", 'COLOR'),
    _in("Band Position", "_DT_RingPosition", 'FLOAT'),
    _in("Band Width", "_DT_RingWidth", 'FLOAT'),
    _in("Band Softness", "_DT_RingSoftness", 'FLOAT'),
    _in("Strand Jitter", "_DT_RingJitter", 'FLOAT'),
    _in("Noise Scale", "_DT_RingNoiseScale", 'FLOAT'),
    _in("Intensity", "_DT_RingIntensity", 'FLOAT'),
)

# Dask Outline node of the <material>.Outline companion (project 1, spec 4.2).
OUTLINE_INPUTS = (
    _in("Base Color", "_DT_OutlineBaseColor", 'COLOR', True),
    _in("Outline Color", "_DT_OutlineColor", 'COLOR', True),
    _in("Outline Width", "_DT_OutlineWidth", 'FLOAT'),
    _in("Light Bleed", "_DT_OutlineLightBleed", 'FLOAT'),
    _in("Hand Wobble", "_DT_OutlineWobble", 'FLOAT'),
    _in("Tint Darkness", "_DT_OutlineTintDarkness", 'FLOAT'),
    _in("Tint Saturation Boost", "_DT_OutlineTintSatBoost", 'FLOAT'),
    _in("Outline Lighting Mix", "_DT_OutlineLightingMix", 'FLOAT'),
)

# Keywords each shader declares, and the inspector toggle that mirrors each keyword.
SHADER_KEYWORDS = {
    "AnimeBSDF": ("_DT_RAMP", "_DT_AMBIENT", "_DT_LIGHT", "_DT_AO", "_DT_RIM", "_DT_GRADE", "_DT_OUTLINE",
                  "_DT_ALPHATEST_ON", "_DT_NORMALMAP"),
    "AnimeCel": ("_DT_RAMP", "_DT_ANGEL_RING", "_DT_OUTLINE", "_DT_NORMALMAP"),
    "AnimeEye": ("_DT_OUTLINE",),
    "DaskCel": ("_DT_RAMP", "_DT_OUTLINE", "_DT_NORMALMAP"),
}
KEYWORD_TOGGLES = {
    "_DT_RAMP": "_DT_UseRamp",
    "_DT_AMBIENT": "_DT_UseAmbient",
    "_DT_LIGHT": "_DT_UseLight",
    "_DT_AO": "_DT_UseAO",
    "_DT_RIM": "_DT_UseRim",
    "_DT_GRADE": "_DT_UseGrade",
    "_DT_OUTLINE": "_DT_UseOutline",
    "_DT_ANGEL_RING": "_DT_UseAngelRing",
    "_DT_ALPHATEST_ON": "_AlphaClip",
    "_DT_NORMALMAP": "_DT_UseNormalMap",
}
```

- [ ] **Step 4: Viết `graph.py`**

File: `scripts/modules/dasktoon_export/graph.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Reads a DaskToon material into a MaterialSpec: shader, values, texture sources, keywords, render state and
outline (spec 5). Nothing here writes files; the only data it may create is the <material>.Outline companion,
through project 1's sync_material."""

from dataclasses import dataclass, field

from . import node_maps

LIGHT_NODES = {
    'ShaderNodeShaderToRGB', 'ShaderNodeLayerWeight', 'ShaderNodeFresnel', 'ShaderNodeLightPath',
    'ShaderNodeAmbientOcclusion', 'ShaderNodeCameraData',
}
LIGHT_OUTPUTS = {
    'ShaderNodeNewGeometry': {"Incoming", "Backfacing"},
    'ShaderNodeTexCoord': {"Window", "Camera", "Reflection"},
}
DASKTOON_PREFIXES = ("ShaderNodeAnime", "ShaderNodeDask", "ShaderNodeManga", "ShaderNodeArtist")
UV_NORMAL = "DT_OutlineN"
UV_MASK = "DT_OutlineW"
OUTLINE_PASS = "SRPDefaultUnlit"
MAX_UNITY_UV = 8


@dataclass
class TexSource:
    kind: str             # 'IMAGE' (copy the file), 'NORMAL' (copy as a normal map) or 'BAKE'
    color: bool           # colour data (sRGB) or numbers
    tree_owner: object    # material whose node tree holds the branch
    node: str             # node whose input is exported
    socket: str           # identifier of that input
    value: object = None  # the input's own value, restored when no texture can be written
    value_prop: str = ""  # Unity property of that value
    flag_prop: str = ""   # Unity float that switches the texture on
    image: object = None


@dataclass
class MaterialSpec:
    material: object
    shader: str
    floats: dict = field(default_factory=dict)
    colors: dict = field(default_factory=dict)
    textures: dict = field(default_factory=dict)
    keywords: set = field(default_factory=set)
    queue: int = -1
    render_type: str = "Opaque"
    disabled_passes: list = field(default_factory=list)
    ramp: object = None
    outline: bool = False
    warnings: list = field(default_factory=list)


def _socket(collection, identifier):
    return next((s for s in collection if s.identifier == identifier), None)


def follow(socket):
    """The output socket feeding `socket`, walking through Reroutes; None when unlinked or muted."""
    for _ in range(64):
        if socket is None or not socket.is_linked:
            return None
        link = socket.links[0]
        if link.is_muted or not link.is_valid:
            return None
        if link.from_node.bl_idname != 'NodeReroute':
            return link.from_socket
        socket = link.from_node.inputs[0]
    return None


def is_outline_companion(mat):
    """True for the <material>.Outline companions of project 1: a parameter source, never exported."""
    from bl_ui import dasktoon_outline as outline
    import bpy
    return any(m.get(outline.OUTLINE_MAT_PROP) == mat for m in bpy.data.materials if m != mat)


def _is_dasktoon(idname):
    return idname.startswith(DASKTOON_PREFIXES)


def _node_reason(node, out):
    if out.type == 'SHADER':
        return "nhánh chứa shader (%s)" % node.name
    if node.bl_idname in LIGHT_NODES or _is_dasktoon(node.bl_idname):
        return "nhánh phụ thuộc ánh sáng hoặc góc nhìn (%s)" % node.name
    if out.name in LIGHT_OUTPUTS.get(node.bl_idname, ()):
        return "nhánh phụ thuộc góc nhìn (%s › %s)" % (node.name, out.name)
    if node.bl_idname == 'ShaderNodeGroup' and node.node_tree is not None:
        return _group_reason(node.node_tree, set())
    return None


def _group_reason(tree, seen):
    if tree.as_pointer() in seen:
        return None
    seen.add(tree.as_pointer())
    for node in tree.nodes:
        linked = [o for o in node.outputs if o.is_linked]
        if (node.bl_idname in LIGHT_NODES or _is_dasktoon(node.bl_idname) or any(o.type == 'SHADER' for o in linked)
                or any(o.name in LIGHT_OUTPUTS.get(node.bl_idname, ()) for o in linked)):
            return "node group %s phụ thuộc ánh sáng hoặc góc nhìn" % tree.name
        if node.bl_idname == 'ShaderNodeGroup' and node.node_tree is not None:
            reason = _group_reason(node.node_tree, seen)
            if reason:
                return reason
    return None


def light_dependency(src):
    """Why the branch ending at output socket `src` cannot be baked, or None (spec 5, input sources)."""
    seen = set()
    stack = [src]
    while stack:
        out = stack.pop()
        reason = _node_reason(out.node, out)
        if reason:
            return reason
        if out.node.as_pointer() in seen:
            continue
        seen.add(out.node.as_pointer())
        for inp in out.node.inputs:
            if inp.enabled:
                upstream = follow(inp)
                if upstream is not None:
                    stack.append(upstream)
    return None


def _first_uv_ok(meshes, uv_name=None):
    """Unity samples uv0 = the first UV map. A node with no UV name uses the render-active map."""
    for mesh in meshes:
        if not mesh.uv_layers:
            return False
        first = mesh.uv_layers[0]
        if (uv_name is None and not first.active_render) or (uv_name is not None and uv_name != first.name):
            return False
    return True


def _direct_image(tex_node, meshes):
    image = tex_node.image
    if image is None or image.source != 'FILE' or tex_node.projection != 'FLAT':
        return False
    vector = follow(tex_node.inputs["Vector"])
    if vector is None:
        return _first_uv_ok(meshes)
    if vector.node.bl_idname == 'ShaderNodeUVMap':
        return _first_uv_ok(meshes, vector.node.uv_map or None)
    if vector.node.bl_idname == 'ShaderNodeTexCoord' and vector.identifier == "UV":
        return _first_uv_ok(meshes)
    return False


def _is_srgb(image):
    return image.colorspace_settings.name == 'sRGB'


def _texture_source(owner, node, sock, src, im, meshes):
    """A TexSource for an input's link, or the reason the link cannot reach Unity."""
    reason = light_dependency(src)
    if reason:
        return reason
    is_color = im.kind == 'COLOR'
    value = tuple(sock.default_value) if is_color else float(sock.default_value)
    tex_node = src.node
    if tex_node.bl_idname == 'ShaderNodeTexImage' and src.identifier == "Color" and _direct_image(tex_node, meshes):
        return TexSource('IMAGE', _is_srgb(tex_node.image), owner, node.name, sock.identifier, value, im.prop,
                         im.flag_prop, tex_node.image)
    return TexSource('BAKE', is_color, owner, node.name, sock.identifier, value, im.prop, im.flag_prop)


def _set_value(spec, im, value):
    if im.kind == 'COLOR':
        spec.colors[im.prop] = tuple(float(v) for v in value)
    else:
        spec.floats[im.prop] = float(value)


def _read_input(owner, node, im, spec, meshes):
    sock = node.inputs.get(im.socket)
    if sock is None:
        return
    _set_value(spec, im, sock.default_value)
    if not sock.enabled:
        return
    src = follow(sock)
    if src is None:
        return
    label = "%s › %s" % (owner.name, im.socket)
    if not im.map_prop:
        spec.warnings.append("%s: input này không nhận texture trong Unity; dùng giá trị đang đặt" % label)
        return
    tex = _texture_source(owner, node, sock, src, im, meshes)
    if isinstance(tex, str):
        spec.warnings.append("%s: %s; dùng giá trị đang đặt" % (label, tex))
        return
    spec.textures[im.map_prop] = tex
    spec.floats[im.flag_prop] = 1.0
    _set_value(spec, im, (1.0, 1.0, 1.0, 1.0) if im.kind == 'COLOR' else 1.0)


def _normal_map(owner, node, spec, meshes):
    sock = node.inputs.get("Normal")
    src = follow(sock) if sock is not None and sock.enabled else None
    if src is None:
        return
    normal_map = src.node
    if (normal_map.bl_idname == 'ShaderNodeNormalMap' and normal_map.space == 'TANGENT'
            and _first_uv_ok(meshes, normal_map.uv_map or None)):
        color = follow(normal_map.inputs["Color"])
        if (color is not None and color.node.bl_idname == 'ShaderNodeTexImage' and color.identifier == "Color"
                and _direct_image(color.node, meshes)):
            strength = normal_map.inputs["Strength"]
            spec.textures["_DT_NormalMap"] = TexSource('NORMAL', False, owner, normal_map.name, "Color",
                                                       image=color.node.image)
            spec.floats["_DT_NormalStrength"] = float(strength.default_value)
            spec.keywords.add("_DT_NORMALMAP")
            if strength.is_linked:
                spec.warnings.append("%s › Normal Map: Strength có nối node; dùng giá trị đang đặt" % owner.name)
            return
    spec.warnings.append("%s › Normal: chỉ hỗ trợ Normal Map (Tangent) nối từ Image Texture; dùng normal của mesh"
                         % owner.name)


def _eye_uv(owner, node, spec):
    src = follow(node.inputs["UV Vector"])
    spec.floats["_DT_EyeUseUV"] = 0.0 if src is None else 1.0
    if src is None:
        return
    is_uv = ((src.node.bl_idname == 'ShaderNodeTexCoord' and src.identifier == "UV")
             or src.node.bl_idname == 'ShaderNodeUVMap')
    if not is_uv:
        spec.warnings.append("%s › UV Vector: chỉ hỗ trợ UV map đầu tiên; Unity dùng uv0" % owner.name)


def _node_inputs(owner, node, spec, meshes):
    nmap = node_maps.NODE_MAPS[node.bl_idname]
    for im in nmap.inputs:
        _read_input(owner, node, im, spec, meshes)
    for prop, unity in nmap.enums:
        spec.floats[unity] = float(node.bl_rna.properties[prop].enum_items[getattr(node, prop)].value)
    for prop, keyword in nmap.modules:
        if getattr(node, prop):
            spec.keywords.add(keyword)
    if nmap.ramp and node.shading_mode == 'RAMP':
        spec.keywords.add("_DT_RAMP")
        spec.ramp = node.shading_ramp
        spec.floats["_DT_RampConstant"] = 1.0 if node.shading_ramp.interpolation == 'CONSTANT' else 0.0
    if nmap.normal:
        _normal_map(owner, node, spec, meshes)
    if node.bl_idname == 'ShaderNodeAnimeEye':
        _eye_uv(owner, node, spec)
    if node.bl_idname == 'ShaderNodeAnimeCel':
        spec.floats["_DT_EmissionStrength"] = 1.0


def _hair_parts(emission):
    """Emission(Color <- Mix[RGBA, ADD](A <- AnimeCel.Color, B <- AngelRing.Color, Factor <- AngelRing.Fac))."""
    color = follow(emission.inputs["Color"])
    if color is None:
        return None
    mix = color.node
    if mix.bl_idname == 'ShaderNodeMix' and mix.data_type == 'RGBA' and mix.blend_type == 'ADD':
        a, b = _socket(mix.inputs, "A_Color"), _socket(mix.inputs, "B_Color")
        fac = _socket(mix.inputs, "Factor_Float")
        clamp_factor, clamp_result = mix.clamp_factor, mix.clamp_result
    elif mix.bl_idname == 'ShaderNodeMixRGB' and mix.blend_type == 'ADD':
        a, b, fac = mix.inputs["Color1"], mix.inputs["Color2"], mix.inputs["Fac"]
        clamp_factor, clamp_result = True, mix.use_clamp
    else:
        return None
    cel_out, ring_out, fac_out = follow(a), follow(b), follow(fac)
    if cel_out is None or ring_out is None or fac_out is None:
        return None
    cel, ring = cel_out.node, ring_out.node
    if cel.bl_idname != 'ShaderNodeAnimeCel' or cel_out.identifier != "Color":
        return None
    if ring.bl_idname != 'ShaderNodeAnimeAngelRing' or ring_out.identifier != "Color":
        return None
    if fac_out.node != ring or fac_out.identifier != "Fac":
        return None
    return cel, ring, clamp_factor, clamp_result


def _hair(mat, emission, parts, spec, meshes):
    cel, ring, clamp_factor, clamp_result = parts
    _node_inputs(mat, cel, spec, meshes)
    for im in node_maps.ANGEL_RING_INPUTS:
        _read_input(mat, ring, im, spec, meshes)
    spec.keywords.add("_DT_ANGEL_RING")
    spec.floats["_DT_RingClampFactor"] = 1.0 if clamp_factor else 0.0
    spec.floats["_DT_RingClampResult"] = 1.0 if clamp_result else 0.0
    strength = emission.inputs["Strength"]
    spec.floats["_DT_EmissionStrength"] = float(strength.default_value)
    if strength.is_linked:
        spec.warnings.append("%s › Emission Strength: có nối node; dùng giá trị đang đặt" % mat.name)
    if ring.inputs["Normal"].is_linked:
        spec.warnings.append("%s › Angel Ring › Normal: Unity dùng normal của bề mặt" % mat.name)


def _render_state(mat, spec):
    """Spec 5, material settings: BLENDED -> Transparent; DITHERED with alpha -> alpha clip; backface culling -> Cull."""
    has_alpha = spec.shader == "AnimeBSDF"
    spec.floats["_Cutoff"] = 0.5
    spec.floats["_Cull"] = 2.0 if mat.use_backface_culling else 0.0
    if has_alpha and mat.surface_render_method == 'BLENDED':
        spec.queue = 3000
        spec.render_type = "Transparent"
        spec.floats.update({"_Surface": 1.0, "_SrcBlend": 5.0, "_DstBlend": 10.0, "_ZWrite": 0.0})
        return
    spec.floats.update({"_Surface": 0.0, "_SrcBlend": 1.0, "_DstBlend": 0.0, "_ZWrite": 1.0})
    if has_alpha and ("_DT_AlphaMap" in spec.textures or spec.floats.get("_DT_Alpha", 1.0) < 1.0):
        spec.keywords.add("_DT_ALPHATEST_ON")
        spec.render_type = "TransparentCutout"


def _outline_channels(mat, spec, meshes):
    pairs = []
    for mesh in meshes:
        n, w = mesh.uv_layers.find(UV_NORMAL), mesh.uv_layers.find(UV_MASK)
        pairs.append((n if n < MAX_UNITY_UV else -1, w if w < MAX_UNITY_UV else -1))
    first = pairs[0] if pairs else (-1, -1)
    if any(pair != first for pair in pairs):
        spec.warnings.append("%s: các mesh dùng material này có thứ tự UV khác nhau; Unity dùng thứ tự của %s"
                             % (mat.name, meshes[0].name))
    if first[0] < 0:
        spec.warnings.append("%s: mesh chưa có %s (hoặc vượt 8 UV map); outline trong Unity đẩy theo normal của mesh"
                             % (mat.name, UV_NORMAL))
    spec.floats["_DT_OutlineUV"] = float(first[0])
    spec.floats["_DT_OutlineWUV"] = float(first[1])


def _outline(mat, spec, meshes):
    from bl_ui import dasktoon_outline as outline
    source = outline.find_source(mat)
    dask = None
    if source is not None:
        outline.sync_material(mat)
        companion = outline.outline_material_for(mat)
        dask = outline.outline_node(companion)
        if dask is None:
            spec.warnings.append("%s: %s thiếu node Dask Outline; tắt outline" % (mat.name, companion.name))
    if dask is None:
        spec.disabled_passes.append(OUTLINE_PASS)
        return
    for im in node_maps.OUTLINE_INPUTS:
        _read_input(companion, dask, im, spec, meshes)
    main = source[1]
    if main is not None:
        spec.floats["_DT_OutlineWidth"] = float(main.inputs["Outline Width"].default_value)
    spec.floats["_DT_OutlineTintMode"] = float(dask.bl_rna.properties["tint_mode"].enum_items[dask.tint_mode].value)
    spec.keywords.add("_DT_OUTLINE")
    spec.outline = True
    _outline_channels(mat, spec, meshes)


def _toggles(spec):
    for keyword in node_maps.SHADER_KEYWORDS[spec.shader]:
        spec.floats[node_maps.KEYWORD_TOGGLES[keyword]] = 1.0 if keyword in spec.keywords else 0.0


def _surface(mat):
    tree = mat.node_tree
    output = tree.get_output_node('EEVEE') if tree is not None else None
    return follow(output.inputs["Surface"]) if output is not None else None


def analyze_material(mat, meshes):
    """(MaterialSpec, "") for a supported material, or (None, reason). `meshes` are the meshes using it."""
    if mat is None:
        return None, "slot trống"
    source = _surface(mat)
    if source is None:
        return None, "Material Output › Surface không nối với node nào"
    node = source.node
    spec = None
    if node.bl_idname in node_maps.NODE_MAPS and source.identifier == "BSDF":
        spec = MaterialSpec(mat, node_maps.NODE_MAPS[node.bl_idname].shader)
        _node_inputs(mat, node, spec, meshes)
    elif node.bl_idname == 'ShaderNodeEmission':
        parts = _hair_parts(node)
        if parts is not None:
            spec = MaterialSpec(mat, "AnimeCel")
            _hair(mat, node, parts, spec, meshes)
    if spec is None:
        return None, "mẫu node chưa được hỗ trợ (%s)" % node.bl_idname
    _render_state(mat, spec)
    _outline(mat, spec, meshes)
    _toggles(spec)
    return spec, ""
```

- [ ] **Step 5: Chạy test, phải PASS**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_graph_test.py 2>&1 | tail -8`
Expected: `Ran 22 tests ... OK`.

- [ ] **Step 6: Commit**

```bash
git add scripts/modules/dasktoon_export/node_maps.py scripts/modules/dasktoon_export/graph.py tests/python/dasktoon_export_graph_test.py
git commit -m "feat: read DaskToon material graphs into Unity material specs"
```

### Task 6: Texture và bake (`textures.py`, `bake.py`)

**Files:**
- Create: `scripts/modules/dasktoon_export/textures.py`
- Create: `scripts/modules/dasktoon_export/bake.py`
- Test: `tests/python/dasktoon_export_textures_test.py`

**Interfaces:**
- Consumes: `graph.follow`, `graph.TexSource`.
- Produces (`textures`): `RAMP_WIDTH = 256`, `png_bytes(width, height, rgba_bytes) -> bytes`,
  `float_to_png(pixels, width, height, srgb) -> bytes`, `needs_float(pixels) -> bool`, `ramp_pixels(ramp) -> bytes`,
  `ramp_png(ramp) -> bytes`, `image_file(image) -> (ext, bytes) | None`, `exr_bytes(pixels, width, height) -> bytes`.
- Produces (`bake`): `MARGIN = 16`, `branch_size(tree_owner, node_name, socket_identifier, default) -> int`,
  `bake_input(obj, material, source: TexSource, size, samples) -> numpy.float32[size*size*4]`.

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_export_textures_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Ramp strips, PNG / EXR writing, copied images and Cycles baking (spec 4, 5)."""

import os
import sys
import tempfile
import unittest

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_export import bake, graph, textures  # noqa: E402

TMP = tempfile.mkdtemp(prefix="dt_textures_")


def load_pixels(name, data):
    path = os.path.join(TMP, name)
    with open(path, "wb") as f:
        f.write(data)
    img = bpy.data.images.load(path, check_existing=False)
    pixels = np.array(img.pixels[:]).reshape(-1, 4)
    size = tuple(img.size)
    bpy.data.images.remove(img)
    return pixels, size


def data_counts():
    return {name: len(getattr(bpy.data, name)) for name in ("objects", "meshes", "materials", "images", "shape_keys")}


class TextureFileTest(unittest.TestCase):
    def test_png_rows_are_bottom_up_like_blender(self):
        rgba = bytes([255, 0, 0, 255, 0, 255, 0, 255,      # bottom row: red, green
                      0, 0, 255, 255, 255, 255, 255, 255])  # top row: blue, white
        pixels, size = load_pixels("rows.png", textures.png_bytes(2, 2, rgba))
        self.assertEqual(size, (2, 2))
        np.testing.assert_allclose(pixels[0], (1, 0, 0, 1), atol=1e-6)
        np.testing.assert_allclose(pixels[2], (0, 0, 1, 1), atol=1e-6)

    def test_float_png_encodes_colour_as_srgb_and_numbers_raw(self):
        half = np.full(4, 0.5, dtype=np.float32)
        half[3] = 1.0
        raw = textures.float_to_png(half, 1, 1, srgb=False)
        srgb = textures.float_to_png(half, 1, 1, srgb=True)
        self.assertEqual(raw, textures.png_bytes(1, 1, bytes([128, 128, 128, 255])))
        self.assertEqual(srgb, textures.png_bytes(1, 1, bytes([188, 188, 188, 255])))

    def test_needs_float(self):
        self.assertFalse(textures.needs_float(np.array([0.0, 0.5, 1.0, 1.0])))
        self.assertTrue(textures.needs_float(np.array([1.5, 0.5, 0.5, 1.0])))
        self.assertTrue(textures.needs_float(np.array([-0.2, 0.5, 0.5, 1.0])))

    def test_ramp_strip_samples_texel_centres(self):
        mat, node = tu.node_material("RampTest", 'ShaderNodeDaskCel')
        ramp = node.shading_ramp
        ramp.interpolation = 'CONSTANT'
        ramp.elements[0].position = 0.0
        ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        ramp.elements[1].position = 0.5
        ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
        px = textures.ramp_pixels(ramp)
        self.assertEqual(len(px), textures.RAMP_WIDTH * 4)
        self.assertEqual(px[127 * 4], 0)
        self.assertEqual(px[128 * 4], 255)
        ramp.interpolation = 'LINEAR'
        ramp.elements[1].position = 1.0
        px = textures.ramp_pixels(ramp)
        t = 100.5 / 256.0
        want = round((1.055 * t ** (1 / 2.4) - 0.055) * 255)
        self.assertLessEqual(abs(px[100 * 4] - want), 1)
        self.assertEqual(px[100 * 4 + 3], 255)
        pixels, size = load_pixels("ramp.png", textures.ramp_png(ramp))
        self.assertEqual(size, (256, 1))

    def test_image_file_reads_disk_and_packed_images(self):
        path = os.path.join(TMP, "disk.png")
        with open(path, "wb") as f:
            f.write(textures.png_bytes(1, 1, bytes([10, 20, 30, 255])))
        img = bpy.data.images.load(path)
        ext, data = textures.image_file(img)
        self.assertEqual(ext, ".png")
        with open(path, "rb") as f:
            self.assertEqual(data, f.read())
        img.pack()
        os.remove(path)
        ext, packed = textures.image_file(img)
        self.assertEqual((ext, packed), (".png", data))
        img.unpack(method='REMOVE')
        self.assertIsNone(textures.image_file(img))

    def test_exr_keeps_values_above_one(self):
        px = np.array([2.0, 0.25, -0.5, 1.0] * 4, dtype=np.float32)
        pixels, size = load_pixels("hdr.exr", textures.exr_bytes(px, 2, 2))
        self.assertEqual(size, (2, 2))
        np.testing.assert_allclose(pixels[0], (2.0, 0.25, -0.5, 1.0), atol=1e-3)


class BakeTest(unittest.TestCase):
    def setUp(self):
        tu.reset_scene()
        bpy.ops.mesh.primitive_plane_add(size=2.0)
        self.obj = bpy.context.active_object
        self.mat, self.node = tu.node_material("Baked", 'ShaderNodeAnimeCharacter')
        tu.assign(self.obj, self.mat)
        self.nt = self.mat.node_tree

    def source(self, socket, is_color=True):
        return graph.TexSource('BAKE', is_color, self.mat, self.node.name, socket, None)

    def test_constant_colour_branch(self):
        mix = self.nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        sockets = {s.identifier: s for s in mix.inputs}
        sockets["Factor_Float"].default_value = 0.25
        sockets["A_Color"].default_value = (1.0, 0.0, 0.0, 1.0)
        sockets["B_Color"].default_value = (0.0, 0.0, 1.0, 1.0)
        self.nt.links.new(next(s for s in mix.outputs if s.identifier == "Result_Color"), self.node.inputs["Base Color"])
        px = bake.bake_input(self.obj, self.mat, self.source("Base Color"), 16, 4).reshape(-1, 4)
        np.testing.assert_allclose(px[:, :3].mean(axis=0), (0.75, 0.0, 0.25), atol=0.01)

    def test_float_branch(self):
        value = self.nt.nodes.new('ShaderNodeValue')
        value.outputs[0].default_value = 0.3
        self.nt.links.new(value.outputs[0], self.node.inputs["Shadow Threshold"])
        px = bake.bake_input(self.obj, self.mat, self.source("Shadow Threshold", False), 16, 4).reshape(-1, 4)
        np.testing.assert_allclose(px[:, :3].mean(axis=0), (0.3, 0.3, 0.3), atol=0.01)

    def test_user_state_and_data_are_restored(self):
        other = tu.add_sphere(segments=8, rings=4)
        other.data = self.obj.data            # a linked duplicate shares the mesh
        other.select_set(True)
        bpy.context.view_layer.objects.active = other
        self.obj.select_set(False)
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_EEVEE'
        scene.cycles.samples = 7
        value = self.nt.nodes.new('ShaderNodeValue')
        self.nt.links.new(value.outputs[0], self.node.inputs["Shadow Threshold"])
        before = data_counts()
        bake.bake_input(self.obj, self.mat, self.source("Shadow Threshold", False), 8, 2)
        self.assertEqual(data_counts(), before)
        self.assertEqual(scene.render.engine, 'BLENDER_EEVEE')
        self.assertEqual(scene.cycles.samples, 7)
        self.assertEqual(bpy.context.view_layer.objects.active, other)
        self.assertTrue(other.select_get())
        self.assertFalse(self.obj.select_get())
        self.assertEqual(self.obj.data.users, 2)

    def test_branch_size_is_the_largest_image(self):
        tex = self.nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.new("Big", 64, 32)
        self.nt.links.new(tex.outputs["Color"], self.node.inputs["Base Color"])
        self.assertEqual(bake.branch_size(self.mat, self.node.name, "Base Color", 1024), 64)
        self.assertEqual(bake.branch_size(self.mat, self.node.name, "Shadow Color", 1024), 1024)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, phải FAIL**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_textures_test.py 2>&1 | tail -5`
Expected: `ImportError: cannot import name 'bake'`.

- [ ] **Step 3: Viết hai module**

File: `scripts/modules/dasktoon_export/textures.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Texture files for Unity: copied images, 256x1 ramp strips, baked branches as PNG or EXR (spec 4, 5)."""

import os
import struct
import tempfile
import zlib

import bpy
import numpy as np

RAMP_WIDTH = 256
UNITY_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tga", ".exr", ".psd", ".tif", ".tiff", ".bmp", ".hdr"}
FORMAT_EXTENSIONS = {'PNG': ".png", 'JPEG': ".jpg", 'TARGA': ".tga", 'TARGA_RAW': ".tga", 'OPEN_EXR': ".exr",
                     'TIFF': ".tif", 'BMP': ".bmp", 'HDR': ".hdr"}


def png_bytes(width, height, rgba):
    """8-bit RGBA PNG. `rgba` holds rows bottom-up, the way Blender stores pixels."""
    stride = width * 4
    raw = bytearray()
    for y in range(height - 1, -1, -1):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def _srgb(values):
    values = np.clip(values, 0.0, None)
    return np.where(values <= 0.0031308, values * 12.92, 1.055 * np.power(values, 1.0 / 2.4) - 0.055)


def _to_bytes(px):
    return (np.clip(px, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).tobytes()


def float_to_png(pixels, width, height, srgb):
    """PNG of float RGBA pixels (rows bottom-up): colour data is sRGB-encoded, numbers are stored as they are."""
    px = np.asarray(pixels, dtype=np.float64).reshape(-1, 4).copy()
    if srgb:
        px[:, :3] = _srgb(px[:, :3])
    return png_bytes(width, height, _to_bytes(px))


def needs_float(pixels):
    """True when a baked branch leaves the 0-1 range and must be stored as EXR."""
    rgb = np.asarray(pixels).reshape(-1, 4)[:, :3]
    return bool((rgb < -1e-4).any() or (rgb > 1.0 + 1e-4).any())


def ramp_pixels(ramp):
    """RGBA bytes of the 256x1 ramp strip: pixel i = ramp.evaluate((i + 0.5) / 256), sRGB-encoded."""
    px = np.array([ramp.evaluate((i + 0.5) / RAMP_WIDTH) for i in range(RAMP_WIDTH)], dtype=np.float64)
    px[:, 3] = 1.0
    px[:, :3] = _srgb(px[:, :3])
    return _to_bytes(px)


def ramp_png(ramp):
    return png_bytes(RAMP_WIDTH, 1, ramp_pixels(ramp))


def image_file(image):
    """(extension, bytes) of an image's own file, packed or on disk; None when Unity cannot use it as is."""
    if image.packed_file is not None:
        ext = os.path.splitext(image.filepath)[1].lower() or FORMAT_EXTENSIONS.get(image.file_format, "")
        data = bytes(image.packed_file.data)
    else:
        path = bpy.path.abspath(image.filepath, library=image.library)
        if not os.path.isfile(path):
            return None
        ext = os.path.splitext(path)[1].lower()
        with open(path, "rb") as f:
            data = f.read()
    if ext not in UNITY_IMAGE_EXTENSIONS:
        return None
    return ext, data


def exr_bytes(pixels, width, height):
    """Float RGBA pixels (rows bottom-up) as OpenEXR, written through a throwaway Blender image."""
    image = bpy.data.images.new("DT_ExportEXR", width, height, alpha=True, float_buffer=True, is_data=True)
    path = os.path.join(tempfile.mkdtemp(prefix="dt_exr_"), "texture.exr")
    try:
        image.pixels.foreach_set(np.asarray(pixels, dtype=np.float32).ravel())
        image.filepath_raw = path
        image.file_format = 'OPEN_EXR'
        image.save()
        with open(path, "rb") as f:
            return f.read()
    finally:
        bpy.data.images.remove(image)
        if os.path.exists(path):
            os.remove(path)
```

File: `scripts/modules/dasktoon_export/bake.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Bake a node branch to pixels with Cycles Emit on throwaway data (spec 5). The user's selection, active object,
render engine and samples are restored and every temporary datablock is removed, also on error."""

import bmesh
import bpy
import numpy as np

from .graph import follow

MARGIN = 16


def _input(tree, node_name, socket_identifier):
    node = tree.nodes[node_name]
    return next(s for s in node.inputs if s.identifier == socket_identifier)


def branch_size(tree_owner, node_name, socket_identifier, default):
    """Bake resolution: the largest image in the branch, else `default` (spec 5)."""
    size = 0
    seen = set()
    stack = [follow(_input(tree_owner.node_tree, node_name, socket_identifier))]
    while stack:
        out = stack.pop()
        if out is None or out.node.as_pointer() in seen:
            continue
        seen.add(out.node.as_pointer())
        if out.node.bl_idname == 'ShaderNodeTexImage' and out.node.image is not None:
            size = max(size, *out.node.image.size)
        stack.extend(follow(s) for s in out.node.inputs if s.enabled)
    return size or default


def _faces_mesh(obj, material):
    """A copy of obj's mesh keeping only the faces that use `material`."""
    slot = next(i for i, s in enumerate(obj.material_slots) if s.material == material)
    mesh = obj.data.copy()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != slot], context='FACES')
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def _bake_material(source, image):
    """A copy of the branch's material whose only output is Emission(branch) and whose active node is `image`."""
    mat = source.tree_owner.copy()
    tree = mat.node_tree
    upstream = follow(_input(tree, source.node, source.socket))
    for node in tree.nodes:
        if node.bl_idname == 'ShaderNodeOutputMaterial':
            node.is_active_output = False
    output = tree.nodes.new('ShaderNodeOutputMaterial')
    output.target = 'ALL'
    output.is_active_output = True
    emission = tree.nodes.new('ShaderNodeEmission')
    emission.inputs["Strength"].default_value = 1.0
    tree.links.new(upstream, emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    tex = tree.nodes.new('ShaderNodeTexImage')
    tex.image = image
    for node in tree.nodes:
        node.select = False
    tex.select = True
    tree.nodes.active = tex
    return mat


def bake_input(obj, material, source, size, samples):
    """Float RGBA pixels (size x size, rows bottom-up) of the branch feeding source.node / source.socket in
    source.tree_owner's tree, baked on the faces of `obj` that use `material`, over the first UV map."""
    if not obj.data.uv_layers:
        raise RuntimeError("mesh %s không có UV map để bake" % obj.name)
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    selected = [o for o in view_layer.objects if o.select_get()]
    active = view_layer.objects.active
    engine, samples_before, device = scene.render.engine, scene.cycles.samples, scene.cycles.device
    temp_obj = mesh = mat = image = None
    try:
        image = bpy.data.images.new("DT_Bake", size, size, alpha=True, float_buffer=True, is_data=True)
        mat = _bake_material(source, image)
        mesh = _faces_mesh(obj, material)
        mesh.materials.clear()
        mesh.materials.append(mat)
        for poly in mesh.polygons:
            poly.material_index = 0
        mesh.uv_layers.active_index = 0
        temp_obj = bpy.data.objects.new("DT_BakeObject", mesh)
        temp_obj.matrix_world = obj.matrix_world
        scene.collection.objects.link(temp_obj)
        if mesh.shape_keys is not None:
            temp_obj.shape_key_clear()
        for o in selected:
            o.select_set(False)
        temp_obj.select_set(True)
        view_layer.objects.active = temp_obj
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = samples
        scene.cycles.device = 'CPU'
        bpy.ops.object.bake(type='EMIT', margin=MARGIN, margin_type='EXTEND', use_clear=True,
                            target='IMAGE_TEXTURES')
        pixels = np.empty(size * size * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        return pixels
    finally:
        if temp_obj is not None:
            bpy.data.objects.remove(temp_obj)
        if mesh is not None:
            bpy.data.meshes.remove(mesh)
        if mat is not None:
            bpy.data.materials.remove(mat)
        if image is not None:
            bpy.data.images.remove(image)
        scene.render.engine = engine
        scene.cycles.samples = samples_before
        scene.cycles.device = device
        for o in view_layer.objects:
            try:
                o.select_set(o in selected)
            except RuntimeError:
                pass
        view_layer.objects.active = active
```

- [ ] **Step 4: Chạy test, phải PASS**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_textures_test.py 2>&1 | tail -8`
Expected: `Ran 10 tests ... OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/modules/dasktoon_export/textures.py scripts/modules/dasktoon_export/bake.py tests/python/dasktoon_export_textures_test.py
git commit -m "feat: write ramp strips, copied images and Cycles bakes for Engine Export"
```

---

### Task 7: Model FBX (`model_fbx.py`)

**Files:**
- Create: `scripts/modules/dasktoon_export/model_fbx.py`
- Test: `tests/python/dasktoon_export_fbx_test.py`

**Interfaces:**
- Consumes: `bl_ui.dasktoon_outline.find_source`, `bl_ui.dasktoon_outline_gamedata.write_outline_uvs`,
  `bl_ui.dasktoon_outline_nodes.MODIFIER_NAME`, `unity_yaml.model_meta`.
- Produces: `FBX_SETTINGS` (dict tham số cố định của spec 4), `export_objects(context, selected_only) -> list[Object]`
  (khi chọn "chỉ object đang chọn" thì thêm cả armature đang deform các mesh được chọn), `outline_meshes(objects)`,
  `prepare_outline_data(objects) -> (done_names, errors)`, `modifier_notes(objects) -> list[str]`,
  `write_fbx(context, objects, filepath, include_animation)`.

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_export_fbx_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""FBX for Unity keeps shape keys and DT_OutlineN/W and never contains the outline hull (spec 4)."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from bl_ui import dasktoon_outline_nodes as gn  # noqa: E402
from dasktoon_export import model_fbx  # noqa: E402


def outlined_character():
    tu.reset_scene()
    outline.reset_cache()
    obj = tu.add_sphere(segments=16, rings=8)
    obj.name = "Body"
    mat, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    node.use_outline = True
    tu.assign(obj, mat)
    obj.shape_key_add(name="Basis")
    smile = obj.shape_key_add(name="Smile")
    smile.data[0].co.z += 0.1
    outline.sync_all(bpy.context.scene)
    return obj


class FbxTest(unittest.TestCase):
    def test_fbx_keeps_shape_keys_and_outline_uvs_without_hull(self):
        obj = outlined_character()
        self.assertIsNotNone(obj.modifiers.get(gn.MODIFIER_NAME))
        faces = len(obj.data.polygons)
        done, errors = model_fbx.prepare_outline_data([obj])
        self.assertEqual((done, errors), (["Body"], []))
        path = os.path.join(tempfile.mkdtemp(prefix="dt_fbx_"), "Hero.fbx")
        model_fbx.write_fbx(bpy.context, [obj], path, include_animation=False)
        tu.reset_scene()
        bpy.ops.import_scene.fbx(filepath=path)
        imported = next(o for o in bpy.data.objects if o.type == 'MESH')
        self.assertEqual(len(imported.data.polygons), faces)
        self.assertIn("Smile", imported.data.shape_keys.key_blocks)
        names = [uv.name for uv in imported.data.uv_layers]
        self.assertEqual(names[0], "UVMap")
        self.assertIn("DT_OutlineN", names)
        self.assertIn("DT_OutlineW", names)
        self.assertEqual([m.name for m in imported.data.materials], ["Skin"])

    def test_selection_is_restored_after_writing(self):
        obj = outlined_character()
        other = tu.add_sphere(segments=8, rings=4)
        bpy.context.view_layer.objects.active = other
        other.select_set(True)
        obj.select_set(False)
        path = os.path.join(tempfile.mkdtemp(prefix="dt_fbx_"), "Only.fbx")
        model_fbx.write_fbx(bpy.context, [obj], path, include_animation=False)
        self.assertTrue(other.select_get())
        self.assertFalse(obj.select_get())
        self.assertEqual(bpy.context.view_layer.objects.active, other)

    def test_selected_only_adds_the_deforming_armature(self):
        obj = outlined_character()
        arm = bpy.data.objects.new("Rig", bpy.data.armatures.new("Rig"))
        bpy.context.scene.collection.objects.link(arm)
        obj.modifiers.new("Armature", 'ARMATURE').object = arm
        for o in bpy.context.view_layer.objects:
            o.select_set(o == obj)
        chosen = model_fbx.export_objects(bpy.context, selected_only=True)
        self.assertEqual(set(o.name for o in chosen), {"Body", "Rig"})
        everything = model_fbx.export_objects(bpy.context, selected_only=False)
        self.assertNotIn("Camera", [o.name for o in everything])

    def test_outline_errors_are_reported_not_raised(self):
        obj = outlined_character()
        obj.data.uv_layers.remove(obj.data.uv_layers[0])
        done, errors = model_fbx.prepare_outline_data([obj])
        self.assertEqual(done, [])
        self.assertEqual(len(errors), 1)

    def test_modifier_notes_skip_armature_and_outline(self):
        obj = outlined_character()
        obj.modifiers.new("Mirror", 'MIRROR')
        obj.modifiers.new("Armature", 'ARMATURE')
        notes = model_fbx.modifier_notes([obj])
        self.assertEqual(len(notes), 1)
        self.assertIn("Mirror", notes[0])
        self.assertNotIn(gn.MODIFIER_NAME, notes[0])


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, phải FAIL**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_fbx_test.py 2>&1 | tail -5`
Expected: `ImportError: cannot import name 'model_fbx'`.

- [ ] **Step 3: Viết module**

File: `scripts/modules/dasktoon_export/model_fbx.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""FBX model for Unity (spec 4). Modifiers are not applied, so shape keys survive and the Geometry Nodes outline
hull stays out of the file; Unity draws the outline in the shader from DT_OutlineN/W."""

import bpy

EXPORT_TYPES = {'ARMATURE', 'MESH', 'EMPTY'}
FBX_SETTINGS = dict(
    use_mesh_modifiers=False,
    axis_forward='-Z',
    axis_up='Y',
    apply_scale_options='FBX_SCALE_ALL',
    add_leaf_bones=False,
    use_armature_deform_only=True,
    mesh_smooth_type='FACE',
    object_types=EXPORT_TYPES,
    path_mode='STRIP',
    embed_textures=False,
)


def export_objects(context, selected_only):
    """The selection (plus the armatures deforming it), or every visible armature, mesh and empty."""
    if not selected_only:
        return [o for o in context.scene.objects if o.type in EXPORT_TYPES and o.visible_get()]
    chosen = [o for o in context.selected_objects if o.type in EXPORT_TYPES]
    for obj in list(chosen):
        rigs = [m.object for m in getattr(obj, "modifiers", ()) if m.type == 'ARMATURE' and m.object is not None]
        if obj.parent is not None and obj.parent.type == 'ARMATURE':
            rigs.append(obj.parent)
        chosen += [rig for rig in rigs if rig not in chosen]
    return chosen


def outline_meshes(objects):
    from bl_ui import dasktoon_outline as outline
    return [o for o in objects if o.type == 'MESH'
            and any(outline.find_source(slot.material) is not None for slot in o.material_slots)]


def prepare_outline_data(objects):
    """DT_OutlineN/W on every outlined mesh (project 1, spec 5). Returns (names written, error messages)."""
    from bl_ui import dasktoon_outline_gamedata as gamedata
    done, errors, seen = [], [], set()
    for obj in outline_meshes(objects):
        if obj.data in seen:
            continue
        seen.add(obj.data)
        if obj.data.library is not None:
            errors.append("%s: mesh link từ thư viện, không ghi được dữ liệu outline" % obj.name)
            continue
        ok, message = gamedata.write_outline_uvs(obj)
        if ok:
            done.append(obj.name)
        else:
            errors.append(message)
    return done, errors


def modifier_notes(objects):
    """Modifiers other than Armature and the DaskToon outline are not in the FBX (Apply Modifiers is off)."""
    from bl_ui import dasktoon_outline_nodes as gn
    notes = []
    for obj in objects:
        extra = [m.name for m in getattr(obj, "modifiers", ()) if m.type != 'ARMATURE' and m.name != gn.MODIFIER_NAME]
        if obj.type == 'MESH' and extra:
            notes.append("%s: modifier %s không được áp dụng vào FBX; hãy Apply trước khi export nếu cần"
                         % (obj.name, ", ".join(extra)))
    return notes


def write_fbx(context, objects, filepath, include_animation):
    """Export `objects` with the fixed settings of spec 4; the user's selection and active object are restored."""
    view_layer = context.view_layer
    selected = [o for o in view_layer.objects if o.select_get()]
    active = view_layer.objects.active
    try:
        for obj in selected:
            obj.select_set(False)
        for obj in objects:
            obj.select_set(True)
        bpy.ops.export_scene.fbx(filepath=filepath, use_selection=True, bake_anim=include_animation, **FBX_SETTINGS)
    finally:
        for obj in view_layer.objects:
            try:
                obj.select_set(obj in selected)
            except RuntimeError:
                pass
        view_layer.objects.active = active
```

- [ ] **Step 4: Chạy test, phải PASS**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_fbx_test.py 2>&1 | tail -8`
Expected: `Ran 5 tests ... OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/modules/dasktoon_export/model_fbx.py tests/python/dasktoon_export_fbx_test.py
git commit -m "feat: export DaskToon characters to FBX with shape keys and outline UV data"
```

### Task 8: Ghép toàn bộ export (`export_model`), báo cáo, bố cục; kiểm tra FBX trong Unity

**Files:**
- Modify: `scripts/modules/dasktoon_export/__init__.py` (thay toàn bộ nội dung)
- Create: `scripts/modules/dasktoon_export/report.py`
- Create: `tests/unity/Editor/DaskToonModelTests.cs`
- Test: `tests/python/dasktoon_export_layout_test.py`, `tests/python/dasktoon_unity_model_test.py`

**Interfaces:**
- Consumes: mọi module ở Task 2–7.
- Produces (`dasktoon_export`): `ExportOptions(model_format='FBX', include_animation=True, export_materials=True, bake_size=1024, bake_samples=16)`,
  `safe_name(name) -> str`, `export_model(context, target, objects, options) -> report.Report`.
- Produces (`report`): `REPORT_TEXT = "DaskToon Engine Export Report"`, `Report` (các trường `mode, root, name, shaders, model,
  materials, skipped, baked, outline_meshes, modifier_notes, warnings, light_hint, ambient_hint`; `lines()`, `summary()`),
  `light_hint(scene)`, `ambient_hint(scene)`, `readme_text(report)`, `write_text(report)`, `show_popup(report)`.
- Produces (C#): `DaskToonModelTests.CheckModel` (args: `model`, `mesh`, `outlineUV`, `normals: [{p, n}]` theo trục Unity) →
  `{imported, materials: {tên: đường dẫn}, meshFound, blendShapes, uvChannels, matched, vertices, maxNormalAngle, top}`.

- [ ] **Step 1: Viết test bố cục (headless)**

File: `tests/python/dasktoon_export_layout_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export end to end: folder layout in both modes, metas, stable GUIDs, user files, report (spec 4, 5)."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import assets, targets, textures  # noqa: E402

OPTIONS = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_character(blend_dir=None):
    """Body: Skin (Anime BSDF, outline, image base colour), 'Áo: đỏ' (Dask Cel), Plastic (unsupported), an empty slot."""
    tu.reset_scene()
    outline.reset_cache()
    tu.add_sun(strength=3.0, rotation=(0.6, 0.0, 0.8))
    body = tu.add_sphere(segments=16, rings=8)
    body.name = "Body"
    skin, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    node.use_outline = True
    png = os.path.join(tempfile.mkdtemp(prefix="dt_layout_img_"), "skin.png")
    with open(png, "wb") as f:
        f.write(textures.png_bytes(2, 2, bytes([200, 150, 120, 255] * 4)))
    tex = skin.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(png)
    skin.node_tree.links.new(tex.outputs["Color"], node.inputs["Base Color"])
    cloth, _cel = tu.node_material("Áo: đỏ", 'ShaderNodeDaskCel')
    plastic = bpy.data.materials.new("Plastic")
    for mat in (skin, cloth, plastic):
        body.data.materials.append(mat)
    body.data.materials.append(None)
    for i, poly in enumerate(body.data.polygons):
        poly.material_index = i % 3
    outline.sync_all(bpy.context.scene)
    if blend_dir:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(blend_dir, "Hero.blend"))
    return body


def export_to(directory, objects=None):
    name = targets.blend_name(bpy.data.filepath)
    target = targets.make_target(directory, name)
    objects = objects or [o for o in bpy.context.scene.objects if o.type == 'MESH']
    return target, dasktoon_export.export_model(bpy.context, target, objects, OPTIONS)


def fake_project():
    root = os.path.join(tempfile.mkdtemp(prefix="dt_layout_proj_"), "Game")
    os.makedirs(os.path.join(root, "Assets"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


class LayoutTest(unittest.TestCase):
    def test_folder_mode_layout(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        target, rep = export_to(out)
        root = os.path.join(out, "Hero_Unity")
        self.assertEqual((target.mode, target.root), ('FOLDER', root))
        for rel in ("README.txt", "Shaders/AnimeBSDF.shader", "Shaders/DaskToonShaders.version", "Hero",
                    "Hero/Model", "Hero/Model/Hero.fbx", "Hero/Materials", "Hero/Materials/Skin.mat",
                    "Hero/Materials/Áo_ đỏ.mat", "Hero/Textures", "Hero/Textures/Skin_Base.png", "Shaders"):
            self.assertTrue(os.path.exists(os.path.join(root, rel)), rel)
            self.assertTrue(os.path.exists(os.path.join(root, rel) + ".meta"), rel + ".meta")
        self.assertFalse(os.path.exists(os.path.join(root, "Hero/Materials/Plastic.mat")))
        meta = read(os.path.join(root, "Hero/Model/Hero.fbx.meta"))
        self.assertIn("      name: Skin\n", meta)
        self.assertIn("      name: 'Áo: đỏ'\n", meta)
        self.assertNotIn("Plastic", meta)
        self.assertIn("Áo_ đỏ", read(os.path.join(root, "Hero/Materials/Áo_ đỏ.mat")))
        self.assertEqual([name for name, _reason in rep.skipped], ["Plastic"])
        self.assertEqual(rep.shaders, 'INSTALLED')
        readme = read(os.path.join(root, "README.txt"))
        self.assertIn("Sun 3.0 → Directional 0.955", readme)
        self.assertIn("Linear", readme)
        self.assertIn(rep.light_hint, "\n".join(rep.lines()))
        self.assertIn(dasktoon_export.report.REPORT_TEXT, bpy.data.texts)

    def test_guids_are_stable_between_exports(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        export_to(out)
        root = os.path.join(out, "Hero_Unity")
        first = {rel: read(os.path.join(root, rel)) for rel in
                 ("Hero/Materials/Skin.mat.meta", "Hero/Materials/Skin.mat", "Hero/Model/Hero.fbx.meta",
                  "Hero/Textures/Skin_Base.png.meta", "Hero.meta")}
        export_to(out)
        for rel, text in first.items():
            self.assertEqual(read(os.path.join(root, rel)), text, rel)

    def test_project_mode_writes_into_assets_dasktoon(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        project = fake_project()
        target, rep = export_to(os.path.join(project, "Assets"))
        root = os.path.join(project, "Assets", "DaskToon")
        self.assertEqual((target.mode, target.root), ('PROJECT', root))
        self.assertTrue(os.path.exists(root + ".meta"))
        self.assertTrue(os.path.exists(os.path.join(root, "Hero/Materials/Skin.mat")))
        self.assertFalse(os.path.exists(os.path.join(root, "README.txt")))
        _target, again = export_to(project)
        self.assertEqual(again.shaders, 'UP_TO_DATE')

    def test_user_file_with_the_same_name_is_kept(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        project = fake_project()
        user = os.path.join(project, "Assets", "DaskToon", "Hero", "Materials", "Skin.mat")
        os.makedirs(os.path.dirname(user))
        with open(user, "w", encoding="utf-8") as f:
            f.write("user material")
        _target, rep = export_to(project)
        self.assertEqual(read(user), "user material")
        self.assertTrue(any("Skin.mat" in w for w in rep.warnings), rep.warnings)

    def test_untitled_file(self):
        build_character()
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        target, _rep = export_to(out)
        self.assertEqual(target.root, os.path.join(out, "Untitled_Unity"))
        self.assertTrue(os.path.exists(os.path.join(target.root, "Untitled/Model/Untitled.fbx")))

    def test_base_texture_shared_with_outline_is_written_once(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        export_to(out)
        textures_dir = os.path.join(out, "Hero_Unity", "Hero", "Textures")
        pngs = sorted(f for f in os.listdir(textures_dir) if f.endswith(".png"))
        self.assertEqual(pngs, ["Skin_Base.png"])
        guid = assets.read_meta_guid(os.path.join(textures_dir, "Skin_Base.png.meta"))
        mat = read(os.path.join(out, "Hero_Unity", "Hero", "Materials", "Skin.mat"))
        self.assertEqual(mat.count(guid), 2)

    def test_mesh_without_uv_still_exports(self):
        body = build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        body.data.uv_layers.remove(body.data.uv_layers[0])
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        _target, rep = export_to(out)
        self.assertTrue(rep.warnings)
        mat = read(os.path.join(out, "Hero_Unity", "Hero", "Materials", "Skin.mat"))
        self.assertIn("    - _DT_OutlineUV: -1\n", mat)

    def test_materials_only(self):
        build_character(tempfile.mkdtemp(prefix="dt_layout_blend_"))
        out = tempfile.mkdtemp(prefix="dt_layout_out_")
        target = targets.make_target(out, "Hero")
        options = dasktoon_export.ExportOptions(model_format='NONE', bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [bpy.data.objects["Body"]], options)
        self.assertEqual(rep.model, "")
        self.assertFalse(os.path.exists(os.path.join(target.root, "Hero", "Model")))
        self.assertTrue(os.path.exists(os.path.join(target.root, "Hero", "Materials", "Skin.mat")))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, phải FAIL**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_layout_test.py 2>&1 | tail -5`
Expected: `AttributeError: module 'dasktoon_export' has no attribute 'ExportOptions'`.

- [ ] **Step 3: Viết `report.py` và `export_model`**

File: `scripts/modules/dasktoon_export/report.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Engine Export report: Text datablock, popup, README.txt and the light hints (spec 3, 5)."""

import math
from dataclasses import dataclass, field

import bpy

from . import unity_yaml

REPORT_TEXT = "DaskToon Engine Export Report"
POPUP_LINES = 14
SHADER_STATE = {
    'INSTALLED': "Shader: đã cài hoặc cập nhật",
    'UP_TO_DATE': "Shader: project đã có bản đủ mới, không ghi lại",
    'SKIPPED': "Shader: không xuất (đã tắt xuất material)",
}


@dataclass
class Report:
    mode: str
    root: str
    name: str
    shaders: str = 'SKIPPED'
    model: str = ""
    materials: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    baked: list = field(default_factory=list)
    outline_meshes: list = field(default_factory=list)
    modifier_notes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    light_hint: str = ""
    ambient_hint: str = ""

    def summary(self):
        return "Engine Export: %d material, %s, %d cảnh báo" % (
            len(self.materials), "có FBX" if self.model else "không có model", len(self.warnings))

    def lines(self):
        where = "ghi thẳng vào project Unity" if self.mode == 'PROJECT' else "thư mục để kéo vào Unity"
        out = ["Đích: %s (%s)" % (self.root, where), SHADER_STATE[self.shaders]]
        if self.model:
            out.append("Model: " + self.model)
        out.append("Material đã xuất (%d): %s" % (len(self.materials), ", ".join(self.materials) or "không có"))
        out += ["Bỏ qua material %s: %s (Unity giữ material mặc định của FBX)" % item for item in self.skipped]
        if self.baked:
            out.append("Đã bake: " + ", ".join(self.baked))
        if self.outline_meshes:
            out.append("Đã ghi DT_OutlineN/W cho: " + ", ".join(self.outline_meshes))
        out += self.modifier_notes
        out += ["Cảnh báo: " + w for w in self.warnings]
        out += [hint for hint in (self.light_hint, self.ambient_hint) if hint]
        out.append("Project Unity phải dùng Linear color space (mặc định của URP).")
        out.append("Export lại sẽ ghi đè mọi chỉnh sửa tay trên các asset này trong Unity.")
        return out


def light_hint(scene):
    """Unity Directional intensity = Blender Sun strength / pi (measured: Sun 1 gives 1/pi of diffuse light)."""
    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.data.type == 'SUN':
            strength = obj.data.energy
            return "Đèn gợi ý: Sun %s → Directional %.3f" % (round(strength, 3), strength / math.pi)
    return "Đèn gợi ý: scene không có Sun; Directional của Unity = Sun strength ÷ π"


def ambient_hint(scene):
    """The World colour is the ambient, 1:1 (Environment Lighting › Source: Color)."""
    world = scene.world
    background = None
    if world is not None and world.node_tree is not None:
        background = next((n for n in world.node_tree.nodes if n.bl_idname == 'ShaderNodeBackground'), None)
    if background is None or background.inputs["Color"].is_linked or background.inputs["Strength"].is_linked:
        return "Ambient: World không phải một màu đơn; tự đặt Environment Lighting trong Unity"
    strength = background.inputs["Strength"].default_value
    linear = [c * strength for c in background.inputs["Color"].default_value[:3]]
    hexa = "".join("%02X" % min(255, int(round(unity_yaml.linear_to_srgb(c) * 255))) for c in linear)
    return "Ambient gợi ý (Environment Lighting › Source: Color): #%s (linear %.3f, %.3f, %.3f)" % (hexa, *linear)


def readme_text(report):
    head = [
        "DaskToon Engine Export: %s" % report.name,
        "",
        "Cách dùng (Unity 6, URP 17.5):",
        "1. Kéo cả thư mục %s_Unity vào cửa sổ Project của Unity." % report.name,
        "2. Project phải dùng Linear color space (Project Settings › Player › Other Settings › Color Space).",
        "3. Đặt Directional Light và Ambient theo gợi ý bên dưới.",
        "",
        "Lưu ý: kéo thư mục của nhân vật thứ hai vào cùng project, Unity sẽ báo trùng GUID của thư mục Shaders.",
        "Material vẫn chạy đúng. Để tránh, hãy chọn thẳng thư mục project Unity khi export, hoặc dùng Dự án DaskToon.",
        "",
    ]
    return "\n".join(head + report.lines()) + "\n"


def write_text(report):
    text = bpy.data.texts.get(REPORT_TEXT) or bpy.data.texts.new(REPORT_TEXT)
    text.clear()
    text.write("\n".join(report.lines()) + "\n")
    return text


def show_popup(report):
    if bpy.app.background:
        return
    lines = report.lines()

    def draw(self, _context):
        for line in lines[:POPUP_LINES]:
            self.layout.label(text=line)
        if len(lines) > POPUP_LINES:
            self.layout.label(text="… xem đầy đủ trong Text '%s'" % REPORT_TEXT)

    bpy.context.window_manager.popup_menu(draw, title="DaskToon Engine Export", icon='INFO')
```

File: `scripts/modules/dasktoon_export/__init__.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon Engine Export: model, materials and shaders for game engines.
Design: docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md"""

from dataclasses import dataclass

from . import report  # noqa: F401  (re-exported for callers: dasktoon_export.report)

_FORBIDDEN = '<>:"/\\|?*'


@dataclass
class ExportOptions:
    model_format: str = 'FBX'       # 'FBX' or 'NONE'
    include_animation: bool = True
    export_materials: bool = True
    bake_size: int = 1024
    bake_samples: int = 16


def safe_name(name):
    """A file name that Windows and Unity accept, as close to the material name as possible."""
    cleaned = "".join("_" if c in _FORBIDDEN or ord(c) < 32 else c for c in name).strip().rstrip(".")
    return cleaned or "Material"


def _tex_label(prop):
    label = prop[len("_DT_"):] if prop.startswith("_DT_") else prop.lstrip("_")
    return label[:-3] if label.endswith("Map") else label


def _materials(objects):
    """{material: [mesh objects using it]} in slot order; empty slots and outline companions are left out."""
    from . import graph
    found = {}
    for obj in objects:
        if obj.type != 'MESH':
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None or graph.is_outline_companion(mat):
                continue
            users = found.setdefault(mat, [])
            if obj not in users:
                users.append(obj)
    return found


def _drop_texture(spec, prop, src):
    """The texture could not be written: Unity falls back to the input's own value."""
    spec.textures.pop(prop, None)
    if src.kind == 'NORMAL':
        spec.keywords.discard("_DT_NORMALMAP")
        spec.floats["_DT_UseNormalMap"] = 0.0
        return
    spec.floats[src.flag_prop] = 0.0
    if isinstance(src.value, tuple):
        spec.colors[src.value_prop] = src.value
    else:
        spec.floats[src.value_prop] = src.value


class _Writer:
    """Writes one model's materials and textures under target.root (spec 4 layout)."""

    def __init__(self, target, options, rep):
        from . import assets, unity_yaml
        self.target, self.options, self.rep = target, options, rep
        self.assets, self.yaml = assets, unity_yaml
        self.written = {}   # (image pointer, kind) -> texture GUID, so a shared image is written once
        self.stems = set()

    def guid(self, relpath):
        return self.yaml.guid_for(self.target.name, relpath)

    def folder(self, relpath):
        self.assets.ensure_folder(self.target.root, relpath, self.guid(relpath))

    def unique_stem(self, mat):
        stem = base = safe_name(mat.name)
        index = 2
        while stem.lower() in self.stems:
            stem = "%s_%d" % (base, index)
            index += 1
        self.stems.add(stem.lower())
        return stem

    def texture(self, spec, stem, prop, src, users):
        from . import bake, textures
        name = self.target.name
        if src.kind in ('IMAGE', 'NORMAL'):
            key = (src.image.as_pointer(), src.kind, src.color)
            if key in self.written:
                return self.written[key]
            found = textures.image_file(src.image)
            if found is not None:
                ext, data = found
                kind = 'NORMAL' if src.kind == 'NORMAL' else ('COLOR' if src.color and ext not in (".exr", ".hdr")
                                                              else 'DATA')
                rel = "%s/Textures/%s_%s%s" % (name, stem, _tex_label(prop), ext)
                guid = self.guid(rel)
                meta = self.yaml.texture_meta(guid, kind, tuple(src.image.size))
                if not self.assets.write_asset(self.target.root, rel, guid, meta, self.rep.warnings, data=data):
                    return None
                self.written[key] = guid
                return guid
            if src.kind == 'NORMAL':
                self.rep.warnings.append("%s: không đọc được ảnh normal map %s; bỏ normal map"
                                         % (spec.material.name, src.image.name))
                return None
        size = bake.branch_size(src.tree_owner, src.node, src.socket, self.options.bake_size)
        try:
            pixels = bake.bake_input(users[0], spec.material, src, size, self.options.bake_samples)
        except Exception as ex:  # A failed bake must not stop the export; the input keeps its value.
            self.rep.warnings.append("%s › %s: bake lỗi (%s); dùng giá trị đang đặt" % (spec.material.name, src.socket, ex))
            return None
        if textures.needs_float(pixels):
            ext, data, kind = ".exr", textures.exr_bytes(pixels, size, size), 'DATA'
        else:
            ext, kind = ".png", ('COLOR' if src.color else 'DATA')
            data = textures.float_to_png(pixels, size, size, src.color)
        rel = "%s/Textures/%s_%s%s" % (name, stem, _tex_label(prop), ext)
        guid = self.guid(rel)
        if not self.assets.write_asset(self.target.root, rel, guid, self.yaml.texture_meta(guid, kind, (size, size)),
                                       self.rep.warnings, data=data):
            return None
        self.rep.baked.append("%s › %s" % (spec.material.name, src.socket))
        if len(users) > 1:
            self.rep.warnings.append("%s › %s: bake trên mesh của %s, các mesh khác dùng chung texture này"
                                     % (spec.material.name, src.socket, users[0].name))
        return guid

    def material(self, spec, users):
        from . import shaders_install, textures
        name = self.target.name
        stem = self.unique_stem(spec.material)
        tex_guids = {}
        if spec.textures:
            self.folder(name + "/Textures")
        for prop, src in sorted(spec.textures.items()):
            guid = self.texture(spec, stem, prop, src, users)
            if guid is None:
                _drop_texture(spec, prop, src)
            else:
                tex_guids[prop] = guid
        if spec.ramp is not None:
            self.folder(name + "/Textures")
            rel = "%s/Textures/%s_Ramp.png" % (name, stem)
            guid = self.guid(rel)
            point = spec.floats.get("_DT_RampConstant", 0.0) > 0.5
            meta = self.yaml.texture_meta(guid, 'RAMP', (textures.RAMP_WIDTH, 1), point_filter=point)
            if self.assets.write_asset(self.target.root, rel, guid, meta, self.rep.warnings,
                                       data=textures.ramp_png(spec.ramp)):
                tex_guids["_DT_RampMap"] = guid
        self.folder(name + "/Materials")
        rel = "%s/Materials/%s.mat" % (name, stem)
        guid = self.guid(rel)
        text = self.yaml.material_yaml(stem, shaders_install.shader_guid(spec.shader), spec.keywords, spec.queue,
                                       spec.render_type, spec.disabled_passes, spec.floats, spec.colors, tex_guids)
        self.rep.warnings += spec.warnings
        if not self.assets.write_asset(self.target.root, rel, guid, self.yaml.material_meta(guid), self.rep.warnings,
                                       data=text.encode("utf-8")):
            return None
        self.rep.materials.append(spec.material.name)
        return guid


def export_model(context, target, objects, options):
    """Write `objects` (FBX), their DaskToon materials and the shaders to `target` (spec 3-5). Returns a Report."""
    from . import assets, graph, model_fbx, shaders_install, targets, unity_yaml
    if target.engine not in targets.SUPPORTED_ENGINES:
        raise ValueError("Engine %s chưa được hỗ trợ" % target.engine)
    rep = report.Report(mode=target.mode, root=target.root, name=target.name)
    meshes = [o for o in objects if o.type == 'MESH']
    rep.outline_meshes, errors = model_fbx.prepare_outline_data(meshes)
    rep.warnings += errors
    rep.modifier_notes = model_fbx.modifier_notes(meshes)
    shaders_install.ensure_root(target)
    writer = _Writer(target, options, rep)
    writer.folder(target.name)
    mat_guids = {}
    if options.export_materials:
        rep.shaders = 'INSTALLED' if shaders_install.install_shaders(target, rep.warnings) else 'UP_TO_DATE'
        for mat, users in _materials(meshes).items():
            mesh_data = list(dict.fromkeys(o.data for o in users))
            spec, reason = graph.analyze_material(mat, mesh_data)
            if spec is None:
                rep.skipped.append((mat.name, reason))
                continue
            guid = writer.material(spec, users)
            if guid is not None:
                mat_guids[mat.name] = guid
    if options.model_format == 'FBX':
        model_dir = target.name + "/Model"
        writer.folder(model_dir)
        rel = "%s/%s.fbx" % (model_dir, safe_name(target.name))
        guid = writer.guid(rel)
        meta = unity_yaml.model_meta(guid, mat_guids, options.include_animation)
        if assets.write_asset(target.root, rel, guid, meta, rep.warnings,
                              writer=lambda path: model_fbx.write_fbx(context, objects, path, options.include_animation)):
            rep.model = rel
    rep.light_hint = report.light_hint(context.scene)
    rep.ambient_hint = report.ambient_hint(context.scene)
    if target.mode == 'FOLDER':
        guid = writer.guid("README.txt")
        assets.write_asset(target.root, "README.txt", guid, unity_yaml.text_meta(guid), rep.warnings,
                           data=report.readme_text(rep).encode("utf-8"))
    report.write_text(rep)
    return rep
```

- [ ] **Step 4: Chạy test bố cục, phải PASS**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_export_layout_test.py 2>&1 | tail -8`
Expected: `Ran 8 tests ... OK`.

- [ ] **Step 5: Viết kiểm tra FBX trong Unity**

File: `tests/unity/Editor/DaskToonModelTests.cs`
```csharp
// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Checks an exported FBX after Unity imported it: material remap, blend shapes, axes, and that DT_OutlineN decodes
// with Unity's own tangent frame into the smoothed normal DaskToon computed (spec 8, Unity step 3).

using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

[Serializable]
public class DtExpectedNormal
{
    public float[] p;
    public float[] n;
}

[Serializable]
public class DtModelArgs
{
    public string model;
    public string mesh;
    public int outlineUV;
    public DtExpectedNormal[] normals;
}

public static class DaskToonModelTests
{
    static Vector3 V(float[] a) => new Vector3(a[0], a[1], a[2]);

    static DtExpectedNormal Nearest(DtExpectedNormal[] list, Vector3 p)
    {
        DtExpectedNormal best = null;
        var bestDistance = 1e-6f;
        foreach (var e in list)
        {
            var d = (V(e.p) - p).sqrMagnitude;
            if (d < bestDistance)
            {
                bestDistance = d;
                best = e;
            }
        }
        return best;
    }

    static Vector3 OctDecode(Vector2 e)
    {
        var n = new Vector3(e.x, e.y, 1f - Mathf.Abs(e.x) - Mathf.Abs(e.y));
        var t = Mathf.Max(-n.z, 0f);
        n.x += n.x >= 0f ? -t : t;
        n.y += n.y >= 0f ? -t : t;
        return n.normalized;
    }

    public static void CheckModel() => DaskToonTests.Run(() =>
    {
        var args = JsonUtility.FromJson<DtModelArgs>(File.ReadAllText(DaskToonTests.ArgsPath));
        AssetDatabase.Refresh();
        var result = new Dictionary<string, object>();
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(args.model);
        result["imported"] = prefab != null;
        if (prefab == null) return result;
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        var materials = new Dictionary<string, object>();
        foreach (var r in go.GetComponentsInChildren<Renderer>(true))
        foreach (var m in r.sharedMaterials)
        {
            if (m != null) materials[m.name] = AssetDatabase.GetAssetPath(m);
        }
        result["materials"] = materials;

        Mesh mesh = null;
        Transform owner = null;
        foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>(true))
        {
            if (smr.name == args.mesh) { mesh = smr.sharedMesh; owner = smr.transform; }
        }
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>(true))
        {
            if (mesh == null && mf.name == args.mesh) { mesh = mf.sharedMesh; owner = mf.transform; }
        }
        result["meshFound"] = mesh != null;
        if (mesh == null) return result;
        result["blendShapes"] = mesh.blendShapeCount;
        var channels = new List<object>();
        for (var i = 0; i < 8; i++)
        {
            if (mesh.HasVertexAttribute(VertexAttribute.TexCoord0 + i)) channels.Add(i);
        }
        result["uvChannels"] = channels;

        var toWorld = owner.localToWorldMatrix;
        var mirror = toWorld.determinant < 0f ? -1f : 1f;
        var vertices = mesh.vertices;
        var normals = mesh.normals;
        var tangents = mesh.tangents;
        var uvs = new List<Vector2>();
        mesh.GetUVs(args.outlineUV, uvs);
        var maxAngle = 0f;
        var matched = 0;
        var top = float.MinValue;
        for (var i = 0; i < vertices.Length; i++)
        {
            var p = toWorld.MultiplyPoint3x4(vertices[i]);
            top = Mathf.Max(top, p.y);
            var expected = Nearest(args.normals, p);
            if (expected == null || uvs.Count != vertices.Length || tangents.Length != vertices.Length) continue;
            var n = toWorld.MultiplyVector(normals[i]).normalized;
            var t = toWorld.MultiplyVector(new Vector3(tangents[i].x, tangents[i].y, tangents[i].z)).normalized;
            var b = Vector3.Cross(n, t) * tangents[i].w * mirror;
            var e = OctDecode(uvs[i]);
            var decoded = (t * e.x + b * e.y + n * e.z).normalized;
            maxAngle = Mathf.Max(maxAngle, Vector3.Angle(decoded, V(expected.n)));
            matched++;
        }
        result["matched"] = matched;
        result["vertices"] = vertices.Length;
        result["maxNormalAngle"] = maxAngle;
        result["top"] = top;
        return result;
    });
}
```

File: `tests/python/dasktoon_unity_model_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unity imports the exported FBX with the exported materials, blend shapes, Blender axes converted, and
DT_OutlineN decoding to DaskToon's smoothed normals in Unity's tangent frame (spec 8, Unity steps 2 and 3)."""

import os
import sys
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from bl_ui import dasktoon_outline_gamedata as gamedata  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import targets  # noqa: E402


def to_unity(v):
    return [-v[0], v[2], -v[1]]


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnityModelTest(unittest.TestCase):
    def test_fbx_import_materials_shapes_axes_and_outline_normals(self):
        root = harness.ensure_project()
        tu.reset_scene()
        outline.reset_cache()
        body = tu.add_sphere(segments=24, rings=12)
        body.name = "Body"
        body.data.uv_layers.new(name="Second")
        mat, node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        node.use_outline = True
        tu.assign(body, mat)
        body.shape_key_add(name="Basis")
        body.shape_key_add(name="Smile").data[0].co.z += 0.1
        outline.sync_all(bpy.context.scene)
        target = targets.make_target(root, "DTModel")
        options = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [body], options)
        self.assertEqual(rep.materials, ["Skin"])
        mesh = body.data
        smooth = gamedata.smoothed_vertex_normals(mesh)
        normals = [{"p": to_unity(v.co), "n": to_unity(s)} for v, s in zip(mesh.vertices, smooth)]
        uv_index = mesh.uv_layers.find("DT_OutlineN")
        self.assertEqual(uv_index, 2)
        result = harness.run_method("DaskToonModelTests.CheckModel", {
            "model": "Assets/DaskToon/DTModel/Model/DTModel.fbx", "mesh": "Body",
            "outlineUV": uv_index, "normals": normals})
        self.assertTrue(result["ok"], result.get("error"))
        self.assertTrue(result["imported"])
        self.assertEqual(result["materials"], {"Skin": "Assets/DaskToon/DTModel/Materials/Skin.mat"})
        self.assertTrue(result["meshFound"])
        self.assertGreaterEqual(result["blendShapes"], 1)
        self.assertIn(uv_index, result["uvChannels"])
        self.assertGreater(result["matched"], 0.9 * result["vertices"])
        self.assertLess(result["maxNormalAngle"], 2.0)
        self.assertAlmostEqual(result["top"], max(v.co.z for v in mesh.vertices), places=3)


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 6: Chạy test Unity, phải PASS**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_unity_model_test.py 2>&1 | tail -20`
Expected: `Ran 1 test ... OK`. Nếu `maxNormalAngle` lớn (MikkTSpace của Unity khác Blender, spec mục 9): chuyển FBX sang
`use_tspace=True` và `.meta` sang `tangentImportMode: 0` (Import) để Unity dùng đúng tangent của Blender, ghi `Ruling:`,
chạy lại cả test FBX headless và test này. Nếu `materials` sai hoặc enum của ModelImporter không được nhận: so `.meta` mà Unity
viết lại trong project tạm với `unity_yaml.model_meta`, sửa trường, ghi `Ruling:`.

- [ ] **Step 7: Commit**

```bash
git add scripts/modules/dasktoon_export/__init__.py scripts/modules/dasktoon_export/report.py tests/unity/Editor/DaskToonModelTests.cs tests/python/dasktoon_export_layout_test.py tests/python/dasktoon_unity_model_test.py
git commit -m "feat: export DaskToon models, materials and shaders as a Unity-ready folder or into a Unity project"
```

### Task 9: Hộp thoại *File › Export › Engine Export…*

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_engine_export.py`
- Modify: `scripts/startup/bl_ui/__init__.py` (thêm `"dasktoon_engine_export",` vào `_modules`, ngay sau `"dasktoon_upgrade",`)
- Test: `tests/python/dasktoon_engine_export_ui_test.py`

**Interfaces:**
- Consumes: `dasktoon_export.{ExportOptions, export_model}`, `targets.{ENGINES, SUPPORTED_ENGINES, make_target, blend_name, remember_target, remembered_target}`,
  `model_fbx.export_objects`, `report.show_popup`.
- Produces: operator `export_scene.dasktoon_engine` (thuộc tính `directory`, `engine`, `model_format`, `use_selection`,
  `include_animation`, `export_materials`, `bake_size`, `bake_samples`), `default_directory(context) -> (directory, engine)`
  (Task 12 thêm ưu tiên cho dự án), `menu_func_export`.

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_engine_export_ui_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""File › Export › Engine Export… operator (spec 3, 5). The dialog itself is checked by hand in DaskToon."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_engine_export as ui  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from dasktoon_export import targets  # noqa: E402


def character():
    tu.reset_scene()
    outline.reset_cache()
    body = tu.add_sphere(segments=12, rings=6)
    mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
    tu.assign(body, mat)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj == body)
    return body


class EngineExportOperatorTest(unittest.TestCase):
    def test_exports_and_remembers_the_target(self):
        character()
        out = tempfile.mkdtemp(prefix="dt_ui_")
        self.assertEqual(bpy.ops.export_scene.dasktoon_engine(directory=out, bake_size=64, include_animation=False),
                         {'FINISHED'})
        root = os.path.join(out, "Untitled_Unity")
        self.assertTrue(os.path.isfile(os.path.join(root, "Untitled", "Model", "Untitled.fbx")))
        self.assertTrue(os.path.isfile(os.path.join(root, "Untitled", "Materials", "Skin.mat")))
        self.assertEqual(targets.remembered_target(bpy.context.scene), (out, 'UNITY_URP'))
        self.assertEqual(ui.default_directory(bpy.context), (out, 'UNITY_URP'))

    def test_coming_soon_engine_is_refused(self):
        character()
        with self.assertRaises(RuntimeError):
            bpy.ops.export_scene.dasktoon_engine(directory=tempfile.mkdtemp(prefix="dt_ui_"), engine='GODOT_4')

    def test_nothing_selected_is_refused(self):
        character()
        for obj in bpy.context.view_layer.objects:
            obj.select_set(False)
        with self.assertRaises(RuntimeError):
            bpy.ops.export_scene.dasktoon_engine(directory=tempfile.mkdtemp(prefix="dt_ui_"), use_selection=True)

    def test_menu_entry_is_registered(self):
        self.assertTrue(hasattr(bpy.ops.export_scene, "dasktoon_engine"))
        self.assertIn(ui.menu_func_export, bpy.types.TOPBAR_MT_file_export._dyn_ui_initialize())


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, phải FAIL**

Run: `cp -r scripts/startup/. "$BUILD/bin/Release/5.2/scripts/startup/"; cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_engine_export_ui_test.py 2>&1 | tail -5`
Expected: `ImportError: cannot import name 'dasktoon_engine_export' from 'bl_ui'`.

- [ ] **Step 3: Viết operator và đăng ký module**

File: `scripts/startup/bl_ui/dasktoon_engine_export.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""File › Export › Engine Export…: export the model, its DaskToon materials and the shaders for a game engine
(docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md, sections 3 and 5)."""

import os

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import Operator

from dasktoon_export import targets


def default_directory(context):
    """(directory, engine) the dialog opens with: the target remembered in this .blend file, else its folder."""
    remembered = targets.remembered_target(context.scene)
    if remembered and os.path.isdir(remembered[0]):
        return remembered
    if bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath), 'UNITY_URP'
    return "", 'UNITY_URP'


class EXPORT_SCENE_OT_dasktoon_engine(Operator):
    """Export the model, its DaskToon materials and the shaders for a game engine"""
    bl_idname = "export_scene.dasktoon_engine"
    bl_label = "Engine Export"
    bl_options = {'REGISTER'}

    directory: StringProperty(name="Thư mục", subtype='DIR_PATH')
    filter_folder: BoolProperty(default=True, options={'HIDDEN'})
    engine: EnumProperty(name="Engine", items=targets.ENGINES, default='UNITY_URP')
    model_format: EnumProperty(
        name="Model",
        items=(('FBX', "FBX", "Xuất model dạng FBX"), ('NONE', "Không xuất model", "Chỉ xuất material và shader")),
        default='FBX')
    use_selection: BoolProperty(name="Chỉ object đang chọn", default=True)
    include_animation: BoolProperty(name="Kèm animation", default=True)
    export_materials: BoolProperty(name="Xuất material và shader", default=True)
    bake_size: IntProperty(name="Bake", default=1024, min=64, max=8192, subtype='PIXEL')
    bake_samples: IntProperty(name="Sample", default=16, min=1, max=4096)

    def invoke(self, context, _event):
        directory, engine = default_directory(context)
        if directory:
            self.directory = directory
        self.engine = engine
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, _context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "engine")
        layout.prop(self, "model_format")
        layout.prop(self, "use_selection")
        row = layout.row()
        row.enabled = self.model_format == 'FBX'
        row.prop(self, "include_animation")
        layout.prop(self, "export_materials")
        col = layout.column(align=True)
        col.enabled = self.export_materials
        col.prop(self, "bake_size")
        col.prop(self, "bake_samples")
        if self.directory:
            target = targets.make_target(self.directory, targets.blend_name(bpy.data.filepath), self.engine)
            box = layout.box()
            if target.mode == 'PROJECT':
                box.label(text="Ghi thẳng vào project Unity", icon='CHECKMARK')
                box.label(text=os.path.basename(target.project) + "/Assets/DaskToon")
            else:
                box.label(text="Tạo thư mục " + os.path.basename(target.root), icon='FILE_FOLDER')

    def execute(self, context):
        import dasktoon_export
        from dasktoon_export import model_fbx, report
        if self.engine not in targets.SUPPORTED_ENGINES:
            self.report({'ERROR'}, "Engine này sắp có; hiện chỉ hỗ trợ Unity 6 (URP)")
            return {'CANCELLED'}
        if not self.directory:
            self.report({'ERROR'}, "Chưa chọn thư mục đích")
            return {'CANCELLED'}
        objects = model_fbx.export_objects(context, self.use_selection)
        if not objects:
            self.report({'ERROR'}, "Không có object nào để export (chưa chọn object?)")
            return {'CANCELLED'}
        directory = bpy.path.abspath(self.directory)
        target = targets.make_target(directory, targets.blend_name(bpy.data.filepath), self.engine)
        options = dasktoon_export.ExportOptions(
            model_format=self.model_format, include_animation=self.include_animation,
            export_materials=self.export_materials, bake_size=self.bake_size, bake_samples=self.bake_samples)
        rep = dasktoon_export.export_model(context, target, objects, options)
        targets.remember_target(context.scene, self.directory, self.engine)
        report.show_popup(rep)
        self.report({'WARNING'} if rep.warnings else {'INFO'}, rep.summary())
        return {'FINISHED'}


def menu_func_export(self, _context):
    self.layout.operator(EXPORT_SCENE_OT_dasktoon_engine.bl_idname, text="Engine Export…")


classes = (EXPORT_SCENE_OT_dasktoon_engine,)


# bl_ui registers `classes` itself; register()/unregister() only manage the menu entry.
def register():
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
```

Sửa `scripts/startup/bl_ui/__init__.py`: trong danh sách `_modules`, thêm dòng `"dasktoon_engine_export",` ngay sau
`"dasktoon_upgrade",`.

- [ ] **Step 4: Chạy test, phải PASS; chạy lại test cũ của bl_ui**

Run: `cp -r scripts/startup/. "$BUILD/bin/Release/5.2/scripts/startup/"; cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_engine_export_ui_test.py 2>&1 | tail -5; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_outline_sync_test.py 2>&1 | tail -3`
Expected: `Ran 4 tests ... OK` và `Ran 12 tests ... OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/startup/bl_ui/dasktoon_engine_export.py scripts/startup/bl_ui/__init__.py tests/python/dasktoon_engine_export_ui_test.py
git commit -m "feat: add File > Export > Engine Export for DaskToon characters"
```

---

### Task 10: So sánh render DaskToon và Unity (spec 8, Unity bước 4)

**Files:**
- Create: `tests/unity/Editor/DaskToonRenderTests.cs`
- Create: `tests/python/dasktoon_unity_render_test.py`
- Create (kết quả): `docs/superpowers/reports/2026-10-03-unity-compare.png` (Git LFS, như ảnh duyệt của Dự án 1)

**Interfaces:**
- Consumes: `dasktoon_export.export_model`, `harness.{ensure_project, run_method}`, `bl_ui.dasktoon_shading_styles.{BUILTIN_STYLES, apply_style}`,
  `textures.png_bytes`.
- Produces (C#): `DaskToonRenderTests.RenderCases` (args: `model`, `cases: [{name, obj, camPos}]`, `resolution`, `orthoSize`,
  `camForward`, `camUp`, `lightDir`, `lightIntensity`, `lightColor`, `ambient`, `outDir`) → `{outputs: {case: exr path}}`.

Cảnh giống nhau ở hai bên: quả cầu bán kính 0.5 (48×24, smooth) cho mỗi trường hợp, đặt cách nhau 3 m theo trục X của
Blender; camera orthographic nhìn theo +Y (Blender), `ortho_scale` 1.4; Sun 3.0, màu (1, 0.9, 0.8), xoay (50°, 0°, 30°),
không đổ bóng; World (0.05, 0.06, 0.08). Unity: Directional = 3 ÷ π, ambient phẳng bằng màu World, không có skybox và phản xạ
môi trường. So sánh trên lưới 9×9 điểm trong đĩa của quả cầu, bỏ các điểm nằm ở ranh giới (chênh lệch với điểm kề > 0.05 trong
ảnh DaskToon), tính trên giá trị sRGB.

- [ ] **Step 1: Viết script render của Unity**

File: `tests/unity/Editor/DaskToonRenderTests.cs`
```csharp
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
        return new Dictionary<string, object> { { "outputs", outputs } };
    });
}
```

- [ ] **Step 2: Viết test so sánh**

File: `tests/python/dasktoon_unity_render_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon (EEVEE) vs Unity URP renders of the same spheres (spec 8): cel and diffuse within 0.03 on sRGB values,
specular and AO reported only. Writes a side-by-side sheet for the user to review."""

import json
import math
import os
import sys
import unittest

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_unity_harness as harness  # noqa: E402
from bl_ui import dasktoon_outline as outline  # noqa: E402
from bl_ui import dasktoon_shading_styles as styles  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import targets, textures  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHEET = os.path.join(REPO, "docs", "superpowers", "reports", "2026-10-03-unity-compare.png")
RES = 128
SPACING = 3.0
ORTHO_SCALE = 1.4
SUN_STRENGTH = 3.0
SUN_COLOR = (1.0, 0.9, 0.8)
SUN_ROTATION = (math.radians(50.0), 0.0, math.radians(30.0))
WORLD = (0.05, 0.06, 0.08)
TOLERANCE = 0.03
EDGE = 0.05
MODEL_NAME = "DTCompare"


def to_unity(v):
    return [-v[0], v[2], -v[1]]


def srgb(x):
    x = np.clip(x, 0.0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def bsdf(name, **props):
    mat, node = tu.node_material(name, 'ShaderNodeAnimeCharacter')
    for key, value in props.items():
        setattr(node, key, value)
    return mat, node


def with_style(mat_node, style):
    mat, node = mat_node
    node.shading_mode = 'RAMP'
    styles.apply_style(node.shading_ramp, styles.BUILTIN_STYLES[style])
    return mat


def anime_cel(name, spec_size=0.0, style=None):
    mat, node = tu.node_material(name, 'ShaderNodeAnimeCel')
    node.inputs["Specular Size"].default_value = spec_size
    if style:
        with_style((mat, node), style)
    return mat


def ambient_world():
    mat, node = bsdf("bsdf_ambient_world", use_ambient=True, ambient_mode='HUE_SAT')
    node.inputs["Use Custom Color"].default_value = False
    node.inputs["Ambient Factor"].default_value = 0.6
    return mat


def hair():
    mat = tu.new_material("hair")
    nt = mat.node_tree
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emission = nt.nodes.new('ShaderNodeEmission')
    cel = nt.nodes.new('ShaderNodeAnimeCel')
    cel.inputs["Specular Size"].default_value = 0.0
    ring = nt.nodes.new('ShaderNodeAnimeAngelRing')
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'ADD'
    sockets = {s.identifier: s for s in mix.inputs}
    nt.links.new(cel.outputs["Color"], sockets["A_Color"])
    nt.links.new(ring.outputs["Color"], sockets["B_Color"])
    nt.links.new(ring.outputs["Fac"], sockets["Factor_Float"])
    nt.links.new(next(s for s in mix.outputs if s.identifier == "Result_Color"), emission.inputs["Color"])
    nt.links.new(emission.outputs["Emission"], out.inputs["Surface"])
    return mat


def eye():
    mat, node = tu.node_material("eye", 'ShaderNodeAnimeEye')
    coords = mat.node_tree.nodes.new('ShaderNodeTexCoord')
    mat.node_tree.links.new(coords.outputs["UV"], node.inputs["UV Vector"])
    return mat


def dask_cel(name, style=None):
    mat, node = tu.node_material(name, 'ShaderNodeDaskCel')
    if style:
        with_style((mat, node), style)
    return mat


# (case, material builder, graded)
CASES = [
    ("bsdf_simple", lambda: bsdf("bsdf_simple")[0], True),
    ("bsdf_ambient_custom", lambda: bsdf("bsdf_ambient_custom", use_ambient=True)[0], True),
    ("bsdf_ambient_world", ambient_world, True),
    ("bsdf_light_overlay", lambda: bsdf("bsdf_light_overlay", use_light=True)[0], True),
    ("bsdf_light_multiply", lambda: bsdf("bsdf_light_multiply", use_light=True, light_blend_mode='MULTIPLY')[0], True),
    ("bsdf_rim", lambda: bsdf("bsdf_rim", use_rim=True)[0], True),
    ("bsdf_grade", lambda: bsdf("bsdf_grade", use_grade=True)[0], True),
    ("bsdf_ramp_3tone", lambda: with_style(bsdf("bsdf_ramp_3tone"), "Anime 3 tông"), True),
    ("bsdf_ramp_soft", lambda: with_style(bsdf("bsdf_ramp_soft"), "Mềm như vẽ"), True),
    ("bsdf_ao", lambda: bsdf("bsdf_ao", use_ao=True)[0], False),
    ("cel_simple", lambda: anime_cel("cel_simple"), True),
    ("cel_ramp", lambda: anime_cel("cel_ramp", style="Anime 2 tông"), True),
    ("cel_spec", lambda: anime_cel("cel_spec", spec_size=0.08), False),
    ("hair", hair, True),
    ("eye", eye, True),
    ("daskcel_simple", lambda: dask_cel("daskcel_simple"), True),
    ("daskcel_manga", lambda: dask_cel("daskcel_manga", style="Manga"), True),
]


def build_scene():
    tu.reset_scene(RES)
    outline.reset_cache()
    scene = bpy.context.scene
    scene.eevee.taa_render_samples = 16
    tu.set_world_color(WORLD)
    sun = tu.add_sun(SUN_STRENGTH, SUN_ROTATION, SUN_COLOR)
    sun.data.use_shadow = False
    cam = scene.camera
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = ORTHO_SCALE
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    spheres = []
    for i, (name, builder, _graded) in enumerate(CASES):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, segments=48, ring_count=24, location=(i * SPACING, 0.0, 0.0))
        obj = bpy.context.active_object
        obj.data.shade_smooth()
        obj.name = "Case_" + name
        tu.assign(obj, builder())
        spheres.append(obj)
    return scene, sun, cam, spheres


def render_blender(scene, cam, spheres):
    images = {}
    for i, obj in enumerate(spheres):
        for other in spheres:
            other.hide_render = other is not obj
        cam.location = (i * SPACING, -5.0, 0.0)
        pixels, size = tu.render_pixels("blender_" + obj.name)
        images[obj.name[len("Case_"):]] = np.array(pixels).reshape(size[1], size[0], 4)
    for obj in spheres:
        obj.hide_render = False
    return images


def load_exr(path):
    img = bpy.data.images.load(path, check_existing=False)
    pixels = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
    bpy.data.images.remove(img)
    return pixels


def sample_points():
    centre = RES / 2.0
    radius = 0.5 / ORTHO_SCALE * RES * 0.85
    points = []
    for gy in np.linspace(0.2, 0.8, 9):
        for gx in np.linspace(0.2, 0.8, 9):
            x, y = int(gx * RES), int(gy * RES)
            if (x + 0.5 - centre) ** 2 + (y + 0.5 - centre) ** 2 < radius ** 2:
                points.append((x, y))
    return points


def compare(blender, unity):
    b, u = srgb(blender[..., :3]), srgb(unity[..., :3])
    worst, used, skipped = 0.0, 0, 0
    for x, y in sample_points():
        here = b[y, x]
        neighbours = [b[y + dy, x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        if max(np.abs(here - n).max() for n in neighbours) > EDGE:
            skipped += 1
            continue
        worst = max(worst, float(np.abs(here - u[y, x]).max()))
        used += 1
    return worst, used, skipped


def write_sheet(rows):
    """One row per case: DaskToon | Unity | |difference| x 5, top to bottom in CASES order."""
    height = RES * len(rows)
    sheet = np.zeros((height, RES * 3, 4))
    for i, (blender, unity) in enumerate(rows):
        y0 = height - (i + 1) * RES
        sheet[y0:y0 + RES, 0:RES] = blender
        sheet[y0:y0 + RES, RES:2 * RES] = unity
        sheet[y0:y0 + RES, 2 * RES:3 * RES, :3] = np.abs(srgb(blender[..., :3]) - srgb(unity[..., :3])) * 5.0
        sheet[y0:y0 + RES, 2 * RES:3 * RES, 3] = 1.0
    sheet[..., :3] = np.where(np.arange(3 * RES)[None, :, None] < 2 * RES, srgb(sheet[..., :3]), sheet[..., :3])
    data = (np.clip(sheet, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).tobytes()
    with open(SHEET, "wb") as f:
        f.write(textures.png_bytes(RES * 3, height, data))


@unittest.skipUnless(harness.unity_exe(), harness.SKIP_REASON)
class UnityRenderTest(unittest.TestCase):
    def test_unity_matches_dasktoon(self):
        root = harness.ensure_project()
        scene, sun, cam, spheres = build_scene()
        blender = render_blender(scene, cam, spheres)
        target = targets.make_target(root, MODEL_NAME)
        options = dasktoon_export.ExportOptions(include_animation=False, bake_size=64, bake_samples=4)
        rep = dasktoon_export.export_model(bpy.context, target, spheres, options)
        self.assertEqual(len(rep.materials), len(CASES), rep.lines())
        light_dir = sun.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
        out_dir = os.path.join(tu.OUT_DIR, "unity_renders")
        args = {
            "model": "Assets/DaskToon/%s/Model/%s.fbx" % (MODEL_NAME, MODEL_NAME),
            "cases": [{"name": name, "obj": "Case_" + name, "camPos": to_unity((i * SPACING, -5.0, 0.0))}
                      for i, (name, _builder, _graded) in enumerate(CASES)],
            "resolution": RES,
            "orthoSize": ORTHO_SCALE / 2.0,
            "camForward": to_unity((0.0, 1.0, 0.0)),
            "camUp": to_unity((0.0, 0.0, 1.0)),
            "lightDir": to_unity(light_dir.normalized()),
            "lightIntensity": SUN_STRENGTH / math.pi,
            "lightColor": list(SUN_COLOR),
            "ambient": list(WORLD),
            "outDir": out_dir,
        }
        result = harness.run_method("DaskToonRenderTests.RenderCases", args)
        self.assertTrue(result["ok"], result.get("error"))
        table, failures, rows = {}, [], []
        for name, _builder, graded in CASES:
            unity = load_exr(result["outputs"][name])
            worst, used, skipped = compare(blender[name], unity)
            table[name] = {"max_diff": round(worst, 4), "points": used, "edge_points": skipped, "graded": graded}
            rows.append((blender[name], unity))
            if graded and (worst > TOLERANCE or used == 0):
                failures.append(name)
        write_sheet(rows)
        with open(os.path.join(tu.OUT_DIR, "unity_compare.json"), "w", encoding="utf-8") as f:
            json.dump(table, f, indent=2)
        print(json.dumps(table, indent=2))
        self.assertEqual(failures, [], json.dumps(table, indent=2))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 3: Chạy test, đọc bảng sai số, sửa tới khi các trường hợp được chấm đều đạt**

Run: `cp -r scripts/startup/. "$BUILD/bin/Release/5.2/scripts/startup/"; cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; DASKTOON_TEST_OUT="$TEMP/dt_unity_compare" "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_unity_render_test.py 2>&1 | tail -60`
Expected: `Ran 1 test ... OK`, bảng in ra có `max_diff ≤ 0.03` cho mọi trường hợp `graded`. Mở `docs/superpowers/reports/2026-10-03-unity-compare.png`
để kiểm tra bằng mắt (hướng ảnh, vị trí quả cầu). Khi lệch: dùng superpowers:systematic-debugging, so trực tiếp `diffuse` của
hai bên (đơn vị đèn, SH, chuyển màu), sửa shader hoặc exporter; mỗi sai khác không thể tránh (ví dụ đèn Sun có góc trong EEVEE)
ghi `Ruling:` kèm con số.

- [ ] **Step 4: Commit**

```bash
git add tests/unity/Editor/DaskToonRenderTests.cs tests/python/dasktoon_unity_render_test.py docs/superpowers/reports/2026-10-03-unity-compare.png
git commit -m "test: compare DaskToon and Unity URP renders of every node, preset and module"
```

---

### Task 11: Thư viện Dự án DaskToon (`dasktoon_project/project.py`) — giai đoạn B

**Files:**
- Create: `scripts/modules/dasktoon_project/__init__.py`
- Create: `scripts/modules/dasktoon_project/project.py`
- Test: `tests/python/dasktoon_project_test.py`

**Interfaces:**
- Consumes: `targets.{ExportTarget, is_unity_project, SUPPORTED_ENGINES}`, `shaders_install.install_shaders`, `dasktoon_export.safe_name`.
- Produces: `PROJECT_FILE = "dasktoon_project.json"`, `PROJECT_VERSION = 1`, `MAX_RECENT = 8`, `Project(folder, name, engines)`
  (thuộc tính `file`, `engine`, `engine_path`), `load(path)`, `save(project)`, `find_project(blend_path) -> Project | None`,
  `project_target(project, name) -> ExportTarget`, `install_project_shaders(project, force=False) -> (written, warnings)`,
  `create_project(name, folder, engine, engine_path, save_current=False) -> Project` (lỗi đầu vào → `ValueError`),
  `project_models(project) -> list[str]`, `config_dir()`, `recent_projects() -> list[str]`, `add_recent(project_file)`.

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_project_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon projects (spec 7): creation, detection, model list, recent list, export into the linked Unity project."""

import json
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
import dasktoon_export  # noqa: E402
from dasktoon_export import targets  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402


def fake_unity():
    root = os.path.join(tempfile.mkdtemp(prefix="dt_proj_unity_"), "Game")
    os.makedirs(os.path.join(root, "Assets"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


class ProjectTest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_proj_config_")
        tu.reset_scene()
        self.unity = fake_unity()
        self.folder = os.path.join(tempfile.mkdtemp(prefix="dt_proj_"), "MyProject")

    def test_create_writes_json_installs_shaders_and_saves_the_file(self):
        project = dtp.create_project("Dự án của tôi", self.folder, 'UNITY_URP', self.unity, save_current=True)
        with open(os.path.join(self.folder, dtp.PROJECT_FILE), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data, {"version": 1, "name": "Dự án của tôi",
                                "engines": [{"engine": "UNITY_URP", "path": self.unity.replace("\\", "/")}]})
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", "Shaders", "AnimeBSDF.shader")))
        self.assertEqual(os.path.dirname(bpy.data.filepath), os.path.abspath(self.folder))
        self.assertEqual(dtp.find_project(bpy.data.filepath).name, "Dự án của tôi")
        self.assertEqual(dtp.recent_projects(), [project.file])

    def test_engine_path_must_be_a_unity_project(self):
        with self.assertRaises(ValueError):
            dtp.create_project("P", self.folder, 'UNITY_URP', tempfile.mkdtemp(prefix="dt_not_unity_"))
        with self.assertRaises(ValueError):
            dtp.create_project("P", self.folder, 'GODOT_4', self.unity)

    def test_existing_project_is_not_overwritten(self):
        dtp.create_project("P", self.folder, 'UNITY_URP', self.unity)
        with self.assertRaises(ValueError):
            dtp.create_project("Q", self.folder, 'UNITY_URP', self.unity)

    def test_project_is_found_from_a_subfolder(self):
        dtp.create_project("P", self.folder, 'UNITY_URP', self.unity)
        blend = os.path.join(self.folder, "characters", "hero", "hero.blend")
        self.assertEqual(dtp.find_project(blend).name, "P")
        self.assertIsNone(dtp.find_project(os.path.join(tempfile.mkdtemp(), "loose.blend")))
        self.assertIsNone(dtp.find_project(""))

    def test_model_list_skips_backups_and_hidden_folders(self):
        project = dtp.create_project("P", self.folder, 'UNITY_URP', self.unity)
        for rel in ("a.blend", "a.blend1", os.path.join("sub", "b.blend"), os.path.join(".hidden", "c.blend")):
            path = os.path.join(self.folder, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "wb").close()
        self.assertEqual(dtp.project_models(project),
                         [os.path.join(self.folder, "a.blend"), os.path.join(self.folder, "sub", "b.blend")])

    def test_recent_list_keeps_the_eight_newest(self):
        files = []
        for i in range(10):
            project = dtp.Project(os.path.join(tempfile.mkdtemp(prefix="dt_recent_"), "P%d" % i), "P%d" % i,
                                  [{"engine": "UNITY_URP", "path": self.unity}])
            dtp.save(project)
            dtp.add_recent(project.file)
            files.append(project.file)
        dtp.add_recent(files[5])
        recent = dtp.recent_projects()
        self.assertEqual(len(recent), dtp.MAX_RECENT)
        self.assertEqual(recent[0], files[5])
        self.assertEqual(recent[1], files[9])

    def test_project_target_writes_into_the_unity_project(self):
        project = dtp.create_project("P", self.folder, 'UNITY_URP', self.unity)
        target = dtp.project_target(project, "Hero")
        self.assertEqual((target.mode, target.root), ('PROJECT', os.path.join(self.unity, "Assets", "DaskToon")))
        body = tu.add_sphere(segments=8, rings=4)
        mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        tu.assign(body, mat)
        options = dasktoon_export.ExportOptions(include_animation=False, bake_size=32, bake_samples=2)
        rep = dasktoon_export.export_model(bpy.context, target, [body], options)
        self.assertEqual(rep.shaders, 'UP_TO_DATE')
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", "Hero", "Materials", "Skin.mat")))
        self.assertTrue(targets.find_unity_project(target.root))


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, phải FAIL**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_project_test.py 2>&1 | tail -5`
Expected: `ModuleNotFoundError: No module named 'dasktoon_project'`.

- [ ] **Step 3: Viết thư viện**

File: `scripts/modules/dasktoon_project/__init__.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon projects: a folder of .blend files linked to one game-engine project.
Design: docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md, section 7."""
```

File: `scripts/modules/dasktoon_project/project.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""dasktoon_project.json: read, write, detect from a .blend path, list models, remember recent projects (spec 7)."""

import json
import os
from dataclasses import dataclass, field

PROJECT_FILE = "dasktoon_project.json"
PROJECT_VERSION = 1
MAX_RECENT = 8
RECENT_FILE = "recent_projects.json"


@dataclass
class Project:
    folder: str
    name: str
    engines: list = field(default_factory=list)  # [{"engine": "UNITY_URP", "path": ...}]; this version uses the first

    @property
    def file(self):
        return os.path.join(self.folder, PROJECT_FILE)

    @property
    def engine(self):
        return self.engines[0]["engine"] if self.engines else ""

    @property
    def engine_path(self):
        return self.engines[0]["path"] if self.engines else ""


def load(path):
    """The project of a dasktoon_project.json file (or of the folder holding it)."""
    if os.path.isdir(path):
        path = os.path.join(path, PROJECT_FILE)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("version") != PROJECT_VERSION:
        raise ValueError("%s: phiên bản dự án %r không được hỗ trợ" % (path, data.get("version")))
    return Project(os.path.dirname(os.path.abspath(path)), data.get("name", ""), list(data.get("engines", [])))


def save(project):
    os.makedirs(project.folder, exist_ok=True)
    data = {"version": PROJECT_VERSION, "name": project.name, "engines": project.engines}
    with open(project.file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def find_project(blend_path):
    """The project whose folder holds `blend_path` (any depth), or None."""
    if not blend_path:
        return None
    current = os.path.dirname(os.path.abspath(blend_path))
    while True:
        candidate = os.path.join(current, PROJECT_FILE)
        if os.path.isfile(candidate):
            try:
                return load(candidate)
            except (OSError, ValueError):
                return None
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def project_target(project, name):
    """PROJECT-mode export target inside the project's Unity project."""
    from dasktoon_export import targets
    root = os.path.join(os.path.normpath(project.engine_path), "Assets", "DaskToon")
    return targets.ExportTarget(project.engine, 'PROJECT', root, name, os.path.normpath(project.engine_path))


def install_project_shaders(project, force=False):
    from dasktoon_export import shaders_install
    warnings = []
    written = shaders_install.install_shaders(project_target(project, ""), warnings, force=force)
    return written, warnings


def create_project(name, folder, engine, engine_path, save_current=False):
    """Create the folder and dasktoon_project.json, install the shaders into the Unity project, optionally save
    the current .blend file into the project, and remember the project (spec 7)."""
    import bpy
    from dasktoon_export import safe_name, targets
    if engine not in targets.SUPPORTED_ENGINES:
        raise ValueError("Engine %s chưa được hỗ trợ" % engine)
    engine_path = os.path.abspath(engine_path)
    if not targets.is_unity_project(engine_path):
        raise ValueError("%s không phải project Unity (cần có Assets/ và ProjectSettings/)" % engine_path)
    folder = os.path.abspath(folder)
    if os.path.exists(os.path.join(folder, PROJECT_FILE)):
        raise ValueError("%s đã là một dự án DaskToon" % folder)
    project = Project(folder, name, [{"engine": engine, "path": engine_path.replace("\\", "/")}])
    save(project)
    install_project_shaders(project)
    if save_current:
        file_name = os.path.basename(bpy.data.filepath) or safe_name(name) + ".blend"
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(folder, file_name))
    add_recent(project.file)
    return project


def project_models(project):
    """Every .blend file of the project (sub-folders included); .blend1 backups and hidden folders are skipped."""
    found = []
    for root, dirs, files in os.walk(project.folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        found += [os.path.join(root, f) for f in sorted(files) if f.lower().endswith(".blend")]
    return found


def config_dir():
    override = os.environ.get("DASKTOON_CONFIG_DIR")
    if override:
        return override
    import bpy
    return bpy.utils.user_resource('CONFIG', path="dasktoon", create=True)


def recent_projects():
    """Project files opened or created lately, newest first, existing ones only."""
    try:
        with open(os.path.join(config_dir(), RECENT_FILE), encoding="utf-8") as f:
            items = json.load(f)
    except (OSError, ValueError):
        return []
    return [p for p in items if isinstance(p, str) and os.path.isfile(p)][:MAX_RECENT]


def add_recent(project_file):
    project_file = os.path.abspath(project_file)
    items = [p for p in recent_projects() if os.path.normcase(p) != os.path.normcase(project_file)]
    items.insert(0, project_file)
    os.makedirs(config_dir(), exist_ok=True)
    with open(os.path.join(config_dir(), RECENT_FILE), "w", encoding="utf-8") as f:
        json.dump(items[:MAX_RECENT], f, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Chạy test, phải PASS**

Run: `cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_project_test.py 2>&1 | tail -5`
Expected: `Ran 7 tests ... OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/modules/dasktoon_project tests/python/dasktoon_project_test.py
git commit -m "feat: add DaskToon projects linked to a Unity project"
```

---

### Task 12: Giao diện Dự án (menu File, panel *DaskToon › Dự án*) và nối với Engine Export

**Files:**
- Create: `scripts/startup/bl_ui/dasktoon_project.py`
- Modify: `scripts/startup/bl_ui/__init__.py` (thêm `"dasktoon_project",` sau `"dasktoon_engine_export",`)
- Modify: `scripts/startup/bl_ui/dasktoon_engine_export.py` (`default_directory` ưu tiên dự án đang mở)
- Test: `tests/python/dasktoon_project_ui_test.py`

**Interfaces:**
- Consumes: toàn bộ `dasktoon_project.project`, `dasktoon_export.{ExportOptions, export_model}`, `model_fbx.export_objects`,
  `shaders_install.installed_version`, `report.show_popup`.
- Produces: `active_project() -> Project | None` (dự án chứa file `.blend` đang mở, nếu không thì dự án mở trong phiên này),
  operator `dasktoon.project_create`, `dasktoon.project_open`, `dasktoon.project_open_model`, `dasktoon.project_export`,
  `dasktoon.project_reinstall_shaders`, `dasktoon.project_open_folder`; menu `TOPBAR_MT_dasktoon_project`; panel
  `VIEW3D_PT_dasktoon_project`.

- [ ] **Step 1: Viết test**

File: `tests/python/dasktoon_project_ui_test.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon project operators and the Engine Export default target (spec 7). Panels are checked by hand."""

import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from bl_ui import dasktoon_engine_export as export_ui  # noqa: E402
from bl_ui import dasktoon_project as project_ui  # noqa: E402
from dasktoon_project import project as dtp  # noqa: E402


def fake_unity():
    root = os.path.join(tempfile.mkdtemp(prefix="dt_projui_unity_"), "Game")
    os.makedirs(os.path.join(root, "Assets"))
    os.makedirs(os.path.join(root, "ProjectSettings"))
    return root


class ProjectUITest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_projui_config_")
        tu.reset_scene()
        project_ui.forget_session_project()
        body = tu.add_sphere(segments=8, rings=4)
        body.name = "Body"
        mat, _node = tu.node_material("Skin", 'ShaderNodeAnimeCharacter')
        tu.assign(body, mat)
        self.unity = fake_unity()
        self.folder = os.path.join(tempfile.mkdtemp(prefix="dt_projui_"), "Proj")

    def create(self):
        return bpy.ops.dasktoon.project_create(name="Proj", folder=self.folder, engine='UNITY_URP',
                                               engine_path=self.unity, save_current=True)

    def test_create_makes_the_saved_file_part_of_the_project(self):
        self.assertEqual(self.create(), {'FINISHED'})
        self.assertEqual(project_ui.active_project().name, "Proj")
        self.assertTrue(bpy.data.filepath.startswith(os.path.abspath(self.folder)))

    def test_create_reports_a_bad_unity_path(self):
        with self.assertRaises(RuntimeError):
            bpy.ops.dasktoon.project_create(name="Proj", folder=self.folder, engine='UNITY_URP',
                                            engine_path=tempfile.mkdtemp(prefix="dt_not_unity_"))

    def test_open_sets_the_session_project_for_an_unsaved_file(self):
        project = dtp.create_project("Opened", self.folder, 'UNITY_URP', self.unity)
        self.assertIsNone(project_ui.active_project())
        self.assertEqual(bpy.ops.dasktoon.project_open(filepath=project.file), {'FINISHED'})
        self.assertEqual(project_ui.active_project().name, "Opened")
        self.assertEqual(dtp.recent_projects()[0], project.file)

    def test_export_this_model_writes_into_the_unity_project(self):
        self.create()
        self.assertEqual(bpy.ops.dasktoon.project_export(), {'FINISHED'})
        name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", name, "Materials", "Skin.mat")))
        self.assertTrue(os.path.isfile(os.path.join(self.unity, "Assets", "DaskToon", name, "Model", name + ".fbx")))

    def test_reinstall_shaders_rewrites_edited_files(self):
        self.create()
        shader = os.path.join(self.unity, "Assets", "DaskToon", "Shaders", "AnimeBSDF.shader")
        with open(shader, "w", encoding="utf-8") as f:
            f.write("edited")
        self.assertEqual(bpy.ops.dasktoon.project_reinstall_shaders(), {'FINISHED'})
        with open(shader, encoding="utf-8") as f:
            self.assertNotEqual(f.read(), "edited")

    def test_engine_export_opens_on_the_project(self):
        self.create()
        self.assertEqual(export_ui.default_directory(bpy.context), (self.unity.replace("\\", "/"), 'UNITY_URP'))

    def test_ui_is_registered(self):
        self.assertTrue(hasattr(bpy.types, "VIEW3D_PT_dasktoon_project"))
        self.assertTrue(hasattr(bpy.types, "TOPBAR_MT_dasktoon_project"))
        self.assertIn(project_ui.menu_func_file, bpy.types.TOPBAR_MT_file._dyn_ui_initialize())


if __name__ == "__main__":
    tu.run_tests()
```

- [ ] **Step 2: Chạy test, phải FAIL**

Run: `cp -r scripts/startup/. "$BUILD/bin/Release/5.2/scripts/startup/"; cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_project_ui_test.py 2>&1 | tail -5`
Expected: `ImportError: cannot import name 'dasktoon_project' from 'bl_ui'`.

- [ ] **Step 3: Viết giao diện dự án**

File: `scripts/startup/bl_ui/dasktoon_project.py`
```python
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""DaskToon projects in the UI: File › Dự án DaskToon and the sidebar panel DaskToon › Dự án
(docs/superpowers/specs/2026-10-03-dasktoon-unity-export-design.md, section 7)."""

import os
import time

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Menu, Operator, Panel

from dasktoon_export import targets
from dasktoon_project import project as dtp

_session = {"project_file": ""}  # project opened with "Mở dự án…", remembered for this session only
_models_cache = {"key": None, "time": 0.0, "models": []}
MODELS_REFRESH = 2.0  # seconds; the panel redraws often and must not walk the folder every time


def forget_session_project():
    _session["project_file"] = ""


def active_project():
    """The project holding the open .blend file, else the one opened this session (spec 7)."""
    found = dtp.find_project(bpy.data.filepath)
    if found is not None:
        return found
    path = _session["project_file"]
    if path and os.path.isfile(path):
        try:
            return dtp.load(path)
        except (OSError, ValueError):
            return None
    return None


def _models(project):
    now = time.monotonic()
    if _models_cache["key"] != project.folder or now - _models_cache["time"] > MODELS_REFRESH:
        _models_cache.update(key=project.folder, time=now, models=dtp.project_models(project))
    return _models_cache["models"]


def _require_project(op):
    project = active_project()
    if project is None:
        op.report({'ERROR'}, "Chưa mở dự án DaskToon nào")
    return project


class DASKTOON_OT_project_create(Operator):
    """Create a DaskToon project linked to a Unity project and install the DaskToon shaders into it"""
    bl_idname = "dasktoon.project_create"
    bl_label = "Tạo dự án DaskToon"
    bl_options = {'REGISTER'}

    name: StringProperty(name="Tên", default="Dự án mới")
    folder: StringProperty(name="Thư mục dự án", subtype='DIR_PATH')
    engine: EnumProperty(name="Engine", items=targets.ENGINES, default='UNITY_URP')
    engine_path: StringProperty(name="Project Unity", subtype='DIR_PATH')
    save_current: BoolProperty(name="Lưu file hiện tại vào dự án", default=True)

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self, width=520)

    def execute(self, _context):
        try:
            project = dtp.create_project(self.name, bpy.path.abspath(self.folder), self.engine,
                                         bpy.path.abspath(self.engine_path), self.save_current)
        except (ValueError, OSError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        _session["project_file"] = project.file
        self.report({'INFO'}, "Đã tạo dự án %s và cài shader vào %s" % (project.name, project.engine_path))
        return {'FINISHED'}


class DASKTOON_OT_project_open(Operator):
    """Open a DaskToon project (dasktoon_project.json)"""
    bl_idname = "dasktoon.project_open"
    bl_label = "Mở dự án DaskToon"

    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default="dasktoon_project.json", options={'HIDDEN'})

    def invoke(self, context, _event):
        if self.filepath and os.path.isfile(self.filepath):
            return self.execute(context)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, _context):
        try:
            project = dtp.load(self.filepath)
        except (OSError, ValueError) as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        _session["project_file"] = project.file
        dtp.add_recent(project.file)
        self.report({'INFO'}, "Đã mở dự án %s" % project.name)
        return {'FINISHED'}


class DASKTOON_OT_project_open_model(Operator):
    """Open this .blend file of the project (DaskToon asks to save the current file first when it has changes)"""
    bl_idname = "dasktoon.project_open_model"
    bl_label = "Mở"

    filepath: StringProperty(subtype='FILE_PATH', options={'HIDDEN'})

    def execute(self, _context):
        bpy.ops.wm.open_mainfile('INVOKE_DEFAULT', filepath=self.filepath, display_file_selector=False)
        return {'FINISHED'}


class DASKTOON_OT_project_export(Operator):
    """Export this file's model, materials and shaders straight into the project's Unity project"""
    bl_idname = "dasktoon.project_export"
    bl_label = "Export model này"

    def execute(self, context):
        import dasktoon_export
        from dasktoon_export import model_fbx, report
        project = _require_project(self)
        if project is None:
            return {'CANCELLED'}
        objects = model_fbx.export_objects(context, selected_only=False)
        if not objects:
            self.report({'ERROR'}, "File không có object nào để export")
            return {'CANCELLED'}
        target = dtp.project_target(project, targets.blend_name(bpy.data.filepath))
        rep = dasktoon_export.export_model(context, target, objects, dasktoon_export.ExportOptions())
        report.show_popup(rep)
        self.report({'WARNING'} if rep.warnings else {'INFO'}, rep.summary())
        return {'FINISHED'}


class DASKTOON_OT_project_reinstall_shaders(Operator):
    """Write the DaskToon shaders into the project's Unity project again"""
    bl_idname = "dasktoon.project_reinstall_shaders"
    bl_label = "Cài lại shader"

    def execute(self, _context):
        project = _require_project(self)
        if project is None:
            return {'CANCELLED'}
        _written, warnings = dtp.install_project_shaders(project, force=True)
        for warning in warnings:
            self.report({'WARNING'}, warning)
        self.report({'INFO'}, "Đã cài lại shader vào %s" % project.engine_path)
        return {'FINISHED'}


class DASKTOON_OT_project_open_folder(Operator):
    """Open the project folder in the file manager"""
    bl_idname = "dasktoon.project_open_folder"
    bl_label = "Mở thư mục dự án"

    def execute(self, _context):
        project = _require_project(self)
        if project is None:
            return {'CANCELLED'}
        bpy.ops.wm.path_open(filepath=project.folder)
        return {'FINISHED'}


class TOPBAR_MT_dasktoon_project(Menu):
    bl_label = "Dự án DaskToon"

    def draw(self, _context):
        layout = self.layout
        layout.operator(DASKTOON_OT_project_create.bl_idname, text="Tạo dự án…", icon='NEWFOLDER')
        layout.operator(DASKTOON_OT_project_open.bl_idname, text="Mở dự án…", icon='FILE_FOLDER')


class VIEW3D_PT_dasktoon_project(Panel):
    bl_label = "Dự án"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"

    def draw(self, _context):
        from dasktoon_export import shaders_install
        layout = self.layout
        project = active_project()
        if project is None:
            col = layout.column(align=True)
            col.operator(DASKTOON_OT_project_create.bl_idname, text="Tạo dự án…", icon='NEWFOLDER')
            col.operator(DASKTOON_OT_project_open.bl_idname, text="Mở dự án…", icon='FILE_FOLDER')
            recent = dtp.recent_projects()
            if recent:
                layout.label(text="Dự án gần đây:")
                col = layout.column(align=True)
                for path in recent:
                    op = col.operator(DASKTOON_OT_project_open.bl_idname,
                                      text=os.path.basename(os.path.dirname(path)), icon='FILE_FOLDER')
                    op.filepath = path
            return
        box = layout.box()
        box.label(text=project.name, icon='FILE_FOLDER')
        engines = {key: label for key, label, _desc in targets.ENGINES}
        box.label(text="Engine: " + engines.get(project.engine, project.engine))
        box.label(text=project.engine_path)
        version = shaders_install.installed_version(os.path.join(project.engine_path, "Assets", "DaskToon"))
        box.label(text=("Shader: phiên bản %d" % version) if version else "Shader: chưa cài",
                  icon='CHECKMARK' if version else 'ERROR')
        current = os.path.normcase(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else ""
        col = layout.column(align=True)
        for path in _models(project):
            row = col.row(align=True)
            is_current = os.path.normcase(path) == current
            row.label(text=os.path.relpath(path, project.folder), icon='RADIOBUT_ON' if is_current else 'BLENDER')
            op = row.operator(DASKTOON_OT_project_open_model.bl_idname, text="Mở")
            op.filepath = path
        layout.operator(DASKTOON_OT_project_export.bl_idname, icon='EXPORT')
        row = layout.row(align=True)
        row.operator(DASKTOON_OT_project_reinstall_shaders.bl_idname, icon='FILE_REFRESH')
        row.operator(DASKTOON_OT_project_open_folder.bl_idname, icon='FILEBROWSER')


def menu_func_file(self, _context):
    self.layout.separator()
    self.layout.menu(TOPBAR_MT_dasktoon_project.bl_idname, icon='FILE_FOLDER')


classes = (
    DASKTOON_OT_project_create,
    DASKTOON_OT_project_open,
    DASKTOON_OT_project_open_model,
    DASKTOON_OT_project_export,
    DASKTOON_OT_project_reinstall_shaders,
    DASKTOON_OT_project_open_folder,
    TOPBAR_MT_dasktoon_project,
    VIEW3D_PT_dasktoon_project,
)


# bl_ui registers `classes` itself; register()/unregister() only manage the File menu entry.
def register():
    bpy.types.TOPBAR_MT_file.append(menu_func_file)


def unregister():
    bpy.types.TOPBAR_MT_file.remove(menu_func_file)
```

Trong `scripts/startup/bl_ui/dasktoon_engine_export.py`, thay hàm `default_directory` bằng:
```python
def default_directory(context):
    """(directory, engine) the dialog opens with: the open DaskToon project's engine project (spec 7), else the
    target remembered in this .blend file, else the .blend file's folder."""
    from . import dasktoon_project
    project = dasktoon_project.active_project()
    if project is not None and project.engine_path:
        return project.engine_path, project.engine
    remembered = targets.remembered_target(context.scene)
    if remembered and os.path.isdir(remembered[0]):
        return remembered
    if bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath), 'UNITY_URP'
    return "", 'UNITY_URP'
```
và thêm `"dasktoon_project",` vào `_modules` của `bl_ui/__init__.py`, ngay sau `"dasktoon_engine_export",`.

- [ ] **Step 4: Chạy test của task này và của Task 9, phải PASS**

Run: `cp -r scripts/startup/. "$BUILD/bin/Release/5.2/scripts/startup/"; cp -r scripts/modules/. "$BUILD/bin/Release/5.2/scripts/modules/"; for t in project_ui_test engine_export_ui_test; do "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_$t.py 2>&1 | tail -3; done`
Expected: `Ran 7 tests ... OK` và `Ran 4 tests ... OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/startup/bl_ui/dasktoon_project.py scripts/startup/bl_ui/dasktoon_engine_export.py scripts/startup/bl_ui/__init__.py tests/python/dasktoon_project_ui_test.py
git commit -m "feat: add the DaskToon project menu and sidebar panel, and target the project in Engine Export"
```

---

### Task 13: Đăng ký test với CMake, chạy toàn bộ, báo cáo

**Files:**
- Modify: `tests/python/CMakeLists.txt` (thêm các test headless vào khối `foreach(dasktoon_test ...)`)
- Create: `docs/superpowers/reports/2026-10-03-dasktoon-unity-export-report.md`

- [ ] **Step 1: Đăng ký test headless**

Trong khối `foreach(dasktoon_test` của `tests/python/CMakeLists.txt`, thêm sau `dasktoon_upgrade_test`:
```cmake
    dasktoon_export_yaml_test
    dasktoon_export_targets_test
    dasktoon_export_shaders_test
    dasktoon_export_graph_test
    dasktoon_export_textures_test
    dasktoon_export_fbx_test
    dasktoon_export_layout_test
    dasktoon_engine_export_ui_test
    dasktoon_project_test
    dasktoon_project_ui_test
```
Test Unity (`dasktoon_unity_*_test`) không đăng ký vì cần Unity 6000.5 và GPU; báo cáo ghi cách chạy tay.

- [ ] **Step 2: Chạy toàn bộ test (Dự án 1 và Dự án 2)**

Run:
```bash
for t in platform_test shading_test shading_baseline shading_styles_test outline_nodes_test outline_sync_test outline_gamedata_test upgrade_test export_yaml_test export_targets_test export_shaders_test export_graph_test export_textures_test export_fbx_test export_layout_test engine_export_ui_test project_test project_ui_test unity_smoke_test unity_shaders_test unity_model_test unity_render_test; do
  "$DT" --background --factory-startup --python-exit-code 1 --python tests/python/dasktoon_$t.py > "$TEMP/dt_$t.log" 2>&1 && echo "PASS $t" || echo "FAIL $t"
done
```
Expected: 22 dòng `PASS`.

- [ ] **Step 3: Viết báo cáo** `docs/superpowers/reports/2026-10-03-dasktoon-unity-export-report.md` (tiếng Việt, cho người dùng):
kết quả từng task, bảng sai số DaskToon/Unity, ảnh `2026-10-03-unity-compare.png`, cách dùng Engine Export và Dự án, mọi
`Ruling:` trong ledger kèm cái giá nếu sai, các minor để lại, những việc người dùng cần tự kiểm tra (hộp thoại Engine Export, panel
Dự án, mở thư mục xuất trong Unity thật, nhân vật có xương và animation), cách chạy lại test, và nhắc lỗ hổng AI Bridge (RCE ở cổng
9998, commit `b9dbe7997f9`) vẫn chưa sửa.

- [ ] **Step 4: Commit**

```bash
git add tests/python/CMakeLists.txt docs/superpowers/reports/2026-10-03-dasktoon-unity-export-report.md
git commit -m "test: register the Engine Export and project tests, and add the project 2 report"
```
