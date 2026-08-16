/* SPDX-FileCopyrightText: 2026 DaskToon Authors
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "BLI_rect.h"
#include "BLI_utildefines.h"
#include "BLT_translation.hh"

#include "DNA_scene_types.h"

#include "GPU_framebuffer.hh"

#include "ED_screen.hh"
#include "ED_view3d.hh"

#include "DRW_render.hh"

#include "RE_engine.h"
#include "RE_pipeline.h"

#include "draw_view_data.hh"

#include "engines/eevee/eevee_instance.hh"

#include "dasktoon_anime_engine.h"

namespace blender {

using namespace blender::eevee;

static void dasktoon_anime_render(RenderEngine *engine, Depsgraph *depsgraph)
{
  Instance *instance = nullptr;

  auto dasktoon_render_to_image = [&](RenderEngine *engine, RenderLayer *layer, const rcti /*rect*/) {
    Render *render = engine->re;
    Object *camera_original_ob = RE_GetCamera(engine->re);
    const char *viewname = RE_GetActiveRenderView(engine->re);
    int size[2] = {engine->resolution_x, engine->resolution_y};

    delete instance;
    instance = new Instance();

    rctf view_rect;
    rcti rect;
    RE_GetViewPlane(render, &view_rect, &rect);
    rcti visible_rect = rect;

    instance->init(size, &rect, &visible_rect, engine, depsgraph, camera_original_ob, layer);
    instance->render_frame(engine, layer, viewname);
  };

  auto dasktoon_store_metadata = [&](RenderResult *render_result) {
    instance->store_metadata(render_result);
  };

  DRW_render_to_image(engine, depsgraph, dasktoon_render_to_image, dasktoon_store_metadata);

  delete instance;
}

static void dasktoon_anime_render_update_passes(RenderEngine *engine,
                                               Scene *scene,
                                               ViewLayer *view_layer)
{
  Instance::update_passes(engine, scene, view_layer);
}

RenderEngineType DRW_engine_viewport_dasktoon_anime_type = {
    /*next*/ nullptr,
    /*prev*/ nullptr,
    /*idname*/ "DASKTOON_ANIME",
    /*name*/ N_("DaskToon Anime Engine"),
    /*flag*/ RE_INTERNAL | RE_USE_PREVIEW | RE_USE_STEREO_VIEWPORT | RE_USE_GPU_CONTEXT,
    /*update*/ nullptr,
    /*render*/ &dasktoon_anime_render,
    /*render_frame_finish*/ nullptr,
    /*draw*/ nullptr,
    /*bake*/ nullptr,
    /*view_update*/ nullptr,
    /*view_draw*/ nullptr,
    /*update_script_node*/ nullptr,
    /*update_render_passes*/ &dasktoon_anime_render_update_passes,
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
