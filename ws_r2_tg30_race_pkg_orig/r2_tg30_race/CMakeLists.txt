cmake_minimum_required(VERSION 3.0.2)
project(r2_tg30_race)

find_package(catkin REQUIRED COMPONENTS
  ackermann_msgs
  amcl
  geometry_msgs
  joy
  laser_filters
  laser_geometry
  map_server
  nav_msgs
  octomap_server
  pcl_ros
  pointcloud_to_laserscan
  roscpp
  rospy
  rviz
  sensor_msgs
  cartographer_ros
  std_msgs
  tf
  tf2
  tf2_ros
  twist_mux
  visualization_msgs
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
  scripts/joy_deadman.py
  scripts/cmdvel_gate.py
  scripts/mode_indicator.py
  scripts/twist_to_ackermann.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config urdf rviz maps waypoints
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
