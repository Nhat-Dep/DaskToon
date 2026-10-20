# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Guide's steps (docs/superpowers/specs/2026-10-20-dasktoon-model-guide-design.md): nine steps from a new model to
Unity, each with a few lines of advice, the checks that belong to it (checks.CHECKS names each check's step), its main
buttons and its page. A step is done when its checks are all OK; the first and the last are done by what they make
(a mesh; Engine Export marking the scene)."""

from typing import NamedTuple

from bpy.app.translations import pgettext_n as n_

from . import checks

EXPORTED = "dasktoon_guide_exported"  # set on the scene by Engine Export


class Step(NamedTuple):
    id: str  # also its page: pages/<language>/<id lowercased>.html
    title: str
    advice: str
    buttons: tuple  # (operator, label, icon)


STEPS = (
    Step('NEW', n_("New Model"),
         n_("Start from File › New Model with the DaskToon Scene: the sun, the camera and the anime engine are set."),
         (("dasktoon.model_new", n_("New Model"), 'FILE_NEW'),)),
    Step('BODY', n_("Body"),
         n_("Model the body standing on the floor in the middle of the scene, facing the front (-Y), the arms out in "
            "a T or A pose. Check it now and then while you model."), ()),
    Step('HEAD', n_("Head and Face"),
         n_("Build each eye of loose pieces in front of the face (the white, the iris, the lashes) or draw it on the "
            "face texture; draw the mouth on the texture or leave it a crease. Apply a Mirror before rigging."), ()),
    Step('HAIR', n_("Hair"),
         n_("Keep the hair a mesh of its own, with its locks as loose pieces: DaskToon sways each lock."), ()),
    Step('CLOTHES', n_("Clothes"),
         n_("Clothes are meshes of their own, a skirt apart from the top; give them faces of 3 or 4 sides."), ()),
    Step('MATERIALS', n_("Materials"),
         n_("Give every mesh a UV map and DaskToon's shader (the material slot menu › Use DaskToon Shader)."), ()),
    Step('RIG', n_("Rigging"),
         n_("Select the character and use Add › Armature › Anime Humanoid: it rigs, weights and checks in one go."),
         ()),
    Step('EXPRESSIONS', n_("Expressions"),
         n_("Sculpt Eye Expressions closes the eyes and smiles; Fill Empty Expressions fills the shape keys that move "
            "nothing."),
         (("dasktoon.sculpt_eye_expressions", n_("Sculpt Eye Expressions"), 'HIDE_OFF'),
          ("dasktoon.fill_empty_expressions", n_("Fill Empty Expressions"), 'SHAPEKEY_DATA'))),
    Step('UNITY', n_("Unity"),
         n_("File › Export › Engine Export writes the model, its rig file and its clips for Unity."),
         (("export_scene.dasktoon_engine", n_("Engine Export"), 'EXPORT'),)),
)
IDS = tuple(step.id for step in STEPS)


def checks_of(step_id):
    """The ids of the checks that belong to the step."""
    return [name for name, _group, step, _fn, _fixable in checks.CHECKS if step == step_id]


def done(step_id, statuses, scene, meshes):
    """True when the step is done: {check id: status} from the last check, the scene, the character's meshes."""
    if step_id == 'NEW':
        return bool(meshes)
    if step_id == 'UNITY':
        return bool(scene.get(EXPORTED))
    names = checks_of(step_id)
    return bool(names) and all(statuses.get(name) == 'OK' for name in names)


def current(statuses, scene, meshes):
    """The id of the first step not done, None when all are."""
    return next((step.id for step in STEPS if not done(step.id, statuses, scene, meshes)), None)
