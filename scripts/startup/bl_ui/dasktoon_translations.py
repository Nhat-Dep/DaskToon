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
    "DaskToon Project": "Dự án DaskToon",
    "New Project…": "Tạo dự án…",
    "Open Project…": "Mở dự án…",
    "No recent projects": "Chưa có dự án gần đây",
    "Models": "Các model",
    "Shaders: version %d": "Shader: phiên bản %d",
    "Shaders: not installed": "Shader: chưa cài",
    "Create DaskToon Project": "Tạo dự án DaskToon",
    "Create a DaskToon project linked to a Unity project and install the DaskToon shaders into it":
        "Tạo dự án DaskToon gắn với một project Unity và cài shader DaskToon vào đó",
    "Project Folder": "Thư mục dự án",
    "Unity Project": "Project Unity",
    "Save Current File in Project": "Lưu file hiện tại vào dự án",
    "Created project %s and installed the shaders into %s": "Đã tạo dự án %s và cài shader vào %s",
    "Open DaskToon Project": "Mở dự án DaskToon",
    "Open a DaskToon project (dasktoon_project.json)": "Mở một dự án DaskToon (dasktoon_project.json)",
    "Opened project %s": "Đã mở dự án %s",
    "Open this .blend file of the project (DaskToon asks to save the current file first when it has changes)":
        "Mở file .blend này của dự án (DaskToon hỏi lưu file hiện tại trước nếu file có thay đổi)",
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
    "%s already has another file named %s: rename the current file or turn off Save Current File in Project":
        "%s đã có file khác tên %s: hãy đổi tên file hiện tại hoặc bỏ chọn Lưu file hiện tại vào dự án",
}


def _table():
    table = {}
    for msgid, msgstr in VI.items():
        for context in ("*", "Operator"):
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
