"""Software renderer for quick visual checks of the SIMORGH-1S assembly."""

from __future__ import annotations

import sys

import numpy as np
import trimesh

import airframe as A


def look_at(eye, target, up=(0, 0, 1)):
    eye = np.asarray(eye, float)
    target = np.asarray(target, float)
    f = target - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, np.asarray(up, float))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return np.stack([r, u, -f]), eye


def render(meshes, colors, eye, target, size=(1500, 950), fov=32.0,
           bg=(250, 250, 252), up=(0, 0, 1)):
    W, H = size
    R, eye = look_at(eye, target, up)
    img = np.zeros((H, W, 3), np.float64)
    img[:] = bg
    zbuf = np.full((H, W), np.inf)
    focal = (W / 2.0) / np.tan(np.radians(fov) / 2.0)
    light = np.array([0.45, 0.62, 0.65])
    light /= np.linalg.norm(light)

    for mesh, col in zip(meshes, colors):
        v = (mesh.vertices - eye) @ R.T
        f = mesh.faces
        tri = v[f]                                    # (n,3,3) camera space
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        ln = np.linalg.norm(n, axis=1)
        ok = ln > 1e-9
        n[ok] /= ln[ok, None]
        z = -tri[:, :, 2]
        keep = ok & (z > 1.0).all(axis=1) & (n[:, 2] > 0)      # cull back faces
        tri, n = tri[keep], n[keep]
        if len(tri) == 0:
            continue

        sx = focal * tri[:, :, 0] / (-tri[:, :, 2]) + W / 2.0
        sy = -focal * tri[:, :, 1] / (-tri[:, :, 2]) + H / 2.0
        depth = -tri[:, :, 2]

        lam = np.clip(n @ light, 0, 1)
        shade = 0.28 + 0.72 * lam ** 0.85
        rim = 0.16 * np.clip(n[:, 2], 0, 1) ** 3
        base = np.asarray(col, float)
        face_col = np.clip(base * shade[:, None] + 255.0 * rim[:, None], 0, 255)

        order = np.argsort(-depth.mean(axis=1))
        for k in order:
            x0 = max(int(np.floor(sx[k].min())), 0)
            x1 = min(int(np.ceil(sx[k].max())) + 1, W)
            y0 = max(int(np.floor(sy[k].min())), 0)
            y1 = min(int(np.ceil(sy[k].max())) + 1, H)
            if x1 <= x0 or y1 <= y0:
                continue
            xs = np.arange(x0, x1) + 0.5
            ys = np.arange(y0, y1) + 0.5
            px, py = np.meshgrid(xs, ys)
            ax, ay = sx[k, 0], sy[k, 0]
            bx, by = sx[k, 1], sy[k, 1]
            cx, cy = sx[k, 2], sy[k, 2]
            d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(d) < 1e-9:
                continue
            w0 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / d
            w1 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / d
            w2 = 1.0 - w0 - w1
            m = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
            if not m.any():
                continue
            zz = w0 * depth[k, 0] + w1 * depth[k, 1] + w2 * depth[k, 2]
            sub = zbuf[y0:y1, x0:x1]
            hit = m & (zz < sub)
            if not hit.any():
                continue
            sub[hit] = zz[hit]
            img[y0:y1, x0:x1][hit] = face_col[k]
    return img.astype(np.uint8)


PALETTE = {
    "fuse": (206, 62, 52),        # red fuselage
    "wing": (238, 238, 240),      # white wings
    "tail": (238, 238, 240),
    "move": (250, 190, 60),       # control surfaces in amber
    "canopy": (60, 74, 92),
}


def colour_for(name):
    if "canopy" in name:
        return PALETTE["canopy"]
    if name.startswith("fuse"):
        return PALETTE["fuse"]
    if "elev" in name or "rudder" in name:
        return PALETTE["move"]
    if "wing" in name:
        return PALETTE["wing"]
    return PALETTE["tail"]


def main():
    parts = {}
    for name, fn, _ in A.PARTS:
        key = name.split("_", 1)[1]
        parts[key] = fn()
    asm = A.assembled(parts)

    meshes = list(asm.values())
    colors = [colour_for(k) for k in asm.keys()]
    all_pts = np.vstack([m.vertices for m in meshes])
    ctr = (all_pts.min(axis=0) + all_pts.max(axis=0)) / 2.0
    print("assembly bbox mm:", (all_pts.max(axis=0) - all_pts.min(axis=0)).round(1))

    views = {
        "iso":   ([ctr[0] - 900, -1250, 780], 40),
        "front": ([ctr[0] - 1600, 0, 30], 34),
        "side":  ([ctr[0], -1700, 25], 32),
        "top":   ([ctr[0], 0, 1700], 50),
        "rear3q": ([ctr[0] + 950, 1050, 520], 40),
    }
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for name, (eye, fov) in views.items():
        up = (0, 0, 1) if name != "top" else (1, 0, 0)
        img = render(meshes, colors, eye, ctr, fov=fov, up=up)
        plt.imsave(f"preview_{name}.png", img)
        print("wrote", f"preview_{name}.png")


if __name__ == "__main__":
    main()
