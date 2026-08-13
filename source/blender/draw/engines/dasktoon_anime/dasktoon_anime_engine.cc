/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "BLI_utildefines.h"
#include "BLT_translation.hh"

#include "DNA_scene_types.h"

#include "RE_engine.h"

#include "dasktoon_anime_engine.h"

namespace blender {

static void dasktoon_anime_render(RenderEngine * /*engine*/, Depsgraph * /*depsgraph*/)
{
}

RenderEngineType DRW_engine_viewport_dasktoon_anime_type = {
    /*next*/ nullptr,
    /*prev*/ nullptr,
    /*idname*/ "DASKTOON_ANIME",
    /*name*/ N_("DaskToon Anime Engine"),
    /*flag*/ RE_INTERNAL | RE_USE_STEREO_VIEWPORT | RE_USE_GPU_CONTEXT,
    /*update*/ nullptr,
    /*render*/ &dasktoon_anime_render,
    /*render_frame_finish*/ nullptr,
    /*draw*/ nullptr,
    /*bake*/ nullptr,
    /*view_update*/ nullptr,
    /*view_draw*/ nullptr,
    /*update_script_node*/ nullptr,
    /*update_render_passes*/ nullptr,
    /*update_custom_camera*/ nullptr,
    /*draw_engine*/ nullptr,
    /*rna_ext*/
    {
        /*data*/ nullptr,
        /*srna*/ nullptr,
        /*call*/ nullptr,
    },
};

}  // namespace blender
