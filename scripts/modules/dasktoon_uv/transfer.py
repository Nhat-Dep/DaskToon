# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The pictures painted on the old UV map carried over to the new one (spec section 2, step 7): every triangle of the new
map takes, pixel by pixel, the colour (alpha too) under the same spot of the old map; then a few pixels of bleed round
the islands. Images of the materials the meshes' faces use, and the paint layers of those images; the right limbs,
which lie on the left ones, are drawn first so the left side is what stays."""

import numpy as np

BLEED = 4  # pixels grown round the islands, so filtering at the seams finds colour


def has_pixels(image):
    """True when the picture has pixels, reading a file picture nothing has shown yet (has_data is False until then:
    tdt's textures were taken for no picture)."""
    if image is None:
        return False
    if image.has_data:
        return True
    try:
        return len(image.pixels) > 0  # reading the pixels loads the file
    except (RuntimeError, ReferenceError):
        return False


def _pixels(image):
    width, height = image.size
    px = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(px)
    return px.reshape(height, width, 4)


def _uv(mesh, name):
    data = mesh.uv_layers[name].data
    out = np.empty(len(data) * 2, dtype=np.float32)
    data.foreach_get("uv", out)
    return out.reshape(-1, 2)


def _sample(src, uv):
    """Bilinear samples of `src` (H, W, 4) at `uv` (N, 2), wrapping like a repeating texture."""
    height, width = src.shape[:2]
    x = uv[:, 0] * width - 0.5
    y = uv[:, 1] * height - 0.5
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    x0, y0 = x0 % width, y0 % height
    x1, y1 = (x0 + 1) % width, (y0 + 1) % height
    return ((src[y0, x0] * (1 - fx) + src[y0, x1] * fx) * (1 - fy) + (src[y1, x0] * (1 - fx) + src[y1, x1] * fx) * fy)


def draw(dst, filled, src, new_tri, old_tri):
    """Fill the pixels of `dst` inside the new triangle with `src` under the matching spot of the old triangle."""
    height, width = dst.shape[:2]
    scale = np.array([width, height], dtype=np.float64)
    a, b, c = (np.asarray(p, dtype=np.float64) * scale for p in new_tri)
    low = np.floor(np.minimum(np.minimum(a, b), c)).astype(int)
    high = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
    low = np.clip(low, 0, [width, height])
    high = np.clip(high, 0, [width, height])
    if (high <= low).any():
        return
    d = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
    if abs(d) < 1e-12:
        return
    ys, xs = np.mgrid[low[1]:high[1], low[0]:high[0]]
    px, py = xs + 0.5 - a[0], ys + 0.5 - a[1]
    u = ((c[1] - a[1]) * px - (c[0] - a[0]) * py) / d
    v = (-(b[1] - a[1]) * px + (b[0] - a[0]) * py) / d
    inside = (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6)
    if not inside.any():
        return
    u, v = u[inside], v[inside]
    oa, ob, oc = (np.asarray(p, dtype=np.float64) for p in old_tri)
    spots = oa + (ob - oa) * u[:, None] + (oc - oa) * v[:, None]
    yy, xx = ys[inside], xs[inside]
    dst[yy, xx] = _sample(src, spots)
    filled[yy, xx] = True


def bleed(dst, filled, steps=BLEED):
    """Grow the filled pixels outward `steps` times, each empty neighbour taking a filled neighbour's colour."""
    for _ in range(steps):
        grown = filled.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            shifted = np.roll(np.roll(filled, dy, axis=0), dx, axis=1)
            take = shifted & ~grown
            if take.any():
                dst[take] = np.roll(np.roll(dst, dy, axis=0), dx, axis=1)[take]
                grown |= take
        filled = grown


def images_of(obj):
    """{image: [face indices]} for the images of the image texture nodes in the materials obj's faces use."""
    out = {}
    indices = np.empty(len(obj.data.polygons), dtype=np.int32)
    obj.data.polygons.foreach_get("material_index", indices)
    for slot_index, slot in enumerate(obj.material_slots):
        mat = slot.material
        if mat is None or mat.node_tree is None:
            continue
        faces = np.nonzero(indices == slot_index)[0].tolist()
        if not faces:
            continue
        for node in mat.node_tree.nodes:
            if (node.bl_idname == 'ShaderNodeTexImage' and any(output.is_linked for output in node.outputs)
                    and has_pixels(node.image)):  # pictures the shader reads
                out.setdefault(node.image, []).extend(faces)
    return out


def transfer(meshes, old_names, mirrored=(), exclude=()):
    """Carry every picture of `meshes` from their old UV maps ({obj: name}) to their active one; returns the images
    changed. `mirrored`: (obj, face) keys of the right faces lying on the left ones (drawn first); `exclude`: pictures
    already laid out on the new map (the sets' colour pictures)."""
    right = set(mirrored)
    work = {}  # image: [(obj, faces)]
    for obj in meshes:
        old = old_names.get(obj)
        if not old:
            continue
        for image, faces in images_of(obj).items():
            if image in exclude:
                continue
            targets = [image] + [item.image for item in image.dasktoon_layers if item.image is not None]
            for target in targets:
                work.setdefault(target, []).append((obj, faces))
    changed = []
    for image, uses in work.items():
        src = _pixels(image)
        dst = np.zeros_like(src)
        filled = np.zeros(src.shape[:2], dtype=bool)
        for obj, faces in uses:
            mesh = obj.data
            new_uv = _uv(mesh, mesh.uv_layers.active.name)
            old_uv = _uv(mesh, old_names[obj])
            ordered = sorted(faces, key=lambda f: (obj, f) not in right)  # the right side first, the left over it
            for f in ordered:
                loops = list(mesh.polygons[f].loop_indices)
                for k in range(1, len(loops) - 1):
                    corners = [loops[0], loops[k], loops[k + 1]]
                    draw(dst, filled, src, new_uv[corners], old_uv[corners])
        bleed(dst, filled)
        image.pixels.foreach_set(dst.ravel())
        image.update()
        changed.append(image)
    owners = {owner for owner in {img for img in work} if len(owner.dasktoon_layers)}
    if owners:
        from dasktoon_paint import layers
        for owner in owners:
            layers.composite(owner)
    return changed
