#!/usr/bin/env python3
"""scan_to_cloud.py – converts LaserScan → PointCloud2 using laser_geometry."""
import rospy
from sensor_msgs.msg import LaserScan, PointCloud2
import laser_geometry.laser_geometry as lg

class ScanToCloud:
    def __init__(self):
        self.scan_topic  = rospy.get_param("~scan_topic",  "/scan_filtered")
        self.cloud_topic = rospy.get_param("~cloud_topic", "/scan_cloud")
        self.proj = lg.LaserProjection()
        self.pub  = rospy.Publisher(self.cloud_topic, PointCloud2, queue_size=5)
        rospy.Subscriber(self.scan_topic, LaserScan, self.cb, queue_size=5)

    def cb(self, scan: LaserScan):
        cloud = self.proj.projectLaser(scan)
        cloud.header.stamp    = scan.header.stamp
        cloud.header.frame_id = scan.header.frame_id
        self.pub.publish(cloud)

if __name__ == "__main__":
    rospy.init_node("scan_to_cloud")
    ScanToCloud()
    rospy.spin()
