#!/usr/bin/env python3
"""
close_loop.py
=============
Post-processes a waypoints.yaml to close the loop for circuit racing.

What it does
------------
1. Reads the waypoints.yaml produced by record_waypoints_live.py or
   waypoint_extractor.py (must be in the MAP frame).
2. Checks whether the last waypoint is close enough to the first to
   form a proper loop (threshold = --close_thresh metres, default 1.0 m).
3. Inserts 'bridge' waypoints interpolated from the last recorded point
   back to the first, spaced at --spacing_m (default 0.20 m).
4. Optionally smooths the full path with a simple moving-average window
   to remove jitter artefacts at the closure seam.
5. Writes the result back to --out_yaml (default: overwrites input).

Usage
-----
  python3 close_loop.py \
      --in_yaml  ~/ws/src/r2_tg30_race/waypoints/waypoints.yaml \
      --out_yaml ~/ws/src/r2_tg30_race/waypoints/waypoints_closed.yaml \
      --spacing_m 0.20 \
      --close_thresh 2.0 \
      --smooth_window 5

  # Then update racing_stack.launch or pure_pursuit.yaml to point at
  # the new waypoints_closed.yaml.

Flags
-----
  --in_yaml        Input waypoints YAML (frame_id must be "map")
  --out_yaml       Output path (defaults to --in_yaml, i.e. overwrites)
  --spacing_m      Spacing of bridge waypoints (default 0.20 m)
  --close_thresh   If last→first distance > this, abort with error (default 3.0 m)
  --smooth_window  Moving-average window size in waypoints (0 = off, default 0)
  --force          Close even if last→first > close_thresh (adds warning)
"""

import argparse
import math
import sys

import yaml


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------

def dist2d(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def lerp_yaw(y0, y1, t):
    """Linearly interpolate between two angles (handles wrap-around)."""
    diff = math.atan2(math.sin(y1 - y0), math.cos(y1 - y0))
    return y0 + t * diff


def interpolate_bridge(wp_start, wp_end, spacing_m):
    """
    Return a list of waypoints from wp_start to wp_end (exclusive of both
    endpoints) spaced at spacing_m apart.
    """
    d = dist2d(wp_start, wp_end)
    if d < spacing_m:
        return []
    n_steps = max(1, int(math.floor(d / spacing_m)))
    bridge = []
    for i in range(1, n_steps):
        t = i / n_steps
        bx  = wp_start["x"]   + t * (wp_end["x"]   - wp_start["x"])
        by  = wp_start["y"]   + t * (wp_end["y"]   - wp_start["y"])
        byaw = lerp_yaw(wp_start["yaw"], wp_end["yaw"], t)
        bridge.append({"x": float(bx), "y": float(by), "yaw": float(byaw)})
    return bridge


def smooth_waypoints(wps, window):
    """Apply a simple symmetric moving-average over x and y (yaw is re-derived)."""
    if window < 2:
        return wps
    n = len(wps)
    smoothed = []
    half = window // 2
    for i in range(n):
        xs, ys = [], []
        for j in range(-half, half + 1):
            idx = (i + j) % n          # wrap around (loop is closed)
            xs.append(wps[idx]["x"])
            ys.append(wps[idx]["y"])
        sx = sum(xs) / len(xs)
        sy = sum(ys) / len(ys)
        # re-derive yaw from smoothed tangent direction
        next_idx = (i + 1) % n
        nx = sum([wps[(i + j + 1) % n]["x"] for j in range(-half, half + 1)]) / window
        ny = sum([wps[(i + j + 1) % n]["y"] for j in range(-half, half + 1)]) / window
        syaw = math.atan2(ny - sy, nx - sx)
        smoothed.append({"x": float(sx), "y": float(sy), "yaw": float(syaw)})
    return smoothed


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Close the waypoint loop for circuit racing.")
    ap.add_argument("--in_yaml",       required=True,   help="Input waypoints YAML")
    ap.add_argument("--out_yaml",      default=None,    help="Output YAML (default: overwrite input)")
    ap.add_argument("--spacing_m",     type=float, default=0.20, help="Bridge waypoint spacing (m)")
    ap.add_argument("--close_thresh",  type=float, default=3.0,
                    help="Abort if last→first gap > this (m). Use --force to override.")
    ap.add_argument("--smooth_window", type=int,   default=0,  help="Moving-average window (0=off)")
    ap.add_argument("--force",         action="store_true",
                    help="Close the loop even if gap > close_thresh")
    args = ap.parse_args()

    out_yaml = args.out_yaml or args.in_yaml

    # --- load ---
    with open(args.in_yaml) as f:
        data = yaml.safe_load(f)

    frame_id = data.get("frame_id", "map")
    wps = data.get("waypoints", [])

    if len(wps) < 2:
        sys.exit("[close_loop] ERROR: need at least 2 waypoints.")

    if frame_id != "map":
        print(f"[close_loop] WARNING: frame_id is '{frame_id}', expected 'map'. "
              f"Proceeding anyway.")

    first = wps[0]
    last  = wps[-1]
    gap   = dist2d(last, first)

    print(f"[close_loop] {len(wps)} waypoints loaded.")
    print(f"[close_loop] First: ({first['x']:.3f}, {first['y']:.3f})")
    print(f"[close_loop] Last:  ({last['x']:.3f},  {last['y']:.3f})")
    print(f"[close_loop] Gap (last→first): {gap:.3f} m")

    if gap > args.close_thresh:
        if not args.force:
            sys.exit(
                f"[close_loop] ERROR: gap {gap:.2f} m > close_thresh {args.close_thresh:.2f} m.\n"
                f"  Drive the course closer to the start before stopping, or\n"
                f"  use --force to close anyway (may produce a sharp corner).\n"
                f"  Tip: --close_thresh {gap + 0.5:.1f}  would accept this gap."
            )
        print(f"[close_loop] WARNING: gap {gap:.2f} m > threshold – closing anyway (--force).")

    # --- build bridge ---
    bridge = interpolate_bridge(last, first, args.spacing_m)
    print(f"[close_loop] Inserting {len(bridge)} bridge waypoints.")

    closed = wps + bridge

    # --- smooth ---
    if args.smooth_window > 1:
        print(f"[close_loop] Smoothing with window={args.smooth_window}.")
        closed = smooth_waypoints(closed, args.smooth_window)

    # --- save ---
    out_data = {"frame_id": frame_id, "waypoints": closed}
    with open(out_yaml, "w") as f:
        yaml.safe_dump(out_data, f)

    print(f"[close_loop] Wrote {len(closed)} waypoints → {out_yaml}")
    print(f"[close_loop] Loop closure complete. "
          f"Update your launch file to use this YAML, then run the racing stack.")


if __name__ == "__main__":
    main()
