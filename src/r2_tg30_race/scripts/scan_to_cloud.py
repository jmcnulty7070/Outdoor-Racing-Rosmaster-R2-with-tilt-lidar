#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import LaserScan, PointCloud2
from laser_geometry import LaserProjection


class ScanToCloudNode:
    def __init__(self):
        scan_topic = rospy.get_param("~scan_topic", "/scan_filtered")
        cloud_topic = rospy.get_param("~cloud_topic", "/scan_cloud")
        self.projector = LaserProjection()
        self.pub = rospy.Publisher(cloud_topic, PointCloud2, queue_size=2)
        self.sub = rospy.Subscriber(scan_topic, LaserScan, self.cb, queue_size=2)

    def cb(self, scan_msg):
        try:
            cloud = self.projector.projectLaser(scan_msg)
            cloud.header = scan_msg.header
            self.pub.publish(cloud)
        except Exception as exc:
            rospy.logwarn_throttle(2.0, "scan_to_cloud failed: %s", exc)


if __name__ == "__main__":
    rospy.init_node("scan_to_cloud")
    ScanToCloudNode()
    rospy.loginfo("scan_to_cloud started")
    rospy.spin()
