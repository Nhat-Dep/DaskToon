# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Images from outside the project are copied into <project>/Textures/ when a person saves (project workflow spec 10):
relative paths, name clashes, identical files, UDIM, what is only warned about and what is left alone."""

import filecmp
import os
import sys
import tempfile
import unittest

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402
from dasktoon_export import textures as png  # noqa: E402
from dasktoon_project import project as dtp, textures as dtt  # noqa: E402


def write_png(path, rgba=(255, 0, 0, 255)):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png.png_bytes(2, 2, bytes(rgba) * 4))
    return path


def load(path):
    image = bpy.data.images.load(path, check_existing=False)
    image.use_fake_user = True
    return image


def resolved(image):
    return os.path.normcase(os.path.normpath(bpy.path.abspath(image.filepath_raw)))


def norm(path):
    return os.path.normcase(os.path.normpath(path))


class TextureCollectTest(unittest.TestCase):
    def setUp(self):
        os.environ["DASKTOON_CONFIG_DIR"] = tempfile.mkdtemp(prefix="dt_tex_config_")
        tu.reset_scene()
        base = tempfile.mkdtemp(prefix="dt_tex_")
        self.project = dtp.create_project("P", os.path.join(base, "Dự án P"))
        self.outside = os.path.join(base, "Ảnh ngoài")
        self.textures = self.project.textures_folder

    def test_outside_image_is_copied_and_relative_after_saving(self):
        source = write_png(os.path.join(self.outside, "skin.png"))
        image = load(source)
        result = dtt.collect(self.project)
        copy = os.path.join(self.textures, "skin.png")
        self.assertEqual((result.copied, result.images, result.warnings), (1, [image], []))
        self.assertTrue(filecmp.cmp(source, copy, shallow=False))
        self.assertEqual(result.summary(), "Copied 1 texture into Textures/")
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(self.project.models_folder, "A.blend"))
        self.assertTrue(image.filepath_raw.startswith("//"))
        self.assertEqual(resolved(image), norm(copy))
        self.assertTrue(os.path.isfile(source))

    def test_saved_draft_gets_a_relative_path_that_follows_the_save(self):
        image = load(write_png(os.path.join(self.outside, "skin.png")))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(self.outside, "draft.blend"))
        dtt.collect(self.project)
        self.assertTrue(image.filepath_raw.startswith("//"))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(self.project.models_folder, "A.blend"))
        self.assertEqual(resolved(image), norm(os.path.join(self.textures, "skin.png")))
        self.assertEqual(dtt.relink_absolute([image]), 0)

    def test_same_name_other_content_gets_a_suffix_and_an_identical_file_is_reused(self):
        write_png(os.path.join(self.textures, "skin.png"), rgba=(0, 0, 255, 255))
        red = load(write_png(os.path.join(self.outside, "a", "skin.png")))
        blue = load(write_png(os.path.join(self.outside, "b", "skin.png"), rgba=(0, 0, 255, 255)))
        result = dtt.collect(self.project)
        self.assertEqual(resolved(red), norm(os.path.join(self.textures, "skin_1.png")))
        self.assertEqual(resolved(blue), norm(os.path.join(self.textures, "skin.png")))
        self.assertEqual(result.copied, 1)
        self.assertEqual(result.summary(), "Copied 1 texture into Textures/")
        self.assertEqual(sorted(os.listdir(self.textures)), ["skin.png", "skin_1.png"])

    def test_a_clash_in_letter_case_only_never_overwrites(self):
        existing = write_png(os.path.join(self.textures, "Skin.png"), rgba=(0, 0, 255, 255))
        with open(existing, "rb") as f:
            before = f.read()
        source = write_png(os.path.join(self.outside, "skin.png"))
        image = load(source)
        dtt.collect(self.project)
        with open(existing, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertTrue(filecmp.cmp(source, bpy.path.abspath(image.filepath_raw), shallow=False))

    def test_udim_tiles_are_copied_with_their_pattern(self):
        pattern = os.path.join(self.outside, "body.<UDIM>.png")
        for number in (1001, 1002):
            write_png(pattern.replace("<UDIM>", str(number)), rgba=(number % 256, 0, 0, 255))
        image = bpy.data.images.new("body", 2, 2, tiled=True)
        image.tiles.new(1002)
        image.source = 'TILED'
        image.filepath_raw = pattern
        image.use_fake_user = True
        result = dtt.collect(self.project)
        self.assertEqual(result.copied, 1)
        self.assertEqual(sorted(os.listdir(self.textures)), ["body.1001.png", "body.1002.png"])
        self.assertEqual(resolved(image), norm(os.path.join(self.textures, "body.<UDIM>.png")))
        self.assertEqual(dtt.suffixed("body.<UDIM>.png", 1, "<UDIM>"), "body_1.<UDIM>.png")
        self.assertEqual(dtt.suffixed("skin.png", 2, None), "skin_2.png")

    def test_movies_are_copied(self):
        clip = os.path.join(self.outside, "clip.mp4")
        os.makedirs(self.outside, exist_ok=True)
        with open(clip, "wb") as f:
            f.write(b"not really a movie")
        image = bpy.data.images.new("clip", 2, 2)
        image.source = 'FILE'
        image.filepath_raw = clip
        image.source = 'MOVIE'
        image.use_fake_user = True
        self.assertEqual(dtt.collect(self.project).copied, 1)
        self.assertTrue(os.path.isfile(os.path.join(self.textures, "clip.mp4")))

    def test_sequences_and_missing_files_are_only_warned_about(self):
        sequence = load(write_png(os.path.join(self.outside, "frame_0001.png")))
        sequence.source = 'SEQUENCE'
        missing = load(write_png(os.path.join(self.outside, "gone.png")))
        os.remove(os.path.join(self.outside, "gone.png"))
        before = (sequence.filepath_raw, missing.filepath_raw)
        result = dtt.collect(self.project)
        self.assertEqual((result.copied, result.images, len(result.warnings)), (0, [], 2))
        self.assertEqual((sequence.filepath_raw, missing.filepath_raw), before)
        self.assertEqual(os.listdir(self.textures), [])

    def test_packed_generated_linked_and_project_images_are_left_alone(self):
        load(write_png(os.path.join(self.outside, "packed.png"))).pack()
        bpy.data.images.new("generated", 2, 2).use_fake_user = True
        load(write_png(os.path.join(self.textures, "inside.png")))
        library = os.path.join(self.outside, "library.blend")
        lib_image = load(write_png(os.path.join(self.outside, "lib.png")))
        bpy.data.libraries.write(library, {lib_image}, fake_user=True)
        bpy.data.images.remove(lib_image)
        with bpy.data.libraries.load(library, link=True) as (_src, dst):
            dst.images = ["lib.png"]
        self.assertIsNotNone(dst.images[0].library)
        paths = {image.name: image.filepath_raw for image in bpy.data.images}
        result = dtt.collect(self.project)
        self.assertEqual((result.copied, result.images, result.warnings), (0, [], []))
        self.assertEqual({image.name: image.filepath_raw for image in bpy.data.images}, paths)
        self.assertEqual(os.listdir(self.textures), ["inside.png"])

    def test_relink_makes_absolute_project_paths_relative(self):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(self.project.models_folder, "A.blend"))
        image = load(write_png(os.path.join(self.textures, "skin.png")))
        self.assertFalse(image.filepath_raw.startswith("//"))
        self.assertEqual(dtt.relink_absolute([image]), 1)
        self.assertEqual(image.filepath_raw, "//../Textures/skin.png")

    def test_painted_images_are_listed_and_keep_their_paint(self):
        image = load(write_png(os.path.join(self.outside, "paint.png")))
        self.assertEqual(dtt.unsaved_images(), [])
        pixels = list(image.pixels)
        pixels[0] = 0.5
        image.pixels = pixels
        self.assertEqual(dtt.unsaved_images(), ["paint.png"])
        dtt.collect(self.project)
        self.assertTrue(image.is_dirty)
        self.assertAlmostEqual(image.pixels[0], 0.5, places=2)


if __name__ == "__main__":
    tu.run_tests()
