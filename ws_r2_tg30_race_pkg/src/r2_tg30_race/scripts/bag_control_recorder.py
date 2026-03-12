#!/usr/bin/env python3
import os
import signal
import subprocess
from datetime import datetime

import rospy
from std_msgs.msg import Bool


class BagControlRecorder:
    def __init__(self):
        self.output_dir = rospy.get_param(
            "~output_dir",
            os.path.expanduser("~/ws_r2_tg30_race_pkg/src/r2_tg30_race/bags")
        )
        self.topics = rospy.get_param(
            "~topics",
            ["/scan", "/scan_filtered", "/scan_obstacles", "/tf", "/odom", "/cmd_vel", "/joy", "/imu/data"]
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self.proc = None
        rospy.Subscriber("/bag_record_cmd", Bool, self.command_cb, queue_size=1)
        rospy.on_shutdown(self.stop_recording)

    def command_cb(self, msg):
        if msg.data:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        if self.proc is not None and self.proc.poll() is None:
            rospy.loginfo("rosbag already running")
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bag_path = os.path.join(self.output_dir, f"course_run_{stamp}.bag")
        cmd = ["rosbag", "record", "-O", bag_path] + self.topics
        rospy.loginfo("Starting rosbag: %s", " ".join(cmd))
        self.proc = subprocess.Popen(cmd, preexec_fn=os.setsid)

    def stop_recording(self):
        if self.proc is None:
            return
        if self.proc.poll() is None:
            rospy.loginfo("Stopping rosbag recorder")
            os.killpg(os.getpgid(self.proc.pid), signal.SIGINT)
            try:
                self.proc.wait(timeout=5.0)
            except Exception:
                pass
        self.proc = None


if __name__ == "__main__":
    rospy.init_node("bag_control_recorder")
    BagControlRecorder()
    rospy.loginfo("bag_control_recorder ready on /bag_record_cmd")
    rospy.spin()
