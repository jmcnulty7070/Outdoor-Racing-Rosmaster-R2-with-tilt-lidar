#!/usr/bin/env python3
"""
record_waypoints_live.py
========================
LIVE waypoint recorder — runs ON the robot during a teleoperated drive.

Subscribes to TF (map → base_link) and records a waypoint every 0.2 m
of actual travel in the MAP frame.  Writes waypoints.yaml on shutdown
or when ROS is killed.

Usage
-----
  # Terminal 1 – bringup + AMCL must already be running so map→base TF exists
  rosrun r2_tg30_race record_waypoints_live.py \
      _spacing_m:=0.20 \
      _out_yaml:=$(rospack find r2_tg30_race)/waypoints/waypoints.yaml \
      _map_frame:=map \
      _base_frame:=base_link

  # Drive the course with the joystick.
  # When done, Ctrl-C or kill the node — waypoints.yaml is written on exit.

Parameters (all rosparams with ~ prefix)
-----------------------------------------
  ~spacing_m   (float, default 0.20) – distance between recorded waypoints
  ~out_yaml    (str)                 – output YAML path
  ~map_frame   (str, default "map")
  ~base_frame  (str, default "base_link")
  ~rate_hz     (float, default 20)   – TF polling rate

Output format (matches waypoint_extractor.py)
---------------------------------------------
  frame_id: map
  waypoints:
    - {x: 1.23, y: 4.56, yaw: 0.78}
    ...
"""

import math
import os
import signal
import sys

import rospy
import tf2_ros
import tf.transformations as tft
import yaml
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from std_msgs.msg import Bool


def yaw_from_tf(transform):
    q = transform.transform.rotation
    return tft.euler_from_quaternion([q.x, q.y, q.z, q.w])[2]


class LiveWaypointRecorder:
    def __init__(self):
        rospy.init_node("record_waypoints_live")

        self.spacing  = rospy.get_param("~spacing_m",  0.20)
        self.out_yaml = rospy.get_param("~out_yaml",
            os.path.join(os.path.dirname(__file__),
                         "../waypoints/waypoints.yaml"))
        self.out_yaml = os.path.abspath(self.out_yaml)
        self.map_frame  = rospy.get_param("~map_frame",  "map")
        self.base_frame = rospy.get_param("~base_frame", "base_link")
        rate_hz         = rospy.get_param("~rate_hz",    20.0)

        self.tf_buf = tf2_ros.Buffer(rospy.Duration(10.0))
        self.tf_lis = tf2_ros.TransformListener(self.tf_buf)

        self.waypoints = []
        self.last_xy   = None

        # Live path publisher so you can watch progress in RViz
        self.path_pub = rospy.Publisher("/recorded_path_live",
                                        Path, queue_size=1, latch=True)
        self.path_msg = Path()
        self.path_msg.header.frame_id = self.map_frame

        rospy.on_shutdown(self._save)
        signal.signal(signal.SIGINT,  self._sighandler)
        signal.signal(signal.SIGTERM, self._sighandler)

        rospy.loginfo("[record_waypoints_live] Recording to: %s", self.out_yaml)
        rospy.loginfo("[record_waypoints_live] Spacing: %.2f m  frame: %s → %s",
                      self.spacing, self.map_frame, self.base_frame)
        rospy.loginfo("[record_waypoints_live] Drive the course then Ctrl-C to save.")

        rate = rospy.Rate(rate_hz)
        while not rospy.is_shutdown():
            self._poll()
            rate.sleep()

    def _poll(self):
        try:
            t = self.tf_buf.lookup_transform(
                self.map_frame, self.base_frame,
                rospy.Time(0), rospy.Duration(0.05))
        except Exception:
            # Try base_footprint fallback
            try:
                t = self.tf_buf.lookup_transform(
                    self.map_frame, "base_footprint",
                    rospy.Time(0), rospy.Duration(0.05))
            except Exception:
                return

        x   = t.transform.translation.x
        y   = t.transform.translation.y
        yaw = yaw_from_tf(t)

        if self.last_xy is None:
            self._record(x, y, yaw)
            self.last_xy = (x, y)
            return

        dist = math.hypot(x - self.last_xy[0], y - self.last_xy[1])
        if dist >= self.spacing:
            self._record(x, y, yaw)
            self.last_xy = (x, y)

    def _record(self, x, y, yaw):
        self.waypoints.append({"x": float(x), "y": float(y), "yaw": float(yaw)})

        ps = PoseStamped()
        ps.header.frame_id = self.map_frame
        ps.header.stamp    = rospy.Time.now()
        ps.pose.position.x = x
        ps.pose.position.y = y
        ps.pose.orientation.w = math.cos(yaw / 2.0)
        ps.pose.orientation.z = math.sin(yaw / 2.0)
        self.path_msg.poses.append(ps)
        self.path_msg.header.stamp = rospy.Time.now()
        self.path_pub.publish(self.path_msg)

        if len(self.waypoints) % 10 == 0:
            rospy.loginfo("[record_waypoints_live] %d waypoints recorded",
                          len(self.waypoints))

    def _save(self):
        if not self.waypoints:
            rospy.logwarn("[record_waypoints_live] No waypoints recorded — nothing saved.")
            return
        os.makedirs(os.path.dirname(self.out_yaml), exist_ok=True)
        data = {"frame_id": self.map_frame, "waypoints": self.waypoints}
        with open(self.out_yaml, "w") as f:
            yaml.safe_dump(data, f)
        rospy.loginfo("[record_waypoints_live] Saved %d waypoints → %s",
                      len(self.waypoints), self.out_yaml)

    def _sighandler(self, *_):
        self._save()
        sys.exit(0)


if __name__ == "__main__":
    LiveWaypointRecorder()
