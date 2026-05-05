#!/usr/bin/env python3
"""
follow_the_gap.py
=================
Reactive obstacle-avoidance using Follow The Gap (FTG).

Input scan:  /scan_obstacles
  This is the PointCloud2 → LaserScan derived scan with height slice
  min_height=0.025 m / max_height=0.28 m in base_footprint frame.
  Curb faces, grass edges, and low obstacles are already present in this scan.
  FTG therefore treats sidewalk edges and grass borders as obstacles
  automatically – no extra processing is needed.

Output:  /cmd_vel_ftg_raw  (geometry_msgs/Twist)

Algorithm:
  1. Cap ranges at danger_distance; NaN/Inf → danger_distance (treat as obstacle).
  2. Inflate each obstacle point by bubble_radius_idx beams (robot half-width proxy).
  3. Find the widest contiguous gap in the front_angle_deg cone.
  4. If no navigable gap exists → stop.
  5. Steer toward the centre of the best gap, speed proportional to gap width.
"""

import math
import numpy as np
import rospy
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist


class FollowTheGap:
    def __init__(self):
        rospy.init_node("follow_the_gap")

        # --- params ---
        scan_topic          = rospy.get_param("~scan_topic",        "/scan_obstacles")
        cmd_topic           = rospy.get_param("~cmd_topic",         "/cmd_vel_ftg_raw")
        self.danger_dist    = rospy.get_param("~danger_distance",    1.10)
        self.stop_dist      = rospy.get_param("~stop_distance",      0.40)
        self.front_angle    = math.radians(rospy.get_param("~front_angle_deg", 120.0))
        self.bubble_r       = int(rospy.get_param("~bubble_radius_idx", 14))
        self.gap_threshold  = rospy.get_param("~gap_threshold",      0.70)
        self.max_speed      = rospy.get_param("~max_speed",          0.40)
        self.min_speed      = rospy.get_param("~min_speed",          0.10)
        self.max_ang        = rospy.get_param("~max_angular_z",      1.60)

        self.pub = rospy.Publisher(cmd_topic, Twist, queue_size=5)
        rospy.Subscriber(scan_topic, LaserScan, self._scan_cb, queue_size=1)

        rospy.loginfo("[follow_the_gap] Listening on %s → publishing to %s", scan_topic, cmd_topic)
        rospy.loginfo("[follow_the_gap] Curb/grass edges are included in /scan_obstacles "
                      "via height slice (min=0.025m, max=0.28m) – no extra config needed.")
        rospy.spin()

    def _scan_cb(self, msg: LaserScan):
        ranges = np.array(msg.ranges, dtype=np.float32)
        n = len(ranges)

        # --- replace NaN/Inf with danger_distance (treat as obstacle at max react range) ---
        bad = ~np.isfinite(ranges)
        ranges[bad] = self.danger_dist

        # --- hard stop: anything closer than stop_distance in the full scan ---
        if np.nanmin(ranges) < self.stop_dist:
            self.pub.publish(Twist())
            return

        # --- cap at danger_distance for gap finding ---
        ranges = np.clip(ranges, 0.0, self.danger_dist)

        # --- identify front-cone indices ---
        angle_inc = msg.angle_increment
        angle_min = msg.angle_min
        half_cone = self.front_angle / 2.0

        # angles of each beam relative to robot forward
        angles = angle_min + np.arange(n) * angle_inc
        front_mask = np.abs(angles) <= half_cone
        front_idx  = np.where(front_mask)[0]

        if len(front_idx) == 0:
            self.pub.publish(Twist())
            return

        # --- bubble inflation: zero out beams near each obstacle ---
        proc = ranges.copy()
        obstacle_idx = np.where(proc < self.danger_dist)[0]
        for oi in obstacle_idx:
            lo = max(0, oi - self.bubble_r)
            hi = min(n - 1, oi + self.bubble_r)
            proc[lo:hi+1] = 0.0

        # --- find gaps in front cone ---
        front_proc = proc[front_idx]
        # gap = contiguous run where range > gap_threshold
        in_gap   = front_proc > self.gap_threshold
        best_gap = None
        best_len = 0
        start     = None

        for i, g in enumerate(in_gap):
            if g and start is None:
                start = i
            elif (not g or i == len(in_gap) - 1) and start is not None:
                end = i if not g else i + 1
                length = end - start
                if length > best_len:
                    best_len = length
                    best_gap = (start, end)
                start = None

        if best_gap is None:
            # No navigable gap – stop
            rospy.logwarn_throttle(1.0, "[follow_the_gap] No gap found – stopping")
            self.pub.publish(Twist())
            return

        # --- steer to gap centre ---
        gap_centre_local = (best_gap[0] + best_gap[1]) // 2
        gap_beam_idx     = front_idx[gap_centre_local]
        gap_angle        = angles[gap_beam_idx]           # radians, robot-relative

        # angular velocity proportional to heading error
        angular_z = max(-self.max_ang, min(self.max_ang,
                         gap_angle * (self.max_ang / half_cone)))

        # speed: full speed when gap is wide and clear, slow on narrow/close gaps
        gap_fraction = min(1.0, best_len / max(1, len(front_idx)))
        min_front    = np.min(front_proc[best_gap[0]:best_gap[1]])
        dist_factor  = min(1.0, min_front / self.danger_dist)
        speed = self.min_speed + (self.max_speed - self.min_speed) * gap_fraction * dist_factor

        cmd = Twist()
        cmd.linear.x  = float(speed)
        cmd.angular.z = float(angular_z)
        self.pub.publish(cmd)


if __name__ == "__main__":
    FollowTheGap()
