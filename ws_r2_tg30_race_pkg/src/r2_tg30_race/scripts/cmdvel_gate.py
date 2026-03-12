#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool


class CmdVelGate:
    def __init__(self):
        self.enable_topic = rospy.get_param("~enable_topic", "/auto_enable")
        self.in_topic = rospy.get_param("~in_topic", "/cmd_vel_auto_raw")
        self.out_topic = rospy.get_param("~out_topic", "/cmd_vel_auto")
        self.rate_hz = float(rospy.get_param("~rate_hz", 30.0))
        self.publish_zero_when_disabled = bool(rospy.get_param("~publish_zero_when_disabled", True))

        self.enabled = False
        self.last_enabled = False
        self.latest_cmd = Twist()
        self.have_cmd = False

        self.pub = rospy.Publisher(self.out_topic, Twist, queue_size=10)
        rospy.Subscriber(self.enable_topic, Bool, self.enable_cb, queue_size=10)
        rospy.Subscriber(self.in_topic, Twist, self.cmd_cb, queue_size=10)
        self.timer = rospy.Timer(rospy.Duration(1.0 / max(self.rate_hz, 1.0)), self.timer_cb)

    def enable_cb(self, msg):
        self.enabled = bool(msg.data)

    def cmd_cb(self, msg):
        self.latest_cmd = msg
        self.have_cmd = True

    def timer_cb(self, _event):
        if self.enabled and self.have_cmd:
            self.pub.publish(self.latest_cmd)
        elif self.publish_zero_when_disabled and self.last_enabled:
            self.pub.publish(Twist())
        self.last_enabled = self.enabled


if __name__ == "__main__":
    rospy.init_node("cmdvel_gate")
    CmdVelGate()
    rospy.loginfo("cmdvel_gate started")
    rospy.spin()
