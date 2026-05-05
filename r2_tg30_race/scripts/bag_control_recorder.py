#!/usr/bin/env python3
"""bag_control_recorder.py – start/stop rosbag recording via service."""
import os, subprocess, rospy
from std_srvs.srv import SetBool, SetBoolResponse
from std_msgs.msg import Bool, String

class BagRecorder:
    def __init__(self):
        self.bag_dir     = rospy.get_param("~bag_dir",     os.path.expanduser("~/bags"))
        self.course_name = rospy.get_param("~course_name", "course")
        self.run_id      = rospy.get_param("~run_id",      "run01")
        self.topics      = rospy.get_param("~topics",
            ["/scan", "/scan_filtered", "/scan_cloud", "/tf", "/tf_static", "/odom", "/cmd_vel"])
        os.makedirs(self.bag_dir, exist_ok=True)
        self.proc = None
        self.pub_state = rospy.Publisher("~recording",  Bool,   queue_size=1, latch=True)
        self.pub_name  = rospy.Publisher("~bag_name",   String, queue_size=1, latch=True)
        rospy.Service("~set_recording", SetBool, self._srv_cb)
        self.pub_state.publish(Bool(data=False))

    def _srv_cb(self, req):
        if req.data and self.proc is None:
            bag_path = os.path.join(self.bag_dir,
                f"{self.course_name}_{self.run_id}.bag")
            cmd = ["rosbag", "record", "-O", bag_path] + self.topics
            self.proc = subprocess.Popen(cmd)
            self.pub_state.publish(Bool(data=True))
            self.pub_name.publish(String(data=bag_path))
            return SetBoolResponse(success=True, message=f"Recording to {bag_path}")
        elif not req.data and self.proc is not None:
            self.proc.terminate()
            self.proc = None
            self.pub_state.publish(Bool(data=False))
            return SetBoolResponse(success=True, message="Stopped")
        return SetBoolResponse(success=False, message="No state change")

if __name__ == "__main__":
    rospy.init_node("bag_control_recorder")
    BagRecorder()
    rospy.spin()
