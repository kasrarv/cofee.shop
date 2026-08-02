// =====================================================================
//  ESP32-DIV V2 "TACTICAL" — compact, button-less, snap/screw enclosure
//  ---------------------------------------------------------------------
//  Design goals (per build brief):
//   * Touch-only (NO button holes) — cleaner, more tactical face
//   * Angular / faceted "tactical" aesthetic (chamfered edges + panel lines)
//   * Pre-defined bays so parts just drop in, no glue:
//       - Battery bay for a 60 x 80 mm ~4000 mAh LiPo (retention clips)
//       - PCB standoffs (Main + Shield stack) with pilot holes
//       - Add-on module pocket (PN5180 RFID reader, larger antenna)
//       - Radar module pocket (DFRobot C4001 26x30 / C1001) + thin window
//   * As compact as the 2.8" display + 60x80 battery allow
//
//  UNITS: mm.  Everything is parametric — MEASURE your boards and tune the
//  standoff / pocket positions before the final print. Print a draft first.
//
//  Export:
//    openscad -D 'part="front"' -o tactical_front.stl enclosure_tactical.scad
//    openscad -D 'part="back"'  -o tactical_back.stl  enclosure_tactical.scad
// =====================================================================

part = "both";     // "front" | "back" | "both"
$fn = 48;

/* ---------------- Outer body ---------------- */
ext_w       = 78;      // external width
ext_h       = 150;     // external height
wall        = 2.4;     // wall thickness
chamf       = 9;       // corner chamfer (bigger = more angular / tactical)
total_depth = 30;
front_depth = 10;      // screen-side half
back_depth  = total_depth - front_depth;

/* ---------------- Screen (2.8" ILI9341 active 43.2 x 57.6) ---------------- */
screen_w       = 46;   // window (slightly larger than active area)
screen_h       = 61;
screen_off_top = 10;   // gap from inner top to window top
bezel_recess   = 1.0;  // depth of the recessed bezel frame
bezel_margin   = 3.0;  // frame width around the window

/* ---------------- Battery bay: 60 x 80 mm LiPo ---------------- */
batt_w    = 61;        // 60 mm + clearance
batt_l    = 81;        // 80 mm + clearance
batt_t    = 11;        // cell thickness (typical 4000mAh pouch ~9-11 mm)
batt_from_bottom = 8;  // gap from inner bottom edge to bay
batt_wallh = batt_t + 1;

/* ---------------- PCB standoffs (Main board) ---------------- */
// Default = 4 posts on a 44 x 80 rectangle. SET THESE to your PCB holes.
standoff_h    = 4;     // height off the back inner floor
standoff_or   = 3.2;   // outer radius
standoff_ir   = 1.3;   // pilot-hole radius (M2.5 self-tap)
pcb_hole_dx   = 44;    // horizontal hole spacing
pcb_hole_dy   = 80;    // vertical hole spacing
pcb_center_dy = 20;    // PCB centre offset from box centre (toward top)

/* ---------------- Add-on module pockets ---------------- */
// PN5180 RFID reader board (~ larger antenna). Thin back window over coil.
rfid_zone_w  = 52;  rfid_zone_h = 52;  rfid_zone_dy = 30;  rfid_wall = 1.0;

// Radar module (C4001 = 26x30, C1001 similar). Pocket + thin front window.
radar_w = 32;  radar_h = 34;  radar_wall = 0.8;  radar_from_top = 6;
radar_post = 1.2;    // corner post pilot radius

/* ---------------- Edge ports ---------------- */
usb_w = 11; usb_h = 7;                     // USB-C, bottom edge
sd_w  = 13; sd_h  = 3;  sd_from_top  = 22; // microSD, right edge
sw_w  = 9;  sw_h  = 5;  sw_from_top  = 18; // power switch, left edge
ant_d = 7;  ant_count = 3; ant_spread = 44;// SMA antenna holes, top edge

/* ---------------- Assembly ---------------- */
boss_r = 4.0; boss_pilot = 1.5; boss_clear = 1.6;
boss_inset = 8; lip_h = 4; lip_t = 1.2;
groove_depth = 0.8;   // decorative tactical panel-line depth

// ---------------------------------------------------------------------
//  2D tactical profile: rectangle with 45-degree chamfered corners
// ---------------------------------------------------------------------
module tprofile(w, h, c) {
    polygon([
        [-w/2+c,-h/2],[ w/2-c,-h/2],[ w/2,-h/2+c],[ w/2, h/2-c],
        [ w/2-c, h/2],[-w/2+c, h/2],[-w/2, h/2-c],[-w/2,-h/2+c]
    ]);
}

module shell_body(w, h, depth, c, wthk) {
    difference() {
        linear_extrude(depth) tprofile(w, h, c);
        translate([0,0,wthk])
            linear_extrude(depth) tprofile(w-2*wthk, h-2*wthk, c-wthk);
    }
}

module corner_bosses(depth, hole_r, countersink=false) {
    for (sx=[-1,1], sy=[-1,1])
        translate([sx*(ext_w/2-boss_inset), sy*(ext_h/2-boss_inset), 0]) {
            difference() {
                cylinder(h=depth, r=boss_r);
                translate([0,0,-0.1]) cylinder(h=depth+0.2, r=hole_r);
                if (countersink)
                    translate([0,0,depth-2.2]) cylinder(h=2.4, r1=hole_r, r2=hole_r+1.8);
            }
        }
}

module inner_lip(depth) {
    linear_extrude(depth)
        difference() {
            tprofile(ext_w-2*wall+0.3, ext_h-2*wall+0.3, chamf-wall);
            tprofile(ext_w-2*wall-2*lip_t, ext_h-2*wall-2*lip_t, chamf-wall-lip_t);
        }
}

// ---------------------------------------------------------------------
//  FRONT — tactical bezel face, touch only (no buttons)
// ---------------------------------------------------------------------
module front_part() {
    win_cy = ext_h/2 - wall - screen_off_top - screen_h/2;
    difference() {
        union() {
            shell_body(ext_w, ext_h, front_depth, chamf, wall);
            corner_bosses(front_depth, boss_pilot, false);
        }
        // Screen through-window
        translate([0, win_cy, -0.1])
            linear_extrude(wall+0.2) tprofile(screen_w, screen_h, 4);
        // Recessed bezel frame (tactical "lens" surround)
        translate([0, win_cy, -0.01])
            linear_extrude(bezel_recess+0.01)
                tprofile(screen_w+2*bezel_margin, screen_h+2*bezel_margin, 6);
        // Decorative tactical panel lines (top & bottom of face)
        for (yy = [ext_h/2-wall-4, -ext_h/2+wall+8])
            translate([0, yy, -0.01])
                linear_extrude(groove_depth)
                    square([ext_w-2*chamf-6, 1.6], center=true);
    }
}

// ---------------------------------------------------------------------
//  BACK — battery bay + standoffs + module pockets + ports
// ---------------------------------------------------------------------
module battery_bay() {
    cy = -ext_h/2 + wall + batt_from_bottom + batt_l/2;
    translate([0, cy, wall]) {
        // Perimeter rails (open top so cell drops in)
        difference() {
            linear_extrude(batt_wallh) offset(2) square([batt_w, batt_l], center=true);
            translate([0,0,-0.1]) linear_extrude(batt_wallh+0.2) square([batt_w, batt_l], center=true);
        }
        // Two retention clips on the long sides (snap over the cell)
        for (sx=[-1,1])
            translate([sx*(batt_w/2+1), 0, batt_wallh-0.5])
                rotate([0,0, sx>0?0:180])
                    translate([-1.2,-6,0]) cube([1.4,12,2.0]);
    }
}

module standoffs() {
    for (sx=[-1,1], sy=[-1,1])
        translate([sx*pcb_hole_dx/2, pcb_center_dy + sy*pcb_hole_dy/2, wall])
            difference() {
                cylinder(h=standoff_h, r=standoff_or);
                translate([0,0,-0.1]) cylinder(h=standoff_h+0.2, r=standoff_ir);
            }
}

module radar_pocket() {
    cy = ext_h/2 - wall - radar_from_top - radar_h/2;
    // corner posts to screw the radar board (no glue)
    for (sx=[-1,1], sy=[-1,1])
        translate([sx*(radar_w/2-3), cy + sy*(radar_h/2-3), wall])
            difference() {
                cylinder(h=3, r=2.2);
                translate([0,0,-0.1]) cylinder(h=3.2, r=radar_post);
            }
}

module back_part() {
    difference() {
        union() {
            shell_body(ext_w, ext_h, back_depth, chamf, wall);
            corner_bosses(back_depth, boss_clear, true);
            inner_lip(lip_h);
            battery_bay();
            standoffs();
            radar_pocket();
        }
        // RFID coil window (thinned back panel, above the battery)
        translate([0, ext_h/2 - wall - rfid_zone_dy - rfid_zone_h/2, rfid_wall])
            linear_extrude(wall) tprofile(rfid_zone_w, rfid_zone_h, 4);

        // Radar thin window (so 24/60 GHz sees out the back-top)
        rcy = ext_h/2 - wall - radar_from_top - radar_h/2;
        translate([0, rcy, radar_wall])
            linear_extrude(wall) square([radar_w-4, radar_h-4], center=true);

        // USB-C, bottom edge
        translate([0, -ext_h/2 - 0.1, back_depth/2])
            rotate([-90,0,0]) linear_extrude(wall+0.2) offset(1) square([usb_w, usb_h], center=true);
        // microSD, right edge
        translate([ext_w/2 - wall - 0.1, ext_h/2 - sd_from_top, back_depth/2])
            rotate([0,90,0]) linear_extrude(wall+0.4) square([sd_h, sd_w], center=true);
        // Power switch, left edge
        translate([-ext_w/2 + wall + 0.1, ext_h/2 - sw_from_top, back_depth/2])
            rotate([0,-90,0]) linear_extrude(wall+0.4) square([sw_h, sw_w], center=true);
        // SMA antenna holes, top edge
        for (i = [0:ant_count-1]) {
            x = (ant_count==1)?0:-ant_spread/2 + i*ant_spread/(ant_count-1);
            translate([x, ext_h/2 + 0.1, back_depth/2]) rotate([90,0,0]) cylinder(h=wall+0.2, d=ant_d);
        }
        // Decorative tactical grooves on the back skin (grip / look)
        for (yy = [-ext_h/4, 0, ext_h/4])
            translate([0, yy, -0.01]) linear_extrude(groove_depth)
                square([ext_w-2*chamf-4, 1.4], center=true);
    }
}

// ---------------------------------------------------------------------
if (part == "front") front_part();
else if (part == "back") back_part();
else {
    translate([-ext_w/2-6, 0, 0]) front_part();
    translate([ ext_w/2+6, 0, 0]) back_part();
}
