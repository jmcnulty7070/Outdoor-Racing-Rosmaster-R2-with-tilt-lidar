#!/usr/bin/env python3
import os
import yaml

import rospy
import tf.transformations as tft
from geometry_msgs.msg import PoseStamped, Quaternion
from nav_msgs.msg import Path


class WaypointMapBuilder:
    def __init__(self):
        self.yaml_file = rospy.get_param(
            "~yaml_file",
            os.path.expanduser("~/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml")
        )
        self.path_topic = rospy.get_param("~path_topic", "/race_path")
        self.publish_rate = rospy.get_param("~publish_rate", 1.0)
        self.pub = rospy.Publisher(self.path_topic, Path, queue_size=1, latch=True)
        self.path = self.load_path()
        self.timer = rospy.Timer(rospy.Duration(1.0 / max(self.publish_rate, 0.1)), self.timer_cb)

    def load_path(self):
        path = Path()
        if not os.path.exists(self.yaml_file):
            rospy.logwarn("Waypoint YAML not found: %s", self.yaml_file)
            path.header.frame_id = "map"
            return path

        with open(self.yaml_file, "r") as f:
            data = yaml.safe_load(f) or {}

        frame_id = data.get("frame_id", "map")
        path.header.frame_id = frame_id
        for wp in data.get("waypoints", []):
            ps = PoseStamped()
            ps.header.frame_id = frame_id
            ps.pose.position.x = float(wp.get("x", 0.0))
            ps.pose.position.y = float(wp.get("y", 0.0))
            yaw = float(wp.get("yaw", 0.0))
            q = tft.quaternion_from_euler(0.0, 0.0, yaw)
            ps.pose.orientation = Quaternion(*q)
            path.poses.append(ps)

        rospy.loginfo("Loaded %d waypoints from %s", len(path.poses), self.yaml_file)
        return path

    def timer_cb(self, _event):
        self.path.header.stamp = rospy.Time.now()
        for pose in self.path.poses:
            pose.header.stamp = self.path.header.stamp
        self.pub.publish(self.path)


if __name__ == "__main__":
    rospy.init_node("waypoint_map_builder")
    WaypointMapBuilder()
    rospy.loginfo("waypoint_map_builder started")
    rospy.spin()
