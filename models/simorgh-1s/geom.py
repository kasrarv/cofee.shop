"""Geometry helpers for the SIMORGH-1S airframe generator.

Everything is in millimetres. Global frame:
    X : nose (0) -> tail (positive aft)
    Y : right wing positive
    Z : up

The airframe is modelled as true thin-walled shells (a closed solid whose wall
is SKIN thick), not as solids-to-be-hollowed-by-the-slicer. That way the slicer
just fills the modelled wall with its perimeters and the geometry is exactly
what gets printed.
"""

from __future__ import annotations

import numpy as np
import trimesh
from shapely.geometry import LineString, Polygon
from shapely import affinity

# ---------------------------------------------------------------- constants

SKIN = 0.45         # modelled wall thickness (1 perimeter @ 0.45 mm line width)
RING = 192          # points per lofted cross-section
EPS = 1e-6


# ---------------------------------------------------------------- 2D profiles

def superellipse(w: float, h: float, n: float, npts: int = RING) -> np.ndarray:
    """Closed superellipse ring, width w, height h, exponent n (2=ellipse)."""
    t = np.linspace(0.0, 2.0 * np.pi, npts, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    x = (w / 2.0) * np.sign(c) * np.abs(c) ** (2.0 / n)
    y = (h / 2.0) * np.sign(s) * np.abs(s) ** (2.0 / n)
    return np.column_stack([x, y])


# Clark Y ordinates in % chord, referenced to the flat lower surface.
_CLARKY_X = np.array([0, 1.25, 2.5, 5, 7.5, 10, 15, 20, 25, 30, 40,
                      50, 60, 70, 80, 90, 95, 100], float)
_CLARKY_U = np.array([3.50, 5.45, 6.50, 7.90, 8.85, 9.60, 10.69, 11.36, 11.70,
                      11.75, 11.40, 10.52, 9.15, 7.35, 5.22, 2.80, 1.49, 0.12], float)
_CLARKY_L = np.array([3.50, 1.93, 1.47, 0.93, 0.63, 0.42, 0.15, 0.03, 0.00,
                      0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.06, 0.12], float)


def clark_y(chord: float, npts: int = 90, te_thick: float = 1.3) -> np.ndarray:
    """Clark Y section as a closed ring, TE first, going over the top.

    Origin is the leading edge, +x aft, +y up; the lower surface is flat and
    sits at y=0 over most of the chord. The trailing edge is opened up to
    ``te_thick`` so the section can be shelled and printed.
    """
    beta = np.linspace(0.0, np.pi, npts)
    xs = (1.0 - np.cos(beta)) / 2.0 * 100.0          # cosine spacing, 0..100 %

    up = np.interp(xs, _CLARKY_X, _CLARKY_U)
    lo = np.interp(xs, _CLARKY_X, _CLARKY_L)

    # Open the trailing edge symmetrically about the mean line, blending in
    # over the aft 35% so the surface stays smooth.
    blend = np.clip((xs - 65.0) / 35.0, 0.0, 1.0) ** 2
    half = (te_thick / chord * 100.0) / 2.0
    up = up + blend * half
    lo = lo - blend * half

    ring_x = np.concatenate([xs[::-1], xs[1:-1]])            # TE->LE->TE
    ring_y = np.concatenate([up[::-1], lo[1:-1]])
    pts = np.column_stack([ring_x, ring_y]) * chord / 100.0
    return pts


def flat_plate(chord: float, thick: float, npts: int = 60,
               le_round: float = 0.45, te_round: float = 0.18) -> np.ndarray:
    """Symmetric flat-plate section with rounded LE/TE, for tail surfaces."""
    beta = np.linspace(0.0, np.pi, npts)
    x = (1.0 - np.cos(beta)) / 2.0
    # elliptical nose, straight middle, tapered tail
    t = np.ones_like(x) * thick / 2.0
    nose = x < le_round
    t[nose] = (thick / 2.0) * np.sqrt(np.clip(1.0 - ((le_round - x[nose]) / le_round) ** 2, 0, 1))
    tail = x > (1.0 - te_round)
    u = (x[tail] - (1.0 - te_round)) / te_round
    t[tail] = (thick / 2.0) * (1.0 - 0.72 * u ** 1.6)
    xs = x * chord
    ring_x = np.concatenate([xs[::-1], xs[1:-1]])
    ring_y = np.concatenate([t[::-1], -t[1:-1]])
    return np.column_stack([ring_x, ring_y])


# ---------------------------------------------------------------- ring utils

def _resample_star(poly: Polygon, center: np.ndarray, npts: int) -> np.ndarray:
    """Sample a star-shaped polygon by casting npts rays from `center`."""
    minx, miny, maxx, maxy = poly.bounds
    reach = 2.5 * max(maxx - minx, maxy - miny) + 10.0
    out = np.zeros((npts, 2))
    ang = np.linspace(0.0, 2.0 * np.pi, npts, endpoint=False)
    for i, a in enumerate(ang):
        tip = center + reach * np.array([np.cos(a), np.sin(a)])
        seg = LineString([tuple(center), tuple(tip)])
        inter = seg.intersection(poly.exterior)
        if inter.is_empty:
            out[i] = center
            continue
        if inter.geom_type == "Point":
            out[i] = (inter.x, inter.y)
        else:
            cand = np.array([[g.x, g.y] for g in inter.geoms]
                            if hasattr(inter, "geoms") else list(inter.coords))
            d = np.linalg.norm(cand - center, axis=1)
            out[i] = cand[np.argmax(d)]
    return out


def offset_ring(pts: np.ndarray, dist: float, center: np.ndarray | None = None,
                npts: int = RING) -> np.ndarray:
    """Inward offset of a closed ring by `dist`, resampled to npts points.

    Returns a degenerate micro-ring at the centroid when the section is too
    small to be hollow, which keeps the loft topology intact (that station is
    then effectively solid).
    """
    poly = Polygon(pts)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if center is None:
        center = np.array(poly.centroid.coords[0])
    inner = poly.buffer(-dist, join_style=2, mitre_limit=4.0)
    if inner.is_empty or inner.area < 1.0:
        a = np.linspace(0, 2 * np.pi, npts, endpoint=False)
        return center + 0.05 * np.column_stack([np.cos(a), np.sin(a)])
    if inner.geom_type == "MultiPolygon":
        inner = max(inner.geoms, key=lambda g: g.area)
    if not inner.contains(Polygon(pts).centroid):
        center = np.array(inner.representative_point().coords[0])
    return _resample_star(inner, center, npts)


def resample(pts: np.ndarray, npts: int = RING,
             center: np.ndarray | None = None) -> np.ndarray:
    poly = Polygon(pts)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if center is None:
        center = np.array(poly.centroid.coords[0])
    return _resample_star(poly, center, npts)


# ---------------------------------------------------------------- lofting

def _quads(a0: int, a1: int, n: int, flip: bool = False) -> np.ndarray:
    """Triangles for a quad strip between two rings of n points."""
    i = np.arange(n)
    j = (i + 1) % n
    f = []
    for k in range(n):
        p0, p1 = a0 + i[k], a0 + j[k]
        q0, q1 = a1 + i[k], a1 + j[k]
        if flip:
            f.append([p0, q0, q1])
            f.append([p0, q1, p1])
        else:
            f.append([p0, q1, q0])
            f.append([p0, p1, q1])
    return np.array(f, dtype=np.int64)


def loft_shell(outer: list[np.ndarray], inner: list[np.ndarray]) -> trimesh.Trimesh:
    """Watertight thin-walled solid from matched outer/inner 3D ring stacks."""
    assert len(outer) == len(inner) >= 2
    n = len(outer[0])
    verts = np.vstack([np.vstack(outer), np.vstack(inner)])
    off = len(outer) * n
    faces = []
    for s in range(len(outer) - 1):
        faces.append(_quads(s * n, (s + 1) * n, n, flip=False))
        faces.append(_quads(off + s * n, off + (s + 1) * n, n, flip=True))
    # annular end caps
    faces.append(_quads(0, off, n, flip=True))
    last = (len(outer) - 1) * n
    faces.append(_quads(last, off + last, n, flip=False))
    mesh = trimesh.Trimesh(vertices=verts, faces=np.vstack(faces), process=True)
    mesh.fix_normals()
    return mesh


def loft_solid(rings: list[np.ndarray]) -> trimesh.Trimesh:
    """Watertight solid from a stack of 3D rings, capped with fans."""
    n = len(rings[0])
    verts = [np.vstack(rings)]
    faces = []
    for s in range(len(rings) - 1):
        faces.append(_quads(s * n, (s + 1) * n, n, flip=False))
    base = len(rings) * n
    c0 = rings[0].mean(axis=0)
    c1 = rings[-1].mean(axis=0)
    verts.append(np.array([c0, c1]))
    i = np.arange(n)
    j = (i + 1) % n
    faces.append(np.column_stack([i, j, np.full(n, base)]))
    last = (len(rings) - 1) * n
    faces.append(np.column_stack([last + j, last + i, np.full(n, base + 1)]))
    mesh = trimesh.Trimesh(vertices=np.vstack(verts),
                           faces=np.vstack(faces), process=True)
    mesh.fix_normals()
    return mesh


# ---------------------------------------------------------------- placement

def place_yz(ring2d: np.ndarray, x: float, zc: float = 0.0,
             yc: float = 0.0) -> np.ndarray:
    """A (y,z) section placed at fuselage station x."""
    return np.column_stack([np.full(len(ring2d), x),
                            ring2d[:, 0] + yc,
                            ring2d[:, 1] + zc])


def place_xz(ring2d: np.ndarray, y: float, x0: float = 0.0, z0: float = 0.0,
             twist: float = 0.0) -> np.ndarray:
    """An (x,z) airfoil section placed at span station y, twisted about the LE."""
    p = ring2d.copy()
    if abs(twist) > EPS:
        a = np.radians(twist)
        ca, sa = np.cos(a), np.sin(a)
        x, z = p[:, 0].copy(), p[:, 1].copy()
        p[:, 0] = ca * x + sa * z
        p[:, 1] = -sa * x + ca * z
    return np.column_stack([p[:, 0] + x0, np.full(len(p), y), p[:, 1] + z0])


# ---------------------------------------------------------------- primitives

def box(size, center) -> trimesh.Trimesh:
    m = trimesh.creation.box(extents=size)
    m.apply_translation(center)
    return m


def cyl(radius: float, height: float, start, direction, sections: int = 48):
    m = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    m.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], d))
    m.apply_translation(np.array(start, float) + d * height / 2.0)
    return m


def union(*meshes) -> trimesh.Trimesh:
    ms = [m for m in meshes if m is not None]
    if len(ms) == 1:
        return ms[0]
    return trimesh.boolean.union(ms, engine="manifold")


def diff(a, *bs) -> trimesh.Trimesh:
    return trimesh.boolean.difference([a] + [b for b in bs if b is not None],
                                      engine="manifold")


def inter(a, b) -> trimesh.Trimesh:
    return trimesh.boolean.intersection([a, b], engine="manifold")


# ---------------------------------------------------------------- reporting

LWPLA_DENSITY = 0.58e-3     # g/mm^3 for foamed LW-PLA at ~50% flow


def report(name: str, mesh: trimesh.Trimesh) -> dict:
    ext = mesh.extents
    vol = mesh.volume
    return {
        "part": name,
        "size_mm": [round(float(v), 1) for v in ext],
        "max_dim": round(float(max(ext)), 1),
        "volume_cm3": round(float(vol) / 1000.0, 1),
        "mass_lwpla_g": round(float(vol) * LWPLA_DENSITY, 1),
        "watertight": bool(mesh.is_watertight),
    }
