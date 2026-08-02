// =====================================================================
//  ESP32-DIV V2 — compact handheld enclosure (parametric)
//  Two parts: FRONT (screen + button face) and BACK (battery + ports).
//  Designed for the full ESP32-DIV V2 build:
//    - 2.8" ILI9341 + XPT2046 touch display
//    - ESP32-S3 main board + RF shield (3x nRF24 + CC1101 + IR)
//    - 18650 Li-ion cell, IP5306 charger, microSD, PN532 RFID coil
//
//  UNITS: millimetres.  All key numbers are parameters — measure YOUR
//  boards and tweak before printing. Print in PETG or PLA, 0.2mm layers,
//  3 perimeters. No supports needed if printed face-down / open-side-up.
//
//  Render a single part for export, e.g.:
//    openscad -D 'part="front"' -o front.stl enclosure.scad
//    openscad -D 'part="back"'  -o back.stl  enclosure.scad
// =====================================================================

part = "both";          // "front" | "back" | "both"
$fn = 64;

/* ---------- Outer body ---------- */
ext_w        = 74;      // external width
ext_h        = 132;     // external height
wall         = 2.4;     // wall thickness
corner_r     = 5;       // outer corner radius
total_depth  = 30;      // front_depth + back_depth
front_depth  = 13;      // internal depth of the front half (screen side)
back_depth   = total_depth - front_depth;

/* ---------- Screen window (2.8" ILI9341 active area = 43.2 x 57.6) ---------- */
screen_w        = 46;   // window width  (a little larger than active area)
screen_h        = 61;   // window height
screen_off_top  = 11;   // gap from inner top edge to top of window
screen_x        = 0;    // horizontal offset of window centre (0 = centred)

/* ---------- Navigation buttons (UP/DOWN/LEFT/RIGHT/SELECT) ---------- */
btn_d           = 7;    // button hole diameter
btn_pitch       = 13;   // spacing of the D-pad cross
btn_cluster_dy  = 26;   // distance from window bottom to cross centre

/* ---------- Side / edge ports ---------- */
usb_w    = 11;  usb_h = 7;    usb_from_left = 0;   // USB-C on bottom edge (centred)
sd_w     = 13;  sd_h  = 3;    sd_from_top   = 24;  // microSD on right edge
sw_w     = 9;   sw_h  = 5;    sw_from_top   = 20;  // power switch on left edge
ant_d    = 7.0;               // SMA antenna holes on top edge
ant_count= 3;                 // number of antenna holes
ant_spread = 40;              // total spread of antenna holes across top

/* ---------- RFID coil zone (thin back panel for good NFC coupling) ---------- */
rfid_zone_w   = 46;
rfid_zone_h   = 42;
rfid_zone_dy  = 30;     // from inner bottom edge upward to zone centre
rfid_wall     = 1.2;    // thinned wall over the coil (closer = better read)

/* ---------- Assembly (corner screw bosses) ---------- */
boss_r       = 4.0;     // boss outer radius
boss_pilot   = 1.5;     // pilot hole radius (self-tapping M2.5 into front)
boss_clear   = 1.6;     // clearance hole radius (back)
boss_inset   = 7;       // boss centre inset from outer corners
lip_h        = 4;       // interlocking lip height
lip_t        = 1.2;     // lip thickness

// ---------------------------------------------------------------------
//  Helpers
// ---------------------------------------------------------------------
module rrect(w, h, r) {
    hull() for (sx=[-1,1], sy=[-1,1])
        translate([sx*(w/2-r), sy*(h/2-r)]) circle(r=r);
}

// A shell (box hollow on +Z open side) of external w x h x depth.
module shell_body(w, h, depth, r, wthk) {
    difference() {
        linear_extrude(depth) rrect(w, h, r);
        translate([0,0,wthk])
            linear_extrude(depth) rrect(w-2*wthk, h-2*wthk, r-wthk);
    }
}

module corner_bosses(depth, hole_r, countersink=false) {
    for (sx=[-1,1], sy=[-1,1])
        translate([sx*(ext_w/2-boss_inset), sy*(ext_h/2-boss_inset), 0]) {
            difference() {
                cylinder(h=depth, r=boss_r);
                translate([0,0,-0.1]) cylinder(h=depth+0.2, r=hole_r);
                if (countersink)
                    translate([0,0,depth-2.2]) cylinder(h=2.3, r1=hole_r, r2=hole_r+1.8);
            }
        }
}

// Interlocking lip that sits on the front's inner rim.
module inner_lip(depth) {
    linear_extrude(depth)
        difference() {
            rrect(ext_w-2*wall+0.3, ext_h-2*wall+0.3, corner_r-wall);
            rrect(ext_w-2*wall-2*lip_t, ext_h-2*wall-2*lip_t, corner_r-wall-lip_t);
        }
}

// ---------------------------------------------------------------------
//  FRONT shell  (screen face up along +Z, opening toward the back)
// ---------------------------------------------------------------------
module front_part() {
    difference() {
        union() {
            shell_body(ext_w, ext_h, front_depth, corner_r, wall);
            // screw bosses grow from the closed (screen) face inward
            corner_bosses(front_depth, boss_pilot, false);
        }
        // Screen window through the closed face
        translate([screen_x, ext_h/2 - wall - screen_off_top - screen_h/2, -0.1])
            linear_extrude(wall+0.2) rrect(screen_w, screen_h, 2);

        // Button cross below the window
        by = ext_h/2 - wall - screen_off_top - screen_h - btn_cluster_dy;
        for (p = [[0,0],[0,btn_pitch],[0,-btn_pitch],[btn_pitch,0],[-btn_pitch,0]])
            translate([p[0], by + p[1], -0.1])
                cylinder(h=wall+0.2, d=btn_d);
    }
}

// ---------------------------------------------------------------------
//  BACK shell  (battery + ports; opening toward the front)
// ---------------------------------------------------------------------
module back_part() {
    difference() {
        union() {
            shell_body(ext_w, ext_h, back_depth, corner_r, wall);
            corner_bosses(back_depth, boss_clear, true);
            inner_lip(lip_h);
        }
        // --- RFID coil zone: thin the back face over a rectangle ---
        translate([0, -ext_h/2 + wall + rfid_zone_dy, 0])
            translate([0,0,rfid_wall])
                linear_extrude(wall) rrect(rfid_zone_w, rfid_zone_h, 3);

        // --- USB-C on bottom edge ---
        translate([usb_from_left, -ext_h/2 - 0.1, back_depth/2])
            rotate([-90,0,0]) linear_extrude(wall+0.2) rrect(usb_w, usb_h, 1.5);

        // --- microSD on right edge ---
        translate([ext_w/2 - wall - 0.1, ext_h/2 - sd_from_top, back_depth/2])
            rotate([0,90,0]) linear_extrude(wall+0.4) rrect(sd_h, sd_w, 1);

        // --- power switch on left edge ---
        translate([-ext_w/2 + wall + 0.1, ext_h/2 - sw_from_top, back_depth/2])
            rotate([0,-90,0]) linear_extrude(wall+0.4) rrect(sw_h, sw_w, 1);

        // --- SMA antenna holes on top edge ---
        for (i = [0:ant_count-1]) {
            x = (ant_count==1) ? 0 : -ant_spread/2 + i*ant_spread/(ant_count-1);
            translate([x, ext_h/2 + 0.1, back_depth/2])
                rotate([90,0,0]) cylinder(h=wall+0.2, d=ant_d);
        }
    }
}

// ---------------------------------------------------------------------
//  Layout for export / preview
// ---------------------------------------------------------------------
if (part == "front") front_part();
else if (part == "back") back_part();
else {
    // "both" — laid out side by side for a preview render
    translate([-ext_w/2 - 6, 0, 0]) front_part();
    translate([ ext_w/2 + 6, 0, 0]) back_part();
}
