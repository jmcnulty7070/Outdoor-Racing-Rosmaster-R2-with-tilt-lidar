#!/usr/bin/env python3
"""mode_indicator.py – logs current driving mode for debugging."""
import rospy
from std_msgs.msg import Bool, String

class ModeIndicator:
    def __init__(self):
        self.pub = rospy.Publisher("/driving_mode", String, queue_size=5, latch=True)
        rospy.Subscriber("/auto_enable", Bool, self._cb, queue_size=5)
        self.pub.publish(String(data="MANUAL"))

    def _cb(self, msg):
        self.pub.publish(String(data="AUTO" if msg.data else "MANUAL"))

if __name__ == "__main__":
    rospy.init_node("mode_indicator")
    ModeIndicator()
    rospy.spin()
