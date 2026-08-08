"""Power system and performance analysis for SIMORGH-1S on a single Li-ion cell.

The interesting part of a 1S design is that the pack voltage is so low that
motor KV, prop size and cell internal resistance are all coupled: pick a prop
that is too big and the motor cannot spin it; pick a cell that sags and the
whole operating point collapses. So rather than assuming an rpm, this solves
the actual equilibrium between the motor and the propeller:

    motor :  I = (V_pack - omega/Kv) / R_motor,   Q = (I - I0)/Kv
    prop  :  Q = Cp rho n^2 D^5 / (2 pi),  T = Ct rho n^2 D^4
    pack  :  V_pack = V_oc - I * R_internal

Prop Ct/Cp are static (J=0) values of APC-E style blades.
"""

from __future__ import annotations

import json
import math

from scipy.optimize import brentq

RHO = 1.225

# prop: (diameter_in, pitch_in) -> static thrust and power coefficients
PROPS = {
    "3x3":   dict(d=3.0, ct=0.115, cp=0.050),
    "4x4":   dict(d=4.0, ct=0.110, cp=0.050),
    "5x4":   dict(d=5.0, ct=0.105, cp=0.048),
    "6x3":   dict(d=6.0, ct=0.108, cp=0.038),
    "6x4":   dict(d=6.0, ct=0.100, cp=0.045),
    "7x4":   dict(d=7.0, ct=0.098, cp=0.044),
}

# motor: KV, winding resistance [ohm], no-load current [A], mass [g]
MOTORS = {
    "1104 4500KV":  dict(kv=4500, rm=0.200, i0=0.5, mass=6),
    "1105 5000KV":  dict(kv=5000, rm=0.150, i0=0.6, mass=8),
    "2204 2300KV":  dict(kv=2300, rm=0.090, i0=0.7, mass=22),
    "2205 3000KV":  dict(kv=3000, rm=0.060, i0=0.9, mass=26),
    "2306 3600KV":  dict(kv=3600, rm=0.045, i0=1.2, mass=32),
}

# cell: open-circuit volts at ~60% SoC, internal resistance, capacity, mass
CELLS = {
    "18650 3500 mAh (35E)":   dict(voc=3.75, r=0.070, wh=12.6, i_max=8, mass=48),
    "18650 3000 mAh (30Q)":   dict(voc=3.75, r=0.025, wh=10.8, i_max=15, mass=47),
    "1S LiPo pouch 3500 mAh": dict(voc=3.80, r=0.020, wh=12.9, i_max=25, mass=60),
}
R_ESC = 0.015          # ESC + wiring + connector

MASS = [
    ("printed airframe (LW-PLA)", 184),
    ("motor + prop + adapter", 33),
    ("ESC 12 A, 1S capable", 7),
    ("ESP32-C3 SuperMini", 4),
    ("5 V / 2 A boost module", 5),
    ("2 x micro servo (9 g class)", 18),
    ("battery (1S Li-ion)", 48),
    ("carbon rods 6 / 3 / 2 mm", 11),
    ("pushrods, horns, hinge tape", 8),
    ("wiring, connector, magnets, screws", 12),
    ("adhesive in the joints", 10),
]

WING_AREA_DM2 = 11.94
CL_MAX = 1.15
LD_CRUISE = 8.0


def solve_operating_point(motor, prop, cell):
    """Find the rpm where motor torque equals prop torque."""
    kv_rad = motor["kv"] * 2 * math.pi / 60.0       # rad/s per volt
    kt = 1.0 / kv_rad                                # N.m per A
    d = prop["d"] * 0.0254
    r_tot = motor["rm"] + cell["r"] + R_ESC

    def residual(n):                                 # n in rev/s
        omega = 2 * math.pi * n
        i = (cell["voc"] - omega / kv_rad) / r_tot
        q_motor = kt * (i - motor["i0"])
        q_prop = prop["cp"] * RHO * n ** 2 * d ** 5 / (2 * math.pi)
        return q_motor - q_prop

    n_free = cell["voc"] * kv_rad / (2 * math.pi)      # free-running rev/s
    try:
        n = brentq(residual, 1.0, n_free * 1.05)
    except ValueError:
        return None
    omega = 2 * math.pi * n
    i = (cell["voc"] - omega / kv_rad) / r_tot
    v_pack = cell["voc"] - i * (cell["r"] + R_ESC)
    thrust = prop["ct"] * RHO * n ** 2 * d ** 4
    return dict(rpm=n * 60, amps=i, volts=v_pack, watts=i * v_pack,
                thrust_g=thrust / 9.81 * 1000.0)


def main():
    auw = sum(m for _, m in MASS)
    w_n = auw / 1000.0 * 9.81
    area = WING_AREA_DM2 / 100.0
    v_stall = math.sqrt(2 * w_n / (RHO * area * CL_MAX))

    print("=" * 74)
    print("MASS BUDGET")
    print("=" * 74)
    for name, m in MASS:
        print(f"  {name:40s} {m:5d} g")
    print(f"  {'ALL-UP WEIGHT':40s} {auw:5d} g")
    print(f"\n  wing area {WING_AREA_DM2} dm^2   wing loading "
          f"{auw / WING_AREA_DM2:.1f} g/dm^2")
    print(f"  stall {v_stall:.1f} m/s ({v_stall * 3.6:.0f} km/h)   "
          f"launch {v_stall * 1.3:.1f} m/s   cruise {v_stall * 1.5:.1f} m/s")

    cell = CELLS["18650 3500 mAh (35E)"]
    print("\n" + "=" * 74)
    print(f"MOTOR / PROP MATCH on {list(CELLS)[0]}  (Voc {cell['voc']} V, "
          f"Ri {cell['r']} ohm, {cell['i_max']} A limit)")
    print("=" * 74)
    print(f"  {'motor':14s} {'prop':6s} {'rpm':>7s} {'A':>6s} {'V':>5s} "
          f"{'W':>6s} {'thrust':>8s} {'T/W':>6s}   note")
    combos = [("2204 2300KV", "6x4"), ("2204 2300KV", "7x4"),
              ("2205 3000KV", "6x4"), ("2205 3000KV", "6x3"),
              ("2306 3600KV", "6x4"), ("2306 3600KV", "5x4"),
              ("1105 5000KV", "4x4"), ("1104 4500KV", "3x3")]
    best = None
    for mk, pk in combos:
        r = solve_operating_point(MOTORS[mk], PROPS[pk], cell)
        if r is None:
            continue
        tw = r["thrust_g"] / auw
        note = ""
        if r["amps"] > cell["i_max"]:
            note = f"over the {cell['i_max']} A cell limit"
        elif tw < 0.35:
            note = "too little thrust to launch"
        elif tw >= 0.45:
            note = "<== good"
        print(f"  {mk:14s} {pk:6s} {r['rpm']:7.0f} {r['amps']:6.1f} "
              f"{r['volts']:5.2f} {r['watts']:6.1f} {r['thrust_g']:6.0f} g "
              f"{tw:6.2f}   {note}")
        if not note.startswith("over") and (best is None or tw > best[1]):
            best = ((mk, pk), tw, r)

    print("\n  twin option, both motors on one cell:")
    for mk, pk in [("1104 4500KV", "3x3"), ("1105 5000KV", "4x4")]:
        r = solve_operating_point(MOTORS[mk], PROPS[pk], cell)
        if r is None:
            continue
        # two motors share the pack: recompute with doubled current draw
        i2 = r["amps"] * 2
        note = f"draws {i2:.1f} A total" + (
            "  -- over the cell limit" if i2 > cell["i_max"] else "")
        print(f"  2 x {mk:12s} {pk:6s} thrust {2 * r['thrust_g']:5.0f} g  "
              f"T/W {2 * r['thrust_g'] / auw:4.2f}   {note}")

    print("\n" + "=" * 74)
    print("ENDURANCE, level cruise")
    print("=" * 74)
    v = v_stall * 1.5
    drag = w_n / LD_CRUISE
    p_cruise = drag * v / 0.55 / 0.68
    print(f"  cruise {v:.1f} m/s, drag {drag:.2f} N -> {p_cruise:.1f} W electrical")
    for name, c in CELLS.items():
        t = c["wh"] * 0.85 / p_cruise * 60
        print(f"  {name:26s} {t:5.0f} min ideal, {t * 0.65:4.0f} min realistic "
              f"({c['mass']} g)")

    if best:
        (mk, pk), tw, r = best
        out = dict(auw_g=auw, wing_loading=round(auw / WING_AREA_DM2, 1),
                   v_stall_ms=round(v_stall, 2), motor=mk, prop=pk,
                   rpm=round(r["rpm"]), amps=round(r["amps"], 1),
                   thrust_g=round(r["thrust_g"]), t_over_w=round(tw, 2),
                   cruise_w=round(p_cruise, 1))
        with open("performance.json", "w") as fh:
            json.dump(out, fh, indent=2)
        print(f"\n  recommended: {mk} + {pk}")


if __name__ == "__main__":
    main()
