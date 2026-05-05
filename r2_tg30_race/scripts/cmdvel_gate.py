#!/usr/bin/env python3
"""cmdvel_gate.py – passes cmd_vel_auto_raw through only when /auto_enable is True."""
import rospy
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

class CmdVelGate:
    def __init__(self):
        enable_topic = rospy.get_param("~enable_topic", "/auto_enable")
        in_topic     = rospy.get_param("~in_topic",     "/cmd_vel_auto_raw")
        out_topic    = rospy.get_param("~out_topic",    "/cmd_vel_auto")
        self.rate_hz = rospy.get_param("~rate_hz",      30.0)
        self.pub_zero= rospy.get_param("~publish_zero_when_disabled", True)
        self.enabled = False
        self.last_cmd= Twist()
        self.pub = rospy.Publisher(out_topic, Twist, queue_size=5)
        rospy.Subscriber(enable_topic, Bool, lambda m: setattr(self, 'enabled', m.data))
        rospy.Subscriber(in_topic, Twist, self._cmd_cb, queue_size=5)
        rospy.Timer(rospy.Duration(1.0 / self.rate_hz), self._timer_cb)

    def _cmd_cb(self, msg):
        self.last_cmd = msg

    def _timer_cb(self, _):
        if self.enabled:
            self.pub.publish(self.last_cmd)
        elif self.pub_zero:
            self.pub.publish(Twist())

if __name__ == "__main__":
    rospy.init_node("cmdvel_gate")
    CmdVelGate()
    rospy.spin()
