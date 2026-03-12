#!/usr/bin/env python3
import math
import os
import yaml

import rospy
import tf.transformations as tft
from nav_msgs.msg import Odometry, Path
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Empty


class WaypointExtractor:
    def __init__(self):
        self.sample_distance = rospy.get_param("~sample_distance", 0.40)
        self.path_topic = rospy.get_param("~path_topic", "/waypoint_path")
        self.frame_id = rospy.get_param("~frame_id", "map")
        self.yaml_file = rospy.get_param(
            "~yaml_file",
            os.path.expanduser("~/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml")
        )
        os.makedirs(os.path.dirname(self.yaml_file), exist_ok=True)

        self.path_pub = rospy.Publisher(self.path_topic, Path, queue_size=1, latch=True)
        self.path = Path()
        self.path.header.frame_id = self.frame_id
        self.last_xy = None
        self.latest_odom = None
        self.points = []

        rospy.Subscriber("/odom", Odometry, self.odom_cb, queue_size=10)
        rospy.Subscriber("/waypoint_mark", Empty, self.mark_cb, queue_size=10)
        rospy.on_shutdown(self.save_yaml)

    def yaw_from_pose(self, q):
        quat = [q.x, q.y, q.z, q.w]
        _, _, yaw = tft.euler_from_quaternion(quat)
        return yaw

    def append_pose(self, odom_msg):
        p = odom_msg.pose.pose.position
        q = odom_msg.pose.pose.orientation
        yaw = self.yaw_from_pose(q)

        pose = PoseStamped()
        pose.header = odom_msg.header
        pose.header.frame_id = self.frame_id if self.frame_id else odom_msg.header.frame_id
        pose.pose = odom_msg.pose.pose

        self.path.header.stamp = rospy.Time.now()
        self.path.header.frame_id = pose.header.frame_id
        self.path.poses.append(pose)
        self.points.append({"x": float(p.x), "y": float(p.y), "yaw": float(yaw)})
        self.path_pub.publish(self.path)
        self.save_yaml()

    def odom_cb(self, odom_msg):
        self.latest_odom = odom_msg
        p = odom_msg.pose.pose.position
        xy = (p.x, p.y)
        if self.last_xy is None:
            self.last_xy = xy
            self.append_pose(odom_msg)
            return
        dist = math.hypot(xy[0] - self.last_xy[0], xy[1] - self.last_xy[1])
        if dist >= self.sample_distance:
            self.last_xy = xy
            self.append_pose(odom_msg)

    def mark_cb(self, _msg):
        if self.latest_odom is not None:
            rospy.loginfo("Manual waypoint mark received")
            self.last_xy = (
                self.latest_odom.pose.pose.position.x,
                self.latest_odom.pose.pose.position.y,
            )
            self.append_pose(self.latest_odom)

    def save_yaml(self):
        data = {
            "frame_id": self.path.header.frame_id or self.frame_id,
            "sample_distance": float(self.sample_distance),
            "waypoints": self.points,
        }
        with open(self.yaml_file, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)


if __name__ == "__main__":
    rospy.init_node("waypoint_extractor")
    WaypointExtractor()
    rospy.loginfo("waypoint_extractor started")
    rospy.spin()
