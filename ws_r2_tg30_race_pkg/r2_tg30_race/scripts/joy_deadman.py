#!/usr/bin/env python3
"""joy_deadman.py – publishes /auto_enable True only while deadman button held."""
import rospy
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool

class JoyDeadman:
    def __init__(self):
        self.button_idx = rospy.get_param("~deadman_button", 4)
        self.pub = rospy.Publisher("/auto_enable", Bool, queue_size=5)
        rospy.Subscriber("/joy", Joy, self._cb, queue_size=5)
    def _cb(self, msg):
        if self.button_idx < len(msg.buttons):
            self.pub.publish(Bool(data=bool(msg.buttons[self.button_idx])))

if __name__ == "__main__":
    rospy.init_node("joy_deadman")
    JoyDeadman()
    rospy.spin()
