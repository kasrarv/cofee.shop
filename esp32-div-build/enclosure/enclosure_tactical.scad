// =====================================================================
//  ESP32-DIV V2 "TACTICAL v4" — compact, button-less, no-GPS, no-radar
//  ---------------------------------------------------------------------
//  Changes in v4 (per feedback):
//   * RADAR REMOVED — its bay is gone, so the body is shorter (126 -> 100 mm)
//   * Battery 40 x 55 mm (3000 mAh)
//   * Dedicated TP4056 charger bay, open, USB aligned to the bottom-edge cutout
//   * USB-C cutout sized to a real USB-C port
//   * PN5180/PN532 RFID coil window on the FRONT (tap card below the screen)
//   * Narrower, shorter one-hand body. GPS + radar both dropped.
//
//  All key numbers are parameters. When you send the exact TP4056 model /
//  photo I'll set tp_* to match it. Print a draft and check fit first.
//
//  Export:
//    openscad -D 'part="front"' -o tactical_front.stl enclosure_tactical.scad
//    openscad -D 'part="back"'  -o tactical_back.stl  enclosure_tactical.scad
// =====================================================================

part = "both";
$fn = 56;

/* ---------------- Outer body ---------------- */
ext_w       = 70;      // narrower (one-hand); display module ~50 wide
// With the radar gone, only charger + battery stack on the back, so the body
// drops to ~100 mm — driven now by the 2.8" display (86 mm) plus margins.
ext_h       = 100;
wall        = 2.4;
chamf       = 10;
total_depth = 27;
front_depth = 10;
back_depth  = total_depth - front_depth;
edge_bevel  = 3.0;

/* ---------------- Screen (2.8" ILI9341 active 43.2 x 57.6) ---------------- */
screen_w = 45; screen_h = 60; screen_off_top = 9;
bezel1_margin = 4.0; bezel1_depth = 1.3;
bezel2_margin = 2.0; bezel2_depth = 0.6;

/* ---------------- Battery bay: 40 x 55 mm 3000 mAh ---------------- */
batt_w = 41; batt_l = 56; batt_t = 10;
batt_center_dy = 6;            // battery centre offset from box centre (+ = up)
batt_wallh = batt_t + 1;

/* ---------------- TP4056 charger bay (open, USB to bottom edge) ---------------- */
// Common TP4056 board ~26x17; USB-C variant ~27x18. TUNE to your module.
tp_w = 27; tp_l = 18; tp_h = 6;
tp_from_bottom = 5;            // gap from inner bottom edge to the bay
tp_post = 1.2;

/* ---------------- USB-C cutout on the bottom edge (real size) ---------------- */
usb_w = 9.5; usb_h = 3.6;      // USB-C plug clearance
usb_z = 6;                     // height of the port centre above the back floor
usb_x = 0;                     // align to the TP4056 USB position (centred)

/* ---------------- PCB standoffs (Main board) — TUNE to your holes ---------------- */
standoff_h = 5; standoff_or = 3.2; standoff_ir = 1.3;
pcb_hole_dx = 42; pcb_hole_dy = 58; pcb_center_dy = 6;

/* ---------------- RFID coil window (PN5180 antenna) — on the FRONT ---------------- */
// The back is full of battery/charger, so the RFID coil lives on the FRONT,
// below the screen: you tap the card on the lower front. Thinned skin for good
// coupling. rfid_front_cy = centre offset (negative = below screen).
rfid_zone_w = 42; rfid_zone_h = 24; rfid_front_cy = -33; rfid_wall = 1.0;

/* ---------------- Edge ports ---------------- */
sd_w = 13.0; sd_h = 2.8; sd_from_top = 20;
sw_w = 9.0;  sw_h = 5.0; sw_from_top = 16;
ant_d = 6.5; ant_count = 5; ant_spread = 42;   // 5 SMA holes, top edge

/* ---------------- Kickstand (rear wedge; aim radar -> screen reclines) ---------------- */
kickstand = true; ks_len = 38; ks_thick = 10;

/* ---------------- Assembly ---------------- */
boss_r = 4.0; boss_pilot = 1.5; boss_clear = 1.6;
boss_inset = 8; lip_h = 4; lip_t = 1.2; groove_depth = 0.8;

// ---------------------------------------------------------------------
module tprofile(w, h, c) {
    polygon([[-w/2+c,-h/2],[ w/2-c,-h/2],[ w/2,-h/2+c],[ w/2, h/2-c],
             [ w/2-c, h/2],[-w/2+c, h/2],[-w/2, h/2-c],[-w/2,-h/2+c]]);
}
module shell_body(w, h, depth, c, wthk) {
    difference() {
        linear_extrude(depth) tprofile(w, h, c);
        translate([0,0,wthk]) linear_extrude(depth) tprofile(w-2*wthk, h-2*wthk, c-wthk);
    }
}
module corner_bosses(depth, hole_r, countersink=false) {
    for (sx=[-1,1], sy=[-1,1])
        translate([sx*(ext_w/2-boss_inset), sy*(ext_h/2-boss_inset), 0])
            difference() {
                cylinder(h=depth, r=boss_r);
                translate([0,0,-0.1]) cylinder(h=depth+0.2, r=hole_r);
                if (countersink) translate([0,0,depth-2.2]) cylinder(h=2.4, r1=hole_r, r2=hole_r+1.8);
            }
}
module inner_lip(depth) {
    linear_extrude(depth) difference() {
        tprofile(ext_w-2*wall+0.3, ext_h-2*wall+0.3, chamf-wall);
        tprofile(ext_w-2*wall-2*lip_t, ext_h-2*wall-2*lip_t, chamf-wall-lip_t);
    }
}
module posts(cx, cy, sw, sl, ph) {
    for (sx=[-1,1], sy=[-1,1])
        translate([cx+sx*(sw/2-3), cy+sy*(sl/2-3), wall])
            difference() { cylinder(h=3, r=2.2); translate([0,0,-0.1]) cylinder(h=3.2, r=ph); }
}
module face_accents(zf) {
    for (sx=[-1,1]) translate([sx*(ext_w/2-chamf-3), ext_h/2-chamf-3, zf-groove_depth])
        rotate([0,0,sx*45]) linear_extrude(groove_depth+0.1) square([15,1.5], center=true);
    for (dy=[0,3]) translate([0, -ext_h/2+wall+10+dy, zf-groove_depth])
        linear_extrude(groove_depth+0.1) square([ext_w-2*chamf-6,1.2], center=true);
}
module grip_scallops(depth) {
    for (sx=[-1,1], k=[-1,0,1])
        translate([sx*ext_w/2, k*14, depth/2]) rotate([0,90,0]) scale([1,2.2,1]) cylinder(h=3, r=3.5, center=true);
}

// ---------------------------------------------------------------------
//  FRONT
// ---------------------------------------------------------------------
module front_part() {
    win_cy = ext_h/2 - wall - screen_off_top - screen_h/2;
    difference() {
        union() { shell_body(ext_w, ext_h, front_depth, chamf, wall); corner_bosses(front_depth, boss_pilot, false); }
        translate([0, win_cy, -0.1]) linear_extrude(wall+0.2) tprofile(screen_w, screen_h, 4);
        translate([0, win_cy, -0.01]) linear_extrude(bezel1_depth+0.01) tprofile(screen_w+2*bezel1_margin, screen_h+2*bezel1_margin, 6);
        translate([0, win_cy, -0.01]) linear_extrude(bezel2_depth+0.01) tprofile(screen_w+2*(bezel1_margin+bezel2_margin), screen_h+2*(bezel1_margin+bezel2_margin), 7);
        for (sy=[-1,1]) translate([0, sy*ext_h/2, 0]) rotate([sy*45,0,0]) translate([0,0,-edge_bevel]) cube([ext_w+2, edge_bevel*2, edge_bevel*2], center=true);
        // RFID coil window: thinned front skin below the screen (tap card here)
        translate([0, rfid_front_cy, rfid_wall]) linear_extrude(wall) tprofile(rfid_zone_w, rfid_zone_h, 4);
        face_accents(0);
        grip_scallops(front_depth);
    }
}

// ---------------------------------------------------------------------
//  BACK
// ---------------------------------------------------------------------
module battery_bay() {
    cy = batt_center_dy;
    translate([0, cy, wall]) difference() {
        linear_extrude(batt_wallh) offset(2) square([batt_w, batt_l], center=true);
        translate([0,0,-0.1]) linear_extrude(batt_wallh+0.2) square([batt_w, batt_l], center=true);
    }
    // retention clips on the long sides
    for (sx=[-1,1]) translate([sx*(batt_w/2+1), cy, wall+batt_wallh-0.5]) translate([-1.2,-6,0]) cube([1.4,12,2.0]);
}
module charger_bay() {
    cy = -ext_h/2 + wall + tp_from_bottom + tp_l/2;
    // Open bay: guide rails on the two long sides + 2 posts. The USB side
    // (toward -Y / bottom edge) stays OPEN so the USB port is reachable.
    for (sx=[-1,1])
        translate([sx*(tp_w/2+0.8)-0.8, cy - tp_l/2, wall])
            cube([1.6, tp_l, tp_h]);
    posts(0, cy, tp_w, tp_l, tp_post);
}
module kickstand_wedge() {
    hull() {
        translate([0, -ext_h/2+wall+1, -ks_thick]) cube([ext_w-2*chamf-6, 2, 0.1], center=true);
        translate([0, -ext_h/2+wall+1, 0])          cube([ext_w-2*chamf-6, 2, 0.1], center=true);
        translate([0, -ext_h/2+wall+ks_len, 0])     cube([ext_w-2*chamf-6, 2, 0.1], center=true);
    }
}

module back_part() {
    difference() {
        union() {
            shell_body(ext_w, ext_h, back_depth, chamf, wall);
            corner_bosses(back_depth, boss_clear, true);
            inner_lip(lip_h);
            battery_bay();
            charger_bay();
            standoffs_all();
            if (kickstand) kickstand_wedge();
        }
        // (RFID coil window is on the FRONT — see front_part)
        // USB-C cutout on the bottom edge, aligned to the TP4056 USB
        translate([usb_x, -ext_h/2 - 0.1, usb_z]) rotate([-90,0,0]) linear_extrude(wall+0.2) offset(0.5) square([usb_w, usb_h], center=true);
        // microSD, right edge
        translate([ext_w/2 - wall - 0.1, ext_h/2 - sd_from_top, back_depth/2]) rotate([0,90,0]) linear_extrude(wall+0.4) square([sd_h, sd_w], center=true);
        // Power switch, left edge
        translate([-ext_w/2 + wall + 0.1, ext_h/2 - sw_from_top, back_depth/2]) rotate([0,-90,0]) linear_extrude(wall+0.4) square([sw_h, sw_w], center=true);
        // 5x SMA antenna holes, top edge
        for (i = [0:ant_count-1]) { x = (ant_count==1)?0:-ant_spread/2 + i*ant_spread/(ant_count-1);
            translate([x, ext_h/2 + 0.1, back_depth/2]) rotate([90,0,0]) cylinder(h=wall+0.2, d=ant_d); }
        // tactical grooves
        for (yy = [-ext_h/4+6, ext_h/4]) translate([0, yy, -0.01]) linear_extrude(groove_depth) square([ext_w-2*chamf-4, 1.4], center=true);
    }
}
module standoffs_all() {
    for (sx=[-1,1], sy=[-1,1])
        translate([sx*pcb_hole_dx/2, pcb_center_dy + sy*pcb_hole_dy/2, wall])
            difference() { cylinder(h=standoff_h, r=standoff_or); translate([0,0,-0.1]) cylinder(h=standoff_h+0.2, r=standoff_ir); }
}

// ---------------------------------------------------------------------
if (part == "front") front_part();
else if (part == "back") back_part();
else { translate([-ext_w/2-6,0,0]) front_part(); translate([ext_w/2+6,0,0]) back_part(); }
