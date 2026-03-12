#!/usr/bin/env python3
import math

import rospy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool


class SteeringModifier:
    def __init__(self):
        self.pp_topic = rospy.get_param("~pp_topic", "/cmd_vel_auto")
        self.ftg_topic = rospy.get_param("~ftg_topic", "/cmd_vel_ftg_raw")
        self.scan_topic = rospy.get_param("~scan_topic", "/scan_obstacles")
        self.enable_topic = rospy.get_param("~enable_topic", "/auto_enable")
        self.cmd_topic = rospy.get_param("~cmd_topic", "/cmd_vel_safety")

        self.danger_distance = rospy.get_param("~danger_distance", 0.85)
        self.stop_distance = rospy.get_param("~stop_distance", 0.35)
        self.blend_distance = rospy.get_param("~blend_distance", 1.20)
        self.clear_scale = rospy.get_param("~clear_path_speed_scale", 1.0)
        self.danger_scale = rospy.get_param("~danger_speed_scale", 0.40)
        self.max_linear = rospy.get_param("~max_linear_x", 0.80)
        self.max_angular = rospy.get_param("~max_angular_z", 1.60)
        self.publish_hz = rospy.get_param("~publish_hz", 20.0)
        self.front_fov_deg = rospy.get_param("~front_fov_deg", 80.0)
        self.publish_zero_once_on_disable = rospy.get_param("~publish_zero_once_on_disable", True)

        self.pp_cmd = Twist()
        self.ftg_cmd = Twist()
        self.min_front = 999.0
        self.enabled = False
        self.last_enabled = False

        self.pub = rospy.Publisher(self.cmd_topic, Twist, queue_size=1)
        rospy.Subscriber(self.pp_topic, Twist, self.pp_cb, queue_size=1)
        rospy.Subscriber(self.ftg_topic, Twist, self.ftg_cb, queue_size=1)
        rospy.Subscriber(self.scan_topic, LaserScan, self.scan_cb, queue_size=1)
        rospy.Subscriber(self.enable_topic, Bool, self.enable_cb, queue_size=1)
        self.timer = rospy.Timer(rospy.Duration(1.0 / max(self.publish_hz, 1.0)), self.control_cb)

    def pp_cb(self, msg):
        self.pp_cmd = msg

    def ftg_cb(self, msg):
        self.ftg_cmd = msg

    def enable_cb(self, msg):
        self.enabled = bool(msg.data)

    def scan_cb(self, msg):
        if not msg.ranges:
            return
        half = math.radians(self.front_fov_deg / 2.0)
        vals = []
        for i, r in enumerate(msg.ranges):
            ang = msg.angle_min + i * msg.angle_increment
            if -half <= ang <= half and math.isfinite(r):
                vals.append(r)
        if vals:
            self.min_front = min(vals)

    @staticmethod
    def clamp(x, lo, hi):
        return max(lo, min(hi, x))

    def control_cb(self, _event):
        if not self.enabled:
            if self.publish_zero_once_on_disable and self.last_enabled:
                self.pub.publish(Twist())
            self.last_enabled = False
            return

        cmd = Twist()

        if self.min_front <= self.stop_distance:
            cmd.linear.x = 0.0
            cmd.angular.z = self.clamp(self.ftg_cmd.angular.z, -self.max_angular, self.max_angular)
            self.pub.publish(cmd)
            self.last_enabled = True
            return

        if self.min_front >= self.blend_distance:
            blend = 0.0
        elif self.min_front <= self.danger_distance:
            blend = 1.0
        else:
            denom = max(self.blend_distance - self.danger_distance, 1e-6)
            blend = 1.0 - ((self.min_front - self.danger_distance) / denom)

        cmd.linear.x = (1.0 - blend) * self.pp_cmd.linear.x * self.clear_scale + blend * self.ftg_cmd.linear.x * self.danger_scale
        cmd.angular.z = (1.0 - blend) * self.pp_cmd.angular.z + blend * self.ftg_cmd.angular.z

        cmd.linear.x = self.clamp(cmd.linear.x, 0.0, self.max_linear)
        cmd.angular.z = self.clamp(cmd.angular.z, -self.max_angular, self.max_angular)
        self.pub.publish(cmd)
        self.last_enabled = True


if __name__ == "__main__":
    rospy.init_node("steering_modifier")
    SteeringModifier()
    rospy.loginfo("steering_modifier started")
    rospy.spin()
