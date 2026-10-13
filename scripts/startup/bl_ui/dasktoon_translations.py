# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Vietnamese translation of the DaskToon interface (docs/superpowers/specs/2026-10-04-dasktoon-ui-reorganization-design.md,
section 6). The source strings are English; with Preferences › Interface › Language set to Tiếng Việt Blender shows
these. Strings Blender already translates keep Blender's wording. Every entry is registered for the default context
("*") and for operator names ("Operator")."""

import bpy

# Names that stay as they are in Vietnamese (brands, standards, shape key names).
KEEP = {
    "DaskToon", "Unity", "Unity 6 (URP)", "VRM", "VRoid", "ARKit", "FBX", "URP",
    "VRM 0.x", "VRM 1.0", "_L / _R", "_l / _r", "Left / Right",
    "Anime BSDF", "Manga BSDF", "DaskToon Anime", "DaskToon Manga", "Manga", "Unity 6, Universal Render Pipeline 17.5",
    "Engine: %s",
}

VI = {
    # bl_ui/dasktoon_engine_export.py
    "Engine Export": "Xuất sang engine",
    "Engine Export…": "Xuất sang engine…",
    "Export the model, its DaskToon materials and the shaders for a game engine":
        "Xuất model, material DaskToon và shader cho game engine",
    "Folder": "Thư mục",
    "Model": "Mô hình",
    "Export the model as FBX": "Xuất model dạng FBX",
    "No Model": "Không xuất model",
    "Export only the materials and shaders": "Chỉ xuất material và shader",
    "Include Animation": "Kèm animation",
    "Export Materials and Shaders": "Xuất material và shader",
    "Bake Size": "Cỡ ảnh bake",
    "Writes straight into the Unity project": "Ghi thẳng vào project Unity",
    "Creates the folder %s": "Tạo thư mục %s",
    "This engine is coming soon; only Unity 6 (URP) is supported for now":
        "Engine này sắp có; hiện chỉ hỗ trợ Unity 6 (URP)",
    "No destination folder chosen": "Chưa chọn thư mục đích",
    "Nothing to export (no object selected?)": "Không có gì để xuất (chưa chọn object?)",

    # bl_ui/dasktoon_outline.py
    "Remove DaskToon Outline": "Gỡ outline DaskToon",
    "Turn off the DaskToon outline this material got before outlines moved onto the Anime BSDF and Dask Cel nodes":
        "Tắt outline DaskToon mà material này được bật từ trước khi outline chuyển lên node Anime BSDF và Dask Cel",

    # bl_ui/dasktoon_outline_gamedata.py
    "Prepare Outline for Games": "Chuẩn bị outline cho game",
    "Write smoothed outline normals and the width mask into real UV maps for game export":
        "Ghi normal outline đã làm mượt và mặt nạ độ dày vào UV map thật để xuất sang game",
    "%s: needs at least one UV map": "%s: cần ít nhất một UV map",
    "%s: has faces with more than 4 sides (n-gons); triangulate or split them first":
        "%s: có mặt nhiều hơn 4 cạnh (ngon); hãy Triangulate hoặc chia lại trước",
    "%s: wrote %s and %s": "%s: đã ghi %s và %s",
    "Prepared %d mesh(es), %d error(s)": "Đã chuẩn bị %d mesh, %d lỗi",

    # bl_ui/dasktoon_face_shading.py
    "Face Shading": "Bóng mặt",
    "Set Up Face Shading": "Tạo bóng mặt anime",
    "Shade the face like an egg: find the head, fit an egg-shaped proxy to it and add the Face Shading modifier":
        "Đổ bóng mặt như một quả trứng: tìm đầu, căn một khối trứng ôm lấy nó và thêm modifier Face Shading",
    "Fit Proxy": "Căn lại khối trứng",
    "Fit the egg-shaped proxy to the face again (position and size); the sliders stay":
        "Căn lại khối trứng theo khuôn mặt (vị trí và kích thước); giữ nguyên các thanh trượt",
    "Remove Face Shading": "Gỡ bóng mặt",
    "Remove the face shading of the mesh: the modifier, DT_Face and the proxy when no other mesh uses it":
        "Gỡ bóng mặt khỏi mesh: modifier, DT_Face và khối trứng nếu không còn mesh nào dùng",
    "Select Proxy": "Chọn khối trứng",
    "Select the egg-shaped proxy to move, rotate or scale it; the face shading follows right away":
        "Chọn khối trứng để di chuyển, xoay hoặc co giãn; bóng mặt cập nhật ngay",
    "Keep Nose Shadow": "Giữ bóng mũi",
    "Keep Chin Shadow": "Giữ bóng cằm",
    "Proxy of %s": "Khối trứng của %s",
    "No proxy yet: press Fit Proxy": "Chưa có khối trứng: bấm Căn lại khối trứng",
    "Linked from a library, cannot be edited": "Link từ thư viện, không sửa được",
    "This mesh still has old custom normals:": "Mesh còn custom normal cũ:",
    "the nose and chin shadows follow them, not the real shape": "bóng mũi và cằm sẽ theo normal đó, không theo hình khối thật",
    "Select a character mesh": "Hãy chọn mesh nhân vật",
    "Mesh %s is linked from a library and cannot be edited": "Mesh %s được link từ thư viện, không sửa được",
    "No head found (no head bone with weights): select the face in Edit Mode and try again":
        "Không tìm thấy vùng đầu (không có xương đầu có trọng số): hãy chọn vùng mặt trong Edit Mode rồi bấm lại",
    "No face skin in the middle of the head: select the whole face, nose included, and try again":
        "Không thấy da mặt ở giữa vùng đầu: hãy chọn cả khuôn mặt, kể cả mũi, rồi bấm lại",
    "The face is too small to fit a proxy": "Vùng mặt quá nhỏ để đặt khối trứng",
    "%s is not inside the head: paint that vertex group again": "%s không nằm trong vùng đầu: hãy tô lại vertex group đó",
    "%s has no face shading yet: press Set Up Face Shading first":
        "%s chưa có bóng mặt: hãy bấm Tạo bóng mặt anime trước",
    "Face shading set up on %s: drag the proxy or use the sliders":
        "Đã tạo bóng mặt cho %s: kéo khối trứng hoặc chỉnh thanh trượt",
    "Proxy of %s fitted again": "Đã căn lại khối trứng của %s",
    "Face shading removed from %s": "Đã gỡ bóng mặt của %s",
    "This mesh has no proxy yet: press Set Up Face Shading or Fit Proxy":
        "Mesh chưa có khối trứng: bấm Tạo bóng mặt anime hoặc Căn lại khối trứng",
    "Proxy %s is not in the open view layer": "Khối trứng %s không nằm trong view layer đang mở",

    # bl_ui/dasktoon_material_combiner.py
    "Combine Materials": "Gộp material",
    "Bake all material slots into one atlas texture and one Anime BSDF material, so the viewport draws faster":
        "Bake mọi slot material vào một texture atlas và một material Anime BSDF để viewport vẽ nhanh hơn",
    "Size of the atlas texture": "Kích thước texture atlas",
    "Lightest": "Nhẹ nhất",
    "Sharp enough for most characters": "Đủ nét cho hầu hết nhân vật",
    "Sharpest, for close-ups": "Nét nhất, cho cảnh cận",
    "Spread the colors this many pixels past the edges of the UV islands, to hide seams":
        "Loang màu ra ngoài mép các đảo UV thêm chừng này pixel để giấu đường nối",
    "Restore Original Slots": "Khôi phục slot gốc",
    "Put back the material slots the mesh had before Combine Materials":
        "Trả lại các slot material mà mesh có trước khi Gộp material",
    "Select a mesh object": "Hãy chọn một object mesh",
    "%s has fewer than 2 material slots: nothing to combine": "%s có ít hơn 2 slot material: không có gì để gộp",
    "Combined %d material slots into %s, atlas %s": "Đã gộp %d slot material vào %s, atlas %s",
    "%s has no saved slots to restore": "%s không có slot đã lưu để khôi phục",
    "Restored %d material slots on %s": "Đã khôi phục %d slot material cho %s",

    # bl_ui/dasktoon_anime_fx.py
    "Anime Effect": "Hiệu ứng anime",
    "Add Anime Effect": "Thêm hiệu ứng anime",
    "Add an anime effect: an impact effect or atmosphere particles":
        "Thêm hiệu ứng anime: hiệu ứng va chạm hoặc hạt không khí",
    "Impact": "Va chạm",
    "Atmosphere": "Không khí",
    "Effect to add": "Hiệu ứng cần thêm",
    "Shockwave Ring": "Vòng sóng xung kích",
    "An expanding ring with sharp energy teeth": "Vòng tròn nở rộng với các răng năng lượng sắc nhọn",
    "Hit Spark": "Tia lửa va chạm",
    "An 8-point spark burst with sharp rays": "Chùm tia lửa 8 cánh với các tia sắc nhọn",
    "Slash Arc": "Vệt chém",
    "A curved glowing crescent, like a sword slash": "Vầng trăng khuyết phát sáng, như một nhát kiếm",
    "Debris Blast": "Đá vụn bắn tung",
    "Rock fragments blasting outward from the point of impact": "Mảnh đá bắn tung ra từ điểm va chạm",
    "Bubbles Rising": "Bong bóng bay lên",
    "Bubbles floating gently upward, with a rainbow sheen": "Bong bóng nhẹ nhàng bay lên, có ánh cầu vồng",
    "Bubbles Sinking": "Bong bóng chìm xuống",
    "Bubbles drifting slowly downward": "Bong bóng trôi chậm xuống dưới",
    "Sakura Petals": "Cánh hoa anh đào",
    "Cherry blossom petals drifting and tumbling in the wind": "Cánh hoa anh đào trôi và xoay trong gió",
    "Magic Sparkles": "Lấp lánh ma thuật",
    "Glowing 4-point stars and floating stardust": "Sao 4 cánh phát sáng và bụi sao lơ lửng",
    "Falling Leaves": "Lá rơi",
    "Leaves swirling in a breeze": "Lá cây xoáy trong làn gió",
    "Cel Rain": "Mưa hoạt hình",
    "Straight rain streaks falling from above": "Vệt mưa thẳng rơi từ trên xuống",
    "Fire Embers": "Tàn lửa",
    "Glowing sparks rising into the air": "Tia lửa phát sáng bay lên không trung",
    "Number of particles or debris pieces": "Số hạt hoặc số mảnh vụn",
    "How fast the particles drift or the impact expands": "Tốc độ hạt trôi hoặc va chạm lan ra",
    "How strongly the particles sway in the wind or water": "Mức hạt đung đưa trong gió hoặc nước",
    "Scale of the effect": "Tỉ lệ của hiệu ứng",
    "Added %s": "Đã thêm %s",

    # bl_ui/dasktoon_shape_key_manager.py: panels, lists and HUD
    "Expression Sets": "Bộ biểu cảm",
    "Expression Tools": "Công cụ biểu cảm",
    "Expression Preview": "Xem trước biểu cảm",
    "Controllers": "Bộ điều khiển",
    "VRM 0.x Set": "Bộ VRM 0.x",
    "VRM 1.0 Set": "Bộ VRM 1.0",
    "ARKit 52: %d / 52 shapes": "ARKit 52: %d / 52 hình mẫu",
    "Eyes": "Mắt",
    "Jaw & Mouth": "Hàm và miệng",
    "Brows": "Lông mày",
    "Cheeks, Nose & Tongue": "Má, mũi và lưỡi",
    "Test on Model": "Thử trên model",
    "Clear Values": "Xóa giá trị",
    "Blink": "Chớp mắt",
    "Speech": "Nói",
    "Emotions": "Cảm xúc",
    "Open Viewport HUD": "Mở HUD trong cổng nhìn",
    "Close Viewport HUD": "Đóng HUD trong cổng nhìn",
    "Reset Group": "Đặt lại nhóm",
    "Reset All": "Đặt lại tất cả",
    "Auto Setup": "Tự thiết lập",
    "Auto Detect VRM / VRoid": "Tự nhận VRM / VRoid",
    "VRM Emotions": "Cảm xúc VRM",
    "AIUEO Visemes": "Khẩu hình AIUEO",
    "Blink Sliders": "Thanh trượt chớp mắt",
    "Ears & Tail": "Tai và đuôi",
    "Controller Groups": "Nhóm bộ điều khiển",
    "Fader Channels (%d sliders)": "Các kênh trượt (%d thanh trượt)",
    "Shape Key Mappings": "Ánh xạ hình mẫu",
    "%d shapes": "%d hình mẫu",
    "%d sliders": "%d thanh trượt",
    "(Empty)": "(Trống)",
    "VRM Expression": "Biểu cảm VRM",
    "Expression to look up": "Biểu cảm cần tra",
    "ARKit Shape Key": "Hình mẫu ARKit",
    "ARKit shape key to look up": "Hình mẫu ARKit cần tra",
    "An ARKit facial movement.": "Một cử động khuôn mặt của ARKit.",
    "Open a 3D Viewport to show the HUD": "Hãy mở một Cổng Nhìn 3D để hiện HUD",
    "HUD open: drag the handle or the sliders, I inserts a keyframe, Esc closes":
        "Đã mở HUD: kéo tay cầm hoặc thanh trượt, I chèn khung khóa, Esc để đóng",

    # bl_ui/dasktoon_shape_key_manager.py: controller data
    "A shape key placed on a controller: a point on the pad, or a slider of a slider bank":
        "Một hình mẫu đặt trên bộ điều khiển: một điểm trên bảng, hoặc một thanh trượt của dãy thanh trượt",
    "Shape key this mapping drives": "Hình mẫu mà ánh xạ này điều khiển",
    "Target X": "Đích X",
    "Target Y": "Đích Y",
    "Position of the shape key on the pad, from left (-1) to right (1)":
        "Vị trí của hình mẫu trên bảng, từ trái (-1) sang phải (1)",
    "Position of the shape key on the pad, from bottom (-1) to top (1)":
        "Vị trí của hình mẫu trên bảng, từ dưới (-1) lên trên (1)",
    "Value of this slider": "Giá trị của thanh trượt này",
    "Influence Radius": "Bán kính ảnh hưởng",
    "Distance from the point at which the shape key fades out": "Khoảng cách tính từ điểm mà tại đó hình mẫu mờ dần hết",
    "Lowest value given to the shape key": "Giá trị thấp nhất gán cho hình mẫu",
    "Highest value given to the shape key": "Giá trị cao nhất gán cho hình mẫu",
    "Exponent of the falloff curve: 1 is linear, 2 smooth, 0.5 sharp":
        "Số mũ của đường suy giảm: 1 là tuyến tính, 2 là mượt, 0.5 là gắt",
    "Use this mapping": "Dùng ánh xạ này",
    "A controller: a pad or a slider bank that drives a set of shape keys":
        "Bộ điều khiển: một bảng hoặc một dãy thanh trượt điều khiển một nhóm hình mẫu",
    "Name of the controller": "Tên bộ điều khiển",
    "What the controller animates": "Thứ mà bộ điều khiển làm chuyển động",
    "Expressions, eyes and brows": "Biểu cảm, mắt và lông mày",
    "Lip Sync": "Khớp khẩu hình",
    "Visemes and speech shapes": "Khẩu hình và hình dạng khi nói",
    "Body": "Cơ thể",
    "Breathing, muscles and proportions": "Hơi thở, cơ bắp và tỉ lệ cơ thể",
    "Hair & Ears": "Tóc và tai",
    "Animal ears, tails and hair": "Tai thú, đuôi và tóc",
    "Skirt and cape sway, wrinkles": "Váy và áo choàng đung đưa, nếp nhăn",
    "Props": "Đạo cụ",
    "Weapons, mechanical parts and customizer shapes": "Vũ khí, bộ phận cơ khí và hình mẫu tùy biến nhân vật",
    "Anything else": "Những thứ khác",
    "Shape of the controller": "Dạng của bộ điều khiển",
    "2D Joystick": "Cần điều khiển 2D",
    "A pad with each shape key at a point": "Một bảng với mỗi hình mẫu ở một điểm",
    "AIUEO Star": "Ngôi sao AIUEO",
    "A five-point star for the vowels A, I, U, E, O": "Ngôi sao năm cánh cho các nguyên âm A, I, U, E, O",
    "Emotion Wheel": "Bánh xe cảm xúc",
    "A wheel with an emotion in each direction": "Một bánh xe với mỗi hướng là một cảm xúc",
    "Slider Bank": "Dãy thanh trượt",
    "One slider per shape key": "Mỗi hình mẫu một thanh trượt",
    "Handle X": "Tay cầm X",
    "Handle Y": "Tay cầm Y",
    "Horizontal position of the handle": "Vị trí ngang của tay cầm",
    "Vertical position of the handle": "Vị trí dọc của tay cầm",
    "Active Mapping Index": "Chỉ số ánh xạ đang chọn",
    "Smooth Blending": "Hòa trộn mượt",
    "Blend smoothly where the influence of two points overlaps":
        "Hòa trộn mượt ở chỗ vùng ảnh hưởng của hai điểm chồng lên nhau",
    "The controllers of a mesh object": "Các bộ điều khiển của một object mesh",
    "Active Controller Index": "Chỉ số bộ điều khiển đang chọn",
    "Show HUD": "Hiện HUD",
    "Show the controller HUD in the 3D Viewport": "Hiện HUD bộ điều khiển trong Cổng Nhìn 3D",
    "HUD X": "Vị trí X của HUD",
    "HUD Y": "Vị trí Y của HUD",
    "HUD Size": "Cỡ HUD",

    # bl_ui/dasktoon_shape_key_manager.py: controller operators
    "Viewport HUD": "HUD trong cổng nhìn",
    "Show the active controller in the 3D Viewport: drag the handle or the sliders, I inserts a keyframe, Esc closes":
        "Hiện bộ điều khiển đang chọn trong Cổng Nhìn 3D: kéo tay cầm hoặc thanh trượt, I chèn khung khóa, Esc để đóng",
    "Select a mesh with shape keys": "Hãy chọn một mesh có hình mẫu",
    "Move the handle of the active controller back to the middle and set its sliders to 0":
        "Đưa tay cầm của bộ điều khiển đang chọn về giữa và đặt các thanh trượt của nó về 0",
    "Reset %s": "Đã đặt lại %s",
    "Reset All Controllers": "Đặt lại mọi bộ điều khiển",
    "Reset every controller and set all shape keys to 0": "Đặt lại mọi bộ điều khiển và đưa mọi hình mẫu về 0",
    "All controllers and shape keys reset": "Đã đặt lại mọi bộ điều khiển và hình mẫu",
    "Insert a keyframe on the handle of the active controller and on its shape keys":
        "Chèn khung khóa cho tay cầm của bộ điều khiển đang chọn và cho các hình mẫu của nó",
    "Keyframed %s at frame %d": "Đã chèn khung khóa cho %s tại khung %d",
    "Add Controller": "Thêm bộ điều khiển",
    "Add a controller": "Thêm một bộ điều khiển",
    "Remove Controller": "Xóa bộ điều khiển",
    "Remove the active controller": "Xóa bộ điều khiển đang chọn",
    "Add Mapping": "Thêm ánh xạ",
    "Add a shape key to the active controller": "Thêm một hình mẫu vào bộ điều khiển đang chọn",
    "Remove Mapping": "Xóa ánh xạ",
    "Remove the active shape key from the controller": "Bỏ hình mẫu đang chọn khỏi bộ điều khiển",
    "Find the character's shape keys (VRM, VRoid, MMD and other common names) and add controllers for them":
        "Tìm các hình mẫu của nhân vật (VRM, VRoid, MMD và các tên thông dụng khác) rồi thêm bộ điều khiển cho chúng",
    "Emotion wheel, AIUEO star, gaze joystick and blink sliders for VRM 0.x, VRM 1.0 and VRoid shape keys":
        "Bánh xe cảm xúc, ngôi sao AIUEO, cần điều khiển ánh nhìn và thanh trượt chớp mắt cho hình mẫu VRM 0.x, "
        "VRM 1.0 và VRoid",
    "Everything": "Tất cả",
    "Every controller below that finds matching shape keys": "Mọi bộ điều khiển bên dưới tìm được hình mẫu phù hợp",
    "An emotion wheel: joy, angry, sorrow, surprised, relaxed": "Bánh xe cảm xúc: vui, giận, buồn, ngạc nhiên, thư thái",
    "A five-point star for the vowels": "Ngôi sao năm cánh cho các nguyên âm",
    "Sliders to blink both eyes, the left eye and the right eye": "Thanh trượt để chớp cả hai mắt, mắt trái và mắt phải",
    "A joystick for animal ear shape keys": "Cần điều khiển cho hình mẫu tai thú",
    "A joystick for breathing, muscle and weight shape keys": "Cần điều khiển cho hình mẫu hơi thở, cơ bắp và cân nặng",
    "Cloth Wind": "Gió thổi vải",
    "A joystick for skirt and cape sway in four directions": "Cần điều khiển cho váy và áo choàng đung đưa theo bốn hướng",
    "Auto Setup added %d controllers": "Tự thiết lập đã thêm %d bộ điều khiển",
    "Generate 3D Rig Board": "Tạo bảng rig 3D",
    "Add a board next to the mesh with a frame and an empty handle per controller, as a start for a rig":
        "Thêm một bảng cạnh mesh, mỗi bộ điều khiển một khung và một tay cầm empty, làm điểm khởi đầu cho rig",
    "No controllers yet: run Auto Setup first": "Chưa có bộ điều khiển: hãy chạy Tự thiết lập trước",
    "Rig board with %d controllers added to collection %s": "Đã thêm bảng rig có %d bộ điều khiển vào bộ sưu tập %s",

    # bl_ui/dasktoon_shape_key_manager.py: expression operators
    "Add VRM Expression Set": "Thêm bộ biểu cảm VRM",
    "Add the VRM expression shape keys the mesh does not have yet, empty, ready to sculpt":
        "Thêm các hình mẫu biểu cảm VRM mà mesh chưa có, để trống, sẵn sàng điêu khắc",
    "The 18 VRM 0.x shape keys: joy, angry, a, i, u, blink…": "18 hình mẫu VRM 0.x: joy, angry, a, i, u, blink…",
    "The 18 VRM 1.0 shape keys: happy, sad, aa, ih, blinkLeft…": "18 hình mẫu VRM 1.0: happy, sad, aa, ih, blinkLeft…",
    "Added %d VRM shape keys": "Đã thêm %d hình mẫu VRM",
    "Split Left / Right": "Tách trái / phải",
    "Split a symmetric shape key into a left and a right shape key, blended across the middle of the mesh":
        "Tách một hình mẫu đối xứng thành hình mẫu trái và phải, hòa trộn ở giữa mesh",
    "Width of the blend across the middle of the mesh (X = 0)": "Độ rộng vùng hòa trộn ở giữa mesh (X = 0)",
    "Names like blink_L and blink_R": "Tên kiểu blink_L và blink_R",
    "Names like blinkLeft and blinkRight": "Tên kiểu blinkLeft và blinkRight",
    "Names like blink_l and blink_r": "Tên kiểu blink_l và blink_r",
    "Shape key %s not found": "Không tìm thấy hình mẫu %s",
    "Split %s into %s and %s": "Đã tách %s thành %s và %s",
    "Bake Expression to New Shape Key": "Bake biểu cảm thành hình mẫu mới",
    "Save the current mix of shape key values as a new shape key":
        "Lưu hỗn hợp giá trị hình mẫu hiện tại thành một hình mẫu mới",
    "Clear Values After Bake": "Xóa giá trị sau khi bake",
    "Baked %d shape keys into %s": "Đã bake %d hình mẫu vào %s",
    "Synthesize ARKit 52 from VRM": "Dựng ARKit 52 từ VRM",
    "Build the 52 ARKit face tracking shape keys from the VRM or VRoid shape keys of the mesh":
        "Dựng 52 hình mẫu theo dõi khuôn mặt ARKit từ các hình mẫu VRM hoặc VRoid của mesh",
    "Overwrite Existing": "Ghi đè cái đã có",
    "Built %d of the 52 ARKit shape keys": "Đã dựng %d trên 52 hình mẫu ARKit",
    "Remove Empty Shape Keys": "Xóa hình mẫu trống",
    "Remove the shape keys that move no vertex": "Xóa các hình mẫu không làm dịch chuyển đỉnh nào",
    "Removed %d empty shape keys": "Đã xóa %d hình mẫu trống",
    "Convert Naming": "Đổi chuẩn tên",
    "Rename shape keys from one naming standard to another (VRoid, VRM 0.x, VRM 1.0)":
        "Đổi tên hình mẫu từ chuẩn tên này sang chuẩn tên khác (VRoid, VRM 0.x, VRM 1.0)",
    "Conversion": "Chuyển đổi",
    "VRoid to VRM 0.x": "VRoid sang VRM 0.x",
    "Rename VRoid shape keys (Fcl_ALL_Joy…) to VRM 0.x names (joy…)":
        "Đổi tên hình mẫu VRoid (Fcl_ALL_Joy…) sang tên VRM 0.x (joy…)",
    "VRM 0.x to VRM 1.0": "VRM 0.x sang VRM 1.0",
    "Rename VRM 0.x shape keys (joy, blink_l…) to VRM 1.0 names (happy, blinkLeft…)":
        "Đổi tên hình mẫu VRM 0.x (joy, blink_l…) sang tên VRM 1.0 (happy, blinkLeft…)",
    "VRM 1.0 to VRM 0.x": "VRM 1.0 sang VRM 0.x",
    "Rename VRM 1.0 shape keys (happy, blinkLeft…) to VRM 0.x names (joy, blink_l…)":
        "Đổi tên hình mẫu VRM 1.0 (happy, blinkLeft…) sang tên VRM 0.x (joy, blink_l…)",
    "Renamed %d shape keys": "Đã đổi tên %d hình mẫu",
    "Live Preview": "Xem trước trực tiếp",
    "Play a blink, speech or emotion test on the mesh in a loop, until Esc or right click":
        "Phát thử chớp mắt, nói hoặc cảm xúc trên mesh theo vòng lặp, đến khi bấm Esc hoặc chuột phải",
    "Blink every few seconds": "Chớp mắt vài giây một lần",
    "Say the vowels A, I, U, E, O in a loop": "Đọc lần lượt các nguyên âm A, I, U, E, O theo vòng lặp",
    "Go through joy, surprise, sorrow and anger in a loop": "Lần lượt vui, ngạc nhiên, buồn, giận theo vòng lặp",
    "Live preview running: press Esc or right click to stop": "Đang xem trước trực tiếp: bấm Esc hoặc chuột phải để dừng",
    "Live preview stopped": "Đã dừng xem trước trực tiếp",
    "Test Expression on Model": "Thử biểu cảm trên model",
    "Show this expression on the mesh: its shape keys go to the intensity, all others to 0":
        "Hiện biểu cảm này trên mesh: các hình mẫu của nó lấy giá trị cường độ, mọi hình mẫu khác về 0",
    "Showing %s: %s": "Đang hiện %s: %s",
    "No shape key of the mesh matches %s: add a VRM expression set first":
        "Không có hình mẫu nào của mesh khớp với %s: hãy thêm bộ biểu cảm VRM trước",
    "Add ARKit 52 Placeholders": "Thêm 52 hình mẫu ARKit trống",
    "Add the 52 ARKit shape keys the mesh does not have yet, empty, ready to sculpt":
        "Thêm các hình mẫu ARKit 52 mà mesh chưa có, để trống, sẵn sàng điêu khắc",
    "Added %d ARKit shape keys to %s": "Đã thêm %d hình mẫu ARKit vào %s",
    "Test ARKit Shape on Model": "Thử hình mẫu ARKit trên model",
    "Show this ARKit shape key on the mesh: it goes to the intensity, all others to 0":
        "Hiện hình mẫu ARKit này trên mesh: nó lấy giá trị cường độ, mọi hình mẫu khác về 0",
    "Showing %s": "Đang hiện %s",
    "Shape key %s not found: synthesize ARKit 52 first": "Không tìm thấy hình mẫu %s: hãy dựng ARKit 52 trước",

    # bl_ui/dasktoon_shape_key_manager.py: VRM reference cards
    "Joy": "Vui vẻ",
    "Mouth Corners and Eyes": "Khóe miệng và mắt",
    "A bright smile: the mouth corners pull out and up, and the lower eyelids push up into smiling half-moon eyes.":
        "Nụ cười tươi tắn: khóe miệng kéo sang hai bên và chếch lên trên, mí mắt dưới đẩy nhẹ tạo mắt cười hình bán "
        "nguyệt.",
    "Angry": "Tức giận",
    "Brows and Mouth Corners": "Lông mày và khóe môi",
    "Anger: the inner ends of the brows drop and press toward the nose, the eyes narrow hard and the mouth corners turn "
    "down.":
        "Biểu cảm tức giận: hai đầu lông mày hạ thấp và ép sát vào sống mũi, mí mắt nheo gắt, khóe môi chúc xuống.",
    "Sorrow": "Buồn bã",
    "Brows and Lower Lip": "Lông mày và môi dưới",
    "Sadness: the inner ends of the brows rise into a slant, the mouth corners droop and the gaze falls.":
        "Biểu cảm buồn bã: hai đầu lông mày nâng cao chếch xuống hai bên, khóe miệng trễ xuống, ánh mắt rũ.",
    "Surprised": "Kinh ngạc",
    "Wide Eyes and O Mouth": "Mắt mở to và miệng chữ O",
    "Surprise: the eyes open as wide as they go, the pupils shrink a little, the brows rise high and the mouth opens "
    "into an O.":
        "Biểu cảm sửng sốt: hai mắt mở to hết cỡ, đồng tử co nhẹ, lông mày nhướng cao, miệng há hình chữ O.",
    "Relaxed": "Thư thái",
    "Curved Closed Eyes and Soft Smile": "Mắt cong nhắm và nụ cười nhẹ",
    "Contentment: the eyes close into curves (^ ^) and the mouth corners smile softly.":
        "Biểu cảm an tâm, dễ chịu: hai mắt nhắm cong (^ ^), khóe miệng mỉm cười nhẹ nhàng.",
    "Viseme A": "Khẩu hình A",
    "Jaw Lowered, Mouth Open Tall": "Cằm hạ thấp, há miệng dọc",
    "Mouth shape for 'A': the jaw drops and the mouth opens tall, showing the upper front teeth and the tongue.":
        "Khẩu hình phát âm 'A': cằm hạ thấp xuống, miệng mở dọc tự nhiên để lộ răng cửa trên và lưỡi.",
    "Viseme I": "Khẩu hình I",
    "Lips Pulled Wide, Teeth Showing": "Kéo ngang môi, lộ răng",
    "Mouth shape for 'I': both mouth corners stretch sideways, showing both rows of teeth.":
        "Khẩu hình phát âm 'I': hai khóe miệng kéo căng sang hai bên theo chiều ngang, để lộ hai hàm răng.",
    "Viseme U": "Khẩu hình U",
    "Small Pursed Lips": "Chu môi nhỏ",
    "Mouth shape for 'U': both lips purse forward into a small circle and the cheeks draw in a little.":
        "Khẩu hình phát âm 'U': môi trên và môi dưới chu tròn nhỏ về phía trước, hai má hơi hóp lại.",
    "Viseme E": "Khẩu hình E",
    "Mouth Half Open": "Miệng mở vừa phải",
    "Mouth shape for 'E': the mouth corners open moderately and the upper lip arches a little.":
        "Khẩu hình phát âm 'E': khóe miệng mở rộng vừa phải, môi trên hơi cong lên tạo hình vòm.",
    "Viseme O": "Khẩu hình O",
    "Round Mouth": "Miệng tròn",
    "Mouth shape for 'O': the mouth opens round like an egg and the lips push forward a little.":
        "Khẩu hình phát âm 'O': miệng mở tròn như quả trứng, môi hơi chìa ra phía trước.",
    "Blink Both Eyes": "Chớp cả hai mắt",
    "Upper Eyelids": "Mí mắt trên",
    "A full blink: the upper eyelids close all the way onto the lower ones and the lashes fold naturally.":
        "Chớp mắt hoàn toàn: mí mắt trên hạ sát hoàn toàn xuống mí dưới, lông mi cụp tự nhiên.",
    "Wink Left": "Nháy mắt trái",
    "Left Eye": "Mắt bên trái",
    "Only the left eye closes in a playful wink; the right eye stays wide open.":
        "Chỉ có mắt bên trái nhắm lại tạo dáng nháy mắt tinh nghịch, mắt bên phải vẫn mở to.",
    "Wink Right": "Nháy mắt phải",
    "Right Eye": "Mắt bên phải",
    "Only the right eye closes; the left eye stays open as usual.":
        "Chỉ có mắt bên phải nhắm lại, mắt bên trái vẫn mở to bình thường.",
    "Cheek Puff": "Phồng má",
    "Both Cheeks": "Hai bên má",
    "Both cheeks puff out, as if holding air or sulking.": "Phồng căng hai bên má ra ngoài như đang ngậm hơi hoặc hờn dỗi.",

    # bl_ui/dasktoon_shape_key_manager.py: ARKit reference
    "Left Eyelid": "Mí mắt trái",
    "Right Eyelid": "Mí mắt phải",
    "Closes the left upper eyelid fully onto the lower one.": "Nhắm mí mắt trên bên trái hoàn toàn chạm mí dưới.",
    "Closes the right upper eyelid fully onto the lower one.": "Nhắm mí mắt trên bên phải hoàn toàn chạm mí dưới.",
    "Left Pupil": "Đồng tử trái",
    "Right Pupil": "Đồng tử phải",
    "Turns the left eye up.": "Đồng tử mắt trái liếc lên trên.",
    "Turns the right eye up.": "Đồng tử mắt phải liếc lên trên.",
    "Turns the left eye down.": "Đồng tử mắt trái liếc cụp xuống dưới.",
    "Turns the right eye down.": "Đồng tử mắt phải liếc cụp xuống dưới.",
    "Turns the left eye in, toward the nose.": "Đồng tử mắt trái liếc vào trong sống mũi.",
    "Turns the right eye in, toward the nose.": "Đồng tử mắt phải liếc vào trong sống mũi.",
    "Turns the left eye out, toward the temple.": "Đồng tử mắt trái liếc ra ngoài thái dương.",
    "Turns the right eye out, toward the temple.": "Đồng tử mắt phải liếc ra ngoài thái dương.",
    "Left Eye Squint": "Nheo mắt trái",
    "Right Eye Squint": "Nheo mắt phải",
    "Pushes the left lower eyelid up, as in a smiling squint.": "Mí dưới mắt trái đẩy nhẹ lên trên như đang nheo mắt cười.",
    "Pushes the right lower eyelid up, as in a smiling squint.": "Mí dưới mắt phải đẩy nhẹ lên trên như đang nheo mắt cười.",
    "Left Eye Wide": "Trợn mắt trái",
    "Right Eye Wide": "Trợn mắt phải",
    "Opens the left upper eyelid as wide as it goes.": "Mí mắt trên bên trái mở to căng hết cỡ.",
    "Opens the right upper eyelid as wide as it goes.": "Mí mắt trên bên phải mở to căng hết cỡ.",
    "Jaw Open": "Mở cằm dọc",
    "Drops the jaw to open the mouth wide.": "Cằm hạ thấp xuống để há miệng lớn.",
    "Jaw Forward": "Đưa cằm ra trước",
    "Pushes the lower jaw forward.": "Xương cằm dưới đẩy tịnh tiến ra phía trước.",
    "Jaw Left": "Lệch cằm trái",
    "Slides the lower jaw to the left.": "Cằm dưới trượt sang bên trái.",
    "Jaw Right": "Lệch cằm phải",
    "Slides the lower jaw to the right.": "Cằm dưới trượt sang bên phải.",
    "Lips Closed": "Khép môi",
    "Presses the lips together while the jaw is open.": "Hai môi ép chặt vào nhau khi cằm đang há.",
    "Lip Funnel": "Mở phễu",
    "Opens the lips into a round funnel, as in a loud 'U'.": "Môi mở tròn hình phễu như đang nói chữ 'U' to.",
    "Lip Pucker": "Chu môi",
    "Puckers the lips forward into a small round shape, as for a kiss.":
        "Hai môi chu tròn nhỏ nhô về phía trước, như khi hôn.",
    "Mouth Left": "Kéo mép trái",
    "Slides the whole mouth to the left.": "Toàn bộ vòm môi trượt sang bên trái.",
    "Mouth Right": "Kéo mép phải",
    "Slides the whole mouth to the right.": "Toàn bộ vòm môi trượt sang bên phải.",
    "Left Smile": "Cười mép trái",
    "Right Smile": "Cười mép phải",
    "Pulls the left mouth corner out and up.": "Khóe môi trái kéo sang bên và chếch lên trên.",
    "Pulls the right mouth corner out and up.": "Khóe môi phải kéo sang bên và chếch lên trên.",
    "Left Frown": "Mếu mép trái",
    "Right Frown": "Mếu mép phải",
    "Pulls the left mouth corner down.": "Khóe môi trái kéo chúc xuống dưới.",
    "Pulls the right mouth corner down.": "Khóe môi phải kéo chúc xuống dưới.",
    "Left Dimple": "Lúm đồng tiền trái",
    "Right Dimple": "Lúm đồng tiền phải",
    "Pulls the left mouth corner back into the cheek, making a dimple.": "Khóe môi trái kéo lùi nhẹ vào má tạo vết lúm.",
    "Pulls the right mouth corner back into the cheek, making a dimple.": "Khóe môi phải kéo lùi nhẹ vào má tạo vết lúm.",
    "Left Stretch": "Kéo căng mép trái",
    "Right Stretch": "Kéo căng mép phải",
    "Stretches the left mouth corner sideways, as for 'I'.": "Khóe miệng trái kéo căng ngang sang bên, như khi phát âm 'I'.",
    "Stretches the right mouth corner sideways, as for 'I'.":
        "Khóe miệng phải kéo căng ngang sang bên, như khi phát âm 'I'.",
    "Lower Lip Roll": "Cuộn môi dưới",
    "Upper Lip Roll": "Cuộn môi trên",
    "Rolls the lower lip in over the teeth.": "Môi dưới cuộn tròn vào trong mép răng.",
    "Rolls the upper lip in over the teeth.": "Môi trên cuộn tròn vào trong mép răng.",
    "Lower Lip Shrug": "Đẩy môi dưới",
    "Pushes the lower lip up.": "Môi dưới đẩy nhếch lên trên.",
    "Upper Lip Shrug": "Đẩy môi trên",
    "Lifts the upper lip a little.": "Môi trên nhếch nhẹ lên trên.",
    "Left Lip Press": "Ép mép trái",
    "Right Lip Press": "Ép mép phải",
    "Presses the left side of the lips flat together.": "Môi bên trái ép dẹt chặt vào nhau.",
    "Presses the right side of the lips flat together.": "Môi bên phải ép dẹt chặt vào nhau.",
    "Left Lower Lip Down": "Hạ môi dưới trái",
    "Right Lower Lip Down": "Hạ môi dưới phải",
    "Pulls the left side of the lower lip down, showing the lower teeth.":
        "Phần môi dưới bên trái kéo hạ xuống để lộ răng dưới.",
    "Pulls the right side of the lower lip down, showing the lower teeth.":
        "Phần môi dưới bên phải kéo hạ xuống để lộ răng dưới.",
    "Left Upper Lip Up": "Nâng môi trên trái",
    "Right Upper Lip Up": "Nâng môi trên phải",
    "Lifts the left side of the upper lip, showing the upper teeth.": "Phần môi trên bên trái kéo nâng lên để lộ răng trên.",
    "Lifts the right side of the upper lip, showing the upper teeth.":
        "Phần môi trên bên phải kéo nâng lên để lộ răng trên.",
    "Left Brow Down": "Hạ mày trái",
    "Right Brow Down": "Hạ mày phải",
    "Lowers the inner end of the left brow toward the nose.": "Đầu lông mày trái hạ thấp và ép sát vào sống mũi.",
    "Lowers the inner end of the right brow toward the nose.": "Đầu lông mày phải hạ thấp và ép sát vào sống mũi.",
    "Inner Brows Up": "Nhướng lông mày giữa",
    "Raises the inner ends of both brows, looking sad or surprised.":
        "Hai đầu lông mày giữa nhướng cao tạo vẻ buồn bã hoặc ngạc nhiên.",
    "Left Outer Brow Up": "Nhướng đuôi mày trái",
    "Right Outer Brow Up": "Nhướng đuôi mày phải",
    "Raises the outer end of the left brow.": "Đuôi ngoài lông mày trái nâng cao lên trên.",
    "Raises the outer end of the right brow.": "Đuôi ngoài lông mày phải nâng cao lên trên.",
    "Puffs both cheeks out.": "Hai bên má phồng căng tròn ra ngoài.",
    "Left Cheek Raise": "Nâng má trái",
    "Right Cheek Raise": "Nâng má phải",
    "Raises the left cheek, pushing the lower eyelid up.": "Khối cơ má trái nâng cao đẩy mí mắt dưới lên.",
    "Raises the right cheek, pushing the lower eyelid up.": "Khối cơ má phải nâng cao đẩy mí mắt dưới lên.",
    "Left Nose Sneer": "Nhăn mũi trái",
    "Right Nose Sneer": "Nhăn mũi phải",
    "Wrinkles the left side of the nose up.": "Cánh mũi trái co nhăn lên trên.",
    "Wrinkles the right side of the nose up.": "Cánh mũi phải co nhăn lên trên.",
    "Tongue Out": "Thè lưỡi",
    "Sticks the tip of the tongue out past the lips.": "Đầu lưỡi thò ra ngoài môi.",

    # bl_ui/dasktoon_project.py and dasktoon_project/project.py
    "New Project…": "Tạo dự án…",
    "Open Project…": "Mở dự án…",
    "No recent projects": "Chưa có dự án gần đây",
    "No recent models or projects": "Chưa có model hay dự án gần đây",
    "Projects": "Dự án",
    "Models": "Các model",
    "Shaders: version %d": "Shader: phiên bản %d",
    "Shaders: not installed": "Shader: chưa cài",
    "Unity Project": "Project Unity",
    "Created project %s": "Đã tạo dự án %s",
    "Opened project %s": "Đã mở dự án %s",
    "Export This Model": "Xuất model này",
    "Export this file's model, materials and shaders straight into the project's Unity project":
        "Xuất model, material và shader của file này thẳng vào project Unity của dự án",
    "This file has no object to export": "File không có object nào để xuất",
    "Reinstall Shaders": "Cài lại shader",
    "Write the DaskToon shaders into the project's Unity project again":
        "Ghi lại shader DaskToon vào project Unity của dự án",
    "Reinstalled the shaders into %s": "Đã cài lại shader vào %s",
    "Open Project Folder": "Mở thư mục dự án",
    "Open the project folder in the file manager": "Mở thư mục dự án trong trình quản lý file",
    "No DaskToon project is open": "Chưa mở dự án DaskToon nào",
    "%s: project version %r is not supported": "%s: phiên bản dự án %r không được hỗ trợ",
    "Engine %s is not supported yet": "Engine %s chưa được hỗ trợ",
    "%s is not a Unity project (it needs Assets/ and ProjectSettings/)":
        "%s không phải project Unity (cần có Assets/ và ProjectSettings/)",
    "%s is already a DaskToon project": "%s đã là một dự án DaskToon",
    "The name is empty": "Tên đang để trống",
    "The project already has a model named %s": "Dự án đã có model tên %s",
    "New Project": "Tạo dự án",
    "Create a DaskToon project: a folder with Models/ and Textures/; link a Unity project now or later":
        "Tạo dự án DaskToon: một thư mục có Models/ và Textures/; gắn project Unity ngay hoặc để sau",
    "The folder that receives the project folder": "Thư mục sẽ chứa thư mục dự án",
    "Optional: the Unity project models are exported to (link it later in Project Settings)":
        "Không bắt buộc: project Unity nhận model khi xuất (có thể gắn sau trong Cài đặt dự án)",
    "Open Project": "Mở dự án",
    "Open a DaskToon project (its dasktoon_project.json or its folder) and show its models on the start screen":
        "Mở một dự án DaskToon (file dasktoon_project.json hoặc thư mục của nó) và hiện các model của nó ở màn hình đầu",
    "%s is not a DaskToon project": "%s không phải dự án DaskToon",
    "Choose Project": "Chọn dự án",
    "Choose this project: the start screen shows its models": "Chọn dự án này: màn hình đầu hiện các model của nó",
    "Project Settings": "Cài đặt dự án",
    "Project Settings…": "Cài đặt dự án…",
    "Rename the project and link it to a Unity project; the DaskToon shaders are installed when the link is new or changes":
        "Đổi tên dự án và gắn với một project Unity; shader DaskToon được cài khi gắn mới hoặc đổi project",
    "The Unity project models are exported to; leave empty to unlink":
        "Project Unity nhận model khi xuất; để trống để bỏ gắn",
    "Saved the settings of project %s": "Đã lưu cài đặt của dự án %s",
    "Project %s is not linked to a Unity project yet: link it in Project Settings":
        "Dự án %s chưa gắn với project Unity: hãy gắn trong Cài đặt dự án",
    "Open this model of the project (DaskToon asks to save the current file first when it has changes)":
        "Mở model này của dự án (DaskToon hỏi lưu file hiện tại trước nếu file có thay đổi)",
    "File not found: %s": "Không tìm thấy file: %s",
    "Create or open a project": "Hãy tạo hoặc mở một dự án",
    "No models yet": "Chưa có model nào",
    "Engine: not linked": "Engine: chưa gắn",
    "Draft (not in a project)": "Bản nháp (chưa thuộc dự án)",

    # dasktoon_project/textures.py
    "Copied 1 texture into Textures/": "Đã chép 1 texture vào Textures/",
    "Copied %d textures into Textures/": "Đã chép %d texture vào Textures/",
    "%s: image sequences are not copied into the project": "%s: chuỗi ảnh không được chép vào dự án",
    "%s: file not found: %s": "%s: không tìm thấy file: %s",

    # bl_ui/dasktoon_model.py
    "New Model": "Tạo model",
    "New Model…": "Tạo model…",
    "Create a model in the selected project: Models/<name>.blend, saved at once and opened":
        "Tạo model trong dự án đang chọn: Models/<tên>.blend, được lưu ngay và mở ra",
    "Start From": "Bắt đầu từ",
    "DaskToon Scene": "Cảnh DaskToon",
    "An empty scene with a Sun, a camera looking at the origin, the DaskToon Anime engine and the Standard view":
        "Cảnh trống có một Sun, một camera nhìn vào gốc tọa độ, engine DaskToon Anime và view Standard",
    "A completely empty scene": "Cảnh trống hoàn toàn",
    "Current Scene": "Cảnh hiện tại",
    "Save the scene that is open now as the new model": "Lưu cảnh đang mở làm model mới",
    "Copy of Model": "Bản sao của model",
    "Start from a copy of another model of the project": "Bắt đầu từ bản sao của một model khác trong dự án",
    "Create or open a project first": "Hãy tạo hoặc mở một dự án trước",
    "Choose the model to copy": "Hãy chọn model để sao chép",
    "Created model %s": "Đã tạo model %s",
    "Finish New Model": "Hoàn tất tạo model",
    "Finish New Model once the startup file or the model to copy has been read":
        "Hoàn tất tạo model sau khi đã đọc file khởi động hoặc model cần sao chép",
    "Image %s has unsaved paint changes: save it with Image › Save":
        "Ảnh %s có nét vẽ chưa lưu: hãy lưu bằng Image › Save",
    "Open a model, a .blend file from outside any project (as a draft), or a project":
        "Mở một model, một file .blend ngoài mọi dự án (làm bản nháp), hoặc một dự án",
    "Save this model in its project, copying textures from outside into Textures/ first; a draft is saved into a project":
        "Lưu model này vào dự án của nó, chép trước texture ở ngoài vào Textures/; bản nháp thì được lưu vào một dự án",
    "Save to Project": "Lưu vào dự án",
    "Save this draft as a new model of a project; the file it came from is not changed":
        "Lưu bản nháp này thành model mới của một dự án; file gốc không bị thay đổi",
    "Choose a project": "Hãy chọn một dự án",
    "Saved model %s in project %s": "Đã lưu model %s vào dự án %s",
    "Save Model As": "Lưu model thành",
    "Save this model under a new name in its project's Models/ folder and keep working on the new file":
        "Lưu model này với tên mới trong thư mục Models/ của dự án và làm việc tiếp trên file mới",
    "Saved as model %s": "Đã lưu thành model %s",
    "Write a copy of this model into its project's Models/ folder and keep working on this file":
        "Ghi bản sao của model này vào thư mục Models/ của dự án và làm việc tiếp trên file này",
    "Saved a copy as model %s": "Đã lưu bản sao thành model %s",
    "Save this model as the next numbered file next to it (Hero.blend gives Hero_001.blend) and keep working on that one":
        "Lưu model này thành file đánh số tiếp theo cạnh nó (Hero.blend thành Hero_001.blend) và làm việc tiếp trên file đó",

    # bl_ui/dasktoon_splash.py, and DaskToon's parts of space_topbar.py and bl_operators/wm.py
    "%d more in File › Models": "còn %d model trong File › Models",
    "Continue as Draft": "Tiếp tục với bản nháp",
    "Close the start screen and keep working on the open scene as a draft, outside any project":
        "Đóng màn hình đầu và làm tiếp trên cảnh đang mở như một bản nháp, ngoài mọi dự án",
    "Open…": "Mở…",
    "Save Model As…": "Lưu model thành…",
    "Save Copy…": "Lưu bản sao…",

    # bl_ui/dasktoon_shading_styles.py
    "Shading Style": "Kiểu đổ bóng",
    "Anime 2-Tone": "Anime 2 tông",
    "Anime 3-Tone": "Anime 3 tông",
    "Soft Painted": "Mềm như vẽ",
    "Anime Skin (Warm Edge)": "Da anime (viền ấm)",
    "Apply Shading Style": "Áp kiểu đổ bóng",
    "Apply a shading style to the node's ramp": "Áp một kiểu đổ bóng vào dải màu của node",
    "Node or style not found": "Không tìm thấy node hoặc kiểu",
    "Save My Style": "Lưu kiểu của tôi",
    "Save the current ramp as one of your own styles (shared by every file)":
        "Lưu dải màu hiện tại thành một kiểu của bạn (dùng chung cho mọi file)",
    "Style Name": "Tên kiểu",
    "Select a DaskToon node that uses a shading ramp": "Hãy chọn một node DaskToon đang dùng dải đổ bóng",
    "The name is empty or the same as a built-in style": "Tên trống hoặc trùng với kiểu có sẵn",
    "Style %s already exists: turn on Overwrite Existing to replace it":
        "Kiểu %s đã có: bật Ghi đè cái đã có để thay",
    "Saved style %s": "Đã lưu kiểu %s",
    "Delete Style": "Xóa kiểu",
    "Delete one of your own shading styles": "Xóa một kiểu đổ bóng của bạn",
    "Style %s not found": "Không tìm thấy kiểu %s",
    "Convert from Simple": "Chuyển từ Đơn giản",
    "Create a ramp that approximates the current Simple sliders":
        "Tạo một dải màu gần đúng với các thanh trượt Đơn giản hiện tại",
    "Select a DaskToon node": "Hãy chọn một node DaskToon",
    "Made a ramp close to the current sliders": "Đã tạo dải màu gần đúng với các thanh trượt hiện tại",

    # bl_ui/dasktoon_upgrade.py
    "Anime Cel: %d nodes switched to Ambient HUE_SAT / Light MULTIPLY (closest to the old look)":
        "Anime Cel: %d node chuyển sang Ambient HUE_SAT / Light MULTIPLY (gần cách cũ nhất)",
    "Skipped %s (data linked from a library)": "Bỏ qua %s (dữ liệu link từ thư viện)",
    "Conflict: %s shares material %s; kept the settings of %s":
        "Xung đột: %s dùng chung material %s; giữ thiết lập của %s",
    "Upgraded the outline of %s": "Đã nâng cấp outline của %s",
    "Removed %d extra slots and %d _DaskOutline materials": "Đã dọn %d slot thừa và %d material _DaskOutline",
    "DaskToon upgraded the file: %s": "DaskToon đã nâng cấp file: %s",
    "nothing": "không có gì",

    # dasktoon_export: engines, warnings and skip reasons
    "Unreal 5 (coming soon)": "Unreal 5 (sắp có)",
    "Godot 4 (coming soon)": "Godot 4 (sắp có)",
    "Not supported yet": "Chưa hỗ trợ",
    "%s: cannot read the normal map image %s; normal map left out":
        "%s: không đọc được ảnh normal map %s; bỏ normal map",
    "%s › %s: bake failed (%s); using its value": "%s › %s: bake lỗi (%s); dùng giá trị đang đặt",
    "%s › %s: baked on the mesh of %s; the other meshes share this texture":
        "%s › %s: bake trên mesh của %s, các mesh khác dùng chung texture này",
    "Not in the FBX: %s (not in the current view layer, for example in an excluded collection)":
        "Không đưa vào FBX: %s (không nằm trong view layer hiện tại, ví dụ collection bị loại trừ)",
    "Skipped %s: the file already exists and was not made by DaskToon":
        "Bỏ qua %s: file đã có sẵn và không do DaskToon tạo",
    "Mesh %s has no UV map to bake": "Mesh %s không có UV map để bake",
    "%s: mesh linked from a library, face shading not written":
        "%s: mesh link từ thư viện, không ghi được bóng mặt",
    "%s: unusual custom normals, face shading not written": "%s: custom normal kiểu lạ, không ghi được bóng mặt",
    "%s: modifier %s changes the vertex count before Face Shading; apply it before exporting. Face shading not written":
        "%s: modifier %s đổi số đỉnh trước Face Shading; hãy Apply trước khi xuất, bóng mặt chưa được ghi",
    "%s: mesh linked from a library, outline data not written":
        "%s: mesh link từ thư viện, không ghi được dữ liệu outline",
    "%s: outline data not written (%s)": "%s: không ghi được dữ liệu outline (%s)",
    "%s: modifiers %s are not applied in the FBX; apply them before exporting if needed":
        "%s: modifier %s không được áp dụng vào FBX; hãy Apply trước khi xuất nếu cần",
    "a branch with a shader (%s)": "nhánh chứa shader (%s)",
    "a branch that depends on light or view (%s)": "nhánh phụ thuộc ánh sáng hoặc góc nhìn (%s)",
    "a branch that depends on the view (%s › %s)": "nhánh phụ thuộc góc nhìn (%s › %s)",
    "node group %s depends on light or view": "node group %s phụ thuộc ánh sáng hoặc góc nhìn",
    "%s: this input takes no texture in Unity; using its value":
        "%s: input này không nhận texture trong Unity; dùng giá trị đang đặt",
    "%s: %s; using its value": "%s: %s; dùng giá trị đang đặt",
    "%s › Normal Map: Strength is linked; using its value":
        "%s › Normal Map: Strength có nối node; dùng giá trị đang đặt",
    "%s › Normal: only a Normal Map (Tangent) fed by an Image Texture is supported; using the mesh normals":
        "%s › Normal: chỉ hỗ trợ Normal Map (Tangent) nối từ Image Texture; dùng normal của mesh",
    "%s › UV Vector: only the first UV map is supported; Unity uses uv0":
        "%s › UV Vector: chỉ hỗ trợ UV map đầu tiên; Unity dùng uv0",
    "%s › Emission Strength: linked; using its value": "%s › Emission Strength: có nối node; dùng giá trị đang đặt",
    "%s › Angel Ring › Normal: Unity uses the surface normal": "%s › Angel Ring › Normal: Unity dùng normal của bề mặt",
    "%s: the meshes using this material have a different UV order; Unity uses the order of %s":
        "%s: các mesh dùng material này có thứ tự UV khác nhau; Unity dùng thứ tự của %s",
    "%s: the mesh has no %s (or more than 8 UV maps); the outline in Unity follows the mesh normals":
        "%s: mesh chưa có %s (hoặc vượt 8 UV map); outline trong Unity đẩy theo normal của mesh",
    "%s: %s has no Dask Outline node; outline off": "%s: %s thiếu node Dask Outline; tắt outline",
    "empty slot": "slot trống",
    "Material Output › Surface is not linked": "Material Output › Surface không nối với node nào",
    "node setup not supported (%s)": "mẫu node chưa được hỗ trợ (%s)",

    # dasktoon_export/report.py
    "Shaders: installed or updated": "Shader: đã cài hoặc cập nhật",
    "Shaders: the project already has a recent enough version, not written again":
        "Shader: project đã có bản đủ mới, không ghi lại",
    "Shaders: not exported (material export is off)": "Shader: không xuất (đã tắt xuất material)",
    "Engine Export: %d materials, %s, %d warnings": "Xuất sang engine: %d material, %s, %d cảnh báo",
    "with FBX": "có FBX",
    "no model": "không có model",
    "written straight into the Unity project": "ghi thẳng vào project Unity",
    "a folder to drag into Unity": "thư mục để kéo vào Unity",
    "Destination: %s (%s)": "Đích: %s (%s)",
    "Model: %s": "Mô hình: %s",
    "Exported materials (%d): %s": "Material đã xuất (%d): %s",
    "none": "không có",
    "Skipped material %s: %s (Unity keeps the default material of the FBX)":
        "Bỏ qua material %s: %s (Unity giữ material mặc định của FBX)",
    "Baked: %s": "Đã bake: %s",
    "Wrote DT_OutlineN/W for: %s": "Đã ghi DT_OutlineN/W cho: %s",
    "Face shading: wrote the egg proxy normals (rest pose) for: %s; blend shapes in the FBX do not change normals":
        "Bóng mặt: đã ghi normal khối trứng (tư thế nghỉ) cho: %s; blend shape trong FBX không đổi normal",
    "Warning: %s": "Cảnh báo: %s",
    "The Unity project must use the Linear color space (the URP default).":
        "Project Unity phải dùng Linear color space (mặc định của URP).",
    "Exporting again overwrites any manual edits to these assets in Unity.":
        "Xuất lại sẽ ghi đè mọi chỉnh sửa tay trên các asset này trong Unity.",
    "Suggested light: Sun %s → Directional %.3f": "Đèn gợi ý: Sun %s → Directional %.3f",
    "Suggested light: the scene has no Sun; Unity Directional = Sun strength ÷ π":
        "Đèn gợi ý: scene không có Sun; Directional của Unity = Sun strength ÷ π",
    "Ambient: the World is not a single color; set Environment Lighting in Unity yourself":
        "Ambient: World không phải một màu đơn; tự đặt Environment Lighting trong Unity",
    "Suggested ambient (Environment Lighting › Source: Color): #%s (linear %.3f, %.3f, %.3f)":
        "Ambient gợi ý (Environment Lighting › Source: Color): #%s (linear %.3f, %.3f, %.3f)",
    "DaskToon Engine Export": "DaskToon: Xuất sang engine",
    "DaskToon Engine Export: %s": "DaskToon: Xuất sang engine: %s",
    "How to use (Unity 6, URP 17.5):": "Cách dùng (Unity 6, URP 17.5):",
    "1. Drag the whole %s_Unity folder into the Project window of Unity.":
        "1. Kéo cả thư mục %s_Unity vào cửa sổ Project của Unity.",
    "2. The project must use the Linear color space (Project Settings › Player › Other Settings › Color Space).":
        "2. Project phải dùng Linear color space (Project Settings › Player › Other Settings › Color Space).",
    "3. Set the Directional Light and the Ambient as suggested below.":
        "3. Đặt Directional Light và Ambient theo gợi ý bên dưới.",
    "Note: drag the folder of a second character into the same project and Unity reports a duplicate GUID for the "
    "Shaders folder.":
        "Lưu ý: kéo thư mục của nhân vật thứ hai vào cùng project, Unity sẽ báo trùng GUID của thư mục Shaders.",
    "The materials still work. To avoid it, choose the Unity project folder itself when exporting, or use a DaskToon "
    "Project.":
        "Material vẫn chạy đúng. Để tránh, hãy chọn thẳng thư mục project Unity khi xuất, hoặc dùng Dự án DaskToon.",
    "… the full report is in the Text %s": "… xem đầy đủ trong Text %s",

    # DaskToon nodes (C++) and the DaskToon Anime / DaskToon Manga Add menus: names
    "Master Shaders": "Shader chính",
    "Anime Materials": "Vật liệu anime",
    "Modular Pipeline": "Quy trình mô-đun",
    "Character Features": "Đặc điểm nhân vật",
    "Outline & Inking": "Viền và mực",
    "Screentones & Hatching": "Tram và gạch",
    "Inking & Pen": "Mực và bút",
    "Anime Wood": "Gỗ anime",
    "Anime Metal": "Kim loại anime",
    "Anime Metal / Armor": "Kim loại / giáp anime",
    "Anime Fabric": "Vải anime",
    "Anime Fabric / Cloth": "Vải anime",
    "Anime Tights & Fishnet": "Quần tất và lưới anime",
    "Anime Knit & Wool": "Len đan anime",
    "Anime Glass": "Kính anime",
    "Anime Glass & Gem": "Kính và đá quý anime",
    "Anime Water": "Nước anime",
    "Anime Water & Liquid": "Nước và chất lỏng anime",
    "Angel Ring": "Vòng thiên thần",
    "Face Shadow": "Bóng đổ trên mặt",
    "Anime Eye": "Mắt anime",
    "Warm/Cool Grade": "Chỉnh màu ấm/lạnh",
    "Classic Cel": "Cel cổ điển",
    "Anime Rim": "Viền sáng anime",
    "Cross-Hatching": "Gạch chéo",
    "Screentone": "Tram",
    "Speed Lines": "Nét tốc độ",

    # DaskToon nodes (C++): sockets
    "1st Tone Color": "Màu tông 1",
    "2nd Tone Color": "Màu tông 2",
    "AO Color": "Màu AO",
    "AO Darkness": "Độ tối AO",
    "AO Mask": "Mặt nạ AO",
    "Ambient": "Môi trường",
    "Ambient Blend": "Hòa trộn môi trường",
    "Ambient Factor": "Hệ số môi trường",
    "Ambient Shadow Only": "Chỉ bóng môi trường",
    "Anisotropy Angle": "Góc dị hướng",
    "Anisotropy Strength": "Độ mạnh dị hướng",
    "Band Position": "Vị trí dải",
    "Band Softness": "Độ mềm dải",
    "Base Width": "Độ dày cơ sở",
    "Bottom Glow Color": "Màu sáng đáy",
    "Bottom Glow Power": "Độ mạnh sáng đáy",
    "Caustics Color": "Màu tụ quang",
    "Caustics Scale": "Tỉ lệ tụ quang",
    "Caustics Speed": "Tốc độ tụ quang",
    "Cel Shading": "Đổ bóng cel",
    "Center X": "Tâm X",
    "Center Y": "Tâm Y",
    "Color Grade": "Chỉnh màu",
    "Crease Darkness": "Độ tối nếp gấp",
    "Crevice AO": "AO khe kẽ",
    "Cross Angle": "Góc nét chéo",
    "Crystal Tint": "Sắc pha lê",
    "Curvature Accent": "Nhấn độ cong",
    "Curve Exponent": "Số mũ đường cong",
    "Custom Outline Color": "Màu viền tùy chọn",
    "Darkness": "Độ tối",
    "Deep Color": "Màu chỗ sâu",
    "Denier Falloff": "Suy giảm denier",
    "Depth Fade": "Mờ theo độ sâu",
    "Depth Info": "Thông tin độ sâu",
    "Depth Map": "Bản đồ độ sâu",
    "Depth Steepness": "Độ dốc theo độ sâu",
    "Dispersion Power": "Độ mạnh tán sắc",
    "Dot Angle": "Góc chấm",
    "Dot Scale": "Tỉ lệ chấm",
    "Dot Sharpness": "Độ sắc chấm",
    "Edge Wear": "Mòn cạnh",
    "Face Map": "Bản đồ mặt",
    "Far Distance": "Khoảng cách xa",
    "Fishnet Distortion": "Độ méo lưới",
    "Fishnet Mask": "Mặt nạ lưới",
    "Fishnet Mode": "Chế độ lưới",
    "Fishnet Scale": "Tỉ lệ lưới",
    "Fishnet Thickness": "Độ dày lưới",
    "Foam Color": "Màu bọt",
    "Foam Mask": "Mặt nạ bọt",
    "Foam Width": "Độ rộng bọt",
    "Fresnel Power": "Độ mạnh Fresnel",
    "Fuzz Color": "Màu lông tơ",
    "Fuzz Mask": "Mặt nạ lông tơ",
    "Fuzz Power": "Độ mạnh lông tơ",
    "Fuzz Width": "Độ rộng lông tơ",
    "Glint Mask": "Mặt nạ ánh lóe",
    "Grade": "Mức chỉnh màu",
    "Grade Factor": "Hệ số chỉnh màu",
    "Graded Color": "Màu đã chỉnh",
    "Grain Color": "Màu vân",
    "Grain Contrast": "Tương phản vân",
    "Grain Distortion": "Độ méo vân",
    "Grain Mask": "Mặt nạ vân",
    "Grain Scale": "Tỉ lệ vân",
    "Hand Wobble": "Rung tay",
    "Hatch Levels": "Số mức gạch",
    "Head Forward": "Hướng trước của đầu",
    "Head Right": "Hướng phải của đầu",
    "Highlight Color": "Màu điểm sáng",
    "Highlight Tint": "Sắc điểm sáng",
    "Ink Color": "Màu mực",
    "Internal Glow Color": "Màu sáng bên trong",
    "Inverse Depth": "Độ sâu đảo",
    "Iris Color": "Màu mống mắt",
    "Knit Bump": "Gồ len đan",
    "Knit Depth": "Độ sâu len đan",
    "Knit Scale": "Tỉ lệ len đan",
    "Light Angle": "Góc đèn",
    "Light Bleed": "Loang sáng",
    "Light Factor": "Hệ số ánh sáng",
    "Light Intensity": "Cường độ ánh sáng",
    "Light Reactive": "Phản ứng ánh sáng",
    "Light Tint": "Nhuộm màu đèn",
    "Light Tint Strength": "Độ mạnh nhuộm màu đèn",
    "Light Vector": "Hướng đèn",
    "Line Alpha": "Độ trong của nét",
    "Line Break Threshold": "Ngưỡng ngắt nét",
    "Line Modulation": "Biến điệu nét",
    "Line Sharpness": "Độ sắc nét vẽ",
    "Linear Depth": "Độ sâu tuyến tính",
    "Lit Warm Tint": "Sắc ấm phía sáng",
    "Metal Tint": "Sắc kim loại",
    "Near Distance": "Khoảng cách gần",
    "Normalized Depth": "Độ sâu chuẩn hóa",
    "Outline Ink": "Mực viền",
    "Outline Lighting Mix": "Trộn ánh sáng viền",
    "Paper / Base Color": "Giấy / màu cơ sở",
    "Paper Color": "Màu giấy",
    "Penumbra Saturation": "Độ bão hòa vùng nửa tối",
    "Primary Angle": "Góc chính",
    "Pupil Color": "Màu đồng tử",
    "Radial Distance": "Khoảng cách xuyên tâm",
    "Ray Density": "Mật độ tia",
    "Rim Factor": "Hệ số viền sáng",
    "Rim Fresnel Power": "Độ mạnh Fresnel viền sáng",
    "Rim Glint Power": "Độ mạnh ánh lóe viền",
    "Rim Glint Width": "Độ rộng ánh lóe viền",
    "Rim Lift": "Nâng viền sáng",
    "Rim Light Strength": "Độ mạnh viền sáng",
    "Rim Lighting Mix": "Trộn ánh sáng viền sáng",
    "Rim Power": "Lũy thừa viền sáng",
    "Rim Softness": "Độ mềm viền sáng",
    "Rim Width": "Độ rộng viền sáng",
    "Screen Depth": "Độ sâu màn hình",
    "Screen Space Lock": "Khóa theo màn hình",
    "Shading Factor": "Hệ số đổ bóng",
    "Shading Ramp": "Dải đổ bóng",
    "Shadow Cool Tint": "Sắc lạnh của bóng",
    "Shadow Fac": "Hệ số bóng (Fac)",
    "Shadow Factor": "Hệ số bóng",
    "Shadow Mask": "Mặt nạ bóng",
    "Shadow Softness": "Độ mềm bóng",
    "Shadow Threshold": "Ngưỡng bóng",
    "Shadow Tint": "Sắc bóng",
    "Shallow Color": "Màu chỗ nông",
    "Sheen Color": "Màu ánh mượt",
    "Sheen Mask": "Mặt nạ ánh mượt",
    "Sheen Power": "Độ mạnh ánh mượt",
    "Sheen Width": "Độ rộng ánh mượt",
    "Sheerness": "Độ mỏng xuyên",
    "Side Factor": "Hệ số bên",
    "Silk Blend": "Hòa trộn lụa",
    "Silk Shift Color": "Màu ánh lụa",
    "Skin Color": "Màu da",
    "Skin Visibility": "Độ lộ da",
    "Smooth Normal": "Normal mượt",
    "Sparkle Color": "Màu lấp lánh",
    "Sparkle Density": "Mật độ lấp lánh",
    "Sparkle Mask": "Mặt nạ lấp lánh",
    "Sparkle Scale": "Tỉ lệ lấp lánh",
    "Specular Intensity": "Cường độ phản xạ",
    "Specular Mask": "Mặt nạ phản xạ",
    "Specular Sharpness": "Độ sắc phản xạ",
    "Specular Size": "Cỡ phản xạ",
    "Specular Softness": "Độ mềm phản xạ",
    "Strand Jitter": "Nhiễu sợi",
    "Stroke Width": "Độ dày nét",
    "Tights Color": "Màu quần tất",
    "Tint Darkness": "Độ tối của sắc",
    "Tint Saturation Boost": "Tăng bão hòa của sắc",
    "Tone Angle": "Góc tram",
    "Tone Fac": "Hệ số tram",
    "Tone Scale": "Tỉ lệ tram",
    "Tone Sharpness": "Độ sắc tram",
    "Top Shadow Tint": "Sắc bóng phía trên",
    "UV Vector": "Vector UV",
    "View Taper": "Thon theo góc nhìn",
    "Weave Scale": "Tỉ lệ dệt",
    "Weave Strength": "Độ mạnh dệt",
    "Wool Color": "Màu len",
    "World Ambient": "Môi trường World",
    "Yarn Thickness": "Độ dày sợi len",

    # DaskToon nodes (C++): properties and their items
    "Ambient Mode": "Chế độ môi trường",
    "How World Ambient color affects shadow / shading": "Cách màu môi trường của World tác động lên bóng / đổ bóng",
    "Light Mode": "Chế độ ánh sáng",
    "How colored lamps affect base color": "Cách đèn màu tác động lên màu cơ sở",
    "How colored lamps affect the lit side": "Cách đèn màu tác động lên phía được chiếu sáng",
    "How light turns into shadow": "Cách ánh sáng chuyển thành bóng",
    "How the Ambient Color tints the shadow tone": "Cách màu môi trường nhuộm tông bóng",
    "Add (Magic/Neon)": "Cộng (phép thuật/neon)",
    "Additive glow from magic/neon lights": "Ánh sáng cộng thêm từ đèn phép thuật/neon",
    "Auto Harmonic (Kyoto Style)": "Hài hòa tự động (kiểu Kyoto)",
    "Auto-synthesize rich dark saturated outline tint from Base Color":
        "Tự tạo màu viền đậm, tối và rực từ màu cơ sở",
    "B&W Manga Comic": "Truyện tranh manga đen trắng",
    "Blend shadow Brightness with Sky/World": "Hòa độ sáng của bóng với bầu trời/World",
    "Blend shadow Saturation with Sky/World": "Hòa độ bão hòa của bóng với bầu trời/World",
    "Cel shading only, no light color shift": "Chỉ đổ bóng cel, không đổi màu theo đèn",
    "Classic Black & White Manga (Paper White + Halftone Gray + Ink Black)":
        "Manga đen trắng cổ điển (giấy trắng + xám tram + mực đen)",
    "Classic circular manga screentone dots": "Chấm tram tròn manga cổ điển",
    "Clean parallel comic shading lines": "Nét đổ bóng truyện tranh song song, sạch",
    "Color Webtoon / Manhwa": "Webtoon / Manhwa màu",
    "Direct color mix with World color": "Trộn màu trực tiếp với màu World",
    "Direct light color multiplication": "Nhân trực tiếp với màu đèn",
    "Enable 3D Inverted Hull anime outline module": "Bật mô-đun viền anime vỏ lật 3D (inverted hull)",
    "Enable Ambient Occlusion crevice shadow module": "Bật mô-đun bóng khe kẽ Ambient Occlusion",
    "Enable Cinematic Color Grading module": "Bật mô-đun chỉnh màu điện ảnh",
    "Enable Scene Light lighting module": "Bật mô-đun chiếu sáng theo đèn trong cảnh",
    "Enable VRM Parametric Rim Light module": "Bật mô-đun viền sáng tham số kiểu VRM",
    "Enable World Ambient lighting module": "Bật mô-đun ánh sáng môi trường từ World",
    "Fine ink stipple paper texture": "Vân giấy chấm mực mịn",
    "Halftone Screentone (Tram)": "Tram chấm (halftone)",
    "Harmonic Tint (Kyoto/Ufotable)": "Màu hài hòa (Kyoto/Ufotable)",
    "Hue + Saturation (HS)": "Sắc độ + độ bão hòa (HS)",
    "Hue Only (H)": "Chỉ sắc độ (H)",
    "Hue Tint (H)": "Nhuộm sắc độ (H)",
    "Light-to-shadow tint, multiplied with Base Color": "Màu chuyển từ sáng sang bóng, nhân với màu cơ sở",
    "Manga / Comic Art Style": "Phong cách manga / truyện tranh",
    "Manga Mode": "Chế độ manga",
    "Manga Screentone Shading Pattern": "Mẫu đổ bóng tram manga",
    "Modern Digital Color Comic with screentone texture overlay":
        "Truyện tranh màu kỹ thuật số hiện đại có lớp vân tram phủ lên",
    "Multi-directional hand-drawn cross hatching": "Gạch chéo vẽ tay nhiều hướng",
    "Multiply shadow with World color": "Nhân bóng với màu World",
    "Natural lighting tint on Base Color": "Nhuộm ánh sáng tự nhiên lên màu cơ sở",
    "Outline Color Harmonization Mode": "Chế độ hài hòa màu viền",
    "Outline Mode": "Chế độ viền",
    "Outline tint brightness reacts to scene lighting": "Độ sáng màu viền phản ứng theo ánh sáng cảnh",
    "Overlay (Movie)": "Phủ (phim)",
    "Overlay (Standard)": "Phủ (chuẩn)",
    "Paint your own light-to-shadow transition with a color ramp":
        "Tự vẽ chuyển từ sáng sang bóng bằng dải màu",
    "Parallel Lines": "Nét song song",
    "Pattern Type": "Kiểu mẫu",
    "Pencil Sketch": "Phác chì",
    "Photoshop Overlay blend (Classic Anime Movie)": "Hòa trộn Overlay kiểu Photoshop (phim anime cổ điển)",
    "Pure Cel": "Cel thuần",
    "Saturation (S)": "Độ bão hòa (S)",
    "Shadow Color, Threshold and Softness sliders": "Thanh trượt màu bóng, ngưỡng và độ mềm",
    "Shift shadow Hue and Saturation towards Sky/World":
        "Đẩy sắc độ và độ bão hòa của bóng về phía bầu trời/World",
    "Shift shadow Hue towards Sky/World without fog": "Đẩy sắc độ của bóng về phía bầu trời/World, không mờ sương",
    "Soft graphite pencil draft shading": "Đổ bóng phác thảo bút chì than mềm",
    "Stipple Paper Grain": "Vân giấy chấm",
    "Tint surface Hue with lamp color": "Nhuộm sắc độ bề mặt theo màu đèn",
    "Use Outline": "Dùng viền",
    "Use fixed Outline Color": "Dùng màu viền cố định",
    "Use specified Outline Color input": "Dùng ô màu viền được chỉ định",
    "Value (V)": "Giá trị (V)",
    # dasktoon_rig/parts.py
    "Part %s: material %s is not on %s": "Phần %s: material %s không có trên %s",
    "Part %s: vertex group %s is not on %s": "Phần %s: vertex group %s không có trên %s",
    "Part %s has no vertices": "Phần %s không có đỉnh nào",
    # dasktoon_rig/build.py
    "Built %d bones in %d chains, weights on %d objects": "Đã dựng %d xương trong %d chuỗi, vẽ weight trên %d object",
    "The active object is not an armature": "Object đang chọn không phải armature",
    "%s is linked from a library": "%s được link từ thư viện",
    "%s is not a standard skeleton; missing bones: %s": "%s không phải khung chuẩn; thiếu xương: %s",
    "%s is hidden; show it before building": "%s đang ẩn; hãy hiện nó trước khi dựng",
    "Add parts before building the rig": "Hãy thêm phần trước khi dựng rig",
    "Part %s has no object": "Phần %s chưa có object",
    "Part %s: %s is not a mesh": "Phần %s: %s không phải mesh",
    "%s shares its mesh with other objects; make it single user first":
        "%s dùng chung mesh với object khác; hãy tách riêng (Single User) trước",
    "Part %s: bone %s is not in %s": "Phần %s: xương %s không có trong %s",
    "Clothing copies its weights from a Body part; add a Body part first":
        "Quần áo chép weight từ phần Body; hãy thêm phần Body trước",
    "%s: %d vertices took the nearest bone (automatic weights found no solution there)":
        "%s: %d đỉnh lấy theo xương gần nhất (weight tự động không tìm được nghiệm ở đó)",
    "%s: no Body surface to copy weights from": "%s: không có bề mặt Body để chép weight",
    # bl_ui/dasktoon_rig.py
    "Anime Humanoid": "Khung người anime",
    "Add the DaskToon standard skeleton, fitted to the selected meshes, which become its parts":
        "Thêm khung xương chuẩn của DaskToon, khớp với các mesh đang chọn và lấy chúng làm phần",
    "Edit Joints": "Sửa khớp",
    "Edit the joints of the skeleton with X-Axis Mirror on, so both sides move together":
        "Sửa khớp của khung xương với X-Axis Mirror bật, hai bên cùng di chuyển",
    "Fit to Parts": "Khớp theo các phần",
    "Move and scale the skeleton to the meshes of the parts; the joints you placed are replaced":
        "Dời và co giãn khung xương theo mesh của các phần; vị trí khớp bạn đã đặt sẽ bị thay",
    "Add Selected Meshes": "Thêm các mesh đang chọn",
    "Add each selected mesh as a part of the rig, with the role its name suggests":
        "Thêm mỗi mesh đang chọn thành một phần của rig, với vai trò đoán theo tên",
    "Add Material Part": "Thêm phần theo material",
    "Add the faces of one material of the active part's mesh as a new part":
        "Thêm các mặt mang một material của mesh thuộc phần đang chọn thành một phần mới",
    "Remove Part": "Xóa phần",
    "Remove the active part from the rig; its weights stay until the next build":
        "Xóa phần đang chọn khỏi rig; weight của nó còn giữ tới lần dựng sau",
    "Build Rig": "Dựng rig",
    "Generate the hair and skirt chains and paint the weights of every part":
        "Sinh chuỗi xương tóc, váy và vẽ weight cho mọi phần",
    "Add Part from Selection": "Thêm phần từ vùng chọn",
    "Make the selected vertices a part of the rig, kept in a new vertex group":
        "Biến các đỉnh đang chọn thành một phần của rig, lưu trong một vertex group mới",
    "Fit the joints in Edit Mode, then press Build Rig in Properties › Object Data":
        "Chỉnh khớp trong Edit Mode, rồi bấm Dựng rig ở Properties › Object Data",
    "The selected meshes are already parts": "Các mesh đang chọn đã là phần của rig",
    "No standard skeleton to add the part to": "Không có khung chuẩn nào để thêm phần vào",
    "Select the vertices of the part first": "Hãy chọn các đỉnh của phần trước",
    "Added part %s to %s": "Đã thêm phần %s vào %s",
    "Anime Rig": "Rig anime",
    "Joints": "Khớp",
    "Parts": "Các phần",
    "Build": "Dựng",
    "Missing bones: %s": "Thiếu xương: %s",
    "Add › Armature › Anime Humanoid adds a standard skeleton":
        "Add › Armature › Khung người anime thêm một khung chuẩn",
    "Standard skeleton": "Khung chuẩn",
    "Select meshes and press + to add them as parts": "Chọn mesh rồi bấm + để thêm chúng làm phần",
    "Build replaces the weights of every part": "Dựng lại sẽ thay weight của mọi phần",
    "Select the vertices of a part in Edit Mode": "Chọn các đỉnh của một phần trong Edit Mode",
    "A part of the character and how it is rigged": "Một phần của nhân vật và cách rig nó",
    "Name of the part; generated bones start with it": "Tên phần; tên các xương sinh ra bắt đầu bằng nó",
    "Mesh that holds the part": "Mesh chứa phần",
    "Scope": "Phạm vi",
    "Which vertices of the mesh make the part": "Những đỉnh nào của mesh tạo nên phần",
    "Whole Object": "Cả object",
    "Every vertex of the mesh": "Mọi đỉnh của mesh",
    "The faces that use a material": "Các mặt dùng một material",
    "The vertices of a vertex group": "Các đỉnh của một vertex group",
    "Material whose faces make the part": "Material có các mặt tạo nên phần",
    "Vertex group whose vertices make the part": "Vertex group có các đỉnh tạo nên phần",
    "Role": "Vai trò",
    "How the part is rigged": "Cách rig phần này",
    "Skin and face: automatic weights from the body bones": "Da và mặt: weight tự động theo xương thân",
    "Clothing": "Quần áo",
    "Follows the body: weights copied from the nearest Body surface":
        "Đi theo thân: weight chép từ bề mặt Body gần nhất",
    "Accessory": "Phụ kiện",
    "Rigid on one bone": "Gắn cứng vào một xương",
    "Hair": "Tóc",
    "A chain of bones for each long lock": "Một chuỗi xương cho mỗi lọn tóc dài",
    "Skirt": "Váy",
    "Chains of bones around the hips": "Các chuỗi xương quanh hông",
    "Bone the part hangs from or sits on; empty picks one automatically (Head for hair, Hips for a skirt, the nearest bone for an accessory)":
        "Xương mà phần treo vào hoặc gắn lên; để trống thì tự chọn (Head cho tóc, Hips cho váy, xương gần nhất cho phụ kiện)",
    "Bones per Chain": "Số xương mỗi chuỗi",
    "Number of bones along each chain": "Số xương dọc mỗi chuỗi",
    "Chains": "Số chuỗi",
    "Number of chains around the skirt": "Số chuỗi quanh váy",
    "The parts of an anime rig": "Các phần của một rig anime",
    "Active Part": "Phần đang chọn",
    "Part shown below the list": "Phần hiện bên dưới danh sách",
    "Parts of the anime rig": "Các phần của rig anime",
    "Material whose faces make the new part": "Material có các mặt tạo nên phần mới",
    "Name of the new part": "Tên của phần mới",
    "Standard skeleton the part belongs to": "Khung chuẩn chứa phần này",
    # bl_ui/dasktoon_rig.py (collection)
    "Parts of the character": "Các phần của nhân vật",
    # dasktoon_rig/build.py (attach bone)
    "Part %s: bone %s is made by Build Rig; pick a bone of the skeleton":
        "Phần %s: xương %s do Dựng rig tạo ra; hãy chọn một xương của khung",
    # bl_ui/dasktoon_rig.py (sway settings and colliders)
    "Stiffness": "Độ cứng",
    "How strongly the chain springs back to its pose": "Mức chuỗi bật về lại tư thế của nó",
    "Gravity": "Trọng lực",
    "How strongly the chain is pulled down": "Mức chuỗi bị kéo xuống",
    "Drag": "Lực cản",
    "How quickly the swing dies down: 0 keeps swinging, 1 stops at once":
        "Độ nhanh mà chuyển động lắc tắt dần: 0 lắc mãi, 1 dừng ngay",
    "How far each joint keeps from the colliders": "Khoảng cách mỗi khớp giữ với collider",
    "A capsule along a bone that hair and skirts do not go through":
        "Một khối capsule dọc theo xương mà tóc và váy không xuyên qua",
    "Bone the capsule runs along, from its head to its tail": "Xương mà capsule chạy dọc theo, từ đầu tới đuôi xương",
    "Radius of the capsule": "Bán kính của capsule",
    "Colliders": "Collider",
    "Capsules that hair and skirts do not go through; Build Rig makes them":
        "Các capsule mà tóc và váy không xuyên qua; Dựng rig tạo ra chúng",
    "Live Sway": "Lắc trực tiếp",
    "Sway hair and skirts while the animation plays": "Cho tóc và váy lắc khi animation đang phát",
    # bl_ui/dasktoon_rig.py (Sway panel)
    "Bake Sway": "Bake chuyển động lắc",
    "Key the sway of hair and skirts on every frame of the scene; Live Sway turns off so the keys play as they are":
        "Đặt keyframe chuyển động lắc của tóc và váy ở mọi khung của scene; Lắc trực tiếp tắt để phát đúng các keyframe",
    "Baked %d frames of %d bones": "Đã bake %d khung cho %d xương",
    "Sway": "Lắc",
    "Build Rig first to make the hair and skirt chains": "Hãy Dựng rig trước để có chuỗi xương tóc và váy",
    "Select a hair or skirt part to set how it sways": "Chọn một phần tóc hoặc váy để chỉnh cách nó lắc",
    # bl_ui/dasktoon_rig.py (Sway in Unity)
    "Sway in Unity": "Lắc trong Unity",
    "How the chain sways in Unity": "Cách chuỗi lắc trong Unity",
    "Runtime": "Khi chạy",
    "DaskToon's spring bone script sways the chain while the game runs":
        "Script spring bone của DaskToon cho chuỗi lắc khi game chạy",
    "Baked": "Đã bake",
    "Unity plays the sway baked into the exported animation":
        "Unity phát chuyển động lắc đã bake trong animation xuất ra",
    # dasktoon_export (anime rig for Unity)
    "Scripts: installed or updated": "Script: đã cài hoặc cập nhật",
    "Scripts: the project already has a recent enough version, not written again":
        "Script: project đã có bản đủ mới, không ghi lại",
    "Scripts: not needed (no hair or skirt chains)": "Script: không cần (không có chuỗi tóc hay váy)",
    "Rig: %s (DaskToon spring bones sway the hair and skirts in Unity)":
        "Rig: %s (spring bone của DaskToon cho tóc và váy lắc trong Unity)",
    "Part %s sways in Unity, but its bones have sway keys: Unity would sway it twice. Set Sway in Unity to Baked, or remove the keys":
        "Phần %s lắc trong Unity nhưng xương của nó có key lắc: Unity sẽ lắc hai lần. Đặt Lắc trong Unity thành Đã bake, hoặc xóa các key đó",
    # dasktoon_export/report.py (scripts once per project)
    "Note: the Scripts folder may be in a Unity project only once. With a second character, delete its Scripts folder after dragging it in, or export into the Unity project itself.":
        "Lưu ý: mỗi project Unity chỉ được có một thư mục Scripts này. Với nhân vật thứ hai, xóa thư mục Scripts của nó sau khi kéo vào, hoặc xuất thẳng vào project Unity.",
    # Spring constraint (C++ RNA, bl_ui/properties_constraint.py)
    "Spring": "Lò xo",
    "Sway the bone like a spring: it swings with the motion, hangs down and keeps out of collider bones (DaskToon)":
        "Cho xương lắc như lò xo: đung đưa theo chuyển động, rủ xuống và không xuyên qua xương collider (DaskToon)",
    "Spring Constraint": "Constraint lò xo",
    "Sway a bone like a spring bone: it swings with the motion, hangs down and keeps out of collider bones":
        "Cho xương lắc như spring bone: đung đưa theo chuyển động, rủ xuống và không xuyên qua xương collider",
    "Spring Collider": "Collider của lò xo",
    "A capsule along a bone that the spring keeps out of": "Một capsule dọc theo xương mà lò xo tránh",
    "Armature of the collider bone": "Armature chứa xương collider",
    "Radius of the capsule, in armature units": "Bán kính của capsule, theo đơn vị của armature",
    "Capsules along bones that the spring keeps out of": "Các capsule dọc theo xương mà lò xo tránh",
    "How strongly the bone springs back to its pose": "Mức xương bật về lại tư thế của nó",
    "How strongly the bone is pulled down": "Mức xương bị kéo xuống",
    "How far the bone's tail keeps from the colliders, in armature units":
        "Khoảng cách đuôi xương giữ với collider, theo đơn vị của armature",
    "Spring Colliders": "Các collider của lò xo",
    "Collider bones of a Spring constraint": "Các xương collider của một constraint lò xo",
    "Add a collider; its armature is the constraint's owner":
        "Thêm một collider; armature của nó là chủ của constraint",
    "Remove all colliders": "Xóa mọi collider",
    "No colliders: Build Rig adds the body bones": "Chưa có collider: Dựng rig sẽ thêm các xương thân",
    # Build Rig: mesh warnings (anime rig spec 12)
    "%s has a negative or non-uniform scale: apply its scale (Object › Apply › Scale) before building and exporting "
    "to Unity":
        "%s có scale âm hoặc không đều: hãy Apply Scale (Object › Apply › Scale) trước khi dựng rig và xuất sang Unity",
    "%s: the faces of the body point inward, so automatic weights may pick the wrong bones. Recalculate the normals "
    "outside (Edit Mode, Mesh › Normals)":
        "%s: mặt của phần thân quay vào trong nên weight tự động có thể chọn sai xương. Hãy tính lại pháp tuyến hướng "
        "ra ngoài (Edit Mode, Mesh › Normals)",
    # Save Copy, Save Incremental on a draft (project workflow)
    "This file is a draft: save it into a project first": "File này là bản nháp: hãy lưu nó vào một dự án trước",
    # Dope Sheet: Whole Character (Animation tab spec 4)
    "Show every channel of the characters that have a selected part: the armature with all its bones, the objects "
    "parented to it and the meshes it deforms (DaskToon)":
        "Hiện mọi kênh của các nhân vật có một phần đang được chọn: armature với mọi xương, các object là con của nó "
        "và các mesh nó điều khiển (DaskToon)",
    # Animation tab: Key Pose and the DaskToon Character keying set (spec 5)
    "DaskToon Character": "Nhân vật DaskToon",
    "Key the whole pose of the selected characters: every bone, every shape key of their meshes and every expression "
    "controller; other selected objects get location, rotation and scale":
        "Chèn khung khóa cho cả dáng của các nhân vật đang chọn: mọi xương, mọi hình mẫu của các mesh và mọi bộ điều "
        "khiển biểu cảm; object khác đang chọn được chèn vị trí, xoay và tỉ lệ",
    "Key Pose": "Khóa cả dáng",
    "Key the whole pose of the selected characters at the current frame: every bone, shape key and controller":
        "Chèn khung khóa cho cả dáng của các nhân vật đang chọn tại khung hiện tại: mọi xương, hình mẫu và bộ điều "
        "khiển",
    "Select a part of a character to key its pose": "Hãy chọn một phần của nhân vật để chèn khung khóa cho dáng của nó",
    # Animation tab: clips of a character (clips spec 4)
    "Armature of the character this action is a clip of (DaskToon)":
        "Armature của nhân vật mà action này là một clip (DaskToon)",
    "Character": "Nhân vật",
    "Clips": "Clip",
    "Delete Clip": "Xóa clip",
    "Delete the clip the character plays; it plays the first clip left":
        "Xóa clip nhân vật đang dùng; nhân vật chuyển sang clip đầu tiên còn lại",
    "Deleted clip %s": "Đã xóa clip %s",
    "Make a new, empty clip of the character and play it; its animation so far becomes a clip first":
        "Tạo một clip mới, rỗng cho nhân vật và dùng nó; animation đang có được gom thành một clip trước",
    "New Clip": "Clip mới",
    "New clip %s": "Đã tạo clip %s",
    "No Clip": "Chưa có clip",
    "No clip %s": "Không có clip %s",
    "Play this clip on the whole character: body and face": "Dùng clip này cho cả nhân vật: thân và mặt",
    "Select a part of a character": "Hãy chọn một phần của nhân vật",
    "Use Clip": "Dùng clip",
    # Engine Export: clips (clips spec 6)
    "Clips: %s": "Clip: %s",
    "%s (loop)": "%s (lặp)",
    # Animation tab: anime timing of a clip (anime timing spec 3)
    "Anime timing of the clip: from each row's frame it runs on that row's step (DaskToon)":
        "Nhịp anime của clip: từ khung của mỗi dòng, clip chạy theo nhịp của dòng đó (DaskToon)",
    "Frame the step starts at": "Khung bắt đầu nhịp",
    "Frames each drawing is held: 1 to 4, or 0 to hold this frame":
        "Số khung giữ mỗi hình: 1 đến 4, hoặc 0 để giữ nguyên khung này",
    "From this frame the clip runs on this step, until the next row":
        "Từ khung này clip chạy theo nhịp này, cho tới dòng sau",
    # Animation tab: Timing popover (anime timing spec 4)
    "1 to 4 frames per drawing, or 0 to hold": "1 đến 4 khung cho mỗi hình, hoặc 0 để giữ",
    "From frame %d: %s": "Từ khung %d: %s",
    "From the current frame the clip runs on this step, until the next timing row":
        "Từ khung hiện tại clip chạy theo nhịp này, cho tới dòng nhịp sau",
    "Key a pose first": "Hãy key một dáng trước",
    "Key on the drawn frames: a key between them shows from the next one":
        "Key vào khung vẽ; key giữa hai khung vẽ hiện từ khung vẽ sau",
    "Keyed the pose of %s at frame %d": "Đã chèn khung khóa cho dáng của %s tại khung %d",
    "Remove Timing": "Bỏ nhịp",
    "Remove this timing row: the timing before it goes on": "Bỏ dòng nhịp này: nhịp trước nó chạy tiếp",
    "Set Timing Here": "Đặt nhịp tại đây",
    "Set timing from this frame:": "Đặt nhịp từ khung này:",
    "The clip runs on 1s": "Clip đang chạy on 1s",
    "Hold": "Giữ",
    # Onion skin (anime timing spec 6)
    "Onion Skin": "Bóc Vỏ Hành",
    "Before": "Trước",
    "After": "Sau",
    "Opacity": "Độ đậm",
    "Show faintly, in the 3D Viewports, the character's poses at the keys before and after this frame":
        "Hiện mờ trong các khung nhìn 3D dáng của nhân vật ở các key trước và sau khung này",
    "How many keyed poses before this frame to show": "Số dáng có key trước khung này được hiện",
    "How many keyed poses after this frame to show": "Số dáng có key sau khung này được hiện",
    "How visible the nearest ghost is; farther ones fade": "Độ đậm của bóng gần nhất; bóng càng xa càng mờ",
    "Ghosts are the keyed poses; they update when you stop for a moment":
        "Bóng là các dáng có key; chúng cập nhật khi bạn dừng tay một chút",
    "Onion skin of the character being animated (DaskToon)": "Bóc vỏ hành của nhân vật đang làm hoạt hình (DaskToon)",
    "Onion skin of the character being animated (anime timing spec 6)": "Bóc vỏ hành của nhân vật đang làm hoạt hình",
    # Fast action filter (anime timing spec 7)
    "Fast Action": "Hành động nhanh",
    "Where the character moves fast, smear it and show afterimages of the frames before and speed lines":
        "Chỗ nhân vật chuyển động nhanh thì kéo nhòe, hiện bóng lưu của các khung trước và vệt tốc độ",
    "Threshold": "Ngưỡng",
    "Speed above which a part of the character gets the effects":
        "Phần nào của nhân vật nhanh hơn tốc độ này thì có hiệu ứng",
    "Smear": "Kéo nhòe",
    "How far the trailing side of a fast part is pulled back toward the frame before":
        "Mặt sau của phần chuyển động nhanh bị kéo lùi về phía khung trước bao xa",
    "Afterimages": "Bóng lưu",
    "How many of the frames before show as afterimages of the fast parts":
        "Số khung trước hiện thành bóng lưu của các phần nhanh",
    "Afterimage Opacity": "Độ đậm bóng lưu",
    "How visible the newest afterimage is; older ones fade": "Độ đậm của bóng lưu mới nhất; bóng cũ hơn mờ dần",
    "Afterimage Color": "Màu bóng lưu",
    "Afterimage Material": "Material bóng lưu",
    "Line Density": "Mật độ vệt",
    "Share of the fast vertices that trail a speed line": "Tỉ lệ đỉnh nhanh có vệt tốc độ kéo theo",
    "Line Length": "Độ dài vệt",
    "A speed line is as long as the distance moved in this time":
        "Vệt tốc độ dài bằng quãng đường đi được trong khoảng thời gian này",
    "Line Color": "Màu vệt",
    "Line Width": "Độ dày vệt",
    "Line Material": "Material vệt",
    "Shows in DaskToon's viewport and render; it does not go into the FBX":
        "Hiện trong khung nhìn và bản render của DaskToon; không vào FBX",
    "Fast action filter of the character (DaskToon)": "Bộ lọc hành động nhanh của nhân vật (DaskToon)",
    "Fast action filter of a character (anime timing spec 7)": "Bộ lọc hành động nhanh của nhân vật",
    # Illustration finish (illustration finish spec)
    "Illustration Finish": "Hoàn thiện tranh",
    "Give the picture the finish a painter gives an illustration: light, colors, depth and texture":
        "Cho bức ảnh lớp hoàn thiện như họa sĩ làm cho một bức tranh minh họa: ánh sáng, màu, chiều sâu và chất",
    "The scene's illustration finish (DaskToon)": "Lớp hoàn thiện tranh của scene (DaskToon)",
    "Show in Viewport": "Hiện trong viewport",
    "Which 3D Viewports in Rendered shading show the finish":
        "Các 3D Viewport ở chế độ Rendered nào hiện lớp hoàn thiện",
    "Only renders show the finish": "Chỉ ảnh render có lớp hoàn thiện",
    "Viewports looking through the camera show the finish": "Viewport nhìn qua camera hiện lớp hoàn thiện",
    "Every viewport in Rendered shading shows the finish": "Mọi viewport ở chế độ Rendered hiện lớp hoàn thiện",
    "The finish's compositor node group (DaskToon builds it again when a layer is switched)":
        "Nhóm node compositor của lớp hoàn thiện (DaskToon dựng lại khi bật hoặc tắt một lớp)",
    "Add to Compositor": "Thêm vào compositor",
    "Put the Illustration Finish right before the output of the scene's compositor":
        "Đặt Hoàn thiện tranh ngay trước đầu ra của compositor của scene",
    "The scene has its own compositor": "Scene đã có compositor riêng",
    "Colored Lines for All Materials": "Nét màu cho mọi material",
    "Give every outlined material lines in a deep shade of its own colors (Auto Harmonic), not one fixed color":
        "Cho nét viền của mọi material có outline lấy sắc đậm của chính màu material (Auto Harmonic), thay vì một màu cố định",
    "Colored lines on %d materials": "Đã đặt nét màu cho %d material",
    "Painting Colors": "Màu tranh",
    "Painting Light": "Ánh sáng tranh",
    "Strokes and Texture": "Nét và chất",
    "How much of the finish shows: 0 is the picture as rendered":
        "Lớp hoàn thiện hiện bao nhiêu: 0 là ảnh như khi render",
    "Shadow and Light Tint": "Màu bóng, màu sáng",
    "Dark areas lean to a shadow color, light areas to a light color":
        "Vùng tối ngả về một màu bóng, vùng sáng ngả về một màu sáng",
    "Color the dark areas lean to": "Màu mà vùng tối ngả về",
    "Color the light areas lean to": "Màu mà vùng sáng ngả về",
    "Tint Strength": "Độ ngả màu",
    "How strongly the areas lean": "Các vùng ngả màu mạnh đến đâu",
    "Saturation and Contrast": "Bão hòa, tương phản",
    "Livelier colors and clearer forms": "Màu tươi hơn, khối rõ hơn",
    "1 keeps the colors": "1 là giữ nguyên màu",
    "0 keeps the contrast": "0 là giữ nguyên tương phản",
    "Brush Strokes": "Nét cọ",
    "Small details become patches of color along the strokes, as if painted with a brush":
        "Chi tiết nhỏ thành mảng màu theo hướng nét, như tô bằng cọ",
    "Brush size, as a share of the picture height": "Cỡ cọ, tính theo phần chiều cao ảnh",
    "How crisp the edges of the strokes are": "Mép nét cọ sắc đến đâu",
    "Strokes Strength": "Độ đậm nét cọ",
    "How much of the strokes shows": "Nét cọ hiện bao nhiêu",
    "Air": "Không khí",
    "The farther, the more things fade into the color of the air": "Vật càng xa càng nhòa vào màu không khí",
    "Distance where the air starts to show": "Khoảng cách không khí bắt đầu hiện",
    "Distance where the air is at full strength": "Khoảng cách không khí đậm nhất",
    "Air Color": "Màu không khí",
    "Color far things fade into": "Màu mà vật ở xa nhòa vào",
    "Air Strength": "Độ đậm không khí",
    "How much far things fade": "Vật ở xa nhòa bao nhiêu",
    "How much the sky behind everything fades": "Bầu trời phía sau mọi thứ nhòa bao nhiêu",
    "Soft Background": "Hậu cảnh mềm",
    "What lies beyond the focus is softened, so the subject stands out":
        "Phần nằm xa hơn chỗ lấy nét được làm mềm, để chủ thể nổi lên",
    "Auto Focus": "Tự lấy nét",
    "Focus where the camera focuses, or else on the selected object":
        "Lấy nét theo camera, nếu không thì vào object đang chọn",
    "Distance kept sharp": "Khoảng cách được giữ sắc nét",
    "Blur size, as a share of the picture height": "Độ mờ, tính theo phần chiều cao ảnh",
    "How far beyond the focus, as a multiple of it, the background is fully soft":
        "Xa hơn chỗ lấy nét bao nhiêu lần thì hậu cảnh mềm hẳn",
    "Soft Glow": "Glow mềm",
    "A blurred copy of the picture lightens it, so light spreads softly as in an anime film":
        "Một bản mờ của ảnh phủ sáng lên chính nó, ánh sáng lan mềm như phim anime chiếu rạp",
    "0 glows the whole picture, 1 only the brightest": "0 là cả ảnh phát sáng, 1 là chỉ chỗ sáng nhất",
    "How far the glow spreads, as a share of the picture height": "Glow lan bao xa, tính theo phần chiều cao ảnh",
    "Glow Strength": "Độ sáng glow",
    "How bright the glow is": "Glow sáng đến đâu",
    "Light Rays": "Tia sáng",
    "Rays from where the sun is in the picture; none when the sun is behind the camera":
        "Tia sáng tỏa từ chỗ mặt trời trong ảnh; không có khi mặt trời ở sau camera",
    "How long the rays are": "Tia sáng dài bao nhiêu",
    "Rays Strength": "Độ sáng tia",
    "How bright the rays are": "Tia sáng sáng đến đâu",
    "Back Light Wrap": "Viền sáng ngược sáng",
    "Light behind a subject spills a little over its outline": "Ánh sáng phía sau chủ thể lấn nhẹ qua mép hình",
    "How far the light spills, as a share of the picture height": "Ánh sáng lấn bao xa, tính theo phần chiều cao ảnh",
    "Wrap Strength": "Độ sáng viền",
    "How bright the spill is": "Phần lấn sáng đến đâu",
    "Light Gradient": "Gradient ánh sáng",
    "A warm to cool wash across the picture, from the side the light comes from":
        "Một lớp màu từ ấm sang lạnh phủ qua ảnh, bắt đầu từ phía ánh sáng tới",
    "Light Side": "Phía sáng",
    "Color on the side of the light": "Màu ở phía ánh sáng tới",
    "Dark Side": "Phía tối",
    "Color on the other side": "Màu ở phía bên kia",
    "Follow Sun": "Theo mặt trời",
    "The light side is where the scene's sun shines from": "Phía sáng là phía mặt trời của scene chiếu tới",
    "Side the light comes from in the picture: at 90 degrees it comes from the top":
        "Phía ánh sáng tới trên ảnh: 90 độ là từ trên xuống",
    "Gradient Strength": "Độ đậm gradient",
    "How strong the wash is": "Lớp màu đậm đến đâu",
    "The corners darken a little, leading the eye in": "Góc ảnh tối đi một chút, dẫn mắt vào giữa",
    "Where the darkening starts, from the middle": "Chỗ bắt đầu tối, tính từ giữa ảnh",
    "Edge Softness": "Độ mềm mép",
    "How gradually it darkens": "Tối dần từ từ đến đâu",
    "Vignette Color": "Màu vignette",
    "Color of the corners": "Màu ở góc ảnh",
    "Vignette Strength": "Độ đậm vignette",
    "How dark the corners get": "Góc ảnh tối đến đâu",
    "Colors split very slightly toward the edges, as through a lens":
        "Màu tách rất nhẹ về phía rìa ảnh, như qua ống kính",
    "Aberration": "Quang sai",
    "How far the colors split": "Màu tách xa đến đâu",
    "A very light grain of paper over the picture": "Một lớp vân giấy rất nhẹ phủ lên ảnh",
    "Paper Scale": "Cỡ vân giấy",
    "Size of the grain": "Kích thước hạt vân",
    "Paper Strength": "Độ đậm vân giấy",
    "How much the grain shows": "Vân giấy hiện bao nhiêu",
    "Changes Each Frame": "Đổi mỗi khung",
    "The grain changes every frame, like film; off, it stays like paper":
        "Hạt vân đổi mỗi khung như phim; tắt thì đứng yên như giấy",
    # Illustration finish styles (illustration finish spec 5)
    "Early Morning": "Nắng sớm",
    "Sunset": "Hoàng hôn",
    "Night": "Đêm",
    "Watercolor": "Màu nước",
    "Use Style": "Dùng style",
    "Set every layer of the finish from this style": "Đặt mọi lớp hoàn thiện theo style này",
    "Save Style": "Lưu style",
    "Save every setting of the finish as a style of your own, for every file":
        "Lưu mọi thiết lập hoàn thiện thành style của bạn, dùng được ở mọi file",
    "Delete this style of your own": "Xóa style này của bạn",
    "Deleted style %s": "Đã xóa style %s",
    "Give the style a name": "Hãy đặt tên cho style",
    "%s is a built-in style: choose another name": "%s là style có sẵn: hãy chọn tên khác",
    "No style %s": "Không có style %s",
    "The style last used or saved": "Style dùng hoặc lưu gần nhất",
    # Illustration finish: labels of its own (illustration finish spec 6)
    "Overall Strength": "Độ mạnh chung",
    "Dark Area Color": "Màu vùng tối",
    "Light Area Color": "Màu vùng sáng",
    "Painting Depth": "Chiều sâu tranh",
    # Anime rig R3: eyes and mouth (anime rig spec 10)
    "Jaw": "Hàm",
    "The lower jaw and chin: follows the Jaw bone, blended into the face":
        "Hàm dưới và cằm: theo xương Jaw, hòa dần vào mặt",
    "Flat Eye": "Mắt phẳng",
    "An iris drawn on the face: slides on its UVs as the eye looks around":
        "Tròng mắt vẽ trên mặt: trượt trên UV khi mắt nhìn quanh",
    "2D Mouth": "Miệng 2D",
    "A drawn mouth: shows one cell of its texture atlas, chosen by the dt_mouth property":
        "Miệng vẽ: hiện một ô trong atlas texture, chọn bằng thuộc tính dt_mouth",
    "Which eye the iris belongs to": "Tròng mắt thuộc mắt nào",
    "The side the part lies on": "Theo phía phần nằm",
    "The character's left eye": "Mắt trái của nhân vật",
    "The character's right eye": "Mắt phải của nhân vật",
    "How far the iris slides on its UVs when the eye turns all the way; negative turns it the other way":
        "Tròng mắt trượt trên UV bao xa khi mắt xoay hết cỡ; số âm thì trượt ngược lại",
    "Rows": "Số hàng",
    "Rows of mouth cells in the atlas texture": "Số hàng ô miệng trong atlas texture",
    "Columns of mouth cells in the atlas texture": "Số cột ô miệng trong atlas texture",
    "Side Limit": "Giới hạn ngang",
    "How far the eyes turn to the side to follow LookTarget": "Mắt xoay sang bên tối đa bao nhiêu để theo LookTarget",
    "Up and Down Limit": "Giới hạn dọc",
    "How far the eyes turn up and down to follow LookTarget": "Mắt xoay lên xuống tối đa bao nhiêu để theo LookTarget",
    # Anime rig R3: the 2D mouth (anime rig spec 10.3)
    "%s: its material has no image texture to show mouth cells from":
        "%s: material của phần không có image texture để hiện các ô miệng",
    "Cell of the mouth atlas to show": "Ô trong atlas miệng được hiện",
    # Anime rig R3: lip sync (anime rig spec 10.3)
    "Lip Sync from Audio": "Khẩu hình từ âm thanh",
    "Key the mouth from a voice file: the vowel shape keys, the jaw and the 2D mouth, in the clip being played":
        "Key miệng theo file giọng nói: shape key nguyên âm, hàm và miệng 2D, vào clip đang dùng",
    "Voice File": "File giọng nói",
    "Sound file of the voice; empty takes the first sound strip of the Sequencer":
        "File âm thanh của giọng nói; để trống thì lấy strip âm thanh đầu tiên trong Sequencer",
    "Frame the voice starts at, for a file (a sound strip starts where it is)":
        "Khung giọng nói bắt đầu, khi dùng file (strip âm thanh thì bắt đầu ở chỗ của nó)",
    "How wide the mouth opens: 1 is the full vowel shapes": "Miệng mở rộng đến đâu: 1 là đủ hình nguyên âm",
    "Choose a voice file, or add a sound strip to the Sequencer":
        "Hãy chọn file giọng nói, hoặc thêm một strip âm thanh vào Sequencer",
    "Cannot read the sound file %s": "Không đọc được file âm thanh %s",
    "Lip sync: %d frames from frame %d": "Khẩu hình: %d khung từ khung %d",
    "%s has no vowel shape keys (A I U E O, aa ih ou ee oh…), Jaw part or 2D mouth to key":
        "%s không có shape key nguyên âm (A I U E O, aa ih ou ee oh…), phần Jaw hay miệng 2D để key",
}

# Words that need their own translation context, because Blender's own translation of the same word in the default
# context means something else here, and Blender's translation always wins in that context.
VI_CONTEXT = {
    "DaskToon": {
        "Project": "Dự án",
        "Chains": "Số chuỗi",
    },
}


def _table():
    table = {}
    for msgid, msgstr in VI.items():
        for context in ("*", "Operator"):
            table[(context, msgid)] = msgstr
    for context, entries in VI_CONTEXT.items():
        for msgid, msgstr in entries.items():
            table[(context, msgid)] = msgstr
    return {"vi_VN": table}


translations = _table()
classes = ()


def register():
    try:
        bpy.app.translations.unregister(__name__)
    except (ValueError, RuntimeError):
        pass
    bpy.app.translations.register(__name__, translations)


def unregister():
    bpy.app.translations.unregister(__name__)
