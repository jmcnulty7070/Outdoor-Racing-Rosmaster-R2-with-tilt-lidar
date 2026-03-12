#!/usr/bin/env python3
import math

import rospy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan


class FollowTheGap:
    def __init__(self):
        self.scan_topic = rospy.get_param("~scan_topic", "/scan_obstacles")
        self.cmd_topic = rospy.get_param("~cmd_topic", "/ftg_cmd_vel")
        self.danger_distance = rospy.get_param("~danger_distance", 1.20)
        self.stop_distance = rospy.get_param("~stop_distance", 0.45)
        self.front_angle_deg = rospy.get_param("~front_angle_deg", 110.0)
        self.bubble_radius_idx = int(rospy.get_param("~bubble_radius_idx", 8))
        self.gap_threshold = rospy.get_param("~gap_threshold", 1.20)
        self.max_speed = rospy.get_param("~max_speed", 0.80)
        self.min_speed = rospy.get_param("~min_speed", 0.18)
        self.max_angular = rospy.get_param("~max_angular_z", 1.60)

        self.pub = rospy.Publisher(self.cmd_topic, Twist, queue_size=1)
        rospy.Subscriber(self.scan_topic, LaserScan, self.scan_cb, queue_size=1)

    def sanitize_ranges(self, ranges, rmin, rmax):
        out = []
        for r in ranges:
            if math.isfinite(r):
                out.append(min(max(r, rmin), rmax))
            else:
                out.append(rmax)
        return out

    def scan_cb(self, msg):
        if not msg.ranges:
            return

        ranges = self.sanitize_ranges(msg.ranges, msg.range_min or 0.01, msg.range_max or 10.0)
        half = math.radians(self.front_angle_deg / 2.0)

        indices = []
        for i in range(len(ranges)):
            angle = msg.angle_min + i * msg.angle_increment
            if -half <= angle <= half:
                indices.append(i)

        if not indices:
            return

        front_ranges = [ranges[i] for i in indices]
        min_front = min(front_ranges)
        if min_front <= self.stop_distance:
            cmd = Twist()
            cmd.linear.x = 0.0
            cmd.angular.z = self.max_angular * 0.5
            self.pub.publish(cmd)
            return

        closest_local = min(range(len(front_ranges)), key=lambda i: front_ranges[i])

        bubble_start = max(0, closest_local - self.bubble_radius_idx)
        bubble_end = min(len(front_ranges) - 1, closest_local + self.bubble_radius_idx)
        proc = list(front_ranges)
        for i in range(bubble_start, bubble_end + 1):
            proc[i] = 0.0

        best_start = best_end = None
        cur_start = None
        for i, r in enumerate(proc):
            if r >= self.gap_threshold:
                if cur_start is None:
                    cur_start = i
            else:
                if cur_start is not None:
                    if best_start is None or (i - 1 - cur_start) > (best_end - best_start):
                        best_start, best_end = cur_start, i - 1
                    cur_start = None
        if cur_start is not None:
            if best_start is None or (len(proc) - 1 - cur_start) > (best_end - best_start if best_end is not None else -1):
                best_start, best_end = cur_start, len(proc) - 1

        if best_start is None:
            best_idx = len(front_ranges) // 2
        else:
            best_idx = (best_start + best_end) // 2

        global_idx = indices[best_idx]
        best_angle = msg.angle_min + global_idx * msg.angle_increment
        angular_z = max(min(best_angle * 1.4, self.max_angular), -self.max_angular)

        clearance_scale = max(0.0, min((min_front - self.stop_distance) / max(self.danger_distance - self.stop_distance, 1e-6), 1.0))
        linear_x = self.min_speed + (self.max_speed - self.min_speed) * clearance_scale
        linear_x *= max(0.35, 1.0 - abs(best_angle) / max(half, 1e-6) * 0.5)

        cmd = Twist()
        cmd.linear.x = linear_x
        cmd.angular.z = angular_z
        self.pub.publish(cmd)


if __name__ == "__main__":
    rospy.init_node("follow_the_gap")
    FollowTheGap()
    rospy.loginfo("follow_the_gap started")
    rospy.spin()
