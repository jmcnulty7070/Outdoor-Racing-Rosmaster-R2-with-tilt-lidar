cmake_minimum_required(VERSION 3.0.2)
project(r2_tg30_race)

find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  nav_msgs
  pcl_ros
  pointcloud_to_laserscan
  laser_filters
  laser_geometry
  roscpp
  rospy
  sensor_msgs
  std_msgs
  tf
  tf2
  tf2_ros
  visualization_msgs
  amcl
  map_server
  octomap_server
  slam_gmapping
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/scan_to_cloud.py
  scripts/bag_control_recorder.py
  scripts/waypoint_extractor.py
  scripts/waypoint_map_builder.py
  scripts/pure_pursuit_twist.py
  scripts/follow_the_gap.py
  scripts/steering_modifier.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config urdf rviz maps waypoints
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
