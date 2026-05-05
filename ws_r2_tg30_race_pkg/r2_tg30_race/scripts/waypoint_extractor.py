#!/usr/bin/env python3
"""
waypoint_extractor.py
=====================
Offline tool: reads a rosbag and extracts waypoints in the MAP frame.

BUG FIX vs original:
  The original script read raw /odom poses and labelled them with whatever
  --frame_id was passed (defaulting to "map"), producing odom-frame
  coordinates silently tagged as "map".  This version:
    1. Reads /tf from the bag to build a BufferCore.
    2. Looks up map->base_link (or map->base_footprint) at each sample time.
    3. Stores the map-frame (x, y, yaw) – drift-free and session-invariant.

Usage:
  python3 waypoint_extractor.py --bag run01.bag --mode auto --spacing_m 0.40
  python3 waypoint_extractor.py --bag run01.bag --mode manual

Requires:  rosbag, tf, geometry_msgs, nav_msgs  (standard ROS 1 + Python 3)
"""

import argparse
import math
import sys

import rosbag
import rospy
import tf.transformations as tft
import tf2_ros
import geometry_msgs.msg
import yaml
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Empty


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def yaw_from_quat(q):
    """Extract yaw from a geometry_msgs/Quaternion."""
    return tft.euler_from_quaternion([q.x, q.y, q.z, q.w])[2]


def dist2d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# ---------------------------------------------------------------------------
# TF buffer populated from bag
# ---------------------------------------------------------------------------

def build_tf_buffer(bag):
    """Return a tf2_ros.BufferCore seeded with all /tf and /tf_static from bag."""
    buf = tf2_ros.BufferCore(rospy.Duration(3600.0))
    for topic, msg, t in bag.read_messages(topics=['/tf', '/tf_static']):
        for transform in msg.transforms:
            if topic == '/tf_static':
                buf.set_transform_static(transform, "bag_reader")
            else:
                buf.set_transform(transform, "bag_reader")
    return buf


def lookup_map_pose(buf, stamp, base_frame='base_link', map_frame='map'):
    """
    Look up base_frame in map_frame at stamp.
    Falls back to base_footprint if base_link is not in the tree.
    Returns (x, y, yaw) or None on failure.
    """
    frames_to_try = [base_frame, 'base_footprint', 'base_link']
    for frame in frames_to_try:
        try:
            t = buf.lookup_transform_core(map_frame, frame, stamp)
            tr = t.transform.translation
            rot = t.transform.rotation
            yaw = yaw_from_quat(rot)
            return float(tr.x), float(tr.y), float(yaw)
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Extract map-frame waypoints from a rosbag.")
    ap.add_argument("--bag",         required=True,  help="Input bag file path")
    ap.add_argument("--odom_topic",  default="/odom", help="Odometry topic (used only for timing in manual mode)")
    ap.add_argument("--mark_topic",  default="/waypoint_mark", help="Empty topic published at each manual mark")
    ap.add_argument("--mode",        choices=["auto", "manual"], default="auto")
    ap.add_argument("--spacing_m",   type=float, default=0.40, help="Distance between auto waypoints (m)")
    ap.add_argument("--map_frame",   default="map",       help="Global frame (must be in /tf)")
    ap.add_argument("--base_frame",  default="base_link", help="Robot base frame")
    ap.add_argument("--out_yaml",    default="waypoints.yaml")
    ap.add_argument("--out_path_bag",default="race_path.bag")
    args = ap.parse_args()

    print(f"[waypoint_extractor] Opening bag: {args.bag}")
    bag = rosbag.Bag(args.bag, "r")

    print("[waypoint_extractor] Loading TF from bag ...")
    buf = build_tf_buffer(bag)

    # ------------------------------------------------------------------
    # Collect sample timestamps
    # ------------------------------------------------------------------
    sample_stamps = []

    if args.mode == "manual":
        print(f"[waypoint_extractor] Manual mode – reading marks from {args.mark_topic}")
        for topic, msg, t in bag.read_messages(topics=[args.mark_topic]):
            sample_stamps.append(t)
        if not sample_stamps:
            sys.exit(f"[waypoint_extractor] ERROR: no messages on {args.mark_topic}")
        print(f"[waypoint_extractor] Found {len(sample_stamps)} manual marks")
    else:
        print(f"[waypoint_extractor] Auto mode – spacing={args.spacing_m} m, reading from TF")
        last_xy = None
        accum = 0.0
        for topic, msg, t in bag.read_messages(topics=[args.odom_topic]):
            # Use odom timestamps as a cheap clock; pose comes from TF below
            pose = lookup_map_pose(buf, t, args.base_frame, args.map_frame)
            if pose is None:
                continue
            x, y, _ = pose
            if last_xy is None:
                sample_stamps.append(t)
                last_xy = (x, y)
                continue
            accum += dist2d((x, y), last_xy)
            last_xy = (x, y)
            if accum >= args.spacing_m:
                sample_stamps.append(t)
                accum = 0.0
        if not sample_stamps:
            sys.exit("[waypoint_extractor] ERROR: no odom messages or TF lookups all failed")
        print(f"[waypoint_extractor] Collected {len(sample_stamps)} auto samples")

    bag.close()

    # ------------------------------------------------------------------
    # Look up map-frame pose at each sample stamp
    # ------------------------------------------------------------------
    waypoints = []
    skipped = 0
    for stamp in sample_stamps:
        pose = lookup_map_pose(buf, stamp, args.base_frame, args.map_frame)
        if pose is None:
            skipped += 1
            continue
        x, y, yaw = pose
        waypoints.append({"x": x, "y": y, "yaw": yaw})

    if skipped:
        print(f"[waypoint_extractor] WARNING: {skipped} stamps had no TF – skipped")
    if not waypoints:
        sys.exit("[waypoint_extractor] ERROR: zero valid map-frame waypoints extracted")

    # ------------------------------------------------------------------
    # Write YAML  (frame_id is always map – coordinates are map-frame)
    # ------------------------------------------------------------------
    out_data = {"frame_id": args.map_frame, "waypoints": waypoints}
    with open(args.out_yaml, "w") as f:
        yaml.safe_dump(out_data, f)
    print(f"[waypoint_extractor] Wrote {len(waypoints)} waypoints → {args.out_yaml}")

    # ------------------------------------------------------------------
    # Write Path bag
    # ------------------------------------------------------------------
    path = Path()
    path.header.frame_id = args.map_frame
    path.header.stamp = rospy.Time(0)
    for i, wp in enumerate(waypoints):
        ps = PoseStamped()
        ps.header.frame_id = args.map_frame
        ps.header.seq = i
        ps.pose.position.x = wp["x"]
        ps.pose.position.y = wp["y"]
        yaw = wp["yaw"]
        ps.pose.orientation.w = math.cos(yaw / 2.0)
        ps.pose.orientation.z = math.sin(yaw / 2.0)
        path.poses.append(ps)

    out_bag = rosbag.Bag(args.out_path_bag, "w")
    out_bag.write("/race_path", path, t=rospy.Time.from_sec(0.0))
    out_bag.close()
    print(f"[waypoint_extractor] Wrote path bag → {args.out_path_bag}")


if __name__ == "__main__":
    main()
