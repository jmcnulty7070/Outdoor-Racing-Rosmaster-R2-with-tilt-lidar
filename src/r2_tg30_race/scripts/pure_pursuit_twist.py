#!/usr/bin/env python3
import math

import rospy
import tf.transformations as tft
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry, Path


class PurePursuitTwist:
    def __init__(self):
        self.lookahead = rospy.get_param("~lookahead_distance", 0.80)
        self.base_speed = rospy.get_param("~base_speed", 0.70)
        self.max_speed = rospy.get_param("~max_speed", 1.00)
        self.min_speed = rospy.get_param("~min_speed", 0.20)
        self.max_angular = rospy.get_param("~max_angular_z", 1.40)
        self.goal_tol = rospy.get_param("~goal_tolerance", 0.35)
        self.path_topic = rospy.get_param("~path_topic", "/race_path")
        self.odom_topic = rospy.get_param("~odom_topic", "/odom")
        self.cmd_topic = rospy.get_param("~cmd_topic", "/pp_cmd_vel")

        self.path = None
        self.odom = None
        self.pub = rospy.Publisher(self.cmd_topic, Twist, queue_size=1)
        rospy.Subscriber(self.path_topic, Path, self.path_cb, queue_size=1)
        rospy.Subscriber(self.odom_topic, Odometry, self.odom_cb, queue_size=10)
        self.timer = rospy.Timer(rospy.Duration(0.05), self.control_cb)

    def yaw_from_quat(self, q):
        return tft.euler_from_quaternion([q.x, q.y, q.z, q.w])[2]

    def path_cb(self, msg):
        self.path = msg

    def odom_cb(self, msg):
        self.odom = msg

    def control_cb(self, _event):
        if self.path is None or self.odom is None or len(self.path.poses) < 2:
            return

        rx = self.odom.pose.pose.position.x
        ry = self.odom.pose.pose.position.y
        ryaw = self.yaw_from_quat(self.odom.pose.pose.orientation)

        points = [(p.pose.position.x, p.pose.position.y) for p in self.path.poses]
        dists = [math.hypot(px - rx, py - ry) for px, py in points]
        nearest_idx = min(range(len(dists)), key=lambda i: dists[i])

        target_idx = nearest_idx
        while target_idx < len(points) - 1 and dists[target_idx] < self.lookahead:
            target_idx += 1

        tx, ty = points[target_idx]
        dx = tx - rx
        dy = ty - ry

        local_x = math.cos(-ryaw) * dx - math.sin(-ryaw) * dy
        local_y = math.sin(-ryaw) * dx + math.cos(-ryaw) * dy

        if target_idx == len(points) - 1 and math.hypot(dx, dy) < self.goal_tol:
            self.pub.publish(Twist())
            return

        ld = max(math.hypot(local_x, local_y), 1e-6)
        curvature = 2.0 * local_y / (ld * ld)
        angular_z = max(min(curvature * self.base_speed, self.max_angular), -self.max_angular)

        speed_scale = max(0.2, 1.0 - min(abs(angular_z) / max(self.max_angular, 1e-6), 1.0) * 0.6)
        linear_x = min(max(self.base_speed * speed_scale, self.min_speed), self.max_speed)

        cmd = Twist()
        cmd.linear.x = linear_x
        cmd.angular.z = angular_z
        self.pub.publish(cmd)


if __name__ == "__main__":
    rospy.init_node("pure_pursuit_twist")
    PurePursuitTwist()
    rospy.loginfo("pure_pursuit_twist started")
    rospy.spin()
