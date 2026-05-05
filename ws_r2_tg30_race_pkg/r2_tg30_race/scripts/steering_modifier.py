#!/usr/bin/env python3
"""
steering_modifier.py
====================
Blends pure-pursuit and FTG commands based on proximity to obstacles.
/scan_obstacles already contains curb and grass-edge returns, so this node
provides the final safety layer without any additional sensor processing.

Priority logic:
  dist < stop_distance   → zero (hard stop)
  dist < danger_distance → FTG command (reactive)
  dist < blend_distance  → weighted blend PP/FTG
  else                   → pure pursuit (race line)
"""
import math, numpy as np
import rospy
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

class SteeringModifier:
    def __init__(self):
        rospy.init_node("steering_modifier")
        pp_topic      = rospy.get_param("~pp_topic",       "/cmd_vel_auto")
        ftg_topic     = rospy.get_param("~ftg_topic",      "/cmd_vel_ftg_raw")
        scan_topic    = rospy.get_param("~scan_topic",     "/scan_obstacles")
        enable_topic  = rospy.get_param("~enable_topic",   "/auto_enable")
        cmd_topic     = rospy.get_param("~cmd_topic",      "/cmd_vel_safety")
        self.stop_d   = rospy.get_param("~stop_distance",  0.40)
        self.danger_d = rospy.get_param("~danger_distance",1.10)
        self.blend_d  = rospy.get_param("~blend_distance", 1.60)
        self.fov      = math.radians(rospy.get_param("~front_fov_deg", 110.0))
        rate          = rospy.get_param("~publish_hz",     25.0)

        self.pp_cmd  = Twist()
        self.ftg_cmd = Twist()
        self.enabled = False
        self.min_dist= float('inf')

        self.pub = rospy.Publisher(cmd_topic, Twist, queue_size=5)
        rospy.Subscriber(pp_topic,    Twist,     lambda m: setattr(self, 'pp_cmd',  m))
        rospy.Subscriber(ftg_topic,   Twist,     lambda m: setattr(self, 'ftg_cmd', m))
        rospy.Subscriber(enable_topic,Bool,      lambda m: setattr(self, 'enabled', m.data))
        rospy.Subscriber(scan_topic,  LaserScan, self._scan_cb, queue_size=1)
        rospy.Timer(rospy.Duration(1.0 / rate), self._publish)
        rospy.spin()

    def _scan_cb(self, msg):
        ranges = np.array(msg.ranges)
        angles = msg.angle_min + np.arange(len(ranges)) * msg.angle_increment
        mask   = np.abs(angles) <= self.fov / 2.0
        front  = ranges[mask]
        front  = front[np.isfinite(front)]
        self.min_dist = float(np.min(front)) if len(front) > 0 else float('inf')

    def _publish(self, _):
        if not self.enabled:
            self.pub.publish(Twist())
            return
        d = self.min_dist
        if d < self.stop_d:
            self.pub.publish(Twist())
        elif d < self.danger_d:
            self.pub.publish(self.ftg_cmd)
        elif d < self.blend_d:
            alpha = (d - self.danger_d) / (self.blend_d - self.danger_d)  # 0→1 as d increases
            cmd = Twist()
            cmd.linear.x  = alpha * self.pp_cmd.linear.x  + (1-alpha) * self.ftg_cmd.linear.x
            cmd.angular.z = alpha * self.pp_cmd.angular.z + (1-alpha) * self.ftg_cmd.angular.z
            self.pub.publish(cmd)
        else:
            self.pub.publish(self.pp_cmd)

if __name__ == "__main__":
    SteeringModifier()
