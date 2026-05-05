#!/usr/bin/env python3
"""twist_to_ackermann.py – converts Twist → AckermannDriveStamped."""
import math, rospy
from geometry_msgs.msg import Twist
from ackermann_msgs.msg import AckermannDriveStamped

class TwistToAckermann:
    def __init__(self):
        self.in_topic  = rospy.get_param("~in_topic",   "/cmd_vel")
        self.out_topic = rospy.get_param("~out_topic",  "/ackermann_cmd")
        self.wheelbase = rospy.get_param("~wheelbase",  0.26)
        self.max_steer = rospy.get_param("~max_steering_angle", 0.45)
        self.pub = rospy.Publisher(self.out_topic, AckermannDriveStamped, queue_size=5)
        rospy.Subscriber(self.in_topic, Twist, self._cb, queue_size=5)

    def _cb(self, msg):
        out = AckermannDriveStamped()
        out.header.stamp = rospy.Time.now()
        out.drive.speed  = msg.linear.x
        if abs(msg.linear.x) > 1e-3 and abs(msg.angular.z) > 1e-4:
            radius = msg.linear.x / msg.angular.z
            steer  = math.atan2(self.wheelbase, radius)
        else:
            steer = 0.0
        out.drive.steering_angle = max(-self.max_steer, min(self.max_steer, steer))
        self.pub.publish(out)

if __name__ == "__main__":
    rospy.init_node("twist_to_ackermann")
    TwistToAckermann()
    rospy.spin()
