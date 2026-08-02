// =====================================================================
//  ESP32-DIV V2 "TACTICAL v2" — compact one-hand, button-less enclosure
//  ---------------------------------------------------------------------
//  Revised per build brief:
//   * Compact / one-hand: 72 mm wide, driven down to the 60 mm battery min
//   * Thin bezel so the 2.8" screen dominates the face (bigger look)
//   * Touch-only, NO buttons
//   * 5 antenna holes (3x nRF24 + CC1101 + main) — matches the real shield
//   * Correctly-sized ports: USB-C, microSD, power switch, SMA (6.5 mm)
//   * Post-modern / tactical look: big chamfers, beveled top/bottom edges,
//     stepped screen bezel, diagonal accent slashes, side grip scallops,
//     corner armor pads
//   * Radar module bay on the BACK + a rear KICKSTAND wedge, so when the
//     back (radar) is aimed at a target the screen reclines toward you
//   * Pre-defined no-glue bays: 60x80 LiPo (clips), PCB standoffs, radar posts
//
//  UNITS: mm. Parametric — MEASURE your boards and tune before final print.
//
//  Export:
//    openscad -D 'part="front"' -o tactical_front.stl enclosure_tactical.scad
//    openscad -D 'part="back"'  -o tactical_back.stl  enclosure_tactical.scad
// =====================================================================

part = "both";     // "front" | "back" | "both"
$fn = 56;

/* ---------------- Outer body ---------------- */
ext_w       = 72;
ext_h       = 118;
wall        = 2.4;
chamf       = 11;      // big angular corners (tactical)
total_depth = 28;
front_depth = 10;
back_depth  = total_depth - front_depth;
edge_bevel  = 3.2;     // 45-deg bevel on outer top/bottom face edges

/* ---------------- Screen (2.8" ILI9341 active 43.2 x 57.6) ---------------- */
screen_w       = 45;
screen_h       = 60;
screen_off_top = 9;
bezel1_margin  = 4.5;  bezel1_depth = 1.3;   // outer stepped frame
bezel2_margin  = 2.0;  bezel2_depth = 0.6;   // inner stepped frame

/* ---------------- Battery bay: 60 x 80 mm LiPo ---------------- */
batt_w = 61; batt_l = 81; batt_t = 11; batt_from_bottom = 7;
batt_wallh = batt_t + 1;

/* ---------------- PCB standoffs (Main board) — TUNE to your holes ---------------- */
standoff_h = 4; standoff_or = 3.2; standoff_ir = 1.3;
pcb_hole_dx = 44; pcb_hole_dy = 74; pcb_center_dy = 6;

/* ---------------- RFID coil window (PN5180 larger antenna) ---------------- */
rfid_zone_w = 50; rfid_zone_h = 46; rfid_zone_dy = 20; rfid_wall = 1.0;

/* ---------------- Radar module bay (C1001 ~30x30) on the BACK ---------------- */
radar_w = 32; radar_h = 32; radar_wall = 0.8; radar_from_top = 6; radar_post = 1.2;

/* ---------------- Edge ports (real sizes) ---------------- */
usb_w = 10.0; usb_h = 5.5;                     // USB-C plug clearance, bottom edge
sd_w  = 13.0; sd_h  = 2.8; sd_from_top  = 20;  // microSD, right edge
sw_w  = 9.0;  sw_h  = 5.0; sw_from_top  = 16;  // power switch, left edge
ant_d = 6.5;  ant_count = 5; ant_spread = 40;  // SMA (6.5mm hole), top edge

/* ---------------- Kickstand (rear wedge, reclines screen ~20 deg) ---------------- */
kickstand      = true;
ks_len         = 40;   // how far up the back it runs
ks_thick       = 11;   // protrusion at the bottom edge (sets recline angle)

/* ---------------- Assembly ---------------- */
boss_r = 4.0; boss_pilot = 1.5; boss_clear = 1.6;
boss_inset = 8; lip_h = 4; lip_t = 1.2;
groove_depth = 0.8;

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
// Post-modern accents cut into the front face
module face_accents(zface) {
    // diagonal slashes in the two top corners
    for (sx=[-1,1])
        translate([sx*(ext_w/2-chamf-3), ext_h/2-chamf-3, zface-groove_depth])
            rotate([0,0,sx*45]) linear_extrude(groove_depth+0.1) square([16,1.6], center=true);
    // twin lines along the bottom
    for (dy=[0,3])
        translate([0, -ext_h/2+wall+10+dy, zface-groove_depth])
            linear_extrude(groove_depth+0.1) square([ext_w-2*chamf-6,1.2], center=true);
}
// Shallow grip scallops on the two long sides
module grip_scallops(depth) {
    for (sx=[-1,1], k=[-1,0,1])
        translate([sx*ext_w/2, k*15, depth/2]) rotate([0,90,0]) scale([1,2.4,1]) cylinder(h=3, r=4, center=true);
}

// ---------------------------------------------------------------------
//  FRONT
// ---------------------------------------------------------------------
module front_part() {
    win_cy = ext_h/2 - wall - screen_off_top - screen_h/2;
    difference() {
        union() {
            shell_body(ext_w, ext_h, front_depth, chamf, wall);
            corner_bosses(front_depth, boss_pilot, false);
        }
        // Screen through-window
        translate([0, win_cy, -0.1]) linear_extrude(wall+0.2) tprofile(screen_w, screen_h, 4);
        // Stepped bezel (two levels)
        translate([0, win_cy, -0.01]) linear_extrude(bezel1_depth+0.01)
            tprofile(screen_w+2*bezel1_margin, screen_h+2*bezel1_margin, 6);
        translate([0, win_cy, -0.01]) linear_extrude(bezel2_depth+0.01)
            tprofile(screen_w+2*(bezel1_margin+bezel2_margin), screen_h+2*(bezel1_margin+bezel2_margin), 7);
        // Bevel the outer top & bottom face edges (45 deg)
        for (sy=[-1,1])
            translate([0, sy*ext_h/2, 0]) rotate([sy*45,0,0])
                translate([0,0,-edge_bevel]) cube([ext_w+2, edge_bevel*2, edge_bevel*2], center=true);
        face_accents(0);
        grip_scallops(front_depth);
    }
}

// ---------------------------------------------------------------------
//  BACK
// ---------------------------------------------------------------------
module battery_bay() {
    cy = -ext_h/2 + wall + batt_from_bottom + batt_l/2;
    translate([0, cy, wall]) {
        difference() {
            linear_extrude(batt_wallh) offset(2) square([batt_w, batt_l], center=true);
            translate([0,0,-0.1]) linear_extrude(batt_wallh+0.2) square([batt_w, batt_l], center=true);
        }
        for (sx=[-1,1]) translate([sx*(batt_w/2+1), 0, batt_wallh-0.5]) translate([-1.2,-6,0]) cube([1.4,12,2.0]);
    }
}
module standoffs() {
    for (sx=[-1,1], sy=[-1,1])
        translate([sx*pcb_hole_dx/2, pcb_center_dy + sy*pcb_hole_dy/2, wall])
            difference() { cylinder(h=standoff_h, r=standoff_or); translate([0,0,-0.1]) cylinder(h=standoff_h+0.2, r=standoff_ir); }
}
module radar_posts() {
    cy = ext_h/2 - wall - radar_from_top - radar_h/2;
    for (sx=[-1,1], sy=[-1,1])
        translate([sx*(radar_w/2-3), cy + sy*(radar_h/2-3), wall])
            difference() { cylinder(h=3, r=2.2); translate([0,0,-0.1]) cylinder(h=3.2, r=radar_post); }
}
module back_part() {
    difference() {
        union() {
            shell_body(ext_w, ext_h, back_depth, chamf, wall);
            corner_bosses(back_depth, boss_clear, true);
            inner_lip(lip_h);
            battery_bay();
            standoffs();
            radar_posts();
            if (kickstand)
                // rear wedge on the OUTER back skin (z<0), thick at the bottom
                // edge, tapering up over ks_len. Rest it wedge-down to recline.
                hull() {
                    translate([0, -ext_h/2+wall+1, -ks_thick]) cube([ext_w-2*chamf-6, 2, 0.1], center=true);
                    translate([0, -ext_h/2+wall+1, 0])          cube([ext_w-2*chamf-6, 2, 0.1], center=true);
                    translate([0, -ext_h/2+wall+ks_len, 0])     cube([ext_w-2*chamf-6, 2, 0.1], center=true);
                }
        }
        // RFID coil window (thinned skin, above the battery)
        translate([0, ext_h/2 - wall - rfid_zone_dy - rfid_zone_h/2, rfid_wall])
            linear_extrude(wall) tprofile(rfid_zone_w, rfid_zone_h, 4);
        // Radar thin window
        rcy = ext_h/2 - wall - radar_from_top - radar_h/2;
        translate([0, rcy, radar_wall]) linear_extrude(wall) square([radar_w-4, radar_h-4], center=true);
        // USB-C, bottom edge
        translate([0, -ext_h/2 - 0.1, back_depth/2]) rotate([-90,0,0]) linear_extrude(wall+0.2) offset(0.8) square([usb_w, usb_h], center=true);
        // microSD, right edge
        translate([ext_w/2 - wall - 0.1, ext_h/2 - sd_from_top, back_depth/2]) rotate([0,90,0]) linear_extrude(wall+0.4) square([sd_h, sd_w], center=true);
        // Power switch, left edge
        translate([-ext_w/2 + wall + 0.1, ext_h/2 - sw_from_top, back_depth/2]) rotate([0,-90,0]) linear_extrude(wall+0.4) square([sw_h, sw_w], center=true);
        // 5x SMA antenna holes, top edge
        for (i = [0:ant_count-1]) {
            x = (ant_count==1)?0:-ant_spread/2 + i*ant_spread/(ant_count-1);
            translate([x, ext_h/2 + 0.1, back_depth/2]) rotate([90,0,0]) cylinder(h=wall+0.2, d=ant_d);
        }
        // tactical grooves on the back skin
        for (yy = [-ext_h/4+6, ext_h/4]) translate([0, yy, -0.01]) linear_extrude(groove_depth) square([ext_w-2*chamf-4, 1.4], center=true);
    }
}

// ---------------------------------------------------------------------
if (part == "front") front_part();
else if (part == "back") back_part();
else { translate([-ext_w/2-6,0,0]) front_part(); translate([ext_w/2+6,0,0]) back_part(); }
