#!/usr/bin/env python3
"""
waypoint_map_builder.py
=======================
Reads waypoints.yaml and publishes:
  /race_path       (nav_msgs/Path)              – for pure_pursuit
  /race_waypoints  (visualization_msgs/MarkerArray) – for RViz

The YAML frame_id is used as the Path header frame_id (should be "map").
A mismatch warning is logged if it differs from the ~map_frame param.
"""
import math
import rospy
import yaml

from nav_msgs.msg              import Path
from geometry_msgs.msg         import PoseStamped
from visualization_msgs.msg    import MarkerArray, Marker
from std_msgs.msg              import ColorRGBA


class WaypointMapBuilder:
    def __init__(self):
        rospy.init_node("waypoint_map_builder")

        yaml_file   = rospy.get_param("~yaml_file",      "waypoints.yaml")
        path_topic  = rospy.get_param("~path_topic",     "/race_path")
        marker_topic= rospy.get_param("~marker_topic",   "/race_waypoints")
        self.map_frame = rospy.get_param("~map_frame",   "map")
        rate_hz     = rospy.get_param("~publish_rate_hz", 1.0)

        self.path_pub   = rospy.Publisher(path_topic,   Path,        queue_size=1, latch=True)
        self.marker_pub = rospy.Publisher(marker_topic, MarkerArray, queue_size=1, latch=True)

        self.path, self.markers = self._load(yaml_file)
        self.path_pub.publish(self.path)
        self.marker_pub.publish(self.markers)

        rospy.loginfo("[waypoint_map_builder] Published %d waypoints on %s (frame=%s)",
                      len(self.path.poses), path_topic, self.path.header.frame_id)

        rospy.Timer(rospy.Duration(1.0 / rate_hz), self._timer_cb)
        rospy.spin()

    def _load(self, yaml_file):
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)

        frame = data.get("frame_id", self.map_frame)
        if frame != self.map_frame:
            rospy.logwarn("[waypoint_map_builder] YAML frame_id='%s' != map_frame='%s'. "
                          "Waypoints may not align with the map!", frame, self.map_frame)

        wps = data.get("waypoints", [])
        path = Path()
        path.header.frame_id = frame
        path.header.stamp    = rospy.Time.now()

        markers = MarkerArray()

        for i, wp in enumerate(wps):
            ps = PoseStamped()
            ps.header.frame_id = frame
            ps.header.stamp    = rospy.Time.now()
            ps.pose.position.x = wp["x"]
            ps.pose.position.y = wp["y"]
            yaw = wp.get("yaw", 0.0)
            ps.pose.orientation.w = math.cos(yaw / 2.0)
            ps.pose.orientation.z = math.sin(yaw / 2.0)
            path.poses.append(ps)

            m = Marker()
            m.header.frame_id = frame
            m.ns = "waypoints"
            m.id = i
            m.type = Marker.SPHERE
            m.action = Marker.ADD
            m.pose = ps.pose
            m.scale.x = m.scale.y = m.scale.z = 0.12
            m.color = ColorRGBA(0.0, 1.0, 0.4, 0.85)
            markers.markers.append(m)

        return path, markers

    def _timer_cb(self, _):
        self.path.header.stamp = rospy.Time.now()
        self.path_pub.publish(self.path)
        self.marker_pub.publish(self.markers)


if __name__ == "__main__":
    WaypointMapBuilder()
