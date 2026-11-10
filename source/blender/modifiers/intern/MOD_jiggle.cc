/* SPDX-FileCopyrightText: 2026 DaskToon
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup modifiers
 *
 * DaskToon "Rung mem" (Jiggle): soft parts that wobble when they move and dent when something pushes in, like a
 * pudding (docs/superpowers/specs/2026-11-10-dasktoon-jiggle-design.md). Every vertex springs back towards where the
 * modifiers before put it (its goal); dents spread to the vertices around, the volume of each piece is kept, and the
 * Collision objects of the scene and the capsules of a rig push the vertices out. Like the Spring constraint, nothing
 * is baked: the solved frames are cached by the original object and the modifier, the scene's start frame starts
 * again, the next frame of a solved one steps on, a jump catches up from the closest earlier state.
 */

#include <algorithm>
#include <cmath>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>

#include <fmt/format.h>

#include "BLI_array.hh"
#include "BLI_kdopbvh.hh"
#include "BLI_math_geom.h"
#include "BLI_math_matrix.h"
#include "BLI_math_matrix.hh"
#include "BLI_math_vector.hh"
#include "BLI_span.hh"
#include "BLI_string.h"
#include "BLI_utildefines.h"
#include "BLI_vector.hh"

#include "BLT_translation.hh"

#include "DNA_action_types.h"
#include "DNA_collection_types.h"
#include "DNA_mesh_types.h"
#include "DNA_meshdata_types.h"
#include "DNA_object_force_types.h"
#include "DNA_object_types.h"
#include "DNA_scene_types.h"
#include "DNA_screen_types.h"

#include "BKE_action.hh"
#include "BKE_collision.h"
#include "BKE_deform.hh"
#include "BKE_lib_query.hh"
#include "BKE_mesh.hh"
#include "BKE_modifier.hh"
#include "BKE_object_types.hh"

#include "BLO_read_write.hh"

#include "UI_interface_layout.hh"
#include "UI_resources.hh"

#include "RNA_access.hh"
#include "RNA_prototypes.hh"

#include "DEG_depsgraph.hh"
#include "DEG_depsgraph_build.hh"
#include "DEG_depsgraph_physics.hh"
#include "DEG_depsgraph_query.hh"

#include "MOD_modifiertypes.hh"
#include "MOD_ui_common.hh"
#include "MOD_util.hh"

namespace blender {

Span<JiggleModifierCollider> JiggleModifierData::colliders() const
{
  return {this->colliders_array, this->colliders_num};
}

/* -------------------------------------------------------------------- */
/** \name Modifier data
 * \{ */

static void init_data(ModifierData *md)
{
  JiggleModifierData *jmd = reinterpret_cast<JiggleModifierData *>(md);
  INIT_DEFAULT_STRUCT_AFTER(jmd, modifier);
}

static void copy_data(const ModifierData *md, ModifierData *target, const int flag)
{
  const JiggleModifierData *jmd = reinterpret_cast<const JiggleModifierData *>(md);
  JiggleModifierData *tjmd = reinterpret_cast<JiggleModifierData *>(target);
  BKE_modifier_copydata_generic(md, target, flag);
  tjmd->colliders_array = jmd->colliders_array ?
                              static_cast<JiggleModifierCollider *>(
                                  MEM_dupalloc(jmd->colliders_array)) :
                              nullptr;
}

static void free_data(ModifierData *md)
{
  JiggleModifierData *jmd = reinterpret_cast<JiggleModifierData *>(md);
  MEM_SAFE_DELETE(jmd->colliders_array);
  jmd->colliders_num = 0;
}

static void required_data_mask(ModifierData * /*md*/, CustomData_MeshMasks *r_cddata_masks)
{
  /* The free weights and the rig colliders' skip test both read the vertex groups. */
  r_cddata_masks->vmask |= CD_MASK_MDEFORMVERT;
}

static bool depends_on_time(Scene * /*scene*/, ModifierData * /*md*/)
{
  return true;
}

static void foreach_ID_link(ModifierData *md, Object *ob, IDWalkFunc walk, void *user_data)
{
  JiggleModifierData *jmd = reinterpret_cast<JiggleModifierData *>(md);
  walk(user_data, ob, reinterpret_cast<ID **>(&jmd->collision_collection), IDWALK_CB_NOP);
  walk(user_data, ob, reinterpret_cast<ID **>(&jmd->rig), IDWALK_CB_NOP);
}

static void update_depsgraph(ModifierData *md, const ModifierUpdateDepsgraphContext *ctx)
{
  JiggleModifierData *jmd = reinterpret_cast<JiggleModifierData *>(md);
  DEG_add_collision_relations(ctx->node,
                              ctx->object,
                              jmd->collision_collection,
                              eModifierType_Collision,
                              nullptr,
                              "Jiggle Collision");
  if (jmd->rig != nullptr && jmd->rig != ctx->object && jmd->colliders_num > 0) {
    DEG_add_object_relation(ctx->node, jmd->rig, DEG_OB_COMP_EVAL_POSE, "Jiggle Rig Colliders");
    DEG_add_object_relation(ctx->node, jmd->rig, DEG_OB_COMP_TRANSFORM, "Jiggle Rig Colliders");
  }
  /* The jiggle runs in world space: the object moving makes it lag. */
  DEG_add_depends_on_transform_relation(ctx->node, "Jiggle Modifier");
}

/** \} */

/* -------------------------------------------------------------------- */
/** \name Cache
 * \{ */

/** All of the solver's state at a whole frame, every vertex, world space. */
struct JiggleState {
  Array<float3> position;
  Array<float3> velocity;
  Array<float3> goal;
  /** Where each rig capsule was (head, tail): the next frame sweeps it from there. */
  Vector<std::pair<float3, float3>> capsules;
};

/** What a frame showed: the offset from the goal of each free vertex (world space). */
struct JiggleFrame {
  Array<float3> offset;
  uint64_t inputs = 0;
  /** Stepped from the frame before it (not caught up over a jump). */
  bool exact = false;
};

struct JiggleCacheEntry {
  std::mutex mutex;
  uint64_t setup = 0;
  /* The soft part of the mesh, made again only when the mesh, the weights or the settings change: the free vertices
   * and the ones sharing a face or an edge with them (those hold still but close the soft part's faces). Every frame
   * works on these alone, so the rest of a character costs nothing. Indices below are into `region` ("local"). */
  bool has_region = false;
  /** Local vertex -> mesh vertex. */
  Array<int> region;
  /** The free vertices: local and mesh indices. */
  Array<int> free_local;
  Array<int> free_mesh;
  Array<float> freedom;
  /** Free neighbours of each local vertex along the edges. */
  Array<int> neighbour_offsets;
  Array<int> neighbours;
  /** The edges and triangles that touch a free vertex. */
  Array<int2> edges;
  Array<int3> tris;
  /** The piece (connected) of each triangle and each vertex (-1: in no triangle). */
  Array<int> tri_piece;
  Array<int> vertex_piece;
  int pieces_num = 0;
  std::map<int, JiggleState> states;
  std::map<int, JiggleFrame> frames;
  /** For each collider (key), the vertices that started inside it: it never pushes those. */
  std::unordered_map<uint64_t, Array<bool>> started_inside;
};

constexpr int JIGGLE_MAX_CATCH_UP = 300;
constexpr int JIGGLE_CHECKPOINT = 10;
constexpr int JIGGLE_MAX_CHECKPOINTS = 16;
constexpr int JIGGLE_MAX_FRAMES = 2000;
/** A vertex showing less of the wobble than this is not pushed by the colliders (its shown share is too small to
 * carry the push back into the wobble). */
constexpr float JIGGLE_MIN_SHOWN = 0.25f;
/** The steepest the shown wobble may change along the surface (metres per metre) where the freedom changes. */
constexpr float JIGGLE_FOLD = 0.7f;
/** A rig capsule closer than this share of its radius (plus the distance) to the skin at the start lies under it. */
constexpr float JIGGLE_UNDER_SKIN = 0.25f;
/** Share of a step's motion along a collider's surface taken back while touching it. */
constexpr float JIGGLE_FRICTION = 0.8f;

static std::mutex &jiggle_mutex()
{
  static std::mutex mutex;
  return mutex;
}

/* Plain std containers: the cache lives until exit, outside guarded memory. */
static std::unordered_map<std::string, std::shared_ptr<JiggleCacheEntry>> &jiggle_cache()
{
  static std::unordered_map<std::string, std::shared_ptr<JiggleCacheEntry>> cache;
  return cache;
}

static std::shared_ptr<JiggleCacheEntry> jiggle_entry(const Object *ob, const ModifierData *md)
{
  const std::string key = std::to_string(DEG_get_original(ob)->id.session_uid) + ":" +
                          std::to_string(md->persistent_uid) + ":" + md->name;
  std::scoped_lock lock(jiggle_mutex());
  std::shared_ptr<JiggleCacheEntry> &entry = jiggle_cache()[key];
  if (!entry) {
    entry = std::make_shared<JiggleCacheEntry>();
  }
  return entry;
}

struct JiggleHash {
  uint64_t value = 1469598103934665603ULL;
  void add(const uint64_t v)
  {
    value = (value ^ v) * 1099511628211ULL;
  }
  void add(const float f)
  {
    uint32_t bits;
    memcpy(&bits, &f, sizeof(bits));
    add(uint64_t(bits));
  }
  void add(const float3 &v)
  {
    add(v.x);
    add(v.y);
    add(v.z);
  }
  void add(const char *str)
  {
    for (; *str; str++) {
      add(uint64_t(uint8_t(*str)));
    }
    add(uint64_t(0xff));
  }
};

/** \} */

/* -------------------------------------------------------------------- */
/** \name Solver
 * \{ */

/** A rig capsule: `a`, `b` where it is at the time being stepped; it ends the frame at `a1`, `b1`. */
struct JiggleCapsule {
  float3 a;
  float3 b;
  float3 a1;
  float3 b1;
  float radius;
  uint64_t key;
};

/** A Collision object's triangles: they go from `start` to `end` over the frame (the same when it did not move or
 * the frame is caught up over a jump). */
struct JiggleMeshCollider {
  Span<float3> start;
  Span<float3> end;
  Span<int3> tris;
  bool moving = false;
  Array<float3> positions;
  BVHTree *tree = nullptr;
  uint64_t key;
};

struct JiggleNearest {
  const JiggleMeshCollider *collider;
};

static void jiggle_nearest_tri(void *userdata, int index, const float co[3], BVHTreeNearest *nearest)
{
  const JiggleMeshCollider &collider = *static_cast<JiggleNearest *>(userdata)->collider;
  const int3 tri = collider.tris[index];
  const float3 &v0 = collider.positions[tri[0]];
  const float3 &v1 = collider.positions[tri[1]];
  const float3 &v2 = collider.positions[tri[2]];
  float3 closest;
  closest_on_tri_to_point_v3(closest, co, v0, v1, v2);
  const float dist_sq = math::distance_squared(closest, float3(co));
  if (dist_sq < nearest->dist_sq) {
    nearest->index = index;
    nearest->dist_sq = dist_sq;
    copy_v3_v3(nearest->co, closest);
    normal_tri_v3(nearest->no, v0, v1, v2);
  }
}

/** The collider's triangles at `t` (0 start, 1 end of the frame), in a fresh tree. */
static void jiggle_place_mesh(JiggleMeshCollider &collider, const float t)
{
  if (collider.tree != nullptr && !collider.moving) {
    return;
  }
  collider.positions.reinitialize(collider.end.size());
  for (const int i : collider.end.index_range()) {
    collider.positions[i] = collider.moving ? math::interpolate(collider.start[i], collider.end[i], t) :
                                              collider.end[i];
  }
  if (collider.tree != nullptr) {
    BLI_bvhtree_free(collider.tree);
  }
  collider.tree = BLI_bvhtree_new(int(collider.tris.size()), 0.0f, 2, 6);
  for (const int i : collider.tris.index_range()) {
    const int3 tri = collider.tris[i];
    float co[3][3];
    copy_v3_v3(co[0], collider.positions[tri[0]]);
    copy_v3_v3(co[1], collider.positions[tri[1]]);
    copy_v3_v3(co[2], collider.positions[tri[2]]);
    BLI_bvhtree_insert(collider.tree, i, co[0], 3);
  }
  BLI_bvhtree_balance(collider.tree);
}

/** The signed distance of `point` from the collider's surface (negative inside) and the surface normal there; false
 * when no triangle is within `search`. */
static bool jiggle_mesh_distance(const JiggleMeshCollider &collider,
                                 const float3 &point,
                                 const float search,
                                 float &r_distance,
                                 float3 &r_normal)
{
  BVHTreeNearest nearest;
  nearest.index = -1;
  nearest.dist_sq = search * search;
  JiggleNearest data = {&collider};
  BLI_bvhtree_find_nearest(collider.tree, point, &nearest, jiggle_nearest_tri, &data);
  if (nearest.index < 0) {
    return false;
  }
  r_normal = float3(nearest.no);
  r_distance = math::dot(point - float3(nearest.co), r_normal);
  return true;
}

/** The signed distance of `point` from the capsule's surface and the direction out of it. */
static float jiggle_capsule_distance(const JiggleCapsule &capsule, const float3 &point, float3 &r_out)
{
  const float3 axis = capsule.b - capsule.a;
  const float length2 = math::dot(axis, axis);
  const float t = length2 < 1e-18f ?
                      0.0f :
                      std::clamp(math::dot(point - capsule.a, axis) / length2, 0.0f, 1.0f);
  const float3 away = point - (capsule.a + axis * t);
  const float gap = math::length(away);
  if (gap < 1e-12f) {
    r_out = float3(0.0f, 0.0f, 1.0f);
    return -capsule.radius;
  }
  r_out = away / gap;
  return gap - capsule.radius;
}

struct JiggleSolver {
  const JiggleModifierData *jmd;
  int verts_num = 0;
  /** How free each vertex is, 0 follows its goal. */
  Array<float> freedom;
  /** Neighbours along the edges (offsets into `neighbours`). */
  Array<int> neighbour_offsets;
  Array<int> neighbours;
  Span<int3> tris;
  /** The piece (connected by edges) of each triangle and each vertex (-1: in no triangle), the number of pieces. */
  Array<int> tri_piece;
  Array<int> vertex_piece;
  int pieces_num = 0;
  /** Bounding box diagonal of the goals: the size of the thing (a jump further than it starts again). */
  float size = 1.0f;
  /** Bounding box diagonal of the free vertices' goals: the soft part's size (it never strays further than a share
   * of it). */
  float free_size = 1.0f;
  /** The furthest a wobble may go before the shown surface folds where the freedom changes fastest (the freedom times
   * the wobble changes by at most JIGGLE_FOLD per unit of length there). */
  float fold_limit = FLT_MAX;

  Vector<JiggleCapsule> capsules;
  /** Per capsule, the vertices its own bone moves (it does not push those). */
  Vector<Array<bool>> capsule_skip;
  Vector<JiggleMeshCollider> meshes;
  /** The cache entry's "started inside" vertices of every collider. */
  std::unordered_map<uint64_t, Array<bool>> *started_inside = nullptr;

  float omega = 0.0f;
  int substeps = 1;

  ~JiggleSolver()
  {
    for (JiggleMeshCollider &collider : meshes) {
      if (collider.tree) {
        BLI_bvhtree_free(collider.tree);
      }
    }
  }

  /** The colliders where they are at `t` of the frame, sweeping the capsules from `from` (where they were). */
  void place_colliders(float t, Span<std::pair<float3, float3>> from, bool sweep);
  void collide(MutableSpan<float3> position, Span<float3> before) const;
  void step(JiggleState &state, Span<float3> goal_new, float dt, bool sweep);
  void reset(JiggleState &state, Span<float3> goal);
};

void JiggleSolver::place_colliders(const float t,
                                   const Span<std::pair<float3, float3>> from,
                                   const bool sweep)
{
  const bool use_from = sweep && from.size() == capsules.size();
  for (const int c : capsules.index_range()) {
    JiggleCapsule &capsule = capsules[c];
    capsule.a = use_from ? math::interpolate(from[c].first, capsule.a1, t) : capsule.a1;
    capsule.b = use_from ? math::interpolate(from[c].second, capsule.b1, t) : capsule.b1;
  }
  for (JiggleMeshCollider &collider : meshes) {
    const bool moving = collider.moving;
    collider.moving = moving && sweep;
    jiggle_place_mesh(collider, t);
    collider.moving = moving;
  }
}

/** Out of every collider, keeping `distance` from its surface; a collider the vertex started inside is left out. */
void JiggleSolver::collide(MutableSpan<float3> position, const Span<float3> before) const
{
  if (capsules.is_empty() && meshes.is_empty()) {
    return;
  }
  const float distance = std::max(jmd->distance, 0.0f);
  const float search = size * 0.5f + distance;
  for (const int i : IndexRange(verts_num)) {
    if (freedom[i] < JIGGLE_MIN_SHOWN) {
      continue;
    }
    float3 p = position[i];
    /* The normal of the last collider that pushed: friction there. */
    float3 contact(0.0f);
    for (const int c : capsules.index_range()) {
      const JiggleCapsule &capsule = capsules[c];
      if (capsule_skip[c][i]) {
        continue;
      }
      const auto inside = started_inside->find(capsule.key);
      if (inside != started_inside->end() && inside->second[i]) {
        continue;
      }
      float3 out;
      const float gap = jiggle_capsule_distance(capsule, p, out);
      if (gap >= distance) {
        continue;
      }
      /* A vertex that was outside before this step goes back out on the side it came from: a thin capsule is not
       * crossed in one step (a vertex on the capsule's axis has no side of its own). */
      float3 out_before;
      if (!before.is_empty() && jiggle_capsule_distance(capsule, before[i], out_before) >= 0.0f) {
        const float3 axis = capsule.b - capsule.a;
        const float length2 = math::dot(axis, axis);
        const float t = length2 < 1e-18f ?
                            0.0f :
                            std::clamp(math::dot(p - capsule.a, axis) / length2, 0.0f, 1.0f);
        const float3 centre = capsule.a + axis * t;
        if (math::dot(p - centre, out_before) < capsule.radius + distance) {
          p = p + out_before * (capsule.radius + distance - math::dot(p - centre, out_before));
          contact = out_before;
          continue;
        }
      }
      p += out * (distance - gap);
      contact = out;
    }
    for (const JiggleMeshCollider &collider : meshes) {
      const auto inside = started_inside->find(collider.key);
      if (inside != started_inside->end() && inside->second[i]) {
        continue;
      }
      float gap;
      float3 normal;
      if (jiggle_mesh_distance(collider, p, search, gap, normal) && gap < distance) {
        p += normal * (distance - gap);
        contact = normal;
      }
    }
    /* Friction: skin pressed by a finger does not slide off it (pressed on the round tip, nothing else would hold
     * it there). Most of the step's motion along the surface is taken back. */
    if (!before.is_empty() && math::length_squared(contact) > 0.0f) {
      const float3 moved = p - before[i];
      const float3 along = moved - contact * math::dot(moved, contact);
      p -= along * JIGGLE_FRICTION;
    }
    position[i] = p;
  }
}

static Vector<std::pair<float3, float3>> capsule_ends(const Span<JiggleCapsule> capsules)
{
  Vector<std::pair<float3, float3>> out;
  for (const JiggleCapsule &capsule : capsules) {
    out.append({capsule.a1, capsule.b1});
  }
  return out;
}

/* Every free vertex wobbles alike (`state.position`, one spring for all); a vertex shows `freedom` of its wobble:
 * shown = goal + freedom * (position - goal). The colliders and the volume work on the shown shape. A freedom that
 * set the stiffness instead let the edge of a soft part wobble at its own pace and tore a breast into a cone. */
static void jiggle_shown(const Span<float> freedom,
                         const Span<float3> goal,
                         const Span<float3> position,
                         MutableSpan<float3> r_shown)
{
  for (const int i : goal.index_range()) {
    r_shown[i] = goal[i] + (position[i] - goal[i]) * freedom[i];
  }
}

/** The wobble of every vertex the colliders pushed, from its pushed shown place. */
static void jiggle_from_shown(const Span<float> freedom,
                              const Span<float3> goal,
                              const Span<float3> shown_before,
                              const Span<float3> shown,
                              MutableSpan<float3> position)
{
  for (const int i : goal.index_range()) {
    if (freedom[i] >= JIGGLE_MIN_SHOWN && shown[i] != shown_before[i]) {
      position[i] = goal[i] + (shown[i] - goal[i]) / freedom[i];
    }
  }
}

void JiggleSolver::reset(JiggleState &state, Span<float3> goal)
{
  state.position = Array<float3>(goal);
  state.velocity = Array<float3>(verts_num, float3(0.0f));
  state.goal = Array<float3>(goal);
  state.capsules = capsule_ends(capsules);
  place_colliders(1.0f, {}, false);
  /* What starts inside a collider or closer to it than the distance it keeps (the plate under a pudding, the chest
   * under the arm) is never pushed by it. A capsule starting just under the skin (within a quarter of its radius more)
   * is the inside of that body, the ribcage under a breast: the skin lagging into it is not thrown out either. */
  started_inside->clear();
  const float distance = std::max(jmd->distance, 0.0f);
  const float search = size * 0.5f + distance;
  for (const JiggleCapsule &capsule : capsules) {
    Array<bool> inside(verts_num, false);
    for (const int i : IndexRange(verts_num)) {
      float3 out;
      inside[i] = jiggle_capsule_distance(capsule, goal[i], out) <
                  distance + JIGGLE_UNDER_SKIN * capsule.radius;
    }
    started_inside->insert_or_assign(capsule.key, std::move(inside));
  }
  for (const JiggleMeshCollider &collider : meshes) {
    Array<bool> inside(verts_num, false);
    for (const int i : IndexRange(verts_num)) {
      float gap;
      float3 normal;
      inside[i] = jiggle_mesh_distance(collider, goal[i], search, gap, normal) && gap < distance;
    }
    started_inside->insert_or_assign(collider.key, std::move(inside));
  }
  const Array<float3> before(goal);
  Array<float3> shown(goal);
  collide(shown, {});
  jiggle_from_shown(freedom, goal, before, shown, state.position);
}

void JiggleSolver::step(JiggleState &state, Span<float3> goal_new, const float dt, const bool sweep)
{
  const Array<float3> goal_old = state.goal;
  MutableSpan<float3> p = state.position;
  MutableSpan<float3> v = state.velocity;
  const Vector<std::pair<float3, float3>> capsules_from = state.capsules;
  state.goal = Array<float3>(goal_new);
  state.capsules = capsule_ends(capsules);

  Array<float3> shown(verts_num);
  Array<float3> shown_start(verts_num);
  Array<float3> shown_pushed(verts_num);

  /* A jump (a cut, the object put somewhere else) starts again instead of flying. */
  float jump = 0.0f;
  for (const int i : IndexRange(verts_num)) {
    jump = std::max(jump, math::distance(goal_new[i], goal_old[i]));
  }
  if (jump > size) {
    p.copy_from(goal_new);
    v.fill(float3(0.0f));
    place_colliders(1.0f, {}, false);
    shown.as_mutable_span().copy_from(goal_new);
    shown_pushed.as_mutable_span().copy_from(goal_new);
    collide(shown_pushed, {});
    jiggle_from_shown(freedom, goal_new, shown, shown_pushed, p);
    return;
  }

  const float h = dt / float(substeps);
  const float follow = std::clamp(jmd->follow, 0.0f, 1.0f);
  const float zeta = std::clamp(jmd->damping, 0.0f, 1.0f);
  const float om = std::min(omega, 1.5f / h);
  const float spread = 1.0f - std::pow(1.0f - std::clamp(jmd->spread, 0.0f, 1.0f), 1.0f / substeps);
  const float keep = 1.0f - std::pow(1.0f - std::clamp(jmd->volume, 0.0f, 1.0f), 1.0f / substeps);
  const float limit = std::min(free_size * 0.25f, fold_limit);

  /* `v` is the velocity relative to the share of the goal's motion the jiggle follows: Follow Motion 1 carries the
   * vertices along with the goals and the springs only see what collides. */
  Array<float3> goal_velocity(verts_num);
  for (const int i : IndexRange(verts_num)) {
    goal_velocity[i] = (goal_new[i] - goal_old[i]) / dt;
  }

  Array<float3> before(verts_num);
  Array<float3> goal(verts_num);
  Array<float3> start(verts_num);
  Array<float3> offset(verts_num);
  Array<float> volume(pieces_num);
  Array<float> rest(pieces_num);
  Array<float> weight_sum(pieces_num);
  Array<float3> gradient(verts_num);
  for (const int s : IndexRange(substeps)) {
    const float t0 = float(s) / float(substeps);
    const float t = float(s + 1) / float(substeps);
    for (const int i : IndexRange(verts_num)) {
      before[i] = math::interpolate(goal_old[i], goal_new[i], t0);
      goal[i] = math::interpolate(goal_old[i], goal_new[i], t);
    }
    start.as_mutable_span().copy_from(p);
    jiggle_shown(freedom, before, start, shown_start);

    /* Springs back to the goal (semi-implicit Euler, the force from the start of the step). */
    for (const int i : IndexRange(verts_num)) {
      if (freedom[i] <= 0.0f) {
        p[i] = goal[i];
        v[i] = goal_velocity[i] * (1.0f - follow);
        continue;
      }
      const float3 a = -(om * om) * (p[i] - before[i]) -
                       (2.0f * zeta * om) * (v[i] - goal_velocity[i] * (1.0f - follow));
      v[i] += a * h;
      p[i] += v[i] * h + goal_velocity[i] * (follow * h);
    }

    /* A dent spreads: each wobble is pulled towards the average of its free neighbours'. */
    if (spread > 0.0f) {
      for (const int i : IndexRange(verts_num)) {
        offset[i] = p[i] - goal[i];
      }
      for (const int i : IndexRange(verts_num)) {
        if (freedom[i] <= 0.0f) {
          continue;
        }
        float3 sum(0.0f);
        int count = 0;
        for (int n = neighbour_offsets[i]; n < neighbour_offsets[i + 1]; n++) {
          if (freedom[neighbours[n]] > 0.0f) {
            sum += offset[neighbours[n]];
            count++;
          }
        }
        if (count > 0) {
          p[i] += (sum / float(count) - offset[i]) * spread;
        }
      }
    }

    /* Keeps the volume of each piece's shown shape: pushed in here, it bulges out there. */
    if (keep > 0.0f && pieces_num > 0 && !tris.is_empty()) {
      jiggle_shown(freedom, goal, p, shown);
      volume.fill(0.0f);
      rest.fill(0.0f);
      weight_sum.fill(0.0f);
      gradient.fill(float3(0.0f));
      for (const int t_index : tris.index_range()) {
        const int3 tri = tris[t_index];
        const int piece = tri_piece[t_index];
        volume[piece] += math::dot(shown[tri[0]], math::cross(shown[tri[1]], shown[tri[2]])) / 6.0f;
        rest[piece] += math::dot(goal[tri[0]], math::cross(goal[tri[1]], goal[tri[2]])) / 6.0f;
        gradient[tri[0]] += math::cross(shown[tri[1]], shown[tri[2]]) / 6.0f;
        gradient[tri[1]] += math::cross(shown[tri[2]], shown[tri[0]]) / 6.0f;
        gradient[tri[2]] += math::cross(shown[tri[0]], shown[tri[1]]) / 6.0f;
      }
      for (const int i : IndexRange(verts_num)) {
        if (vertex_piece[i] >= 0) {
          weight_sum[vertex_piece[i]] += freedom[i] * freedom[i] * math::length_squared(gradient[i]);
        }
      }
      for (const int i : IndexRange(verts_num)) {
        const int piece = vertex_piece[i];
        if (piece < 0 || freedom[i] <= 0.0f || weight_sum[piece] < 1e-20f) {
          continue;
        }
        const float lambda = -(volume[piece] - rest[piece]) / weight_sum[piece];
        /* The shown place moves by freedom * this: the volume comes back at the shown shape. */
        p[i] += gradient[i] * (keep * lambda * freedom[i]);
      }
    }

    /* Never further from the goal than a quarter of the soft part's size (before the colliders, which win). */
    for (const int i : IndexRange(verts_num)) {
      const float3 d = p[i] - goal[i];
      const float length = math::length(d);
      if (length > limit) {
        p[i] = goal[i] + d * (limit / length);
      }
    }

    /* The colliders swept through the frame step by step (a fast hand cannot jump over a vertex), pushing the shown
     * shape. */
    place_colliders(t, capsules_from, sweep);
    jiggle_shown(freedom, goal, p, shown);
    shown_pushed.as_mutable_span().copy_from(shown);
    collide(shown_pushed, shown_start);
    jiggle_from_shown(freedom, goal, shown, shown_pushed, p);

    for (const int i : IndexRange(verts_num)) {
      if (freedom[i] > 0.0f) {
        v[i] = (p[i] - start[i]) / h - goal_velocity[i] * follow;
      }
    }
  }
}

/** \} */

/* -------------------------------------------------------------------- */
/** \name Evaluation
 * \{ */

/** The soft part of the mesh into `entry` (see JiggleCacheEntry). */
static void build_region(JiggleCacheEntry &entry, const Mesh &mesh, const Span<float> freedom)
{
  const int verts_num = mesh.verts_num;
  Array<bool> in_region(verts_num, false);
  for (const int i : IndexRange(verts_num)) {
    in_region[i] = freedom[i] > 0.0f;
  }
  Array<int3> all_tris(mesh.corner_tris().size());
  bke::mesh::vert_tris_from_corner_tris(mesh.corner_verts(), mesh.corner_tris(), all_tris);
  Vector<int3> tris;
  for (const int3 &tri : all_tris) {
    if (freedom[tri[0]] > 0.0f || freedom[tri[1]] > 0.0f || freedom[tri[2]] > 0.0f) {
      tris.append(tri);
    }
  }
  Vector<int2> edges;
  for (const int2 &edge : mesh.edges()) {
    if (freedom[edge[0]] > 0.0f || freedom[edge[1]] > 0.0f) {
      edges.append(edge);
    }
  }
  for (const int3 &tri : tris) {
    in_region[tri[0]] = in_region[tri[1]] = in_region[tri[2]] = true;
  }
  for (const int2 &edge : edges) {
    in_region[edge[0]] = in_region[edge[1]] = true;
  }
  Array<int> local(verts_num, -1);
  Vector<int> region;
  for (const int i : IndexRange(verts_num)) {
    if (in_region[i]) {
      local[i] = region.size();
      region.append(i);
    }
  }
  const int count = region.size();
  entry.region = Array<int>(region.as_span());
  entry.freedom.reinitialize(count);
  Vector<int> free_local, free_mesh;
  for (const int l : IndexRange(count)) {
    entry.freedom[l] = freedom[region[l]];
    if (entry.freedom[l] > 0.0f) {
      free_local.append(l);
      free_mesh.append(region[l]);
    }
  }
  entry.free_local = Array<int>(free_local.as_span());
  entry.free_mesh = Array<int>(free_mesh.as_span());
  entry.tris.reinitialize(tris.size());
  for (const int t : tris.index_range()) {
    entry.tris[t] = int3(local[tris[t][0]], local[tris[t][1]], local[tris[t][2]]);
  }
  entry.edges.reinitialize(edges.size());
  for (const int e : edges.index_range()) {
    entry.edges[e] = int2(local[edges[e][0]], local[edges[e][1]]);
  }

  /* Free neighbours (spread). */
  Array<int> counts(count, 0);
  for (const int2 &edge : entry.edges) {
    if (entry.freedom[edge[0]] > 0.0f && entry.freedom[edge[1]] > 0.0f) {
      counts[edge[0]]++;
      counts[edge[1]]++;
    }
  }
  entry.neighbour_offsets.reinitialize(count + 1);
  int total = 0;
  for (const int l : IndexRange(count)) {
    entry.neighbour_offsets[l] = total;
    total += counts[l];
  }
  entry.neighbour_offsets[count] = total;
  entry.neighbours.reinitialize(total);
  Array<int> fill(count, 0);
  for (const int2 &edge : entry.edges) {
    if (entry.freedom[edge[0]] > 0.0f && entry.freedom[edge[1]] > 0.0f) {
      entry.neighbours[entry.neighbour_offsets[edge[0]] + fill[edge[0]]++] = edge[1];
      entry.neighbours[entry.neighbour_offsets[edge[1]] + fill[edge[1]]++] = edge[0];
    }
  }

  /* Pieces: connected through the edges and triangles kept. */
  Array<int> parent(count);
  for (const int l : IndexRange(count)) {
    parent[l] = l;
  }
  const auto find = [&](int l) {
    while (parent[l] != l) {
      parent[l] = parent[parent[l]];
      l = parent[l];
    }
    return l;
  };
  const auto join = [&](const int a, const int b) { parent[find(a)] = find(b); };
  for (const int2 &edge : entry.edges) {
    join(edge[0], edge[1]);
  }
  for (const int3 &tri : entry.tris) {
    join(tri[0], tri[1]);
    join(tri[1], tri[2]);
  }
  Array<int> piece_of_root(count, -1);
  int pieces = 0;
  for (const int l : IndexRange(count)) {
    const int root = find(l);
    if (piece_of_root[root] < 0) {
      piece_of_root[root] = pieces++;
    }
  }
  entry.pieces_num = pieces;
  entry.tri_piece.reinitialize(entry.tris.size());
  entry.vertex_piece.reinitialize(count);
  entry.vertex_piece.fill(-1);
  for (const int t : entry.tris.index_range()) {
    entry.tri_piece[t] = piece_of_root[find(entry.tris[t][0])];
    for (const int corner : IndexRange(3)) {
      entry.vertex_piece[entry.tris[t][corner]] = entry.tri_piece[t];
    }
  }
  entry.has_region = true;
}

/** How free each mesh vertex is (the vertex group, Pin Bottom). */
static Array<float> build_freedom(const JiggleModifierData &jmd,
                                  const Object *ob,
                                  const Mesh &mesh,
                                  Span<float3> local_positions)
{
  const int verts_num = mesh.verts_num;
  Array<float> freedom(verts_num, 1.0f);
  const MDeformVert *dvert = nullptr;
  int defgrp_index = -1;
  MOD_get_vgroup(ob, &mesh, jmd.defgrp_name, &dvert, &defgrp_index);
  const bool invert = (jmd.flag & MOD_JIGGLE_INVERT_VGROUP) != 0;
  if (jmd.defgrp_name[0] != '\0') {
    for (const int i : IndexRange(verts_num)) {
      const float w = (dvert && defgrp_index >= 0) ?
                          BKE_defvert_find_weight(&dvert[i], defgrp_index) :
                          0.0f;
      freedom[i] = std::clamp(invert ? 1.0f - w : w, 0.0f, 1.0f);
    }
  }
  if ((jmd.flag & MOD_JIGGLE_PIN_BOTTOM) != 0 && verts_num > 0) {
    float low = FLT_MAX, high = -FLT_MAX;
    for (const float3 &co : local_positions) {
      low = std::min(low, co.z);
      high = std::max(high, co.z);
    }
    const float height = high - low;
    for (const int i : IndexRange(verts_num)) {
      freedom[i] *= height > 1e-8f ? (local_positions[i].z - low) / height : 0.0f;
    }
  }
  for (float &w : freedom) {
    if (w < 1e-4f) {
      w = 0.0f;
    }
  }
  return freedom;
}

static void build_colliders(JiggleSolver &solver,
                            const JiggleModifierData &jmd,
                            const ModifierEvalContext *ctx,
                            const Mesh &mesh,
                            const Span<int> region,
                            const float ctime,
                            JiggleHash &inputs)
{
  /* The rig's capsules: not pushing the vertices their own bone moves. */
  const Object *rig = jmd.rig;
  if (rig != nullptr && rig->type == OB_ARMATURE && rig->pose != nullptr) {
    const float (*world)[4] = rig->object_to_world().ptr();
    const float scale = mat4_to_scale(world);
    const Span<MDeformVert> dverts = mesh.deform_verts();
    for (const int c : jmd.colliders().index_range()) {
      const JiggleModifierCollider &collider = jmd.colliders()[c];
      const bPoseChannel *head = BKE_pose_channel_find_name(rig->pose, collider.bone);
      const bPoseChannel *tail = collider.bone_end[0] ?
                                     BKE_pose_channel_find_name(rig->pose, collider.bone_end) :
                                     head;
      if (head == nullptr || tail == nullptr) {
        continue;
      }
      JiggleCapsule capsule;
      mul_v3_m4v3(capsule.a1, world, head->pose_head);
      mul_v3_m4v3(capsule.b1, world, tail->pose_tail);
      capsule.a = capsule.a1;
      capsule.b = capsule.b1;
      capsule.radius = collider.radius * scale;
      capsule.key = 0x100000000ULL + uint64_t(c);
      inputs.add(capsule.a1);
      inputs.add(capsule.b1);
      inputs.add(capsule.radius);

      Array<bool> skip(region.size(), false);
      if (!dverts.is_empty()) {
        const int groups[2] = {BKE_id_defgroup_name_index(&mesh.id, collider.bone),
                               collider.bone_end[0] ?
                                   BKE_id_defgroup_name_index(&mesh.id, collider.bone_end) :
                                   -1};
        for (const int l : region.index_range()) {
          for (const int group : groups) {
            if (group >= 0 && BKE_defvert_find_weight(&dverts[region[l]], group) > 0.05f) {
              skip[l] = true;
            }
          }
        }
      }
      solver.capsules.append(capsule);
      solver.capsule_skip.append(std::move(skip));
    }
  }

  /* Objects with Collision. */
  uint numcollobj = 0;
  Object **collobjs = BKE_collision_objects_create(
      ctx->depsgraph, ctx->object, jmd.collision_collection, &numcollobj, eModifierType_Collision);
  for (uint i = 0; i < numcollobj; i++) {
    Object *collob = collobjs[i];
    CollisionModifierData *collmd = reinterpret_cast<CollisionModifierData *>(
        BKE_modifiers_findby_type(collob, eModifierType_Collision));
    if (collmd == nullptr || collmd->xnew == nullptr || collmd->vert_tris == nullptr ||
        collmd->tri_num == 0)
    {
      continue;
    }
    JiggleMeshCollider collider;
    collider.end = Span(reinterpret_cast<const float3 *>(collmd->xnew), collmd->mvert_num);
    /* Swept from the frame before only when that is where it was evaluated last. */
    const bool from_before = collmd->x != nullptr && !collmd->is_static &&
                             std::fabs(collmd->time_xnew - ctime) < 1e-4f &&
                             std::fabs(collmd->time_xnew - collmd->time_x - 1.0f) < 1e-4f;
    collider.start = from_before ?
                         Span(reinterpret_cast<const float3 *>(collmd->x), collmd->mvert_num) :
                         collider.end;
    collider.moving = from_before;
    collider.tris = Span(reinterpret_cast<const int3 *>(collmd->vert_tris), collmd->tri_num);
    collider.key = DEG_get_original(collob)->id.session_uid;
    inputs.add(collider.key);
    for (const float3 &co : collider.end) {
      inputs.add(co);
    }
    solver.meshes.append(std::move(collider));
  }
  BKE_collision_objects_free(collobjs);
}

static uint64_t setup_hash(const JiggleModifierData &jmd, const Span<float> freedom, const Mesh &mesh)
{
  JiggleHash hash;
  hash.add(uint64_t(mesh.verts_num));
  hash.add(uint64_t(mesh.edges_num));
  hash.add(uint64_t(mesh.faces_num));
  hash.add(uint64_t(mesh.corners_num));
  hash.add(jmd.frequency);
  hash.add(jmd.damping);
  hash.add(jmd.spread);
  hash.add(jmd.volume);
  hash.add(jmd.follow);
  hash.add(jmd.distance);
  hash.add(uint64_t(jmd.substeps));
  hash.add(uint64_t(jmd.flag));
  for (const JiggleModifierCollider &collider : jmd.colliders()) {
    hash.add(collider.bone);
    hash.add(collider.bone_end);
    hash.add(collider.radius);
  }
  for (const float w : freedom) {
    hash.add(w);
  }
  return hash.value;
}

static void store_frame(JiggleCacheEntry &entry,
                        const int frame,
                        const JiggleState &state,
                        const Span<float> freedom,
                        const uint64_t inputs,
                        const bool exact)
{
  JiggleFrame out;
  out.offset.reinitialize(entry.free_local.size());
  for (const int n : entry.free_local.index_range()) {
    const int l = entry.free_local[n];
    out.offset[n] = (state.position[l] - state.goal[l]) * freedom[l];
  }
  out.inputs = inputs;
  out.exact = exact;
  entry.frames.insert_or_assign(frame, std::move(out));
  while (int(entry.frames.size()) > JIGGLE_MAX_FRAMES) {
    /* Drop the frame furthest from this one. */
    const auto first = entry.frames.begin();
    const auto last = std::prev(entry.frames.end());
    entry.frames.erase(frame - first->first > last->first - frame ? first : last);
  }
}

/** Keeps this frame's state, the one before, the start frame's and one every JIGGLE_CHECKPOINT frames (the furthest
 * from this frame go first). */
static void store_state(JiggleCacheEntry &entry, const int frame, const int start_frame, JiggleState state)
{
  entry.states.insert_or_assign(frame, std::move(state));
  const auto kept = [&](const int f) { return f == frame || f == frame - 1 || f == start_frame; };
  for (auto it = entry.states.begin(); it != entry.states.end();) {
    if (!kept(it->first) && it->first % JIGGLE_CHECKPOINT != 0) {
      it = entry.states.erase(it);
    }
    else {
      ++it;
    }
  }
  while (int(entry.states.size()) > JIGGLE_MAX_CHECKPOINTS + 3) {
    auto victim = entry.states.end();
    int furthest = -1;
    for (auto it = entry.states.begin(); it != entry.states.end(); ++it) {
      if (!kept(it->first) && std::abs(it->first - frame) > furthest) {
        furthest = std::abs(it->first - frame);
        victim = it;
      }
    }
    if (victim == entry.states.end()) {
      break;
    }
    entry.states.erase(victim);
  }
}

static void deform_verts(ModifierData *md,
                         const ModifierEvalContext *ctx,
                         Mesh *mesh,
                         MutableSpan<float3> positions)
{
  JiggleModifierData *jmd = reinterpret_cast<JiggleModifierData *>(md);
  if (mesh == nullptr || ctx->depsgraph == nullptr || positions.size() != mesh->verts_num ||
      positions.is_empty())
  {
    return;
  }
  const Scene *scene = DEG_get_evaluated_scene(ctx->depsgraph);
  if (scene == nullptr) {
    return;
  }
  Object *ob = ctx->object;
  const float4x4 &to_world = ob->object_to_world();
  const float4x4 &to_local = ob->world_to_object();

  /* Only the free vertices' weights are read over the whole mesh; the rest works on the soft part. */
  const Array<float> freedom = build_freedom(*jmd, ob, *mesh, positions);
  bool any_free = false;
  for (const float w : freedom) {
    any_free |= w > 0.0f;
  }
  if (!any_free) {
    return;
  }
  const std::shared_ptr<JiggleCacheEntry> entry_ptr = jiggle_entry(ob, md);
  JiggleCacheEntry &entry = *entry_ptr;
  std::scoped_lock lock(entry.mutex);
  const uint64_t setup = setup_hash(*jmd, freedom, *mesh);
  if (setup != entry.setup || !entry.has_region) {
    entry.setup = setup;
    entry.states.clear();
    entry.frames.clear();
    entry.started_inside.clear();
    build_region(entry, *mesh, freedom);
  }
  const Span<int> region = entry.region;
  const int verts_num = region.size();

  JiggleSolver solver;
  solver.jmd = jmd;
  solver.verts_num = verts_num;
  solver.freedom = entry.freedom;
  solver.neighbour_offsets = entry.neighbour_offsets;
  solver.neighbours = entry.neighbours;
  solver.tris = entry.tris;
  solver.tri_piece = entry.tri_piece;
  solver.vertex_piece = entry.vertex_piece;
  solver.pieces_num = entry.pieces_num;
  solver.omega = 2.0f * float(M_PI) * std::max(jmd->frequency, 0.01f);
  solver.substeps = std::clamp(int(jmd->substeps), 1, 50);
  solver.started_inside = &entry.started_inside;

  const float ctime = DEG_get_ctime(ctx->depsgraph);
  const int frame = int(std::lround(ctime));
  const bool subframe = std::fabs(ctime - float(frame)) > 1e-4f;
  const float dt = scene->r.frs_sec > 0 ? scene->r.frs_sec_base / float(scene->r.frs_sec) :
                                          1.0f / 24.0f;

  Array<float3> goal(verts_num);
  float3 low(FLT_MAX), high(-FLT_MAX), free_low(FLT_MAX), free_high(-FLT_MAX);
  JiggleHash inputs;
  for (const int l : IndexRange(verts_num)) {
    goal[l] = math::transform_point(to_world, positions[region[l]]);
    low = math::min(low, goal[l]);
    high = math::max(high, goal[l]);
    if (solver.freedom[l] > 0.0f) {
      free_low = math::min(free_low, goal[l]);
      free_high = math::max(free_high, goal[l]);
    }
    inputs.add(goal[l]);
  }
  solver.size = std::max(math::distance(low, high), 1e-6f);
  solver.free_size = std::max(math::distance(free_low, free_high), 1e-6f);
  float steepest = 0.0f;
  for (const int2 &edge : entry.edges) {
    const float change = std::fabs(solver.freedom[edge[0]] - solver.freedom[edge[1]]);
    if (change > 0.0f) {
      steepest = std::max(steepest, change / std::max(math::distance(goal[edge[0]], goal[edge[1]]), 1e-6f));
    }
  }
  solver.fold_limit = steepest > 0.0f ? JIGGLE_FOLD / steepest : FLT_MAX;
  build_colliders(solver, *jmd, ctx, *mesh, region, ctime, inputs);

  /* The offsets from the goals to show (free vertices only). */
  Array<float3> offset(entry.free_local.size(), float3(0.0f));
  const auto show_state = [&](const JiggleState &state) {
    for (const int n : entry.free_local.index_range()) {
      const int l = entry.free_local[n];
      offset[n] = (state.position[l] - state.goal[l]) * solver.freedom[l];
    }
  };
  const int start_frame = scene->r.sfra;

  if (subframe) {
    /* Motion blur: between the two whole frames, the cache left alone. */
    const int whole = int(std::floor(ctime));
    const auto a = entry.frames.find(whole);
    const auto b = entry.frames.find(whole + 1);
    const float t = ctime - float(whole);
    if (a != entry.frames.end()) {
      for (const int n : offset.index_range()) {
        offset[n] = b != entry.frames.end() ?
                        math::interpolate(a->second.offset[n], b->second.offset[n], t) :
                        a->second.offset[n];
      }
    }
  }
  else {
    const uint64_t hash = inputs.value;
    const auto found = entry.frames.find(frame);
    if (found != entry.frames.end() && found->second.inputs != hash) {
      /* The animation, the colliders or the rig changed since this frame was solved: start again here. */
      entry.states.clear();
      entry.frames.clear();
    }
    const auto cached = entry.frames.find(frame);
    const auto previous = entry.frames.find(frame - 1);
    const bool previous_exact = previous != entry.frames.end() && previous->second.exact &&
                                entry.states.count(frame - 1);
    if (frame == start_frame) {
      /* The scene's start frame always starts again, so playing from it gives the same jiggle. */
      entry.states.clear();
      entry.frames.clear();
      JiggleState state;
      solver.reset(state, goal);
      show_state(state);
      store_frame(entry, frame, state, solver.freedom, hash, true);
      store_state(entry, frame, start_frame, std::move(state));
    }
    else if (cached != entry.frames.end() && cached->second.exact) {
      offset.as_mutable_span().copy_from(cached->second.offset);
    }
    else if (previous_exact) {
      JiggleState state = entry.states.at(frame - 1);
      solver.step(state, goal, dt, true);
      show_state(state);
      store_frame(entry, frame, state, solver.freedom, hash, true);
      store_state(entry, frame, start_frame, std::move(state));
    }
    else if (cached != entry.frames.end()) {
      offset.as_mutable_span().copy_from(cached->second.offset);
    }
    else {
      /* A jump: catch up from the closest earlier state, the goals going straight from its to these. */
      JiggleState state;
      const auto after = entry.states.lower_bound(frame);
      if (after != entry.states.begin() && frame - std::prev(after)->first <= JIGGLE_MAX_CATCH_UP) {
        const auto earlier = std::prev(after);
        state = earlier->second;
        const Array<float3> from = state.goal;
        const int steps = frame - earlier->first;
        Array<float3> between(verts_num);
        for (int s = 1; s <= steps; s++) {
          const float t = float(s) / float(steps);
          for (const int i : IndexRange(verts_num)) {
            between[i] = math::interpolate(from[i], goal[i], t);
          }
          solver.step(state, between, dt, false);
        }
      }
      else {
        solver.reset(state, goal);
      }
      show_state(state);
      store_frame(entry, frame, state, solver.freedom, hash, false);
      store_state(entry, frame, start_frame, std::move(state));
    }
  }

  for (const int n : entry.free_local.index_range()) {
    positions[entry.free_mesh[n]] = math::transform_point(to_local, goal[entry.free_local[n]] + offset[n]);
  }
}

/** \} */

/* -------------------------------------------------------------------- */
/** \name Panel
 * \{ */

static void panel_draw(const bContext *C, Panel *panel)
{
  ui::Layout &layout = *panel->layout;
  PointerRNA ob_ptr;
  PointerRNA *ptr = modifier_panel_get_property_pointers(panel, &ob_ptr);
  layout.use_property_split_set(true);

  PointerRNA op_ptr = layout.op_menu_enum(
      C, "OBJECT_OT_dasktoon_jiggle_preset", "preset", IFACE_("Preset"), ICON_PRESET);
  if (!RNA_pointer_is_null(&op_ptr)) {
    RNA_string_set(&op_ptr, "modifier", static_cast<ModifierData *>(ptr->data)->name);
  }

  modifier_vgroup_ui(layout, ptr, &ob_ptr, "vertex_group", "invert_vertex_group", std::nullopt);
  layout.prop(ptr, "use_pin_bottom", UI_ITEM_NONE, std::nullopt, ICON_NONE);

  layout.separator();
  layout.prop(ptr, "frequency", UI_ITEM_NONE, std::nullopt, ICON_NONE);
  layout.prop(ptr, "damping", UI_ITEM_NONE, std::nullopt, ICON_NONE);
  layout.prop(ptr, "spread", UI_ITEM_NONE, std::nullopt, ICON_NONE);
  layout.prop(ptr, "volume", UI_ITEM_NONE, std::nullopt, ICON_NONE);
  layout.prop(ptr, "follow", UI_ITEM_NONE, std::nullopt, ICON_NONE);
  layout.prop(ptr, "substeps", UI_ITEM_NONE, std::nullopt, ICON_NONE);

  modifier_error_message_draw(layout, ptr);
}

static void collision_panel_draw(const bContext * /*C*/, Panel *panel)
{
  ui::Layout &layout = *panel->layout;
  PointerRNA *ptr = modifier_panel_get_property_pointers(panel, nullptr);
  layout.use_property_split_set(true);

  layout.prop(ptr, "collision_collection", UI_ITEM_NONE, std::nullopt, ICON_NONE);
  layout.prop(ptr, "distance", UI_ITEM_NONE, std::nullopt, ICON_NONE);
  layout.prop(ptr, "rig", UI_ITEM_NONE, std::nullopt, ICON_NONE);
  const JiggleModifierData *jmd = static_cast<const JiggleModifierData *>(ptr->data);
  if (jmd->rig != nullptr) {
    layout.label(fmt::format(fmt::runtime(IFACE_("{} body colliders")), jmd->colliders_num),
                 ICON_INFO);
  }
  layout.op("OBJECT_OT_dasktoon_make_collider", IFACE_("Make Selected Colliders"), ICON_MOD_PHYSICS);
}

static void panel_register(ARegionType *region_type)
{
  PanelType *panel_type = modifier_panel_register(region_type, eModifierType_Jiggle, panel_draw);
  modifier_subpanel_register(
      region_type, "collision", "Collision", nullptr, collision_panel_draw, panel_type);
}

static void blend_write(BlendWriter *writer, const ID * /*id_owner*/, const ModifierData *md)
{
  const JiggleModifierData *jmd = reinterpret_cast<const JiggleModifierData *>(md);
  writer->write_struct(jmd);
  if (jmd->colliders_array != nullptr) {
    writer->write_struct_array(jmd->colliders_num, jmd->colliders_array);
  }
}

static void blend_read(BlendDataReader *reader, ModifierData *md)
{
  JiggleModifierData *jmd = reinterpret_cast<JiggleModifierData *>(md);
  BLO_read_array_and_validate_size(reader, &jmd->colliders_array, &jmd->colliders_num);
}

/** \} */

ModifierTypeInfo modifierType_Jiggle = {
    /*idname*/ "Jiggle",
    /*name*/ N_("Jiggle"),
    /*struct_name*/ "JiggleModifierData",
    /*struct_size*/ sizeof(JiggleModifierData),
    /*srna*/ &RNA_JiggleModifier,
    /*type*/ ModifierTypeType::OnlyDeform,
    /*flags*/ eModifierTypeFlag_AcceptsMesh,
    /*icon*/ ICON_MOD_SOFT,

    /*copy_data*/ copy_data,

    /*deform_verts*/ deform_verts,
    /*deform_matrices*/ nullptr,
    /*deform_verts_EM*/ nullptr,
    /*deform_matrices_EM*/ nullptr,
    /*modify_mesh*/ nullptr,
    /*modify_geometry_set*/ nullptr,

    /*init_data*/ init_data,
    /*required_data_mask*/ required_data_mask,
    /*free_data*/ free_data,
    /*is_disabled*/ nullptr,
    /*update_depsgraph*/ update_depsgraph,
    /*depends_on_time*/ depends_on_time,
    /*depends_on_normals*/ nullptr,
    /*foreach_ID_link*/ foreach_ID_link,
    /*foreach_tex_link*/ nullptr,
    /*free_runtime_data*/ nullptr,
    /*panel_register*/ panel_register,
    /*blend_write*/ blend_write,
    /*blend_read*/ blend_read,
    /*foreach_cache*/ nullptr,
    /*foreach_working_space_color*/ nullptr,
};

}  // namespace blender
