#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool


class JoyDeadman:
    def __init__(self):
        self.joy_topic = rospy.get_param("~joy_topic", "/joy")
        self.enable_topic = rospy.get_param("~enable_topic", "/auto_enable")
        self.button_index = int(rospy.get_param("~deadman_button_index", 5))
        self.publish_hz = float(rospy.get_param("~publish_hz", 30.0))
        self.joy_timeout = float(rospy.get_param("~joy_timeout", 0.75))

        self.last_joy_time = rospy.Time(0)
        self.enabled = False

        self.pub = rospy.Publisher(self.enable_topic, Bool, queue_size=1, latch=True)
        rospy.Subscriber(self.joy_topic, Joy, self.joy_cb, queue_size=10)
        self.timer = rospy.Timer(rospy.Duration(1.0 / max(self.publish_hz, 1.0)), self.timer_cb)

    def joy_cb(self, msg):
        self.last_joy_time = rospy.Time.now()
        if 0 <= self.button_index < len(msg.buttons):
            self.enabled = bool(msg.buttons[self.button_index])
        else:
            self.enabled = False

    def timer_cb(self, _event):
        if self.last_joy_time == rospy.Time(0):
            self.pub.publish(Bool(data=False))
            return
        fresh = (rospy.Time.now() - self.last_joy_time).to_sec() <= self.joy_timeout
        self.pub.publish(Bool(data=bool(self.enabled and fresh)))


if __name__ == "__main__":
    rospy.init_node("joy_deadman")
    JoyDeadman()
    rospy.loginfo("joy_deadman started")
    rospy.spin()
