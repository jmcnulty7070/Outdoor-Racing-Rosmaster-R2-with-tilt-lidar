#!/usr/bin/env python3
"""
twist_to_rosmaster.py
=====================
Converts a standard ROS Twist (linear.x = speed, angular.z = turn rate)
into the ROSMASTER R2 Twist format:

  ROSMASTER R2 driver (Mcnamu_driver.py) expects:
    msg.linear.x  = forward speed (m/s)
    msg.linear.y  = steering angle in RADIANS (positive = left)
    msg.angular.z = passed through but largely unused by firmware

  Standard ROS navigation outputs:
    msg.linear.x  = forward speed (m/s)
    msg.angular.z = turn rate (rad/s)

Conversion:
  At speed v and turn rate w, the Ackermann steering angle is:
    steer_angle = atan(wheelbase * w / v)   [radians]

  When v ≈ 0 (stopped), steer angle = 0 (can't steer while stopped anyway).

Parameters:
  ~wheelbase_m   (float, default 0.26)  – front-to-rear axle distance in metres
  ~max_steer_rad (float, default 0.45)  – hardware steering limit in radians
  ~in_topic      (str)  – input  topic  (standard Twist)
  ~out_topic     (str)  – output topic  (ROSMASTER Twist, goes to /cmd_vel driver)
"""

import math
import rospy
from geometry_msgs.msg import Twist


class TwistToRosmaster:
    def __init__(self):
        rospy.init_node("twist_to_rosmaster")

        self.wheelbase  = rospy.get_param("~wheelbase_m",   0.26)
        self.max_steer  = rospy.get_param("~max_steer_rad", 0.45)
        in_topic        = rospy.get_param("~in_topic",  "/cmd_vel_nav")
        out_topic       = rospy.get_param("~out_topic", "/cmd_vel")

        self.pub = rospy.Publisher(out_topic, Twist, queue_size=5)
        rospy.Subscriber(in_topic, Twist, self._cb, queue_size=5)

        rospy.loginfo("[twist_to_rosmaster] %s → %s  wheelbase=%.3f m  max_steer=%.3f rad",
                      in_topic, out_topic, self.wheelbase, self.max_steer)
        rospy.spin()

    def _cb(self, msg):
        out = Twist()
        out.linear.x = msg.linear.x

        vx = msg.linear.x
        wz = msg.angular.z

        if abs(vx) > 0.01:
            # Pure-pursuit / standard nav: angular.z = v / R  →  steer = atan(L/R) = atan(L*w/v)
            steer = math.atan2(self.wheelbase * wz, vx)
        elif abs(wz) > 0.01:
            # Turning on the spot — clamp to max steer
            steer = math.copysign(self.max_steer, wz)
        else:
            steer = 0.0

        # Clamp to hardware limit
        steer = max(-self.max_steer, min(self.max_steer, steer))

        out.linear.y  = steer   # ROSMASTER steering field
        out.angular.z = wz      # pass through (firmware largely ignores it)

        self.pub.publish(out)


if __name__ == "__main__":
    TwistToRosmaster()
