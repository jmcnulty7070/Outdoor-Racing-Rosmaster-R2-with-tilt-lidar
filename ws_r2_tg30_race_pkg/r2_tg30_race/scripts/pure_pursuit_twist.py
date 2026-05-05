#!/usr/bin/env python3
"""
pure_pursuit_twist.py
=====================
Pure-pursuit path follower that localises the robot in the MAP frame via TF.

BUG FIX vs original:
  The original config set  odom_topic: /odom  which caused the robot pose to
  be read from /odom (odom frame) and compared against map-frame waypoints.
  The heading error is then wrong by the accumulated map→odom rotation, causing
  the robot to drift off the recorded path over time.

  This version:
    1. Gets robot pose by looking up  map → base_link  (or base_footprint) via TF.
       This is correct because AMCL publishes map→odom and the chain closes.
    2. Falls back to /odom ONLY if the map→base TF is unavailable, and logs
       a prominent warning so the user knows they are in degraded mode.

Subscriptions:
  /race_path  (nav_msgs/Path)  – waypoints in map frame
  TF          (map → base_link via tf2_ros)

Publications:
  /cmd_vel_auto_raw  (geometry_msgs/Twist)
  /pure_pursuit/lookahead_point  (geometry_msgs/PointStamped, debug)

Parameters (loaded from pure_pursuit.yaml):
  lookahead_distance  [m]     – fixed lookahead; override with adaptive below
  base_speed          [m/s]
  max_speed           [m/s]
  min_speed           [m/s]
  max_angular_z       [rad/s]
  goal_tolerance      [m]     – within this distance of last waypoint → stop
  path_topic          [str]
  cmd_topic           [str]
  map_frame           [str]   – default "map"
  base_frame          [str]   – default "base_link"
"""

import math
import rospy
import tf2_ros
import tf.transformations as tft

from nav_msgs.msg    import Path, Odometry
from geometry_msgs.msg import Twist, PointStamped
from std_msgs.msg    import Bool


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def yaw_from_quat(q):
    return tft.euler_from_quaternion([q.x, q.y, q.z, q.w])[2]


def dist2d(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


# ---------------------------------------------------------------------------
# node
# ---------------------------------------------------------------------------

class PurePursuit:
    def __init__(self):
        rospy.init_node("pure_pursuit_twist")

        # --- params ---
        self.lookahead  = rospy.get_param("~lookahead_distance", 0.65)
        self.base_speed = rospy.get_param("~base_speed",         0.45)
        self.max_speed  = rospy.get_param("~max_speed",          0.70)
        self.min_speed  = rospy.get_param("~min_speed",          0.18)
        self.max_ang    = rospy.get_param("~max_angular_z",       1.40)
        self.goal_tol   = rospy.get_param("~goal_tolerance",      0.30)
        path_topic      = rospy.get_param("~path_topic",         "/race_path")
        cmd_topic       = rospy.get_param("~cmd_topic",          "/cmd_vel_auto_raw")
        self.map_frame  = rospy.get_param("~map_frame",          "map")
        self.base_frame = rospy.get_param("~base_frame",         "base_link")

        # FIX: TF2 buffer for map→base lookup (replaces raw /odom subscription)
        self.tf_buf = tf2_ros.Buffer(rospy.Duration(10.0))
        self.tf_lis = tf2_ros.TransformListener(self.tf_buf)

        # odom fallback (used only if TF unavailable – prints loud warning)
        self._odom_x   = 0.0
        self._odom_y   = 0.0
        self._odom_yaw = 0.0
        self._odom_ok  = False
        odom_topic = rospy.get_param("~odom_topic", "/odom")
        rospy.Subscriber(odom_topic, Odometry, self._odom_cb, queue_size=5)

        # path storage
        self.path = []          # list of (x, y) in map frame
        self.wp_idx = 0         # index of next target waypoint
        self.active = False

        # publishers
        self.cmd_pub = rospy.Publisher(cmd_topic, Twist, queue_size=5)
        self.dbg_pub = rospy.Publisher("/pure_pursuit/lookahead_point",
                                       PointStamped, queue_size=5)

        # subscribers
        rospy.Subscriber(path_topic, Path, self._path_cb, queue_size=1)
        rospy.Subscriber("/auto_enable", Bool, self._enable_cb, queue_size=5)

        rospy.Timer(rospy.Duration(0.05), self._control_cb)   # 20 Hz
        rospy.loginfo("[pure_pursuit] Initialized – waiting for path on %s", path_topic)
        rospy.spin()

    # --- callbacks ---

    def _path_cb(self, msg):
        if not msg.poses:
            rospy.logwarn("[pure_pursuit] Received empty path")
            return
        frame = msg.header.frame_id
        if frame != self.map_frame:
            rospy.logwarn("[pure_pursuit] Path frame_id='%s' != map_frame='%s' – "
                          "waypoints may be in wrong frame!", frame, self.map_frame)
        self.path   = [(p.pose.position.x, p.pose.position.y) for p in msg.poses]
        self.wp_idx = 0
        self.active = True
        rospy.loginfo("[pure_pursuit] Received path with %d waypoints (frame=%s)",
                      len(self.path), frame)

    def _enable_cb(self, msg):
        if not msg.data:
            self.active = False
            self.cmd_pub.publish(Twist())

    def _odom_cb(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self._odom_x   = p.x
        self._odom_y   = p.y
        self._odom_yaw = yaw_from_quat(q)
        self._odom_ok  = True

    # --- pose lookup (map frame, with odom fallback) ---

    def _get_map_pose(self):
        """
        Returns (x, y, yaw) in the map frame.
        PRIMARY  : TF lookup  map → base_link  (correct; uses AMCL output)
        FALLBACK : raw /odom  (drift-prone; warns loudly)
        """
        try:
            t = self.tf_buf.lookup_transform(
                    self.map_frame, self.base_frame, rospy.Time(0),
                    rospy.Duration(0.05))
            tr  = t.transform.translation
            rot = t.transform.rotation
            return float(tr.x), float(tr.y), yaw_from_quat(rot)
        except (tf2_ros.LookupException,
                tf2_ros.ConnectivityException,
                tf2_ros.ExtrapolationException):
            pass

        # Try base_footprint as alternate base frame
        try:
            t = self.tf_buf.lookup_transform(
                    self.map_frame, "base_footprint", rospy.Time(0),
                    rospy.Duration(0.05))
            tr  = t.transform.translation
            rot = t.transform.rotation
            return float(tr.x), float(tr.y), yaw_from_quat(rot)
        except Exception:
            pass

        # Degraded fallback
        if self._odom_ok:
            rospy.logwarn_throttle(5.0,
                "[pure_pursuit] DEGRADED: map→base TF unavailable – using raw /odom. "
                "Ensure AMCL/Cartographer is running and has converged.")
            return self._odom_x, self._odom_y, self._odom_yaw

        return None

    # --- control loop ---

    def _control_cb(self, _event):
        if not self.active or not self.path:
            return

        pose = self._get_map_pose()
        if pose is None:
            rospy.logwarn_throttle(2.0, "[pure_pursuit] No pose available – skipping")
            return

        rx, ry, ryaw = pose

        # --- advance waypoint index past points we've already reached ---
        while self.wp_idx < len(self.path) - 1:
            wx, wy = self.path[self.wp_idx]
            if dist2d(rx, ry, wx, wy) < self.lookahead:
                self.wp_idx += 1
            else:
                break

        # --- goal reached? ---
        gx, gy = self.path[-1]
        if dist2d(rx, ry, gx, gy) < self.goal_tol:
            rospy.loginfo("[pure_pursuit] Goal reached – stopping")
            self.active = False
            self.cmd_pub.publish(Twist())
            return

        # --- find lookahead point on the remaining path ---
        lx, ly = self._find_lookahead(rx, ry, ryaw)

        # --- publish debug marker ---
        pt = PointStamped()
        pt.header.frame_id = self.map_frame
        pt.header.stamp    = rospy.Time.now()
        pt.point.x = lx
        pt.point.y = ly
        self.dbg_pub.publish(pt)

        # --- pure-pursuit geometry ---
        dx = lx - rx
        dy = ly - ry
        # angle to lookahead point in world frame, then relative to robot heading
        alpha = math.atan2(dy, dx) - ryaw
        alpha = math.atan2(math.sin(alpha), math.cos(alpha))   # wrap to [-π, π]

        L = max(self.lookahead, dist2d(rx, ry, lx, ly))
        if L < 1e-3:
            return

        # curvature κ = 2 sin(α) / L  →  angular_z = v * κ
        curvature = 2.0 * math.sin(alpha) / L
        speed = self.base_speed
        # slow down on tight curves
        turn_ratio = abs(alpha) / (math.pi / 2.0)
        speed = max(self.min_speed, speed * (1.0 - 0.5 * min(1.0, turn_ratio)))
        speed = min(speed, self.max_speed)

        angular = max(-self.max_ang, min(self.max_ang, speed * curvature))

        cmd = Twist()
        cmd.linear.x  = speed
        cmd.angular.z = angular
        self.cmd_pub.publish(cmd)

    def _find_lookahead(self, rx, ry, ryaw):
        """
        Walk forward along the stored path from wp_idx and return the first
        point at distance >= lookahead_distance.  Falls back to the last point.
        """
        for i in range(self.wp_idx, len(self.path)):
            wx, wy = self.path[i]
            if dist2d(rx, ry, wx, wy) >= self.lookahead:
                return wx, wy
        # fallback: interpolate just beyond last waypoint in current heading
        lx = rx + self.lookahead * math.cos(ryaw)
        ly = ry + self.lookahead * math.sin(ryaw)
        return lx, ly


if __name__ == "__main__":
    PurePursuit()
