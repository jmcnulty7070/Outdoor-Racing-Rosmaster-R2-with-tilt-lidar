#!/usr/bin/env python3
import math

import rospy
from ackermann_msgs.msg import AckermannDriveStamped
from geometry_msgs.msg import Twist


class TwistToAckermann:
    def __init__(self):
        self.in_topic = rospy.get_param("~in_topic", "/cmd_vel")
        self.out_topic = rospy.get_param("~out_topic", "/ackermann_cmd")
        self.frame_id = rospy.get_param("~frame_id", "base_link")
        self.wheelbase = float(rospy.get_param("~wheelbase", 0.26))
        self.max_steering_angle = float(rospy.get_param("~max_steering_angle", 0.45))
        self.min_speed_for_steer = float(rospy.get_param("~min_speed_for_steer", 0.05))
        self.speed_scale = float(rospy.get_param("~speed_scale", 1.0))
        self.steering_sign = float(rospy.get_param("~steering_sign", 1.0))
        self.publish_hz = float(rospy.get_param("~publish_hz", 30.0))
        self.timeout_s = float(rospy.get_param("~timeout_s", 0.30))
        self.publish_zero_on_timeout = bool(rospy.get_param("~publish_zero_on_timeout", True))

        self.last_msg = Twist()
        self.last_time = rospy.Time(0)
        self.pub = rospy.Publisher(self.out_topic, AckermannDriveStamped, queue_size=10)
        rospy.Subscriber(self.in_topic, Twist, self.cmd_cb, queue_size=10)
        self.timer = rospy.Timer(rospy.Duration(1.0 / max(self.publish_hz, 1.0)), self.timer_cb)

    @staticmethod
    def clamp(x, lo, hi):
        return max(lo, min(hi, x))

    def cmd_cb(self, msg):
        self.last_msg = msg
        self.last_time = rospy.Time.now()

    def convert(self, twist):
        out = AckermannDriveStamped()
        out.header.stamp = rospy.Time.now()
        out.header.frame_id = self.frame_id

        v = twist.linear.x * self.speed_scale
        omega = twist.angular.z

        if abs(v) < self.min_speed_for_steer:
            steer = 0.0
        else:
            steer = math.atan(self.wheelbase * omega / v)

        steer *= self.steering_sign
        steer = self.clamp(steer, -self.max_steering_angle, self.max_steering_angle)

        out.drive.speed = v
        out.drive.steering_angle = steer
        out.drive.steering_angle_velocity = 0.0
        out.drive.acceleration = 0.0
        out.drive.jerk = 0.0
        return out

    def timer_cb(self, _event):
        if self.last_time == rospy.Time(0):
            return

        age = (rospy.Time.now() - self.last_time).to_sec()
        if age > self.timeout_s and not self.publish_zero_on_timeout:
            return

        twist = Twist()
        if age <= self.timeout_s:
            twist = self.last_msg

        self.pub.publish(self.convert(twist))


if __name__ == "__main__":
    rospy.init_node("twist_to_ackermann")
    TwistToAckermann()
    rospy.loginfo("twist_to_ackermann started")
    rospy.spin()
