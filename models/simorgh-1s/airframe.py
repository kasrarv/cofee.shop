"""SIMORGH-1S — parametric generator for a 1S, 3-channel printed park flyer.

Run:  python3 airframe.py [--out stl]

Design point
------------
  span 870 mm | wing area 12.2 dm^2 | AUW ~285 g | 1S Li-ion | 3 ch (thr/rud/ele)

Every printed part fits inside a 250 x 250 x 250 mm envelope. All shells are
modelled at SKIN thickness so the slicer prints exactly one perimeter.
"""

from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np
import trimesh
from scipy.interpolate import PchipInterpolator
from shapely.geometry import Polygon, box as sbox

from geom import (RING, SKIN, LWPLA_DENSITY, box, clark_y, cyl, diff, flat_plate,
                  inter, loft_shell, loft_solid, offset_ring, place_xz, place_yz,
                  report, resample, superellipse, union)

# ---------------------------------------------------------------- parameters

# fuselage stations                x,   width, top,   bottom, exponent
FUSE = np.array([
    [5,    36,  16.0,  -16.0, 2.6],
    [26,   46,  24.0,  -22.0, 2.8],
    [55,   58,  29.0,  -27.0, 3.0],
    [88,   65,  30.2,  -30.0, 3.2],
    [110,  67,  33.0,  -31.0, 3.3],
    [150,  68,  33.1,  -31.0, 3.4],
    [195,  68,  31.5,  -31.0, 3.4],
    [240,  67,  29.9,  -30.5, 3.3],
    [300,  62,  27.8,  -29.0, 3.1],
    [360,  55,  25.2,  -26.0, 2.9],
    [415,  46,  21.8,  -22.0, 2.8],
    [435,  43,  18.6,  -20.6, 2.8],
    [500,  35,  15.0,  -16.0, 2.7],
    [625,  24,  10.0,  -10.0, 2.6],
    [665,  16,  13.2,   -8.5, 4.0],
    [700,  14,  13.8,   -6.5, 6.0],
    [740,  13,  14.0,   -5.0, 7.0],
])
_FX = FUSE[:, 0]
_FW = PchipInterpolator(_FX, FUSE[:, 1])
_FT = PchipInterpolator(_FX, FUSE[:, 2])
_FB = PchipInterpolator(_FX, FUSE[:, 3])
_FN = PchipInterpolator(_FX, FUSE[:, 4])

INCIDENCE = 2.0                      # wing incidence, degrees
DECK_X0, DECK_Z0 = 95.0, 30.0        # deck reference point
DECK_SLOPE = math.tan(math.radians(INCIDENCE))

SPLIT = [5.0, 195.0, 415.0, 625.0, 740.0]     # F1 F2 F3 F4 boundaries
DECK_X1 = 440.0                       # deck clip ends here
TAIL_DECK_X, TAIL_DECK_Z = 650.0, 12.0        # flat pad the fin sits on
COLLAR_LEN = 14.0
FIT = 0.25                            # sliding-fit clearance

WING_LE = 235.0                       # fuselage station of the wing LE
C_ROOT, C_MID, C_TIP = 165.0, 145.0, 105.0
B_INNER, B_OUTER = 220.0, 205.0
DIHEDRAL = 10.0                       # outer panel, degrees
TONGUE_L = 28.0                       # outer-panel joint tongue length
SPAR_D, SPAR_Z, SPAR_XC = 6.3, 9.0, 0.30      # carbon rod bore, height, %chord

SERVO_L, SERVO_W, SERVO_H = 33.0, 13.5, 32.0  # pocket for a 31x32 mm micro servo
SERVO_EAR_Z = 22.0                            # flange depth below the deck
SERVO_SCREW_PITCH = 28.0
SERVO_X0 = 286.0                              # clear of the rear wing bolt

BOLT_X = (17.0, 100.0)                # wing-local stations of the M3 bolts
BOLT_Y = 18.0                         # must stay inside the flat deck

STAB_SPAN, STAB_CR, STAB_CT, STAB_T = 340.0, 90.0, 68.0, 6.0
ELEV_C = 34.0
FIN_H, FIN_CR, FIN_CT, FIN_T = 150.0, 105.0, 62.0, 5.5
RUD_C = 38.0

MOTOR_X = 26.0                        # firewall station
THRUST_DOWN, THRUST_RIGHT = 2.0, 2.0


# ---------------------------------------------------------------- fuselage

def deck_z(x: float) -> float:
    return DECK_Z0 - DECK_SLOPE * (x - DECK_X0)


def fuse_poly(x: float, clip: bool = True) -> Polygon:
    """Outer cross-section of the fuselage at station x, deck already flattened."""
    w, t, b, n = float(_FW(x)), float(_FT(x)), float(_FB(x)), float(_FN(x))
    ring = superellipse(w, t - b, n, RING)
    ring[:, 1] += (t + b) / 2.0
    poly = Polygon(ring)
    if clip:
        dz = None
        if 85.0 <= x <= DECK_X1:
            dz = deck_z(x)
        elif x >= TAIL_DECK_X:
            dz = TAIL_DECK_Z
        if dz is not None and dz < t - 0.05:
            poly = poly.intersection(sbox(-200, -400, 200, dz))
    if poly.geom_type == "MultiPolygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    return poly


def fuse_rings(x: float, shrink: float = 0.0):
    poly = fuse_poly(x)
    if shrink:
        poly = poly.buffer(-shrink, join_style=2)
        if poly.geom_type == "MultiPolygon":
            poly = max(poly.geoms, key=lambda g: g.area)
    c = np.array(poly.representative_point().coords[0])
    return resample(poly, RING, c), offset_ring(np.array(poly.exterior.coords), SKIN, c)


def fuse_shell(x0: float, x1: float, step: float = 4.0,
               shrink: float = 0.0) -> trimesh.Trimesh:
    xs = list(np.arange(x0, x1, step)) + [x1]
    outs, ins = [], []
    for x in xs:
        o, i = fuse_rings(float(x), shrink)
        outs.append(place_yz(o, float(x)))
        ins.append(place_yz(i, float(x)))
    return loft_shell(outs, ins)


def fuse_solid(x0: float, x1: float, step: float = 6.0,
               shrink: float = 0.0) -> trimesh.Trimesh:
    """Solid hull of the fuselage, used to trim internal structure to the skin."""
    xs = list(np.arange(x0, x1, step)) + [x1]
    rings = []
    for x in xs:
        poly = fuse_poly(float(x))
        if shrink:
            poly = poly.buffer(-shrink, join_style=2)
            if poly.geom_type == "MultiPolygon":
                poly = max(poly.geoms, key=lambda g: g.area)
        c = np.array(poly.representative_point().coords[0])
        rings.append(place_yz(resample(poly, RING, c), float(x)))
    return loft_solid(rings)


def former(x: float, width: float = 4.5, thick: float = 1.2,
           shrink: float = 0.0) -> trimesh.Trimesh:
    """A ring frame: the section band `width` wide, `thick` along x."""
    o, _ = fuse_rings(x, shrink)
    poly = Polygon(o)
    inner = poly.buffer(-(SKIN + width), join_style=2)
    rings_o = [place_yz(o, x - thick / 2), place_yz(o, x + thick / 2)]
    if inner.is_empty or inner.area < 25:
        return loft_solid(rings_o)
    c = np.array(inner.representative_point().coords[0])
    ri = resample(np.array(inner.exterior.coords), RING, c)
    return loft_shell(rings_o, [place_yz(ri, x - thick / 2), place_yz(ri, x + thick / 2)])


def bulkhead(x: float, thick: float = 2.0) -> trimesh.Trimesh:
    o, _ = fuse_rings(x)
    return loft_solid([place_yz(o, x - thick / 2), place_yz(o, x + thick / 2)])


def collar(x: float, length: float) -> trimesh.Trimesh:
    """Male spigot protruding aft of station x, a sliding fit inside the next part."""
    outs, ins = [], []
    for s in np.linspace(x, x + length, 6):
        poly = fuse_poly(float(s)).buffer(-(SKIN + FIT), join_style=2)
        if poly.geom_type == "MultiPolygon":
            poly = max(poly.geoms, key=lambda g: g.area)
        c = np.array(poly.representative_point().coords[0])
        o = resample(np.array(poly.exterior.coords), RING, c)
        i = offset_ring(np.array(poly.exterior.coords), 0.8, c)
        outs.append(place_yz(o, float(s)))
        ins.append(place_yz(i, float(s)))
    return loft_shell(outs, ins)


def deck_cut(x0: float, x1: float, w: float, ledge: float = 0.0):
    """Box that removes the deck skin between x0..x1 (for hatch openings)."""
    zc = (deck_z(x0) + deck_z(x1)) / 2.0
    return box([x1 - x0, w, 30.0], [(x0 + x1) / 2.0, 0.0, zc + 15.0 - ledge])


def build_f1():
    """Nose: cowl, firewall with thrust angles, battery bay, canopy opening."""
    shell = fuse_shell(SPLIT[0], SPLIT[1])

    # --- firewall, tilted for 2 deg down and 2 deg right thrust
    fw = bulkhead(MOTOR_X, 2.4)
    rot = trimesh.transformations.concatenate_matrices(
        trimesh.transformations.rotation_matrix(math.radians(-THRUST_DOWN), [0, 1, 0],
                                                [MOTOR_X, 0, 3]),
        trimesh.transformations.rotation_matrix(math.radians(-THRUST_RIGHT), [0, 0, 1],
                                                [MOTOR_X, 0, 3]))
    fw.apply_transform(rot)
    holes = [cyl(4.6, 14, [MOTOR_X - 6, 0, 3], [1, 0, 0])]            # shaft/wire pass
    for pitch in (16.0, 19.0):
        for sy in (-1, 1):
            for sz in (-1, 1):
                holes.append(cyl(1.6, 14, [MOTOR_X - 6, sy * pitch / 2,
                                           3 + sz * pitch / 2], [1, 0, 0]))
    hole_solid = union(*holes)
    hole_solid.apply_transform(rot)
    fw = diff(fw, hole_solid)

    # --- cooling louvres in the cowl cheeks
    louvres = []
    for sy in (-1, 1):
        for k in range(3):
            louvres.append(cyl(3.2, 40, [40 + k * 13, sy * 40, -4], [0, sy, 0.25]))
    shell = diff(shell, union(*louvres))

    # --- battery tray: floor plate on two rails
    floor = box([128, 46, 1.0], [122, 0, -17.5])
    rails = union(box([128, 1.4, 9], [122, -23, -13.5]),
                  box([128, 1.4, 9], [122, 23, -13.5]))
    slots = union(*[box([6, 60, 20], [x, 0, -17.5]) for x in (78, 166)])  # strap slots
    tray = diff(union(floor, rails), slots)
    tray = inter(tray, fuse_solid(SPLIT[0], SPLIT[1], shrink=SKIN + 0.4))  # trim to hull

    parts = [shell, fw, tray,
             former(70), former(150),
             collar(SPLIT[1] - 0.1, COLLAR_LEN)]
    body = union(*parts)

    # --- canopy/battery hatch opening in the deck
    body = diff(body, deck_cut(96, 192, 46))
    # locating lip for the canopy
    lip = []
    for x in (96.0, 192.0):
        lip.append(box([2.4, 46, 7], [x + (1.2 if x < 100 else -1.2), 0, deck_z(x) - 3.5]))
    body = union(body, *lip)
    return body


def build_f2():
    """Centre section: wing saddle, servo bays, avionics tray."""
    shell = fuse_shell(SPLIT[1], SPLIT[2])
    parts = [shell, former(250), former(360), former(408),
             collar(SPLIT[2] - 0.1, COLLAR_LEN)]
    body = union(*parts)

    # --- servo pockets, opening at the deck, arms facing aft
    cuts, frames = [], []
    for sy in (-1, 1):
        x0 = SERVO_X0
        yc = sy * (SERVO_W / 2 + 3.0)
        zc = deck_z(x0 + SERVO_L / 2)
        cuts.append(box([SERVO_L + 2 * FIT, SERVO_W + 2 * FIT, SERVO_H],
                        [x0 + SERVO_L / 2, yc, zc - SERVO_H / 2 + 0.1]))
        # flange relief so the servo ears sit on a ledge
        cuts.append(box([SERVO_L + 12, SERVO_W + 2 * FIT, 3.0],
                        [x0 + SERVO_L / 2, yc, zc - 1.5]))
        # thin-walled socket around the pocket, not a solid block
        outer = box([SERVO_L + 2 * FIT + 2.6, SERVO_W + 2 * FIT + 2.6, SERVO_H - 2],
                    [x0 + SERVO_L / 2, yc, zc - (SERVO_H - 2) / 2])
        cavity = box([SERVO_L + 2 * FIT, SERVO_W + 2 * FIT, SERVO_H],
                     [x0 + SERVO_L / 2, yc, zc - SERVO_H / 2 - 1.4])
        frames.append(diff(outer, cavity))
        for sx in (-1, 1):
            cuts.append(cyl(0.85, 8, [x0 + SERVO_L / 2 + sx * SERVO_SCREW_PITCH / 2,
                                      yc, zc - 6], [0, 0, 1]))
    body = union(body, *frames)
    body = diff(body, *cuts)

    # --- wing hold-down bosses (M3 self-tapping)
    bosses, bores = [], []
    for bx in BOLT_X:
        x = WING_LE + bx
        for sy in (-1, 1):
            top = deck_z(x)
            bosses.append(cyl(4.5, 13, [x, sy * BOLT_Y, top - 13], [0, 0, 1]))
            bores.append(cyl(1.35, 16, [x, sy * BOLT_Y, top - 14], [0, 0, 1]))
    body = union(body, *bosses)
    body = diff(body, *bores)

    # --- avionics shelf ahead of the wing
    shelf = box([44, 50, 1.0], [220, 0, -6.0])
    shelf = inter(shelf, fuse_solid(SPLIT[1], SPLIT[2], shrink=SKIN + 0.4))
    body = union(body, shelf)

    # --- pushrod exits through the aft former
    body = diff(body, *[cyl(1.9, 20, [408, sy * 9, -4], [1, 0, 0]) for sy in (-1, 1)])
    return body


def build_f3():
    """Tail boom."""
    body = union(fuse_shell(SPLIT[2], SPLIT[3]),
                 former(470), former(540), former(595),
                 collar(SPLIT[3] - 0.1, COLLAR_LEN))
    guides = []
    for x in (470, 540, 595):
        for sy in (-1, 1):
            guides.append(cyl(1.9, 6, [x - 3, sy * 6, -3], [1, 0, 0]))
    return diff(body, *guides)


STAB_X = 655.0          # fuselage station of the stab LE
STAB_Z = -1.0           # stab mid-thickness height
FIN_X = 645.0           # fuselage station of the fin LE


def build_f4():
    """Tail cone / fin post: stab seat, fin slot, joiner bore, skid."""
    body = union(fuse_shell(SPLIT[3], SPLIT[4]), former(645))

    # ledge the two stab halves sit on, sticking out both sides
    seat = box([88, 26, 1.2], [STAB_X + 44, 0, STAB_Z - STAB_T / 2 - 0.6])
    body = union(body, seat)

    # slot for the fin tab, down from the flat tail deck
    fin_slot = box([FIN_CR - 15, FIN_T + 2 * FIT, 11.0],
                   [FIN_X + FIN_CR * 0.42, 0, TAIL_DECK_Z - 4.0])
    # bore for the 3 mm carbon rod that ties the stab halves together
    rod = cyl(1.75, 60, [STAB_X + STAB_CR * 0.35, -30, STAB_Z], [0, 1, 0])
    body = diff(body, fin_slot, rod)

    # tail skid
    skid = box([22, 2.6, 12], [714, 0, -10.0])
    body = union(body, skid)
    body = diff(body, *[cyl(1.9, 14, [636, sy * 4, -3], [1, 0, 0]) for sy in (-1, 1)])
    return body


# ---------------------------------------------------------------- canopy

CANOPY = np.array([
    [96,  40, 1.5],
    [104, 46, 11.0],
    [118, 50, 19.0],
    [140, 50, 21.0],
    [162, 48, 19.0],
    [180, 42, 12.0],
    [192, 34, 4.0],
])


def build_canopy():
    cw = PchipInterpolator(CANOPY[:, 0], CANOPY[:, 1])
    ch = PchipInterpolator(CANOPY[:, 0], CANOPY[:, 2])
    outs, ins = [], []
    xs = list(np.arange(96.0, 192.0, 3.0)) + [192.0]
    for x in xs:
        w, h = float(cw(x)), float(ch(x))
        base = deck_z(x)
        ring = superellipse(w, 2 * h, 2.4, RING)
        ring[:, 1] += base
        poly = Polygon(ring).intersection(sbox(-200, base, 200, 400))
        if poly.geom_type == "MultiPolygon":
            poly = max(poly.geoms, key=lambda g: g.area)
        c = np.array(poly.representative_point().coords[0])
        outs.append(place_yz(resample(poly, RING, c), x))
        ins.append(place_yz(offset_ring(np.array(poly.exterior.coords), SKIN, c), x))
    body = loft_shell(outs, ins)

    # inner lip that drops into the deck opening
    lip = diff(box([92, 44.4, 6.0], [144, 0, deck_z(144) - 2.0]),
               box([92, 42.4, 6.0], [144, 0, deck_z(144) - 2.0]))
    body = union(body, lip)
    # magnet pockets (6 x 3 mm discs)
    mags = [cyl(3.15, 3.2, [x, 0, deck_z(x) - 0.2], [0, 0, 1]) for x in (103.0, 186.0)]
    return diff(body, *mags)


# ---------------------------------------------------------------- wing

TIP_LEN = 30.0


def wing_panel(span: float, c0: float, c1: float, ribs, tip=False,
               spar=True, bolts=False, tip_slot=False, tongue=False):
    stations = list(np.arange(0.0, span - (TIP_LEN if tip else 0.0), 5.0))
    if tip:
        # denser sampling through the rounded tip
        stations += list(span - TIP_LEN + np.linspace(0, TIP_LEN, 9))
    else:
        stations += [span]

    def sec(y):
        if tip and y > span - TIP_LEN:
            u = min(1.0, (y - (span - TIP_LEN)) / TIP_LEN)
            base = c0 + (c1 - c0) * ((span - TIP_LEN) / span)
            c = base * (1.0 - 0.45 * u ** 1.4)
            zs = 1.0 - 0.55 * u ** 1.5
            return c, zs, base
        c = c0 + (c1 - c0) * (y / span)
        return c, 1.0, c

    outs, ins = [], []
    for y in stations:
        c, zs, base = sec(float(y))
        a = clark_y(c)
        a[:, 1] *= zs
        # keep the tip rounding centred on the section
        if zs < 1.0:
            a[:, 0] += (base - c) * 0.32
        cen = np.array([a[:, 0].mean(), a[:, 1].mean() * 0.8 + 0.5])
        outs.append(place_xz(resample(a, RING, cen), float(y)))
        ins.append(place_xz(offset_ring(a, SKIN, cen), float(y)))
    body = loft_shell(outs, ins)

    # internal ribs
    rib_solids = []
    for y in ribs:
        c, zs, base = sec(float(y))
        a = clark_y(c)
        a[:, 1] *= zs
        if zs < 1.0:
            a[:, 0] += (base - c) * 0.32
        cen = np.array([a[:, 0].mean(), a[:, 1].mean() * 0.8 + 0.5])
        r = resample(a, RING, cen)
        slab = loft_solid([place_xz(r, y - 0.55), place_xz(r, y + 0.55)])
        # lightening holes, sized off the local section thickness
        lighten = [cyl(0.030 * c * zs, 6, [0.22 * c, y - 3, 0.057 * c * zs], [0, 1, 0]),
                   cyl(0.032 * c * zs, 6, [0.45 * c, y - 3, 0.054 * c * zs], [0, 1, 0]),
                   cyl(0.021 * c * zs, 6, [0.72 * c, y - 3, 0.036 * c * zs], [0, 1, 0])]
        rib_solids.append(diff(slab, union(*lighten)))
    if rib_solids:
        body = union(body, *rib_solids)

    if spar:
        sx = SPAR_XC * c0
        tube = cyl(SPAR_D / 2 + 1.6, span + 2, [sx, -1, SPAR_Z], [0, 1, 0])
        tube = inter(tube, loft_solid(outs))
        body = union(body, tube)
        body = diff(body, cyl(SPAR_D / 2, span + 8, [sx, -4, SPAR_Z], [0, 1, 0]))

    if bolts:
        bs, br = [], []
        for bx in BOLT_X:
            bs.append(cyl(4.4, 30, [bx, BOLT_Y, -1], [0, 0, 1]))
            br.append(cyl(1.7, 40, [bx, BOLT_Y, -4], [0, 0, 1]))
        bs = inter(union(*bs), loft_solid(outs))
        body = union(body, bs)
        body = diff(body, *br)

    if tip_slot:      # socket for the outer panel tongue, cut at the dihedral angle
        t = box([46, TONGUE_L, 3.4 + 2 * FIT],
                [0.30 * c1 + 4, span - TONGUE_L / 2, 0.055 * c1])
        t.apply_transform(trimesh.transformations.rotation_matrix(
            math.radians(DIHEDRAL), [1, 0, 0], [0, span, 0.055 * c1]))
        body = diff(body, t)

    if tongue:        # blade that plugs into the inner panel
        tg = box([46, TONGUE_L, 3.4], [0.30 * c0 + 4, -TONGUE_L / 2, 0.055 * c0])
        body = union(body, tg)

    return body


def build_wing_inner():
    return wing_panel(B_INNER, C_ROOT, C_MID, ribs=[48, 96, 144, 192],
                      spar=True, bolts=True, tip_slot=True)


def build_wing_outer():
    return wing_panel(B_OUTER, C_MID, C_TIP, ribs=[42, 88, 134, 176],
                      tip=True, spar=False, tongue=True)


# ---------------------------------------------------------------- tail

def plate_panel(span, c0, c1, thick, ribs, rod=None, tip_round=True, tab=None):
    stations = list(np.arange(0.0, span, 5.0)) + [span]

    def sec(y):
        c = c0 + (c1 - c0) * (y / span)
        zs = 1.0
        if tip_round and y > span - 14.0:
            u = (y - (span - 14.0)) / 14.0
            c *= (1 - 0.55 * u ** 1.6)
            zs = math.sqrt(max(1e-3, 1 - u ** 2.2))
        return c, zs

    outs, ins = [], []
    for y in stations:
        c, zs = sec(float(y))
        a = flat_plate(c, thick * zs)
        cen = np.array([c * 0.45, 0.0])
        outs.append(place_xz(resample(a, RING, cen), float(y)))
        ins.append(place_xz(offset_ring(a, SKIN, cen), float(y)))
    body = loft_shell(outs, ins)

    for y in ribs:
        c, zs = sec(float(y))
        a = flat_plate(c, thick * zs)
        cen = np.array([c * 0.45, 0.0])
        r = resample(a, RING, cen)
        body = union(body, loft_solid([place_xz(r, y - 0.5), place_xz(r, y + 0.5)]))

    if rod is not None:
        xr, dia = rod
        t = cyl(dia / 2 + 1.3, span + 2, [xr, -1, 0], [0, 1, 0])
        body = union(body, inter(t, loft_solid(outs)))
        body = diff(body, cyl(dia / 2, span + 8, [xr, -4, 0], [0, 1, 0]))
    if tab is not None:
        body = union(body, tab)
    return body


def build_stab_half():
    return plate_panel(STAB_SPAN / 2, STAB_CR, STAB_CT, STAB_T,
                       ribs=[40, 85, 130], rod=(STAB_CR * 0.35, 3.2))


def build_elevator_half():
    body = plate_panel(STAB_SPAN / 2 - 2.0, ELEV_C, ELEV_C - 7, 5.4,
                       ribs=[40, 85, 130], rod=(ELEV_C * 0.5, 2.2))
    body = _shear_x(body, (STAB_CT - STAB_CR) / (STAB_SPAN / 2))   # follow the stab TE
    horn = box([9, 2.0, 17], [ELEV_C * 0.5, 26, -8.0])
    horn = diff(horn, cyl(0.8, 6, [ELEV_C * 0.5, 26, -13.0], [0, 1, 0]))
    return union(body, horn)


FIN_SWEEP = 20.0        # degrees of LE sweep


def _shear_x(mesh, slope):
    """Sweep a panel by shearing X with span (Y) — keeps sections true."""
    m = mesh.copy()
    m.vertices[:, 0] += slope * m.vertices[:, 1]
    return m


def build_fin():
    body = plate_panel(FIN_H, FIN_CR, FIN_CT, FIN_T, ribs=[45, 95])
    body = _shear_x(body, math.tan(math.radians(FIN_SWEEP)))
    # tab that drops into the tail-cone slot (span direction is -Y)
    tab = box([FIN_CR - 18, 10.0, FIN_T], [FIN_CR * 0.42, -5.0, 0.0])
    return union(body, tab)


def build_rudder():
    body = plate_panel(FIN_H - 10, RUD_C, RUD_C - 9, 5.0, ribs=[45, 95])
    # the rudder LE has to sit on the fin TE, which is swept LE minus the taper
    body = _shear_x(body, math.tan(math.radians(FIN_SWEEP))
                    + (FIN_CT - FIN_CR) / FIN_H)
    horn = box([8, 2.0, 15], [RUD_C * 0.55, 12, -8.0])
    horn = diff(horn, cyl(0.8, 6, [RUD_C * 0.55, 12, -13.0], [0, 1, 0]))
    return union(body, horn)


# ---------------------------------------------------------------- assembly

def mirror(mesh):
    """Mirror about the XZ plane, flipping winding so the solid stays valid."""
    m = mesh.copy()
    m.vertices[:, 1] *= -1.0
    m.faces = m.faces[:, ::-1]
    return m


# How each part must be laid on the bed. Thin shells have to be oriented so
# that no large surface is horizontal, otherwise a 1-perimeter skin cannot be
# printed. Fuselage sections and tail surfaces therefore stand on a flat joint
# face (every layer is then a closed loop); the wing lies flat because its
# Clark Y underside *is* a plane and makes a perfect first layer.
PRINT_ORIENT = {
    "upright": (90.0, [0, 1, 0]),    # fuselage: aft face down, nose up
    "onroot": (90.0, [1, 0, 0]),     # tail surfaces: root face down, span up
    "flat": None,                    # wings, canopy: as modelled
}


def place_for_print(mesh, orient="flat"):
    """Rotate into the recommended print pose, drop onto Z=0, centre on the bed."""
    m = mesh.copy()
    spec = PRINT_ORIENT[orient]
    if spec is not None:
        ang, axis = spec
        m.apply_transform(trimesh.transformations.rotation_matrix(
            math.radians(ang), axis, [0, 0, 0]))
    m.apply_translation(-m.bounds[0])
    c = m.bounds.mean(axis=0)
    m.apply_translation([-c[0], -c[1], 0])
    return m


def assembled(parts):
    """Pose the parts into the flying configuration (preview / CG check)."""
    def rot(m, ang, axis, point=(0, 0, 0)):
        m.apply_transform(trimesh.transformations.rotation_matrix(
            math.radians(ang), axis, point))
        return m

    out = {k: v.copy() for k, v in parts.items()
           if k.startswith("fuse") or k == "canopy_hatch"}

    # +2 deg about +Y drops the TE, so the flat wing underside lies on the
    # 2 deg deck -> the wing ends up at +2 deg incidence to the fuselage datum
    inc = trimesh.transformations.rotation_matrix(
        math.radians(INCIDENCE), [0, 1, 0], [0, 0, 0])

    for side, tag in ((1, "R"), (-1, "L")):
        w = parts["wing_inner"].copy()
        if side < 0:
            w = mirror(w)
        w.apply_transform(inc)
        w.apply_translation([WING_LE, 0, deck_z(WING_LE)])
        out[f"wing_inner_{tag}"] = w

        o = parts["wing_outer"].copy()
        if side < 0:
            o = mirror(o)
        rot(o, side * DIHEDRAL, [1, 0, 0])
        o.apply_transform(inc)
        o.apply_translation([WING_LE, side * B_INNER, deck_z(WING_LE)])
        out[f"wing_outer_{tag}"] = o

        s = parts["stab_half"].copy()
        if side < 0:
            s = mirror(s)
        s.apply_translation([STAB_X, side * 6.5, STAB_Z])
        out[f"stab_{tag}"] = s

        e = parts["elevator_half"].copy()
        if side < 0:
            e = mirror(e)
        e.apply_translation([STAB_X + STAB_CR + 1.5, side * 8.0, STAB_Z])
        out[f"elev_{tag}"] = e

    f = rot(parts["fin"].copy(), 90, [1, 0, 0])
    f.apply_translation([FIN_X, 0, TAIL_DECK_Z])
    out["fin_a"] = f

    r = rot(parts["rudder"].copy(), 90, [1, 0, 0])
    r.apply_translation([FIN_X + FIN_CR + 1.5, 0, TAIL_DECK_Z])
    out["rudder_a"] = r
    return out


def wing_geometry():
    """Exact wing area / MAC / CG from the panel planform."""
    def panel(c0, c1, span):
        ys = np.linspace(0, span, 400)
        c = c0 + (c1 - c0) * ys / span
        return np.trapezoid(c, ys), np.trapezoid(c ** 2, ys), np.trapezoid(c * ys, ys)

    a1, q1, m1 = panel(C_ROOT, C_MID, B_INNER)
    a2, q2, m2 = panel(C_MID, C_TIP, B_OUTER)
    area_half = a1 + a2
    mac = (q1 + q2) / area_half
    y_mac = (m1 + (m2 + B_INNER * a2)) / area_half
    area = 2 * area_half / 10000.0                 # dm^2
    span = 2 * (B_INNER + B_OUTER)
    return {"span_mm": span, "area_dm2": round(area, 2), "mac_mm": round(mac, 1),
            "y_mac_mm": round(y_mac, 1), "aspect_ratio": round((span / 100) ** 2 / area, 2),
            "cg_mm_from_nose": round(WING_LE + 0.28 * mac, 1),
            "cg_mm_behind_wing_le": round(0.28 * mac, 1)}


PARTS = [
    ("01_fuse_F1_nose", build_f1, "upright"),
    ("02_canopy_hatch", build_canopy, "flat"),
    ("03_fuse_F2_centre", build_f2, "upright"),
    ("04_fuse_F3_boom", build_f3, "upright"),
    ("05_fuse_F4_tailcone", build_f4, "upright"),
    ("06_wing_inner", build_wing_inner, "flat"),
    ("07_wing_outer", build_wing_outer, "flat"),
    ("08_stab_half", build_stab_half, "onroot"),
    ("09_elevator_half", build_elevator_half, "onroot"),
    ("10_fin", build_fin, "onroot"),
    ("11_rudder", build_rudder, "onroot"),
]

MIRRORED = {"06_wing_inner", "07_wing_outer", "08_stab_half", "09_elevator_half"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="stl")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    raw, rows = {}, []
    for name, fn, orient in PARTS:
        if args.only and args.only not in name:
            continue
        m = fn()
        key = name.split("_", 1)[1]
        raw[key] = m
        variants = [(name + "_R", m), (name + "_L", mirror(m))] if name in MIRRORED \
            else [(name, m)]
        for tag, mesh in variants:
            p = place_for_print(mesh, orient)
            p.export(os.path.join(args.out, tag + ".stl"))
            r = report(tag, p)
            r["print_pose"] = orient
            rows.append(r)
            print(f"{tag:26s} {str(r['size_mm']):24s} max {r['max_dim']:6.1f} "
                  f"{r['mass_lwpla_g']:6.1f} g  wt={r['watertight']}")

    total = sum(r["mass_lwpla_g"] for r in rows)
    over = [r for r in rows if r["max_dim"] > 250.0]
    leak = [r for r in rows if not r["watertight"]]
    print(f"\nairframe mass (LW-PLA @ {LWPLA_DENSITY*1000:.2f} g/cm3): {total:.0f} g")
    print(f"parts over 250 mm: {[r['part'] for r in over] or 'none'}")
    print(f"non-watertight   : {[r['part'] for r in leak] or 'none'}")
    with open(os.path.join(args.out, "parts.json"), "w") as fh:
        json.dump({"parts": rows, "airframe_mass_g": round(total, 1)}, fh, indent=2)
    return raw


if __name__ == "__main__":
    main()
