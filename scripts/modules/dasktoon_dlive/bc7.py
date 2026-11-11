# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""A vectorised numpy BC7 encoder (mode 6 only: one subset, RGBA 7.7.7.7 endpoints with p-bits, 4-bit indices) and a
DDS writer, for the optional `textures/*.dds` entries of the .dlive format (D:\\DaskLive\\docs\\dlive-format.md).

Endpoints come from the block's principal axis, then each block is refined by least squares on its own indices
(`REFINE` times). Nothing here needs bpy: pixels in, bytes out."""

import struct

import numpy as np

REFINE = 2
WEIGHTS = np.array([0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64], np.float32)
T_GRID = WEIGHTS / 64.0
T_MID = (T_GRID[1:] + T_GRID[:-1]) * 0.5
CHANNEL_WEIGHT = np.array([1.0, 1.0, 1.0, 2.0], np.float32)  # alpha is less forgiving than a colour channel
CHUNK = 32768  # blocks per step: bounds the working memory to a few tens of MB
SHIFTS = (np.arange(16, dtype=np.uint64) * np.uint64(4))


def _quantise(e):
    """(N,2,4) float endpoints -> ((N,2,4) 7-bit values, (N,2) p-bits): the p-bit of each endpoint is the one giving
    the smaller error over its four channels."""
    best_err = None
    for p in (0, 1):
        q = np.clip(np.rint((e - p) * 0.5), 0, 127)
        err = (((q * 2 + p) - e) ** 2 * CHANNEL_WEIGHT).sum(axis=2)
        if best_err is None:
            best_err, best_q, best_p = err, q, np.zeros(err.shape, np.uint8)
        else:
            better = err < best_err
            best_q = np.where(better[..., None], q, best_q)
            best_p = np.where(better, np.uint8(1), best_p)
            best_err = np.minimum(err, best_err)
    return best_q.astype(np.uint8), best_p


def _decode(q, p):
    """(N,2,4) 7-bit + (N,2) p-bit -> (N,2,4) float 8-bit endpoints."""
    return (q.astype(np.float32) * 2 + p[..., None]).astype(np.float32)


def _indices(px, ends):
    """Nearest of the 16 palette points to each pixel (px (N,16,4), ends (N,2,4)): the palette lies on one line, so
    the position along it is enough."""
    d = ends[:, 1] - ends[:, 0]
    dd = (d * d).sum(axis=1)
    t = np.einsum('npc,nc->np', px - ends[:, None, 0], d) / np.maximum(dd, 1e-6)[:, None]
    t = np.where(dd[:, None] > 1e-6, t, 0.0)
    return np.searchsorted(T_MID, t.ravel()).reshape(t.shape).astype(np.uint8), t


def _encode_chunk(px):
    """px (N,16,4) float32 0..255 -> (lo, hi) uint64 arrays: the two halves of each 128-bit block."""
    n = px.shape[0]
    mean = px.mean(axis=1)
    centred = px - mean[:, None]
    cov = np.einsum('npc,npd->ncd', centred, centred)
    axis = px.max(axis=1) - px.min(axis=1)
    axis = axis + 1e-3
    for _ in range(4):  # power iteration for the principal axis
        axis = np.einsum('ncd,nd->nc', cov, axis)
        axis = axis / np.maximum(np.abs(axis).max(axis=1, keepdims=True), 1e-9)
    proj = np.einsum('npc,nc->np', centred, axis) / np.maximum((axis * axis).sum(axis=1), 1e-9)[:, None]
    ends = np.stack([mean + axis * proj.min(axis=1)[:, None], mean + axis * proj.max(axis=1)[:, None]], axis=1)
    ends = np.clip(ends, 0, 255)
    q, p = _quantise(ends)
    idx, t = _indices(px, _decode(q, p))
    best = None
    for step in range(REFINE + 1):
        dec = _decode(q, p)
        w1 = T_GRID[idx]
        w0 = 1.0 - w1
        pal = w0[..., None] * dec[:, None, 0] + w1[..., None] * dec[:, None, 1]
        err = ((pal - px) ** 2 * CHANNEL_WEIGHT).sum(axis=(1, 2))
        if best is None:
            best = (err, q, p, idx)
        else:
            better = err < best[0]
            best = (np.where(better, err, best[0]), np.where(better[:, None, None], q, best[1]),
                    np.where(better[:, None], p, best[2]), np.where(better[:, None], idx, best[3]))
        if step == REFINE:
            break
        a = (w0 * w0).sum(axis=1)
        b = (w0 * w1).sum(axis=1)
        c = (w1 * w1).sum(axis=1)
        det = a * c - b * b
        ok = det > 1e-4
        safe = np.where(ok, det, 1.0)
        r0 = np.einsum('np,npc->nc', w0, px)
        r1 = np.einsum('np,npc->nc', w1, px)
        e0 = (c[:, None] * r0 - b[:, None] * r1) / safe[:, None]
        e1 = (a[:, None] * r1 - b[:, None] * r0) / safe[:, None]
        new = np.clip(np.stack([e0, e1], axis=1), 0, 255)
        new = np.where(ok[:, None, None], new, ends)
        q, p = _quantise(new)
        idx, t = _indices(px, _decode(q, p))
    _, q, p, idx = best
    idx = idx.copy()
    flip = idx[:, 0] >= 8  # the first pixel's index has 3 bits: its top bit must be 0
    q = np.where(flip[:, None, None], q[:, ::-1], q)
    p = np.where(flip[:, None], p[:, ::-1], p)
    idx = np.where(flip[:, None], 15 - idx, idx).astype(np.uint64)
    q64 = q.astype(np.uint64)
    lo = np.full(n, 1 << 6, np.uint64)
    shift = 7
    for c in range(4):
        for e in range(2):
            lo |= q64[:, e, c] << np.uint64(shift)
            shift += 7
    lo |= p[:, 0].astype(np.uint64) << np.uint64(63)
    packed = idx << SHIFTS  # pixel i at bit 4i; pixel 0 uses bits 0-3 here and moves to bits 1-4 below
    hi = (packed[:, 1:].sum(axis=1, dtype=np.uint64) + np.uint64(0))
    hi = hi | ((idx[:, 0] << np.uint64(1)) | p[:, 1].astype(np.uint64))
    return lo, hi


def encode_level(rgba):
    """(H,W,4) uint8 -> the BC7 blocks of that picture, bytes (ceil(H/4) * ceil(W/4) blocks, row by row)."""
    h, w = rgba.shape[:2]
    bh, bw = (h + 3) // 4, (w + 3) // 4
    if (bh * 4, bw * 4) != (h, w):
        rgba = np.pad(rgba, ((0, bh * 4 - h), (0, bw * 4 - w), (0, 0)), mode='edge')
    blocks = rgba.reshape(bh, 4, bw, 4, 4).transpose(0, 2, 1, 3, 4).reshape(bh * bw, 16, 4)
    out = np.empty((bh * bw, 2), np.uint64)
    for start in range(0, bh * bw, CHUNK):
        lo, hi = _encode_chunk(blocks[start:start + CHUNK].astype(np.float32))
        out[start:start + CHUNK, 0] = lo
        out[start:start + CHUNK, 1] = hi
    return out.astype('<u8').tobytes()


def _halve(img):
    """Next mip: (H,W,4) uint8 -> (max(1,H//2), max(1,W//2), 4), a box filter weighted by alpha so see-through
    pixels do not darken the colour of their neighbours."""
    h, w = img.shape[:2]
    nh, nw = max(1, h // 2), max(1, w // 2)
    ys0 = np.minimum(np.arange(nh) * 2, h - 1)
    ys1 = np.minimum(ys0 + 1, h - 1)
    xs0 = np.minimum(np.arange(nw) * 2, w - 1)
    xs1 = np.minimum(xs0 + 1, w - 1)
    f = img.astype(np.float32)
    taps = [f[ys][:, xs] for ys in (ys0, ys1) for xs in (xs0, xs1)]
    alpha = sum(t[..., 3] for t in taps)
    out = sum(taps) * 0.25
    if alpha.min() < 4 * 255:  # something see-through: weight the colour by alpha
        weighted = sum(t[..., :3] * t[..., 3:4] for t in taps)
        colour = np.where(alpha[..., None] > 0, weighted / np.maximum(alpha, 1e-6)[..., None], out[..., :3])
        out[..., :3] = colour
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def mip_chain(rgba):
    levels = [rgba]
    while max(levels[-1].shape[:2]) > 1:
        levels.append(_halve(levels[-1]))
    return levels


def dds_bytes(rgba):
    """(H,W,4) uint8 straight-alpha pixels, top row first -> a BC7 DDS with the whole mip chain."""
    levels = mip_chain(np.ascontiguousarray(rgba))
    data = [encode_level(level) for level in levels]
    h, w = rgba.shape[:2]
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000
    header = b"DDS " + struct.pack("<7I", 124, flags, h, w, len(data[0]), 0, len(levels)) + bytes(44)
    header += struct.pack("<II4s5I", 32, 0x4, b"DX10", 0, 0, 0, 0, 0)
    header += struct.pack("<5I", 0x401008, 0, 0, 0, 0)
    header += struct.pack("<5I", 98, 3, 0, 1, 0)  # DXGI_FORMAT_BC7_UNORM, 2D texture
    return header + b"".join(data)


def decode_level(blocks, h, w):
    """Mode 6 blocks (as encode_level writes them) -> (H,W,4) uint8; for tests and for measuring the error."""
    bh, bw = (h + 3) // 4, (w + 3) // 4
    arr = np.frombuffer(blocks, '<u8').reshape(bh * bw, 2)
    lo, hi = arr[:, 0], arr[:, 1]
    assert np.all((lo & np.uint64(0x7F)) == np.uint64(64)), "not mode 6"
    ends = np.empty((bh * bw, 2, 4), np.float32)
    shift = 7
    p = [((lo >> np.uint64(63)) & np.uint64(1)), (hi & np.uint64(1))]
    for c in range(4):
        for e in range(2):
            ends[:, e, c] = ((lo >> np.uint64(shift)) & np.uint64(0x7F)).astype(np.float32) * 2 + p[e].astype(np.float32)
            shift += 7
    idx = np.empty((bh * bw, 16), np.int64)
    idx[:, 0] = ((hi >> np.uint64(1)) & np.uint64(7)).astype(np.int64)
    for i in range(1, 16):
        idx[:, i] = ((hi >> np.uint64(4 * i)) & np.uint64(15)).astype(np.int64)
    wt = WEIGHTS[idx]
    pix = np.floor(((64 - wt)[..., None] * ends[:, None, 0] + wt[..., None] * ends[:, None, 1] + 32) / 64)
    img = pix.reshape(bh, bw, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 4)
    return np.clip(img, 0, 255).astype(np.uint8)[:h, :w]
